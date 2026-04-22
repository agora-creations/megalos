"""Canonicalisation table for the workflow fingerprint helper.

Pins the load-then-canonical-JSON contract from
``docs/adr/001-workflow-versioning.md``. Guards against silent drift when
the YAML loader is upgraded (PyYAML → ruamel, C-loader swap, version
bump, etc.) by asserting that cosmetic edits never trip the fingerprint
and that semantically meaningful edits always do.

Four rows:
  (a) comment content                  → identical fingerprint
  (b) mapping key order                 → identical fingerprint
  (c) quote style / flow-vs-block       → identical fingerprint
  (d) any runtime-significant edit     → different fingerprint

Plus a backfill-behaviour test that pre-migration rows receive the
sentinel ``"pre-versioning"`` when ``init_schema`` runs over a database
that was created without the column.
"""

from __future__ import annotations

import sqlite3

import pytest  # type: ignore[import-not-found]

from megalos_server import db, state
from megalos_server.schema import workflow_fingerprint

# --- Canonicalisation table ----------------------------------------------

_BASELINE_YAML = """\
name: canonical
description: Synthetic 3-step fingerprint fixture.
category: test
output_format: structured_code
steps:
  - id: alpha
    title: Alpha
    directive_template: Stub directive.
    gates: [done]
    anti_patterns: [skipping]
  - id: bravo
    title: Bravo
    directive_template: Stub directive.
    gates: [done]
    anti_patterns: [skipping]
"""


def test_comment_only_edit_preserves_fingerprint():
    """(a) Comments do not reach the parsed object — fingerprint is stable."""
    commented = (
        "# top-of-file banner, not runtime-significant\n"
        + _BASELINE_YAML
        + "# trailing comment\n"
    )
    assert workflow_fingerprint(_BASELINE_YAML) == workflow_fingerprint(commented)


def test_mapping_key_order_preserves_fingerprint():
    """(b) sort_keys=True collapses key-order differences to one canonical form."""
    reordered = """\
description: Synthetic 3-step fingerprint fixture.
name: canonical
output_format: structured_code
category: test
steps:
  - gates: [done]
    directive_template: Stub directive.
    anti_patterns: [skipping]
    title: Alpha
    id: alpha
  - anti_patterns: [skipping]
    directive_template: Stub directive.
    title: Bravo
    gates: [done]
    id: bravo
"""
    assert workflow_fingerprint(_BASELINE_YAML) == workflow_fingerprint(reordered)


def test_quote_and_flow_style_preserves_fingerprint():
    """(c) Quote style / flow-vs-block do not survive yaml.safe_load."""
    stylised = """\
name: "canonical"
description: 'Synthetic 3-step fingerprint fixture.'
category: test
output_format: structured_code
steps:
  - {id: alpha, title: "Alpha", directive_template: "Stub directive.", gates: [done], anti_patterns: [skipping]}
  - id: "bravo"
    title: 'Bravo'
    directive_template: "Stub directive."
    gates:
      - done
    anti_patterns:
      - skipping
"""
    assert workflow_fingerprint(_BASELINE_YAML) == workflow_fingerprint(stylised)


@pytest.mark.parametrize(
    "mutated",
    [
        # Step rename (id change on a canonicalised step).
        _BASELINE_YAML.replace("id: alpha", "id: alpha_renamed"),
        # output_schema addition — a runtime-significant field surviving the load.
        _BASELINE_YAML.replace(
            "    anti_patterns: [skipping]\n  - id: bravo",
            "    anti_patterns: [skipping]\n    output_schema: {type: object}\n  - id: bravo",
        ),
        # Branch target edit — swap a step's directive text for a demonstrably different one.
        _BASELINE_YAML.replace("Stub directive.", "Stub directive (edited)."),
    ],
)
def test_semantic_edits_change_fingerprint(mutated: str) -> None:
    """(d) Any edit that reaches the parsed object produces a different digest."""
    assert workflow_fingerprint(_BASELINE_YAML) != workflow_fingerprint(mutated)


# --- Backfill sentinel migration -----------------------------------------


def test_pre_versioning_backfill_on_legacy_db(monkeypatch, tmp_path):
    """An existing DB with a sessions row lacking workflow_fingerprint is
    migrated to carry the ``'pre-versioning'`` sentinel on the first call
    to ``init_schema``. Simulates the scenario an operator upgrades to a
    build that includes ADR-001's column before having wiped state."""
    db_path = tmp_path / "legacy.db"
    # Build the legacy table directly — no workflow_fingerprint column.
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            current_step TEXT NOT NULL,
            step_data TEXT NOT NULL DEFAULT '{}',
            retry_counts TEXT NOT NULL DEFAULT '{}',
            step_visit_counts TEXT NOT NULL DEFAULT '{}',
            escalation TEXT,
            artifact_checkpoints TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            called_session TEXT,
            parent_session_id TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO sessions (session_id, workflow_type, current_step, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("legacy-sid", "legacy_wf", "step1", "2026-01-01", "2026-01-01"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("MEGALOS_DB_PATH", str(db_path))
    db._reset_for_test()
    db.init_schema()

    # Connection re-opened through the module; row now carries the sentinel.
    sess = state.get_session("legacy-sid")
    assert sess["workflow_fingerprint"] == "pre-versioning"
    db._reset_for_test()


def test_fingerprint_stamped_from_create_session_kwarg():
    """A fresh session carries exactly the fingerprint create_session was
    handed, not the default sentinel."""
    sid = state.create_session(
        "wf", current_step="s1", workflow_fingerprint="abc123"
    )
    sess = state.get_session(sid)
    assert sess["workflow_fingerprint"] == "abc123"
