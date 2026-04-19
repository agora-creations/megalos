# Deferred: M005/S04 — T04b, T05, T06

Plans preserved here were scoped, shape-reviewed, and dispatch-ready when M005 closed at T04a on 2026-04-19. Execution was blocked on availability of multi-provider API access (ANTHROPIC_API_KEY + OPENAI_API_KEY) for cross-model synthetic fixture generation (T04b), live-catalog measurement (T05), and gate evaluation against recorded runs (T06). M005 shipped the selection mechanism code unverified; see D023 in `.gsd/DECISIONS.md` for the full framing of what "unverified" means here and why warping the measurement to match available resources was rejected.

## Blocking condition

Multi-provider paid API access unavailable at M005 close. D014 requires Claude + GPT panel for cross-model authorship separation; both providers require paid API access. Local-only models (Ollama, Gemini free tier alone) would violate D014's cross-model rule or degrade measurement validity in ways D023 documents as unacceptable.

## Resumption criteria

Four conditions must hold before T04b dispatches:

1. **API keys available.** ANTHROPIC_API_KEY and OPENAI_API_KEY in the execution environment. Per D025, the spend envelope is named in the S04 resumption plan before dispatch (not in operator memory).
2. **Catalog state pinned or re-validated.** The synthetic fixtures + live scenarios authored today target the workflow catalog as it existed at M005 close. M006 adds MCP-tool-call actions; Phase F resumption plausibly adds mikros workflows. At resumption, either the catalog is pinned to its M005-close state for the measurement run, OR the fixtures are re-validated against whatever catalog exists then. "Re-validated" means re-running T04a's generator against the current catalog and re-authoring T05's live scenarios; partial re-validation (only one of the two) is insufficient because they're linked measurements.
3. **D014 cross-model discipline held.** No degradation to single-model measurement, no pivot to free-tier-only provider combinations that don't meet the cross-model requirement. If resource constraints force a D014 amendment, that amendment is a prerequisite decision recorded in DECISIONS.md, not an ad-hoc execution choice at dispatch time.
4. **D016 mechanical gate re-passes.** The panel contract commitments (A: panel_query signature + PanelRequest/PanelResult fields; B: record format with schema_version; C: PanelProviderError + retry budget) must still hold against main at resumption. If any commitment has drifted via intervening milestones, the contract is amended or restored before T04b dispatches.

## Catalog-drift risk

The workflow catalog at M005 close is the selection problem S04 was designed to measure. Between now and resumption, the catalog will grow. Three concrete drift vectors:

- **M006** introduces MCP-tool-call actions as a new authoring surface. The selection measurement's catalog expansion from 6 workflows to some larger N changes the per-scenario chance-rate baseline (Cohen's κ divisor shifts from ~0.83 at N=6 toward ~1.0 as N grows), which affects D018's rescaling math.
- **Phase F** resumption adds mikros workflows authored outside the three current domain repos. New categories may exist. The band definitions (Band 1 = cross-category / multi-marker; Band 2 = same-category / few-marker; Band 3 = same-workflow-family / one-minimal-marker) may need band boundaries redrawn.
- **Workflow description edits.** Any revision to existing workflow descriptions (clarification, tightening, authorship-guide changes per docs/AUTHORING.md updates) changes the discrimination surface S04 measures. The measurement is a point-in-time property.

Consequence: resumption cannot assume the fixtures preserved here are still the right fixtures. Re-authoring is the default, not the exception, unless the catalog is explicitly held constant.

## Decision pointers

Read these before resumption planning. Each survives in `.gsd/DECISIONS.md`:

- **D014** — Cross-model panel composition (Claude + GPT). Load-bearing for S04's measurement validity.
- **D016** — Three contract commitments (API surface, record format, error/retry budget) + four-item mechanical gate + drift resolution rule. T04b, T05, T06 depend on these.
- **D017** — Retry budget as expected amendment surface; gate-pass necessary-but-not-sufficient for Commitment C.
- **D018** — Gap threshold in per-scenario κ space + per-pair-to-per-scenario κ rescaling. Threshold revisitable after first two measurements.
- **D019** — SDK-free invariant for megalos_panel.adapters; structurally enforced by hermeticity tests. Preserved through M006.
- **D020** — Plan-internal-contradiction resolution meta-rule (agent preserves harder constraints, reviewer confirms).
- **D021** — Close-criterion sequencing rule (load-bearing hardening lands in-task before merge).
- **D022** — Execution-environment boundaries as legitimate task-split motivation. Precedent: T04 → T04a + T04b.
- **D023** — M005 ships unverified; measurement deferred. Names what "unverified" precisely means and what restoration requires.
- **D025** — Spend-envelope-at-plan-time rule (supersedes D024's minimal form). Applies prospectively to any future measurement slice.

## Shape-review task decomposition (commitment mapping)

| Task | Consumes (commitments) | Gate-gated | Status at M005 close |
|---|---|---|---|
| T01 | none (gate-independent) | no | complete |
| T02 | none (gate-independent) | no | complete |
| T03 | A (panel_query signature, PanelRequest/PanelResult fields) | yes (passed) | complete |
| T04a | A, B (panel + record format) | yes (passed) | complete |
| T04b | A, B, C (+ keys) | yes | deferred |
| T05 | A, B, C (+ T04b fixtures) | yes | deferred |
| T06 | B (reads records) | yes | deferred |

## Artifacts preserved

- `T04b-PLAN.md` — live synthetic fixture generation via cross-model authoring + concordance QA gate (≥70% authored-band vs judged-band match) + fixture commit with metadata sidecars.
- `T05-PLAN.md` — scenario runner + live closeness matrix + end-to-end measurement harness. Authors live-scenario fixtures via cross-model generation against the live catalog. Runs measurement across Claude + GPT panel, produces JSON-lines records.
- `T06-PLAN.md` — full measurement execution + gate evaluation (Wilson CI + κ-adjusted gap per D018) + CSV reporting + three-branch failure tree + DECISIONS.md entry with outcome.

See also: `.gsd/milestones/M005/slices/S04/tasks/T01-PLAN.md` and `T02-PLAN.md` for completed gate-independent work; `T03-PLAN.md` and `T04a-PLAN.md` for completed gate-gated code work. Those remain in the active GSD tree because the slice was replanned to remove T04b/T05/T06 from its task list rather than marking the completed tasks deferred.

## Resumption-time concordance-gate-fail tree (pre-specified, not yet exercised)

T04b's concordance QA gate reads judged-band vs authored-band concordance across the synthetic pair corpus. On fail, the recovery path is pre-specified here so it is not invented under recency pressure at resumption:

- **Aggregate concordance 60-69%** → one regeneration attempt with prompt adjustments. If second run is still sub-threshold, escalate to replan. No indefinite regeneration loop — p-hacking fixture quality into compliance is the failure mode this rule closes.
- **Aggregate concordance 40-59%** → escalate to replan. Prompt tuning is not sufficient at this gap; structural change to the generator or scorer is required.
- **Aggregate concordance below 40%** → premise audit. The generator, scorer, or authoring protocol has a structural issue, not a tuning one. Halt and reassess at milestone altitude.
- **Any band individually below 50% regardless of aggregate** → band-specific regeneration. Band-level failure signals the band's prompt template or the generator's band-separation logic; aggregate-level repair will mask rather than fix it.

## Cost-logging requirement (for the resumption execution)

When T04b dispatches, the completion record names: actual token consumption per provider, approximate dollar cost per provider, total measurement cost across T04b + T05 live runs. Matches the metadata-sidecar discipline (future re-runs need to know what they cost) and serves as a M006-and-beyond planning input for any live-API slice estimate.

## M005 formal-state lag (tool issue)

M005 is functionally complete per D023 and D025; `main` is the source of truth for milestone state. Formal GSD milestone-state remains `active` in `.gsd/gsd.db` because `gsd_complete_milestone` rejects `verificationPassed: true` across multiple attempts with minimal and full content — an MCP bridge boolean-coercion issue that also forced D024→D025 (on the `when_context` parameter). Both failures are documented in `.gsd/deferred/M005/upstream-issues/mcp-bridge-boolean-coercion.md` for GSD-2 upstream. Until the upstream fix lands, treat main as authoritative: if querying "what milestones completed" against GSD's formal record, cross-reference against git history (M005 final commit: `5119702` and onward through the deferred-archive commit).

## Positioning audit — specific trigger

Before any external communication touching M005 outcomes, or at the start of M006 planning if M006's public framing references selection behavior: audit README.md and any public-facing documentation to ensure no language claims selection quality that is unsubstantiated per D023.

Minimum pass:

```
grep -i -E "selection|discrimination|workflow.choice|picks.the.right" README.md docs/
```

Any hit naming or implying reliable selection quality: soften or remove until S04 resumes. Acceptable framing when the topic comes up: "workflow selection mechanism shipped; quality verification deferred pending multi-provider measurement infrastructure." External materials (blog posts, pitch decks, anywhere the project is pitched publicly): same audit, same softening.

Trigger is NOT "someday follow up" — trigger is **one of: (a) next README or docs/ edit that touches selection language; (b) start of M006 external-facing planning; (c) any public communication referencing M005**. At whichever of those fires first, run the audit before the communication ships.
