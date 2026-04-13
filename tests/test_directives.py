"""Tests for step-level LLM behavioral directives."""

import os
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.schema import validate_workflow
from tests.conftest import call_tool


def _write_workflow(steps):
    """Write a minimal workflow YAML with given steps, return path."""
    doc = {
        "name": "test-directives",
        "description": "test",
        "category": "testing",
        "output_format": "text",
        "steps": steps,
    }
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

class TestDirectivesValidation:
    def test_valid_full_directives(self):
        steps = [_make_step("a", directives={
            "tone": "formal",
            "strategy": "chain-of-thought",
            "constraints": ["no jargon", "be concise"],
            "persona": "expert reviewer",
        })]
        errors, doc = validate_workflow(_write_workflow(steps))
        assert errors == []

    def test_valid_partial_directives(self):
        steps = [_make_step("a", directives={"tone": "casual"})]
        errors, doc = validate_workflow(_write_workflow(steps))
        assert errors == []

    def test_directives_not_a_dict(self):
        steps = [_make_step("a", directives="bad")]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("directives must be a mapping" in e for e in errors)

    def test_constraints_must_be_list(self):
        steps = [_make_step("a", directives={"constraints": "not a list"})]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("directives.constraints must be a list" in e for e in errors)

    def test_constraints_entries_must_be_strings(self):
        steps = [_make_step("a", directives={"constraints": [1, 2]})]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("constraints entries must be strings" in e for e in errors)

    def test_tone_must_be_string(self):
        steps = [_make_step("a", directives={"tone": 123})]
        errors, _ = validate_workflow(_write_workflow(steps))
        assert any("directives.tone must be a string" in e for e in errors)

    def test_unknown_keys_allowed(self):
        steps = [_make_step("a", directives={"custom_key": "value"})]
        errors, doc = validate_workflow(_write_workflow(steps))
        assert errors == []


# --- Runtime directive delivery tests ---

class TestDirectivesRuntime:
    _registered_wf_names: list = []

    def setup_method(self):
        from server import state
        state.clear_sessions()

    def teardown_method(self):
        from server import state
        from server.main import WORKFLOWS as wfs
        state.clear_sessions()
        for name in self._registered_wf_names:
            wfs.pop(name, None)
        self._registered_wf_names.clear()

    def _register_wf(self, name, wf):
        from server.main import WORKFLOWS as wfs
        wfs[name] = wf
        self._registered_wf_names.append(name)

    def test_full_directives_in_submit_step(self):
        """submit_step response includes directives for next step."""
        directives = {
            "tone": "formal",
            "strategy": "step-by-step",
            "constraints": ["no jargon"],
            "persona": "teacher",
        }
        steps = [_make_step("a"), _make_step("b", directives=directives)]
        self._register_wf("dir-full", {
            "name": "dir-full", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-full", "context": "test"})
        sid = r["session_id"]
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "a", "content": "data"})
        assert r2["directives"] == directives

    def test_partial_directives_only_tone(self):
        """Only tone specified -- returned verbatim, no extra keys added."""
        directives = {"tone": "playful"}
        steps = [_make_step("a"), _make_step("b", directives=directives)]
        self._register_wf("dir-tone", {
            "name": "dir-tone", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-tone", "context": "test"})
        sid = r["session_id"]
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "a", "content": "data"})
        assert r2["directives"] == {"tone": "playful"}

    def test_no_directives_backward_compat(self):
        """Steps without directives have no directives key in response."""
        steps = [_make_step("a"), _make_step("b")]
        self._register_wf("dir-none", {
            "name": "dir-none", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-none", "context": "test"})
        sid = r["session_id"]
        assert "directives" not in r
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "a", "content": "data"})
        assert "directives" not in r2

    def test_directives_in_get_state(self):
        """get_state includes directives for current step."""
        directives = {"strategy": "compare-contrast", "constraints": ["max 3 points"]}
        steps = [_make_step("a", directives=directives), _make_step("b")]
        self._register_wf("dir-gs", {
            "name": "dir-gs", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-gs", "context": "test"})
        gs = call_tool("get_state", {"session_id": r["session_id"]})
        assert gs["directives"] == directives

    def test_get_state_no_directives(self):
        """get_state without directives has no directives key."""
        steps = [_make_step("a"), _make_step("b")]
        self._register_wf("dir-gs-no", {
            "name": "dir-gs-no", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-gs-no", "context": "test"})
        gs = call_tool("get_state", {"session_id": r["session_id"]})
        assert "directives" not in gs

    def test_directives_in_start_workflow(self):
        """start_workflow includes directives for first step when present."""
        directives = {"tone": "encouraging", "persona": "mentor"}
        steps = [_make_step("a", directives=directives), _make_step("b")]
        self._register_wf("dir-start", {
            "name": "dir-start", "description": "t", "category": "t",
            "output_format": "text", "steps": steps,
        })
        r = call_tool("start_workflow", {"workflow_type": "dir-start", "context": "test"})
        assert r["directives"] == directives
