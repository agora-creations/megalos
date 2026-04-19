---
estimated_steps: 27
estimated_files: 7
skills_used: []
---

# T04b: Run live cross-model synthetic fixture generation + concordance QA gate + fixture commit

GATE-GATED on API-key availability + T04a merged + T03 merged + S04 mechanical gate passed. Live-service-requiring half of the original T04 per D022.

Prerequisites (verify before starting):
1. ANTHROPIC_API_KEY and OPENAI_API_KEY env vars present and valid.
2. `uv sync --extra panel` completed (anthropic + openai SDKs installed).
3. T04a merged on main (generator CLI importable + dry-run exit-code 0).
4. T03 merged on main (scorer importable + concordance gate primitives available).
5. D016 mechanical gate re-passes against current main.

**Execution:**

- Run T04a's generator live: `uv run python -m tests.selection.generate_synthetic --band all --n-per-band 20 --run-id synthetic_v1`. Produces ~60 pairs written to output staging.
- Cross-model verification: each pair's Claude-proposed-GPT-filtered and GPT-proposed-Claude-filtered passes. Reject pairs where either model flags the pair as not fitting its intended band.
- Write final pairs to `tests/fixtures/workflow_selection/synthetic/band_1.yaml`, `band_2.yaml`, `band_3.yaml`.
- Write sidecar metadata files carrying `{generator_models, generation_date, prompt_template_version, generator_seed}` per the authoring protocol.
- Commit both fixtures and sidecars.

**Concordance QA gate:**
- Run T03's `score_pairs_batch` over the generated synthetic pairs using T02's calibration anchors. For each pair, compare judged-band (from scorer output) against authored-band (from fixture file). Compute concordance rate.
- Gate: ≥70% passes → T04b closes clean. On fail (<70%): record outcome, do NOT commit fixtures, propose recovery paths (regenerate with adjusted prompts OR expand anchors per D018). Operator decides recovery; this task does NOT auto-retry.

**Deliverables (on gate pass):**
- 3 committed YAML fixture files with ~20 pairs each (total ~60 pairs).
- 3 committed YAML metadata sidecars.
- `tests/selection/test_concordance.py` as regression guard in standard CI.
- Completion report: total pairs generated, concordance rate, per-band breakdown, run-ID + record file location.

**Fixture-metadata requirement pinned:** metadata sidecars are mandatory, not optional. Without them, future re-runs cannot reproduce or supersede the fixtures honestly. T04b does not close if metadata is missing.

**Hard scope boundaries:**
- Do NOT modify T04a's generator code. T04b runs the generator as T04a delivered it.
- Do NOT create `live_scenarios/` fixtures — T05 territory.
- Do NOT implement scenario runner or measurement execution — T05/T06.

**Commit:** describe the effect, not the coordinate. Co-author footer. Dispatch only with operator go-ahead AND keys available.

## Inputs

- `T04a generator CLI (committed on main)`
- `T03 scorer (committed on main)`
- `S04/T02 anchors.yaml (calibration ground truth)`
- `S03 panel infrastructure (live API)`
- `ANTHROPIC_API_KEY + OPENAI_API_KEY env vars`
- `D016 mechanical gate pass + D018 measurement thresholds`

## Expected Output

- `3 committed synthetic fixture YAML files with ~20 pairs each + 3 metadata sidecars`
- `Concordance regression test (test_concordance.py) as CI guard for fixture integrity`
- `Completion report with concordance rate + per-band breakdown + run-ID pointer`

## Verification

Concordance gate ≥70% on authored-band vs judged-band match + uv run pytest tests/selection/test_concordance.py + uv run pytest (full suite)
