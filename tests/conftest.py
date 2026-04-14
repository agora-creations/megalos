"""Shared test fixtures for mikros MCP tests."""

import asyncio

from mikros_server.main import mcp


def call_tool(tool_name, args):
    """Sync wrapper around mcp.call_tool — returns the structured dict."""
    result = asyncio.run(mcp.call_tool(tool_name, args))
    return result.structured_content
