# slides-to-images

[![pipeline status](https://gitlab.com/riphixel/slides-to-images/badges/main/pipeline.svg)](https://gitlab.com/riphixel/slides-to-images/-/commits/main)
[![coverage report](https://gitlab.com/riphixel/slides-to-images/badges/main/coverage.svg)](https://gitlab.com/riphixel/slides-to-images/-/commits/main)
[![Latest Release](https://gitlab.com/riphixel/slides-to-images/-/badges/release.svg)](https://gitlab.com/riphixel/slides-to-images/-/releases)


A library that converts a PowerPoint deck into an animation-playback video
plus per-slide static frames — for embedding in another codebase, not for
running standalone. Two independent capabilities:

- **Timing analysis** (`build_recording_plan`, `compute_deck_timeline`) —
  pure Python, parses the deck's OOXML `<p:timing>`/`<p:transition>` trees
  to compute per-slide/per-click pacing. No external dependencies. See
  `TIMING.md` for the full model.
- **Conversion** (`convert`) — drives a real, disposable LibreOffice Impress
  instance (via the `docker-libreoffice-impress` container image) to
  actually play the deck, recording video throughout and taking a live
  screenshot the moment each click settles. See `IMPRESS_PROTOCOL.md` for
  how that's driven end to end.

## Install

```sh
pip install slides-to-images
```

The PyPI distribution name and the importable package name differ:
`pip install slides-to-images`, but `import slides2images`.

For local development from a source checkout instead: `pip install -e .`
(or `.[test]`/`.[dev]` — see `pyproject.toml`).

`convert()` additionally needs a reachable Docker daemon, with the image
pulled: `docker pull registry.gitlab.com/riphixel/docker-libreoffice-impress:latest`.

## Usage

### Timing analysis only (no Docker required)

```python
from pathlib import Path
from slides2images import build_recording_plan

plan = build_recording_plan(Path("deck.pptx"), click_delay_ms=500)
for slide in plan:
    print(
        f"slide {slide['index']}: "
        f"{len(slide['click_gaps_ms'])} click(s), "
        f"holds {slide['post_click_hold_ms']}ms after the last one"
    )
```

`compute_deck_timeline()` returns the same data uncollapsed — every
animation node's start/end/duration, trigger, and target shape — useful for
debugging a deck's timing rather than just driving a recorder with it.

### Full conversion to video + static frames

```python
from pathlib import Path
from slides2images import convert

result = convert(Path("deck.pptx"), Path("out/"), width=1920, height=1080)

print(result.video_path)  # out/recording.mp4
for image_path in result.image_paths:  # out/images/frame-0-0.png, frame-0-1.png, frame-1-0.png, ...
    print(image_path)
```

`convert()` raises `slides2images.RecordingError` for anything that stops a
conversion short — an unsupported file extension, a deck with zero slides,
or a failure in the underlying Docker/LibreOffice pipeline.

`run.py` in the repo root is this same example as a working CLI:

```sh
python3 run.py deck.pptx   # writes deck/recording.mp4 + deck/images/*.png
```

## Supported input files

`SUPPORTED_EXTENSIONS` (also enforced by `convert()`):

- Office Open XML Presentations and Templates — `.pptx`, `.ppsx`, `.ppmx`,
  `.potx`, `.pomx` (both strict and transitional OpenXML).
- Legacy Microsoft PowerPoint 97/2000/XP/2003 — `.ppt`, `.pps`, `.ppm`,
  `.pot`, `.pom`. Converted to `.pptx` internally before anything else runs
  (`python-pptx`, which the timing model uses, only reliably opens the
  modern OOXML zip structure).

`RESOLUTIONS` is a small convenience dict of common `(width, height)` pairs
(`"vga"`, `"720p"`, `"hd"`, `"4k"`) if you'd rather not hardcode pixels.

## See also

- `TIMING.md` — how animation and transition timing is computed, including
  the corner cases found by validating against real PowerPoint-rendered
  reference videos.
- `IMPRESS_PROTOCOL.md` — how `convert()` actually drives a live Impress
  instance end to end: UNO connection, auto-advance disabling, the
  per-slide control loop, container lifecycle.
- `features.md` — end-user-visible feature list.
- `AGENTS.md` — guidelines for working on this codebase.

## Links

- PyPI: <https://pypi.org/project/slides-to-images/>
- Source, issues: <https://gitlab.com/riphixel/slides-to-images>
