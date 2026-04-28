# megalos-server configuration

Operational reference for environment variables and HTTP-route conventions
exposed by the megalos MCP server. Keep entries terse — one paragraph plus a
default and a "when to set it" note is enough for most knobs.

## Environment variables

### `MEGALOS_DEV_CORS`

- **Default:** unset (CORS middleware NOT registered).
- **Accepted values:** `true` to enable; anything else (or unset) leaves it off.
- **When to set:** local development only — when running the agorá UI dev
  server (`npm run dev`, default port 5173) cross-origin against a
  megalos-server bound on `127.0.0.1:8000`.
- **Effect when enabled:** registers Starlette's `CORSMiddleware` with
  `allow_origins=["http://localhost:5173"]`,
  `allow_methods=["GET", "POST", "OPTIONS"]`, and the headers an
  MCP-over-HTTP client needs (`Content-Type`, `MCP-Session-Id`,
  `Mcp-Protocol-Version`, `Authorization`). Emits a one-shot warning at
  startup so an operator who set it accidentally notices.
- **Production rule:** MUST NOT be set. There is no production scenario
  where the megalos server should be CORS-permissive — the agorá SPA is
  served same-origin from `/` by the same process. CI smoke tests assert
  CORS is off by default.

### `FASTMCP_HOST` / `FASTMCP_PORT`

Read directly by FastMCP's HTTP transport. Defaults to `127.0.0.1:8000`.
Override only when binding for non-default network access (e.g. running
inside a container with `0.0.0.0`). Setting `MEGALOS_DEV_CORS=true` while
listening on `0.0.0.0` is a configuration smell — the warning log
flagging CORS-on is the operator's cue.

## HTTP route precedence

The megalos server serves three concerns through one Starlette app:

| Path                | Owner                     | Purpose                                 |
|---------------------|---------------------------|-----------------------------------------|
| `/mcp`              | FastMCP transport         | MCP-over-HTTP (streamable-http).        |
| `/_/healthz`        | `static_handler`          | Liveness probe — returns `{"status":"ok"}`. |
| `/_/<future>`       | `static_handler` (future) | Ops surfaces (readyz, metrics, …).      |
| `/assets/...`       | `static_handler`          | Vite bundle assets (StaticFiles mount). |
| `/{path:path}`      | `static_handler`          | SPA history-mode catch-all.             |

Starlette routes are matched **first match wins**. The route table in
`megalos_server/static_handler.py::build_routes` is therefore ordered
deliberately:

1. `/_/healthz` (and any future `/_/*` exact routes) BEFORE the catch-all.
2. `/assets/*` mount BEFORE the catch-all.
3. `/{path:path}` SPA catch-all LAST.

FastMCP appends these routes after its own `/mcp` route in
`_additional_http_routes`, so `/mcp` always wins over the catch-all.

### Adding a new ops surface (`/_/readyz`, `/_/metrics`, …)

Register it as an exact `Route` inside `build_routes()`, **before** the
SPA catch-all. Never co-locate ops endpoints next to `/mcp` (path
collisions with FastMCP's transport are silent and dangerous), and never
register them after the catch-all (the catch-all swallows them and
returns `index.html` instead of your handler's response).

### Missing-bundle behaviour

When `megalos_server/static_ui/` is empty (e.g. a source checkout where
`scripts/build-agora-ui.sh` has not been run), the catch-all returns a
graceful **503** with a plain-text "UI bundle missing" message rather
than a 500 stack trace. `/mcp` and `/_/healthz` continue to work — the
server stays useful as an MCP transport even without the SPA.
