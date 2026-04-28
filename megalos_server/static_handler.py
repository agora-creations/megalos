"""Static-route handler + ops namespace + CORS gate (D064 / D065).

This module produces the route table that wraps the FastMCP `/mcp` endpoint:

    /mcp                  — FastMCP streamable-http (registered by FastMCP itself)
    /_/healthz            — first ops-namespace surface; returns {"status": "ok"}
    /assets/...           — Vite bundle assets (StaticFiles mount)
    /{path:path}          — SPA history-mode catch-all (returns index.html)

Route precedence is "first match wins" in Starlette. Ops surfaces under
``/_/*`` MUST be registered as exact routes BEFORE the SPA catch-all so the
catch-all does not swallow them. New ops endpoints (readyz, metrics, …) get
appended next to ``/_/healthz`` in :func:`build_routes`.

The SPA bundle lives at ``megalos_server/static_ui/`` and is produced by
``scripts/build-agora-ui.sh`` — it is gitignored as a build artifact and
shipped via ``[tool.setuptools.package-data]``. If the bundle is missing
(e.g. a source checkout without a build), the catch-all returns a graceful
503 instead of crashing.

CORS is gated by the ``MEGALOS_DEV_CORS=true`` envvar. Default OFF: production
must NEVER ship with CORS-permissive defaults. When enabled, only the Vite
dev origin (``http://localhost:5173``) is allowed.
"""

from __future__ import annotations

import logging
import os
from importlib.resources import files
from pathlib import Path
from typing import Any

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import BaseRoute, Mount, Route
from starlette.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# Sentinel envvar value that flips CORS on (only ever for local dev).
_DEV_CORS_ENVVAR = "MEGALOS_DEV_CORS"
_VITE_DEV_ORIGIN = "http://localhost:5173"


def _resolve_static_ui_path() -> Path:
    """Resolve the on-disk path to the bundled ``static_ui/`` directory.

    Uses :mod:`importlib.resources` so this works both from a source checkout
    (where ``static_ui/`` sits next to ``__init__.py``) and from a wheel-
    installed venv (where it lives inside the installed package).

    Returns the resolved :class:`Path` whether or not it exists — callers
    must check ``index.html`` presence and degrade gracefully if missing.
    """
    return Path(str(files("megalos_server").joinpath("static_ui")))


async def healthz_endpoint(request: Request) -> Response:  # noqa: ARG001
    """First ops-namespace surface. Returns 200 + ``{"status": "ok"}``."""
    return JSONResponse({"status": "ok"})


def _spa_catchall_factory(static_ui_path: Path) -> Any:
    """Build the SPA catch-all endpoint bound to a resolved static_ui path."""

    async def spa_catchall(request: Request) -> Response:  # noqa: ARG001
        index_path = static_ui_path / "index.html"
        if not index_path.is_file():
            logger.warning(
                "static_ui/index.html missing at %s — returning 503. "
                "Run scripts/build-agora-ui.sh from the megalos repo root "
                "to populate the bundle.",
                index_path,
            )
            return Response(
                "UI bundle missing — run scripts/build-agora-ui.sh from the "
                "megalos repo root.",
                status_code=503,
                media_type="text/plain",
            )
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    return spa_catchall


def build_routes() -> list[BaseRoute]:
    """Return the static-handler routes in correct precedence order (D064).

    Order is load-bearing — Starlette matches routes top-to-bottom.

    1. ``/_/healthz`` — exact ops route (future ``/_/*`` surfaces append here).
    2. ``/assets/*``  — Vite bundle assets via :class:`StaticFiles` mount.
    3. ``/{path:path}`` — SPA history-mode catch-all (LAST).

    The FastMCP ``/mcp`` route is registered by FastMCP itself ahead of these
    when the routes returned here are appended to ``mcp._additional_http_routes``.
    """
    static_ui_path = _resolve_static_ui_path()
    assets_path = static_ui_path / "assets"
    routes: list[BaseRoute] = [
        Route("/_/healthz", healthz_endpoint, methods=["GET"]),
    ]
    # StaticFiles refuses to construct on a non-existent dir; only mount when
    # the bundle is present. When absent, the SPA catch-all 503 covers all
    # paths uniformly (assets included).
    if assets_path.is_dir():
        routes.append(Mount("/assets", app=StaticFiles(directory=str(assets_path))))
    # SPA catch-all MUST be last — it matches every remaining GET.
    routes.append(
        Route(
            "/{path:path}",
            _spa_catchall_factory(static_ui_path),
            methods=["GET"],
        )
    )
    return routes


def build_cors_middleware() -> list[Middleware]:
    """Return the CORS middleware list, or empty if ``MEGALOS_DEV_CORS`` unset.

    Gated by ``MEGALOS_DEV_CORS=true``. Default OFF — production must NEVER
    ship with CORS-permissive defaults (D065). Emits a one-shot warning at
    startup when enabled so an operator who set it accidentally notices.

    Allowed origin is hard-coded to the Vite dev server (``http://localhost:5173``);
    methods + headers cover what an MCP-over-HTTP client needs.
    """
    if os.environ.get(_DEV_CORS_ENVVAR, "").lower() != "true":
        return []
    logger.warning(
        "%s=true — CORS enabled for %s. This is for local dev only and "
        "MUST NOT be set in production.",
        _DEV_CORS_ENVVAR,
        _VITE_DEV_ORIGIN,
    )
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=[_VITE_DEV_ORIGIN],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "MCP-Session-Id",
                "Mcp-Protocol-Version",
                "Authorization",
            ],
        )
    ]


__all__ = ["build_routes", "build_cors_middleware"]
