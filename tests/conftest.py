"""Shared test fixtures for megalos MCP tests."""

import asyncio
import os

import pytest  # type: ignore[import-not-found]

from megalos_server import db
from megalos_server.main import mcp, WORKFLOWS
from megalos_server.schema import load_workflow

# Register the canonical 6-step framework test fixture so framework-level
# tests have a stable target after the M007 production-workflow split.
_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "workflows", "canonical.yaml"
)
WORKFLOWS["canonical"] = load_workflow(_FIXTURE_PATH)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Every test runs against its own file-backed SQLite DB in tmp_path.
    Required because FastMCP dispatches handlers through asyncio's executor —
    cross-thread visibility needs a real file, not :memory:."""
    monkeypatch.setenv("MEGALOS_DB_PATH", str(tmp_path / "test_session.db"))
    db._reset_for_test()
    yield
    db._reset_for_test()


def call_tool(tool_name, args):
    """Sync wrapper around mcp.call_tool — returns the structured dict."""
    result = asyncio.run(mcp.call_tool(tool_name, args))
    return result.structured_content
