"""Computes per-slide animation/transition timing from a .pptx's raw OOXML <p:timing> tree; see TIMING.md for the full model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree  # pyright: ignore[reportAttributeAccessIssue] -- lxml ships no stubs; etree is a real submodule at runtime  # nosemgrep: cache.semgrep.gitlab.bandit.B313.B314.B315.B316.B318.B319.B320.B405.B406.B407.B408.B409.B410 -- etree used only for QName/type-annotations here; parsing of untrusted XML happens inside python-pptx, not this file
from pptx import Presentation

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
# Office 2010+ extension namespace — where Transition's real duration lives.
P14 = "{http://schemas.microsoft.com/office/powerpoint/2010/main}"

LEAF_BEHAVIOR_TAGS = {
    "set",
    "anim",
    "animClr",
    "animEffect",
    "animMotion",
    "animRot",
    "animScale",
    "cmd",
    "audio",
    "video",
}
AFTER_NODE_TYPES = {"afterEffect", "afterGroup"}
WITH_NODE_TYPES = {"withEffect", "withGroup"}
CLICK_NODE_TYPES = {"clickEffect", "clickPar"}

CLICK_DELAY_MS = 500  # minimum wait between clicks, regardless of animation content; also the default advTm fallback


def _int_or_none(value: str | None) -> int | None:
    """ST_TLTime is either an int (ms) or the literal string "indefinite"; None in, None out."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None  # "indefinite" or any other non-numeric value


@dataclass
class TimelineNode:
    tag: str
    node_type: str | None
    start_ms: int
    end_ms: int | None
    duration_ms: int | None
    repeat_count: float
    trigger: str  # "click" | "with" | "after" | "concurrent" | "sequential"
    target_shape_id: str | None
    preset_class: str | None
    preset_id: int | None
    fill: str | None
    click_index: int | None
    id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tag": self.tag,
            "node_type": self.node_type,
            "trigger": self.trigger,
            "click_index": self.click_index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "repeat_count": self.repeat_count,
            "target_shape_id": self.target_shape_id,
            "preset_class": self.preset_class,
            "preset_id": self.preset_id,
            "fill": self.fill,
        }


@dataclass
class SlideTimeline:
    slide_index: int
    transition: dict[str, Any]
    nodes: list[TimelineNode] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    click_gaps_ms: list[int] = field(default_factory=list)  # wait after firing click i; see TIMING.md §5
    post_click_hold_ms: int = 0  # extra wait after the last click (or the whole slide) before advancing
    total_slide_ms: int = 0  # max(sum(click_gaps_ms), advance_after_time_ms) + transition_duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "transition": self.transition,
            "nodes": [n.to_dict() for n in self.nodes],
            "click_gaps_ms": self.click_gaps_ms,
            "post_click_hold_ms": self.post_click_hold_ms,
            "total_slide_ms": self.total_slide_ms,
            "warnings": self.warnings,
        }


def _get_target_shape_id(cbhvr_or_similar: etree._Element) -> str | None:
    """The shape id from <p:cBhvr><p:tgtEl><p:spTgt spid="N"/>, or None for rarer target types (audio/video/ink/bg)."""
    cbhvr = cbhvr_or_similar.find(f"{P}cBhvr")
    if cbhvr is None:
        return None
    tgt_el = cbhvr.find(f"{P}tgtEl")
    if tgt_el is None:
        return None
    sp_tgt = tgt_el.find(f"{P}spTgt")
    if sp_tgt is not None:
        spid: str | None = sp_tgt.get("spid")
        return spid
    return None


def _own_cTn(el: etree._Element) -> etree._Element | None:
    """This element's own <p:cTn>: a direct child for par/seq, nested under cBhvr for a leaf behavior, itself for a cTn."""
    tag = etree.QName(el).localname
    if tag == "cTn":
        return el
    if tag in ("par", "seq", "excl"):
        return el.find(f"{P}cTn")
    if tag in LEAF_BEHAVIOR_TAGS:
        cbhvr = el.find(f"{P}cBhvr")
        return cbhvr.find(f"{P}cTn") if cbhvr is not None else None
    return None


def _resolve_start_ms(
    cTn: etree._Element,
    anchor_start_ms: int,
    prev_sibling_end_ms: int | None,
    warnings: list[str],
) -> tuple[int, str]:
    """Returns (start_ms, trigger_label); priority order documented in TIMING.md §2."""
    node_type = cTn.get("nodeType")

    st_cond_lst = cTn.find(f"{P}stCondLst")
    if st_cond_lst is not None:
        conds = st_cond_lst.findall(f"{P}cond")
        if len(conds) > 1:
            warnings.append(
                f"cTn id={cTn.get('id')}: stCondLst has {len(conds)} conditions, "
                "only using the first (multi-condition start sync not modeled)"
            )
        if conds:
            cond = conds[0]
            delay_raw = cond.get("delay")
            delay_ms = _int_or_none(delay_raw)
            evt = cond.get("evt")
            rtn = cond.find(f"{P}rtn")
            if rtn is not None:
                warnings.append(
                    f"cTn id={cTn.get('id')}: start condition syncs to another time node (rtn) — not modeled, treated as anchor-relative"
                )
            if delay_ms is not None:
                return anchor_start_ms + delay_ms, "timed"  # always anchor-relative, regardless of nodeType
            # "indefinite"/malformed delay: no fixed timer, modeled as happening at the anchor (which IS the click here).
            if evt not in (None, "onClick", "onNext"):
                warnings.append(
                    f"cTn id={cTn.get('id')}: indefinite delay with evt={evt!r} "
                    "(not onClick/onNext) — treated as anchor-relative, may be wrong"
                )

    if node_type in AFTER_NODE_TYPES:
        if prev_sibling_end_ms is None:
            warnings.append(
                f"cTn id={cTn.get('id')}: nodeType={node_type} but no preceding sibling end time available — falling back to anchor start"
            )
            return anchor_start_ms, "after"
        return prev_sibling_end_ms, "after"

    if node_type in WITH_NODE_TYPES:
        return anchor_start_ms, "with"

    if node_type in CLICK_NODE_TYPES:
        return anchor_start_ms, "click"

    return anchor_start_ms, "concurrent"  # no nodeType, no numeric delay: concurrent-by-default


def _resolve_span_ms(cTn: etree._Element, warnings: list[str]) -> tuple[int | None, int | None, float]:
    """Returns the raw, unmultiplied (own_dur_ms, repeat_dur_ms, repeat_multiplier); caller applies the multiplier (see _walk)."""
    dur_ms = _int_or_none(cTn.get("dur"))
    repeat_dur_ms = _int_or_none(cTn.get("repeatDur"))

    repeat_count_raw = cTn.get("repeatCount")
    if repeat_count_raw is None:
        repeat_multiplier = 1.0
    else:
        raw = _int_or_none(repeat_count_raw)
        if raw is None:
            warnings.append(f"cTn id={cTn.get('id')}: unparseable repeatCount={repeat_count_raw!r}, assuming 1x")
            repeat_multiplier = 1.0
        else:
            repeat_multiplier = raw / 1000.0  # NOT /100000 (ST_PositiveFixedPercentage) — see TIMING.md §3.2

    return dur_ms, repeat_dur_ms, repeat_multiplier


def _walk(
    el: etree._Element,
    anchor_start_ms: int,
    prev_sibling_end_ms: int | None,
    click_index: int | None,
    out: list[TimelineNode],
    warnings: list[str],
) -> int | None:
    """Walks one node and its subtree, appending a TimelineNode per leaf behavior; returns this node's own end_ms."""
    tag = etree.QName(el).localname
    cTn = _own_cTn(el)
    if cTn is None:
        warnings.append(f"{tag}: no cTn found, skipping subtree")
        return anchor_start_ms

    start_ms, trigger = _resolve_start_ms(cTn, anchor_start_ms, prev_sibling_end_ms, warnings)
    node_click_index = click_index
    if trigger == "click" and click_index is None:
        warnings.append(f"cTn id={cTn.get('id')}: click-triggered node with no click_index assigned")

    own_dur_ms, repeat_dur_ms, repeat_multiplier = _resolve_span_ms(cTn, warnings)

    child_tn_lst = cTn.find(f"{P}childTnLst")
    children_end_ms: int | None = None
    if child_tn_lst is not None and len(child_tn_lst):
        par_children = child_tn_lst.findall(f"{P}par")
        seq_children = child_tn_lst.findall(f"{P}seq")
        if par_children:
            ends = [_walk(child, start_ms, None, node_click_index, out, warnings) for child in par_children]
            real_ends = [e for e in ends if e is not None]
            children_end_ms = max(real_ends) if real_ends else None
        elif seq_children:
            running_end = start_ms
            for child in seq_children:
                e = _walk(child, start_ms, running_end, node_click_index, out, warnings)
                running_end = e if e is not None else running_end
            children_end_ms = running_end
        else:
            # Bare list of behavior leaves; each resolves its own timing via the same rules.
            running_end = start_ms
            leaf_ends: list[int] = []
            for child in child_tn_lst:
                child_tag = etree.QName(child).localname
                if child_tag not in LEAF_BEHAVIOR_TAGS:
                    warnings.append(f"childTnLst: unrecognized child <{child_tag}>, skipping")
                    continue
                e = _walk(child, start_ms, running_end, node_click_index, out, warnings)
                if e is not None:
                    running_end = e
                    leaf_ends.append(e)
            children_end_ms = max(leaf_ends) if leaf_ends else None

    if repeat_dur_ms is not None:
        # repeatDur overrides the repeatCount*dur product entirely, per spec.
        end_ms: int | None = start_ms + repeat_dur_ms
        own_span_ms: int | None = repeat_dur_ms
    else:
        # Intrinsic (un-repeated) span: own `dur` if present, else the children's span; repeatCount multiplies
        # either way, including a wrapper cTn with no own `dur` — see TIMING.md §3.2.
        if own_dur_ms is not None:
            intrinsic_span_ms: int | None = own_dur_ms
        elif children_end_ms is not None:
            intrinsic_span_ms = children_end_ms - start_ms
        else:
            intrinsic_span_ms = None

        if intrinsic_span_ms is not None:
            own_span_ms = round(intrinsic_span_ms * repeat_multiplier)
            end_ms = start_ms + own_span_ms
        else:
            own_span_ms = None
            end_ms = None  # open-ended, no own dur and no children span

    if tag in LEAF_BEHAVIOR_TAGS:
        out.append(
            TimelineNode(
                tag=tag,
                node_type=cTn.get("nodeType"),
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=own_span_ms,
                repeat_count=repeat_multiplier,
                trigger=trigger,
                target_shape_id=_get_target_shape_id(el),
                preset_class=cTn.get("presetClass"),
                preset_id=_int_or_none(cTn.get("presetID")),
                fill=cTn.get("fill"),
                click_index=node_click_index,
                id=cTn.get("id"),
            )
        )

    return end_ms


def _extract_transition(slide_el: etree._Element) -> dict[str, Any]:
    # Recursive search, not a direct-child find(): real decks often wrap <p:transition> in
    # <mc:AlternateContent>, which a direct-child lookup would miss entirely — see TIMING.md §4.1.
    transition = slide_el.find(f".//{P}transition")
    if transition is None:
        return {
            "present": False,
            "advance_on_click": True,  # spec default when <p:transition> is absent entirely
            "advance_after_time_ms": None,
            "duration_ms": None,
            "speed": None,
        }
    adv_click_raw = transition.get("advClick")
    advance_on_click = True if adv_click_raw is None else adv_click_raw == "1" or adv_click_raw.lower() == "true"
    return {
        "present": True,
        "advance_on_click": advance_on_click,
        "advance_after_time_ms": _int_or_none(transition.get("advTm")),
        "duration_ms": _int_or_none(transition.get(f"{P14}dur")),  # namespaced p14:dur, not a bare `dur` — see TIMING.md §4
        "speed": transition.get("spd"),
    }


def compute_slide_timeline(
    slide_index: int,
    slide_el: etree._Element,
    click_delay_ms: int = CLICK_DELAY_MS,
) -> SlideTimeline:
    timeline = SlideTimeline(
        slide_index=slide_index,
        transition=_extract_transition(slide_el),
    )

    timing = slide_el.find(f"{P}timing")
    main_seq_children = None
    if timing is not None:
        tn_lst = timing.find(f"{P}tnLst")
        top_par = tn_lst.find(f"{P}par") if tn_lst is not None else None
        tm_root_cTn = top_par.find(f"{P}cTn") if top_par is not None else None
        if tm_root_cTn is not None and tm_root_cTn.get("nodeType") != "tmRoot":
            timeline.warnings.append("top-level par's cTn is not nodeType=tmRoot; proceeding anyway")
        child_tn_lst = tm_root_cTn.find(f"{P}childTnLst") if tm_root_cTn is not None else None
        main_seq = child_tn_lst.find(f"{P}seq") if child_tn_lst is not None else None
        if child_tn_lst is not None and main_seq is None:
            timeline.warnings.append("no mainSeq <p:seq> found under tmRoot")
        main_seq_cTn = main_seq.find(f"{P}cTn") if main_seq is not None else None
        main_seq_children = main_seq_cTn.find(f"{P}childTnLst") if main_seq_cTn is not None else None

    click_cursor_ms = 0
    click_index = 0
    click_gaps_ms: list[int] = []
    if main_seq_children is not None:
        for chain_par in main_seq_children.findall(f"{P}par"):
            chain_start_ms = click_cursor_ms
            end_ms = _walk(chain_par, click_cursor_ms, None, click_index, timeline.nodes, timeline.warnings)
            if end_ms is not None:
                chain_span_ms = end_ms - chain_start_ms
                click_cursor_ms = max(click_cursor_ms, end_ms)
                gap_ms = max(click_delay_ms, chain_span_ms)  # see TIMING.md §5
            else:
                timeline.warnings.append(
                    f"click chain {click_index} is open-ended (indefinite duration); "
                    "no natural span to pace on, falling back to click_delay_ms"
                )
                gap_ms = click_delay_ms
            click_gaps_ms.append(gap_ms)
            click_index += 1

    timeline.click_gaps_ms = click_gaps_ms

    # transition_duration_ms only stacks on an EXPLICITLY authored advTm, not the CLICK_DELAY_MS fallback — see TIMING.md §4.2.
    raw_advance_after_time_ms = timeline.transition["advance_after_time_ms"]
    if raw_advance_after_time_ms is None:
        advance_after_time_ms = click_delay_ms
        transition_duration_ms = 0
    else:
        advance_after_time_ms = raw_advance_after_time_ms
        transition_duration_ms = timeline.transition["duration_ms"] or 0

    sum_click_gaps_ms = sum(click_gaps_ms)
    timeline.total_slide_ms = max(sum_click_gaps_ms, advance_after_time_ms) + transition_duration_ms
    timeline.post_click_hold_ms = timeline.total_slide_ms - sum_click_gaps_ms

    return timeline


def compute_deck_timeline(pptx_path: Path, click_delay_ms: int = CLICK_DELAY_MS) -> list[dict[str, Any]]:
    prs = Presentation(str(pptx_path))  # python-pptx's stub is str-only; Path works at runtime but this satisfies the type checker
    return [
        compute_slide_timeline(i, slide._element, click_delay_ms).to_dict()  # pyright: ignore[reportPrivateUsage] -- python-pptx has no public accessor for the raw XML element
        for i, slide in enumerate(prs.slides)
        if slide._element.get("show") != "0"  # pyright: ignore[reportPrivateUsage] -- hidden slides are skipped by Impress's own "next slide" during playback, so no plan entry must be generated for them either
    ]


def build_recording_plan(pptx_path: Path, click_delay_ms: int = CLICK_DELAY_MS) -> list[dict[str, Any]]:
    """Per-slide click-pacing schedule for control_record.py: trims compute_deck_timeline()'s full output down to just index/click_gaps_ms/post_click_hold_ms."""
    slides = compute_deck_timeline(pptx_path, click_delay_ms)
    return [
        {
            "index": s["slide_index"],
            "click_gaps_ms": s["click_gaps_ms"],
            "post_click_hold_ms": s["post_click_hold_ms"],
        }
        for s in slides
    ]
