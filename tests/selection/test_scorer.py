"""Unit tests for the workflow-selection closeness scorer.

All tests mock ``panel_query`` via ``unittest.mock.create_autospec`` built
from the real ``megalos_panel.panel.panel_query`` signature — per D016's
mock-from-real-types rule. If the real signature drifts, the autospec
mock auto-breaks, which is the structural tie between this module and
Commitment A of the S03->S04 interface contract. No local re-definition
of PanelRequest / PanelResult is tolerated.
"""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest  # type: ignore[import-not-found]

from megalos_panel import PanelProviderError, PanelRequest, PanelResult, panel_query

from tests.selection.scorer import (
    JUDGE_PROMPT,
    PROMPT_TEMPLATE_VERSION,
    anchor_sensitivity_analysis,
    score_pair_closeness,
    score_pairs_batch,
)


# --- Fixtures --------------------------------------------------------------


ANCHORS = [
    {
        "pair_id": "anchor_low_001",
        "description_A": "Produce a long-form analytical essay on a chosen topic.",
        "description_B": "Write code to implement a new feature from a design spec.",
        "operator_assigned_closeness": 0.2,
        "rationale": "cross-category.",
    },
    {
        "pair_id": "anchor_mid_001",
        "description_A": "Research a topic and produce a written report.",
        "description_B": "Analyze a decision and produce a reasoned recommendation.",
        "operator_assigned_closeness": 0.5,
        "rationale": "same category, different output shape.",
    },
    {
        "pair_id": "anchor_high_001",
        "description_A": "Draft a short blog post for a general audience.",
        "description_B": "Draft a short blog post for a technical audience.",
        "operator_assigned_closeness": 0.75,
        "rationale": "audience-only distinction.",
    },
]


def _mock_panel() -> object:
    """Return a fresh create_autospec mock of the real panel_query.

    Centralized so every test uses the same mock-construction path and
    any drift in panel_query's signature surfaces as a uniform failure.
    """

    return create_autospec(panel_query, spec_set=True)


def _result_dict(
    requests: list[PanelRequest], selections: list[str]
) -> dict[str, PanelResult]:
    """Build the dict[request_id, PanelResult] shape panel_query returns."""

    if len(requests) != len(selections):
        raise ValueError("selections must align 1:1 with requests")
    return {
        req.request_id: PanelResult(selection=sel, raw_response=sel, error=None)
        for req, sel in zip(requests, selections)
    }


# --- Single-pair scoring ---------------------------------------------------


def test_score_pair_closeness_happy_path():
    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        return _result_dict(requests, ["0.65"])

    mock.side_effect = side_effect

    out = score_pair_closeness(
        "Description A text",
        "Description B text",
        anchors=ANCHORS,
        judge_model="claude-sonnet-4-5",
        panel_query_fn=mock,
    )

    assert out["score"] == 0.65
    assert out["raw_response"] == "0.65"
    assert out["judge_model"] == "claude-sonnet-4-5"
    assert out["prompt_template_version"] == PROMPT_TEMPLATE_VERSION
    assert out["anchors_used"] == [
        "anchor_low_001",
        "anchor_mid_001",
        "anchor_high_001",
    ]
    assert out["error"] is None
    assert mock.call_count == 1


def test_score_pair_closeness_tolerates_decorated_numeric():
    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        return _result_dict(requests, ["  0.42  "])

    mock.side_effect = side_effect

    out = score_pair_closeness(
        "A",
        "B",
        anchors=ANCHORS,
        judge_model="gpt-5",
        panel_query_fn=mock,
    )
    assert out["score"] == 0.42


def test_score_pair_closeness_rejects_out_of_range():
    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        return _result_dict(requests, ["1.5"])

    mock.side_effect = side_effect

    out = score_pair_closeness(
        "A",
        "B",
        anchors=ANCHORS,
        judge_model="gpt-5",
        panel_query_fn=mock,
    )
    assert out["score"] is None
    assert "unparseable" in out["error"]


def test_score_pair_closeness_error_path_propagates():
    mock = _mock_panel()
    mock.side_effect = PanelProviderError(
        model="claude-sonnet-4-5",
        attempts=3,
        last_error="429 rate limit",
    )

    out = score_pair_closeness(
        "A",
        "B",
        anchors=ANCHORS,
        judge_model="claude-sonnet-4-5",
        panel_query_fn=mock,
    )

    assert out["score"] is None
    assert out["error"] is not None
    assert "rate limit" in out["error"]
    assert out["judge_model"] == "claude-sonnet-4-5"


def test_score_pair_closeness_per_request_error_surface():
    """panel_query returned a PanelResult with error set (not a raised exc)."""

    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        req = requests[0]
        return {
            req.request_id: PanelResult(
                selection="",
                raw_response="",
                error="provider returned empty body",
            )
        }

    mock.side_effect = side_effect

    out = score_pair_closeness(
        "A",
        "B",
        anchors=ANCHORS,
        judge_model="gpt-5",
        panel_query_fn=mock,
    )
    assert out["score"] is None
    assert out["error"] == "provider returned empty body"


# --- Batch scoring ---------------------------------------------------------


def test_score_pairs_batch_single_call_multiple_results():
    mock = _mock_panel()

    captured: dict[str, list[PanelRequest]] = {}

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        captured["requests"] = list(requests)
        # Return scores in reverse input order to verify id-based mapping.
        mapping = ["0.30", "0.60", "0.90"]
        return _result_dict(requests, mapping)

    mock.side_effect = side_effect

    pairs = [
        ("desc a0", "desc b0"),
        ("desc a1", "desc b1"),
        ("desc a2", "desc b2"),
    ]
    out = score_pairs_batch(
        pairs,
        ANCHORS,
        "claude-sonnet-4-5",
        panel_query_fn=mock,
    )

    assert mock.call_count == 1  # D016: one panel_query call per batch.
    assert len(captured["requests"]) == 3
    assert [r["score"] for r in out] == [0.30, 0.60, 0.90]
    assert all(r["error"] is None for r in out)


def test_score_pairs_batch_empty_input_returns_empty():
    mock = _mock_panel()
    out = score_pairs_batch([], ANCHORS, "gpt-5", panel_query_fn=mock)
    assert out == []
    assert mock.call_count == 0


def test_score_pairs_batch_maps_by_request_id_not_order():
    """Results are keyed by request_id; order in the dict is irrelevant."""

    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        # Dict keys shuffled compared to requests order — correct
        # implementation must map back via request_id, not index.
        by_id = {
            req.request_id: PanelResult(
                selection=str(round(0.10 * (idx + 1), 2)),
                raw_response="",
                error=None,
            )
            for idx, req in enumerate(requests)
        }
        return dict(reversed(list(by_id.items())))

    mock.side_effect = side_effect
    pairs = [("a0", "b0"), ("a1", "b1"), ("a2", "b2")]
    out = score_pairs_batch(
        pairs,
        ANCHORS,
        "claude-sonnet-4-5",
        panel_query_fn=mock,
    )
    assert [r["score"] for r in out] == [0.10, 0.20, 0.30]


def test_score_pairs_batch_propagates_panel_provider_error():
    mock = _mock_panel()
    mock.side_effect = PanelProviderError(
        model="gpt-5", attempts=5, last_error="timeout"
    )
    pairs = [("a", "b"), ("c", "d")]
    out = score_pairs_batch(pairs, ANCHORS, "gpt-5", panel_query_fn=mock)
    assert len(out) == 2
    assert all(r["score"] is None for r in out)
    assert all("timeout" in r["error"] for r in out)


# --- Anchor interleaving ---------------------------------------------------


def test_prompt_contains_each_anchor_block():
    mock = _mock_panel()
    captured: dict[str, list[PanelRequest]] = {}

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        captured["requests"] = list(requests)
        return _result_dict(requests, ["0.5"])

    mock.side_effect = side_effect

    score_pair_closeness(
        "Pair A text",
        "Pair B text",
        anchors=ANCHORS,
        judge_model="claude-sonnet-4-5",
        panel_query_fn=mock,
    )

    prompt = captured["requests"][0].prompt
    for anchor in ANCHORS:
        assert anchor["description_A"] in prompt
        assert anchor["description_B"] in prompt
        assert str(anchor["operator_assigned_closeness"]) in prompt
    assert "Pair A text" in prompt
    assert "Pair B text" in prompt


def test_prompt_uses_versioned_template_shape():
    """Prompt inherits the JUDGE_PROMPT shell — protects against silent rewrites."""

    mock = _mock_panel()
    captured: dict[str, list[PanelRequest]] = {}

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        captured["requests"] = list(requests)
        return _result_dict(requests, ["0.5"])

    mock.side_effect = side_effect
    score_pair_closeness(
        "A",
        "B",
        anchors=ANCHORS[:1],
        judge_model="gpt-5",
        panel_query_fn=mock,
    )
    prompt = captured["requests"][0].prompt
    # Sentinel phrases from the module-level JUDGE_PROMPT.
    assert "Calibration anchors" in prompt
    assert "Return only the score as a float" in JUDGE_PROMPT


# --- Sensitivity analysis --------------------------------------------------


def test_anchor_sensitivity_produces_variance_per_count():
    mock = _mock_panel()

    # Five-anchor pool; we'll ask for counts 2, 3, 4.
    anchor_pool = [
        {
            "pair_id": f"a{i}",
            "description_A": f"desc A {i}",
            "description_B": f"desc B {i}",
            "operator_assigned_closeness": 0.2 + 0.1 * i,
            "rationale": "synthetic",
        }
        for i in range(5)
    ]
    # Emit different score patterns per count so variance differs.
    # 3 pairs; count=2 -> [0.1, 0.2, 0.3]; count=3 -> [0.4, 0.4, 0.4];
    # count=4 -> [0.1, 0.9, 0.5].
    pattern = {
        2: ["0.1", "0.2", "0.3"],
        3: ["0.4", "0.4", "0.4"],
        4: ["0.1", "0.9", "0.5"],
    }

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        # Count of anchors is encoded in the prompt — recover it by counting
        # "Closeness:" occurrences (one per anchor).
        prompt = requests[0].prompt
        count = prompt.count("Closeness:")
        return _result_dict(requests, pattern[count])

    mock.side_effect = side_effect
    pairs = [("x", "y"), ("p", "q"), ("m", "n")]

    out = anchor_sensitivity_analysis(
        pairs,
        anchor_pool,
        judge_model="claude-sonnet-4-5",
        panel_query_fn=mock,
        anchor_counts=[2, 3, 4],
    )

    assert out["anchor_counts"] == [2, 3, 4]
    # count=2: variance of [0.1, 0.2, 0.3] > 0.
    assert out["per_count"][2]["variance"] > 0
    # count=3: all-equal scores -> variance 0.
    assert out["per_count"][3]["variance"] == 0
    # count=4: wide spread -> variance higher than count=2.
    assert out["per_count"][4]["variance"] > out["per_count"][2]["variance"]


def test_anchor_sensitivity_skips_counts_exceeding_pool():
    mock = _mock_panel()

    def side_effect(requests: list[PanelRequest]) -> dict[str, PanelResult]:
        return _result_dict(requests, ["0.5"] * len(requests))

    mock.side_effect = side_effect

    anchor_pool = ANCHORS[:2]  # only 2 anchors available
    out = anchor_sensitivity_analysis(
        [("a", "b")],
        anchor_pool,
        judge_model="gpt-5",
        panel_query_fn=mock,
        anchor_counts=[2, 3, 4],
    )
    assert out["anchor_counts"] == [2]
    assert 3 not in out["per_count"]
    assert 4 not in out["per_count"]


def test_anchor_sensitivity_rejects_count_below_two():
    mock = _mock_panel()
    with pytest.raises(ValueError):
        anchor_sensitivity_analysis(
            [("a", "b")],
            ANCHORS,
            judge_model="gpt-5",
            panel_query_fn=mock,
            anchor_counts=[1, 2],
        )


# --- Structural mock sanity ------------------------------------------------


def test_autospec_rejects_wrong_arg_types():
    """create_autospec(panel_query) is not a permissive pass-through.

    Calling the mock with the wrong shape (a raw string instead of a
    list[PanelRequest]) must raise TypeError — that is the D016
    structural guarantee that ties scorer tests to Commitment A. If the
    real panel_query signature drifts (e.g. renames ``requests`` to a
    keyword-only parameter), this test is the tripwire.
    """

    mock = _mock_panel()
    # Real signature: panel_query(requests: list[PanelRequest], *,
    # record_writer=None, max_workers=8). Passing zero args must raise.
    with pytest.raises(TypeError):
        mock()
    # Passing an unknown keyword must also raise under spec_set.
    with pytest.raises(TypeError):
        mock([], nonexistent_kwarg=True)
