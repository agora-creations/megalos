"""Replay-diff regression: dormant fingerprint scaffolding must produce
byte-identical MCP responses to the pre-scaffolding baseline.

This test is the *permanent* guard on ADR-001's T01 "dormant" property
(see ``docs/adr/001-workflow-versioning.md`` § Decision). It pins a
scripted session lifecycle against a golden JSON file captured the day
T01 landed. Any future change — refactor, migration, envelope edit —
that alters a session-touching tool response before T02 activates the
runtime's fingerprint-mismatch behaviour will trip this test.

Scripted lifecycle (5 MCP calls against the ``canonical`` fixture):

    1. start_workflow     → returns session_id + first directive
    2. get_state          → confirms session at step 'alpha'
    3. submit_step alpha  → advances to 'bravo'
    4. get_state          → confirms session at step 'bravo'
    5. submit_step bravo  → advances to 'charlie'

The replay redacts fields that are legitimately non-deterministic across
runs (session_id, fingerprints derived from it, timestamps) before
comparison. Everything else — status codes, step metadata, directive
text, the exact list of keys in each envelope — is compared byte-for-
byte against the golden. If a future change needs to alter any of the
non-redacted surface, this test has to be re-pinned deliberately (delete
the golden, re-run, commit). That is the intended friction.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from megalos_server import state
from tests.conftest import call_tool

_GOLDEN_PATH = (
    Path(__file__).parent / "fixtures" / "fingerprint_dormant_replay.golden.json"
)

# Opaque 48-char hex fingerprints (sha256 truncated to 12 hex chars).
_FP_RE = re.compile(r"^[0-9a-f]{12}$")
# Opaque ISO-8601 timestamps with UTC offset; canonicalise to a literal.
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}$")


def _redact(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Recursively replace non-deterministic values with stable tokens.

    Targeted fields:
      session_id           → "<SESSION_ID>"
      session_fingerprint  → "<SESSION_FP>"
      fingerprint          → "<SESSION_FP>" (state.get_session output)
      created_at           → "<TIMESTAMP>"
      updated_at           → "<TIMESTAMP>"
      completed_at         → "<TIMESTAMP>"
    Structure-preserving; non-targeted strings, numbers, bools pass through.
    """
    if isinstance(value, dict):
        return {k: _redact(v, path + (k,)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, path) for v in value]
    if isinstance(value, str):
        last = path[-1] if path else ""
        if last in {"session_id", "parent_session_id", "under_session_id"}:
            return "<SESSION_ID>" if value else value
        if last in {"session_fingerprint", "fingerprint"}:
            # Length check guards against redacting future fields that happen
            # to share the key name but carry a different shape (e.g. the
            # full-width SHA-256 workflow fingerprint that ADR-001 adds in
            # T02 for the envelope keys session_fingerprint /
            # previous_fingerprint / current_fingerprint).
            if _FP_RE.match(value):
                return "<SESSION_FP>"
            return value
        if last in {"created_at", "updated_at", "completed_at"}:
            return "<TIMESTAMP>" if _ISO_RE.match(value) else value
    return value


def _script_lifecycle() -> list[dict]:
    """Execute the scripted five-call lifecycle against the canonical
    fixture and return the redacted response sequence."""
    captures: list[dict] = []

    r1 = call_tool("start_workflow", {"workflow_type": "canonical", "context": "replay-diff"})
    captures.append({"call": "start_workflow", "response": _redact(r1)})

    sid = r1["session_id"]

    r2 = call_tool("get_state", {"session_id": sid})
    captures.append({"call": "get_state", "response": _redact(r2)})

    r3 = call_tool(
        "submit_step",
        {"session_id": sid, "step_id": "alpha", "content": "alpha done"},
    )
    captures.append({"call": "submit_step_alpha", "response": _redact(r3)})

    r4 = call_tool("get_state", {"session_id": sid})
    captures.append({"call": "get_state_after_alpha", "response": _redact(r4)})

    r5 = call_tool(
        "submit_step",
        {"session_id": sid, "step_id": "bravo", "content": "bravo done"},
    )
    captures.append({"call": "submit_step_bravo", "response": _redact(r5)})

    return captures


def test_dormant_replay_is_byte_identical_to_golden():
    state.clear_sessions()
    captured = _script_lifecycle()

    if not _GOLDEN_PATH.exists():
        # Seeding path: write the golden, then require the operator to
        # commit it and re-run. This is the intended friction when an
        # intentional surface change lands.
        _GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _GOLDEN_PATH.write_text(
            json.dumps(captured, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        raise AssertionError(
            f"Golden file did not exist; wrote {_GOLDEN_PATH}. Inspect, "
            "commit, and re-run. If the diff is intentional this is the "
            "point at which to re-pin the contract."
        )

    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    # Compare via canonical JSON so dict-key ordering drift does not show
    # up as a false positive.
    captured_canon = json.dumps(captured, indent=2, sort_keys=True, ensure_ascii=False)
    golden_canon = json.dumps(golden, indent=2, sort_keys=True, ensure_ascii=False)
    assert captured_canon == golden_canon, (
        "Replay-diff mismatch — a session-touching tool response has changed "
        "under T01 dormant scaffolding. ADR-001 requires zero behavioural "
        "change visible to MCP clients in T01. If this change is intentional, "
        f"delete {_GOLDEN_PATH} and re-run to re-pin."
    )
