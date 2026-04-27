# Phase G — Roadmap Scoping

**Status:** Scoping document with synthesis applied. The four (P) /discusses (D, A+B, C, I) resolved 2026-04-27 → ADRs 006, 007, 010, 011. Synthesis pass crystallized the milestone breakdown in §5 (amended in place; the rough breakdown was replaced with the post-synthesis version). The Phase G roadmap document itself is drafted next, consuming this document plus the four ADRs as input.
**Author:** Diego Marono (with strategic review)
**Date:** 2026-04-27
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](./2026-04-27-megalos-vision-v7.md). v6 was the governing vision when this scoping was originally drafted earlier on 2026-04-27; v7 superseded v6 the same day with a brand-architecture inversion and repo-consolidation reversal that emerged in the predecessor /discuss. The scoping's structural analysis stands unchanged — the four (P)s, three (R)s, and five (S)s carry forward; only the consumer-surface naming (megálos → agorá) and Phase G's prerequisite (predecessor work introduced) shift between v6 and v7. Inline updates below.
**Shape served:** Shapes 1, 2, 3, 4 (Shape 5 deferred per [ADR-003](../adr/003-phase-j-shipping-decision.md)).

---

## 1. Why this document exists

Phase G is committed under v6 §6.5: megálos's chat UI, run mode plus configure-mode-naive picker, FastMCP Client over progressive tool disclosure, self-host-capable from day one, deployed on Phase H's hardened distribution surface in Phase I to become the paid product. v6 §7 names Phase G as "next, re-scoped" but commits no roadmap document.

Phase G has substantial unfamiliar surface. There is no prior chat-UI work in this codebase. Drafting a milestone-structured roadmap directly against v6 §6.5 would over-determine choices on questions whose answers materially shape the milestone breakdown. The right shape of Phase G's milestones depends on strategic decisions about tech stack, distribution shape, connection model, and analytics posture that v6 itself does not pin.

This document is the output of a scoping /discuss run on 2026-04-27 that classified the pre-roadmap questions Phase G surfaces. It identifies which questions must be decided strategically before the roadmap is drafted **(P)**, which the roadmap itself decides as part of its normal scoping work **(R)**, and which belong to per-milestone slice gates **(S)**. The threshold used is **soft (P)**: a question is (P) if its answer materially shapes the milestone breakdown, even if a wrong answer is recoverable. The strict threshold ("wrong answer would force a roadmap rewrite mid-Phase-G") was rejected on the grounds that Phase G's surface is unfamiliar enough that structural-call recovery is more expensive than it is in better-understood domains.

The scoping's purpose is to bound the pre-roadmap work — the subset that must happen before the Phase G roadmap document can be written defensibly — and to leave everything else for the roadmap and its slices.

---

## 2. Phase G in context

The pins Phase G's roadmap inherits from v7, v6, and the ADRs are not subjects of any (P) /discuss in this scoping. They are inputs.

**Phase G presupposes predecessor work** (added 2026-04-27 post-v7). Per v7 §6.5, predecessor work — brand resolution, repo consolidation, catalog website MVP at `agora-workflows.dev` — lands before Phase G's MG1 begins. Phase G's chat UI assumes the catalog website already exists as the user's entry point: a user lands on the catalog, browses collections, clicks "Use in agorá," and is dropped into the chat UI with a collection already selected. MG1's foundation slice does not implement a Workflows-discovery surface within the chat UI itself; that lives in the catalog. Predecessor work is not Phase G; it is its own phase between current state (post-M012, post-Phase-F) and Phase G/Phase H.

- **Configure-mode-naive UI design.** ADR-003 Clause 1. Collection picker is in scope; per-user customized-collection storage and embedded mikrós-reading agent are Phase J only. If Phase J reopens, it adapts to whatever Phase G has built; Phase G does not pre-adapt to Phase J.
- **Analytics instrumentation at launch.** ADR-003 Clause 3. Two specific signals from Phase G ship: Shape-4 IDE-extension users exercising any in-product lightweight-customization affordance; Shape-4 churn at the customization wall vs Shape-2. Forward-looking on Phase G — not added at +5 months. Analytics is product instrumentation, not session data; its retention/privacy posture is independent of ADR-002's session TTL.
- **Account-bound collection-version binding.** ADR-005 commitments 1+2+4. Per-(user, collection) version stored, prompt at session start with [Upgrade]/[Stay] (default Stay), critical-fix carve-out for CVE-class fixes, version-binding log as first-class feature.
- **Session-resumption affordance.** ADR-002 §2 commitment 1. Single-click resume per collection the user has an in-flight session against (v6 prose: "single-click resume per Library entry"). No ChatGPT-style sidebar. Bounded UI surface — one entry-point per collection the user is mid-session on.
- **Same default behavior across paid and self-host.** ADR-004 (C)/(O)/(B) framework. Every Phase G surface design decision categorized: (C) Capability OSS in both tiers; (O) Operational layer paid-only; (B) Billing-bound paid-only by definition.
- **Sequencing.** Phase G ships before Phase H completes and before Phase I. Pre-Phase-I, paid megálos run mode operates at effective Level 0 (no account binding) per ADR-002 §3. Phase G's chat UI exposes a "Resume in this tab" affordance using browser-local `session_id` storage. The UI must signal that account-bound resumption arrives with the managed-tier launch.
- **`workflow_changed` envelope.** ADR-001. Propagates to chat UI as a session-killing terminal state. Recovery is `start_workflow` again.

---

## 3. Twelve candidate pre-roadmap questions

Generated against v6, ADR-001 through ADR-005, the Phase H roadmap, and the Phase J scaffold. Listed by ID for downstream reference; no ordering implied at this point.

| ID | Question | Source |
|----|----------|--------|
| A | Tech stack and framework for the chat UI | Not addressed anywhere — greenfield choice. |
| B | Self-host distribution shape | v6 §3.2 commits self-host parity but doesn't specify shape; Phase H is runtime-side only. |
| C | Connection model: how the UI reaches Library entries | v6 §3.2 names FastMCP Client + progressive tool disclosure but doesn't pin connection model. |
| D | Artifact retention decoupling — buildable at acceptable cost? | ADR-002 §2 commitment 4 names this a Phase G /discuss BLOCKER. |
| E | Session-resumption affordance UX | ADR-002 §2 commitment 1 + §4 bound the shape, punt design. |
| F | Pre-Phase-I transition UX | ADR-002 §3, named explicitly as Phase G design deliverable. |
| G | Self-host auth contract: consumption of MH5's `X-Forwarded-User` | ADR-002 §3 + ADR-004 commitment 5 + Phase H MH5. |
| H | Collection version-prompt + version-display + version-binding log UX | ADR-005 §3, named as Phase G deliverable (v6 prose: "Library entry"). |
| I | Analytics instrumentation surface for ADR-003 Clause 3 | ADR-003 Clause 3 + implementation notes 1 and 2. |
| J | `workflow_changed` envelope UX in the chat | ADR-001 envelope shape; UX surface unaddressed. |
| K | Library catalog discovery UI | v6 §3.1 names the curated catalog; megálos's surface for browsing it not specified. |
| L | BYOK API key management UX | v6 §5 + §6.4. Surface entirely undefined. |

---

## 4. Classifications

| ID | Question | Class | Reasoning |
|----|----------|-------|-----------|
| A | Tech stack / framework | (R) ✓ resolved jointly with B 2026-04-27 → [ADR-007](../adr/007-phase-g-chat-ui-stack.md) | Wrong tech stack is recoverable; milestones look the same under React vs Svelte at the level the roadmap describes them. Decided at MG1 kickoff, paired with B. *Outcome: Svelte 5 + Vite + TypeScript, plain SPA, no SSR.* |
| **B** | Self-host distribution shape | **(P)** ✓ resolved jointly with A 2026-04-27 → [ADR-007](../adr/007-phase-g-chat-ui-stack.md) | Single-binary vs two-artifacts vs static-bundle-served-by-runtime materially changes self-host distribution milestone scope, self-host auth integration (G), and packaging discipline. Paired with A. *Outcome: single static bundle, two delivery paths — self-host bundles into `megalos-server` as package data; hosted serves same bundle from agorá's CDN with operator's commercial wrapper backend.* |
| **C** | Connection model | **(P)** ✓ resolved 2026-04-27 → [ADR-010](../adr/010-phase-g-connection-model.md) | Most load-bearing of the twelve. Operator-hosted catalog vs user-managed connection registry vs hybrid produces very different milestone scope for "Library picker," different paid-vs-self-host story (ADR-004), different binding to ADR-003 Clause 1's configure-mode-naive picker. K folds into whatever C settles. *Outcome: Pattern B (single backend per session) with MCP-over-HTTP refinement; thin TS MCP client in the chat UI; cross-cutting concerns in the backend layer; per-folder MCP endpoints retained for AI-agent consumption; "switch entry" affordance backed by ADR-005 account-bound entry list (K folds in here).* |
| **D** | Artifact retention decoupling | **(P)** ✓ resolved 2026-04-27 → [ADR-006](../adr/006-artifact-retention-decoupling.md) | Pre-pinned by ADR-002 §2 commitment 4 as a Phase G /discuss BLOCKER. Investigation, not strategic position-finding. *Outcome: decoupling buildable at ~1 milestone-equivalent via `ArtifactStore` parallel to `SessionStore`, user-captured-explicit model. ADR-002 holds.* |
| E | Session-resumption affordance UX | (S) | ADR-002 commits the surface bound; rest is design detail. Depends on C (where the affordance lives). |
| F | Pre-Phase-I transition UX | (S) | Small surface — copy + browser-local `session_id` "Resume in this tab" affordance. Fits in resumption slice. |
| G | Self-host auth contract | (S) | Consumption of MH5's already-defined header contract. Slice-gate work; depends on B. |
| H | Version-prompt + display + log UX | (R) | ADR-005 commits the three surfaces; design space is bounded. Roadmap decides whether own milestone or distributed. Design itself is per-slice. |
| **I** | Analytics instrumentation surface | **(P)** ✓ resolved 2026-04-27 → [ADR-011](../adr/011-phase-g-analytics-instrumentation.md) | "What gets instrumented" is design, but the privacy posture for analytics is genuinely strategic and ADR-003 Clause 3 implementation note 2 explicitly distinguishes it from session-data retention. Depends on C. *Outcome: 13-month retention ceiling (delete-at framing); self-host opt-in only; behavioral-proxy segmentation with sticky tagging; custom emit-to-Postgres at v1 with PostHog migration triggers; 7-event schema; HMAC-SHA-256 with per-deployment salt for account_id_hash; analytics-session-id namespace-distinct from ADR-002.* |
| J | `workflow_changed` envelope UX | (S) | ADR-001 ships the envelope; UI surfaces the terminal-state error. Standard error-handling slice work. |
| K | Library catalog discovery UI | (R) | At v1 Library scale (5–10 entries per v6 §6.1), discovery is a static list with descriptions. Folds into C's milestone. |
| L | BYOK API key management UX | (S) | Pre-Phase-I client-side storage, provider validation, settings page. Narrow, well-precedented. Post-Phase-I behavior is Phase I scoping. |

**Total: 4 (P), 3 (R), 5 (S).**

---

## 5. Milestone breakdown (crystallized after the four (P)s landed)

The four (P) /discusses have resolved (D → ADR-006; A+B → ADR-007; C → ADR-010; I → ADR-011). The rough five-milestone shape from the scoping pass holds; the four ADRs add specifics, shift one surface (artifact gallery) into MG4, and pin where analytics threads through. Synthesized shape below.

The synthesis input is "the four ADRs plus the Phase G scoping doc's rough five-milestone shape" per the operator's pre-synthesis discipline note. Synthesis is not re-deriving MG1–MG5 from scratch; it is crystallizing the rough shape against the four (P) decisions.

### MG1 — Foundation

Largest milestone — establishes the entire technical substrate. Highest-risk: closes the longest period before user-visible value lands and gates every downstream milestone.

- **Tech-stack scaffold** per ADR-007: Svelte 5 + Vite + TypeScript SPA, static-build target, agorá-branded UI from inception per ADR-008.
- **Thin TypeScript MCP-over-HTTP client** per ADR-010 commitment 2: hand-written, ~300–500 LOC, no framework dependency. **Spike-verified at MG1 kickoff** — if the spike overruns the budget, ADR-010 T1 fires and FastMCP-JS evaluation begins. The spike is the gating slice; everything downstream depends on it.
- **`megalos-server` static-bundle integration** per ADR-007 commitment 2: UI ships as Python package data; `megalos-server` serves the static assets from its existing HTTP layer.
- **Hosted-backend stub**: minimal MCP-over-HTTP transport on the outer edge for development and verification of the contract-singularity claim. The full proxy implementation against per-entry endpoints is operator commercial code (O), parallel to Phase I.
- **BYOK API key entry surface** (L). Pre-Phase-I client-side storage; provider validation; settings page.
- **Basic connection to one collection**: entry-id parameter via URL; the chat UI accepts an entry parameter from the catalog website's "Use in agorá" landing flow. The catalog website itself is predecessor work, not Phase G.
- **Analytics emission scaffolding** per ADR-011: chat UI client + backend handler + `analytics_events` table schema. Per-event emitters are added in subsequent milestones as their corresponding features land.
- **"Customize this entry" affordance** per ADR-011 commitment 3: ~30 LOC; click event captured.

*Slices: ~5–7. Largest milestone by LOC and risk.*

### MG2 — Run-mode chat loop

The user-visible execution surface. By end of MG2 a user can run a collection from start to artifact via the chat UI.

- **Directive/gate/anti-pattern run loop** in the chat UI: orchestrates the sequence of `get_state` → `get_guidelines` → LLM call browser-direct → `submit_step` per ADR-010's MCP-over-HTTP client.
- **Progressive tool disclosure** per v7 §2 + v6 §2 carryover. Tool definitions loaded incrementally rather than upfront.
- **Step-state rendering**: the chat UI surfaces what step is active, what gates apply, what anti-patterns were flagged.
- **`workflow_changed` envelope UX** (J) per ADR-001: terminal-state rendering with clear recovery path ("start a new session").
- **`generate_artifact` integration** + **write to `ArtifactStore`** per ADR-006: the artifact-capture trigger persists the result to the user-bound `ArtifactStore`. Phase G's chat UI emits the capture; backend writes the row.
- **Per-event emitters land**: `session_started`, `session_progressed`, `session_completed` per ADR-011 commitment 6.

*Slices: ~4–5.*

### MG3 — Catalog and picker (configure-mode-naive)

Lightest milestone. The "switch entry" affordance and the configure-mode-naive picker per ADR-003 Clause 1.

- **"Switch entry" affordance** per ADR-010 commitment 8: surfaces the user's account-bound entry list (resolved by the backend per ADR-005); does not duplicate the catalog website's discovery surface.
- **Configure-mode-naive picker** per ADR-003 Clause 1. The picker is in scope; per-user customized-entry storage and embedded mikrós-reading agent are Phase J only (deferred per ADR-003).
- **Multi-entry browser tabs** per ADR-010 commitment 7: each tab is one MCP-over-HTTP session; no in-product tab manager. Backend tracks per-(user, entry) per ADR-002.
- **K folds in here**: the catalog website (predecessor work, at `agora-workflows.dev`) is the discovery surface; the chat UI's "switch entry" is the in-product affordance only. K is closed.
- **Per-event emitters land**: `entry_switched` per ADR-011.

*Slices: ~3–4.*

### MG4 — Persistence and continuity UX

Bundles ADR-005 (H) + ADR-002 (E, F) + ADR-006 (artifact gallery). All three are surfaces the user sees about state continuity across sessions, versions, and artifacts; the design coherence wins from bundling.

- **Version-prompt + display + binding-log UX** per ADR-005 §2 commitments 1+2+4 (H): account-bound version binding; non-blocking session-start prompt with `[Upgrade] / [Stay on V_user]` (default Stay); critical-fix carve-out auto-migrates; version-binding log as first-class feature.
- **Single-click resume affordance** per ADR-002 §2 commitment 1 (E): one entry-point per collection the user has an in-flight session against. No ChatGPT-shaped sidebar.
- **Pre-Phase-I "Resume in this tab" affordance + transition UX** per ADR-002 §3 (F): browser-local `session_id` resumption during the Phase G → Phase I window; clear in-product affordance signaling that account-bound resumption arrives with the managed-tier launch.
- **Artifact gallery / saved-outputs surface** per ADR-006: the user-captured-explicit retrieval surface; UX distinguishes "your conversation expired" from "your saved artifacts are still here."
- **Per-event emitters land**: `version_prompt_responded` per ADR-011 commitment 6 — the only direct signal on whether users actually read or auto-dismiss the version-binding prompt.

*Slices: ~4–5. **Possible split point**: if MG4 runs heavy at design time, split into MG4a (version + resumption) and MG4b (artifact gallery). Decision at MG3 close; not pre-committed.*

### MG5 — Self-host distribution and auth integration

By end of MG5, self-host single-binary works end-to-end per ADR-007 commitment 2.

- **Package-data bundling**: UI ships as Python package data inside `megalos-server`; `pip install megalos-server` ships runtime + UI together.
- **`X-Forwarded-User` consumption** (G) per Phase H MH5 + ADR-002 §3: chat UI consumes the header populated by upstream proxy auth; behavior on absence is documented (default to anonymous-equivalent or `deny-anonymous` per MH5 envvar).
- **Phase H MH1 deployment-recipes coupling**: the static-bundle integration plays cleanly with MH1's Docker / Compose / K8s / Helm recipes. `pip install megalos-server`, run, browse to `localhost`, see agorá UI.
- **Self-host analytics opt-in envvar surface** per ADR-011 commitment 2: `MEGALOS_ANALYTICS_ENABLED=false` default; emission target configurable; admin documentation explains the opt-in path.
- **`MEGALOS_ANALYTICS_RETENTION_DAYS`** envvar surfaced with admin documentation.

*Slices: ~3–4.*

### Cross-cutting: analytics instrumentation across MG1–MG5

Per ADR-011 + ADR-003 Clause 3 implementation note 1: instrumentation is launch-time, not retroactive. Each milestone's slices carry their own emitters per ADR-011 commitment 6. Not a separate milestone — analytics is a discipline applied across all five, mirroring Phase H MH6's "lands continuously alongside MH2–MH5" pattern.

| Event | Lands in |
|-------|----------|
| `session_started`, `session_progressed`, `session_completed` | MG2 |
| `customize_intent_clicked` | MG1 (affordance ships at MG1) |
| `file_download_used` | MG1 (chat UI lands user from "Use in agorá" flow) |
| `entry_switched` | MG3 |
| `version_prompt_responded` | MG4 |

The analytics scaffolding (chat UI client + backend handler + Postgres table) lands at MG1; per-event emitters land alongside their feature milestones.

### Cross-cutting: hosted commercial backend (parallel to Phase I)

The (O) operator commercial code that proxies MCP-over-HTTP to per-entry endpoints, layers ADR-002 / ADR-003 / ADR-005 / ADR-006 cross-cutting concerns, hosts the `analytics_events` Postgres table, and runs the 13-month retention enforcement job is **parallel work, not part of Phase G OSS scope** per ADR-007 commitment 7 + ADR-010 commitment 4. Phase G ships the OSS pieces; Phase I scaffolding consumes them.

### Summary

| Milestone | Slices | Risk | What lands |
|-----------|--------|------|-----------|
| MG1 | ~5–7 | High | Foundation; thin TS MCP client (spike-gated); static-bundle integration; backend stub; analytics scaffolding; "customize" affordance |
| MG2 | ~4–5 | Medium | Run-mode chat loop; `generate_artifact` + `ArtifactStore`; first event emitters |
| MG3 | ~3–4 | Low | Switch-entry affordance; configure-mode-naive picker (K folds in) |
| MG4 | ~4–5 (possibly split) | Medium | Version + resumption + artifact-gallery UX |
| MG5 | ~3–4 | Low–medium | Self-host distribution + auth; analytics envvars |

**Total: ~20 slices across 5 milestones**, 21–22 if MG4 splits. Sole-author estimated at 4–6 months sequenced after predecessor work lands per v7 §6.5. The Phase G roadmap document drafted from this synthesis pins MG1–MG5 into per-slice work plans.

---

## 6. (P)-discuss sequencing

```
        ┌─────────────────────┐
        │ D (investigation)   │  ✓ resolved 2026-04-27 → ADR-006
        │ artifact decoupling │
        └──────────┬──────────┘
                   │ (succeeded; ADR-002 holds)
                   ▼
        ┌─────────────────────┐
        │ A+B joint /discuss  │  ✓ resolved 2026-04-27 → ADR-007
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ C /discuss          │  ✓ resolved 2026-04-27 → ADR-010
        │ connection model    │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ I /discuss          │  ✓ resolved 2026-04-27 → ADR-011
        │ analytics posture   │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Synthesis pass      │  ✓ resolved 2026-04-27 → §5 amended in place
        │ (four ADRs +        │
        │  rough 5-MG shape)  │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Phase G roadmap     │  ◄── next
        │ drafting            │
        └─────────────────────┘
```

**Why this order.**

- **D first.** It is the only one that can invalidate ADR-002 retroactively. Running A+B/C/I before D wastes effort if D surfaces decoupling is unbuildable — ADR-002 reopens, the run-mode persistence story changes, and several downstream questions reset.
- **A+B second.** Tech-stack + distribution choice constrains every subsequent design surface. Self-host distribution especially: if B settles as static-bundle-served-by-runtime, G (auth header consumption) becomes trivial; if B settles as separate Node service, G is a real slice.
- **C third.** Most load-bearing strategic question, but it depends on A+B answering "what kind of UI are we building" first. C is where the milestone breakdown actually crystallizes.
- **I fourth.** Depends on C because the analytics-affordance question ("what is there to instrument exercise of") requires knowing what the configure-mode-naive picker looks like. The privacy-posture question is independent but bundling them keeps the analytics surface coherent.

Each (P) /discuss output is recorded as an ADR or a v6 §9 amendment per the precedent set by ADR-002/003/004/005.

---

## 7. Pre-roadmap effort estimate

**~5 /discuss-equivalents.**

| (P) | Effort | Notes |
|-----|--------|-------|
| D | ~1 | Investigation, smaller than a full /discuss but real cost (code reading, schema analysis, cost modeling). |
| A+B joint | ~1.5 | Joint conversation; tech-stack research adds time; distribution-shape options need spelling out. |
| C | ~1.5 | Most load-bearing; deserves the most thought; multiple defensible positions to weigh. |
| I | ~1 | Smaller; privacy posture is the load-bearing piece; instrumentation surface is design. |

**Calendar: roughly 2 weeks at one /discuss every 2–3 days,** which matches the rhythm of the recent ADR-002/003/004/005 pass. After all four (P)s land, the Phase G roadmap drafting session has firm inputs and the milestone breakdown above can be sharpened into proper MG1–MG5 documents.

---

## 8. Out of scope for this scoping

- **The (P) /discusses themselves.** This scoping classifies which questions need (P) treatment; it does not answer them.
- **The Phase G roadmap document.** Drafted in a separate session after all four (P)s resolve.
- **Per-milestone slice gates.** The (S) classifications point at the milestone that owns each question; the slice gates run when their milestones begin.
- **Phase I scoping.** Pricing model (v6 §9 Q3), account-bound API key storage, billing UI, multi-tenant isolation. Phase I scaffold is owed after Phase H MH2–MH4 land per v6 §7.
- **Phase J reopening.** Phase J is deferred per ADR-003. T1 reopening depends on Phase G post-ship analytics signal — but the reopening itself is downstream of Phase G shipping, not part of this scoping.
- **Tech-stack-specific implementation details.** What state-management library, what styling approach, what test framework. (R) and (S) work, not (P).

---

## 9. References

- **vision-v7** ([`2026-04-27-megalos-vision-v7.md`](./2026-04-27-megalos-vision-v7.md)) — current canonical vision; supersedes v6 with brand inversion (agorá as consumer brand) + repo consolidation. The chat UI is now agorá-branded; the consumer surface lives at `agora-workflows.dev`.
- vision-v6 ([`2026-04-26-megalos-vision-v6.md`](./2026-04-26-megalos-vision-v6.md)) — historical reference; the original governing vision when this scoping was drafted. v6 §3.2, §6.5, §7, §9 carry forward into v7 with surface-naming updates.
- ADR-001 ([`docs/adr/001-workflow-versioning.md`](../adr/001-workflow-versioning.md)) — `workflow_changed` envelope inherited by the agorá chat UI.
- ADR-002 ([`docs/adr/002-run-mode-session-persistence.md`](../adr/002-run-mode-session-persistence.md)) — Phase G /discuss BLOCKER (commitment 4, resolved by ADR-006); session-resumption affordance; pre-Phase-I transition UX; self-host auth contract source.
- ADR-003 ([`docs/adr/003-phase-j-shipping-decision.md`](../adr/003-phase-j-shipping-decision.md)) — configure-mode-naive design (Clause 1) + analytics instrumentation at launch (Clause 3).
- ADR-004 ([`docs/adr/004-paid-vs-self-host-value-asymmetry.md`](../adr/004-paid-vs-self-host-value-asymmetry.md)) — (C)/(O)/(B) framework applied to every Phase G design decision.
- ADR-005 ([`docs/adr/005-library-entry-versioning-ux.md`](../adr/005-library-entry-versioning-ux.md)) — version-prompt + display + binding log UX as Phase G deliverable.
- ADR-006 ([`docs/adr/006-artifact-retention-decoupling.md`](../adr/006-artifact-retention-decoupling.md)) — D's resolution; `ArtifactStore` parallel to `SessionStore`, user-captured-explicit model.
- ADR-007 ([`docs/adr/007-phase-g-chat-ui-stack.md`](../adr/007-phase-g-chat-ui-stack.md)) — A+B's resolution; Svelte 5 + Vite + TS, single static bundle, two delivery paths.
- ADR-008 ([`docs/adr/008-brand-architecture.md`](../adr/008-brand-architecture.md)) — agorá as consumer-facing brand; megálos demoted to runtime technical name; three-layer architecture (consumer/content/technical).
- ADR-009 ([`docs/adr/009-repo-consolidation.md`](../adr/009-repo-consolidation.md)) — `agora-creations/agora-library` aggregator with sibling folders; per-folder MCP endpoints + per-folder versioning preserved.
- ADR-010 ([`docs/adr/010-phase-g-connection-model.md`](../adr/010-phase-g-connection-model.md)) — C's resolution; Pattern B (single backend per session) with MCP-over-HTTP refinement; thin TS MCP client; backend-mediated cross-cutting concerns.
- ADR-011 ([`docs/adr/011-phase-g-analytics-instrumentation.md`](../adr/011-phase-g-analytics-instrumentation.md)) — I's resolution; 13-month retention ceiling (delete-at framing); self-host opt-in; sticky-tagging segmentation; custom emit-to-Postgres at v1; 7-event schema with HMAC-SHA-256 hash.
- Phase H roadmap ([`2026-04-22-phase-h-distribution-hardening-roadmap.md`](./2026-04-22-phase-h-distribution-hardening-roadmap.md)) — structural template for roadmap shape; MH1 deployment recipes; MH5 header middleware.
- Phase J scaffold ([`2026-04-22-phase-j-scaffold.md`](./2026-04-22-phase-j-scaffold.md)) — superseded for the shipping decision by ADR-003; "five irreducible components" §2 framing as a model for enumerating Phase G's irreducible components.

---

*End of Phase G roadmap scoping. The four (P) /discusses run in the order in §6 — D first as gate, then A+B, then C, then I. The Phase G roadmap document is drafted after all four resolve.*
