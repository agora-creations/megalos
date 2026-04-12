#!/usr/bin/env bash
# mikrós PreToolUse hook: auto-approve `git add` and `git commit` ONLY when
# the Bash tool call is rooted inside a git worktree (i.e. `.git` is a file,
# not a directory). This unblocks phase-builder subagents running under
# `--permission-mode acceptEdits`, without relaxing interactive safety in
# the main repo — the main repo's `.git` is a directory, so commands issued
# from there still fall through to the normal permission prompt.
#
# Input (stdin JSON):
#   Claude Code: { "tool_name": "Bash",              "tool_input": { "command": "..." }, "cwd": "..." }
#   Gemini CLI:  { "tool_name": "run_shell_command",  "tool_args":  { "command": "..." }, "cwd": "..." }
#
# Output: on approval, prints a JSON decision to stdout and exits 0.
# The approval JSON includes both hookSpecificOutput (Claude Code) and
# decision (Gemini CLI) so either runtime accepts it.
# On no-opinion, exits 0 with empty stdout (lets normal permission flow run).
#
# Scope is intentionally narrow:
#   - Only `git add ...` and `git commit ...` (no push, reset, checkout, rm).
#   - No shell chaining: commands containing ; & | ` $ < > are rejected so
#     an approved `git commit` cannot smuggle a second command through.
#   - CWD must have a `.git` file (worktree linkage), not a `.git` directory.

set -e

command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat)

TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
# Accept both "Bash" (Claude Code) and "run_shell_command" (Gemini CLI).
[ "$TOOL" = "Bash" ] || [ "$TOOL" = "run_shell_command" ] || exit 0

# Accept both tool_input (Claude Code) and tool_args (Gemini CLI).
CMD=$(echo "$INPUT" | jq -r '(.tool_input.command // .tool_args.command) // empty' 2>/dev/null || true)
[ -n "$CMD" ] || exit 0

# Only `git add ...` or `git commit ...`, and reject any shell metachars that
# would allow chaining or substitution inside the approved command.
if ! [[ "$CMD" =~ ^git\ (add|commit)(\ [^\;\&\|\`\$\<\>]*)?$ ]]; then
  exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[ -n "$CWD" ] || exit 0

# Worktree check: linked worktrees store `.git` as a file pointing at the
# main repo's gitdir. The main repo has `.git` as a directory.
[ -f "$CWD/.git" ] || exit 0

# Emit approval JSON understood by both Claude Code (hookSpecificOutput) and
# Gemini CLI (decision). Extra keys are ignored by each runtime.
cat <<'JSON'
{"decision":"allow","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"mikrós: auto-approved git add/commit inside isolated worktree"}}
JSON
exit 0
