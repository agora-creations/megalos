#!/usr/bin/env bash
# mikrós PostToolUse hook for Write and Edit.
#
# Runs a fast guard (lint + type-check) on the edited file and then invokes
# loc-budget.sh. Exit 2 blocks the tool call, surfacing the error back to
# the model as immediate feedback.
#
# NOTE: the exact env var name for the edited file path is spec open
# question 7. We read from known candidates in priority order and pick the
# first non-empty one. Collapse to the correct name once verified in the
# self-test (plan Task 20).

set -e

EDITED="${CLAUDE_HOOK_TOOL_INPUT_file_path:-}"
[ -z "$EDITED" ] && EDITED="${CLAUDE_TOOL_INPUT_file_path:-}"
[ -z "$EDITED" ] && EDITED="${CLAUDE_FILE_PATH:-}"

# No path reported → nothing to check (some tool calls don't carry a file path)
if [ -z "$EDITED" ]; then
  exit 0
fi

# If the file doesn't exist (e.g. deleted by the tool call), skip language checks.
if [ -f "$EDITED" ]; then
  case "$EDITED" in
    *.py)
      ruff check "$EDITED" >&2 || exit 2
      mypy "$EDITED" >&2 || exit 2
      ;;
    *.ts|*.tsx|*.js|*.jsx)
      # Lightweight syntax check. Project can override with stricter commands.
      node --check "$EDITED" 2>/dev/null || true
      ;;
  esac
fi

# Always enforce the LOC budget.
if [ -x .claude/skills/simplicity-guard/scripts/loc-budget.sh ]; then
  bash .claude/skills/simplicity-guard/scripts/loc-budget.sh || exit 2
fi

exit 0
