"""Tests for step-level context injection (inject_context)."""

import json
import tempfile

import yaml


from mikros_server.schema import validate_workflow
from tests.conftest import call_tool


def _write_workflow(steps, **extras):
    """Write a minimal workflow YAML with given steps, return path."""
    doc = {
        "name": "test-inject",
        "description": "test",
        "category": "testing",
        "output_format": "text",
        "steps": steps,
    }
    doc.update(extras)
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(doc, f)
    f.close()
    return f.name


def _make_step(id, **kwargs):
    """Create a minimal valid step dict."""
    base = {
        "id": id,
        "title": f"Step {id}",
        "directive_template": f"Do {id}",
        "gates": ["gate1"],
        "anti_patterns": ["ap1"],
    }
    base.update(kwargs)
    return base


# --- Schema validation tests ---

class TestInjectContextValidation:
    def test_valid_inject_context(self):
        steps = [
            _make_step("a"),
            _make_step("b", inject_context=[{"from": "a", "fields": ["x"], "summary": False}]),
        ]
        errors, doc = validate_workflow(_write_workflow(steps))
        assert errors == []

    def test_nonexistent_step_reference(self):
        steps = [
            _make_step("a"),
            _make_step("b", inject_context=[{"from": "nonexistent"}]),
        ]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("nonexistent" in e for e in errors)

    def test_inject_context_not_a_list(self):
        steps = [_make_step("a", inject_context="bad")]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("inject_context must be a list" in e for e in errors)

    def test_inject_context_entry_missing_from(self):
        steps = [
            _make_step("a"),
            _make_step("b", inject_context=[{"fields": ["x"]}]),
        ]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("missing required key 'from'" in e for e in errors)


# --- Runtime context assembly tests ---

class TestContextInjectionRuntime:
    """Test inject_context in submit_step and get_state responses."""

    _registered_wf_names: list = []

    def setup_method(self):
        from mikros_server import state
        state.clear_sessions()

    def teardown_method(self):
        from mikros_server import state
        from mikros_server.main import WORKFLOWS as wfs
        state.clear_sessions()
        for name in self._registered_wf_names:
            wfs.pop(name, None)
        self._registered_wf_names.clear()

    def _register_wf(self, name, wf):
        from mikros_server.main import WORKFLOWS as wfs
        wfs[name] = wf
        self._registered_wf_names.append(name)

    def _setup_workflow_with_injection(self, inject_context):
        """Register a 3-step workflow where step_c injects from earlier steps."""
        steps = [
            _make_step("step_a"),
            _make_step("step_b"),
            _make_step("step_c", inject_context=inject_context),
        ]
        wf = {
            "name": "inject-test",
            "description": "test",
            "category": "testing",
            "output_format": "text",
            "steps": steps,
        }
        self._register_wf("inject-test", wf)
        return wf

    def test_full_content_injection(self):
        """inject_context without fields injects full content."""
        self._setup_workflow_with_injection([{"from": "step_a"}])
        r = call_tool("start_workflow", {"workflow_type": "inject-test", "context": "test"})
        sid = r["session_id"]
        call_tool("submit_step", {"session_id": sid, "step_id": "step_a", "content": "alpha content"})
        # submit step_b -> response has next_step=step_c with injected_context
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "step_b", "content": "beta content"})
        assert "injected_context" in r2
        assert r2["injected_context"] == [{"from": "step_a", "content": "alpha content"}]

    def test_field_filtered_injection(self):
        """inject_context with fields extracts specific keys from JSON content."""
        self._setup_workflow_with_injection([{"from": "step_a", "fields": ["x", "y"]}])
        r = call_tool("start_workflow", {"workflow_type": "inject-test", "context": "test"})
        sid = r["session_id"]
        call_tool("submit_step", {
            "session_id": sid, "step_id": "step_a",
            "content": json.dumps({"x": 1, "y": 2, "z": 3}),
        })
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "step_b", "content": "beta"})
        assert r2["injected_context"] == [{"from": "step_a", "fields": {"x": 1, "y": 2}}]

    def test_summary_truncation(self):
        """inject_context with summary=true truncates to 500 chars."""
        self._setup_workflow_with_injection([{"from": "step_a", "summary": True}])
        r = call_tool("start_workflow", {"workflow_type": "inject-test", "context": "test"})
        sid = r["session_id"]
        long_content = "A" * 600
        call_tool("submit_step", {"session_id": sid, "step_id": "step_a", "content": long_content})
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "step_b", "content": "beta"})
        injected = r2["injected_context"][0]["content"]
        assert injected == "A" * 500 + "[truncated]"
        assert len(injected) == 511  # 500 + len("[truncated]")

    def test_no_inject_context_backward_compat(self):
        """Steps without inject_context have no injected_context in response."""
        steps = [_make_step("step_a"), _make_step("step_b")]
        self._register_wf("no-inject", {
            "name": "no-inject", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "no-inject", "context": "test"})
        sid = r["session_id"]
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "step_a", "content": "data"})
        assert "injected_context" not in r2

    def test_inject_non_json_content_fallback(self):
        """When source step has non-JSON content and fields requested, falls back to raw string."""
        self._setup_workflow_with_injection([{"from": "step_a", "fields": ["x"]}])
        r = call_tool("start_workflow", {"workflow_type": "inject-test", "context": "test"})
        sid = r["session_id"]
        call_tool("submit_step", {"session_id": sid, "step_id": "step_a", "content": "plain text, not json"})
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "step_b", "content": "beta"})
        # Falls back to raw content since it's not JSON
        assert r2["injected_context"] == [{"from": "step_a", "content": "plain text, not json"}]

    def test_get_state_includes_injected_context(self):
        """get_state for a step with inject_context includes injected_context."""
        self._setup_workflow_with_injection([{"from": "step_a"}])
        r = call_tool("start_workflow", {"workflow_type": "inject-test", "context": "test"})
        sid = r["session_id"]
        call_tool("submit_step", {"session_id": sid, "step_id": "step_a", "content": "alpha"})
        call_tool("submit_step", {"session_id": sid, "step_id": "step_b", "content": "beta"})
        # Now current step is step_c which has inject_context
        gs = call_tool("get_state", {"session_id": sid})
        assert "injected_context" in gs
        assert gs["injected_context"] == [{"from": "step_a", "content": "alpha"}]

    def test_get_state_no_inject_context(self):
        """get_state for step without inject_context has no injected_context key."""
        steps = [_make_step("a"), _make_step("b")]
        self._register_wf("gs-no-ic", {
            "name": "gs-no-ic", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "gs-no-ic", "context": "t"})
        gs = call_tool("get_state", {"session_id": r["session_id"]})
        assert "injected_context" not in gs
