# Workflow-Selection Authoring Protocol

This document defines how fixtures for the workflow-selection measurement
slice are authored. It governs two fixture families — synthetic pair
diagnostics and live-scenario fixtures — plus the hand-authored
calibration anchor set. The protocol exists so measurement runs are
reproducible, comparable across re-measurements, and insulated from
same-model authorship contamination.

## 1. Marker definition

**Working definition (use while authoring):**

> A marker is a content word or phrase naming a distinct object,
> output, or operation that the other workflow's description does not
> name or contradict.

Authors count markers by reading both descriptions in parallel and
noting spans that would not be substitutable between them. A marker is
not a stylistic choice (tone, hedging, register) — it is a referent.

**Ex-post formal definition (for post-hoc analysis, not authoring):**

> A marker is a span that, if deleted from one description, would flip
> the LLM's selection on the pairs that depend on it.

The formal definition is the honest one — closeness ultimately cashes
out as "how much does the LLM's decision depend on this span?" — but
it is circular at authoring time (the LLM has not been queried yet).
Authors use the working definition; the formal definition anchors the
axis during analysis.

## 2. Closeness bands

Every authored pair is placed in exactly one band. Bands correspond to
the three regimes the measurement design (D018) probes.

- **Band 1 — low closeness.** Descriptions differ in multiple lexical
  and semantic markers. Selection should be near-trivial for any
  competent selector. Anchor score range: ~0.2–0.3.

- **Band 2 — mid closeness.** Descriptions overlap significantly. A
  few markers distinguish them; most of the content could appear in
  either. Anchor score range: ~0.5.

- **Band 3 — high closeness.** Descriptions overlap near-entirely. A
  single minimal marker distinguishes them. Anchor score range:
  ~0.7–0.8.

Scores above 0.85 are reserved for genuinely indistinguishable pairs —
the selector should perform at chance. They are not authored by
default; include only when the measurement design calls for a
ceiling probe.

## 3. Cross-model generator rule

Per D014 (Claude + GPT cross-model panel), synthetic pairs **and**
live-scenario utterances are authored under a cross-model generator
protocol: one model proposes the candidate, a different model filters
or rewrites it. No single-model generation is permitted for either
fixture family.

Live-scenario utterances are not exempt. The rule exists to separate
fixture authorship from the measurement target — if the measurement
target is Claude, the fixture cannot be Claude-authored end-to-end,
regardless of whether the fixture is a synthetic pair or a live
scenario. The calibration anchors (§4) are the only exception: they
are hand-authored by the operator and form the ground-truth calibration
instrument.

## 4. Calibration anchor structure

Anchors live in `tests/fixtures/workflow_selection/anchors.yaml`. Each
entry has the following shape:

```yaml
anchors:
  - pair_id: anchor_001
    description_A: "..."
    description_B: "..."
    operator_assigned_closeness: 0.3   # float in [0.0, 1.0]
    rationale: "One-sentence explanation of the score."
```

The initial set covers the three bands (≥1 anchor at each band
mid-point). Expansion to 5–7 anchors is triggered only if
sensitivity analysis (T03 of this slice, or later diagnostic work)
reveals instability in the judge's calibration.

## 5. Generation-time metadata

Every fixture YAML carries a sidecar `<file>.meta.yaml` with:

```yaml
generator_models: [string, ...]    # e.g. ["claude-opus-4.7", "gpt-5"]
generation_date: "YYYY-MM-DD"      # ISO-8601
prompt_template_version: "v1"      # semver-ish author choice
generator_seed: 42                 # int or null if provider RNG unseeded
```

Sidecar metadata applies to both synthetic fixture files (T04
territory) and live-scenario fixture files (T05 territory). Calibration
anchors do not carry sidecar metadata — they are hand-authored, so the
metadata schema does not apply.

## 6. Refresh-cadence policy

Fixtures are frozen snapshots of today's catalog. They are not
calendar-refreshed.

**Trigger:** the catalog grows by ≥6 new workflows, or the total live
catalog reaches ≥12 workflows in any single category group. Either
trigger initiates a re-measurement review — not an automatic
regeneration. The review decides whether the shift materially changes
the selection surface (new categories, collapsed category boundaries,
new closeness-band occupancy).

The trigger is recorded in DECISIONS.md when the next measurement
review fires, not on a schedule. This policy is itself revisitable if
the catalog grows in a way the trigger fails to detect (e.g., one
category doubles while others hold — the review cadence must still
fire).
