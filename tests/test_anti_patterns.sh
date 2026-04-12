#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source tests/lib/assert.sh

FILE=".claude/skills/simplicity-guard/references/anti-patterns.md"

assert_file_exists "$FILE" "anti-patterns.md exists"
assert_file_contains "$FILE" "Enterprise patterns" "has Enterprise patterns section"
assert_file_contains "$FILE" "Framework swaps"     "has Framework swaps section"
assert_file_contains "$FILE" "Cosmetic refactors"  "has Cosmetic refactors section"
assert_file_contains "$FILE" "Heavy orchestration" "has Heavy orchestration section"
assert_file_contains "$FILE" "single implementation" "has single-impl rule"
assert_file_contains "$FILE" "Three-strikes"         "has three-strikes rule"
assert_file_contains "$FILE" "Boring"                "has boring-is-feature rule"
assert_file_contains "$FILE" "always query docmancer" "has strict docmancer grounding rule"
assert_file_contains "$FILE" "not \"when uncertain\"" "docmancer rule is strict, not conditional"

test_summary
