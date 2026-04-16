#!/usr/bin/env bash
# .mcp.json must exist and be valid JSON.
# Rescued from the deleted test_settings.sh; the rest of that file tested
# mikrós-era hook wiring that no longer exists.
set -e
cd "$(dirname "$0")/.."
source tests/lib/assert.sh

assert_file_exists ".mcp.json" ".mcp.json exists"

TESTS_RUN=$((TESTS_RUN + 1))
if ! jq -e . .mcp.json >/dev/null 2>&1; then
  TESTS_FAILED=$((TESTS_FAILED + 1))
  echo "FAIL: .mcp.json is not valid JSON" >&2
fi

test_summary
