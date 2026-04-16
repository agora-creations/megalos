#!/usr/bin/env bash
# Integration test: fresh install -> state files exist -> megalos.py gate works.
set -e
cd "$(dirname "$0")/.."
source tests/lib/assert.sh

HERE="$PWD"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Minimal PATH with only system essentials (no claude/docmancer).
BARE_PATH="/usr/bin:/bin:/usr/sbin:/sbin"

TARGET="$WORK/target"
mkdir -p "$TARGET"
PATH="$BARE_PATH" bash "$HERE/install.sh" "$TARGET" 2>/dev/null

assert_file_exists "$TARGET/.megalos/STATE.md"      "STATE.md seeded"
assert_file_exists "$TARGET/.megalos/PROJECT.md"    "PROJECT.md seeded"
assert_file_exists "$TARGET/.megalos/DECISIONS.md"  "DECISIONS.md seeded"
assert_file_exists "$TARGET/.megalos/config"        "config seeded"
assert_file_exists "$TARGET/.claude/settings.json"  ".claude copied"
assert_file_exists "$TARGET/CLAUDE.md"              "CLAUDE.md copied"
assert_file_exists "$TARGET/megalos.py"             "megalos.py copied"

# Verify megalos.py gate discuss exits 0
( cd "$TARGET" && python3 megalos.py gate discuss )
RC=$?
assert_exit_code "0" "$RC" "gate discuss exits 0"

# Verify STATE.md has correct defaults
assert_file_contains "$TARGET/.megalos/STATE.md" "active_milestone:" "STATE has active_milestone"
assert_file_contains "$TARGET/.megalos/STATE.md" "active_slice:"     "STATE has active_slice"
assert_file_contains "$TARGET/.megalos/STATE.md" "loc_budget:"       "STATE has loc_budget"

test_summary
