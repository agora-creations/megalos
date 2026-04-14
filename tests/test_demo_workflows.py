"""Tests for demo workflows — validation, context injection, directives."""

import json
import os


from mikros_server import state
from mikros_server.schema import validate_workflow
from tests.conftest import call_tool

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "..", "mikros_server", "workflows")


def _wf_path(name):
    return os.path.join(WORKFLOW_DIR, name)


# --- All four load without errors ---

class TestWorkflowsLoad:
    def test_demo_validation_loads(self):
        errors, doc = validate_workflow(_wf_path("demo_validation.yaml"))
        assert errors == [], errors

    def test_demo_context_loads(self):
        errors, doc = validate_workflow(_wf_path("demo_context.yaml"))
        assert errors == [], errors

    def test_demo_directives_socratic_loads(self):
        errors, doc = validate_workflow(_wf_path("demo_directives_socratic.yaml"))
        assert errors == [], errors

    def test_demo_directives_direct_loads(self):
        errors, doc = validate_workflow(_wf_path("demo_directives_direct.yaml"))
        assert errors == [], errors


# --- Schema validation rejection loop ---

class TestDemoValidation:
    def setup_method(self):
        state.clear_sessions()
        from mikros_server.main import WORKFLOWS
        from mikros_server.schema import load_workflow
        WORKFLOWS["demo_validation"] = load_workflow(_wf_path("demo_validation.yaml"))

    def _start(self):
        r = call_tool("start_workflow", {"workflow_type": "demo_validation", "context": "test"})
        return r["session_id"]

    def test_valid_submission_accepted(self):
        sid = self._start()
        content = json.dumps({"title": "My Project", "goals": ["a", "b", "c"], "confirmed": True})
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert "submitted" in r
        assert r["submitted"]["id"] == "collect_info"

    def test_missing_field_rejected(self):
        sid = self._start()
        content = json.dumps({"title": "My Project", "confirmed": True})  # missing goals
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert r["status"] == "validation_error"
        assert any("goals" in e for e in r["errors"])

    def test_wrong_type_rejected(self):
        sid = self._start()
        content = json.dumps({"title": "My Project", "goals": "not-an-array", "confirmed": True})
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert r["status"] == "validation_error"
        assert any("array" in e.lower() or "not-an-array" in e for e in r["errors"])

    def test_constraint_violation_title_too_short(self):
        sid = self._start()
        content = json.dumps({"title": "ab", "goals": ["a", "b", "c"], "confirmed": True})
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert r["status"] == "validation_error"

    def test_constraint_violation_too_few_goals(self):
        sid = self._start()
        content = json.dumps({"title": "My Project", "goals": ["a"], "confirmed": True})
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert r["status"] == "validation_error"

    def test_constraint_violation_confirmed_false(self):
        sid = self._start()
        content = json.dumps({"title": "My Project", "goals": ["a", "b", "c"], "confirmed": False})
        r = call_tool("submit_step", {"session_id": sid, "step_id": "collect_info", "content": content})
        assert r["status"] == "validation_error"


# --- Cross-step context injection ---

class TestDemoContext:
    def setup_method(self):
        state.clear_sessions()
        from mikros_server.main import WORKFLOWS
        from mikros_server.schema import load_workflow
        WORKFLOWS["demo_context"] = load_workflow(_wf_path("demo_context.yaml"))

    def test_step2_receives_step1_context(self):
        # Start and complete step 1
        r = call_tool("start_workflow", {"workflow_type": "demo_context", "context": "test"})
        sid = r["session_id"]
        step1_data = {"project": "Widget Builder", "goals": ["fast", "reliable", "cheap"]}
        r = call_tool("submit_step", {"session_id": sid, "step_id": "gather", "content": json.dumps(step1_data)})
        assert "submitted" in r

        # Get state for step 2 — should have injected_context
        r2 = call_tool("get_state", {"session_id": sid})
        assert "injected_context" in r2
        ctx = r2["injected_context"]
        # injected_context is a list of dicts; step 1's data should appear
        ctx_str = json.dumps(ctx)
        assert "Widget Builder" in ctx_str


# --- Directive differentiation ---

class TestDemoDirectives:
    def setup_method(self):
        state.clear_sessions()
        from mikros_server.main import WORKFLOWS
        from mikros_server.schema import load_workflow
        WORKFLOWS["demo_directives_socratic"] = load_workflow(_wf_path("demo_directives_socratic.yaml"))
        WORKFLOWS["demo_directives_direct"] = load_workflow(_wf_path("demo_directives_direct.yaml"))

    def test_socratic_has_socratic_directives(self):
        r = call_tool("start_workflow", {"workflow_type": "demo_directives_socratic", "context": "test"})
        assert "directives" in r
        assert "Socratic" in r["directives"]["strategy"]
        assert r["directives"]["persona"] == "You are a university professor who genuinely enjoys teaching."

    def test_direct_has_direct_directives(self):
        state.clear_sessions()
        r = call_tool("start_workflow", {"workflow_type": "demo_directives_direct", "context": "test"})
        assert "directives" in r
        assert "direct" in r["directives"]["strategy"].lower()
        assert r["directives"]["persona"] == "You are a senior engineer who values brevity and precision."

    def test_directives_differ_between_workflows(self):
        r_soc = call_tool("start_workflow", {"workflow_type": "demo_directives_socratic", "context": "test"})
        state.clear_sessions()
        r_dir = call_tool("start_workflow", {"workflow_type": "demo_directives_direct", "context": "test"})
        assert r_soc["directives"]["strategy"] != r_dir["directives"]["strategy"]
        assert r_soc["directives"]["tone"] != r_dir["directives"]["tone"]
