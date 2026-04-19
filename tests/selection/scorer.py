"""Closeness scorer for workflow-selection measurement.

The scorer rates how close two workflow descriptions are on a 0.0-1.0 axis
by asking a judge model (via the cross-model panel utility) to emit a single
float. To keep the axis stable across models, each prompt interleaves a set
of hand-authored calibration anchors whose operator-assigned scores define
the fixed points of the closeness scale.

The panel entry point is passed in as ``panel_query_fn`` rather than imported
directly so tests can inject a ``unittest.mock.create_autospec`` mock built
from the real ``megalos_panel.panel.panel_query`` signature (per D016's
mock-from-real-types rule). Default resolves at call time to the real
panel entry point; there is no hidden module-level import.

Prompt template is pinned behind ``PROMPT_TEMPLATE_VERSION`` so a downstream
run record can identify which prompt shape produced a score — reproduction
across template revisions demands the version string.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import variance
from typing import Any

from megalos_panel import PanelRequest, PanelResult, panel_query


# --- Prompt template -------------------------------------------------------

PROMPT_TEMPLATE_VERSION = "scorer-v1"

JUDGE_PROMPT = """You rate the semantic closeness between two workflow descriptions on a 0.0-1.0 scale.

0.0 means the workflows are unrelated (different categories, different outputs, different audiences).
1.0 means the descriptions are effectively interchangeable.

Calibration anchors (use these as fixed points for your scale):
{anchor_block}
Pair to score:
Description A: {desc_a}
Description B: {desc_b}

Return only the score as a float between 0.0 and 1.0."""


def _format_anchor_block(anchors: list[dict]) -> str:
    """Render the anchor list as a prompt-ready block.

    Each anchor is laid out with its two descriptions and its
    operator-assigned closeness. Kept deterministic (caller-provided
    order) so tests can assert exact substrings.
    """

    lines: list[str] = []
    for anchor in anchors:
        desc_a = anchor["description_A"]
        desc_b = anchor["description_B"]
        score = anchor["operator_assigned_closeness"]
        lines.append(f"- Description A: {desc_a}")
        lines.append(f"  Description B: {desc_b}")
        lines.append(f"  Closeness: {score}")
    return "\n".join(lines) + ("\n" if lines else "")


def _build_prompt(desc_a: str, desc_b: str, anchors: list[dict]) -> str:
    return JUDGE_PROMPT.format(
        anchor_block=_format_anchor_block(anchors),
        desc_a=desc_a,
        desc_b=desc_b,
    )


def _anchors_used(anchors: list[dict]) -> list[str]:
    return [a["pair_id"] for a in anchors]


def _parse_score(raw: str) -> float | None:
    """Parse a 0.0-1.0 float from a judge response.

    Judges occasionally decorate the number with whitespace, a trailing
    period, or a leading label ("Score: 0.65"). We tolerate the common
    shapes: strip whitespace, keep the first float-like token, clamp the
    value to [0.0, 1.0] only if it parses. Anything outside that range
    or unparseable returns None so the caller surfaces it as an error.
    """

    text = raw.strip()
    if not text:
        return None
    # Find the first numeric run (including decimal point, optional sign).
    start = None
    end = None
    for i, ch in enumerate(text):
        if ch.isdigit() or ch in "+-.":
            if start is None:
                start = i
            end = i + 1
        elif start is not None:
            break
    if start is None or end is None:
        return None
    token = text[start:end]
    try:
        value = float(token)
    except ValueError:
        return None
    if value < 0.0 or value > 1.0:
        return None
    return value


# --- Public API ------------------------------------------------------------


def score_pair_closeness(
    description_A: str,
    description_B: str,
    *,
    anchors: list[dict],
    judge_model: str,
    panel_query_fn: Callable[..., Any] = panel_query,
) -> dict:
    """Score a single pair's closeness via one panel request.

    Returns a dict with ``score`` (float or None on error), ``raw_response``
    (the judge's text), ``anchors_used`` (pair_ids of the anchors passed in),
    ``judge_model``, ``prompt_template_version``, and ``error`` (str or None).
    """

    prompt = _build_prompt(description_A, description_B, anchors)
    request = PanelRequest(prompt=prompt, model=judge_model)
    try:
        results: dict[str, PanelResult] = panel_query_fn([request])
    except Exception as exc:  # PanelProviderError or any provider-side fault
        return {
            "score": None,
            "raw_response": "",
            "anchors_used": _anchors_used(anchors),
            "judge_model": judge_model,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "error": str(exc),
        }

    result = results[request.request_id]
    if result.error is not None:
        return {
            "score": None,
            "raw_response": result.raw_response,
            "anchors_used": _anchors_used(anchors),
            "judge_model": judge_model,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "error": result.error,
        }

    score = _parse_score(result.selection)
    error = None if score is not None else f"unparseable score: {result.selection!r}"
    return {
        "score": score,
        "raw_response": result.raw_response,
        "anchors_used": _anchors_used(anchors),
        "judge_model": judge_model,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "error": error,
    }


def score_pairs_batch(
    pairs: list[tuple[str, str]],
    anchors: list[dict],
    judge_model: str,
    panel_query_fn: Callable[..., Any] = panel_query,
) -> list[dict]:
    """Score many pairs via a single panel_query call.

    Builds one PanelRequest per input pair and dispatches the whole list in
    a single ``panel_query_fn`` invocation — this is the D016 list-of-requests
    shape, and consolidating the call keeps rate-limit accounting coherent.
    Results are mapped back to pairs by request_id so the returned list
    preserves input order.
    """

    if not pairs:
        return []

    requests = [
        PanelRequest(
            prompt=_build_prompt(desc_a, desc_b, anchors),
            model=judge_model,
        )
        for desc_a, desc_b in pairs
    ]

    try:
        results: dict[str, PanelResult] = panel_query_fn(requests)
    except Exception as exc:
        return [
            {
                "score": None,
                "raw_response": "",
                "anchors_used": _anchors_used(anchors),
                "judge_model": judge_model,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                "error": str(exc),
            }
            for _ in pairs
        ]

    out: list[dict] = []
    for request in requests:
        result = results[request.request_id]
        if result.error is not None:
            out.append(
                {
                    "score": None,
                    "raw_response": result.raw_response,
                    "anchors_used": _anchors_used(anchors),
                    "judge_model": judge_model,
                    "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                    "error": result.error,
                }
            )
            continue
        score = _parse_score(result.selection)
        error = (
            None if score is not None else f"unparseable score: {result.selection!r}"
        )
        out.append(
            {
                "score": score,
                "raw_response": result.raw_response,
                "anchors_used": _anchors_used(anchors),
                "judge_model": judge_model,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                "error": error,
            }
        )
    return out


def anchor_sensitivity_analysis(
    pairs: list[tuple[str, str]],
    anchor_pool: list[dict],
    judge_model: str,
    panel_query_fn: Callable[..., Any] = panel_query,
    anchor_counts: list[int] | None = None,
) -> dict:
    """Measure how score variance changes as the anchor count varies.

    For each requested anchor count, take that many anchors from the front
    of ``anchor_pool`` (deterministic — no random sampling, so reruns are
    reproducible), run ``score_pairs_batch`` against all ``pairs``, and
    record the variance of the resulting scores. Counts that exceed the
    pool size are skipped silently; counts < 2 are rejected up front.

    Returns ``{"per_count": {count: {"scores": [...], "variance": float|None},
    ...}, "anchor_counts": [...]}``. Variance is ``None`` when fewer than two
    valid scores landed (statistics.variance requires n >= 2).

    The intent is to support D018's anchor-count expansion policy: if
    variance drops as anchor count grows, the calibration is under-anchored
    and anchors.yaml should expand 2-3 -> 5-7.
    """

    if anchor_counts is None:
        anchor_counts = [2, 3, 4, 5, 6, 7]
    for count in anchor_counts:
        if count < 2:
            raise ValueError("anchor_counts entries must be >= 2")

    per_count: dict[int, dict] = {}
    evaluated: list[int] = []
    for count in anchor_counts:
        if count > len(anchor_pool):
            continue
        anchors = anchor_pool[:count]
        results = score_pairs_batch(
            pairs,
            anchors,
            judge_model,
            panel_query_fn=panel_query_fn,
        )
        scores = [r["score"] for r in results if r["score"] is not None]
        per_count[count] = {
            "scores": scores,
            "variance": variance(scores) if len(scores) >= 2 else None,
        }
        evaluated.append(count)

    return {
        "per_count": per_count,
        "anchor_counts": evaluated,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
    }
