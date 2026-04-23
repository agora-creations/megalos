"""Subprocess-driven tests for the dry-run CLI bootstrap entry point.

Each test spawns ``python -m megalos_server.dryrun`` as a subprocess so
the __main__ guard and env-var ordering discipline are exercised in the
same shape as production invocation. One in-process test
(``test_loop_invariant_same_step_id_for_retries``) monkeypatches the
MCP ``call_tool`` surface to pin the D039 client-side loop invariant.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "workflows"
CANONICAL_FIXTURE = FIXTURES_DIR / "canonical.yaml"
DEMO_VALIDATION_FIXTURE = FIXTURES_DIR / "demo_validation.yaml"

# Schema-failing payload (missing `confirmed`, fewer than 3 goals, short title).
_INVALID_JSON = json.dumps({"title": "xy", "goals": ["only one"]})
# Schema-valid payload for `collect_info` step of demo_validation.yaml.
_VALID_JSON = json.dumps(
    {"title": "Project X", "goals": ["a", "b", "c"], "confirmed": True}
)
_VALIDATION_HINT = (
    "Submit JSON with title (string, 3+ chars), goals (array of 3+ strings), "
    "and confirmed (must be boolean true)."
)


def _run(
    args: list[str], input: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "megalos_server.dryrun", *args],
        capture_output=True,
        text=True,
        input=input,
    )


def test_help_exits_zero() -> None:
    result = _run(["--help"])
    assert result.returncode == 0
    assert "--help" in result.stdout


def test_nonexistent_path_errors_cleanly(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    result = _run([str(missing)])
    assert result.returncode == 1
    assert "Workflow file not found" in result.stderr


def test_no_sessions_db_writes(tmp_path: Path) -> None:
    # canonical.yaml has 3 steps; see tests/fixtures/workflows/canonical.yaml
    target = tmp_path / "canonical.yaml"
    shutil.copy(CANONICAL_FIXTURE, target)
    sessions_db = Path("server/megalos_sessions.db")
    pre_exists = sessions_db.exists()
    pre_stat = sessions_db.stat() if pre_exists else None
    result = _run([str(target)], input="ok\n" * 3)
    assert result.returncode == 0, result.stderr
    if pre_exists:
        assert sessions_db.exists()
        post_stat = sessions_db.stat()
        assert pre_stat is not None
        assert post_stat.st_mtime == pre_stat.st_mtime
        assert post_stat.st_size == pre_stat.st_size
    else:
        assert not sessions_db.exists()


def test_broken_sibling_produces_framed_error(tmp_path: Path) -> None:
    target = tmp_path / "canonical.yaml"
    shutil.copy(CANONICAL_FIXTURE, target)
    broken = tmp_path / "broken.yaml"
    # Valid YAML, invalid schema: call-target cross-check fails. The
    # cross-check error embeds the workflow name ('broken') so the raw
    # exception passes through a sibling-identifying string, which the
    # Approach E framing paragraph hands to the user unmodified.
    broken.write_text(
        "name: broken\n"
        "description: Sibling workflow with invalid schema.\n"
        "category: test\n"
        "output_format: structured_code\n"
        "steps:\n"
        "  - id: s1\n"
        "    title: S1\n"
        "    call: nonexistent_workflow\n",
        encoding="utf-8",
    )
    result = _run([str(target)])
    assert result.returncode == 1
    assert "dry-run loads all *.yaml files" in result.stderr
    # Raw exception passes through and identifies the broken workflow by name.
    assert "broken" in result.stderr


def test_broken_target_produces_framed_error(tmp_path: Path) -> None:
    target = tmp_path / "bad_target.yaml"
    # Valid YAML, invalid schema: call-target cross-check fails. The
    # cross-check error embeds the workflow name ('bad_target') which
    # passes through the Approach E framing so the user can identify
    # the failing workflow.
    target.write_text(
        "name: bad_target\n"
        "description: Target workflow with invalid schema.\n"
        "category: test\n"
        "output_format: structured_code\n"
        "steps:\n"
        "  - id: s1\n"
        "    title: S1\n"
        "    call: nonexistent_workflow\n",
        encoding="utf-8",
    )
    result = _run([str(target)])
    assert result.returncode != 0
    assert "dry-run loads all *.yaml files" in result.stderr
    # Target path in framing + workflow name in raw exception.
    assert str(target.parent) in result.stderr
    assert "bad_target" in result.stderr


def test_canonical_fixture_runs_end_to_end(tmp_path: Path) -> None:
    target = tmp_path / "canonical.yaml"
    shutil.copy(CANONICAL_FIXTURE, target)
    # canonical.yaml has 3 steps; see tests/fixtures/workflows/canonical.yaml
    result = _run([str(target)], input="ok\nok\nok\n")
    assert result.returncode == 0, result.stderr
    assert "alpha" in result.stdout
    assert "bravo" in result.stdout
    assert "charlie" in result.stdout
    assert "Workflow complete" in result.stdout


def test_stdin_eof_exits_nonzero(tmp_path: Path) -> None:
    target = tmp_path / "canonical.yaml"
    shutil.copy(CANONICAL_FIXTURE, target)
    result = _run([str(target)], input="")
    assert result.returncode != 0
    assert "Dry-run aborted by user (EOF)" in result.stderr


# ---- S02: validation_error re-prompt + gates rendering ---------------------


def test_validation_retry_loop_advances_on_valid(tmp_path: Path) -> None:
    target = tmp_path / "demo_validation.yaml"
    shutil.copy(DEMO_VALIDATION_FIXTURE, target)
    # stdin: one schema-failing, then valid (advance), then any line for step 2.
    stdin = f"{_INVALID_JSON}\n{_VALID_JSON}\nsummary line\n"
    result = _run([str(target)], input=stdin)
    assert result.returncode == 0, result.stderr
    # Both step banners rendered on stdout.
    assert "collect_info" in result.stdout
    assert "summarize" in result.stdout
    # Validation-error surface on stderr.
    assert "Validation failed:" in result.stderr
    assert "Retries remaining: 2" in result.stderr
    assert _VALIDATION_HINT in result.stderr


def test_validation_budget_exhaustion_exits_nonzero(tmp_path: Path) -> None:
    target = tmp_path / "demo_validation.yaml"
    shutil.copy(DEMO_VALIDATION_FIXTURE, target)
    # Three schema-failing submissions — max_retries=3 exhausts.
    stdin = f"{_INVALID_JSON}\n{_INVALID_JSON}\n{_INVALID_JSON}\n"
    result = _run([str(target)], input=stdin)
    assert result.returncode == 1
    assert "Max retries (3) exceeded" in result.stderr
    # Step 2 banner must NOT appear — no advance on exhaustion.
    assert "summarize" not in result.stdout


def test_gates_rendered_at_step_entry(tmp_path: Path) -> None:
    target = tmp_path / "demo_validation.yaml"
    shutil.copy(DEMO_VALIDATION_FIXTURE, target)
    stdin = f"{_VALID_JSON}\nsummary line\n"
    result = _run([str(target)], input=stdin)
    assert result.returncode == 0, result.stderr
    assert "Gates:" in result.stdout
    # Step 1 gates (3 bullets).
    assert "- User provided project title" in result.stdout
    assert "- User listed at least three goals" in result.stdout
    assert "- User confirmed the information" in result.stdout
    # Step 2 gate (1 bullet).
    assert "- Summary is clear and concise" in result.stdout


def test_validation_hint_rendered_verbatim(tmp_path: Path) -> None:
    target = tmp_path / "demo_validation.yaml"
    shutil.copy(DEMO_VALIDATION_FIXTURE, target)
    stdin = f"{_INVALID_JSON}\n{_VALID_JSON}\nsummary line\n"
    result = _run([str(target)], input=stdin)
    assert result.returncode == 0, result.stderr
    # Verbatim — no paraphrase, no ellipsis.
    assert _VALIDATION_HINT in result.stderr


def test_loop_invariant_same_step_id_for_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """D039 client-side invariant: on validation_error, re-prompt submits the
    SAME ``step_id``; no local retry mutation. Option (a): record every
    ``call_tool`` invocation and assert the submit_step sequence pins
    step_id=collect_info exactly N+1 times (1 retry -> 2 submits) before any
    submit_step with step_id=summarize.
    """
    target = tmp_path / "demo_validation.yaml"
    shutil.copy(DEMO_VALIDATION_FIXTURE, target)

    # In-process import — subprocess boundary can't monkeypatch the MCP layer.
    # Env-var ordering matches production: the module sets MEGALOS_DB_PATH
    # at top level, before any megalos_server imports.
    import importlib

    import megalos_server.dryrun as dryrun_mod

    importlib.reload(dryrun_mod)

    from megalos_server import create_app as real_create_app

    calls: list[tuple[str, dict[str, Any]]] = []

    def recording_create_app(*args: Any, **kwargs: Any) -> Any:
        mcp = real_create_app(*args, **kwargs)
        real_call_tool = mcp.call_tool
        # FastMCP re-invokes call_tool recursively through middleware. Use a
        # reentrancy counter so we record only the operator-initiated (outermost)
        # invocation, not the middleware pass-through.
        depth = {"n": 0}

        async def wrapped_call_tool(
            name: str, arguments: dict[str, Any], *args: Any, **kwargs: Any
        ) -> Any:
            if depth["n"] == 0:
                calls.append((name, dict(arguments)))
            depth["n"] += 1
            try:
                return await real_call_tool(name, arguments, *args, **kwargs)
            finally:
                depth["n"] -= 1

        mcp.call_tool = wrapped_call_tool  # type: ignore[method-assign]
        return mcp

    monkeypatch.setattr(dryrun_mod, "create_app", recording_create_app)
    monkeypatch.setattr(sys, "argv", ["megalos-dryrun", str(target)])

    # Feed stdin: one invalid (triggers validation_error), then one valid
    # (advance), then line for step 2.
    stdin_lines = iter([_INVALID_JSON, _VALID_JSON, "summary"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(stdin_lines))

    with pytest.raises(SystemExit) as exc_info:
        dryrun_mod.main()
    assert exc_info.value.code == 0

    submit_calls = [args for (name, args) in calls if name == "submit_step"]
    # 2 submissions on collect_info (1 retry + 1 valid), then 1 on summarize.
    collect_submits = [c for c in submit_calls if c["step_id"] == "collect_info"]
    summarize_submits = [c for c in submit_calls if c["step_id"] == "summarize"]
    assert len(collect_submits) == 2, submit_calls
    assert len(summarize_submits) == 1, submit_calls
    # Ordering: all collect_info submits precede any summarize submit.
    first_summarize_idx = next(
        i for i, c in enumerate(submit_calls) if c["step_id"] == "summarize"
    )
    assert all(
        c["step_id"] == "collect_info" for c in submit_calls[:first_summarize_idx]
    )
