# ADR-011 — Phase G analytics instrumentation surface and privacy posture

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](../vision/2026-04-27-megalos-vision-v7.md)
**Resolves:** Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) (P) /discuss I — analytics instrumentation surface for [ADR-003](003-phase-j-shipping-decision.md) Clause 3, plus the privacy posture for analytics that ADR-003 Clause 3 implementation note 2 explicitly distinguishes from ADR-002 session-data retention
**Related:** ADR-002 (run-mode session persistence, `002-run-mode-session-persistence.md` — analytics-session-id is **distinct from** ADR-002's session-id and has its own retention regime); ADR-003 (Phase J shipping decision, `003-phase-j-shipping-decision.md` — Clause 3 names the two specific signals this ADR's instrumentation collects); ADR-004 (paid-vs-self-host value asymmetry, `004-paid-vs-self-host-value-asymmetry.md` — (C)/(O) split applied to emission code vs analytics backend); ADR-005 (Library entry versioning UX, `005-library-entry-versioning-ux.md` — `version_prompt_responded` event source); ADR-006 (artifact retention decoupling, `006-artifact-retention-decoupling.md` — analytics is yet another retention regime distinct from artifact retention); ADR-007 (Phase G chat UI stack, `007-phase-g-chat-ui-stack.md` — emission code is in the chat UI source); ADR-008 (brand architecture, `008-brand-architecture.md` — agorá as consumer brand raises the trust bar that this ADR's privacy framing addresses); ADR-010 (Phase G connection model, `010-phase-g-connection-model.md` — backend is where events get persisted).

---

## 1. Context

Vision-v7 inherits from v6 the strategic frame in which Phase G ships configure-mode-naive (per ADR-003 Clause 1) but with two specific signals instrumented from launch (per ADR-003 Clause 3). The signals are the empirical input to any T1 reopening of Phase J: signal (i) — Shape-4 users with IDE-extension access exercising any in-product lightweight-customization affordance; signal (ii) — Shape-4 vs Shape-2 churn at the customization wall.

ADR-003 Clause 3 implementation note 1 binds Phase G to instrument these signals **from launch**, not retroactively. ADR-003 Clause 3 implementation note 2 binds Phase G to keep analytics distinct from ADR-002 session-data retention — analytics is its own discipline with its own privacy and retention posture.

The Phase G roadmap scoping document classified this as (P) /discuss I: the privacy/retention posture is genuinely strategic; the instrumentation surface is design but binds Phase G launch behavior. Both must resolve before Phase G's roadmap can be drafted defensibly. The /discuss specifically depends on C (the chat UI's connection model) — the affordance for "lightweight customization" needs to exist before its exercise can be measured, which means C's configure-mode-naive picker shape (committed in [ADR-010](010-phase-g-connection-model.md)) is upstream of where this ADR plants instrumentation.

A focused /discuss session of 2026-04-27 walked six decision points (privacy/retention posture, self-host emission posture, customization affordance shape, shape segmentation method, analytics framework choice, event schema) against six criteria (distinctness from ADR-002 session retention; (C)/(O) split per ADR-004; self-host autonomy; T1 informability at +6 months; sole-author velocity; privacy-defensibility under the brand-inversion trust bar). Operator review applied four ADR-text refinements (retention as ceiling-not-target framing; sticky-tagging segmentation behavior; PostHog migration trigger expansion to include p95 latency; HMAC-SHA-256 with per-deployment salt for `account_id_hash`) and one schema addition (`version_prompt_responded` event for ADR-005 prompt-response signal). This ADR encodes the result.

## 2. Decision

Six commitments. They hold together; weakening any one weakens the others.

**1. Privacy/retention posture: account-bound, 13-month retention ceiling.** Analytics events are bound to `account_id_hash` (per commitment 6) and **deleted at 13 months** from event timestamp. The framing is critical and load-bearing: the operator commits to **deleting events at 13 months**, not to **retaining events for 13 months**. The privacy policy and the engineering implementation use the same framing — "events older than 13 months are deleted" — because the consumer-trust-defensible phrasing matters under the brand inversion (ADR-008) raises the trust bar above what a technical-layer product would carry. 13 months covers T1's ~6-month firing window plus ~6 months of tail-of-launch trend analysis plus a ~1-month buffer for T1 slipping. Self-host operators can tune retention via `MEGALOS_ANALYTICS_RETENTION_DAYS` from 30 days (a defensible floor for compliance-sensitive deployments) up to indefinite (a defensible ceiling for solo or trusted-team deployments where there is no operational reason to expire events at all). Paid-tier hosted retention is fixed at 13 months at v1; admin-tunable in self-host only.

**2. Self-host emission: opt-in only, off by default.** Default `MEGALOS_ANALYTICS_ENABLED=false`. Self-host operators who want to participate in operator-aggregate research flip the envvar and configure the destination URL via `MEGALOS_ANALYTICS_DESTINATION_URL`. Default behavior emits no analytics. The dotnet-style default-on-with-prominent-disclosure pattern is rejected — it works for language-runtime telemetry where the trust bar is technical-layer; it does not survive contact with the brand inversion that puts agorá at consumer-layer. ADR-003 Clause 3's signals are Shape-4-anchored, and Shape-4 is hosted-tier by definition (per v6 §4 + v7 §4), so self-host emission isn't the load-bearing source for the load-bearing signals — the opt-in posture costs little signal volume while gaining materially on privacy-defensibility.

**3. Customization-wall affordance: explicit "Customize this entry" link in the chat UI from MG1.** A small surface (button, link, menu item — Phase G `/plan` decides exact UX) labeled approximately "Customize this entry" that, when clicked, surfaces a friction-reducing message ("Configure mode is coming in a future release. For now, you can download this entry as YAML and edit it in your editor.") plus links to the file-download path (per v7 §6.3) and the IDE-extension docs. The click event is captured as `customize_intent_clicked` per the event schema in commitment 6. This affordance ships at MG1 alongside the foundation slice — implementation cost is trivial (~30 LOC); information value is high. It also doubles as user-facing utility: the affordance itself tells the user the file-download path exists, which is the desired Shape-2 onramp.

**4. Shape-4 vs Shape-2 segmentation: behavioral proxy with sticky tagging.** A user is tagged at first qualifying event:

- **Shape-2 tag** — applied when the user first uses the file-download path (`file_download_used` event fires).
- **Shape-4 tag** — applied when the user first runs an entry via MCP-connect without ever having used file-download (default tag for users whose only behavior is MCP-connect).

**Sticky tagging on contradicting events.** When a user with one tag emits an event that would have qualified them for the other tag, the new tag is **added** to the user's record (with its own first-occurrence timestamp), rather than overwriting the original tag. A user record can carry both tags with separate timestamps. This enables three cohort-analysis queries:

- **"Users tagged Shape-2 at any point"** — broadest Shape-2-ish cohort.
- **"Users currently tagged Shape-2-only"** — pure-Shape-2 users.
- **"Users tagged Shape-4 → Shape-2 (transition signal)"** — users who started with MCP-only behavior and revealed file-download/IDE-aligned behavior over time. **This is the highest-signal cohort for ADR-003 Clause 3's audience-overlap analysis** — users who started as Shape-4 and revealed Shape-2 behavior are precisely the audience-overlap evidence T1 is looking for.

Implementation cost: ~5 LOC over a simple overwrite-on-cross approach. Cohort-analysis-query expressiveness gain: the transition signal is what T1 was originally configured to ask for.

**5. Analytics framework: custom emit-to-Postgres at v1; PostHog migration triggered by either of two conditions.** v1 uses a single `analytics_events` table in the operator's commercial Postgres instance with a JSON `payload` column. Schema is documented in commitment 6. Aggregation queries run as needed against this table. **PostHog (self-hosted) migration is triggered when either:**

- **(a)** Event volume exceeds ~100k events/day, OR
- **(b)** p95 latency on the standard cohort-analysis query exceeds ~5 seconds.

The two triggers are independent; either firing justifies migration. Condition (b) catches query-pattern-driven friction that volume-driven (a) wouldn't — if cohort queries get more complex than v1 anticipates, p95 latency degrades before raw volume does. Migration is a /plan-time decision when triggered, not a v1 commitment.

The (C)/(O) split is clean: emission code in the chat UI is **(C) Capability** — OSS, identical in both tiers; the `analytics_events` Postgres table and aggregation tooling live in the operator's commercial backend per ADR-010 commitment 4 and are **(O) Operational layer** per ADR-004 commitment 7.

**6. Event schema (7 events at v1) plus identifier discipline.**

Seven events at v1:

| Event | Payload (in addition to standard envelope) |
|-------|--------------------------------------------|
| `session_started` | `entry_id`, `entry_version`, `deployment_type` |
| `session_progressed` | `step_id` |
| `session_completed` | `last_step`, `duration_seconds`, `terminated_state` (one of: `complete`, `abandoned`, `workflow_changed`) |
| `customize_intent_clicked` | `entry_id`, `source_label` |
| `file_download_used` | `entry_id`, `entry_version` |
| `entry_switched` | `from_entry_id`, `to_entry_id` |
| `version_prompt_responded` | `entry_id`, `prompt_action` (one of: `accept_new`, `keep_bound`, `dismiss_unanswered`), `bound_version`, `latest_version` |

Standard envelope on every event: `event_id`, `event_type`, `timestamp`, `account_id_hash`, `analytics_session_id`.

**Identifier discipline:**

- **`account_id_hash` is HMAC-SHA-256(account_id, per-deployment-salt).** The per-deployment salt is stored in operator config (e.g., `MEGALOS_ANALYTICS_HASH_SALT`) and is not included in the analytics database. A non-salted SHA-256 is reversible by anyone with the account_id list (the operator has this); HMAC with a per-deployment salt makes the hash actually defensive — if the analytics database is exfiltrated separately from the main database (different breach surfaces, different access patterns), raw account identities aren't recovered. Cost is zero (one hash call per event, vs unsalted SHA-256); defensive value is real.
- **`analytics_session_id` is distinct from ADR-002's session-id.** ADR-002's session-id is bound to the resumption-state record with a 7-day TTL (paid) or admin-tunable (self-host). The `analytics_session_id` is a stable per-user-per-chat-session identifier — generated once per chat session, retained for 13 months (ceiling), used for cohort and funnel analysis. Implementation must keep these two identifiers in different namespaces and code paths to prevent the conflation ADR-003 Clause 3 implementation note 2 explicitly flags.

The `version_prompt_responded` event is added (vs the original /discuss output) at operator request to capture whether users actually read or auto-dismiss the ADR-005 version-binding prompt. This is the only direct signal on whether ADR-005's design is working post-launch; the prompt-response handler is already in the chat UI per ADR-005 §3, so the event is nearly free to emit.

## 3. Implementation sequencing

**MG1 (Foundation) lands the analytics emission scaffolding.** The chat UI ships the emit-to-backend client; the megalos-server / agorá backend ships the receive-and-write-to-Postgres handler; the `analytics_events` table schema is created as part of the backend's initial migration. The "Customize this entry" affordance lands here per commitment 3. The emission scaffolding ships even though most events fire from later milestones — the seam exists at MG1 so subsequent milestones add events without rebuild.

**MG2–MG5 add events as their corresponding features land.** `session_started` / `session_progressed` / `session_completed` from MG2 (run-mode chat loop); `version_prompt_responded` from MG4 (ADR-005 UX); `entry_switched` from MG3 (catalog-and-picker); `file_download_used` from the agorá backend's "Use in agorá" handler (predecessor work — Phase G chat UI emits the event when the user lands back from a file-download flow).

**The `analytics_events` table and aggregation tooling are operator's commercial code (O).** Schema: `(event_id UUID, event_type TEXT, timestamp TIMESTAMPTZ, account_id_hash TEXT, analytics_session_id UUID, payload JSONB)`. Indexed on `(event_type, timestamp)` and `(account_id_hash, timestamp)`. Standard cohort-analysis queries land alongside the table; query-performance baselines are captured to track against the commitment 5 (b) trigger condition.

**Self-host operators see the analytics scaffolding but emit nothing by default.** The chat UI's emission code is present (it's bundled in the static bundle per ADR-007); but the emission target is unconfigured by default in self-host, so emit-attempts no-op gracefully. Self-host admins who flip `MEGALOS_ANALYTICS_ENABLED=true` and configure `MEGALOS_ANALYTICS_DESTINATION_URL` get a working emit path to whatever destination they configure (could be operator's hosted backend if configured to participate in aggregate research, or could be a self-host operator's own analytics infrastructure — the destination URL is configurable).

**Privacy-policy text** (operator-facing commitment, not ADR scope) discloses the 13-month retention ceiling, the HMAC-hashed `account_id` storage, and the event-type list. ADR-011's commitments are the inputs to the privacy policy; the policy itself is Phase I scoping work.

**Retention enforcement** is a backend job that runs on a schedule (e.g., daily) and deletes events older than the configured retention window (13 months for paid; tunable for self-host). The job is part of the operator's commercial backend tooling (O); it is not a runtime concern of the chat UI or `megalos-server`.

## 4. Consequences

**What this commits agorá to.**

- 13-month retention ceiling on the `analytics_events` table for paid hosted; admin-tunable via `MEGALOS_ANALYTICS_RETENTION_DAYS` for self-host.
- Privacy-policy text framed as "we delete events at 13 months," not "we keep events for 13 months." Engineering surface and policy surface use the same framing.
- `MEGALOS_ANALYTICS_ENABLED=false` as the self-host default; opt-in via envvar.
- A "Customize this entry" affordance in the chat UI from MG1.
- Sticky-tagging segmentation: per-user record may carry both Shape-2 and Shape-4 tags with separate first-occurrence timestamps.
- Custom emit-to-Postgres at v1; PostHog migration as a future move triggered by either >100k events/day or >5s p95 on standard cohort queries.
- Seven event types at v1: `session_started`, `session_progressed`, `session_completed`, `customize_intent_clicked`, `file_download_used`, `entry_switched`, `version_prompt_responded`.
- `account_id_hash` is HMAC-SHA-256 with a per-deployment salt stored in operator config; the salt is not included in the analytics database.
- `analytics_session_id` is namespace-distinct from ADR-002's session-id; code paths and storage are separate.
- Phase I scoping consumes this ADR's commitments when drafting the privacy-policy surface and the analytics-data-deletion-on-request workflow. Both are (O) operational tooling per ADR-004 §3 Group 6 (Compliance and trust).

**What this forecloses.**

- Indefinite retention on paid hosted. 13 months is a hard ceiling at v1; longer retention requires an ADR amendment.
- Default-on telemetry from self-host. The dotnet pattern doesn't survive the brand-inversion trust bar.
- A separate analytics SaaS (PostHog Cloud, Plausible, Mixpanel, etc.) at v1. Custom Postgres is committed; SaaS is a future move.
- Anonymous-only analytics. Sticky-tagging requires stable per-user identity; anonymized-at-emission would defeat the segmentation that ADR-003 Clause 3 requires.
- Overwrite-on-cross tagging. Sticky-tagging is committed because the Shape-4 → Shape-2 transition cohort is the highest-signal cohort for T1 and overwriting destroys it.
- Per-message content emission. Analytics events carry metadata (event types, IDs, timestamps, payload-of-listed-shape) — they do not carry raw user prompts, raw LLM responses, or workflow content. This is a hard line for the privacy-defensibility criterion.
- Conflation of `analytics_session_id` and ADR-002 session-id. ADR-003 Clause 3 implementation note 2 names the distinction; this ADR enforces it structurally.
- Bundling the analytics backend with the runtime Postgres in self-host. Self-host can opt to share the same Postgres instance, but the schema and retention regime are separate from session-store and artifact-store.

## 5. What would have to be true for this to be wrong

Four conditions, named honestly because the decision is not unconditional.

**The 13-month retention ceiling is wrong by an order of magnitude.** If T1 fires later than expected (e.g., +12 months instead of +6 months) and the trailing tail-of-launch analysis still needs signal, 13 months might be too short. Conversely, if regulatory pressure pushes toward shorter retention norms (6–9 months becoming a privacy-compliance default), 13 months might be too long. Mitigation: the retention is admin-tunable at the operator level via the same envvar self-host uses; the policy text and the technical implementation share the same number, so updating one updates both. An amendment to this ADR can shift the ceiling without architectural change.

**Behavioral-proxy segmentation produces noisy or misleading cohort analysis.** "Has used file-download once" might overlap heavily with "uses MCP-connect 99% of the time," making the Shape-2-ish/Shape-4-ish split weaker than expected. The sticky-tagging refinement helps — the transition cohort (Shape-4 → Shape-2) is more interesting than the binary split — but if even the transition cohort is noisy, signal (ii) is degraded. Mitigation: validate segmentation against actual user behavior in the first quarter post-launch; if proxy is too noisy, supplement with an explicit-self-declaration UI surface as a secondary signal at signup, gated behind a Phase I /plan decision.

**The custom emit-to-Postgres approach hits scale issues earlier than expected.** Either trigger (volume or p95 latency) firing means PostHog migration; the cost is an operational uplift (running self-hosted PostHog adds Postgres + Redis + a web service). Mitigation: the migration path is named here as a future move; the trigger conditions are concrete; the chat UI's emission code does not change (it already emits to a configurable URL). Migration is a backend re-implementation, not a chat-UI rewrite.

**HMAC-SHA-256 with per-deployment salt is insufficient defensive hashing.** If a future cryptographic finding weakens HMAC-SHA-256 in a way that affects the `account_id_hash` defensive property, or if the per-deployment salt is itself exfiltrated alongside the analytics database (single-breach scenario rather than two-breach), the hash's defensive value collapses. Mitigation: salt rotation (with re-hashing of historical events) is operationally available; the per-deployment salt is in operator config rather than in the database, which means a database-only breach doesn't recover the salt. If a stronger primitive is needed (e.g., HMAC-SHA-512, or a key-derivation-function-based scheme like HKDF), the migration is a backend job, not an ADR-level architectural change.

## 6. Trigger conditions for revisit

- **T1 — Retention norm shift.** Either regulatory pressure pushes toward shorter norms (e.g., new EU regulation post-GDPR with stricter limits) or T1's audience-overlap analysis turns out to need longer trailing data. Reopen commitment 1's ceiling number; the architecture stays.
- **T2 — Behavioral-proxy segmentation noisy.** First-quarter post-launch validation surfaces that the file-download-vs-MCP-only proxy doesn't separate Shape-2 and Shape-4 meaningfully. Reopen commitment 4 toward supplementary self-declaration or refined behavioral signals.
- **T3 — PostHog migration triggers fire.** Either >100k events/day OR >5s p95 on cohort queries. Reopen commitment 5 toward PostHog (self-hosted) migration. /plan-time work, not architectural reopening.
- **T4 — ADR-002 reopens.** Cross-coupled — the analytics-vs-session-data distinction in this ADR rests on ADR-002's session-retention posture. If ADR-002 reopens, this ADR reopens alongside.
- **T5 — ADR-003 reopens** (per its own T1/T2/T3 triggers). If Phase J reopens, the analytics signals (i) and (ii) may need amendment, addition, or removal depending on the reopened Phase J's information needs.
- **T6 — ADR-005 reopens.** If the version-binding UX changes, `version_prompt_responded` event may need schema amendment (different prompt actions, additional fields).
- **T7 — Privacy regulation change.** A new privacy regulation in a major operating jurisdiction that shifts retention or deletion-on-request norms beyond GDPR. Reopen commitment 1's framing if the "delete at 13 months" framing is no longer compliant with the new regulation.
- **T8 — HMAC-SHA-256 cryptographic weakening.** Reopen commitment 6's identifier discipline toward stronger primitive (HMAC-SHA-512, HKDF-based scheme, etc.). Backend migration; not architectural reopening.

## 7. References

- vision-v7 §3.1 (consumer surface — agorá's chat UI is where instrumentation lives).
- vision-v7 §3.2 (Library — `entry_id` and `entry_version` reference per-folder Library entries).
- vision-v7 §6.3 (file-download path — the behavioral signal for Shape-2 segmentation).
- vision-v7 §6.5 (predecessor work — the catalog website is where "Use in agorá" originates; chat UI emits `file_download_used` when the user lands from this flow).
- Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) — the (P) classification of I that this ADR resolves.
- ADR-001 (`001-workflow-versioning.md`) — `workflow_changed` is a `terminated_state` value in `session_completed` events.
- ADR-002 (`002-run-mode-session-persistence.md`) — analytics-session-id is namespace-distinct; analytics retention is its own discipline.
- ADR-003 (`003-phase-j-shipping-decision.md`) — Clause 3 names the two specific signals; Clause 3 implementation note 2 names the distinction this ADR enforces.
- ADR-004 (`004-paid-vs-self-host-value-asymmetry.md`) — emission code (C); analytics backend (O); §3 Group 6 (compliance and trust) for retention/deletion tooling categorization.
- ADR-005 (`005-library-entry-versioning-ux.md`) — `version_prompt_responded` event captures user response to ADR-005 §2 commitment 2 prompt.
- ADR-006 (`006-artifact-retention-decoupling.md`) — yet another retention regime (artifacts) distinct from analytics.
- ADR-007 (`007-phase-g-chat-ui-stack.md`) — emission code lives in the chat UI source per (C) categorization.
- ADR-008 (`008-brand-architecture.md`) — agorá brand inversion raises the trust bar; the privacy-defensibility criterion that drives commitment 1's framing comes from here.
- ADR-010 (`010-phase-g-connection-model.md`) — backend layer where events get persisted; the connection model's backend-mediated cross-cutting-concerns commitment is the seat of analytics emission target.

---

*End of ADR-011. This ADR's commitments hold conditional on the 13-month retention ceiling matching T1's actual firing window plus tail analysis, and on the behavioral-proxy segmentation producing distinguishable Shape-2 vs Shape-4 cohorts. If post-launch signal surfaces meaningful problems with either, this ADR reopens — likely toward an extended retention amendment (T1) or supplementary segmentation (T2), both contained changes within the architectural frame this ADR commits.*
