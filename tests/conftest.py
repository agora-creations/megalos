"""Shared test fixtures for mikros MCP tests."""

import asyncio
import os

from mikros_server.main import mcp
from mikros_server.main import WORKFLOWS
from mikros_server.schema import load_workflow

# Register the canonical 6-step framework test fixture so framework-level
# tests have a stable target after the M007 production-workflow split.
_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "workflows", "canonical.yaml"
)
WORKFLOWS["canonical"] = load_workflow(_FIXTURE_PATH)


def call_tool(tool_name, args):
    """Sync wrapper around mcp.call_tool — returns the structured dict."""
    result = asyncio.run(mcp.call_tool(tool_name, args))
    return result.structured_content
