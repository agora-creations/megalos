---
estimated_steps: 21
estimated_files: 3
skills_used: []
---

# T06: Full measurement execution + gate evaluation + reporting + DECISIONS.md entry with failure-tree

GATE-GATED via T05's records (not panel directly).

Create `tests/selection/measure.py` — the full-measurement CLI entry point (invokable: `uv run python -m tests.selection.measure [--models claude-opus-4-7,gpt-4o] [--run-id <id>]`):
- Loads committed fixtures (live scenarios from T05, synthetic pairs from T04, anchors from T02, catalog from T02's pool loader).
- Runs full measurement: `run_live_scenarios` + `run_synthetic_pairs` + `compute_live_closeness_matrix`.
- Writes JSON-lines records via `RecordWriter` to `runs/measurement_<run_id>.jsonl`.
- Writes CSV reports via `csv_schema` helpers to `runs/measurement_<run_id>_scenarios.csv` and `runs/measurement_<run_id>_summary.csv`.
- Applies `primitives.evaluate_gate` to the aggregated results; prints pass/fail summary.
- On fail, applies the three-branch failure tree (from D016 / T06 design pass) automatically, recording the branch taken + rationale:
  - Branch A — **Live <90% AND gap ≤25pp**: fixture/scorer problem. Action: re-run concordance gate (T04's test_concordance); if concordance drops below 70%, flag for fixture regeneration; if concordance holds, flag for anchor re-verification. Measurement run records the diagnosis but does not auto-regenerate.
  - Branch B — **Live ≥90% AND gap >25pp**: discrimination exists but weaker than target. Requires human decision: (a) relax gap threshold with written rationale naming the property sacrificed, or (b) enrich workflow descriptions and re-measure. Measurement run records the branch as Branch B but halts execution pending operator decision; does not auto-relax.
  - Branch C — **Both fail**: architectural signal, not gate-tuning. Measurement run records Branch C with the instruction to escalate to M005-level reassessment before additional measurement.
- Writes a draft DECISIONS.md entry with the full outcome, to be promoted via `gsd_save_decision` at task completion.

Create `tests/selection/test_measure.py`:
- Mocks runner invocations; verifies CSV shape; verifies gate evaluation invocation; verifies failure-tree branch selection on synthetic input numbers that trigger each branch.
- All panel touchpoints use autospec.

On task completion:
- Run the full measurement once against real Claude + GPT panel (`uv run python -m tests.selection.measure`).
- Commit the resulting CSVs and JSON-lines record file as measurement artifacts under `runs/<id>/` (gitignored directory is runs/; artifacts *from this measurement* are committed under `tests/fixtures/workflow_selection/measurement_<id>/` instead, outside the gitignore, to preserve the M005 vision of 'always ships a committed artifact').
- Save the gate-outcome DECISIONS.md entry via `gsd_save_decision` with scope `measurement`, decision `M005 workflow-selection gate outcome`, choice capturing pass/fail + branch executed + key numbers.
- If Branch B or Branch C fires, the task completion record names the branch and surfaces the decision back to the operator before closing M005.

Standard CI: unit tests pass. Full measurement is a manual invocation + commit gesture, not an automated CI run.

## Inputs

- `All prior S04 outputs (T01-T05)`
- `S03 as-built (panel_query with real API keys for the full measurement run)`
- `.gsd/DECISIONS.md D016 + D018 (gate thresholds, failure tree, measurement design)`
- `ANTHROPIC_API_KEY, OPENAI_API_KEY env vars`

## Expected Output

- `tests/selection/measure.py CLI with full measurement execution + gate evaluation + failure-tree branch selection`
- `Unit tests covering gate evaluation + failure-tree branch logic`
- `Committed measurement artifacts (CSV + JSON-lines records) under tests/fixtures/workflow_selection/measurement_<id>/`
- `gsd_save_decision entry recording M005 workflow-selection gate outcome with branch + numbers`

## Verification

uv run pytest tests/selection/test_measure.py && uv run python -m tests.selection.measure --dry-run
