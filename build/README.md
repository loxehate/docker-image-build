# docker-libreoffice-impress

A Docker image that runs LibreOffice Impress under a virtual display and
exposes it for programmatic control via UNO, so a slideshow's animations can
be played back and recorded to video. It's not a headless converter image:
`soffice` runs in real GUI mode against an Xvfb display (via
[`jlesage/baseimage-gui`](https://github.com/jlesage/docker-baseimage-gui))
so a presentation can actually be started, driven click-by-click, and
captured on screen.

This repo is a spinoff of the `docker-libreoffice-impress/` image originally
developed inside
[riphixel/slides-to-images](https://gitlab.com/riphixel/slides-to-images),
extracted so it can be built and versioned independently of that project.

## What's here

- **`Dockerfile`** — builds on `jlesage/baseimage-gui` (Alpine), installing
  the full LibreOffice suite, fonts, and the tools needed to record and
  post-process a slideshow (`ffmpeg`, `imagemagick`).
- **`rootfs/startapp.sh`** — the entrypoint the base image execs once its
  Xvfb/supervision setup is ready. Starts `soffice` in GUI (non-headless)
  mode with a UNO listener on port 2002.
- **`rootfs/opt/control_record.py`** — baked into the image, this is the
  in-container driver: it connects to the UNO socket, opens a `.pptx`, steps
  through a JSON recording plan (per-slide click gaps and hold times) while
  `ffmpeg` captures the X11 display to an `.mp4`. It also takes a live
  ImageMagick screenshot (`import -window root`) right after each click
  settles — ground truth for "what does this click look like once it's
  settled", rather than a guess at a timestamp in the recorded video.

## Building

```sh
docker build -t slides2images-libreoffice-impress:latest .
```

## Running `control_record.py`

The script is invoked inside the running container (e.g. via `docker exec`),
against a `.pptx` and a plan file already present in the container:

```sh
python3 /opt/control_record.py \
    --pptx /path/to/deck.pptx \
    --plan /path/to/plan.json \
    --output /path/to/output.mp4 \
    --frames-dir /path/to/frames
```

`plan.json` is a list of per-slide entries:

```json
[{"index": 0, "click_gaps_ms": [500, 500], "post_click_hold_ms": 1000}]
```

`--frames-dir` is created if it doesn't exist, and gets one
`frame-{slide_index}-{capture_index}.png` per settled click —
`capture_index` reset to 0 at the start of each slide, one entry per
`click_gaps_ms` value, plus one frame (`capture_index` 0) for a slide with
none at all, at the end of its hold — the same frame count and ordering
`slides2images`'s old video-based `extract_static_frames()` used to
reconstruct after the fact.

## Notes

- **`libreoffice-impress` + `libreoffice-common` alone is broken on
  Alpine** — aborts with an uncaught `com::sun::star::uno::RuntimeException`
  even on a bare `soffice --version`, no Xvfb or document involved. The full
  `libreoffice` meta-package (pulls in writer/calc/draw/math/base) fixes it;
  root cause not fully bisected, likely the shared component registry
  (`main.xcd`) referencing services from modules that aren't installed.
- **No pyuno bridge gymnastics needed.** `libreoffice-common` installs
  `uno`/`unohelper` straight into system Python's site-packages — plain
  `python3 -c "import uno"` works with no `PYTHONPATH`/`LD_LIBRARY_PATH`
  juggling, as long as the calling script runs *inside* the container (via
  `docker exec`, not from an external process).
- **Auto-advance is disabled before the presentation starts** (each draw
  page's `Change` property is set to `0`), so `control_record.py` is the sole
  driver of slide progression — nothing races a slide's own timer into an
  overshoot.
- **Recording starts only after the full-screen slideshow is ready.** The
  controller is paused immediately, activated, and checked for running,
  active, full-screen first-slide state before `ffmpeg` starts, preventing
  the visible Impress editor window from leaking into the beginning of the
  recording.
