"""The conversion pipeline: normalize a presentation, compute its timing plan, and drive
docker-libreoffice-impress to record it and capture a live screenshot per settled click.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosemgrep: cache.semgrep.gitlab.bandit.B404 -- every call site below uses list-form args, no shell=True, no untrusted string interpolation
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .animation_timeline import CLICK_DELAY_MS, build_recording_plan

IMAGE = os.environ.get("SLIDES2IMAGES_IMPRESS_IMAGE", "registry.gitlab.com/riphixel/docker-libreoffice-impress:latest")
CONTAINER_NAME_PREFIX = "slides2images"
CONTAINER_CONTROL_SCRIPT_PATH = "/opt/control_record.py"  # baked into the image, not copied in per job
CONTAINER_READY_TIMEOUT_S = 60

RESOLUTIONS: dict[str, tuple[int, int]] = {  # "hd" is Full HD (1080p), distinct from the separate "720p" tier
    "vga": (640, 480),
    "720p": (1280, 720),
    "hd": (1920, 1080),
    "4k": (3840, 2160),
}

SUPPORTED_EXTENSIONS = {
    # OOXML, strict and transitional
    ".pptx",
    ".ppsx",
    ".ppmx",
    ".potx",
    ".pomx",
    # legacy PowerPoint 97/2000/XP/2003 binary format
    ".ppt",
    ".pps",
    ".ppm",
    ".pot",
    ".pom",
}


class RecordingError(RuntimeError):
    """Any expected failure in the normalize/plan/record pipeline."""


@dataclass
class ConversionResult:
    video_path: Path
    image_paths: list[Path]


def normalize_to_pptx(input_path: Path, workdir: Path) -> Path:
    """Convert to .pptx via a throwaway headless container if not already one; python-pptx only opens the modern OOXML zip structure."""
    if input_path.suffix.lower() == ".pptx":
        return input_path

    workdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "soffice",
            "-v",
            f"{input_path.parent}:/in:ro",
            "-v",
            f"{workdir}:/out",
            IMAGE,
            "--headless",
            "--convert-to",
            "pptx",
            "--outdir",
            "/out",
            "-env:UserInstallation=file:///tmp/lo-profile",  # overriding --entrypoint skips baseimage-gui's own profile setup
            f"/in/{input_path.name}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RecordingError(f"format conversion to .pptx failed (exit {result.returncode}): {result.stderr.strip()}")

    converted = workdir / f"{input_path.stem}.pptx"
    if not converted.exists():
        raise RecordingError(f"format conversion reported success but {converted.name} was not produced")
    return converted


def compute_plan(pptx_path: Path, click_delay_ms: int) -> list[dict[str, Any]]:
    try:
        return build_recording_plan(pptx_path, click_delay_ms=click_delay_ms)
    except Exception as exc:
        raise RecordingError(f"could not compute animation timing: {exc}") from exc


def _wait_for_container_ready(container_name: str) -> None:
    deadline = time.monotonic() + CONTAINER_READY_TIMEOUT_S
    while time.monotonic() < deadline:
        logs = subprocess.run(["docker", "logs", container_name], capture_output=True, text=True, check=False)
        if "all services started" in (logs.stdout + logs.stderr):
            return
        running = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if running != "true":
            raise RecordingError(f"container {container_name} exited before becoming ready")
        time.sleep(1)
    raise RecordingError(f"container {container_name} did not become ready within {CONTAINER_READY_TIMEOUT_S}s")


def record_video(
    pptx_path: Path,
    plan: list[dict[str, Any]],
    width: int,
    height: int,
    output_path: Path,
    images_dir: Path,
) -> None:
    """Runs control_record.py in a fresh container: records output_path and, alongside it, one
    live screenshot per settled click into images_dir (see docker-libreoffice-impress's own
    README for the frame-count/ordering contract — same as build_recording_plan()'s click_gaps_ms).
    """
    if not plan:
        raise RecordingError("deck has no slides — nothing to record")

    container_name = f"{CONTAINER_NAME_PREFIX}-{uuid.uuid4().hex[:12]}"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-e",
            f"DISPLAY_WIDTH={width}",
            "-e",
            f"DISPLAY_HEIGHT={height}",
            IMAGE,
        ],
        check=True,
        capture_output=True,
    )
    try:
        _wait_for_container_ready(container_name)
        subprocess.run(["docker", "exec", container_name, "mkdir", "-p", "/tmp/output"], check=True)
        subprocess.run(["docker", "cp", str(pptx_path), f"{container_name}:/tmp/deck.pptx"], check=True)

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(plan, f)
            plan_local_path = f.name
        try:
            subprocess.run(["docker", "cp", plan_local_path, f"{container_name}:/tmp/plan.json"], check=True)
        finally:
            Path(plan_local_path).unlink(missing_ok=True)

        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "python3",
                CONTAINER_CONTROL_SCRIPT_PATH,
                "--pptx",
                "/tmp/deck.pptx",
                "--plan",
                "/tmp/plan.json",
                "--output",
                "/tmp/output/recording.mp4",
                "--frames-dir",
                "/tmp/output/frames",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RecordingError(f"control_record.py failed (exit {result.returncode}): {result.stdout}\n{result.stderr}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["docker", "cp", f"{container_name}:/tmp/output/recording.mp4", str(output_path)],
            check=True,
        )

        images_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["docker", "cp", f"{container_name}:/tmp/output/frames/.", str(images_dir)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RecordingError(f"docker command failed: {exc}") from exc
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, check=False)


def convert(
    input_path: Path,
    output_dir: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    click_delay_ms: int = CLICK_DELAY_MS,
) -> ConversionResult:
    """Normalize, compute timing, and record via docker-libreoffice-impress.

    Requires a reachable Docker daemon with the docker-libreoffice-impress image pulled:
    `docker pull registry.gitlab.com/riphixel/docker-libreoffice-impress:latest`.
    """
    extension = input_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise RecordingError(f"unsupported file extension {extension!r}; supported: {sorted(SUPPORTED_EXTENSIONS)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    pptx_path = normalize_to_pptx(input_path, output_dir / "_normalized")
    plan = compute_plan(pptx_path, click_delay_ms)

    video_path = output_dir / "recording.mp4"
    images_dir = output_dir / "images"
    record_video(pptx_path, plan, width, height, video_path, images_dir)

    image_paths = sorted(images_dir.glob("*.png"), key=_frame_sort_key)
    return ConversionResult(video_path=video_path, image_paths=image_paths)


def _frame_sort_key(path: Path) -> tuple[int, int]:
    """`frame-<slide_index>-<capture_index>.png` sorts numerically by (slide_index, capture_index)."""
    _prefix, slide_index, capture_index = path.stem.split("-")
    return int(slide_index), int(capture_index)
