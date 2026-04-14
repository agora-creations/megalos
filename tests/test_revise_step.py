"""Tests for revise_step tool — invalidate-forward semantics."""

from mikros_server import state
from tests.conftest import call_tool

CANONICAL_STEPS = ["alpha", "bravo", "charlie"]


def _fresh_session(workflow="canonical", steps_to_complete=None):
    """Start workflow and optionally submit steps. Returns session_id."""
    state.clear_sessions()
    r = call_tool("start_workflow", {"workflow_type": workflow, "context": "test"})
    sid = r["session_id"]
    for step_id in (steps_to_complete or []):
        call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": f"content-{step_id}"})
    return sid


class TestReviseStep:
    def test_revise_resets_current_step(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:2])  # alpha, bravo done; current=charlie
        r = call_tool("revise_step", {"session_id": sid, "step_id": "bravo"})
        assert r["revised_step"]["id"] == "bravo"
        s = call_tool("get_state", {"session_id": sid})
        assert s["current_step"]["id"] == "bravo"

    def test_revise_deletes_forward_step_data(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:2])  # alpha, bravo done
        r = call_tool("revise_step", {"session_id": sid, "step_id": "alpha"})
        assert "bravo" in r["invalidated_steps"]
        s = call_tool("get_state", {"session_id": sid})
        assert "bravo" not in s["step_data"]
        # alpha data preserved
        assert "alpha" in s["step_data"]

    def test_revise_returns_previous_content(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:2])
        r = call_tool("revise_step", {"session_id": sid, "step_id": "alpha"})
        assert r["previous_content"] == "content-alpha"

    def test_revise_uncompleted_step_errors(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:2])  # alpha, bravo done
        r = call_tool("revise_step", {"session_id": sid, "step_id": "charlie"})
        assert "error" in r
        assert "not been completed" in r["error"]

    def test_revise_nonexistent_step_errors(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:1])
        r = call_tool("revise_step", {"session_id": sid, "step_id": "bogus"})
        assert "error" in r
        assert "not found" in r["error"]

    def test_revise_completed_workflow_uncompletes(self):
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS)  # all done
        s = call_tool("get_state", {"session_id": sid})
        assert s["current_step"] is None  # __complete__ means no current step found
        # Revise earliest step
        r = call_tool("revise_step", {"session_id": sid, "step_id": "alpha"})
        assert r["revised_step"]["id"] == "alpha"
        s = call_tool("get_state", {"session_id": sid})
        assert s["current_step"]["id"] == "alpha"
        # All forward data gone
        assert "bravo" not in s["step_data"]
        assert "charlie" not in s["step_data"]

    def test_revise_last_completed_step_no_invalidation(self):
        """Revising the most recently completed step invalidates only the steps after it."""
        sid = _fresh_session(steps_to_complete=CANONICAL_STEPS[:2])  # current=charlie
        r = call_tool("revise_step", {"session_id": sid, "step_id": "bravo"})
        assert r["invalidated_steps"] == ["charlie"]
        s = call_tool("get_state", {"session_id": sid})
        assert s["current_step"]["id"] == "bravo"
