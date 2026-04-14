"""End-to-end tests for megalos MCP workflow tools."""

from tests.conftest import call_tool

STEPS = ["alpha", "bravo", "charlie"]


class TestFullWorkflow:
    """Happy path: start -> submit all steps -> generate artifact."""

    def test_happy_path(self):
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "build a CLI"})
        assert "session_id" in r
        assert r["current_step"]["id"] == "alpha"
        assert "Do NOT" in r["directive"]
        sid = r["session_id"]

        for i, step_id in enumerate(STEPS):
            r = call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": f"content-{step_id}"})
            assert r["submitted"]["id"] == step_id
            assert r["progress"] == f"step {i + 1} of 3 complete"

            if i < len(STEPS) - 1:
                assert r["next_step"]["id"] == STEPS[i + 1]
                assert "directive" in r
                assert "gates" in r
            else:
                assert r["status"] == "workflow_complete"

        # Verify final state
        st = call_tool("get_state", {"session_id": sid})
        assert st["progress"] == "unknown"  # __complete__ has no index
        assert len(st["step_data"]) == 3

        # Generate artifact — auto returns last step only
        art = call_tool("generate_artifact", {"session_id": sid})
        assert art["output_format"] == "auto"
        assert art["artifact"] == "content-charlie"

        # Explicit structured_code still returns all steps
        art2 = call_tool("generate_artifact", {"session_id": sid, "output_format": "structured_code"})
        assert art2["output_format"] == "structured_code"
        assert len(art2["artifact"]) == 3
        for step_id in STEPS:
            contents = [s["content"] for s in art2["artifact"]]
            assert f"content-{step_id}" in contents


class TestGateEnforcement:
    """Out-of-order and premature artifact rejection."""

    def test_out_of_order_rejected(self):
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]
        # Try submitting 'bravo' when 'alpha' is current
        r = call_tool("submit_step", {"session_id": sid, "step_id": "bravo", "content": "nope"})
        assert "error" in r
        assert "Out-of-order" in r["error"]
        assert r["expected_step"] == "alpha"

    def test_premature_artifact_rejected(self):
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]
        r = call_tool("generate_artifact", {"session_id": sid})
        assert "error" in r
        assert "not complete" in r["error"].lower() or "Finish all steps" in r["error"]
        assert "remaining_steps" in r


class TestEdgeCases:
    """Unknown workflow, invalid session."""

    def test_unknown_workflow(self):
        r = call_tool("start_workflow", {"workflow_type": "nonexistent", "context": "x"})
        assert "error" in r
        assert "available_types" in r

    def test_invalid_session(self):
        r = call_tool("get_state", {"session_id": "bogus123"})
        assert "error" in r

    def test_get_guidelines(self):
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        sid = r["session_id"]
        g = call_tool("get_guidelines", {"session_id": sid})
        assert g["current_step"]["id"] == "alpha"
        assert len(g["anti_patterns"]) > 0
        assert len(g["gates"]) > 0


class TestDirectiveContent:
    """Verify canonical fixture directives include 'Do NOT' markers (smoke check on injected fixture)."""

    def test_no_placeholders(self):
        r = call_tool("start_workflow", {"workflow_type": "canonical", "context": "test"})
        assert "PLACEHOLDER" not in r["directive"]
        sid = r["session_id"]
        for step_id in STEPS:
            sub = call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": "x"})
            if "directive" in sub:
                assert "PLACEHOLDER" not in sub["directive"]
                assert "Do NOT" in sub["directive"]
