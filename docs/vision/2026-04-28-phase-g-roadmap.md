# Phase G — agorá Chat UI Roadmap (MG1–MG5)

**Status:** Planning draft. Canonical for Phase G; consumes the four (P) /discuss outputs (ADR-006, ADR-007, ADR-010, ADR-011) and the synthesized milestone shape from `2026-04-27-phase-g-roadmap-scoping.md` §5.
**Author:** Diego Marono (with strategic review)
**Date:** 2026-04-28
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](./2026-04-27-megalos-vision-v7.md). All decisions in this roadmap defer to v7 where they conflict.
**Shape served:** Shapes 1, 2, 3, and 4 (Shape 5 deferred per [ADR-003](../adr/003-phase-j-shipping-decision.md)).

---

## 1. Context

The runtime is feature-complete against CALM parity after M001–M008. M009 shipped the dry-run inspector; M010 (ADR-001) installed the workflow-versioning correctness property; M011 and M012 closed the authoring-DX gap; M014 closed predecessor work — repo consolidation into `agora-creations/awesome-conversations`, brand architecture rollout (consumer surface = agorá, content layer = Conversations, technical layer = megálos), catalog website MVP at `agora-conversations.dev`. Phase F shipped the mikrós authoring assistant. The runtime ships, the catalog ships, the brand ships. What does not yet exist is a chat UI.

Phase G fills that gap. It is the consumer-facing surface — agorá-branded, run mode plus configure-mode-naive picker, FastMCP Client over progressive tool disclosure, self-host-capable from day one, deployed on Phase H's hardened distribution surface in Phase I to become the paid product.

Phase G has substantial unfamiliar surface. There is no prior chat-UI work in this codebase. The 2026-04-27 scoping pass classified twelve pre-roadmap questions: four required strategic /discuss treatment (D, A+B joint, C, I); three were roadmap-internal (A as roadmap-decided alongside B, H, K); five were per-milestone slice-gate work (E, F, G, J, L). The four (P) /discusses resolved between 2026-04-27 and 2026-04-28 produced four ADRs:

- **[ADR-006](../adr/006-artifact-retention-decoupling.md)** — D's resolution. Artifact retention decouples from session retention via `ArtifactStore` parallel to `SessionStore`, user-captured-explicit model. ADR-002 holds.
- **[ADR-007](../adr/007-phase-g-chat-ui-stack.md)** — A+B's resolution. Svelte 5 + Vite + TypeScript SPA, single static bundle, two delivery paths (self-host bundled into `megalos-server` as package data; hosted served from agorá's CDN with operator's commercial wrapper backend).
- **[ADR-010](../adr/010-phase-g-connection-model.md)** — C's resolution. Pattern B (single backend per session) with MCP-over-HTTP refinement; thin TS MCP client (~300–500 LOC, hand-written, no framework dependency); cross-cutting concerns in the backend layer; per-folder MCP endpoints retained for AI-agent consumption.
- **[ADR-011](../adr/011-phase-g-analytics-instrumentation.md)** — I's resolution. 13-month retention ceiling (delete-at framing); self-host opt-in only; behavioral-proxy segmentation with sticky tagging; custom emit-to-Postgres at v1 with PostHog migration triggers; 7-event schema; HMAC-SHA-256 with per-deployment salt for `account_id_hash`; analytics-session-id namespace-distinct from ADR-002.

The synthesis pass crystallized the MG1–MG5 milestone shape in scoping §5. This roadmap pins those into per-milestone Goal/Scope/Slices/Success/Risk subsections, adds cross-milestone constraints, sequencing rationale, out-of-scope, open questions, and post-phase evaluation — the structural template Phase H established and against which Phase G's milestones can now plan.

Three constitutional constraints carry forward and bind Phase G strictly. **Brand-architecture discipline.** Per ADR-008: agorá is the consumer surface, Conversations is the content layer, megálos is the technical-runtime name. Phase G's UI is agorá-branded throughout; megálos-runtime references stay internal-technical. **Configure-mode-naive.** Per ADR-003 Clause 1: the collection picker is in scope; per-user customized-collection storage and embedded mikrós-reading agent are Phase J only. Phase G does not pre-adapt to Phase J. **Same-default-behavior across paid and self-host.** Per ADR-004: every Phase G surface design decision is categorized as (C) Capability OSS in both tiers, (O) Operational layer paid-only, or (B) Billing-bound paid-only by definition.

---

## 2. Decision: five separate milestones, sequenced

Each functional surface is its own milestone. The alternative — one combined "Phase G chat UI" milestone — was rejected on three grounds. Scope mismatch: MG1 is foundation work (tech-stack scaffold + thin TS MCP client spike + analytics scaffolding) gating every downstream surface, while MG3 is the lightest milestone (switch-entry affordance + configure-mode-naive picker) where the user-visible scope is bounded. Independent shippability: MG1's foundation is invisible to users on its own (no run loop yet); MG2 delivers the first user-visible value (run mode end-to-end); MG3, MG4, MG5 each deliver discrete user surfaces. Bundling delays user-visible value behind heavy work, and bundling cancellation surface — if Phase G post-ship signal underperforms expectations and Phase J reopens before MG5 ships, individual milestones can be deferred or re-prioritized. A combined milestone is harder to suspend partway.

The sequencing MG1 → MG2 → MG3 → MG4 → MG5, with the analytics-instrumentation discipline landing continuously alongside MG2–MG5, follows the same ascending-foundation-then-user-surface criterion used in Phase H's MH1 → MH6 program. The thin-TS-MCP-client spike at MG1 is the gating sub-slice — if it overruns the ADR-010 LOC budget, ADR-010 T1 fires and the FastMCP-JS evaluation begins, which may in turn promote ADR-010 to a follow-up.

---

## 3. MG1 — Foundation

### 3.1 Goal

Establish the entire technical substrate — tech stack, thin TS MCP-over-HTTP client, megalos-server static-bundle integration, hosted-backend stub for OSS smoke testing, analytics scaffolding, and the BYOK API key entry surface. By end of MG1 the chat UI exists as a deployable artifact (no run loop yet) and every downstream milestone has the foundation it needs to land its user-visible features.

### 3.2 Scope

In scope: a Svelte 5 + Vite + TypeScript SPA per ADR-007, with agorá-branded chrome from inception per ADR-008 (consumer-facing language, agorá visual identity, no megálos-runtime references in user-facing copy); a static-build target producing one bundle that ships through both delivery paths; a hand-written thin TS MCP-over-HTTP client per ADR-010 commitment 2 covering the surface the chat loop will exercise (`start_workflow`, `get_state`, `get_guidelines`, `submit_step`, `generate_artifact`, transport-level error handling); the client is **spike-verified at MG1 kickoff** — if the spike overruns ADR-010's ~300–500 LOC budget by more than ~50%, ADR-010 T1 fires; static-bundle integration with `megalos-server` per ADR-007 commitment 2 (UI ships as Python package data; `megalos-server` serves the static assets from its existing HTTP layer); a hosted-backend stub on the outer edge implementing the minimum MCP-over-HTTP transport for development and contract-singularity verification (the full proxy implementation against per-folder endpoints is operator commercial code and parallel to Phase I); a BYOK API key entry surface per (L) — pre-Phase-I client-side storage, provider validation against at least one provider's auth endpoint, settings page; entry-id-from-URL handling so the catalog website's "Use in agorá" landing flow can drop a user into the chat UI with a collection already selected; analytics emission scaffolding per ADR-011 — chat UI client emitter and hosted-stub dev-verification endpoints; per ADR-011 §61 the `analytics_events` Postgres table, HMAC application, and aggregation queries are operator commercial code (O) parallel to Phase I and out of MG1 scope; the "Customize this entry" affordance per ADR-011 commitment 3 (~30 LOC; click captured as `customize_intent_clicked`, no actual customization surface — that is Phase J).

Out of scope: any user-visible run-loop behavior (MG2); any switch-entry affordance or picker (MG3); any version-binding, resumption, or artifact-gallery UX (MG4); any self-host packaging or auth-integration work (MG5); SSR, server-side rendering, or any non-static-build target — explicitly forbidden by ADR-007; tab-manager UX inside the chat UI itself — multi-tab behavior is the browser's native multi-tab per ADR-010 commitment 7; per-collection MCP endpoint discovery surface (the catalog website at `agora-conversations.dev` is the discovery surface; the chat UI consumes already-resolved collections).

### 3.3 Slices

- **S01 — Svelte 5 + Vite + TS scaffold with agorá chrome.** Project init, Svelte 5 runes-mode TS configuration, Vite static-build target, agorá visual chrome (logo, color tokens, typography), no run-loop logic yet. Includes `customize_intent_clicked` affordance scaffold. LOC budget: ~350.
- **S02 — Thin TS MCP-over-HTTP client (spike-gated).** Hand-written client per ADR-010 commitment 2; full surface for downstream chat loop; transport-level error handling; conformance against `megalos-server`'s existing MCP-over-HTTP layer. **This slice is the spike.** If LOC overruns the budget by more than ~50%, ADR-010 T1 fires before the slice closes. LOC budget: ~400 (stretch ~600 before T1).
- **S03 — megalos-server static-bundle integration.** UI ships as Python package data; `megalos-server` serves the static assets from its existing FastMCP HTTP layer; per ADR-007 commitment 2; verification that `pip install megalos-server` then runtime startup serves the bundle correctly. LOC budget: ~150 (mostly Python plumbing + `MANIFEST.in`).
- **S04 — Hosted-backend stub for OSS smoke.** Minimal MCP-over-HTTP transport on the outer edge sufficient for development and contract-singularity verification per ADR-010; operator commercial code (the full proxy + cross-cutting concerns) is parallel work, not in this slice. LOC budget: ~250.
- **S05 — BYOK API key entry surface (L).** Settings page, client-side encrypted local storage, provider validation, at least one provider integrated end-to-end. LOC budget: ~200.
- **S06 — Entry-id URL parameter and catalog landing flow.** The chat UI accepts an entry parameter from the catalog website's "Use in agorá" link; resolution against the user's account-bound entry list (placeholder during MG1, full resolution lands at MG3). LOC budget: ~150.
- **S07 — Analytics emission scaffolding.** Chat UI client emitter + hosted-stub dev-verification endpoints + runtime `/config.json` configuration model. Per ADR-011 §61, the receiver layer (HMAC-SHA-256 hashing, `analytics_events` Postgres table, retention enforcement, aggregation) is operator commercial code (O) parallel to Phase I and out of MG1 scope. `MEGALOS_ANALYTICS_ENABLED` and `MEGALOS_ANALYTICS_DESTINATION_URL` are receiver-layer envvars. Per-event emitters land in subsequent milestones; this slice ships only `customize_intent_clicked` and `file_download_used` from MG1's surface. LOC budget: ~250.

### 3.4 Success criteria

A `pip install megalos-server` followed by runtime startup serves the static bundle on `localhost`. Visiting `localhost/#/entry/<entry-id>` resolves the entry-id-from-URL flow and renders the agorá chrome. The thin TS MCP client successfully exchanges `start_workflow` and a single `get_state` round-trip against the hosted-backend stub and against `megalos-server` directly — both paths verify the contract-singularity claim. The BYOK API key flow accepts a key, validates it against the chosen provider, and stores it client-side. The `customize_intent_clicked` and `file_download_used` events POST envelopes to the configured destination URL (read at app init from `/config.json`) when enabled; zero events emit when `/config.json` returns `enabled: false`, when `/config.json` is absent (404), or when the `destination_url` is unset. Persistence into the `analytics_events` table is operator commercial code (Phase I) per ADR-011 §61 and is not verified at MG1. HMAC-SHA-256 with per-deployment salt is also a receiver-side responsibility — the chat UI emits envelopes carrying raw `account_id` (a browser-bound UUID at MG1, account-bound at Phase I), and the receiver applies HMAC + salt before persistence per the (C)/(O) split. Self-host operators who opt into analytics by configuring a destination URL must implement HMAC at their receiver to inherit the privacy posture; a self-host receiver that persists raw envelopes stores raw account IDs. The `customize` affordance is visible and click-captured. The static-build output is reproducible — same source produces byte-identical `dist/` across two clean builds.

### 3.5 Risk

High. This is the heaviest milestone in Phase G and the riskiest, comparable to MH2 in Phase H's program. Three named risk sources. **Thin TS MCP client overrun.** ADR-010 budgets ~300–500 LOC against the MCP-over-HTTP surface. Hand-written transports historically grow under reality contact (auth-header propagation, retry semantics, streaming-response framing). The S02 spike is the gate; if it overruns, ADR-010 T1 escalates to FastMCP-JS evaluation, which may add a milestone-equivalent of work and re-open ADR-010. Mitigation: spike against a real `megalos-server` from S02 day one; do not stub the server side. **Static-bundle integration friction.** Vite's static-build output and `megalos-server`'s FastMCP HTTP layer have not previously interoperated. Path resolution under `pip install` differs from path resolution under `uv run` differs from path resolution under a built wheel; package-data discovery semantics in Python differ across `setuptools`, `hatchling`, and `flit`. Mitigation: stand up the integration in a smoke test from S03 day one and exercise the wheel-built path before the slice closes. **Analytics privacy posture verification.** ADR-011 mandates HMAC-SHA-256 with per-deployment salt and 13-month retention — both are commitments the operator commercial code must enforce, but the client-side emitter must be architected to make those commitments expressible without leaking raw identifiers. Mitigation: the S07 design must be reviewed against ADR-011 commitments 4 and 5 explicitly before slice close.

---

## 4. MG2 — Run-mode chat loop

### 4.1 Goal

Land the user-visible execution surface. By end of MG2 a user can run a Conversation from start to artifact via the chat UI: start a session against an entry, walk the directive/gate/anti-pattern loop, see step state and gate flagging, hit `generate_artifact`, and have the artifact land in `ArtifactStore` per ADR-006.

### 4.2 Scope

In scope: orchestration of the directive/gate/anti-pattern run loop in the chat UI per ADR-010's MCP-over-HTTP client — the sequence `get_state` → `get_guidelines` → LLM call browser-direct → `submit_step` repeats until terminal; progressive tool disclosure per v7 §2 + v6 §2 carryover (tool definitions loaded incrementally rather than upfront); step-state rendering surfacing what step is active, what gates apply, what anti-patterns were flagged; `workflow_changed` envelope UX (J) per ADR-001 — terminal-state rendering with a clear "start a new session" recovery path; `generate_artifact` integration that triggers persistence to the user-bound `ArtifactStore` per ADR-006 (Phase G's chat UI emits the capture trigger; backend writes the row); per-event emitters land — `session_started`, `session_progressed`, `session_completed` per ADR-011 commitment 6.

Out of scope: any switch-entry affordance, picker, or multi-entry surface (MG3); any version-binding prompt, resume affordance, or artifact-gallery surface (MG4); any self-host distribution work (MG5); custom system-prompt UX; conversation-branching UX; session-mid-flight collection-switch (forbidden — `workflow_changed` is a session-killing terminal state per ADR-001); offline mode or service-worker caching; rich-media rendering inside the chat (Phase J); voice-mode UX; mobile-specific layouts beyond reasonable responsive design.

### 4.3 Slices

- **S01 — Run-loop orchestration.** Driver component executing `start_workflow` → loop(`get_state` → `get_guidelines` → LLM call → `submit_step`) → terminal; error envelopes surfaced; integrates with the S02 client from MG1. LOC budget: ~400.
- **S02 — Progressive tool disclosure.** Tool definitions loaded incrementally per the disclosure protocol; the chat UI defers loading inactive-step tools until they become active. LOC budget: ~200.
- **S03 — Step-state rendering.** Visual surface for active step, applicable gates, flagged anti-patterns; integrates with `get_state`'s schema. LOC budget: ~300.
- **S04 — `workflow_changed` envelope UX (J).** Terminal-state rendering with copy that explains the situation in agorá-consumer language (not megálos-runtime jargon) and a clear recovery affordance. LOC budget: ~150.
- **S05 — `generate_artifact` + `ArtifactStore` write.** Trigger from the chat UI; backend persists per ADR-006's user-captured-explicit model; success/failure surfaces in the UI; per-event emitters (`session_started`, `session_progressed`, `session_completed`) land. LOC budget: ~200.

### 4.4 Success criteria

A user lands from the catalog at `agora-conversations.dev`, picks an entry, runs through the entire loop, and produces an artifact persisted in `ArtifactStore`. The progressive-tool-disclosure surface loads tool schemas only as steps become active (verified by inspecting client-side network traffic). Step state, gate applicability, and anti-pattern flags render correctly across at least three reference Conversations (one each from analysis, professional, writing collections). A mid-flight workflow YAML edit on the server triggers `workflow_changed` and the UI renders the recovery surface with consumer-language copy. `session_started`, `session_progressed`, and `session_completed` events emit at the right transition points (verified against `analytics_events` table when `MEGALOS_ANALYTICS_ENABLED=true`).

### 4.5 Risk

Medium. The runtime surface is well-pinned (`get_state`, `get_guidelines`, `submit_step`, `generate_artifact` are all stable), but the chat UI's orchestration of them is novel. Two named risk sources. **LLM call topology.** Browser-direct LLM calls (per ADR-010's Pattern B) put auth-key handling on the client. The BYOK surface from MG1 S05 must hold up under load — re-validate that key persistence, error envelopes, and failure-recovery paths work for the run loop, not just the settings-page smoke test. **Step-state schema drift.** `get_state`'s envelope shape evolved across M001–M008 and again at M010. The chat UI binds to whatever shape ships; if the runtime extends the schema during MG2 development, the UI breaks. Mitigation: pin against a tagged `megalos-server` version for MG2 development and update the pin once MG2 lands.

---

## 5. MG3 — Catalog and picker (configure-mode-naive)

### 5.1 Goal

Land the in-product entry-switching affordance and the configure-mode-naive picker per ADR-003 Clause 1. By end of MG3 a user can switch between entries they have account-bound sessions against, browse the user's account-bound entry list, and exercise the configure-mode-naive picker. The catalog website's discovery surface (predecessor work) is unchanged; MG3 is the in-product complement.

### 5.2 Scope

In scope: the "switch entry" affordance per ADR-010 commitment 8 — surfaces the user's account-bound entry list (resolved by the backend per ADR-005) and lets the user move between entries; configure-mode-naive picker per ADR-003 Clause 1, surfacing the available entries with descriptions, no per-user customization controls (those are Phase J); multi-entry browser-tab session topology per ADR-010 commitment 7 — each browser tab is one MCP-over-HTTP session against one entry; backend tracks per-(user, entry) session state per ADR-002; K folds in here — the catalog website remains the public discovery surface, the in-product affordance is for already-known entries the user has interacted with; `entry_switched` emitter per ADR-011 commitment 6.

Out of scope: any per-user customized-entry storage (Phase J); any embedded mikrós-reading or configure-mode authoring surface (Phase J); any in-product duplication of the catalog website's full discovery surface (the catalog at `agora-conversations.dev` is canonical for discovery); any version-prompt UX (MG4); any artifact-gallery surface (MG4); cross-entry session migration (forbidden — sessions are per-(user, entry) per ADR-002); collaborative or shared-session topology.

### 5.3 Slices

- **S01 — Switch-entry affordance and account-bound list resolution.** Backend endpoint resolving the user's account-bound entry list; chat UI affordance surfacing the list; clicking moves the active tab to the chosen entry. LOC budget: ~250.
- **S02 — Configure-mode-naive picker.** Surface listing available entries with descriptions; integrates with the catalog metadata; explicitly does not surface per-user customization. LOC budget: ~300.
- **S03 — Multi-entry browser-tab topology.** Each tab establishes its own MCP-over-HTTP session per ADR-010; backend tracks per-(user, entry) per ADR-002; verification across at least three concurrent tabs against three distinct entries. `entry_switched` emitter lands. LOC budget: ~150.

### 5.4 Success criteria

A user with sessions against entries A and B sees both in the switch-entry affordance and can move between them in one click; the previously-active session for the entry being switched away from is preserved (not killed). The configure-mode-naive picker surfaces all entries from the catalog with their descriptions and zero per-user customization controls. Three browser tabs against three distinct entries operate independently, each with their own MCP-over-HTTP session, with no cross-tab state leakage. `entry_switched` events emit at the right transition points.

### 5.5 Risk

Low. The smallest milestone in Phase G. The main risk is scope creep into Phase J's customization surface — the configure-mode-naive constraint must hold at the slice gate. Configure-mode-naive means: a picker that lets users choose between curated entries, with zero affordance for per-user customization. If a slice proposes any form of "save my preference for entry X" or "remember my settings," that is Phase J, not MG3. Guard at S02's `/discuss` gate.

---

## 6. MG4 — Persistence and continuity UX

### 6.1 Goal

Bundle three user-visible state-continuity surfaces — version-prompt + display + binding-log UX (ADR-005, H), session-resumption affordance + pre-Phase-I transition UX (ADR-002, E + F), and artifact-gallery / saved-outputs surface (ADR-006). All three are surfaces the user sees about state continuity across sessions, versions, and artifacts; the design coherence wins from bundling. By end of MG4 a user can see what version of an entry they are bound to, resume an in-flight session per entry, and retrieve their saved artifacts.

### 6.2 Scope

In scope: version-prompt + display + binding-log UX per ADR-005 §2 commitments 1+2+4 (H) — account-bound version binding per (user, entry); non-blocking session-start prompt with `[Upgrade to V_latest] / [Stay on V_user]` (default Stay) for entries where the user's bound version differs from latest; critical-fix carve-out auto-migrates for CVE-class fixes per ADR-005; version-binding log as a first-class user-visible feature surfacing the user's bound-version history per entry; single-click resume affordance per ADR-002 §2 commitment 1 (E) — one entry-point per collection the user has an in-flight session against, no ChatGPT-shaped sidebar; pre-Phase-I "Resume in this tab" affordance + transition UX per ADR-002 §3 (F) — browser-local `session_id` resumption during the Phase G → Phase I window, with clear in-product copy signaling that account-bound resumption arrives with the managed-tier launch; artifact-gallery / saved-outputs surface per ADR-006 — the user-captured-explicit retrieval surface, distinguishing "your conversation expired" from "your saved artifacts are still here"; `version_prompt_responded` emitter per ADR-011 commitment 6 — the only direct signal on whether users actually engage with or auto-dismiss the version-binding prompt.

Out of scope: any cross-entry artifact aggregation or search surface (Phase J or later); any conversation-replay or transcript-retrieval surface (artifacts are the captured outputs, not conversation transcripts — ADR-006 commitment); any export-to-external-system flow for artifacts (Phase I or later); any account-management surface for the version-binding log beyond display (no "delete my history" or "share this binding" affordances in Phase G); any operator-side version-binding intervention surface; any pre-Phase-I cross-device resume (intentionally degraded to single-tab resume; ADR-002 commitment).

### 6.3 Slices

- **S01 — Version-prompt + display + binding-log UX (H).** Account-bound version binding per ADR-005; non-blocking prompt at session start; critical-fix carve-out auto-migrate path; binding-log surface; `version_prompt_responded` emitter. LOC budget: ~400.
- **S02 — Single-click resume affordance (E).** One entry-point per collection the user has an in-flight session against; integrates with backend per-(user, entry) session tracking. LOC budget: ~200.
- **S03 — Pre-Phase-I "Resume in this tab" + transition UX (F).** Browser-local `session_id` resumption; in-product copy explaining the managed-tier transition. LOC budget: ~150.
- **S04 — Artifact-gallery / saved-outputs surface.** ArtifactStore retrieval per ADR-006; UX distinguishing expired-conversation from preserved-artifacts states. LOC budget: ~350.

**Possible split:** if MG4 runs heavy at design time, split into MG4a (S01+S02+S03 — version + resumption) and MG4b (S04 — artifact gallery). The decision lands at MG3 close, not pre-committed here. The reason for the split point: S01–S03 are session-state continuity, S04 is artifact-state continuity, and they can ship independently with the rest of MG4 deferred if signal warrants.

### 6.4 Success criteria

A user with a bound-version V_user against entry E, where the entry has shipped V_user+1, sees the version prompt at session start with `[Upgrade] / [Stay]` and a default of Stay; pressing either button stamps the chosen binding into the binding-log; pressing neither (auto-dismiss) preserves V_user binding. A critical-fix release auto-migrates without prompting. The binding-log surface displays the user's full per-entry version history. A user with an in-flight session against entry E sees a single-click resume affordance from the picker. The pre-Phase-I "Resume in this tab" affordance recovers a session within the same browser tab; the transition copy mentions managed-tier explicitly. The artifact-gallery surface lists all artifacts the user has captured via `generate_artifact`, with clear separation from session-expiry messaging. `version_prompt_responded` emits with the user's choice (`upgraded` / `stayed` / `auto_dismissed`).

### 6.5 Risk

Medium. The bundle is intentionally coherent — version binding, session resumption, and artifact retrieval are all forms of state continuity — but the design surface is the largest in Phase G. Two named risk sources. **Version-binding semantics interaction with `workflow_changed`.** ADR-001's `workflow_changed` envelope fires on fingerprint change; ADR-005's version binding is per-(user, entry) at the version axis. If a user is bound to V_user and the runtime's filesystem registry serves V_user+1 (because the deploy promoted a new version mid-session), `workflow_changed` fires and kills the session. The version-binding UX must explain this consistently — the binding does not protect against `workflow_changed`; the binding governs which version the user starts a new session against. Mitigation: S01's design includes explicit copy on this distinction, reviewed at the slice gate. **Pre-Phase-I transition UX setting wrong expectations.** "Resume in this tab" is intentionally degraded relative to what Phase I delivers (cross-device, account-bound resume). The copy must signal that without overpromising and without underdelivering. Mitigation: copy review at S03 close, against the ADR-002 §3 transition framing.

---

## 7. MG5 — Self-host distribution and auth integration

### 7.1 Goal

By end of MG5, self-host single-binary works end-to-end per ADR-007 commitment 2: `pip install megalos-server`, run, browse to `localhost`, see agorá UI, exercise run mode against a local entry. Auth integration consumes Phase H MH5's `X-Forwarded-User` header per ADR-002 §3 + ADR-004 commitment 5. Self-host analytics opt-in surface lands per ADR-011 commitment 2.

### 7.2 Scope

In scope: package-data bundling — UI ships as Python package data inside `megalos-server`, distributed via `pip install megalos-server` as a single artifact; `X-Forwarded-User` consumption (G) per Phase H MH5 + ADR-002 §3 — the chat UI consumes the header populated by upstream proxy auth, with documented behavior on absence (default to anonymous-equivalent, or `deny-anonymous` per Phase H MH5 envvar); Phase H MH1 deployment-recipes coupling — verification that the static-bundle integration plays cleanly with MH1's Docker/Compose/K8s/Helm recipes (`pip install megalos-server`, run, browse to `localhost`, see agorá UI); self-host analytics opt-in envvar surface per ADR-011 commitment 2 — `MEGALOS_ANALYTICS_ENABLED=false` by default, emission target configurable via `MEGALOS_ANALYTICS_TARGET`, admin documentation explaining the opt-in path; `MEGALOS_ANALYTICS_RETENTION_DAYS` envvar surfaced with admin documentation.

Out of scope: any commercial-tier auth surface — that is Phase I (B); any non-`X-Forwarded-User` auth integration (OIDC, SSO, OAuth flows inside megálos-server are forbidden per Phase H MH5 §7.2); any Phase H deployment-recipe authoring (those are Phase H MH1 — Phase G consumes them, does not author them); any commercial-tier analytics target surface (the operator's hosted Postgres is operator commercial code; Phase G's self-host analytics target is the self-hoster's own Postgres or a configured external target); cross-region or multi-tenant self-host configurations.

### 7.3 Slices

- **S01 — Package-data bundling and `pip install` smoke.** UI ships as Python package data; `MANIFEST.in` and `pyproject.toml` adjustments; `pip install megalos-server` then runtime startup serves the bundle in a fresh venv. LOC budget: ~150.
- **S02 — `X-Forwarded-User` consumption.** Chat UI consumes the header populated by upstream proxy auth per Phase H MH5; behavior on absence documented; `deny-anonymous` envvar respected per MH5. LOC budget: ~200.
- **S03 — Phase H MH1 deployment-recipes coupling.** Verification that the static-bundle integration works cleanly across Docker/Compose/K8s/Helm; smoke tests added to existing Phase H integration-test harness. LOC budget: ~150 (mostly verification + docs).
- **S04 — Self-host analytics opt-in surface.** `MEGALOS_ANALYTICS_ENABLED`, `MEGALOS_ANALYTICS_TARGET`, `MEGALOS_ANALYTICS_RETENTION_DAYS` envvars; admin documentation in `docs/CONFIGURATION.md`; default behavior with the flag unset is zero emissions (verified). LOC budget: ~150.

### 7.4 Success criteria

A self-hoster runs `pip install megalos-server` in a fresh venv, runs the server, browses to `localhost`, and sees the agorá chat UI; they can run a Conversation end-to-end against a local entry. A request carrying `X-Forwarded-User: alice@example.com` produces a session with `owner_identity` populated accordingly; `deny-anonymous` mode rejects requests without a populated identity. The chat UI bundle works under each of Phase H MH1's deployment recipes (Docker, Docker Compose, K8s, Helm) — verified by integration tests. With `MEGALOS_ANALYTICS_ENABLED=false` (default), zero events emit; with `=true` and a configured `MEGALOS_ANALYTICS_TARGET`, events emit to the configured target. `MEGALOS_ANALYTICS_RETENTION_DAYS` is documented with default `395` (13 months) per ADR-011.

### 7.5 Risk

Low–medium. The work is mostly integration and configuration. Two named risk sources. **Package-data path resolution edge cases.** `pip install` from a wheel resolves package-data paths differently from `uv run` in a development checkout. Mitigation: smoke-test both paths at S01 close. **Phase H MH1 dependency.** MG5 S03 verifies coupling against MH1's recipes, which means MG5 cannot fully ship until MH1 has shipped. Sequencing rationale (§9) addresses this; if MH1 is not yet shipped at MG5 kickoff, S03 ships partial and full verification follows when MH1 lands.

---

## 8. Cross-cutting: analytics instrumentation across MG1–MG5

Per ADR-011 + ADR-003 Clause 3 implementation note 1: instrumentation is launch-time, not retroactive. Each milestone's slices carry their own emitters per ADR-011 commitment 6. Analytics is not a separate milestone — it is a discipline applied across all five, mirroring Phase H MH6's "lands continuously alongside MH2–MH5" pattern.

| Event | Lands in slice |
|-------|----------------|
| `customize_intent_clicked` | MG1 S01 (affordance) + MG1 S07 (emitter) |
| `file_download_used` | MG1 S07 (emitter and trigger — "Download YAML" link in the Customize affordance's friction-message); MG2 S05 adds artifact-download trigger |
| `session_started`, `session_progressed`, `session_completed` | MG2 S05 |
| `entry_switched` | MG3 S03 |
| `version_prompt_responded` | MG4 S01 |

The analytics scaffolding (chat UI client emitter + runtime `/config.json` configuration model + hosted-stub dev-verification endpoints) lands at MG1 S07; the receiver layer (handler, Postgres table, HMAC-SHA-256 hashing, retention enforcement) is operator commercial code (O) per ADR-011 §61 and lands parallel to Phase I. Per-event emitters land alongside their feature milestones. Self-host opt-in envvar surface lands at MG5 S04. The 7-event schema per ADR-011 covers Phase G surface; future events require an ADR-011 amendment.

---

## 9. Cross-milestone constraints

The following invariants bind every Phase G milestone and should be checked at each slice gate.

**Brand-architecture discipline.** Per ADR-008: agorá is the consumer surface, Conversations is the content layer, megálos is the technical-runtime name. Phase G's UI is agorá-branded throughout — visual identity, copy, product naming. megálos-runtime references stay internal-technical (server logs, error envelopes that bubble up untranslated, debug surfaces). User-facing copy uses agorá-consumer language; megálos-runtime jargon does not leak into the chat UI's user surfaces. `workflow_changed`'s UX (MG2 S04) is the canonical example: the runtime's envelope name stays internal, but the UI's terminal-state copy uses consumer language ("the conversation has been updated; please start a new session" or similar).

**Configure-mode-naive design holds.** Per ADR-003 Clause 1: no slice ships per-user customized-collection storage, embedded mikrós-reading agent, or any form of in-product authoring. The picker (MG3) lets users choose between curated entries; it does not let users customize them. If a slice proposes "save my preferences for entry X" or "edit this entry," that is Phase J. Guard at every slice's `/discuss` gate.

**(C)/(O)/(B) categorization at every design surface.** Per ADR-004: every Phase G surface is categorized. (C) Capability OSS ships in both tiers — chat UI itself, run loop, picker, version-binding UX, artifact gallery, BYOK key entry. (O) Operational layer is paid-only — the hosted backend's full proxy implementation, the operator's commercial-tier analytics Postgres, hosted-tier auth, hosted-tier billing UI. (B) Billing-bound is paid-only by definition — usage caps, plan management, payment surfaces (all Phase I). Phase G's OSS scope is (C) only. The hosted-backend stub at MG1 S04 is the OSS contract surface; the full proxy is parallel commercial code per ADR-007 commitment 7 + ADR-010 commitment 4.

**Schema stability.** Phase G is consumer-side work; `megalos-server`'s YAML schema, MCP-over-HTTP envelope shapes, and `analytics_events` schema are inherited unchanged. If a Phase G milestone wants to change them, the design is wrong. Vision-v5 guardrail 6 (expressiveness ceiling holds) applies. The one exception: ADR-006's `ArtifactStore` is new, so MG2 S05's persistence path adds a new table — that is the artifact-storage decoupling, not a schema change to existing surfaces.

**Same default behavior across paid and self-host.** Per ADR-004: every (C) Capability surface behaves identically in both tiers. The chat UI does not feature-gate (C) capabilities; users in self-host get the same run loop, same picker, same artifact gallery as users in paid. (O) and (B) surfaces appear in paid tier only. Self-host users see "this feature is in the managed tier" copy where (O) or (B) surfaces would otherwise appear, not silent-no-op behavior.

**Public-surface hygiene.** Per `CLAUDE.md`: GSD-2 coordinates (M014, S04, T03) do not leak into commits, PR titles, repo files, or user-facing copy. The chat UI's source code (separate repo or inside `megalos-server` per the §12 open question) does not carry `mg1_s07_` filename prefixes or `MG1/S07/T01` annotations. Describe the thing by its function, not by its plan coordinate.

**Everything is a runtime client.** Vision-v5 guardrail 4 restated for Phase G context. The chat UI is one client of `megalos-server`, alongside the CLI tools, the IDE extension, the dry-run inspector, and (eventually) any Phase J authoring surface. The chat UI does not get a private API or a special path; it consumes the same FastMCP HTTP surface every other client consumes.

---

## 10. Sequencing rationale

### Within Phase G

MG1 → MG2 → MG3 → MG4 → MG5, with analytics instrumentation landing alongside each milestone's user-facing slices. The order is chosen against three criteria.

Ascending foundation-to-user-surface. MG1 is foundation; until it lands, no user-visible surface ships. MG2 is the first user-visible value (run mode end-to-end). MG3 lightens; MG4 bundles the heaviest user-surface design work into one milestone; MG5 closes with self-host integration.

Descending dependency density. MG1 is the gate for everything. MG2 depends on MG1 (the thin TS MCP client and the static-bundle integration). MG3 depends on MG2 (the run loop must work before switching between entries makes sense). MG4 depends on MG2 (`generate_artifact` must work before the artifact gallery surfaces it; the version-binding UX must integrate with run-mode session start). MG5 depends on MG4 only loosely (Phase H MH1 dependency is more load-bearing).

Spike-gate at MG1. The thin TS MCP client is the riskiest single sub-slice in Phase G. If the spike overruns the ADR-010 budget, ADR-010 T1 fires and the FastMCP-JS evaluation may add a milestone-equivalent of work. Sequencing this at MG1 S02 means the rest of the program either proceeds with confidence or re-plans against the new shape — not midway through MG3 or MG4.

An acceptable refinement: ship MG3 before MG2 if early signal from the catalog-website MVP suggests users want to browse entries before running them. This is an unlikely shift — running is the value, switching is the convenience — but flagged here for completeness. If it materializes, the re-plan happens at the MG1 → MG2 boundary, not pre-committed here.

### Phase G relative to predecessor work, Phase H, Phase I, Phase J

**Predecessor work (M013–M014).** Shipped. Catalog website at `agora-conversations.dev`, repo consolidation, brand architecture rollout. Phase G's MG1 S06 consumes the catalog website's "Use in agorá" landing flow; without predecessor work, MG1 S06 has no entry point to consume.

**Phase H.** Phase G ships before Phase H completes. MG5 S03 verifies coupling against Phase H MH1's deployment recipes; if MH1 is not yet shipped at MG5 kickoff, S03 ships partial and full verification follows when MH1 lands. Phase G does not architecturally depend on MH2/MH3/MH4 (the multi-replica state work) — Phase G's hosted-backend stub at MG1 S04 is single-process; the operator's full proxy (parallel commercial code) is what consumes MH2/MH3/MH4 to scale. MG5 S02's `X-Forwarded-User` consumption is the only direct integration point with Phase H MH5.

**Phase I.** Phase G ships before Phase I begins. Pre-Phase-I, paid agorá run mode operates at effective Level 0 (no account binding) per ADR-002 §3. MG4 S03's "Resume in this tab" affordance is the explicit pre-Phase-I transition UX. Phase I consumes Phase G's (C) Capability surface and adds the (O) Operational and (B) Billing-bound layers; it does not modify Phase G's OSS scope.

**Phase J.** Deferred indefinitely per ADR-003. Phase G is configure-mode-naive by design. If Phase J reopens (per ADR-003's T1/T2/T3 triggers), Phase J adapts to whatever Phase G has built; Phase G does not pre-adapt to Phase J. The configure-mode-naive constraint at MG3 is the discipline that keeps this clean.

**Conversations curation.** Parallel sustained track. Phase G's run loop consumes Conversations; new entries added to `agora-creations/awesome-conversations` become available to Phase G's chat UI without Phase G re-shipping.

---

## 11. Out of scope for Phase G

These are strategic questions Phase G does not answer, listed explicitly so that scope creep during implementation is caught at the `/discuss` gate rather than at merge time.

- **Per-user customized-entry storage, in-product authoring, embedded mikrós-reading agent.** Phase J. Configure-mode-naive constraint.
- **Hosted-tier auth, billing UI, plan management, multi-tenant isolation.** Phase I (B Billing-bound).
- **Cross-device session resume, account-bound persistence beyond version-binding.** Phase I.
- **Cross-region or multi-tenant self-host configurations.** Phase H ceiling is single-region multi-replica; Phase G inherits.
- **Operator's full hosted-backend proxy, commercial-tier analytics Postgres, retention-enforcement job.** Operator commercial code, parallel to Phase I; Phase G ships the OSS stub at MG1 S04 only.
- **PostHog migration, alternative analytics targets.** ADR-011 pins emit-to-Postgres at v1 with documented migration triggers; Phase G does not pre-implement the migration.
- **Conversation transcript export, replay, branching, sharing.** Phase J or later.
- **Voice-mode UX, mobile-native apps, browser-extension surfaces.** Not Phase G; not currently scoped to any phase.
- **Workflow marketplace mechanics, user-contributed Conversations submission flow.** Curated catalog only; Conversations curation is a parallel sustained track operated by the maintainer.
- **Auth protocols inside megálos-server.** Phase H MH5 §7.2 is canonical: megálos-server consumes upstream proxy headers, never implements auth.
- **Schema changes to `megalos-server`'s YAML or MCP-over-HTTP envelope shapes.** Schema-stability constraint.

---

## 12. Open questions

The following resolve at per-milestone `/discuss` gates, not preemptively.

**Where does the agorá chat UI source live?** Separate repo (e.g., `agora-creations/agora-ui`) bundled as Python package data, or inside `megalos-server` directly. v7 §8 punts this to predecessor-work `/plan` time before MG1 begins; if predecessor-work `/plan` did not resolve it, MG1 S01's `/discuss` gate is the deadline. Default lean: separate repo, bundled as package data — keeps the chat UI's release cadence independent of `megalos-server`'s.

**Hosted-backend stub depth.** How much OSS smoke-test coverage does the MG1 S04 stub need to verify the contract-singularity claim against the operator's full proxy? Decide at MG1 S04's `/discuss`. Lean toward the minimum that exercises every MCP-over-HTTP envelope shape the chat UI uses, no more — the full proxy's behavior under load, retry semantics, and operator-side cross-cutting concerns are commercial-code concerns, not OSS smoke-test concerns.

**Spike outcome and ADR-010 T1 trigger.** The thin TS MCP client at MG1 S02 is budgeted at ~300–500 LOC per ADR-010; T1 fires if the spike overruns by more than ~50% (i.e., > ~750 LOC). If T1 fires, what is the FastMCP-JS evaluation's milestone shape — a dedicated MG-prefix milestone or a re-plan of MG1? Decide at the moment T1 fires, not preemptively. If T1 does not fire, this question closes.

**MG4 split.** MG4 bundles version-prompt + resumption + artifact-gallery into one milestone. If at MG3 close the design surface looks too heavy, split into MG4a (S01+S02+S03 — session-state continuity) and MG4b (S04 — artifact-state continuity). Decide at MG3 close, not pre-committed.

**MG5 sequencing relative to Phase H MH1.** MG5 S03 verifies coupling against Phase H MH1's deployment recipes. If Phase H MH1 has not shipped at MG5 kickoff, what is MG5 S03's behavior — defer to a follow-up, or ship partial verification and complete when MH1 lands? Default: ship partial (Docker only, since the existing repo Dockerfile predates MH1) and complete the K8s/Helm verification when MH1 ships. Decide at MG5 S03's `/discuss`.

**Configure-mode-naive picker copy and visual treatment.** ADR-003 Clause 1 commits the constraint; the visual and copy treatment that signals "this is a curated catalog you choose from" without inviting customization expectations is design work. MG3 S02's `/discuss` gate.

**Pre-Phase-I transition copy.** MG4 S03's "Resume in this tab" affordance must signal the managed-tier transition without overpromising or underdelivering. Specific copy reviewed at slice gate; ADR-002 §3 provides the framing.

---

## 13. Post-Phase-G evaluation

After Phase G ships, run the post-milestone evaluation across the existing five dimensions — timed-user validation, workflow completion rate, multi-provider validation, runtime stability boundary, documented correction-loop recovery cases. Add three dimensions specific to Phase G.

**Run-mode session completion rate.** Percentage of `session_started` events that reach a terminal state — `session_completed`, `workflow_changed` recovery, or explicit user abandonment — versus sessions that die mid-flight from runtime or UI errors. Target: above 90% non-error termination. If this falls below the threshold, MG2's run-loop or MG4's session-resumption is broken in production-realistic conditions and needs a follow-up. The metric is computable from `analytics_events` in deployments where `MEGALOS_ANALYTICS_ENABLED=true`; self-host deployments without analytics rely on operator-side logs.

**Artifact-capture invariant.** Every `session_completed` event must correspond to at least one `ArtifactStore` row written by the same session. The invariant that `generate_artifact` ran successfully before the session terminated. If this fails — sessions completing without artifacts — MG2 S05's `generate_artifact` integration shipped with a correctness bug. A concrete pass/fail check, not a timing dimension.

**Self-host single-binary onboarding time.** Time-to-first-successful-session for a self-hoster starting from `pip install megalos-server` on a fresh venv, through running the server and reaching a working chat UI on `localhost`, to completing one Conversation end-to-end. Target: under 15 minutes. If this exceeds the target, MG5's package-data integration or the documentation surface is insufficient — a docs-iteration follow-up rather than a milestone-level problem.

If all three succeed alongside the existing five dimensions, Phase G is complete and Phase I (hosted agorá platform) becomes architecturally possible. Phase I's own design conversation can begin at that point. Phase I requires Phase H MH2/MH3/MH4 in addition to Phase G — the parallel-track dependency between Phase G and Phase H means both must be substantially complete before Phase I begins.

---

## 14. Summary

| Milestone | Scope | Slices | LOC est. | Risk | User surface |
|-----------|-------|--------|----------|------|--------------|
| MG1 — Foundation | Svelte 5 + Vite + TS scaffold; thin TS MCP client (spike-gated); static-bundle integration; hosted-backend stub; BYOK; analytics scaffolding | 7 | ~1750 | High | None user-visible (foundation) |
| MG2 — Run-mode chat loop | Run loop; progressive tool disclosure; step-state rendering; `workflow_changed` UX; `generate_artifact` + `ArtifactStore` | 5 | ~1250 | Medium | First user-visible value: end-to-end run mode |
| MG3 — Catalog and picker | Switch-entry affordance; configure-mode-naive picker; multi-tab session topology | 3 | ~700 | Low | In-product entry switching |
| MG4 — Persistence and continuity UX | Version-prompt + binding-log; single-click resume; pre-Phase-I transition; artifact gallery | 4 (possibly split into MG4a + MG4b) | ~1100 | Medium | State continuity across sessions, versions, artifacts |
| MG5 — Self-host distribution and auth | Package-data bundling; `X-Forwarded-User` consumption; Phase H MH1 coupling; analytics opt-in envvars | 4 | ~650 | Low–medium | Self-host single-binary onboarding |

Five milestones, sequenced foundation-to-user-surface with the analytics-instrumentation discipline landing continuously alongside MG2–MG5. Each independently shippable for the user-surface milestones (MG2 is the first user-visible value; MG3, MG4, MG5 each deliver discrete user surfaces); MG1 is the foundation gate. Together they deliver the agorá chat UI: run mode, configure-mode-naive picker, persistence and continuity UX, self-host single-binary distribution, and the (C) Capability surface that Phase I will consume to deliver the paid product.

Phase G serves Shapes 1, 2, 3, and 4. Shape 5 (visual studio, template library, consumer-subscription onramp for non-technical authors) is deferred per ADR-003. The configure-mode-naive constraint at MG3 is the discipline that keeps Phase J adaptable when (if) it reopens.

At sole-author pace, Phase G is a four-to-six-month investment after predecessor work lands per v7 §6.5. Combined with Phase H, Phase I, and the deferred Phase J, the remaining megálos roadmap is in the range vision-v7 §7 names. Phase G is not the largest single remaining investment — Phase H plausibly matches it in LOC and Phase J would exceed both — but it is the user-visible-product investment: Shapes 1–4 cannot exercise the runtime through a chat UI until Phase G ships, and Phase I cannot begin without Phase G's (C) Capability surface to consume.

Upon Phase G completion, the agorá chat UI is a deployable artifact in both self-host and (parallel) hosted forms. Combined with Phase H's distribution hardening, the runtime + UI is ready to be deployed as production infrastructure by an enterprise platform team or as the foundation for Phase I's managed-hosting offering. That is the threshold Phase G exists to cross.
