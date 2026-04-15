"""Tests for conversation_repair defaults and per-workflow overrides."""

import os
import tempfile

from megalos_server import state
from megalos_server.main import WORKFLOWS
from megalos_server.schema import load_workflow, validate_workflow
from tests.conftest import call_tool


_NO_REPAIR_YAML = """\
name: test_no_repair
description: no conversation_repair block
category: testing
output_format: text
steps:
  - id: s1
    title: Step 1
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
  - id: s2
    title: Step 2
    directive_template: do more
    gates: [done]
    anti_patterns: [none]
"""

_PARTIAL_OVERRIDE_YAML = """\
name: test_partial_override
description: only on_cancel overridden
category: testing
output_format: text
conversation_repair:
  on_cancel: "Custom cancel behavior"
steps:
  - id: s1
    title: Step 1
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
"""

_FULL_OVERRIDE_YAML = """\
name: test_full_override
description: all four keys overridden
category: testing
output_format: text
conversation_repair:
  on_go_back: "Custom go_back"
  on_cancel: "Custom cancel"
  on_digression: "Custom digression"
  on_clarification: "Custom clarification"
steps:
  - id: s1
    title: Step 1
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
"""

_DEFAULTS = {
    "on_go_back": "Guide the user to use revise_step",
    "on_cancel": "Confirm cancellation, then use delete_session",
    "on_digression": "Acknowledge, then redirect to current step",
    "on_clarification": "Re-explain the current step's directive more simply",
}


def _load_and_register(yaml_str, name):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(yaml_str)
        wf = load_workflow(path)
    finally:
        os.unlink(path)
    WORKFLOWS[name] = wf
    return wf


def _start(name, context="test"):
    state.clear_sessions()
    return call_tool("start_workflow", {"workflow_type": name, "context": context})


class TestDefaultsPresent:
    def test_start_workflow_has_defaults(self):
        _load_and_register(_NO_REPAIR_YAML, "test_no_repair")
        r = _start("test_no_repair")
        assert "conversation_repair" in r
        assert r["conversation_repair"] == _DEFAULTS

    def test_submit_step_has_defaults(self):
        _load_and_register(_NO_REPAIR_YAML, "test_no_repair")
        r = _start("test_no_repair")
        sid = r["session_id"]
        r2 = call_tool("submit_step", {"session_id": sid, "step_id": "s1", "content": "x"})
        assert r2["conversation_repair"] == _DEFAULTS

    def test_revise_step_has_defaults(self):
        _load_and_register(_NO_REPAIR_YAML, "test_no_repair")
        r = _start("test_no_repair")
        sid = r["session_id"]
        call_tool("submit_step", {"session_id": sid, "step_id": "s1", "content": "x"})
        rv = call_tool("revise_step", {"session_id": sid, "step_id": "s1"})
        assert rv["conversation_repair"] == _DEFAULTS


class TestPartialOverride:
    def test_only_on_cancel_overridden(self):
        _load_and_register(_PARTIAL_OVERRIDE_YAML, "test_partial_override")
        r = _start("test_partial_override")
        cr = r["conversation_repair"]
        assert cr["on_cancel"] == "Custom cancel behavior"
        assert cr["on_go_back"] == _DEFAULTS["on_go_back"]
        assert cr["on_digression"] == _DEFAULTS["on_digression"]
        assert cr["on_clarification"] == _DEFAULTS["on_clarification"]


class TestFullOverride:
    def test_all_four_overridden(self):
        _load_and_register(_FULL_OVERRIDE_YAML, "test_full_override")
        r = _start("test_full_override")
        assert r["conversation_repair"] == {
            "on_go_back": "Custom go_back",
            "on_cancel": "Custom cancel",
            "on_digression": "Custom digression",
            "on_clarification": "Custom clarification",
        }


class TestLoadTimeValidation:
    def test_unknown_key_rejected(self):
        bad = """\
name: bad
description: bad repair
category: testing
output_format: text
conversation_repair:
  on_cancell: "typo"
steps:
  - id: s1
    title: Step 1
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
"""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(bad)
            errors, _ = validate_workflow(path)
            assert any("on_cancell" in e for e in errors), errors
        finally:
            os.unlink(path)

    def test_non_string_value_rejected(self):
        bad = """\
name: bad
description: non-string value
category: testing
output_format: text
conversation_repair:
  on_cancel: 42
steps:
  - id: s1
    title: Step 1
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
"""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(bad)
            errors, _ = validate_workflow(path)
            assert any("on_cancel" in e and "string" in e for e in errors), errors
        finally:
            os.unlink(path)
