"""Records every real fixture deck and checks the actual video's duration and final frame against the computed plan.

Requires:
    docker pull registry.gitlab.com/riphixel/docker-libreoffice-impress:latest
    python3 -m venv .venv && .venv/bin/pip install -e ".[test]"

Run from the project root:
    .venv/bin/pytest tests/ -v
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest
from PIL import Image
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from slides2images.animation_timeline import build_recording_plan
from slides2images.recorder import CONTAINER_CONTROL_SCRIPT_PATH, IMAGE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

CONTAINER_PPTX_PATH = "/tmp/deck.pptx"
CONTAINER_PLAN_PATH = "/tmp/plan.json"
CONTAINER_OUTPUT_PATH = "/tmp/output/recording.mp4"
CONTAINER_FRAMES_PATH = "/tmp/output/frames"

CLICK_DELAY_MS = 500
LEAD_IN_S = 0.3  # matches control_record.py's own LEAD_IN_S default

END_OF_SHOW_MEAN_BRIGHTNESS_THRESHOLD = 0.05  # brightness signature of Impress's "Click to exit presentation…" placeholder
TOLERANCE_S = 2.5  # real-time X11 capture has overhead (UNO round trips, ffmpeg start/stop) an offline renderer wouldn't


def _expected_seconds(plan: list[dict[str, Any]]) -> float:
    total_ms: float = sum(sum(entry["click_gaps_ms"]) + entry["post_click_hold_ms"] for entry in plan)
    return total_ms / 1000.0 + LEAD_IN_S


def _expected_frame_names(plan: list[dict[str, Any]]) -> list[str]:
    """`frame-<slide_index>-<capture_index>.png` per entry, capture_index reset per slide."""
    names: list[Any] = []
    for entry in plan:
        capture_count = len(entry["click_gaps_ms"]) or 1
        names.extend(f"frame-{entry['index']}-{capture_index}.png" for capture_index in range(capture_count))
    return names


# "no slide.pptx" has zero slides and gets its own dedicated test below.
FIXTURE_CASES = sorted(p.name for p in FIXTURES_DIR.glob("*.pptx") if p.name != "no slide.pptx")


def _put_file(container: DockerContainer, local_path: Path, container_path: str) -> None:
    dest_dir, dest_name = container_path.rsplit("/", 1)
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar.add(str(local_path), arcname=dest_name)
    _ = tar_stream.seek(0)
    _ = container.get_wrapped_container().put_archive(dest_dir, tar_stream.read())


def _put_bytes(container: DockerContainer, data: bytes, container_path: str) -> None:
    dest_dir, dest_name = container_path.rsplit("/", 1)
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        info = tarfile.TarInfo(name=dest_name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    _ = tar_stream.seek(0)
    _ = container.get_wrapped_container().put_archive(dest_dir, tar_stream.read())


def _get_file(container: DockerContainer, container_path: str) -> bytes:
    stream, _stat = container.get_wrapped_container().get_archive(container_path)
    tar_bytes = b"".join(stream)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        member = tar.getmembers()[0]
        extracted = tar.extractfile(member)
        assert extracted is not None
        return extracted.read()


def _get_dir_files(container: DockerContainer, container_dir: str) -> dict[str, bytes]:
    """{basename: contents} for every regular file directly inside container_dir."""
    stream, _stat = container.get_wrapped_container().get_archive(container_dir)
    tar_bytes = b"".join(stream)
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                extracted = tar.extractfile(member)
                assert extracted is not None
                files[Path(member.name).name] = extracted.read()
    return files


def _ffprobe_duration_s(mp4_bytes: bytes) -> float:
    with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
        _ =  f.write(mp4_bytes)
        f.flush()
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                f.name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())


def _last_frame_mean_brightness(mp4_bytes: bytes) -> float:
    """Decode the recording's actual last frame and return its mean grayscale brightness (0-1)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4") as mp4_f, tempfile.NamedTemporaryFile(suffix=".png") as png_f:
        _ =  mp4_f.write(mp4_bytes)
        mp4_f.flush()
        _ = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-sseof",
                "-0.15",
                "-i",
                mp4_f.name,
                "-update",
                "1",
                "-q:v",
                "2",
                png_f.name,
            ],
            check=True,
        )
        with Image.open(png_f.name) as img:
            grayscale = img.convert("L")
            # get_flattened_data()'s stub covers multi-band images too (tuple[tuple[int, ...], ...]);
            # a single-band "L" image always returns a flat tuple[int, ...] at runtime.
            pixels = grayscale.get_flattened_data()
            return (sum(pixels) / len(pixels)) / 255.0  # type: ignore[arg-type]  # pyright: ignore[reportCallIssue, reportArgumentType] -- see above


@pytest.fixture()
def lo_container() -> Generator[Any, Any, None]:
    # Function-scoped deliberately, not module-scoped: a shared soffice session was found to reliably
    # SIGABRT after roughly a dozen consecutive loadComponentFromURL/close cycles.
    # VGA, not the 1920x1080 default: this suite only checks duration/frame-count/end-of-show
    # brightness, none of which depend on resolution -- and a smaller display cuts Xvnc render,
    # ffmpeg encode, and import -window root capture cost per operation, on shared CI runners.
    container = (
        DockerContainer(IMAGE)
        .with_env("DISPLAY_WIDTH", "640")
        .with_env("DISPLAY_HEIGHT", "480")
        .waiting_for(LogMessageWaitStrategy("all services started").with_startup_timeout(60))
    )
    with container:
        yield container


@pytest.mark.parametrize("fixture_name", FIXTURE_CASES)
def test_recording_duration_and_final_frame(lo_container: DockerContainer, fixture_name: str) -> None:
    """Record one fixture and check its duration, its live-captured frames, and its final video frame."""
    pptx_path = FIXTURES_DIR / fixture_name
    plan = build_recording_plan(pptx_path, click_delay_ms=CLICK_DELAY_MS)
    assert plan, f"{fixture_name} has no slides"

    expected_s = _expected_seconds(plan)
    expected_frame_names = _expected_frame_names(plan)

    _put_file(lo_container, pptx_path, CONTAINER_PPTX_PATH)
    _put_bytes(lo_container, json.dumps(plan).encode(), CONTAINER_PLAN_PATH)
    _ = lo_container.exec(["mkdir", "-p", "/tmp/output"])

    exit_code, output = lo_container.exec(
        [
            "python3",
            CONTAINER_CONTROL_SCRIPT_PATH,
            "--pptx",
            CONTAINER_PPTX_PATH,
            "--plan",
            CONTAINER_PLAN_PATH,
            "--output",
            CONTAINER_OUTPUT_PATH,
            "--frames-dir",
            CONTAINER_FRAMES_PATH,
        ]
    )
    stdout = output.decode() if isinstance(output, (bytes, bytearray)) else str(output)
    assert exit_code == 0, f"control_record.py failed (exit {exit_code}) for {fixture_name!r}:\n{stdout}"

    result = json.loads(stdout.strip().splitlines()[-1])
    assert result["ok"] is True, result

    # Live-captured frames — one per click_gaps_ms entry, or one for a click-less slide.
    frame_files = _get_dir_files(lo_container, CONTAINER_FRAMES_PATH)
    assert sorted(frame_files) == sorted(expected_frame_names), (
        f"{fixture_name}: expected {expected_frame_names}, got {sorted(frame_files)}"
    )
    for name, data in frame_files.items():
        # 100, not 1000: at VGA a simple/mostly-blank slide's PNG can legitimately compress to a few
        # hundred bytes (e.g. "one slide.pptx" -> 255 bytes) -- this just catches an empty/corrupt capture.
        assert len(data) > 100, f"{fixture_name}: frame {name} suspiciously small ({len(data)} bytes)"

    mp4_bytes = _get_file(lo_container, CONTAINER_OUTPUT_PATH)
    assert len(mp4_bytes) > 1000, f"{fixture_name}: recording suspiciously small ({len(mp4_bytes)} bytes)"

    # Level 1 — duration.
    actual_s = _ffprobe_duration_s(mp4_bytes)
    diff = abs(actual_s - expected_s)
    assert diff <= TOLERANCE_S, (
        f"{fixture_name}: expected ~{expected_s:.2f}s, got {actual_s:.2f}s (diff {diff:.2f}s > tolerance {TOLERANCE_S}s). Plan: {plan}"
    )

    # Level 3 — final-frame content, independent of control_record.py's own self-report above.
    brightness = _last_frame_mean_brightness(mp4_bytes)
    assert brightness >= END_OF_SHOW_MEAN_BRIGHTNESS_THRESHOLD, (
        f"{fixture_name}: final frame mean brightness {brightness:.4f} is below "
        f"{END_OF_SHOW_MEAN_BRIGHTNESS_THRESHOLD} — looks like the end-of-show "
        "placeholder, not real slide content"
    )


def test_empty_deck_has_zero_duration_and_is_not_recorded() -> None:
    """ "no slide.pptx" has zero slides: the plan is empty and no recording is attempted."""
    plan = build_recording_plan(FIXTURES_DIR / "no slide.pptx", click_delay_ms=CLICK_DELAY_MS)
    assert plan == []
