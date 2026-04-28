#!/usr/bin/env bash
# Clean-venv wheel smoke (D065 — Layer 3 dev workflow).
#
# Builds the agorá UI bundle, builds a megalos-server wheel, installs it into
# a fresh tempdir venv, boots the server on a random free port, asserts four
# production-shape invariants, and tears everything down.
#
# Exit 0 = all assertions PASS. Non-zero = at least one FAIL.
#
# Assertions (each prints PASS/FAIL on its own line):
#   1. GET /            -> 200 + body contains the SPA <title> marker.
#   2. GET /_/healthz   -> 200.
#   3. POST /mcp        -> JSON-RPC initialize returns valid response.
#   4. CORS-OFF guard   -> Access-Control-Allow-Origin header absent on /.
#
# Why this exists: catches package-data declaration regressions, missing
# wheel imports, and accidental CORS-on defaults that Layer 1 (Vite dev)
# and Layer 2 (source-tree boot) cannot see.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

FAIL=0
SERVER_PID=""
TMP=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  if [[ -n "${TMP}" && -d "${TMP}" ]]; then
    rm -rf "${TMP}"
  fi
}
trap cleanup EXIT

pass() { echo "  PASS $1"; }
fail() { echo "  FAIL $1 — $2"; FAIL=1; }

echo "==> Building agorá UI bundle"
bash scripts/build-agora-ui.sh

echo "==> Building megalos-server wheel"
rm -rf dist
uv build --wheel >/dev/null
WHEEL="$(ls dist/megalos_server-*.whl | tail -1)"
echo "    wheel: ${WHEEL}"

echo "==> Creating clean venv + installing wheel"
TMP="$(mktemp -d -t megalos-smoke.XXXXXX)"
uv venv "${TMP}/venv" >/dev/null
# uv pip install reads VIRTUAL_ENV; set it so the wheel lands in the tempdir venv.
VIRTUAL_ENV="${TMP}/venv" uv pip install --quiet "${WHEEL}"

PYBIN="${TMP}/venv/bin/python"

PORT="$("${PYBIN}" -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')"
echo "==> Booting server on 127.0.0.1:${PORT}"

# Boot from the wheel-installed venv. main.py uses absolute imports so
# `python -m megalos_server.main` resolves cleanly.
FASTMCP_HOST=127.0.0.1 FASTMCP_PORT="${PORT}" \
  "${PYBIN}" -m megalos_server.main >"${TMP}/server.log" 2>&1 &
SERVER_PID=$!

# Poll /_/healthz until 200 (max ~10s). Robust against slow CI boots.
HEALTH_URL="http://127.0.0.1:${PORT}/_/healthz"
READY=0
for _ in $(seq 1 50); do
  if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.2
done
if [[ "${READY}" -ne 1 ]]; then
  echo "    server failed to come up. log:"
  sed 's/^/    | /' "${TMP}/server.log"
  fail "boot" "server did not become ready within ~10s"
  exit 1
fi

echo "==> Running assertions"

# 1. GET / -> 200 + SPA marker.
ROOT_BODY="$(curl -sS -w '\n__STATUS__:%{http_code}' "http://127.0.0.1:${PORT}/")"
ROOT_STATUS="${ROOT_BODY##*__STATUS__:}"
ROOT_BODY="${ROOT_BODY%__STATUS__:*}"
if [[ "${ROOT_STATUS}" == "200" ]] && grep -q '<title>agorá' <<<"${ROOT_BODY}"; then
  pass "GET / 200 + SPA <title>agorá marker"
else
  fail "GET /" "status=${ROOT_STATUS} marker-found=$(grep -c '<title>agorá' <<<"${ROOT_BODY}")"
fi

# 2. GET /_/healthz -> 200.
HZ_STATUS="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/_/healthz")"
if [[ "${HZ_STATUS}" == "200" ]]; then
  pass "GET /_/healthz 200"
else
  fail "GET /_/healthz" "status=${HZ_STATUS}"
fi

# 3. POST /mcp JSON-RPC initialize -> valid response (200, body contains "result"
#    or "jsonrpc"). MCP streamable-http accepts JSON or SSE; either works.
MCP_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke-wheel","version":"0.0.0"}}}'
MCP_RESP="$(curl -sS -X POST "http://127.0.0.1:${PORT}/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d "${MCP_PAYLOAD}" \
  -w '\n__STATUS__:%{http_code}')"
MCP_STATUS="${MCP_RESP##*__STATUS__:}"
MCP_BODY="${MCP_RESP%__STATUS__:*}"
if [[ "${MCP_STATUS}" == "200" ]] && grep -q '"jsonrpc"' <<<"${MCP_BODY}"; then
  pass "POST /mcp initialize 200 + jsonrpc body"
else
  fail "POST /mcp" "status=${MCP_STATUS} body=$(head -c 200 <<<"${MCP_BODY}")"
fi

# 4. CORS-OFF guard: Access-Control-Allow-Origin MUST be absent on default boot.
HEADERS="$(curl -sI "http://127.0.0.1:${PORT}/")"
if grep -qi '^access-control-allow-origin' <<<"${HEADERS}"; then
  fail "CORS-OFF guard" "Access-Control-Allow-Origin present (production must never ship CORS-permissive)"
else
  pass "CORS-OFF guard (Access-Control-Allow-Origin absent)"
fi

if [[ "${FAIL}" -ne 0 ]]; then
  echo "==> smoke-wheel FAILED"
  echo "    server log tail:"
  tail -n 40 "${TMP}/server.log" | sed 's/^/    | /'
  exit 1
fi

echo "==> smoke-wheel OK"
