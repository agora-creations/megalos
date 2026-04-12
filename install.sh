#!/usr/bin/env bash
# mikrós installer — copies the template into a target project and
# installs the runtime dependencies (caveman plugin, docmancer skill).
#
# Usage: ./install.sh /path/to/target-project
set -euo pipefail

TARGET="${1:?usage: ./install.sh /path/to/target-project}"

if [ ! -d "$TARGET" ]; then
  echo "mikrós install: target does not exist: $TARGET" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"

# --- 1. Copy template files ---------------------------------------------
# Destructive on re-run: remove any prior mikrós install in the target so
# a second run refreshes cleanly instead of creating nested .claude/.claude/
rm -rf "$TARGET/.claude"  "$TARGET/.mikros"  "$TARGET/.gemini"
cp -r "$HERE/.claude"  "$TARGET/.claude"
cp -r "$HERE/.mikros"  "$TARGET/.mikros"
cp    "$HERE/.mcp.json" "$TARGET/.mcp.json"

# Copy mikros.py orchestrator if present in source
if [ -f "$HERE/mikros.py" ]; then
  cp "$HERE/mikros.py" "$TARGET/mikros.py"
fi

# Copy simplicity-guard standalone directory if present in source
if [ -d "$HERE/simplicity-guard" ]; then
  rm -rf "$TARGET/simplicity-guard"
  cp -r "$HERE/simplicity-guard" "$TARGET/simplicity-guard"
fi

# Detect runtimes and install appropriate config files
HAS_CLAUDE=false
HAS_GEMINI=false
command -v claude >/dev/null 2>&1 && HAS_CLAUDE=true
command -v gemini >/dev/null 2>&1 && HAS_GEMINI=true

# If neither is on PATH, install both so the user can pick later
if ! $HAS_CLAUDE && ! $HAS_GEMINI; then
  HAS_CLAUDE=true
  HAS_GEMINI=true
fi

if $HAS_CLAUDE; then
  cp "$HERE/CLAUDE.md" "$TARGET/CLAUDE.md"
fi

if $HAS_GEMINI; then
  cp "$HERE/GEMINI.md" "$TARGET/GEMINI.md"
  cp -r "$HERE/.gemini" "$TARGET/.gemini"
  cp "$HERE/gemini-extension.json" "$TARGET/gemini-extension.json"
fi

# --- 2. Seed .mikros state from templates -------------------------------
cp "$TARGET/.mikros/templates/STATE.md.tmpl"     "$TARGET/.mikros/STATE.md"
cp "$TARGET/.mikros/templates/PROJECT.md.tmpl"   "$TARGET/.mikros/PROJECT.md"
cp "$TARGET/.mikros/templates/DECISIONS.md.tmpl" "$TARGET/.mikros/DECISIONS.md"
cp "$TARGET/.mikros/templates/config.tmpl"       "$TARGET/.mikros/config"

# --- 3. Install caveman plugin ------------------------------------------
# https://github.com/JuliusBrussee/caveman — output token reduction.
if $HAS_CLAUDE && command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add JuliusBrussee/caveman
  claude plugin install caveman@caveman
fi

# --- 4. Install docmancer skill for doc grounding -----------------------
# https://github.com/docmancer/docmancer — local doc retrieval.
if command -v docmancer >/dev/null 2>&1; then
  docmancer install claude-code
fi

# --- 5. Compress CLAUDE.md via caveman-compress -------------------------
# Produces a compressed CLAUDE.md and keeps CLAUDE.original.md as the
# human-readable backup the user edits.
if $HAS_CLAUDE && command -v claude >/dev/null 2>&1; then
  ( cd "$TARGET" && claude --permission-mode acceptEdits -p "/caveman:compress CLAUDE.md" )
fi

echo
echo "mikrós installed into $TARGET"
RUNTIMES=""
$HAS_CLAUDE && RUNTIMES="${RUNTIMES}claude "
$HAS_GEMINI && RUNTIMES="${RUNTIMES}gemini "
echo "Runtimes configured: ${RUNTIMES:-none}"
echo "Next: cd $TARGET && start your CLI, then /discuss to begin your first milestone"
