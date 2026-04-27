# megálos vision-v6: the Library and megálos

**Date:** 2026-04-26
**Supersedes:** vision-v5 (2026-04-22)
**Status:** Canonical. Promoted from draft on 2026-04-27 after OAuth-investigation amendment (§6.4, §9 Q2) and resolution of §9 Q9 (see [ADR-002](../adr/002-run-mode-session-persistence.md)) and §9 Q11 (see [ADR-003](../adr/003-phase-j-shipping-decision.md)). Where v5 and v6 conflict, v6 governs.

---

## 1. What v6 is

Vision-v5 named five customer shapes and asserted that megálos serves them through shared runtime, schema, and authoring contracts. v5 added Shape 5 (non-technical authors via visual studio) and the Phase J scaffold to serve them. v5's underlying product story was "one runtime, many authoring surfaces" — technically accurate, commercially diffuse.

Vision-v6 re-centers the product narrative on two pillars:

1. **The Library.** A curated catalog of production-ready megálos MCP servers, each bundling related workflows in a domain (writing, analysis, professional, and future additions). Open-source. Battle-tested. The Library's quality is the product's reputation.

2. **megálos.** A hosted chat UI in which users pick a Library entry, configure it lightly, plug in their own LLM API key, and run it. BYOK for inference. Paid for infrastructure.

The five customer shapes from v5 do not disappear. They remain the audience taxonomy. What changes is that the *product narrative* now leads with the Library and megálos, and the shapes describe who picks what within that narrative.

The technical thesis of the project (LLM interprets, code enforces, schema stays simple) is unchanged. Every guardrail of v5 is preserved. The roadmap phases keep their letters and approximate sequencing. What changes is:

- The product story is concrete and monetizable rather than abstract and BYOK-only.
- Phase J's scope shrinks substantively (configuration, not authoring).
- Phase G and Phase I become tightly coupled as two layers of megálos.
- Library curation is named as a first-class sustained activity parallel to the phase roadmap.
- Inference stays BYOK in perpetuity. Infrastructure is the paid product.

**Naming convention used throughout this document.** "The Library" (capitalized) refers to the curated catalog product surface. "megálos" without qualification refers to the consumer-facing chat UI product. "The megálos runtime" or "`megalos-server`" refers to the underlying server runtime when disambiguation matters. See §9 question 1 for the rationale.

---

## 2. The technical thesis (unchanged from v5)

Restated for register completeness:

- **LLM interprets, code enforces.** The MCP server is the deterministic layer. All structural enforcement — out-of-order rejection, output_schema validation, forward invalidation, session caps, TTL, the `_DO_NOT_RULES` injection — is mechanical and code-level. None of v6's product framing changes this.
- **Schema as contract.** YAML stays canonical. The schema (`megalos_server/schema.py`) is the source of truth across every authoring surface and every consumer surface, including configure mode in megálos.
- **Three-dependency runtime.** `fastmcp`, `pyyaml`, `jsonschema`. Phase H pluggable backends live in extras. The Library and megálos add no hard runtime dependency.
- **Provider-agnosticism.** No per-provider prompt translation. Library entries work the same against any provider the user's API key supports.
- **Progressive tool disclosure.** megálos must not load all tool definitions upfront. Discovery-first architecture inherited from FastMCP CodeMode and tag-based filtering.
- **The expressiveness ceiling.** No debugger, no interpreter, no recursion. The schema does not become Turing-complete to accommodate the Library, megálos, configure mode, or any future authoring surface.

The thesis applies to every product surface v6 introduces.

---

## 3. The product — the Library and megálos

### 3.1 The Library

The Library is a curated catalog of megálos MCP servers. Each entry is a single domain repository — `megalos-writing`, `megalos-analysis`, `megalos-professional`, plus future additions — bundling related workflows behind one MCP server with a single deploy story.

**Granularity: one entry equals one MCP server.** Not one workflow per entry. Not one per repository commit. The granularity matches how users consume: they connect a client to a server and get all of that server's workflows. Splitting at the workflow level fragments the catalog and complicates megálos's connection model. The domain-repo unit is what already exists, what already deploys to Horizon, and what megálos will consume.

**Curation is closed at launch and opens with mikrós-driven scale.** The Library starts under sole-author curation. Each entry ships only after the four-skill mikrós ladder (author → validate → test → deploy) has been walked end to end against it, and after independent verification against a real LLM has confirmed workflow completion against spec. As mikrós adoption grows the candidate pool — Shape-2 contributors authoring Library candidates with skill assistance — curation opens to third-party submissions under a review gate. This sequencing keeps the "battle-tested" claim defensible at the cold-start phase and scales catalog growth without dropping the quality bar.

**The Library is open-source.** Every entry is a public repository under `agora-creations`. The runtime (`megalos-server`) is open-source. The mikrós skill library is open-source. Self-hosting any combination of these is a first-class supported path. The OSS commitment is load-bearing for the technical-author trust the product depends on, and it bounds the lock-in concern that any paid claim could otherwise raise.

### 3.2 megálos

megálos is a hosted chat UI in which a user picks a Library entry, configures it, supplies their own LLM API key, and runs the entry's workflows interactively.

**Two modes inside one UI.** megálos combines two surfaces that v5 kept conceptually separate:

- **Run mode** (formerly Phase G's chat client). The user picks a Library entry, the UI connects to it via FastMCP Client, and the user drives workflows the same way they would drive any megálos workflow — through a chat interface that runs the directive/gate/anti-pattern loop. BYOK inference. This is the mass surface.
- **Configure mode** (formerly Phase J's visual studio, dramatically lighter). The user selects a Library entry and adapts it to their specific case — substituting a directive, adjusting a gate, picking a branch default — guided by an embedded AI agent that reads mikrós at intent level. The agent does not write workflows from scratch; it walks the user through bounded modifications to a curated entry. The output is a YAML workflow, identical in shape to a CLI-authored workflow, that lives under the user's account in megálos.

**The embedded agent is mikrós's primary new consumer.** mikrós's published artifact (Markdown skill content, AGENTS.md cross-tool entry-point, four phase-keyed skills) does not change. What changes is who reads it: in v5 the consumer was an external AI coding agent (Claude Code, Gemini CLI, OpenCode) running in a developer's terminal. In v6 the primary consumer at the user-volume level is the agent embedded in megálos's configure mode. The portability discipline in `docs/ADAPTERS.md` already permits this: any AGENTS.md-supporting agent can consume the skills, and the embedded agent is a constrained instance of exactly that pattern.

**megálos is paid.** Infrastructure costs at the scale Phase H plus Phase I imply (multi-replica session stores, observability, auth, rate-limit shared state, billing, the chat UI itself) cannot be funded by donations or LLM-pass-through margin. Inference stays BYOK — the operator never pays for LLM tokens — and the operator charges for hosted megálos. This is the load-bearing monetization claim of v6 and it is named explicitly here so it does not drift.

**Self-hosting is supported.** A technically capable user can run the megálos runtime, deploy Library entries (or their own forks) to their own infrastructure, and connect any MCP-compatible client. Self-host parity is an OSS commitment; the paid megálos must add value above self-hosting through operational maturity, not through capability withholding.

### 3.3 The relationship between the two pillars

The Library is the product's content; megálos is the product's surface. Neither alone is the product.

- A Library without megálos is a curated catalog that technical authors can self-host and consume. This is a real but narrow product, restricted to Shapes 1–3.
- megálos without a Library is a chat UI with no content to run. This is not a product at all.

The two pillars compound: the Library makes megálos immediately useful (a new user with no workflow expertise can pick an entry and run it); megálos makes the Library immediately consumable (a curated entry with no easy way to run it is a GitHub repo, not a product).

The OSS-content-plus-paid-infrastructure split is a natural one because:

- Open content with paid infrastructure is the proven model — open-source databases with managed cloud offerings, open-source CMSes with managed hosting, open-source code editors with managed pair-programming services.
- The infrastructure is what is hard to operate at scale, not what is hard to copy. A self-host-capable team can replicate the Library in days; replicating the operational maturity is a years-long investment.
- BYOK for inference removes the "the platform marks up tokens" failure mode that would otherwise make the paid claim feel extractive.

---

## 4. Customer shapes — rebalanced

The five customer shapes from v5 are preserved as an audience taxonomy. The rebalance is in how each shape interacts with the Library and megálos.

**Shape 1 — Technical YAML authors.** Author Library candidates. Use the shipped runtime and authoring DX (M001–M012 outputs). May also self-host any combination of the Library and megálos. Do not pay for megálos unless they value its operational maturity over running it themselves.

**Shape 2 — Small teams and indie developers.** Build domain-specific workflows with mikrós assistance in their own development environment (Claude Code, Gemini CLI, etc.). May contribute Library candidates back. May self-host, may use paid megálos for ease of distribution to non-technical teammates. mikrós's external-consumer audience.

**Shape 3 — Enterprise self-hosters.** Self-host megálos plus Library on their own infrastructure for compliance, security, or cost reasons. Phase H serves them.

**Shape 4 — Hosted-plan customers.** Use paid megálos, picking Library entries and running them with their own API keys. The primary paying audience. Phases G and I jointly serve them.

**Shape 5 — Non-technical configurers.** Use paid megálos, picking Library entries and using configure mode to adapt them lightly. Audience is non-technical users *willing to provision an LLM API key* — narrower than v5's "non-technical mass-market" framing because the consumer-subscription onramp is not currently feasible (see §6.4 amendment, §9 Q2). Phase J (light) serves them, layered on top of Phase G's run mode. The strategic question of whether Phase J is worth shipping on API-key-only economics is open; see §9 Q11.

The shapes are no longer five parallel onramps. They are a gradient from "build their own" (Shape 1) to "pick and configure" (Shape 5). The Library and megálos are shared across all five shapes; what differs is how much each shape modifies the entries they pick and where they run them.

---

## 5. What v6 preserves from v5

The following v5 positions carry forward unchanged and are re-asserted here:

- **The expressiveness ceiling** (v5 §4, §9.5). The schema must not become Turing-complete. Configure mode does not expand expressiveness; it surfaces existing expressiveness through a constrained UI.
- **The LLM-interprets, code-enforces thesis** (v5 §4). Configure mode produces YAML; YAML is enforced by the runtime exactly as CLI-authored YAML is.
- **BYOK for inference** (v5 §9.4, §9.10). The runtime never sees billing. megálos's user supplies their own API key. The consumer-subscription onramp ("connect your Claude Pro account") was a v5 commitment that v6 cannot keep — the OAuth feasibility investigation (2026-04-26) determined that no major LLM provider currently supports third-party routing of inference through consumer subscriptions, and the trajectory across Q1 2026 has been restrictive rather than permissive. API-key BYOK is megálos's sole inference onramp at v6 ship; the consumer-subscription onramp is removed from v6 commitments and may return to a future vision if provider behavior shifts. See §6.4 and §9 Q2 for details.
- **Provider-agnosticism** (v5 §9.1). No per-provider prompt translation.
- **Progressive tool disclosure** (v5 §9.2). megálos's chat UI must not load all tool definitions upfront.
- **Three-dependency runtime** (v5 §4.2). `fastmcp`, `pyyaml`, `jsonschema`. megálos runs over a separate distribution; Library entries inherit the runtime's dependency floor; nothing new lands in `megalos-server`.
- **YAML stays canonical** (v5 guardrail 1). Configure mode produces YAML, not an intermediate representation.
- **The schema is the contract** (v5 guardrail 2). One schema, every surface.
- **Templates are workflows, not a subtype** (v5 guardrail 3). Library entries are workflows produced under elevated curation discipline, not a separate schema variant.
- **Studio is a runtime client, not a privileged surface** (v5 guardrail 4). Configure mode reads the same schema and produces the same artifacts as the CLI.
- **Non-technical authoring is bounded by entries** (v5 guardrail 5). Configure mode adapts curated entries; it does not author from scratch.
- **Vision documents formally supersede predecessors** (v5 §6 discipline). v6 supersedes v5; v5 decisions amended by v6 are named explicitly in §6 below.

---

## 6. New decisions in v6

### 6.1 The Library is the product's content layer

The Library is named as a first-class product pillar, not a Phase J deliverable. Curation is a sustained activity parallel to the phase roadmap, not bounded to a milestone. The Library's quality bar — battle-tested, production-ready, mikrós-walked end-to-end, real-LLM-verified against spec — is the operator's standing commitment.

The minimum-viable Library size is **not** v5's "roughly two hundred templates" floor. v5's number was scoped against a free-form template library serving Shape 5 at per-workflow granularity. v6's Library is at the domain-repo granularity (one entry equals one MCP server) and the appropriate floor is much smaller. A defensible v1 Library is in the range of **five to ten domain repos**, each carrying three to seven workflows, each end-to-end verified. The exact floor is empirical and may move based on early-user signal. v5 §9.9's two-hundred-template floor is hereby retired.

### 6.2 megálos is a paid product

Infrastructure for hosted megálos is the operator's revenue surface. Inference stays BYOK in perpetuity. Self-hosting stays supported. The paid claim is on operational maturity, not on capability withholding.

The exact pricing model — per-server hosted, per-active-session, flat-tier, freemium with metered run mode — is deferred to Phase I scoping. What is committed in v6 is the principle: infrastructure is paid; inference is BYOK; capability parity holds between paid and self-hosted.

### 6.3 mikrós's primary consumer becomes the embedded agent

mikrós's external audience (Claude Code, Gemini CLI, and the future v1.1 / v1.2 adapters) remains valid and supported. A new audience — the AI agent embedded in megálos's configure mode — becomes the primary consumer at the user-volume level. mikrós's published artifact does not change.

This answers v5 §9 open question 3 ("Shape-5's relationship to Phase F's mikrós"). The answer is "mostly reusable; the embedded agent is one more AGENTS.md-supporting consumer, constrained to a configure-mode subset of the four skills."

### 6.4 Phase J's scope shrinks

Phase J in v5 was visual studio plus template library plus consumer-subscription onramp. In v6:

- The visual studio shrinks to **configure mode** — bounded modification of Library entries via an embedded AI agent reading mikrós. Not a free-form authoring surface.
- The template library is the OSS Library defined in §3.1, which is the product's content layer rather than a Phase J deliverable.
- **The consumer-subscription onramp is removed.** The OAuth feasibility investigation (`docs/discovery/2026-04-26-oauth-feasibility-investigation.md`) determined that no major LLM provider currently supports third-party routing of inference through consumer subscriptions. As of April 2026: Anthropic explicitly prohibits third-party use of consumer OAuth tokens and enforces server-side; Google has no public surface and actively restricts subscription accounts that use third-party tools via Gemini CLI OAuth; OpenAI's Codex OAuth flow is technically accessible but officially scoped to coding tools and explicitly disclaimed by third-party implementations as not for commercial multi-user services. Phase J ships with API-key BYOK as the sole inference onramp until the provider landscape changes. The investigation memo is the canonical source on this question.

The smaller Phase J ships faster and integrates more deeply with Phase G than v5's heavy studio would have. The six guardrails of v5's studio reversal still hold; what changes is how much studio there actually is to build.

**Downstream consequence — Phase J's economic case requires re-examination.** The consumer-subscription onramp was load-bearing for Phase J's "non-technical mass-market" framing in v5. Without it, Shape 5's audience narrows to "non-technical users willing to provision an LLM API key" — a smaller and more friction-tolerant audience than v5 assumed. The Landbot economic comparison from v5 also weakens: megálos still wins on inference economics (API-key BYOK undercuts Landbot's per-conversation pricing with LLM markup), but the onboarding-friction differential narrows substantially. Whether Phase J is worth shipping under these economics, or should be deferred until provider behavior changes, is open. See §9 Q11.

### 6.5 Phase G and Phase I are tightly coupled

In v5, Phase G was the technical-team client (Shape 2) and Phase I was Horizon Developer+ (Shape 4). In v6 they are two layers of one product:

- Phase G builds the chat UI surface (run mode plus the framework for configure mode), deployable anywhere and self-host-capable from day one.
- Phase I deploys Phase G's surface on the operator's infrastructure with billing, auth, and the operational disciplines Phase H provides.

Sequencing remains G → H → I, but the coupling is now explicit: shipping Phase G without Phase I yields a self-host-only megálos; shipping Phase I without Phase G yields managed infrastructure with no UI. Neither half ships a viable paid product alone.

### 6.6 OSS commitment formalized

The runtime (`megalos-server`), the Library entries (`agora-creations/megalos-*`), the mikrós skill library, and megálos's UI source are committed open-source in perpetuity. The operational layer — billing, auth, deployment automation, observability infrastructure, fleet management — is the operator's commercial code and is not open-source.

This split — open content and open client surface, closed operations — is the defensible OSS line. It preserves the technical-author trust without forcing the operator to open-source the parts of the system that have no community-collaboration value. A self-host-capable team can rebuild equivalent operational tooling from scratch; what they cannot do without significant investment is replicate the operator's operational maturity.

This decision was approved by the operator on 2026-04-26. The OSS scope must be named to make the paid claim coherent; this approval pins the scope.

---

## 7. Relationship to the roadmap

The roadmap phases keep their letters. What changes is content, coupling, and audience.

**M001–M012 (shipped).** Runtime, post-parity authoring DX, workflow versioning, dry-run inspector, IDE support. Unchanged.

**Phase F (shipped).** mikrós external library at `agora-creations/mikros`. Claude Code v1 empirically certified at v0.2.1 on 2026-04-26. Audience expands per §6.3 but the artifact is unchanged. Future adapters (Gemini CLI / OpenCode at v1.1, Codex at v1.2) proceed under the existing portability protocol.

**Phase G (next, re-scoped).** megálos's chat UI. Two modes: run mode and configure mode. FastMCP Client over progressive tool disclosure. Self-host-capable from day one. Configure mode's embedded agent reads mikrós. Phase G does not depend on Phase H or Phase I to ship a viable self-host build. Roadmap document to be drafted; supersedes vision-v4 §3.3 "megálos client" content.

**Phase H (deferred behind Phase G).** Distribution hardening. MH1 → MH2 → MH3 → MH4 → MH5, with MH6 continuous. Same scope as v5's Phase H roadmap document (2026-04-22). Now sits on the revenue-critical path because Phase I depends on it. Discipline to watch: Shape-2 wishlist items will tempt scope expansion during MH1–MH6; the Phase H roadmap stays scoped to Shape 3 self-hosters.

**Phase I (re-scoped).** Hosted megálos platform. Phase G's UI deployed on Phase H'd infrastructure with billing, auth, and managed operations. The paid product. Scaffold to be drafted after Phase H MH2–MH4 land. Pricing model is a Phase I `/discuss` deliverable.

**Phase J (re-scoped, lighter; economics now open).** Configure mode, layered on Phase G. The visual-studio scope is dramatically reduced from v5. Phase J's roadmap document, when drafted, supersedes the v5 Phase J scaffold (`docs/roadmaps/2026-04-22-phase-j-scaffold.md`). Phase J no longer carries the template library — that lives under §3.1 as a sustained track. Phase J no longer carries the consumer-subscription onramp — see §6.4 amendment. Whether Phase J ships at all under API-key-only economics is open (§9 Q11) and resolves before Phase G's `/discuss` gate.

**Library curation (parallel sustained track).** Not a phase. An ongoing investment, beginning at sole-author curation and opening to third-party contributions as mikrós-driven scale arrives. Library quality is the operator's standing responsibility. Curation work proceeds in parallel with phase work, not gated behind it.

The OAuth feasibility investigation (v5 §7 open question 1) was completed 2026-04-26 with a negative result; see §6.4 amendment and §9 Q2. The post-parity evaluation dimensions (timed-user validation against the 30-minute authoring target, workflow completion rate against the >70% spec target, multi-provider validation) are no longer waiting on milestones since three of the four gating milestones (M011, M012, Phase F) have shipped.

---

## 8. Out of scope for v6

These belong in later documents or remain rejected:

- **The detailed scope of configure mode.** What modifications are allowed, how the configuration UI surfaces them, how the embedded agent prompts the user, what failure modes need explicit handling. Phase J roadmap work, not strategic.
- **The exact pricing model for megálos.** Phase I scoping work. v6 commits the principle, not the price.
- **The Library's contribution and review process for opened curation.** A future document. Closed curation is sufficient at v1 and remains so until mikrós-assisted authoring throughput justifies opening.
- **A second runtime, a second schema, or a second source of truth.** Rejected (v5 carryover).
- **Python or arbitrary-code escape hatches in YAML.** Rejected (v5 carryover).
- **Workflow-marketplace mechanics — discovery, ratings, install commands, search across third-party libraries.** Out of scope until the Library is large enough to warrant them and curation is open enough that third-party entries exist.
- **Multi-provider LLM routing inside megálos beyond what FastMCP Client already provides.** Phase G ships against FastMCP Client's existing sampling handlers. Custom routing logic is out of scope.
- **Mobile megálos.** A mobile client (vision-v4's Phase H scope, before Phase H was repurposed for distribution hardening) is deferred until web megálos has user signal. Not committed in v6.

---

## 9. Open questions

The following should be resolved during the relevant phase's `/discuss` gate, not preemptively:

1. **The naming question — RESOLVED.** The curated catalog of MCP servers is **"the Library"** (capitalized when referring to the product surface; lowercase when referring to the general concept). The hosted chat UI product is **"megálos."** Under this resolution, "megálos" is the consumer-facing brand of the paid product specifically, and the underlying runtime is referred to as "the megálos runtime" or "`megalos-server`" in technical contexts where disambiguation matters. The Library is the OSS content layer; megálos is the surface that runs Library entries.

   *Implication for technical writing.* Documentation that refers to "megálos" without qualification refers to the consumer-facing product from v6 forward. Documentation needing to refer to the runtime specifically uses "the megálos runtime" or the package name `megalos-server`. The Library entries (`agora-creations/megalos-writing`, etc.) keep their current `megalos-*` repo naming because the prefix denotes ecosystem membership, not product identity.

2. **OAuth feasibility for consumer-subscription onramp — RESOLVED (negative).** Investigated 2026-04-26 (`docs/discovery/2026-04-26-oauth-feasibility-investigation.md`). All three major LLM providers (Anthropic, OpenAI, Google) currently disallow third-party routing of inference through consumer subscriptions, with the trajectory across Q1 2026 being uniformly restrictive rather than permissive. Consumer-subscription onramp is removed from v6 commitments per §6.4. May return to a future vision if provider behavior shifts; worth a quarterly re-check given how recently the landscape moved. Downstream economic question (whether Phase J is still worth shipping under API-key-only economics) is now Q11.

3. **The pricing model for megálos.** Per-server hosted, per-active-session, flat-tier, freemium with metered run mode, hybrid. Phase I scoping question.

4. **Self-host vs paid: explicit value asymmetry — RESOLVED.** See [`docs/adr/004-paid-vs-self-host-value-asymmetry.md`](../adr/004-paid-vs-self-host-value-asymmetry.md). Decision: three-category framework — (C) Capability OSS in both tiers, (O) Operational layer paid-only closed-source, (B) Billing-bound paid-only by definition — with capability parity preserved across tiers and operational maturity (not capability withholding) as the differentiator. Boundary discipline defaults new features to (C). Hybrid-feature pattern names capability + operational halves separately. Initial feature mapping in ADR-004 §3 is the v1 reference; Phase I scaffolding consumes it. Yearly audit catches drift.

5. **The minimum Library size for megálos launch.** §6.1 names five to ten domain repos as a defensible v1 floor. Empirically validating this requires shipping megálos against a real Library and observing user behavior. Floor may move up or down based on early-user signal.

6. **The embedded agent's failure modes.** Configure mode ships an AI agent reading mikrós. What happens when the agent misinterprets a user's intent, produces a workflow modification that breaks validation, or reaches the limits of mikrós's coverage. What does the user-visible recovery look like. Phase J `/discuss` work.

7. **Library quality enforcement at opened curation.** The closed-curation v1 enforces quality through sole-author discipline. Opened curation needs a review gate. What that gate looks like — automated mikrós-walk verification, human review, both, neither — is a future document.

8. **Consumer brand for the operator entity.** The operator is currently the `agora-creations` GitHub organization. Whether paid megálos carries that brand or a different one is a marketing question that intersects with question 1 (now resolved to "the Library" and "megálos") above. Resolution: likely `agora-creations` remains the GitHub-organization brand and "megálos" is the consumer-facing product brand; final naming for the legal/billing entity is deferred.

9. **Run-mode session persistence in paid megálos — RESOLVED.** See [`docs/adr/002-run-mode-session-persistence.md`](../adr/002-run-mode-session-persistence.md). Decision: Level 1 (account-bound in-flight resumption, 7-day TTL, no browseable history) for paid; same code path with admin-tunable TTL for self-host. Session is not a billing-meaningful unit. Artifact retention is decoupled from session retention. Implementation depends on Phase I delivery for paid account binding; transition story documented in ADR-002 §Implementation sequencing.

10. **Library entry versioning visible to the user.** Library entries evolve. A user who picks an entry and configures it has implicitly bound to a version of that entry. What happens when the entry updates upstream — silent migration, opt-in upgrade, version pinning. Touches ADR-001 and Phase G's connection-management UX.

11. **Phase J's economic case under API-key-only — RESOLVED.** See [`docs/adr/003-phase-j-shipping-decision.md`](../adr/003-phase-j-shipping-decision.md). Decision: defer Phase J indefinitely with three binding clauses (Phase G UI proceeds configure-mode-naive; three explicit revisit triggers covering Phase G post-ship signal, OAuth landscape shift, and run-mode revenue underperformance; audience-overlap as load-bearing input to any T1 reopening with Phase G analytics instrumented at launch to collect the relevant signals). The (d) thin-slice position — ship configure mode's picker + manual tweak panel without the embedded agent — is named in ADR-003 as the most likely T1 evolution but is not committed; revisit happens when one of T1/T2/T3 fires.

---

## 10. Summary

Vision-v6 re-centers megálos's product narrative on two pillars: **the Library** (a curated open-source catalog of production-ready MCP servers) and **megálos** (a hosted chat-UI product in which users pick Library entries, configure them lightly, and run them under API-key BYOK). The Library is the content; megálos is the surface. Neither alone is the product.

The technical thesis is unchanged from v5. The schema, runtime, mikrós skill artifacts, and post-M008 authoring DX investments are all preserved. The five customer shapes from v5 are preserved as an audience taxonomy and rebalanced into a gradient from "build their own" to "pick and configure."

What changes is the product story (concrete and monetizable rather than abstract and BYOK-only), the scope of Phase J (configuration, not authoring), the coupling between Phase G and Phase I (one megálos in two deployment modes — self-host and managed), and the elevation of Library curation to a first-class sustained activity parallel to the phase roadmap.

Inference stays BYOK in perpetuity. Infrastructure is the paid product. Self-hosting is a first-class supported path. Open-source coverage extends to the runtime, the Library entries, the mikrós skills, and megálos's UI source; the operational layer is the operator's commercial code.

**One v5 commitment v6 cannot keep.** The consumer-subscription onramp ("Connect your Claude Pro account") was a v5 commitment carried into v6's initial draft and removed by the OAuth feasibility investigation of 2026-04-26. No major LLM provider currently supports third-party routing of inference through consumer subscriptions. API-key BYOK is megálos's sole inference onramp at v6 ship; the consumer-subscription onramp may return in a future vision if provider behavior shifts. The downstream consequence — Shape 5's audience narrows from "non-technical mass-market" to "non-technical users willing to provision an API key," and Phase J's economic case requires re-examination — is captured as §9 Q11.

The reversal of v5 is in narrative emphasis, not in technical commitment. v6 preserves every guardrail v5 named and adds clarity to questions v5 left at the strategic level.

---

*End of vision-v6 draft. Amended 2026-04-26 to incorporate OAuth feasibility findings. Review against shipped Phase F state and operator's pricing intent before promotion.*
