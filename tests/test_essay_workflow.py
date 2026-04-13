"""End-to-end tests for mikros essay workflow."""

from tests.conftest import call_tool

STEPS = ["explore", "commit", "structure", "draft", "revise", "polish"]


class TestEssayHappyPath:
    """Happy path: start -> submit all 6 steps -> generate text artifact."""

    def test_happy_path(self):
        r = call_tool("start_workflow", {"workflow_type": "essay", "context": "write about solitude"})
        assert "session_id" in r
        assert r["current_step"]["id"] == "explore"
        assert "Do NOT" in r["directive"]
        sid = r["session_id"]

        for i, step_id in enumerate(STEPS):
            r = call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": f"essay-{step_id}"})
            assert r["submitted"]["id"] == step_id
            assert r["progress"] == f"step {i + 1} of 6 complete"

            if i < len(STEPS) - 1:
                assert r["next_step"]["id"] == STEPS[i + 1]
                assert "directive" in r
                assert "gates" in r
            else:
                assert r["status"] == "workflow_complete"

        # Generate artifact — auto returns last step only
        art = call_tool("generate_artifact", {"session_id": sid})
        assert art["output_format"] == "auto"
        assert art["artifact"] == "essay-polish"


class TestEssayOutOfOrder:
    """Out-of-order submission rejected."""

    def test_out_of_order_rejected(self):
        r = call_tool("start_workflow", {"workflow_type": "essay", "context": "test"})
        sid = r["session_id"]
        # Try submitting 'commit' when 'explore' is current
        r = call_tool("submit_step", {"session_id": sid, "step_id": "commit", "content": "nope"})
        assert "error" in r
        assert "Out-of-order" in r["error"]
        assert r["expected_step"] == "explore"


class TestEssayDirectiveContent:
    """Verify essay.yaml directives have real content and domain-specific Do NOT rules."""

    def test_directives_have_do_not(self):
        r = call_tool("start_workflow", {"workflow_type": "essay", "context": "test"})
        assert "PLACEHOLDER" not in r["directive"]
        assert "Do NOT" in r["directive"]
        sid = r["session_id"]

        for step_id in STEPS:
            sub = call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": "x"})
            if "directive" in sub:
                assert "PLACEHOLDER" not in sub["directive"]
                assert "Do NOT" in sub["directive"]


class TestEssayTextArtifact:
    """Verify generate_artifact returns concatenated text, not structured_code."""

    def test_text_format(self):
        r = call_tool("start_workflow", {"workflow_type": "essay", "context": "test"})
        sid = r["session_id"]
        for step_id in STEPS:
            call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": f"part-{step_id}"})

        art = call_tool("generate_artifact", {"session_id": sid, "output_format": "text"})
        assert art["output_format"] == "text"
        assert isinstance(art["artifact"], str)
        # Text format joins with double newline
        assert "part-explore" in art["artifact"]
        assert "part-polish" in art["artifact"]

    def test_auto_format_returns_last_step(self):
        r = call_tool("start_workflow", {"workflow_type": "essay", "context": "test"})
        sid = r["session_id"]
        for step_id in STEPS:
            call_tool("submit_step", {"session_id": sid, "step_id": step_id, "content": f"auto-{step_id}"})

        art = call_tool("generate_artifact", {"session_id": sid, "output_format": "auto"})
        assert art["output_format"] == "auto"
        assert art["artifact"] == "auto-polish"
