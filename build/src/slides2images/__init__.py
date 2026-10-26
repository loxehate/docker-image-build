"""Converts a PowerPoint deck into an animation-playback video plus per-slide static frames.

See README.md for usage; TIMING.md and IMPRESS_PROTOCOL.md for how the timing model and the
recording pipeline work internally.
"""

from __future__ import annotations

from .animation_timeline import CLICK_DELAY_MS, build_recording_plan, compute_deck_timeline
from .recorder import (
    RESOLUTIONS,
    SUPPORTED_EXTENSIONS,
    ConversionResult,
    RecordingError,
    convert,
)

__all__ = [
    "CLICK_DELAY_MS",
    "RESOLUTIONS",
    "SUPPORTED_EXTENSIONS",
    "ConversionResult",
    "RecordingError",
    "build_recording_plan",
    "compute_deck_timeline",
    "convert",
]
