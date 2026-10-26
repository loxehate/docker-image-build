"""Unit tests for the parts of the conversion pipeline that don't need Docker/LibreOffice:
extension validation and plan-computation error wrapping. Frame/video correctness now requires a
real container run (control_record.py captures frames live, no host-side reconstruction left to
unit test) — see tests/test_video_recording.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from slides2images.recorder import RecordingError, compute_plan, convert

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


def test_convert_rejects_unsupported_extension(tmp_path: Path) -> None:
    bogus = tmp_path / "deck.txt"
    bogus.write_text("not a presentation")

    with pytest.raises(RecordingError, match="unsupported file extension"):
        convert(bogus, tmp_path / "out")


def test_convert_raises_for_deck_with_no_slides(tmp_path: Path) -> None:
    """Exercises the real normalize -> plan -> record_video wiring; record_video's no-slides
    check fires before any Docker container is started, so this needs no Docker daemon.
    """
    with pytest.raises(RecordingError, match="no slides"):
        convert(FIXTURES_DIR / "no slide.pptx", tmp_path / "out")


def test_compute_plan_wraps_parse_failures_as_recording_error(tmp_path: Path) -> None:
    bogus = tmp_path / "deck.pptx"
    bogus.write_bytes(b"not a real pptx zip")

    with pytest.raises(RecordingError, match="could not compute animation timing"):
        compute_plan(bogus, click_delay_ms=500)
