"""Tests for list_sessions and delete_session tools."""

from megalos_server import state
from tests.conftest import call_tool

STEPS = ["alpha", "bravo", "charlie"]


def _clear_sessions():
    state.clear_sessions()


class TestListSessions:
    def test_list_empty(self):
        _clear_sessions()
        r = call_tool("list_sessions", {})
        assert r == {"sessions": []}

    def test_list_with_sessions(self):
        _clear_sessions()
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]

        r = call_tool("list_sessions", {})
        assert len(r["sessions"]) == 1
        s = r["sessions"][0]
        assert s["session_id"] == sid
        assert s["workflow_type"] == "canonical"
        assert s["current_step"] == "alpha"
        assert s["status"] == "active"
        assert "created_at" in s
        assert "updated_at" in s

    def test_list_shows_completed(self):
        _clear_sessions()
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]
        for step_id in STEPS:
            call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": "x"})

        r = call_tool("list_sessions", {})
        assert r["sessions"][0]["status"] == "completed"


class TestDeleteSession:
    def test_delete_active(self):
        _clear_sessions()
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]

        r = call_tool("delete_session", {"session_id": sid})
        assert r["session_id"] == sid
        assert r["workflow_type"] == "canonical"
        assert r["current_step"] == "alpha"
        assert r["completed"] is False

        # Verify gone
        r = call_tool("list_sessions", {})
        assert r["sessions"] == []

    def test_delete_completed(self):
        _clear_sessions()
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]
        for step_id in STEPS:
            call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": "x"})

        r = call_tool("delete_session", {"session_id": sid})
        assert r["session_id"] == sid
        assert r["completed"] is True

    def test_delete_unknown(self):
        _clear_sessions()
        r = call_tool("delete_session", {"session_id": "nonexistent"})
        assert "error" in r
        assert r["session_id"] == "nonexistent"
