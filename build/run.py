#!/usr/bin/env python3
"""CLI: convert a .pptx to an animation-playback video + per-slide static frames.

Requires the docker-libreoffice-impress image (`docker pull
registry.gitlab.com/riphixel/docker-libreoffice-impress:latest`) and the
slides2images package installed on the host (`pip install -e .` from the
repo root).

Usage:
    python3 run.py deck.pptx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slides2images import CLICK_DELAY_MS, RecordingError, convert


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--click-delay-ms", type=int, default=CLICK_DELAY_MS)
    args = parser.parse_args()

    if not args.pptx.exists():
        sys.exit(f"Not found: {args.pptx}")

    output_dir = args.pptx.parent / args.pptx.stem
    try:
        result = convert(args.pptx, output_dir, width=args.width, height=args.height, click_delay_ms=args.click_delay_ms)
    except RecordingError as exc:
        sys.exit(str(exc))

    print(f"video:  {result.video_path}")
    print(f"images: {len(result.image_paths)} frame(s) in {output_dir / 'images'}")


if __name__ == "__main__":
    main()
