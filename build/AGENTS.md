# AGENTS.md

Guidelines for agents (and humans) working on `slides2images`. See
`TIMING.md` and `IMPRESS_PROTOCOL.md` for the architecture/design this
project follows — this file is about *how* to work here, not *what* to
build.

## Project nature

Long-term project expected to go through major evolutions, not a one-off script.
Optimize for what a future contributor (human or agent) needs to safely change
this code later, not for the shortest diff today.

## Tooling

- Python + `uv` only. No user- or system-level installs (`pip install --user`,
  `apt install`, global `pipx`, etc.) — every dependency goes through
  `uv add` / `uv add --dev`, every command runs through `uv run`.
- New CLI entry points, if added, should be registered in `pyproject.toml`'s
  `[project.scripts]` — none exist yet (`run.py` is currently invoked
  directly, not as an installed console script).

## Static analysis

`mypy` and `basedpyright` are a must, not optional — both must pass clean before
code lands; they catch real type mismatches (wrong argument types, `None`/`Any`
leaking into places that assume a concrete type) that would otherwise only surface
as runtime errors. `ruff check` + `ruff format` (140-char line length, see
`[tool.ruff]` in `pyproject.toml`) is the linter/formatter. Run all three via
`uv run mypy`, `uv run basedpyright`, `uv run ruff check`/`ruff format`.
`[tool.basedpyright]` disables `reportAny` specifically (argparse.Namespace and
sqlite3.Row are `Any` in typeshed by design, not a real error signal) — every other
rule stays at basedpyright's default strictness; don't casually disable more.

## Workflow

- **CI**: validate `.gitlab-ci.yml` locally with `gitlab-ci-local` regularly, not
  just when something looks broken — catch drift before it reaches GitLab.
- **Feature list**: run `/update-features` to keep the project's feature list
  current after any change that adds, removes, or changes user-visible behavior.
- **Commit messages**: only via `/commit-message`. Don't hand-write commit messages.
- **Scope**: ask before implementing anything not explicitly requested. A bug fix
  doesn't come with a refactor, and a feature doesn't come with adjacent features,
  unless asked for or agreed on first.

## Code style

- Lean and minimalistic — no speculative abstractions, no config knobs for
  hypothetical futures, no half-finished scaffolding for features not yet built.
- Follow YAGNI principle.
- Comments explain *why*, in one line where possible: a non-obvious constraint, a
  workaround, a rejected alternative. Never narrate *what* the code does — that's
  what reading the code is for. No multi-line essays, no restating the
  investigation that led here — a comment longer than the code it annotates is a
  sign to cut it down, not a sign the reasoning was worth preserving in full.
- **Docstrings are a one-line contract**: what it does/returns, in one sentence.
  Not a second place for design rationale, alternatives considered, edge cases,
  or the history of how the code got this way — that goes in a short inline
  comment at the specific line it explains if a future editor genuinely needs
  it, or nowhere (commit messages are where investigation belongs, not code
  every future reader must scroll past). A docstring needing more than one line
  is a sign the function does too much, not a sign the extra lines earned their
  place.
- Modularity and separation of concerns are non-negotiable given the project's
  long horizon: each module owns one responsibility
  (`src/slides2images/animation_timeline.py` is the timing model,
  `src/slides2images/recorder.py` is the docker-driven recording/extraction
  pipeline, etc.). New code should extend this shape, not bypass it by
  re-implementing something a sibling module already owns.
- No duplication — if the same logic is about to appear in two places, factor it
  out first.
- Refactor when the code's current shape actively fights the change you're making,
  not preemptively. Land the refactor and the feature as distinguishable steps.

## Testing

- `pytest`, run via `uv run pytest`. Fixtures live under `tests/fixtures/` —
  prefer small, deterministic, committed fixtures (see `tests/fixtures/one slide.pptx`,
  paired with a real PowerPoint-rendered reference video of the same name) over
  generating throwaway files at test time, so test data is inspectable and
  reviewable like any other code.
- Assert against real outcomes (e.g. decoding the actual recorded `.mp4` and
  checking its duration and last-frame brightness, or a real
  `testcontainers`-driven Docker container's actual output), not mocked internals.
