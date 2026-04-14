#!/usr/bin/env bash
# Tests for Gemini CLI extension structure (T04)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO/tests/lib/assert.sh"

# --- gemini-extension.json validity ---

jq . "$REPO/gemini-extension.json" >/dev/null
assert_eq 0 $? "gemini-extension.json is valid JSON"

jq -e '.hooks.BeforeTool' "$REPO/gemini-extension.json" >/dev/null
assert_eq 0 $? "gemini-extension.json declares BeforeTool hook"

jq -e '.hooks.AfterTool' "$REPO/gemini-extension.json" >/dev/null
assert_eq 0 $? "gemini-extension.json declares AfterTool hook"

jq -e '.skills[] | select(.path | contains("simplicity-guard"))' "$REPO/gemini-extension.json" >/dev/null
assert_eq 0 $? "gemini-extension.json references simplicity-guard skill"

jq -e '.agents[] | select(.path | contains("phase-builder"))' "$REPO/gemini-extension.json" >/dev/null
assert_eq 0 $? "gemini-extension.json references phase-builder agent"

# --- .gemini/settings.json ---

jq . "$REPO/.gemini/settings.json" >/dev/null
assert_eq 0 $? ".gemini/settings.json is valid JSON"

MATCHER=$(jq -r '.hooks.BeforeTool[0].matcher' "$REPO/.gemini/settings.json")
assert_eq "run_shell_command" "$MATCHER" "BeforeTool matcher is run_shell_command"

CMD=$(jq -r '.hooks.AfterTool[0].hooks[0].command' "$REPO/.gemini/settings.json")
echo "$CMD" | grep -q '.claude/hooks/'
assert_eq 0 $? "AfterTool hooks point to .claude/hooks/ (shared scripts)"

# --- GEMINI.md content parity ---
assert_file_exists "$REPO/GEMINI.md" "GEMINI.md exists"
assert_file_contains "$REPO/GEMINI.md" "Iron rule" "GEMINI.md has Iron rule section"
assert_file_contains "$REPO/GEMINI.md" "Anti-defaults" "GEMINI.md has Anti-defaults section"
assert_file_contains "$REPO/GEMINI.md" "megálos" "GEMINI.md references megálos workflow"

# --- install.sh runtime detection ---
# Create temp dir with fake gemini on PATH but no claude
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT
mkdir -p "$TMPDIR_TEST/bin" "$TMPDIR_TEST/target"
printf '#!/bin/sh\nexit 0\n' > "$TMPDIR_TEST/bin/gemini"
chmod +x "$TMPDIR_TEST/bin/gemini"

# Run install.sh with only gemini on PATH
env PATH="$TMPDIR_TEST/bin:/usr/bin:/bin" \
  bash "$REPO/install.sh" "$TMPDIR_TEST/target" >/dev/null 2>&1 || true

assert_file_exists "$TMPDIR_TEST/target/GEMINI.md" "install.sh installs GEMINI.md when gemini on PATH"
assert_file_exists "$TMPDIR_TEST/target/gemini-extension.json" "install.sh installs gemini-extension.json when gemini on PATH"

test_summary
