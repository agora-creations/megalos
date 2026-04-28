"""megalos MCP server entrypoint — default app + CLI with --workflow-dir override."""

import argparse

from megalos_server import create_app
from megalos_server.static_handler import build_cors_middleware, build_routes

# Module-level app for FastMCP CLI / Horizon entrypoint resolution.
mcp = create_app()

# Tests import and mutate WORKFLOWS — share the same dict register_tools closed over.
WORKFLOWS: dict[str, dict] = mcp._megalos_workflows  # type: ignore[attr-defined]


def _attach_static_routes(app) -> None:  # type: ignore[no-untyped-def]
    """Append static-handler routes to FastMCP's additional-routes list.

    Route precedence per D064 (first-match-wins in Starlette):
        1. ``/mcp``           — registered by FastMCP itself ahead of everything below.
        2. ``/_/healthz``     — first ops-namespace surface; future ``/_/*`` here.
        3. ``/assets/*``      — Vite bundle StaticFiles mount.
        4. ``/{path:path}``   — SPA history-mode catch-all (LAST).

    New ops surfaces MUST register as exact routes inside ``build_routes`` BEFORE
    the catch-all, never as ad-hoc additions adjacent to ``/mcp`` (path collisions
    with FastMCP's transport are silent and dangerous).
    """
    app._additional_http_routes.extend(build_routes())  # type: ignore[attr-defined]


_attach_static_routes(mcp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflow-dir", default=None, help="Directory containing workflow YAML files."
    )
    args = parser.parse_args()
    if args.workflow_dir:
        mcp = create_app(workflow_dir=args.workflow_dir)
        _attach_static_routes(mcp)
    # FastMCP reads FASTMCP_HOST / FASTMCP_PORT from env automatically.
    # CORS middleware is gated by MEGALOS_DEV_CORS=true (D065). Default OFF.
    mcp.run(  # type: ignore[arg-type]
        transport="streamable-http",
        middleware=build_cors_middleware(),
    )
