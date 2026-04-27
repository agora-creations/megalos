# ADR-003 — Phase J shipping decision

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-26-megalos-vision-v6.md`](../vision/2026-04-26-megalos-vision-v6.md)
**Resolves:** vision-v6 §9 Q11 (Phase J's economic case under API-key-only)
**Related:** ADR-001 (workflow versioning, `docs/adr/001-workflow-versioning.md`); ADR-002 (run-mode session persistence, `docs/adr/002-run-mode-session-persistence.md`); v5 Phase J scaffold (`docs/vision/2026-04-22-phase-j-scaffold.md`, superseded by this ADR for the shipping-decision question).

---

## 1. Context

Vision-v6 §3.2 commits megálos to two modes inside one UI: run mode and configure mode. Configure mode has two structural halves — the UI surface (picker, tweak panel, customized-entry storage) and the embedded mikrós-reading agent that walks a non-technical user through bounded modifications of a Library entry. v6 §6.4 substantially shrank Phase J's scope from v5: the visual-studio-as-authoring-surface became configure-mode-as-bounded-modification; the template library moved into the OSS Library as a sustained track; the consumer-subscription onramp was removed.

That last removal is what made this ADR's question open. The OAuth feasibility investigation completed 2026-04-26 (`docs/discovery/2026-04-26-oauth-feasibility-investigation.md`) determined that no major LLM provider currently supports third-party routing of inference through consumer subscriptions, with the Q1 2026 trajectory being uniformly restrictive. v6 §6.4's downstream-consequence paragraph named the resulting strategic question: with the consumer-subscription onramp gone, Shape 5's audience narrows from "non-technical mass-market" to "non-technical users willing to provision an LLM API key" — a smaller, more friction-tolerant audience than v5 assumed. v6 §9 Q11 asked: under that narrowed audience, is Phase J still worth shipping? Three positions were defensible at the question level: (a) ship as scoped; (b) defer indefinitely; (c) hold the question open until Phase G's user signal arrives.

The question binds three downstream surfaces. Phase G's UI design implicitly assumes whether configure mode is on the near roadmap — a configure-mode-ready UI pays a design tax that is wasted if Phase J never ships. Phase I's revenue model assumes a particular audience size; if Shape 5 doesn't materialize, the Shape-4-only revenue base must carry the paid product alone. Library curation's content discipline must be tight enough that "close but not quite right" friction is rare at v1 Library scale, since Phase J's configure-mode relief would otherwise be the answer to that friction.

The OAuth resolution also elevated v6 §9 Q4 (paid-vs-self-host value asymmetry). ADR-002 inherited that elevation for the session-persistence slice; this ADR inherits the same elevation. With no consumer-subscription onramp anchoring the paid pitch, every ADR resolving a v6 question now operates in a frame where the operational-maturity claim has to carry more weight, and any decision that touches the paid product's value proposition must engage with that pressure.

A focused /discuss session of 2026-04-27 walked the three named positions against six criteria (audience size and willingness-to-friction; v6-amended build cost; strategic value of shipping vs not-shipping; the "wait for OAuth to lift" assumption; sole-author resource opportunity cost; reversibility) and surfaced a structurally distinct fourth position (d) — ship a thin slice of configure mode's UI surface (picker + manual tweak panel) without the embedded mikrós-reading agent. Operator review applied a meta-reframe: because the recommendation defers Phase J anyway, the (d)-vs-(b) sub-decision should be deferred to a future trigger rather than forcing a Shape-4-behavior prediction now. This ADR resolves §9 Q11 in the form that /discuss-and-review reached, with the deferral-of-the-sub-decision discipline encoded as Clause 3 below.

## 2. Decision

Four commitments. They hold together; weakening any one weakens the others.

**1. Phase J is deferred indefinitely.** Phase J does not ship in the v6 horizon. Engineering bandwidth flows to Phases H, I, Library curation, and Phase F follow-on adapter work (Gemini CLI / OpenCode at v1.1, Codex at v1.2). The friction-tolerant Shape-5 wedge — non-technical users willing to provision an LLM API key, narrowed from v5's mass-market framing by the OAuth resolution — is order-of-magnitude tens of thousands of users globally, not hundreds of thousands. At sole-author pace the engineering dollar is the binding constraint, and Library + Phases G/H/I serving Shapes 1–4 well is the higher-leverage v6 commitment than committing 4–6 months of engineering against an audience that may not materialize.

**2. (Clause 1) Phase G's UI design proceeds configure-mode-naive.** Phase G ships run mode without architectural accommodations for configure mode. The Library-entry picker is a Phase G feature; the per-user-customized-entry storage and the embedded mikrós-reading agent are Phase J only. If Phase J later ships, it adapts to whatever Phase G has built; Phase G does not pre-adapt to Phase J. Phase G's `/discuss` gate must verify that configure-mode-naive design does not lock out efficient Phase J integration when Phase J reopens at any of the trigger conditions in §6 below. If Phase G's design surfaces that configure-mode-naive UI design *cannot* avoid significant rework cost when configure mode later integrates, the assumption underlying this ADR fails and Q11 reopens.

**3. (Clause 2) Three explicit revisit triggers.** "Defer indefinitely" without explicit triggers drifts into abandonment-by-neglect. The triggers are named in §6 below. Restated commitment-side: the operator commits to evaluating each trigger when the conditions named in §6 obtain, and to reopening this ADR (rather than patching around it) when any single trigger fires. The trigger set covers the three failure modes that would invalidate this decision: missing demand signal at Phase G post-ship horizon, OAuth landscape shift, or revenue underperformance attributable to audience size.

**4. (Clause 3) Audience-overlap is the load-bearing input to any T1 reopening, with Phase G analytics instrumented at launch to collect the relevant signals.** The /discuss surfaced that the (d)-vs-(b) hinge — whether Shape-4 users (those who already have IDE-extension access for serious customization) would route casual tweaks through a web panel given the choice — is empirically unanswerable until Phase G ships, and that introspective prediction has known bias (the operator's IDE is open at all hours; a casual Shape-4 customer in a browser is in a different cognitive frame). At T1 reopening, this question is the *first* stress-test the reopened /discuss runs. To make T1 informable when it fires, Phase G analytics must collect two specific signals from launch: (i) whether Shape-4 users (those with IDE-extension access) exercise any in-product lightweight-customization affordance Phase G ships — even a minimal "duplicate this entry" / "open in IDE" link is observable signal; (ii) whether Shape-4 users churn at the customization wall ("close but not quite right") at a meaningfully different rate than Shape-2 users do.

Two implementation notes on commitment 4. **Forward-looking on Phase G:** these signals only inform T1 if they are instrumented from Phase G ship, not added at +5 months when T1 is approaching. Phase G's `/discuss` gate must honor this commitment as it honors Clause 1's configure-mode-naive commitment — same flavor, same binding force, named in this ADR rather than left for Phase G to derive. **Analytics is product instrumentation, not session data:** ADR-002 governs session retention (Level 1, 7-day TTL, account-bound, no browseable history). Product analytics for shape-segmentation behavior is a separate discipline with its own privacy and retention posture, not bound by ADR-002's session TTL. Phase G's `/discuss` should not conflate the two and end up either under-instrumenting (treating analytics as bound by session TTL) or over-collecting (treating session data as bound by analytics-flexible retention).

## 3. Implementation sequencing

The deferral has no immediate implementation work because the decision is "do not build." But two forward-looking sequencing commitments are recorded here so they bind future work explicitly rather than being left for future authors to derive.

**Phase G's `/discuss` gate verifies Clauses 1 and 3.** Before Phase G S01 lands, the `/discuss` must (i) confirm that configure-mode-naive UI design does not lock out efficient Phase J integration if it later reopens at T1/T2/T3, and (ii) adopt Clause 3's analytics instrumentation as a launch-time commitment. If Phase G's `/discuss` cannot honor either at acceptable cost, this ADR reopens — Phase G does not ship workarounds.

**Quarterly OAuth re-check is the standing operator discipline; T2 firing surfaces here.** Per v6 §9 Q2's quarterly re-check commitment, the operator monitors the LLM provider OAuth landscape on a roughly quarterly cadence. The output of that monitoring — observed provider-behavior shift versus continuation of the Q1 2026 restrictive trajectory — is the input that determines whether T2 has fired. The re-check is not gated on this ADR; it pre-existed in v6 §9 Q2. This ADR ties T2 to it explicitly so the operator's monitoring discipline has a downstream reopen-condition rather than producing signal that lands in no specific decision context.

ADR-002's §3 framed implementation sequencing across the Phase G → Phase I window because ADR-002 commits to building. This ADR's §3 is shorter because the deferral commits nothing to build — only constraints on Phase G's eventual shipping shape and the operator's standing monitoring discipline.

## 4. Consequences

**What this commits megálos to.**

- Phase G's `/discuss` gate verifying Clause 1 (configure-mode-naive UI design) and Clause 3 (analytics instrumentation from launch) before Phase G S01 lands.
- Phase G analytics instrumented at ship to collect the two T1 signals (Clause 3 implementation note 1).
- Quarterly v6 §9 Q2 OAuth re-check as standing operator discipline; T2 firing surfaces from this re-check.
- This ADR reopened (not patched) if any of the three trigger conditions in §6 fires or if the Clause-1 configure-mode-naive assumption fails Phase G's `/discuss`.
- Library curation discipline must be tight enough that the "close but not quite right" friction Phase J would otherwise relieve is rare enough not to dominate run-mode churn at v1 Library scale (5–10 domain repos, per v6 §6.1).
- v5's Phase J scaffold (`docs/vision/2026-04-22-phase-j-scaffold.md`) is superseded by this ADR for the shipping-decision question. The scaffold's other content (the five irreducible components, the guardrail-derived constraints, the open questions) remains historical reference; its sequencing and cost/value arguments are stale.

**What this forecloses.**

- Phase J as scoped in v6 §3.2 (configure mode + embedded agent) shipping in the v6 horizon. Reopening requires T1, T2, or T3 firing.
- Configure-mode-readiness as a Phase G design goal. Phase G's UI does not pay design tax for Phase J integration that may never come.
- A "Phase J might ship soon" assumption being load-bearing for any other roadmap, marketing claim, or operator decision. v6's "five shapes served" claim becomes "four shapes served at v6 ship, with Shape 5 conditional on T1/T2/T3."
- Opening Phase J on the basis of operator introspection alone. T1 specifically requires Phase G analytics signal, not introspective prediction; the Clause-3 instrumentation exists to prevent introspection from substituting for measurement at the (d)-vs-(b) decision point.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**The friction-tolerant Shape-5 wedge is much larger than estimated** (>100k users globally rather than tens of thousands), AND those users will pay a premium for the rigor differentiator over Landbot/Voiceflow/Typebot, AND that revenue dwarfs the Phase H/I/Library opportunity-cost gains from spending the engineering elsewhere. All three would need to hold; the audience-size estimate is the most uncertain of the three, but even a higher estimate doesn't invalidate the decision unless the willingness-to-pay and opportunity-cost legs also hold.

**Phase G's `/discuss` reveals that configure-mode-naive UI design cannot avoid significant rework cost when configure mode later integrates.** This would tip retroactively toward position (c) — hold the question open with the design tax paid up front. This ADR would reopen rather than Phase G adopting workarounds. The §3 sequencing commitment makes this dependency visible at the gate where the question gets answered.

**The embedded mikrós-reading agent is not actually what makes configure mode Shape-5-worthy.** This ADR's structural claim is that the embedded agent is the bridge from mikrós-quality customization to non-technical users; without it, configure mode is "a YAML editor with training wheels" which Shape 1's IDE extension already does better. If the (d) thin-slice surface (picker + manual tweak panel without the agent) turns out to serve Shape 5 adequately on its own — i.e., the manual tweak panel is enough friction reduction even for non-technical users — then (d) becomes the right shape and the deferred posture is wasting a low-cost validated-demand opportunity. This claim is structurally load-bearing for the recommendation and is named here because future readers may not derive it from context alone; it is the deepest reason (d) is named in §6 as the most likely T1 evolution rather than as the leading candidate today.

## 6. Trigger conditions for revisit

Three trigger conditions for reopening this ADR. Each names the observable that fires the trigger and the position the reopened /discuss starts from.

- **T1 — Phase G post-ship signal.** After ~6 months of Phase G + Phase I (paid run mode) operation, if user-research data shows that Library-entry customization is the dominant unmet request from the friction-tolerant Shape-5/Shape-4 boundary audience, reopen Q11 as a thin-slice question (resembling position (d)). The Clause-3 analytics instrumentation provides the empirical input; the audience-overlap question is the first stress-test the reopened /discuss runs.
- **T2 — OAuth landscape shift.** Per v6 §9 Q2's quarterly re-check, if any major LLM provider opens a consumer-subscription OAuth flow that makes the Shape-5 onramp feasible without API-key paste, reopen as a full-scope question (resembling original v5 framing or v6 (a) with the consumer-subscription onramp restored).
- **T3 — Run-mode revenue underperformance.** If Phase I revenue at ~12 months post-launch is below the operator's sustainable-solo-pace threshold *and* root-cause analysis attributes the shortfall to Shape-4 audience size rather than pricing or operational issues, reopen as a defensive market-expansion question (resembling (d) or (a) depending on T2 status at that time).

**Calibration note on T2.** Current OAuth-shift probability estimates against the Q1 2026 trajectory: ~10% probability of material shift in 12 months, ~25% in 24 months, ~40% in 36 months. These are operator-amendable guesses calibrated against a uniformly-restrictive prior, not forecasts. Future revisits may update them as the §9 Q2 quarterly re-check produces signal. The trigger T2 condition itself does not depend on the specific numerical values — it depends on observed provider-behavior shift, not on prediction.

**Starting positions for reopened /discuss.** A reopened /discuss at T1 starts from the (d) thin-slice position rather than a blank page; a reopened /discuss at T2 starts from the (a) full-scope position with the consumer-subscription onramp restored; a reopened /discuss at T3 routes to (d) or (a) depending on T2 status at that time. These starting positions are recorded so that future reopened /discuss has a named starting point, not as a commitment to ship either at trigger firing.

## 7. References

- vision-v6 §3.2 (run mode + configure mode definitions, including the embedded-agent half this ADR's structural claim hinges on).
- vision-v6 §6.4 (Phase J's amended scope; the question this ADR resolves descended from §6.4's downstream-consequence paragraph).
- vision-v6 §9 Q2 (OAuth resolution and quarterly re-check discipline; T2 ties here).
- vision-v6 §9 Q4 (paid-vs-self-host value asymmetry — elevated priority post-OAuth resolution; same elevation ADR-002 inherited and this ADR inherits).
- vision-v6 §9 Q11 (the question this ADR resolves; §9 Q11's prose now points at this ADR per the amendment recorded alongside this commit).
- `docs/discovery/2026-04-26-oauth-feasibility-investigation.md` — for the Q1 2026 trajectory the OAuth probability estimates rest on.
- ADR-001 (`docs/adr/001-workflow-versioning.md`) — for tone and the ADR pattern.
- ADR-002 (`docs/adr/002-run-mode-session-persistence.md`) — for structural template; also relevant because ADR-002's analytics-vs-session-data distinction is reinforced by Clause 3's implementation note.
- v5 Phase J scaffold (`docs/vision/2026-04-22-phase-j-scaffold.md`) — superseded by this ADR for the shipping-decision question; remaining content is historical reference.

---

*End of ADR-003. This ADR's commitments hold conditional on Phase G's `/discuss` confirming that configure-mode-naive UI design does not lock out efficient Phase J integration if it later reopens. If Phase G surfaces that the configure-mode-naive assumption fails at acceptable cost, this ADR is reopened, not patched.*
