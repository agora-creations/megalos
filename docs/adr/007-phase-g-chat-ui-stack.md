# ADR-007 — Phase G chat UI tech stack and distribution shape

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](../vision/2026-04-27-megalos-vision-v7.md)
**Resolves:** Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) (P) /discuss A+B — joint resolution of tech stack (A) and self-host distribution shape (B) for the agorá chat UI
**Related:** ADR-002 (run-mode session persistence, `002-run-mode-session-persistence.md`); ADR-004 (paid-vs-self-host value asymmetry, `004-paid-vs-self-host-value-asymmetry.md` — (C)/(O)/(B) framework applied here); ADR-005 (Library entry versioning UX, `005-library-entry-versioning-ux.md`); ADR-006 (artifact retention decoupling, `006-artifact-retention-decoupling.md`); ADR-008 (brand architecture, `008-brand-architecture.md` — agorá as consumer-facing brand); ADR-009 (repo consolidation, `009-repo-consolidation.md`).

---

## 1. Context

Vision-v7 §3.1 commits the consumer surface as agorá: a catalog website at `agora-library.dev` (predecessor-work deliverable) plus a chat UI (Phase G deliverable). The chat UI is where users select a Library entry, configure it lightly, plug in their LLM API key, and run workflows interactively. v7 §3.5 places this surface in the consumer layer of the three-layer architecture — agorá (consumer) over the Library (content) over megálos+mikrós (technical).

Phase G has substantial unfamiliar surface — no prior chat-UI work in this codebase. The Phase G roadmap scoping document (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) classified two questions as (P) pre-roadmap /discusses requiring resolution before the Phase G roadmap can be drafted defensibly: A — tech stack and framework choice, B — self-host distribution shape. The two were classified as joint because they constrain each other: framework choices with hard runtime requirements (Next.js, SvelteKit-with-Node-server, Remix) force the distribution shape toward two-process self-host; framework-light or compile-away choices keep distribution options open including "static bundle served by `megalos-server`."

The /discuss session of 2026-04-27 walked the joint surface against seven criteria (self-host friction; (C) categorization purity per ADR-004; sole-author velocity; long-term framework stability; chat-UI ecosystem maturity; bundle size; build complexity), enumerated six candidate combinations, pruned five, and reached a recommendation. The operator review introduced a structural reinforcement — a sister frontend (the catalog website) ships during predecessor work, before Phase G, with different needs (SEO matters; mostly-static; SvelteKit + adapter-static fits). Two frontends, one architect, one framework family.

This ADR encodes the joint resolution with stable naming throughout — vision-v7 is canonical, ADR-008 commits agorá as the consumer brand, ADR-009 commits the aggregator repo, and the bare-name domain commitment in v7 §6.4 lets external-surface references in this ADR pin to `agora-library.dev` without TBDs.

## 2. Decision

Seven commitments. They hold together; weakening any one weakens the others.

**1. Svelte 5 + Vite + TypeScript for the chat UI.** Plain Svelte 5 SPA. No SvelteKit. No SSR. Vite as the bundler (Svelte's recommended). TypeScript across all UI source — no JavaScript-only files. Build output target is static — the bundle is a directory of static assets (`index.html` + JS/CSS/font files) suitable for serving from any HTTP origin.

**2. Single static bundle, two delivery paths.** The build produces one artifact. Two delivery paths consume it identically:

- **Self-host path.** The static bundle is bundled into `megalos-server` as Python package data. `pip install megalos-server` ships the runtime + the UI together. The runtime serves the static assets from its existing HTTP layer (FastMCP transport already exists; an additional static-asset route is trivial). The browser hits `megalos-server` at the configured port for both UI assets and API endpoints. **Single binary self-host.** No second process, no Node runtime, no separate UI service.
- **Hosted path.** The same bundle is served from agorá's CDN (operator-owned infrastructure). The operator's commercial wrapper backend handles auth, BYOK storage, billing, and routing to per-Library-entry MCP endpoints (`writing.agora-library.dev`, etc.). The wrapper backend is the operator's closed-source commercial code per ADR-004 commitment 3 — (O) Operational layer; the static bundle itself is (C) Capability and identical to the self-host bundle.

**One artifact, two delivery paths.** No fork between self-host and hosted UI sources. The (C)/(O) split runs through the *delivery infrastructure*, not through the bundle.

**3. TypeScript across all UI source.** Type-system safety net for sole-author maintainability. Two frontends instead of one (chat UI under Phase G; catalog website under predecessor work) reinforces the case — the type system catches contract drift between surfaces sharing types (Library-entry shape, version metadata, auth tokens, etc.).

**4. agorá-branded UI; no megálos-branded fallback** per ADR-008 commitment 1. The chat UI ships agorá branding from MG1's foundation slice. Self-host bundle and hosted bundle show identical agorá branding. There is no transitional megálos-branded build; there is no admin-toggleable megálos fallback. White-label support is a future possibility per ADR-008's T1 trigger condition, not a Phase G commitment.

**5. The catalog website is NOT in Phase G scope.** The catalog ships during predecessor work, before Phase G's MG1 begins. Phase G's chat UI assumes the catalog at `agora-library.dev` already exists as the user's entry point — the user lands on the catalog, browses Library entries, clicks "Use in agorá" on a chosen entry, and is dropped into the chat UI. The chat UI starts in a state that already has an entry selected (entry ID passed via URL parameter or session state); MG1 does not implement a discovery surface within the chat UI itself.

**6. Framework family unified across both consumer frontends.** The chat UI uses plain Svelte 5 SPA (commitment 1); the catalog website uses SvelteKit + adapter-static (predecessor-work scope, this ADR doesn't commit catalog stack but names it for context). One mental model across both surfaces. SvelteKit's adapter-static produces static-bundle output (no Node runtime needed) — same constitutional purity as commitment 1, with SvelteKit's routing/SSG features available where the catalog needs them. React was rejected partly because it would have pulled the catalog toward Next.js, applying the same Node-runtime objection at a second surface.

**7. (C)/(O)/(B) categorization per ADR-004.** UI source is **(C) Capability** — OSS, identical in both tiers, lives at whatever repo predecessor-work `/plan` time names (likely `agora-ui` or co-located in `megalos-server`; deferred). Static-bundle distribution mechanism is (C). The hosted-tier commercial wrapper backend (auth, BYOK storage, billing, MCP-endpoint routing) is **(O) Operational layer** — paid-only, closed-source. Per-tenant analytics, audit logging, and managed CDN configuration are (O). Billing UI surfaces and BYOK-key-account-binding are **(B) Bound by billing** under Phase I.

## 3. Implementation sequencing

The five-milestone breakdown from the Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md` §5) is the working model; Phase G's roadmap drafting session refines.

**MG1 — Foundation** scaffolds the Svelte 5 + Vite + TypeScript project; sets up the static-build target; implements FastMCP Client integration for talking to a Library entry's MCP endpoint; adds BYOK key entry surface (per ADR-006 §3.4 in spirit — narrow, well-precedented). Outputs a working "open the chat UI, paste an API key, connect to one entry, run a workflow end-to-end" shell.

**MG2 — Run-mode chat loop** implements the directive/gate/anti-pattern run loop in the UI; surfaces progressive tool disclosure; renders step-state; handles `workflow_changed` envelope per ADR-001.

**MG3 — Catalog and picker** implements the configure-mode-naive Library-entry picker per ADR-003 Clause 1. The picker affordance lives inside the chat UI for users who want to switch entries within an authenticated session; the discovery surface is the catalog website (commitment 5) and is not duplicated here.

**MG4 — Version-awareness and session-resumption UX** implements ADR-005's prompt + display + binding-log UX and ADR-002's single-click resume affordance.

**MG5 — Self-host distribution and auth integration** implements the package-data bundling that ships the static bundle inside `megalos-server`; consumes Phase H MH5's `X-Forwarded-User` header per ADR-002 §3 + ADR-004 commitment 5.

**Hosted-side commercial wrapper backend** is operator's commercial code, sequenced parallel to Phase I (managed agorá platform). It is (O) per commitment 7 and not part of Phase G's OSS scope.

**Chat UI repo location is pinned at predecessor-work `/plan` time, not at Phase G `/plan` time.** Per the operator's framing in the A+B /discuss review, the repo's existence and naming are part of the rescoping (predecessor work), not part of Phase G's tech-stack commitments. This ADR commits the *technical pattern* (single static bundle, package-data bundling for self-host, CDN-served bundle for hosted); it does not commit *where the source lives*. Candidate names (`agora-ui`, co-located in `megalos-server`, etc.) get evaluated against predecessor-work's repo-consolidation discipline (per ADR-009) plus Phase G's Phase H MH1 deployment-recipes coupling.

## 4. Consequences

**What this commits agorá to.**

- A Svelte 5 + Vite + TypeScript SPA for the chat UI, with static-build output. No SvelteKit, no SSR, no Node runtime in production.
- A single static bundle artifact consumed by both self-host and hosted delivery paths. No fork between the two.
- Self-host single-binary distribution: `pip install megalos-server` ships the UI bundle as Python package data; `megalos-server` serves the bundle from its existing HTTP layer.
- Hosted distribution: same bundle, served from agorá's CDN, wrapped by operator's commercial backend (auth, BYOK storage, billing, MCP-endpoint routing).
- agorá branding throughout the UI from MG1; no megálos-branded fallback.
- Phase H MH5's `X-Forwarded-User` header consumed by the chat UI for self-host identity propagation per ADR-002 §3.
- (C) categorization for UI source and bundle distribution mechanism; (O) categorization for hosted-tier commercial wrapper backend.
- The chat UI repo location is a predecessor-work `/plan` deliverable, not a Phase G commitment.

**What this forecloses.**

- React, Vue, Solid, vanilla TS, Next.js, HTMX as Phase G chat UI frameworks. Each was considered and rejected in the A+B /discuss with reasoning recorded there.
- SSR or server components for the chat UI. No use case at v7 ship; if a real need emerges, this ADR reopens.
- Two-process self-host where the UI is a separate Node service. Single-binary self-host is constitutional per the three-dependency rule (`fastmcp`, `pyyaml`, `jsonschema`) — adding a Node runtime to the self-host story violates the spirit of the constraint even if technically permissible via extras packages.
- A megálos-branded UI variant for self-host. Per ADR-008 commitment 1 the brand-inversion does not admit a self-host fallback brand.
- Different framework families across the two consumer frontends. Catalog website + chat UI both ride Svelte; framework-family fragmentation across consumer surfaces is rejected.
- A "paid features are better UI" tier per ADR-004 commitment 1's no-capability-withholding principle. The bundle is identical in both tiers; differentiation is in the operational wrapper.
- Renaming or rebranding the megálos package in response to Phase G work. The package stays `megalos-server` (technical layer); ADR-008 commitment 2 explicitly preserves this.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**Svelte 5 introduces a major API break in the next ~2 years.** The runes API is new (stabilized late 2024). A hostile migration story in Svelte 6 or 7 — comparable in disruption to Vue 2→3's refactor cost — would invalidate the long-term-stability claim that tipped the framework choice toward Svelte over React. Mitigation: monitor Svelte's RFC process; the project hasn't done major breaking migrations on Svelte 4→5's scope before, but the risk is non-zero. If a hostile migration surfaces, this ADR reopens; the right response is likely a measured port (not a panic-rewrite to React) because the alternatives haven't gotten more stable in the interim.

**A second engineer joins React-fluent without Svelte experience.** Sole-author velocity argument tipped the choice toward Svelte. If the project moves to multi-author and React fluency dominates the contributor pool, the velocity calculus inverts. This is not a present concern — the project is sole-author at v7 ship — but it is foreseeable at scale. Mitigation lives in two places: (a) Svelte's documentation and component model are easier to onboard a React-fluent contributor onto than the reverse; (b) a multi-author future at Phase I or beyond would warrant reopening this ADR alongside other multi-author concerns (code-review processes, shared-state management, etc.).

**Chat UI patterns turn out to need SSR, server components, or streaming HTML.** No signal points there at v7 ship — chat is post-login, dynamic, no SEO surface, and the FastMCP transport handles streaming responses natively. If a future use case (e.g., a chat-history-replay surface that benefits from server-side rendering, or a deep-link sharing flow that needs SEO) emerges and the static-bundle architecture can't accommodate it cleanly, this ADR reopens toward SvelteKit or another SSR-capable framework. The hybrid-feature pattern from ADR-004 commitment 4 is the first-line response: implement the SSR-needing feature as a separate (O) operational layer rather than rewriting the (C) capability.

## 6. Trigger conditions for revisit

- **T1 — Svelte 5 → 6 hostile migration.** Reopen commitment 1; evaluate measured port vs. framework switch. Likely a measured port unless the alternatives (React in particular) have meaningfully improved on stability in the interim.
- **T2 — Multi-author future with React-dominant fluency.** Reopen commitment 1's velocity argument. May warrant migration if contributor-onboarding cost outweighs framework-rewrite cost; otherwise hold.
- **T3 — Real use case for SSR / server components.** Reopen commitment 1 toward SvelteKit (or alternative). Hybrid-feature pattern first-line response: separate the SSR-needing feature as (O) layer.
- **T4 — Bundle size limit hit.** Static bundle grows to >2MB minified-gzipped and self-host UX degrades. Reopen the static-bundle commitment; consider lazy-loading patterns within Svelte before structural reversal.
- **T5 — A second chat-UI surface emerges that doesn't fit the pattern.** Hypothetical: a mobile-native client, a desktop Electron build, a CLI-embedded UI. Each is a separate decision; this ADR's commitments cover the web chat UI specifically.
- **T6 — ADR-008 reopens.** Brand architecture changes invalidate commitment 4's agorá-branding pin. Cross-coupled.
- **T7 — Phase H MH5's `X-Forwarded-User` contract changes.** Self-host auth consumption pattern (commitment 7's MH5 dependency) may need revisit.
- **T8 — Chat UI repo geography decision** (predecessor-work `/plan` time). Outcome doesn't reopen this ADR but does inform commitment 7's (C) categorization specifics — whether the UI source repo is part of `megalos-server`'s OSS distribution or a separate (C) repo.

## 7. References

- vision-v7 §3.1 (consumer surface — agorá's catalog and chat UI definitions).
- vision-v7 §3.5 (three-layer architecture; chat UI is consumer-layer).
- vision-v7 §6.4 (external surface; `agora-library.dev` v1 base domain).
- vision-v7 §6.5 (predecessor work; the catalog website is a predecessor-work deliverable; Phase G assumes its existence).
- vision-v7 §7 (relationship to roadmap; Phase G after predecessor work).
- Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) — the (P) classification of A+B that this ADR resolves; the five-milestone working model that §3 implementation sequencing references.
- ADR-001 (`001-workflow-versioning.md`) — `workflow_changed` envelope handling in MG2.
- ADR-002 (`002-run-mode-session-persistence.md`) — single-click resume affordance (MG4); `X-Forwarded-User` header consumption (MG5).
- ADR-003 (`003-phase-j-shipping-decision.md`) — configure-mode-naive picker (MG3); analytics instrumentation (continuous across MG1–MG5 per scoping doc §5).
- ADR-004 (`004-paid-vs-self-host-value-asymmetry.md`) — (C)/(O)/(B) framework applied to commitment 7's categorization; commitment 5's architectural-vs-code self-host equivalence pattern.
- ADR-005 (`005-library-entry-versioning-ux.md`) — version-prompt + display + binding-log UX (MG4).
- ADR-006 (`006-artifact-retention-decoupling.md`) — artifact-gallery / saved-outputs surface in the chat UI; the user-captured-explicit model.
- ADR-008 (`008-brand-architecture.md`) — agorá branding (commitment 4); no megálos-branded fallback.
- ADR-009 (`009-repo-consolidation.md`) — sibling reversal; `agora-library` aggregator structure that the catalog and chat UI both consume.
- Phase H roadmap (`../vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`) — MH1 deployment recipes (the static-bundle distribution coupling); MH5 header middleware (the auth-header consumption point in MG5).

---

*End of ADR-007. This ADR's commitments hold conditional on Svelte 5's API stability over the next ~2 years and on the project's sole-author state for the duration of Phase G implementation. If either changes meaningfully — Svelte hostile migration or multi-author future with React-dominant fluency — this ADR reopens.*
