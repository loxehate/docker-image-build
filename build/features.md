# slides2images — features

A library, for embedding in another codebase: converts a PowerPoint deck
into a full animation-playback video, plus one per-slide static frame per
settled click, for downstream VLM analysis or general use.

## Supported input files

- Office Open XML Presentations and Templates — `.pptx`, `.ppsx`, `.ppmx`,
  `.potx`, `.pomx` (both strict and transitional OpenXML).
- Legacy Microsoft PowerPoint 97/2000/XP/2003 — `.ppt`, `.pps`, `.ppm`,
  `.pot`, `.pom`.

## What you get back

- **Animation-playback video** — a single video of the whole deck played
  back the way PowerPoint would play it: entrance/emphasis/exit animations
  triggered in order, slide transitions rendered, and each click's own
  animation given its full natural playback time (see `TIMING.md`).
- **`click_delay_ms`** — the minimum wait between two clicks, used whenever
  a click's own animation (if any) is shorter than this (default 500ms).
  This is a machine-pacing floor, not PowerPoint's human-reading-time
  default — see `TIMING.md` §5.
- **Static frames** — one PNG per settled (non-animating) moment, captured
  live the instant it happens (a real screenshot, not reconstructed from
  the video afterward): every point where nothing is currently animating,
  including intermediate states within a slide that reveals its content
  progressively across several clicks, not just one frame per slide. Named
  `frame-<slide_index>-<capture_index>.png`, so which slide and which click
  produced a frame is always in the filename.

## Library API

A single synchronous call per conversion — no upload, no job queue, no
polling; the caller owns scheduling/concurrency:

- **`convert(input_path, output_dir, width=1920, height=1080,
  click_delay_ms=500)`** — runs the whole normalize → compute-plan → record
  (video + live per-click screenshots) pipeline and returns a
  `ConversionResult` (`video_path`, `image_paths`). Raises `RecordingError`
  for an unsupported extension, a deck with zero slides, or a pipeline failure.
- **`build_recording_plan(pptx_path, click_delay_ms=500)`** — just
  the timing computation, no Docker/LibreOffice involved; useful standalone
  for inspecting a deck's pacing.
- Full usage examples: `README.md`.

## See also

- `TIMING.md` — how animation and transition timing is computed.
- `IMPRESS_PROTOCOL.md` — how the recording is actually driven, end to
  end, from `convert()` to LibreOffice Impress.
