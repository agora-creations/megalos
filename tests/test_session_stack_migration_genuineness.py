"""Negative-assertion tests that prove sub-workflow parent/child reads route
through the session_stack table, not through the legacy parent_session_id /
called_session columns on the sessions row.

Setup strategy: seed a session state in which the legacy columns are set
(pointing to a plausible parent/child link) but NO session_stack row backs
that link. A tool that routes reads through the stack must behave as if
there were no link at all. A tool that falls back to the legacy columns
when the stack is empty would fire a sub-workflow guard and give itself
away.

Each test asserts the stack-authoritative outcome on the positive side
(operation proceeds) and the guard's specific error code on the negative
side (to document which branch would have been taken by a legacy-column
reader).
"""

import pytest  # type: ignore[import-not-found]

from megalos_server import db, state
from megalos_server.main import WORKFLOWS
from tests.conftest import call_tool


_PARENT = "genuineness-parent"
_CHILD = "genuineness-child"


def _parent_wf() -> dict:
    return {
        "name": _PARENT,
        "description": "parent with call step",
        "category": "test",
        "output_format": "text",
        "steps": [
            {
                "id": "p1",
                "title": "Parent step 1",
                "directive_template": "do p1",
                "gates": ["done"],
                "anti_patterns": [],
            },
            {
                "id": "p2",
                "title": "Parent call step",
                "directive_template": "hand off",
                "gates": ["done"],
                "anti_patterns": [],
                "call": _CHILD,
            },
            {
                "id": "p3",
                "title": "Parent step 3",
                "directive_template": "do p3",
                "gates": ["done"],
                "anti_patterns": [],
            },
        ],
    }


def _child_wf() -> dict:
    return {
        "name": _CHILD,
        "description": "child workflow",
        "category": "test",
        "output_format": "text",
        "steps": [
            {
                "id": "c1",
                "title": "Child step 1",
                "directive_template": "child work",
                "gates": ["done"],
                "anti_patterns": [],
            },
        ],
    }


@pytest.fixture(autouse=True)
def _register_wfs():
    WORKFLOWS[_PARENT] = _parent_wf()
    WORKFLOWS[_CHILD] = _child_wf()
    yield
    WORKFLOWS.pop(_PARENT, None)
    WORKFLOWS.pop(_CHILD, None)


def _seed_legacy_called_session(parent_sid: str, child_sid: str) -> None:
    """Write the parent's legacy called_session column AND a matching child
    sessions row whose parent_session_id column points at the parent — but
    push NO session_stack frame. This is the bad state the test probes."""
    with db.transaction() as conn:
        conn.execute(
            "UPDATE sessions SET called_session = ? WHERE session_id = ?",
            (child_sid, parent_sid),
        )
        conn.execute(
            "INSERT INTO sessions (session_id, workflow_type, current_step, "
            "step_data, retry_counts, step_visit_counts, escalation, "
            "artifact_checkpoints, created_at, updated_at, completed_at, "
            "called_session, parent_session_id) "
            "VALUES (?, ?, ?, '{}', '{}', '{}', NULL, '{}', "
            "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', NULL, "
            "NULL, ?)",
            (child_sid, _CHILD, "c1", parent_sid),
        )


def _advance_parent_to_call_step(parent_sid: str) -> None:
    r = call_tool(
        "submit_step",
        {"session_id": parent_sid, "step_id": "p1", "content": "first"},
    )
    assert "error" not in r, r


def test_enter_sub_workflow_ignores_legacy_called_session_without_stack_frame():
    """Seed parent.called_session + orphan child row with no stack frame, then
    call enter_sub_workflow. Stack-authoritative: guard sees no pending child
    and the spawn proceeds. Legacy-reader: would fire sub_workflow_pending."""
    r = call_tool("start_workflow", {"workflow_type": _PARENT, "context": ""})
    parent_sid = r["session_id"]
    _advance_parent_to_call_step(parent_sid)

    fake_child_sid = "ghostchild001"
    _seed_legacy_called_session(parent_sid, fake_child_sid)

    # Sanity: legacy column carries the ghost child, stack carries nothing.
    assert state.get_session(parent_sid)["called_session"] == fake_child_sid
    assert state.top_frame_for(parent_sid) is None

    result = call_tool(
        "enter_sub_workflow",
        {"parent_session_id": parent_sid, "call_step_id": "p2"},
    )

    # If the guard had read the legacy column it would have returned
    # sub_workflow_pending with child_session_id=fake_child_sid. Instead
    # the spawn proceeds and a real child session is created.
    assert result.get("code") != "sub_workflow_pending", result
    assert "session_id" in result, result
    real_child_sid = result["session_id"]
    assert real_child_sid != fake_child_sid

    # And the real child DID get a stack frame — proving stack writes are live.
    assert state.top_frame_for(parent_sid) is not None
    assert state.top_frame_for(parent_sid)["session_id"] == real_child_sid


def test_submit_step_on_call_step_ignores_legacy_called_session_without_stack_frame():
    """Seed parent.called_session without a stack frame, then call submit_step
    on the call-step. Stack-authoritative: the in-flight-child guard does NOT
    fire, and submit_step returns the call_step_requires_enter_sub_workflow
    routing error. Legacy-reader: would fire sub_workflow_pending."""
    r = call_tool("start_workflow", {"workflow_type": _PARENT, "context": ""})
    parent_sid = r["session_id"]
    _advance_parent_to_call_step(parent_sid)

    fake_child_sid = "ghostchild002"
    _seed_legacy_called_session(parent_sid, fake_child_sid)

    result = call_tool(
        "submit_step",
        {"session_id": parent_sid, "step_id": "p2", "content": "x"},
    )

    # Legacy-reader would have returned sub_workflow_pending. Stack-reader
    # sees an empty stack, skips that guard, and returns the call-step
    # routing error instead.
    assert result.get("code") == "call_step_requires_enter_sub_workflow", result


def test_revise_step_on_ghost_child_proceeds_because_stack_shows_no_parent():
    """Seed a child whose parent_session_id legacy column is set, but with
    no session_stack row. Calling revise_step on the child must PROCEED:
    the parent-owned guard consults parent_of(child) via the stack and sees
    None. A legacy-reader would have returned sub_workflow_parent_owned."""
    # Real parent is needed only so the legacy FK target exists.
    r = call_tool("start_workflow", {"workflow_type": _PARENT, "context": ""})
    parent_sid = r["session_id"]
    _advance_parent_to_call_step(parent_sid)

    # Start a standalone child session (top-level), then backdate its
    # parent_session_id column to point at the parent without pushing a frame.
    child_sid = state.create_session(_CHILD, current_step="c1")
    with db.transaction() as conn:
        conn.execute(
            "UPDATE sessions SET parent_session_id = ? WHERE session_id = ?",
            (parent_sid, child_sid),
        )
        # Also fake the parent's legacy called_session to make the ghost
        # link look fully bidirectional.
        conn.execute(
            "UPDATE sessions SET called_session = ? WHERE session_id = ?",
            (child_sid, parent_sid),
        )

    # Complete c1 on the child so revise_step has content to operate on.
    submit = call_tool(
        "submit_step",
        {"session_id": child_sid, "step_id": "c1", "content": "child-done"},
    )
    # c1 is the only child step, so submit_step completes the child. Child
    # has parent_session_id set in the legacy column but NO stack frame.
    # The child completion path gates on state.parent_of(child) — with no
    # stack row this returns None and propagation is correctly skipped.
    assert submit.get("status") == "workflow_complete", submit

    # Sanity: parent_of() returns None (stack-authoritative), the legacy
    # column still says otherwise.
    assert state.parent_of(child_sid) is None
    assert state.get_session(child_sid)["parent_session_id"] == parent_sid

    # revise_step on the child: the parent-owned guard is keyed on
    # parent_of(child_sid) — None via the stack — so the guard is skipped
    # and revise_step proceeds. A legacy-column reader would have fired
    # sub_workflow_parent_owned.
    result = call_tool(
        "revise_step",
        {"session_id": child_sid, "step_id": "c1"},
    )
    assert result.get("code") != "sub_workflow_parent_owned", result
    assert "revised_step" in result, result
    assert result["revised_step"]["id"] == "c1"
