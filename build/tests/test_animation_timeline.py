"""Unit tests for the timing model — see TIMING.md for the narrative version of each rule tested here.

Builds minimal synthetic <p:sld> XML per test (fast, no Docker/LibreOffice needed) to isolate one
rule at a time, plus a corpus-wide regression test locking in the current model's numbers against
the real fixture decks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue] -- lxml ships no stubs; etree is a real submodule at runtime

from slides2images.animation_timeline import SlideTimeline, compute_deck_timeline, compute_slide_timeline

NSMAP = (
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


def _slide(inner: str) -> etree._Element:
    return etree.fromstring(f"<p:sld {NSMAP}><p:cSld/>{inner}</p:sld>")


def _timeline(inner: str, click_delay_ms: int = 500) -> SlideTimeline:
    return compute_slide_timeline(0, _slide(inner), click_delay_ms)


def test_no_timing_no_transition_defaults_to_click_delay() -> None:
    timeline = _timeline("", click_delay_ms=500)

    assert timeline.transition == {
        "present": False,
        "advance_on_click": True,
        "advance_after_time_ms": None,
        "duration_ms": None,
        "speed": None,
    }
    assert timeline.click_gaps_ms == []
    assert timeline.total_slide_ms == 500
    assert timeline.post_click_hold_ms == 500


def test_repeat_count_scales_children_derived_span_on_dur_less_wrapper() -> None:
    """TIMING.md §3.2: repeatCount="5000" (=5x, /1000 not /100000) on a cTn with no own `dur`
    must still multiply its *children's* span (2000ms animEffect) — an earlier bug silently
    dropped the multiplier whenever it lived on a wrapper instead of a `dur`-bearing leaf.
    """
    inner = """
    <p:timing>
      <p:tnLst>
        <p:par>
          <p:cTn nodeType="tmRoot">
            <p:childTnLst>
              <p:seq nodeType="mainSeq">
                <p:cTn>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="5" nodeType="clickEffect" repeatCount="5000">
                        <p:stCondLst><p:cond delay="500"/></p:stCondLst>
                        <p:childTnLst>
                          <p:set><p:cBhvr><p:cTn id="6" dur="1"/></p:cBhvr></p:set>
                          <p:animEffect><p:cBhvr><p:cTn id="7" dur="2000"/></p:cBhvr></p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>
    """
    timeline = _timeline(inner, click_delay_ms=500)

    # chain start (500ms delay) + (2000ms children span * 5x repeat) = 10500ms.
    assert timeline.click_gaps_ms == [10500]
    assert timeline.total_slide_ms == 10500
    assert timeline.post_click_hold_ms == 0
    # the leaf nodes themselves report their own (un-multiplied) span, per TIMING.md §3.3.
    durations = {n.tag: n.duration_ms for n in timeline.nodes}
    assert durations == {"set": 1, "animEffect": 2000}


def test_click_chain_gap_is_max_of_click_delay_and_own_span() -> None:
    """TIMING.md §5: every click's gap is max(CLICK_DELAY_MS, chain's own span) — uniformly,
    regardless of whether the chain has any observable animation. A short chain (instant or
    observable) clamps to the floor; a chain whose own span already exceeds it isn't touched.
    """
    inner = """
    <p:timing>
      <p:tnLst>
        <p:par>
          <p:cTn nodeType="tmRoot">
            <p:childTnLst>
              <p:seq nodeType="mainSeq">
                <p:cTn>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn nodeType="clickEffect">
                        <p:childTnLst>
                          <p:set><p:cBhvr><p:cTn dur="1"/></p:cBhvr></p:set>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                    <p:par>
                      <p:cTn nodeType="clickEffect">
                        <p:childTnLst>
                          <p:animEffect><p:cBhvr><p:cTn dur="200"/></p:cBhvr></p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                    <p:par>
                      <p:cTn nodeType="clickEffect">
                        <p:childTnLst>
                          <p:animEffect><p:cBhvr><p:cTn dur="2000"/></p:cBhvr></p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>
    """
    timeline = _timeline(inner, click_delay_ms=500)

    # click 0 (instant, 1ms) and click 1 (observable, 200ms) both clamp to the 500ms floor;
    # click 2 (observable, 2000ms) already exceeds it, so its own span governs.
    assert timeline.click_gaps_ms == [500, 500, 2000]


def test_transition_wrapped_in_mc_alternate_content_is_found() -> None:
    """TIMING.md §4.1: a direct-child find() misses <p:transition> nested under mc:Choice."""
    inner = """
    <mc:AlternateContent>
      <mc:Choice Requires="p14">
        <p:transition p14:dur="2000" advTm="1000"/>
      </mc:Choice>
      <mc:Fallback>
        <p:transition advTm="1000"/>
      </mc:Fallback>
    </mc:AlternateContent>
    """
    timeline = _timeline(inner, click_delay_ms=500)

    assert timeline.transition["present"] is True
    assert timeline.transition["advance_after_time_ms"] == 1000
    assert timeline.transition["duration_ms"] == 2000
    # explicit advTm -> transition duration stacks on top (TIMING.md §4.2).
    assert timeline.total_slide_ms == 3000


def test_transition_duration_only_stacks_on_explicit_advtm() -> None:
    """TIMING.md §4.2: p14:dur is NOT added on top of the CLICK_DELAY_MS fallback — only
    on top of an explicitly authored advTm.
    """
    fallback = _timeline('<p:transition p14:dur="2000"/>', click_delay_ms=500)
    assert fallback.transition["advance_after_time_ms"] is None
    assert fallback.total_slide_ms == 500  # not 2500

    explicit = _timeline('<p:transition p14:dur="2000" advTm="1000"/>', click_delay_ms=500)
    assert explicit.total_slide_ms == 3000  # 1000 + 2000


def test_open_ended_duration_warns_and_falls_back_to_click_delay() -> None:
    """TIMING.md §6: dur="indefinite" with no repeatDur and no children span is genuinely
    unknowable — recorded as a warning, not silently guessed at.
    """
    inner = """
    <p:timing>
      <p:tnLst>
        <p:par>
          <p:cTn nodeType="tmRoot">
            <p:childTnLst>
              <p:seq nodeType="mainSeq">
                <p:cTn>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn nodeType="clickEffect">
                        <p:childTnLst>
                          <p:animEffect><p:cBhvr><p:cTn dur="indefinite"/></p:cBhvr></p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>
    """
    timeline = _timeline(inner, click_delay_ms=500)

    assert timeline.click_gaps_ms == [500]
    assert any("open-ended" in w for w in timeline.warnings)
    node = timeline.nodes[0]
    assert node.end_ms is None
    assert node.duration_ms is None


def test_after_effect_chains_to_previous_sibling_end() -> None:
    """TIMING.md §2 rule 2: nodeType=afterEffect with no numeric delay starts when the
    *preceding sibling* ends, not concurrently with the anchor.
    """
    inner = """
    <p:timing>
      <p:tnLst>
        <p:par>
          <p:cTn nodeType="tmRoot">
            <p:childTnLst>
              <p:seq nodeType="mainSeq">
                <p:cTn>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn nodeType="clickEffect">
                        <p:childTnLst>
                          <p:animEffect><p:cBhvr><p:cTn dur="1000"/></p:cBhvr></p:animEffect>
                          <p:animEffect><p:cBhvr><p:cTn nodeType="afterEffect" dur="500"/></p:cBhvr></p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
    </p:timing>
    """
    timeline = _timeline(inner, click_delay_ms=500)

    first, second = timeline.nodes
    assert (first.start_ms, first.end_ms) == (0, 1000)
    assert (second.start_ms, second.end_ms) == (1000, 1500)  # chained off the first's end, not 0
    assert timeline.click_gaps_ms == [1500]


def test_no_slides_returns_empty_deck_timeline() -> None:
    assert compute_deck_timeline(FIXTURES_DIR / "no slide.pptx") == []


def test_hidden_slides_are_excluded_from_deck_timeline() -> None:
    """A hidden slide (<p:sld show="0">) is never actually shown during playback — LibreOffice
    Impress's "next slide" skips straight past it. Including a plan entry for it anyway causes
    that click to land on (and capture) the *following visible* slide instead, mislabeling the
    frame as the hidden slide's own content (see bug.md).

    "hidden slides.pptx" is 4 slides: 0 visible, 1 hidden, 2 hidden, 3 visible.
    """
    slides = compute_deck_timeline(FIXTURES_DIR / "hidden slides.pptx", click_delay_ms=500)
    indices = [s["slide_index"] for s in slides]

    assert indices == [0, 3]


# Current model's total_slide_ms figures (click_delay_ms=500), summed per deck — a corpus-wide
# regression guard: any future change to the timing model that shifts one of these is exactly the
# kind of silent drift the reference-video validation this replaced was meant to catch. These no
# longer match TIMING.md's old PowerPoint-reference-video table (CLICK_DELAY_MS intentionally
# diverges from PowerPoint's own slide_duration default — see TIMING.md §5).
EXPECTED_TOTAL_MS = {
    "animation looping until end slide.pptx": 500,
    "one slide.pptx": 500,
    "slide animation 01 - delay before animation.pptx": 6510,
    "slide animation 01 - repeat.pptx": 10510,
    "slide animation 01.pptx": 11770,
    "slide animation 02.pptx": 6750,
    "slide animation 03.pptx": 4000,
    "slide animation animateColor.pptx": 2800,
    "slide animation animateEffect.pptx": 2000,
    "slide animation animateMotion.pptx": 2250,
    "slide animation animateRotation.pptx": 2000,
    "slide animation animateScale.pptx": 2000,
    "slide with video.pptx": 10032,
    "slides animations.pptx": 18520,
    "slides morph.pptx": 4600,
    "slides no transition no animation.pptx": 2820,
}


@pytest.mark.parametrize("fixture_name", sorted(EXPECTED_TOTAL_MS))
def test_fixture_corpus_total_slide_ms_matches_current_model(fixture_name: str) -> None:
    slides = compute_deck_timeline(FIXTURES_DIR / fixture_name, click_delay_ms=500)
    total_ms = sum(s["total_slide_ms"] for s in slides)
    assert total_ms == EXPECTED_TOTAL_MS[fixture_name]
