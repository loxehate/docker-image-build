#!/usr/bin/env python3
"""Drives a live Impress slideshow through a precomputed plan while ffmpeg records the X11 display; see IMPRESS_PROTOCOL.md."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uno  # type: ignore[import-not-found]  # provided by the container's system Python at runtime; no stub package exists
from com.sun.star.beans import PropertyValue  # type: ignore[import-not-found]

DISPLAY = ":0"
DISPLAY_SIZE = f"{os.environ.get('DISPLAY_WIDTH', '1920')}x{os.environ.get('DISPLAY_HEIGHT', '1080')}"  # keeps ffmpeg in sync with Xvfb
FRAMERATE = "30"
UNO_HOST = "localhost"
UNO_PORT = 2002
CONNECT_TIMEOUT_S = 30
CONNECT_RETRY_INTERVAL_S = 0.5
SLIDESHOW_READY_TIMEOUT_S = 15
SLIDESHOW_READY_RETRY_INTERVAL_S = 0.05
SLIDESHOW_RENDER_SETTLE_S = float(os.environ.get("SLIDESHOW_RENDER_SETTLE_S", "1.0"))

LEAD_IN_S = float(os.environ.get("LEAD_IN_S", "0.3"))  # full-screen first slide held while ffmpeg starts, before animations resume

ADVANCE_STEP_TIMEOUT_S = 2.0  # ceiling per gotoNextSlide() call for the index to actually change
ADVANCE_TOTAL_TIMEOUT_S = 5.0  # ceiling for the whole per-slide advance


def make_prop(name: str, value) -> PropertyValue:
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def connect(local_context):
    resolver = local_context.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local_context)
    uno_url = f"uno:socket,host={UNO_HOST},port={UNO_PORT};urp;StarOffice.ComponentContext"
    deadline = time.monotonic() + CONNECT_TIMEOUT_S
    last_err = None
    while time.monotonic() < deadline:
        try:
            return resolver.resolve(uno_url)
        except Exception as exc:  # noqa: BLE001 - broad on purpose, this is a retry loop
            last_err = exc
            time.sleep(CONNECT_RETRY_INTERVAL_S)
    raise RuntimeError(f"could not connect to UNO socket after {CONNECT_TIMEOUT_S}s: {last_err}")


def start_recording(output_path: str) -> subprocess.Popen:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "x11grab",
        "-video_size",
        DISPLAY_SIZE,
        "-framerate",
        FRAMERATE,
        "-draw_mouse",  # without this ffmpeg draws the static, never-moved X11 cursor into every frame
        "0",
        "-i",
        DISPLAY,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_recording(proc: subprocess.Popen) -> None:
    # 'q' on stdin is ffmpeg's own clean-shutdown request; a bare SIGKILL can leave a truncated file.
    try:
        proc.communicate(input=b"q", timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()


def capture_frame(output_path: str) -> None:
    """A direct X11 screenshot of the current display — ground truth for 'settled after this
    click', instead of guessing a timestamp in the ffmpeg recording after the fact.
    """
    subprocess.run(["import", "-display", DISPLAY, "-window", "root", output_path], check=True)


def wait_for_slideshow_ready(controller, expected_slide_index: int) -> None:
    """Wait until the full-screen slideshow, rather than the Impress editor, owns the presentation UI."""
    deadline = time.monotonic() + SLIDESHOW_READY_TIMEOUT_S
    last_state = None
    while time.monotonic() < deadline:
        last_state = {
            "running": controller.isRunning(),
            "active": controller.isActive(),
            "fullscreen": controller.isFullScreen(),
            "paused": controller.isPaused(),
            "slide_index": controller.getCurrentSlideIndex(),
        }
        if (
            last_state["running"]
            and last_state["active"]
            and last_state["fullscreen"]
            and last_state["paused"]
            and last_state["slide_index"] == expected_slide_index
        ):
            return
        controller.activate()
        time.sleep(SLIDESHOW_READY_RETRY_INTERVAL_S)
    raise RuntimeError(f"slideshow window did not become ready within {SLIDESHOW_READY_TIMEOUT_S}s; last state: {last_state}")


def advance_to_slide(controller, target_index: int) -> int:
    """Advance to target_index, calling gotoNextSlide() only while genuinely behind it; see IMPRESS_PROTOCOL.md §6."""
    total_deadline = time.monotonic() + ADVANCE_TOTAL_TIMEOUT_S
    while controller.getCurrentSlideIndex() < target_index and time.monotonic() < total_deadline:
        before = controller.getCurrentSlideIndex()
        controller.gotoNextSlide()
        step_deadline = time.monotonic() + ADVANCE_STEP_TIMEOUT_S  # a transition takes real wall-clock time to land
        while controller.getCurrentSlideIndex() == before and time.monotonic() < step_deadline:
            time.sleep(0.05)
    return controller.getCurrentSlideIndex()


# len(click_gaps_ms) per slide can structurally overcount the real gotoNextEffect() calls a slide
# needs; harmless now that auto-advance is disabled (see IMPRESS_PROTOCOL.md §6/§9), but not itself fixed.


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument(
        "--plan",
        required=True,
        help="JSON file: [{index, click_gaps_ms: [...], post_click_hold_ms}, ...] "
        "(see src/slides2images/animation_timeline.py's build_recording_plan())",
    )
    parser.add_argument("--output", required=True, help="Output .mp4 path")
    parser.add_argument("--frames-dir", required=True, help="Directory for one live screenshot per settled click")
    args = parser.parse_args()

    with open(args.plan) as f:
        plan = json.load(f)

    os.makedirs(args.frames_dir, exist_ok=True)

    result = {"ok": False, "steps": [], "plan": plan}

    local_context = uno.getComponentContext()
    ctx = connect(local_context)
    _ = result["steps"].append("connected")

    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    file_url = f"file://{args.pptx}"
    load_props = (make_prop("Hidden", False),)
    doc = desktop.loadComponentFromURL(file_url, "_blank", 0, load_props)
    _ = result["steps"].append("loaded")
    editor_window = doc.getCurrentController().getFrame().getContainerWindow()

    # Disable per-slide auto-advance BEFORE starting the show, so manual driving is the sole advance
    # mechanism and nothing races an advTm timer into overshoot — see IMPRESS_PROTOCOL.md §6.
    try:
        draw_pages = doc.getDrawPages()
        for i in range(draw_pages.getCount()):
            draw_pages.getByIndex(i).Change = 0
        _ = result["steps"].append(f"disabled auto-advance on {draw_pages.getCount()} page(s)")
    except Exception as exc:  # noqa: BLE001 - non-fatal; index-checked advancing still guards overshoot
        result["steps"].append(f"could not disable auto-advance (non-fatal): {exc}")

    recording = None
    controller = None
    try:
        presentation = doc.getPresentation()
        presentation.IsFullScreen = True
        presentation.IsAlwaysOnTop = True
        presentation.StartWithNavigator = False
        presentation.start()

        deadline = time.monotonic() + 15
        while True:
            if presentation.isRunning():
                controller = presentation.getController()
                if controller is not None:
                    controller.pause()
                    break
            if time.monotonic() > deadline:
                raise RuntimeError("presentation never produced a running slideshow controller")
            time.sleep(SLIDESHOW_READY_RETRY_INTERVAL_S)
        _ = result["steps"].append("presentation running and paused")

        # The slideshow has its own window. Remove the document editor from X11 before
        # recording so delayed focus/mapping cannot leak its toolbars into the video.
        editor_window.setVisible(False)
        _ = result["steps"].append("editor window hidden")

        controller.AlwaysOnTop = True
        controller.activate()
        expected_slide_index = plan[0]["index"] if plan else 0
        wait_for_slideshow_ready(controller, expected_slide_index)
        time.sleep(SLIDESHOW_RENDER_SETTLE_S)
        _ = result["steps"].append(f"fullscreen slideshow ready on slide {expected_slide_index}")

        recording = start_recording(args.output)
        _ = result["steps"].append("recording started")
        time.sleep(LEAD_IN_S)
        controller.resume()
        _ = result["steps"].append("slideshow resumed")

        total_frame_count = 0
        for pos, entry in enumerate(plan):
            is_last_entry = pos == len(plan) - 1
            click_gaps_ms = entry.get("click_gaps_ms", [])
            post_click_hold_ms = entry.get("post_click_hold_ms", 0)
            slide_index = entry["index"]
            capture_index = 0

            slide_start = time.monotonic()
            for gap_ms in click_gaps_ms:
                controller.gotoNextEffect()
                time.sleep(gap_ms / 1000.0)
                # Ground truth for "settled after this click" — captured live, right before
                # whatever comes next (the following click, or advancing off this slide), rather
                # than reconstructed later from a plan-derived guess at a video timestamp.
                capture_frame(os.path.join(args.frames_dir, f"frame-{slide_index}-{capture_index}.png"))
                capture_index += 1
                total_frame_count += 1

            # Spend whatever's left of this slide's computed budget.
            elapsed_s = time.monotonic() - slide_start
            total_budget_s = (sum(click_gaps_ms) + post_click_hold_ms) / 1000.0
            time.sleep(max(0.0, total_budget_s - elapsed_s))

            if not click_gaps_ms:
                # No click chains at all: one frame for the whole slide, at the end of its hold —
                # not the start, so it can't land on the previous slide's transition tail.
                capture_frame(os.path.join(args.frames_dir, f"frame-{slide_index}-{capture_index}.png"))
                capture_index += 1
                total_frame_count += 1

            if is_last_entry:
                result["steps"].append(f"slide {entry['index']}: terminal slide held")  # holds full budget, no advance
            else:
                next_index = plan[pos + 1]["index"]
                landed = advance_to_slide(controller, next_index)
                if landed != next_index:
                    result["steps"].append(f"slide {entry['index']}: advance landed on index {landed}, expected {next_index}")

        _ = result["steps"].append(f"all slides played, {total_frame_count} frame(s) captured")
        result["ok"] = True
    finally:
        if recording is not None:
            stop_recording(recording)
            _ = result["steps"].append("recording stopped")
        if controller is not None:
            try:
                controller.deactivate()  # after stop_recording() on purpose: this can itself touch the screen
            except Exception as exc:  # noqa: BLE001 - best-effort; an early-ended show can leave this throwing, non-fatal
                _ = result["steps"].append(f"controller.deactivate() failed (non-fatal): {exc}")
        try:
            doc.close(False)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass

    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
