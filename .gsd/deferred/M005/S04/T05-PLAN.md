---
estimated_steps: 20
estimated_files: 6
skills_used: []
---

# T05: Scenario runner + live closeness matrix + end-to-end measurement harness

GATE-GATED. Assumes T03 and T04 complete (fixtures + scorer available).

Create `tests/selection/live_scenarios.py`:
- Authoring of live-scenario fixtures via cross-model generation (same protocol as T04 but against the live catalog rather than synthetic pairs). Each scenario = `{scenario_id, user_utterance, correct_workflow_name, distractor_workflows: list[str]}`.
- Target: ~60 scenarios covering all current workflows across writing/analysis/professional categories, distributed so each workflow is the correct answer ≥5 times.
- Committed under `tests/fixtures/workflow_selection/live_scenarios/scenarios.yaml` with metadata sidecar.
- Invoked via `uv run python -m tests.selection.live_scenarios` (run-once-and-commit, same pattern as T04 Phase 1).

Create `tests/selection/runner.py`:
- `def run_live_scenarios(scenarios: list[dict], catalog: list[dict], models: list[str], record_writer: RecordWriter) -> list[dict]` — for each (scenario, model), builds a PanelRequest whose prompt is `SCENARIO_PROMPT_TEMPLATE.format(utterance=s.user_utterance, catalog_descriptions=render_catalog(catalog))`. Invokes panel_query. Parses the returned workflow name from `PanelResult.selection`. Compares against `scenario.correct_workflow_name`. Records per-request via record_writer. Returns per-scenario results.
- `def run_synthetic_pairs(synthetic_pairs: list[dict], judge_model: str, anchors: list[dict], record_writer: RecordWriter) -> list[dict]` — reuses T03's scorer.score_pairs_batch over the committed synthetic fixtures; returns per-pair results with judged-band, authored-band, κ input data.
- `def compute_live_closeness_matrix(catalog: list[dict], anchors: list[dict], judge_model: str, record_writer: RecordWriter) -> dict` — invokes T03's scorer on every pair in the live catalog (6-workflow × 6-workflow = 15 unique pairs). Result: dict mapping each workflow to its nearest-neighbor distance on the judge's closeness axis.
- Scenario-prompt template versioned (`SCENARIO_PROMPT_TEMPLATE_VERSION`).

Unit tests (`tests/selection/test_runner.py`):
- All tests use `create_autospec(panel_query)` for panel mocking (D016 rule).
- `run_live_scenarios`: mocked panel returns canned selections; correctness counted against expected correct answers; records written with expected fields.
- `run_synthetic_pairs`: delegates to T03; result shape verified.
- `compute_live_closeness_matrix`: pairwise invocation count equals N*(N-1)/2; nearest-neighbor distance per workflow returned correctly.
- Error paths: panel errors surface as per-scenario PanelResult.error; runner does not crash on partial failures.

Live smoke test (`tests/selection/test_runner_live.py`, `@pytest.mark.live`):
- Run a 3-scenario smoke test against real panel (Claude + GPT). Assert records written, selections parsed, correctness evaluable. Provides the first real-API exercise path for the measurement harness before T06 does the full run.

Standard CI: unit tests pass. Live smoke skipped in CI; invoked manually or in nightly cron.

## Inputs

- `S03 as-built (panel_query, record_writer)`
- `S04/T02: pool loader, authoring protocol`
- `S04/T03: scorer`
- `S04/T04: committed synthetic fixtures`
- `.gsd/DECISIONS.md D016 (contract), D018 (measurement design)`

## Expected Output

- `tests/selection/live_scenarios.py (run-once generator for live scenario fixtures)`
- `Committed live-scenario fixtures + metadata`
- `tests/selection/runner.py with scenario runner + synthetic pair runner + closeness matrix computation`
- `Unit tests (mocked) + live smoke tests`

## Verification

uv run pytest tests/selection/test_runner.py
