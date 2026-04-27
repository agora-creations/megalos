# ADR-010 — Phase G connection model (chat UI ↔ runtime)

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](../vision/2026-04-27-megalos-vision-v7.md)
**Resolves:** Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) (P) /discuss C — connection model for the agorá chat UI, plus K (Library catalog discovery UI) which folds into C
**Related:** ADR-002 (run-mode session persistence, `002-run-mode-session-persistence.md` — backend mediates the resumption affordance); ADR-003 (Phase J shipping decision, `003-phase-j-shipping-decision.md` — backend instruments analytics from launch); ADR-004 (paid-vs-self-host value asymmetry, `004-paid-vs-self-host-value-asymmetry.md` — (C)/(O) split applied here); ADR-005 (Library entry versioning UX, `005-library-entry-versioning-ux.md` — backend resolves per-(user, entry) version-binding); ADR-006 (artifact retention decoupling, `006-artifact-retention-decoupling.md` — backend writes to `ArtifactStore`); ADR-007 (Phase G chat UI stack, `007-phase-g-chat-ui-stack.md` — single static bundle commits this ADR's "single chat UI codebase" requirement); ADR-008 (brand architecture, `008-brand-architecture.md` — agorá branding); ADR-009 (repo consolidation, `009-repo-consolidation.md` — per-folder MCP endpoints).

---

## 1. Context

Vision-v7 §3.1 commits the agorá chat UI as a Svelte 5 SPA per ADR-007, served from `megalos-server` for self-host or from agorá's CDN for hosted. v7 §6.3 commits two consumption paths: MCP-connect (AI agents to per-entry endpoints) and file-download (entries dropped into local workflows directory). v7 §6.4 commits per-folder MCP endpoints under `<folder>.agora-library.dev`.

What v7 does *not* commit is how the chat UI itself talks to the runtime to drive workflow execution — `get_state`, `get_guidelines`, `submit_step`, `generate_artifact`, sibling tools. The Phase G roadmap scoping document classified this as (P) /discuss C: load-bearing on milestone breakdown because the connection-model choice determines where cross-cutting concerns live (ADR-002 session resumption, ADR-003 analytics, ADR-005 version-binding, ADR-006 artifact storage), how the (C)/(O) split runs through the surface, and what the chat UI's own architecture looks like.

A focused /discuss session of 2026-04-27 walked three candidate patterns (browser-direct MCP to per-entry endpoints; backend-mediated single contract; hybrid split) against six criteria (single chat UI codebase per ADR-007; cross-cutting concerns in one place; (C)/(O) split per ADR-004; constitutional purity; self-host friction; operator role in hosted). Pattern A (browser-direct) was rejected on cross-cutting-concerns grounds and ADR-004 contradiction; Pattern C (hybrid) was rejected on ADR-007 single-bundle violation. Pattern B (backend-mediated single contract) won. A refinement — using MCP-over-HTTP as the contract rather than a separate custom HTTP API — collapses the "second interface to maintain" weakness and is adopted.

The K question (Library catalog discovery UI) was scoped in the Phase G roadmap scoping doc as (R), folding into whatever C settled. Under Pattern B, K resolves naturally: the catalog website (predecessor work, at `agora-library.dev`) is the discovery surface; the chat UI has a "switch entry" affordance backed by the backend's account-bound entry list rather than a duplicate in-product browser.

This ADR encodes Pattern B with the MCP-over-HTTP refinement.

## 2. Decision

Eight commitments. They hold together; weakening any one weakens the others.

**1. The chat UI talks to one backend per session via MCP-over-HTTP.** A single connection target per browser tab. The protocol is JSON-RPC over HTTP for unary calls and Server-Sent Events for streaming, matching FastMCP's existing HTTP transport. There is no separate `/api/v1/` style custom HTTP surface — the contract IS MCP. The chat UI is, structurally, a thin MCP client.

**2. The chat UI implements a hand-written thin MCP client in TypeScript.** No FastMCP-JS or equivalent framework dependency. The client is `fetch` for unary RPCs plus `EventSource` (or `ReadableStream`) for streaming responses, layered with a small JSON-RPC envelope helper. Estimated implementation cost: ~300–500 LOC of TypeScript. The thin-client approach minimizes framework surface for sole-author maintainability per ADR-007 commitment 1's velocity argument.

**3. Self-host backend is `megalos-server` itself.** The same Python package that ships the static UI bundle as package data (per ADR-007 commitment 2) also exposes the MCP-over-HTTP transport the chat UI consumes. Same origin, same port, same binary. The chat UI's connection target is the localhost megalos-server it was served from. megalos-server has its workflows directory loaded (via file-download per v7 §6.3 or any other means); the chat UI's MCP calls run against those local workflows. **Single-binary self-host** per ADR-007 commitment 2 holds end-to-end.

**4. Hosted backend is the operator's commercial agorá backend.** The browser hits agorá-hosted infrastructure (subdomain or path under `agora-library.dev`, pinned at /plan time per ADR-007 §3). The backend speaks MCP-over-HTTP to the chat UI on its outer surface; on its inner surface, it uses FastMCP Client (Python, server-side) to talk to per-entry endpoints (`writing.agora-library.dev`, etc.). The agorá backend is **(O) Operational layer** per ADR-004 commitment 7 — closed-source, paid-only, operator's commercial code. It proxies MCP traffic with cross-cutting concerns layered in.

**5. Per-folder MCP endpoints retained per v7 §6.4 and ADR-009.** The chat UI does not bypass them. AI-agent consumers (Claude Desktop, mikrós-driven agents, future adapters) continue connecting to `<folder>.agora-library.dev` directly via standard MCP transport. The hosted agorá backend proxies *to* these endpoints; self-host's local megalos-server *is* this kind of endpoint. The chat UI sits on top of the same surface AI agents use, just mediated through a backend that adds platform concerns.

**6. Cross-cutting concerns live in the backend layer, not in the chat UI.** ADR-002 session resumption, ADR-003 analytics instrumentation, ADR-005 entry-version-binding resolution, ADR-006 artifact storage — all backend-mediated. The chat UI surfaces UX for these (the resumption affordance, the version prompt, the artifact gallery) but does not implement the persistence, analytics, or version-resolution mechanics. The HTTP API contract surfaces only what the chat UI needs to drive the workflow loop and render its UX; the backend handles everything else under the hood.

**7. Multi-entry parallel sessions via browser tabs.** Each browser tab holds one MCP-over-HTTP session against one entry. The backend tracks sessions per-(user, entry) per ADR-002 §2 commitment 1's "single-click resume per Library entry" framing. The chat UI does not implement an in-product tab manager or multi-entry workspace — that's browser-tab-native, which keeps the UI's state model simple. Users wanting parallel sessions open additional tabs.

**8. Catalog discovery (K) lives at the website, not in the chat UI.** The agorá catalog at `agora-library.dev` is **not part of Phase G at all** — it is a predecessor-work deliverable per v7 §6.5, scoped and shipped before Phase G's MG1 begins. What folds from K into C is *only* the chat UI's in-product **"switch entry" affordance**: a small surface inside the chat UI that lets users move between entries within their account-bound entry list, where the entry list is **resolved by the backend per ADR-005** (account-bound, version-bound, accumulated via "Use in agorá" captures from the catalog website). The chat UI never needs its own catalog browser because (i) the catalog website is the discovery surface and (ii) the backend is the authority on which entries the user has access to. Users discover entries on the catalog; the chat UI's job is execution and resumption against the entries the backend says the user has, not browsing.

## 3. Implementation sequencing

**MG1 — Foundation (per Phase G roadmap scoping §5).** The thin TypeScript MCP-over-HTTP client implementation lands here. A spike at MG1 kickoff verifies the ~300–500 LOC budget; if the spike surfaces complexity (capability-token semantics in browser context, session-resumption protocol edge cases, streaming-cancel semantics) that exceeds the budget meaningfully, this ADR's commitment 2 reopens to consider FastMCP-JS or equivalent.

**MG1 also lands the `megalos-server` HTTP transport surface for chat-UI consumption.** FastMCP already provides MCP-over-HTTP for AI-agent consumers; the chat UI uses the same transport. No new transport implementation is needed — the chat UI consumes what FastMCP already exposes.

**MG2 — Run-mode chat loop** consumes the connection from MG1. The directive/gate/anti-pattern loop is implemented as a sequence of MCP calls (`get_state`, `get_guidelines`, LLM call browser-direct, `submit_step`, repeat).

**MG3 — Catalog and picker** implements the in-chat-UI "switch entry" affordance per commitment 8. The picker surfaces the user's account-bound entry list (resolved by the backend); the discovery surface lives on the catalog website. Configure-mode-naive picker per ADR-003 Clause 1.

**MG4 — Version-awareness and session-resumption UX** consumes ADR-002 + ADR-005 backend-resolved state and renders UX per ADR-005 §2 commitments 1+2 and ADR-002 §2 commitment 1. The chat UI receives "your account has version 0.5.2 of writing; v0.6.0 is available" from the backend and surfaces the [Upgrade]/[Stay] prompt; backend stores the binding.

**MG5 — Self-host distribution and auth integration.** The package-data bundling (ADR-007 commitment 2) makes the chat UI ship inside megalos-server. `X-Forwarded-User` consumption for self-host identity (ADR-002 §3) gets surfaced through the MCP-over-HTTP layer — backend reads the header, attaches identity to MCP calls.

**Hosted agorá backend** is operator's commercial code, sequenced parallel to Phase I. It implements MCP-over-HTTP at the browser-facing edge and FastMCP Client (Python, server-side) at the per-entry-endpoint-facing edge, layering ADR-002/003/005/006 cross-cutting concerns in between. The HTTP API contract on its outer surface is the same MCP-over-HTTP that megalos-server's local backend exposes — capability parity per ADR-004 (C).

## 4. Consequences

**What this commits agorá to.**

- A thin TypeScript MCP-over-HTTP client in the chat UI source. Hand-written, no framework dependency. Implementation lands in MG1.
- The `megalos-server` HTTP transport (already FastMCP-provided) is the connection target for self-host. No new transport implementation required on the runtime side.
- A hosted agorá backend that exposes MCP-over-HTTP on its outer edge and uses FastMCP Client on its inner edge to proxy to per-entry endpoints. (O) per ADR-004 commitment 7. Closed-source operator's commercial code.
- ADR-002 session resumption, ADR-003 analytics, ADR-005 version-binding, ADR-006 artifact storage all backend-mediated. The chat UI surfaces UX for them; persistence and resolution mechanics live in the backend.
- Multi-entry sessions via browser tabs. The chat UI does not implement an in-product tab manager.
- Catalog discovery on the agorá catalog website (predecessor-work deliverable); chat UI has an in-product "switch entry" affordance only, backed by account-bound entry list.
- Per-folder MCP endpoints (per v7 §6.4 + ADR-009) continue to serve AI-agent consumers directly. The chat UI doesn't bypass them; the hosted backend proxies through them.

**What this forecloses.**

- Browser-side FastMCP-JS or equivalent framework dependency at v7 ship. The thin hand-written client is what's committed; framework adoption is a /plan-time revisit if MG1's spike surfaces complexity (per §6 T1).
- Pattern A (browser-direct MCP to per-entry endpoints). Foreclosed structurally on cross-cutting-concerns grounds; reopening would require reopening ADR-002, ADR-003, ADR-005, and ADR-006 in concert.
- Pattern C (hybrid: direct for self-host, backend for hosted). Foreclosed by ADR-007 commitment 2's single-bundle requirement.
- A separate non-MCP custom HTTP API surface. The MCP-over-HTTP refinement is committed; one contract end-to-end.
- An in-product Library catalog browser inside the chat UI. The catalog website is the discovery surface; the chat UI has a "switch entry" affordance only.
- Browser-side direct connections from chat UI to per-entry endpoints in hosted. The agorá backend always sits in the path for hosted; this is positive structural commitment per commitment 4.
- An operator-bypass mode where users connect their hosted-tier chat UI to self-managed entry endpoints. Hosted means hosted; if a user wants direct-to-self-managed-endpoints, they self-host.

## 5. What would have to be true for this to be wrong

Four conditions, named honestly because the decision is not unconditional.

**The thin TypeScript MCP-over-HTTP client implementation cost exceeds the ~500 LOC budget meaningfully.** The estimate rests on JSON-RPC + EventSource being a well-trodden browser pattern that doesn't surface unanticipated complexity. If MG1's spike reveals that capability-token semantics, session-resumption protocol, streaming-cancel coordination, or error-envelope handling drives the implementation to 1500+ LOC, the cost-vs-benefit shifts against hand-writing. Mitigation lives in the §3 sequencing — MG1 spikes the client first; if budget overruns, FastMCP-JS or equivalent framework gets evaluated before commitments compound.

**The hosted agorá backend's MCP-over-HTTP proxy layer introduces unmanageable issues.** Browser → backend → per-entry-endpoint adds two MCP hops where Pattern A would have had one. If proxying surfaces issues — latency stack-up, capability-mismatch between MCP versions on browser and per-entry sides, session-state synchronization across the proxy boundary, streaming response coordination — the architecture's value proposition weakens. Mitigation: a Phase H MH2-adjacent sanity check verifies the proxy layer is buildable cleanly before MG3 (which assumes it). If proxying turns out to be substantially harder than expected, this ADR reopens — likely toward a thinner backend with browser-side direct connections for some paths, which would partially-restore Pattern A's tradeoffs.

**MCP transport-layer breaking changes affect both consumption paths simultaneously.** Under the MCP-over-HTTP refinement, MCP becomes load-bearing for two surfaces at once: the AI-agent consumption path (Claude Desktop, mikrós-driven agents, future adapters connecting to per-folder endpoints) and the chat UI consumption path. A breaking change in MCP's transport layer — protocol version increment with non-backward-compatible semantics, capability-negotiation reshape, streaming-frame format change — hits both surfaces in the same window rather than only the agent surface as it would under Pattern A. The mitigation that makes this acceptable rather than fatal: the AI-agent consumption serves as a **canary**. Claude Desktop and similar mainstream MCP clients have a much larger active user base than the chat UI will at v1, and they hit transport-incompatibility issues before the chat UI's smaller user base would. The agent-consumption traffic acts as early warning. If a breaking change does surface, the chat UI's thin TypeScript client can be updated faster than the broader ecosystem of AI-agent MCP clients — Phase G's own surface is the smaller, more controllable side of the coupling. This ADR reopens only if the canary pattern fails (e.g., transport-layer changes hit the chat UI surface before the agent-consumption surface in a way that doesn't admit fast remediation).

**Phase J reopens with configure-mode requirements that don't fit Pattern B.** ADR-003's T1/T2/T3 triggers may reopen Phase J. If the reopened Phase J's configure-mode design surfaces a connection-model requirement Pattern B can't accommodate (e.g., per-user customized entries that need their own deployed endpoints, or a configure-mode-agent that needs direct browser-side LLM-to-MCP coupling), this ADR reopens alongside ADR-003. The hybrid-feature pattern from ADR-004 commitment 4 is the first-line response: Phase J's specific surface gets a (C) capability + (O) operational split that fits its needs without forcing the run-mode connection model to follow.

## 6. Trigger conditions for revisit

- **T1 — Thin client implementation cost overrun.** MG1 spike reveals the hand-written TypeScript client requires meaningfully more than ~500 LOC. Reopen commitment 2 toward FastMCP-JS or equivalent framework.
- **T2 — Hosted-backend proxy issues surface.** Latency, capability-mismatch, session-state, or streaming coordination problems in the browser → backend → per-entry proxy layer. Reopen commitment 4 toward thinner backend.
- **T3 — Phase J reopens** (per ADR-003 T1/T2/T3). Reopened Phase J's connection-model needs may amend this ADR. Hybrid-feature pattern from ADR-004 commitment 4 is the first-line response.
- **T4 — ADR-007 reopens** (per its own conditions). Cross-coupled — the single-bundle commitment in ADR-007 commitment 2 is the reason Pattern C was rejected. If ADR-007 reopens toward split-bundle, this ADR reopens alongside.
- **T5 — Performance issue at scale.** Hosted backend's MCP proxy becomes a bottleneck at user-traffic volumes Phase I anticipates. Reopen toward partial-direct-connection patterns for traffic-heavy surfaces; the hybrid-feature pattern from ADR-004 commitment 4 applies.
- **T6 — Catalog and chat UI convergence pressure.** If user research after Phase I ship shows that having catalog discovery and chat-UI execution on different domains/surfaces is a UX problem (e.g., users want browse + start-session + switch in one surface), reopen commitment 8 toward in-product catalog browser. Predecessor-work artifact (the catalog website) and Phase G surface remain separate code; the question is whether to fold discovery into the chat UI's surface, not whether to merge the codebases.
- **T7 — MCP transport-layer canary failure.** A breaking transport-layer change hits the chat UI surface before (or in a way that doesn't track with) the AI-agent consumption surface, defeating the canary mitigation in §5. Reopen the MCP-over-HTTP refinement toward a separate HTTP API contract that decouples the chat UI's transport from the agent-consumption transport.

## 7. References

- vision-v7 §3.1 (consumer surface — agorá's catalog and chat UI definitions).
- vision-v7 §3.2 (the Library — content layer; per-folder MCP endpoints).
- vision-v7 §3.3 (two consumption paths — MCP-connect and file-download; this ADR's connection model coexists with both).
- vision-v7 §3.5 (three-layer architecture; the chat UI is consumer-layer, the backend is consumer-or-operator-layer depending on deployment).
- vision-v7 §6.4 (external surface; per-folder endpoints under `<folder>.agora-library.dev`).
- Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) — the (P) classification of C and the (R) classification of K (which folds in here); the five-milestone working model that §3 references.
- ADR-002 (`002-run-mode-session-persistence.md`) — backend mediates the session-resumption affordance per commitment 6; pre-Phase-I "Resume in this tab" affordance still consumes the same MCP-over-HTTP surface, just bound to browser-local session_id rather than account-bound.
- ADR-003 (`003-phase-j-shipping-decision.md`) — backend instruments analytics from launch per Clause 3; the chat UI does not handle analytics directly.
- ADR-004 (`004-paid-vs-self-host-value-asymmetry.md`) — (C)/(O) split runs through the backend layer; HTTP API contract is (C), self-host backend implementation is (C), hosted commercial backend is (O).
- ADR-005 (`005-library-entry-versioning-ux.md`) — backend resolves per-(user, entry) version-binding; chat UI surfaces the prompt and binding-log UX.
- ADR-006 (`006-artifact-retention-decoupling.md`) — backend writes captured artifacts to `ArtifactStore`; chat UI surfaces the gallery.
- ADR-007 (`007-phase-g-chat-ui-stack.md`) — single static bundle commitment is what rules out Pattern C and constrains the chat UI to be a single codebase with one connection model.
- ADR-008 (`008-brand-architecture.md`) — agorá branding; the chat UI presents agorá identity regardless of deployment.
- ADR-009 (`009-repo-consolidation.md`) — per-folder MCP endpoints under the aggregator structure; this ADR consumes the per-folder endpoints rather than restructuring them.

---

*End of ADR-010. This ADR's commitments hold conditional on the thin TypeScript MCP-over-HTTP client landing within budget at MG1 and on the hosted agorá backend's proxy layer being buildable cleanly. If MG1's spike reveals client complexity overrun, or if proxy layer issues surface during Phase H/I implementation, this ADR reopens — likely toward framework adoption (T1) or thinner backend (T2), respectively.*
