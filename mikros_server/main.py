"""mikros MCP server entrypoint — default app + CLI with --workflow-dir override."""

import argparse

from mikros_server import create_app

# Module-level app for FastMCP CLI / Horizon entrypoint resolution.
mcp = create_app()

# Tests import and mutate WORKFLOWS — share the same dict register_tools closed over.
WORKFLOWS: dict[str, dict] = mcp._mikros_workflows  # type: ignore[attr-defined]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-dir", default=None, help="Directory containing workflow YAML files.")
    args = parser.parse_args()
    if args.workflow_dir:
        mcp = create_app(workflow_dir=args.workflow_dir)
    # FastMCP reads FASTMCP_HOST / FASTMCP_PORT from env automatically.
    mcp.run(transport="streamable-http")  # type: ignore[arg-type]
