#!/usr/bin/env bash
# Tests for mikros.py state machine
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MIKROS="python3 $REPO_ROOT/mikros.py"

# Create a temp directory for isolated tests
TMPDIR_BASE="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

setup_fresh() {
  local dir="$TMPDIR_BASE/fresh-$$-$RANDOM"
  mkdir -p "$dir/.mikros/templates"
  cat > "$dir/.mikros/STATE.md" <<'STATE'
# mikros state

active_milestone:
active_slice:
active_task:
active_worktree:
active_worktree_path:
loc_budget: 300

## Recently completed

(none)

## Notes

Test state file.
STATE
  echo "$dir"
}

setup_with_milestone() {
  local dir
  dir="$(setup_fresh)"
  sed -i.bak 's/^active_milestone:.*/active_milestone: M001/' "$dir/.mikros/STATE.md"
  rm -f "$dir/.mikros/STATE.md.bak"
  mkdir -p "$dir/.mikros/plans/M001"
  echo "# Context" > "$dir/.mikros/plans/M001/CONTEXT.md"
  echo "$dir"
}

setup_with_slice() {
  local dir
  dir="$(setup_with_milestone)"
  sed -i.bak 's/^active_slice:.*/active_slice: S01/' "$dir/.mikros/STATE.md"
  sed -i.bak 's/^active_task:.*/active_task: T01/' "$dir/.mikros/STATE.md"
  rm -f "$dir/.mikros/STATE.md.bak"
  cat > "$dir/.mikros/plans/M001/S01-PLAN.md" <<'PLAN'
# Slice S01

### T01 — First task

Some content.

**LOC budget:** 120

---

### T02 — Second task

More content.

**LOC budget:** 300

---

### T03 — Third task

Even more.

**LOC budget:** 150
PLAN
  echo "$dir"
}

# Helper: run command, capture exit code without triggering set -e
run_expecting() {
  local expected_rc="$1"; shift
  local msg="$1"; shift
  local rc=0
  "$@" || rc=$?
  assert_exit_code "$expected_rc" "$rc" "$msg"
}

# --- gate discuss ---

echo "=== gate discuss (fresh project) ==="
dir="$(setup_fresh)"
run_expecting 0 "gate discuss on fresh project" \
  bash -c "cd '$dir' && $MIKROS gate discuss"

# --- gate plan-slice ---

echo "=== gate plan-slice (no milestone) ==="
dir="$(setup_fresh)"
run_expecting 1 "gate plan-slice no milestone" \
  bash -c "cd '$dir' && $MIKROS gate plan-slice 2>/dev/null"

echo "=== gate plan-slice (with milestone, no CONTEXT.md) ==="
dir="$(setup_fresh)"
sed -i.bak 's/^active_milestone:.*/active_milestone: M001/' "$dir/.mikros/STATE.md"
rm -f "$dir/.mikros/STATE.md.bak"
run_expecting 1 "gate plan-slice no CONTEXT.md" \
  bash -c "cd '$dir' && $MIKROS gate plan-slice 2>/dev/null"

echo "=== gate plan-slice (with milestone + CONTEXT.md) ==="
dir="$(setup_with_milestone)"
run_expecting 0 "gate plan-slice with milestone" \
  bash -c "cd '$dir' && $MIKROS gate plan-slice"

# --- gate execute-task ---

echo "=== gate execute-task (no slice) ==="
dir="$(setup_with_milestone)"
run_expecting 1 "gate execute-task no slice" \
  bash -c "cd '$dir' && $MIKROS gate execute-task T01 2>/dev/null"

echo "=== gate execute-task (wrong task) ==="
dir="$(setup_with_slice)"
run_expecting 1 "gate execute-task wrong task" \
  bash -c "cd '$dir' && $MIKROS gate execute-task T99 2>/dev/null"

echo "=== gate execute-task (correct task) ==="
dir="$(setup_with_slice)"
run_expecting 0 "gate execute-task correct task" \
  bash -c "cd '$dir' && $MIKROS gate execute-task T01"

# --- gate sniff-test ---

echo "=== gate sniff-test (no completed tasks) ==="
dir="$(setup_with_slice)"
run_expecting 1 "gate sniff-test no completed tasks" \
  bash -c "cd '$dir' && $MIKROS gate sniff-test 2>/dev/null"

echo "=== gate sniff-test (with summary file) ==="
dir="$(setup_with_slice)"
mkdir -p "$dir/.mikros/plans/M001/S01"
echo "# Summary" > "$dir/.mikros/plans/M001/S01/T01-SUMMARY.md"
run_expecting 0 "gate sniff-test with summary" \
  bash -c "cd '$dir' && $MIKROS gate sniff-test"

# --- advance ---

echo "=== advance T01 ==="
dir="$(setup_with_slice)"
run_expecting 0 "advance T01 exit code" \
  bash -c "cd '$dir' && $MIKROS advance T01"

assert_file_exists "$dir/.mikros/STATE.md" "STATE.md exists after advance"
assert_file_contains "$dir/.mikros/STATE.md" "active_task: T02" "advance sets next task"
assert_file_contains "$dir/.mikros/STATE.md" "loc_budget: 300" "advance sets next LOC budget"
assert_file_contains "$dir/.mikros/STATE.md" "T01" "advance records completed task"

echo "=== advance last task ==="
dir="$(setup_with_slice)"
sed -i.bak 's/^active_task:.*/active_task: T03/' "$dir/.mikros/STATE.md"
rm -f "$dir/.mikros/STATE.md.bak"
run_expecting 0 "advance last task" \
  bash -c "cd '$dir' && $MIKROS advance T03"
assert_file_contains "$dir/.mikros/STATE.md" "active_task:" "advance clears task when last"

# --- write-summary ---

echo "=== write-summary ==="
dir="$(setup_with_slice)"
mkdir -p "$dir/.mikros/plans/M001/S01"
cat > "$dir/.mikros/DECISIONS.md" <<'DEC'
# DECISIONS

## Entries
DEC

SUMMARY="## T01 — First task

### Worktree
- branch: feature-branch-123
- path: /tmp/worktree/test

### Must-haves
- done

### Files modified
- foo.py (+10/-0)

### Decisions (append to DECISIONS.md)
- Use plain dicts instead of dataclasses

### Verification output
All passed"

echo "$SUMMARY" | bash -c "cd '$dir' && $MIKROS write-summary T01"
rc=$?
assert_exit_code "0" "$rc" "write-summary exit code"

assert_file_exists "$dir/.mikros/plans/M001/S01/T01-SUMMARY.md" "summary file written"
assert_file_contains "$dir/.mikros/plans/M001/S01/T01-SUMMARY.md" "feature-branch-123" "summary content preserved"
assert_file_contains "$dir/.mikros/STATE.md" "active_worktree: feature-branch-123" "worktree branch extracted"
assert_file_contains "$dir/.mikros/STATE.md" "active_worktree_path: /tmp/worktree/test" "worktree path extracted"
assert_file_contains "$dir/.mikros/DECISIONS.md" "Use plain dicts" "decisions appended"

# --- atomic write safety ---

echo "=== no temp files left behind ==="
dir="$(setup_with_slice)"
bash -c "cd '$dir' && $MIKROS advance T01"
tmp_count=$(find "$dir/.mikros" -name "*.tmp" | wc -l | tr -d ' ')
assert_eq "0" "$tmp_count" "no tmp files after advance"

# --- stderr message on gate failure ---

echo "=== stderr message on gate failure ==="
dir="$(setup_fresh)"
err=$(bash -c "cd '$dir' && $MIKROS gate plan-slice" 2>&1 || true)
TESTS_RUN=$((TESTS_RUN + 1))
if [ -z "$err" ]; then
  echo "FAIL: expected stderr output from gate failure" >&2
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

test_summary
