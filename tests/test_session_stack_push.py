"""End-to-end coverage of the push_flow digression primitive.

Covers:
- push creates a digression-frame above the outer session with correct semantics
- paused_at_step defensive echo (mismatch → out_of_order_submission)
- outer-session preconditions (unknown session, complete, escalated)
- unknown workflow_type rejected
- digression completes → outer auto-resumes at preserved current_step, no data handoff
- digression data does NOT propagate into outer.step_data
- generalized pending guard: submit_step on outer while digression in flight
- generalized pending guard: push_flow on outer while already-pushed digression in flight
- generalized parent-owned guard: revise_step on digression-child
- generalized parent-owned guard: delete_session on digression-child
- additive frame_type field on pending + parent_owned error bodies (for both
  'call' and 'digression' frame flavors)
- call-frame auto-resume still uses M004 propagate semantics (regression probe)
"""

import pytest  # type: ignore[import-not-found]

from megalos_server import state
from megalos_server.main import WORKFLOWS
from tests.conftest import call_tool


_OUTER = "push-outer"
_DIGRESSION = "push-digression"
_CALL_PARENT = "push-call-parent"
_CALL_CHILD = "push-call-child"


def _outer_wf() -> dict:
    return {
        "name": _OUTER,
        "description": "outer linear workflow",
        "category": "test",
        "output_format": "text",
        "steps": [
            {"id": "o1", "title": "Outer 1", "directive_template": "do o1",
             "gates": ["done"], "anti_patterns": []},
            {"id": "o2", "title": "Outer 2", "directive_template": "do o2",
             "gates": ["done"], "anti_patterns": []},
            {"id": "o3", "title": "Outer 3", "directive_template": "do o3",
             "gates": ["done"], "anti_patterns": []},
        ],
    }


def _digression_wf() -> dict:
    return {
        "name": _DIGRESSION,
        "description": "short digression",
        "category": "test",
        "output_format": "text",
        "steps": [
            {"id": "d1", "title": "Digression 1", "directive_template": "do d1",
             "gates": ["done"], "anti_patterns": []},
            {"id": "d2", "title": "Digression 2", "directive_template": "do d2",
             "gates": ["done"], "anti_patterns": []},
        ],
    }


def _call_parent_wf() -> dict:
    return {
        "name": _CALL_PARENT,
        "description": "parent with call step — regression probe for M004 auto-resume",
        "category": "test",
        "output_format": "text",
        "steps": [
            {"id": "p1", "title": "P1", "directive_template": "do p1",
             "gates": ["done"], "anti_patterns": []},
            {"id": "p2", "title": "Call step", "directive_template": "hand off",
             "gates": ["done"], "anti_patterns": [], "call": _CALL_CHILD},
            {"id": "p3", "title": "P3", "directive_template": "do p3",
             "gates": ["done"], "anti_patterns": []},
        ],
    }


def _call_child_wf() -> dict:
    return {
        "name": _CALL_CHILD,
        "description": "callable child",
        "category": "test",
        "output_format": "text",
        "steps": [
            {"id": "c1", "title": "C1", "directive_template": "do c1",
             "gates": ["done"], "anti_patterns": []},
        ],
    }


@pytest.fixture(autouse=True)
def _register_wfs():
    WORKFLOWS[_OUTER] = _outer_wf()
    WORKFLOWS[_DIGRESSION] = _digression_wf()
    WORKFLOWS[_CALL_PARENT] = _call_parent_wf()
    WORKFLOWS[_CALL_CHILD] = _call_child_wf()
    yield
    WORKFLOWS.pop(_OUTER, None)
    WORKFLOWS.pop(_DIGRESSION, None)
    WORKFLOWS.pop(_CALL_PARENT, None)
    WORKFLOWS.pop(_CALL_CHILD, None)


def _start_outer() -> str:
    r = call_tool("start_workflow", {"workflow_type": _OUTER, "context": ""})
    return r["session_id"]


def _advance_outer_to_o2(outer_sid: str) -> None:
    r = call_tool("submit_step", {"session_id": outer_sid, "step_id": "o1", "content": "o1-done"})
    assert r.get("code") is None, r


def _push_digression(outer_sid: str, paused_at: str = "o2", ctx: str = "why-digress") -> dict:
    return call_tool(
        "push_flow",
        {
            "session_id": outer_sid,
            "workflow_type": _DIGRESSION,
            "paused_at_step": paused_at,
            "context": ctx,
        },
    )


def _complete_digression(child_sid: str) -> dict:
    r1 = call_tool("submit_step", {"session_id": child_sid, "step_id": "d1", "content": "d1-done"})
    assert r1.get("code") is None, r1
    r2 = call_tool("submit_step", {"session_id": child_sid, "step_id": "d2", "content": "d2-done"})
    return r2


# --- push_flow happy path ---------------------------------------------------


def test_push_flow_creates_child_session_and_pushes_digression_frame():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    r = _push_digression(outer_sid)
    assert r.get("session_id") and r["session_id"] != outer_sid
    child_sid = r["session_id"]
    own = state.own_frame(child_sid)
    assert own is not None and own["frame_type"] == "digression"
    assert own["call_step_id"] == "o2"  # paused_at_step stored in overloaded column


def test_push_flow_returns_first_step_directive_and_context():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    r = _push_digression(outer_sid, ctx="focus-topic")
    assert r["current_step"]["id"] == "d1"
    assert r["directive"] == "do d1"
    assert r["context"] == "focus-topic"
    assert r["parent_session_id"] == outer_sid
    assert r["paused_at_step"] == "o2"


def test_push_flow_reports_frame_depth():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    r = _push_digression(outer_sid)
    assert r["frame_depth"] == 1


def test_push_flow_does_not_mutate_outer_current_step():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    _push_digression(outer_sid)
    outer = state.get_session(outer_sid)
    assert outer["current_step"] == "o2"


# --- push_flow precondition rejects -----------------------------------------


def test_push_flow_rejects_unknown_outer_session():
    r = call_tool(
        "push_flow",
        {"session_id": "no-such", "workflow_type": _DIGRESSION, "paused_at_step": "o1", "context": ""},
    )
    assert r["code"] == "session_not_found"


def test_push_flow_rejects_paused_at_step_mismatch():
    outer_sid = _start_outer()  # at o1
    r = _push_digression(outer_sid, paused_at="o2")  # mismatch
    assert r["code"] == "out_of_order_submission"
    assert r["expected_step"] == "o1"
    assert r["submitted_step"] == "o2"


def test_push_flow_rejects_unknown_workflow_type():
    outer_sid = _start_outer()
    r = call_tool(
        "push_flow",
        {"session_id": outer_sid, "workflow_type": "no-such-wf", "paused_at_step": "o1", "context": ""},
    )
    assert r["code"] == "workflow_not_loaded"


def test_push_flow_rejects_completed_outer():
    outer_sid = _start_outer()
    call_tool("submit_step", {"session_id": outer_sid, "step_id": "o1", "content": "o1"})
    call_tool("submit_step", {"session_id": outer_sid, "step_id": "o2", "content": "o2"})
    call_tool("submit_step", {"session_id": outer_sid, "step_id": "o3", "content": "o3"})
    # outer now at __complete__
    r = _push_digression(outer_sid, paused_at="o3")
    assert r["code"] == "workflow_complete"


# --- auto-resume on digression completion -----------------------------------


def test_digression_completion_auto_resumes_outer_at_paused_step():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    child_sid = push["session_id"]
    r = _complete_digression(child_sid)
    assert r["resumed_from_digression"] is True
    assert r["session_id"] == outer_sid
    assert r["current_step"]["id"] == "o2"
    assert r["directive"] == "do o2"


def test_digression_completion_deletes_digression_child():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    child_sid = push["session_id"]
    _complete_digression(child_sid)
    r = call_tool("get_state", {"session_id": child_sid})
    assert r.get("code") == "session_not_found"


def test_digression_completion_does_not_propagate_artifact_to_outer():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    child_sid = push["session_id"]
    _complete_digression(child_sid)
    outer = state.get_session(outer_sid)
    # No data contract for digression frames — outer.step_data unchanged beyond o1.
    assert list(outer["step_data"].keys()) == ["o1"]
    assert outer["current_step"] == "o2"


def test_digression_resume_response_does_not_mark_propagated_from_sub_workflow():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    r = _complete_digression(push["session_id"])
    # Digression resume != call-frame propagate. Field must be absent to keep the
    # M004 marker semantically meaningful.
    assert "propagated_from_sub_workflow" not in r


def test_outer_can_resume_and_complete_after_digression():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    _complete_digression(push["session_id"])
    r2 = call_tool("submit_step", {"session_id": outer_sid, "step_id": "o2", "content": "o2-done"})
    assert r2.get("code") is None
    assert r2["next_step"]["id"] == "o3"


# --- generalized pending guard (submit / push on non-top) -------------------


def test_submit_step_on_outer_rejected_while_digression_in_flight():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    r = call_tool("submit_step", {"session_id": outer_sid, "step_id": "o2", "content": "oops"})
    assert r["code"] == "sub_workflow_pending"
    assert r["child_session_id"] == push["session_id"]
    # Additive field: frame_type carries the blocking frame's type.
    assert r["frame_type"] == "digression"


def test_push_flow_on_outer_rejected_while_digression_in_flight():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    first = _push_digression(outer_sid)
    second = _push_digression(outer_sid)
    assert second["code"] == "sub_workflow_pending"
    assert second["child_session_id"] == first["session_id"]
    assert second["frame_type"] == "digression"


def test_submit_step_pending_envelope_carries_call_frame_type_for_call_frames():
    """Regression probe: the same generalized pending guard must carry
    frame_type='call' when the blocking frame is a call-frame (M004 path)."""
    start = call_tool("start_workflow", {"workflow_type": _CALL_PARENT, "context": ""})
    parent_sid = start["session_id"]
    call_tool("submit_step", {"session_id": parent_sid, "step_id": "p1", "content": "p1"})
    spawn = call_tool(
        "enter_sub_workflow", {"parent_session_id": parent_sid, "call_step_id": "p2"}
    )
    child_sid = spawn["session_id"]
    r = call_tool("submit_step", {"session_id": parent_sid, "step_id": "p2", "content": "oops"})
    assert r["code"] == "sub_workflow_pending"
    assert r["child_session_id"] == child_sid
    assert r["frame_type"] == "call"


# --- generalized parent-owned guard (revise / delete) -----------------------


def test_revise_step_on_digression_child_returns_parent_owned_with_digression_frame_type():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    child_sid = push["session_id"]
    # Complete d1 so there is something to revise.
    call_tool("submit_step", {"session_id": child_sid, "step_id": "d1", "content": "d1-done"})
    r = call_tool("revise_step", {"session_id": child_sid, "step_id": "d1"})
    assert r["code"] == "sub_workflow_parent_owned"
    assert r["parent_session_id"] == outer_sid
    assert r["frame_type"] == "digression"


def test_delete_session_on_digression_child_returns_parent_owned_with_digression_frame_type():
    outer_sid = _start_outer()
    _advance_outer_to_o2(outer_sid)
    push = _push_digression(outer_sid)
    child_sid = push["session_id"]
    r = call_tool("delete_session", {"session_id": child_sid})
    assert r["code"] == "sub_workflow_parent_owned"
    assert r["parent_session_id"] == outer_sid
    assert r["frame_type"] == "digression"


def test_revise_step_parent_owned_envelope_carries_call_frame_type_for_call_children():
    """Regression probe: the same generalized parent-owned guard must carry
    frame_type='call' when the framed child is a call-frame (M004 path)."""
    start = call_tool("start_workflow", {"workflow_type": _CALL_PARENT, "context": ""})
    parent_sid = start["session_id"]
    call_tool("submit_step", {"session_id": parent_sid, "step_id": "p1", "content": "p1"})
    spawn = call_tool(
        "enter_sub_workflow", {"parent_session_id": parent_sid, "call_step_id": "p2"}
    )
    child_sid = spawn["session_id"]
    # Complete c1 so there is something to revise on the child.
    call_tool("submit_step", {"session_id": child_sid, "step_id": "c1", "content": "c1-done"})
    # c1 was the last step — child completed and auto-propagated. Rebuild the
    # owned-child state: spawn another child and revise while it's in flight.
    call_tool("revise_step", {"session_id": parent_sid, "step_id": "p2"})
    spawn2 = call_tool(
        "enter_sub_workflow", {"parent_session_id": parent_sid, "call_step_id": "p2"}
    )
    child2 = spawn2["session_id"]
    r = call_tool("revise_step", {"session_id": child2, "step_id": "c1"})
    # c1 not yet completed on child2; revise guard still fires because child2 is
    # parent-owned. Whether the guard precedes the "not completed" check is an
    # implementation detail — what we check is the code + frame_type.
    assert r["code"] == "sub_workflow_parent_owned"
    assert r["frame_type"] == "call"


# --- call-frame regression probe (M004 path unchanged) ----------------------


def test_call_frame_auto_resume_still_propagates_artifact_to_parent():
    """M004 call-frame path must not regress after frame-type dispatch. Child
    artifact propagates into parent.step_data[call_step_id] and parent advances
    to the next step with propagated_from_sub_workflow=True."""
    start = call_tool("start_workflow", {"workflow_type": _CALL_PARENT, "context": ""})
    parent_sid = start["session_id"]
    call_tool("submit_step", {"session_id": parent_sid, "step_id": "p1", "content": "p1"})
    spawn = call_tool(
        "enter_sub_workflow", {"parent_session_id": parent_sid, "call_step_id": "p2"}
    )
    child_sid = spawn["session_id"]
    r = call_tool("submit_step", {"session_id": child_sid, "step_id": "c1", "content": "child-artifact"})
    assert r["propagated_from_sub_workflow"] is True
    assert r["next_step"]["id"] == "p3"
    parent = state.get_session(parent_sid)
    assert parent["step_data"]["p2"] == "child-artifact"
