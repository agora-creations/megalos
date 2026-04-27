# megálos vision-v7: agorá, Workflows, and megálos

**Date:** 2026-04-27
**Supersedes:** vision-v6 (2026-04-26)
**Status:** Canonical. Promoted from draft on 2026-04-27 after the predecessor /discuss session resolved the brand-architecture and repo-topology open questions. Where v6 and v7 conflict, v7 governs. v6 is retained as historical reference.

---

## 1. What v7 is

Vision-v6 re-centered the product narrative on two pillars — Workflows (a curated catalog of MCP-server collections, called "the Library" in v6 prose) and megálos (a hosted chat UI in which users pick a collection and run its workflows under BYOK inference). The technical thesis carried forward from v5; the commercial story sharpened.

Vision-v7 makes three changes to v6: two reversals and one addition. The technical thesis is unchanged. The five customer shapes are unchanged. Every v6 guardrail is preserved.

**Reversal 1 — repo topology.** v6 inherited a multi-repo pattern from prior phases: each collection (v6 prose: "Library entry") was its own repository under `agora-creations` (`megalos-writing`, `megalos-analysis`, `megalos-professional`, plus future additions). v7 consolidates these into a single aggregator repository with one folder per collection. Server-level catalog granularity from v6 §3.1 is preserved unchanged — one MCP server per collection, one collection per domain. Only the multi-repo *structural* pattern reverses.

**Reversal 2 — brand inversion.** v6 §9 Q1 resolved "megálos" as the consumer-facing brand of the paid product, with `agora-creations` retained as the GitHub-organization brand and the legal/billing entity deferred. v7 inverts this: **agorá** becomes the consumer-facing brand for both surfaces (catalog website and chat UI) and both deployments (self-host and hosted). megálos demotes to the runtime's technical name — `megalos-server` at the package level, "the megálos runtime" in technical contexts where disambiguation matters. mikrós similarly stays at the developer-tooling layer under existing naming. `agora-creations` remains the GitHub-organization brand. A self-hoster running `pip install megalos-server` and hitting `localhost` in their browser sees agorá branding — the GitLab-analogy: product identity travels with the bundle, not with the operator.

**Addition — file-download consumption path.** v6 framed collection consumption as MCP-connect-only: the user (or their AI agent) connects to a deployed MCP server endpoint and runs the collection's workflows. v7 adds an `npx`-style install path that drops a collection's YAML directly into the user's local `megalos-server` workflows directory, where it is loaded by the runtime exactly as a hand-authored workflow would be. The hosted-side equivalent is a "Use in agorá" affordance on the catalog website that adds the collection to the user's hosted agorá account. Two consumption paths, one set of Workflows, no schema change.

The conceptual analog explicitly validated by the operator: VoltAgent's `awesome-design-md` aggregator repo plus its `getdesign.md` website. One aggregator, collection-per-folder, sibling website with collection-per-page browsing, two install paths.

The downstream consequences — what the consumer sees, where the content lives, how the surface is named in marketing — are large. The runtime, the schema, the curation discipline, the inference economics, and the customer-shape framework do not change.

---

## 2. The technical thesis (unchanged from v6 → v5)

Restated for register completeness:

- **LLM interprets, code enforces.** The MCP server is the deterministic layer. All structural enforcement — out-of-order rejection, output_schema validation, forward invalidation, session caps, TTL, the `_DO_NOT_RULES` injection — is mechanical and code-level. None of v7's product framing changes this.
- **Schema as contract.** YAML stays canonical. The schema (`megalos_server/schema.py`) is the source of truth across every authoring surface and every consumer surface.
- **Three-dependency runtime.** `fastmcp`, `pyyaml`, `jsonschema`. Phase H pluggable backends live in extras. Workflows, agorá, and the file-download path add no hard runtime dependency.
- **Provider-agnosticism.** No per-provider prompt translation. Workflows run the same against any provider the user's API key supports.
- **Progressive tool disclosure.** The agorá chat UI must not load all tool definitions upfront.
- **The expressiveness ceiling.** No debugger, no interpreter, no recursion. The schema does not become Turing-complete.

The thesis applies to every product surface v7 introduces.

---

## 3. The product — agorá, Workflows, and megálos

### 3.1 agorá — the consumer surface

agorá is the consumer-facing brand. Two surfaces sit under it, deployed both as a self-host bundle and as a hosted product:

- **The catalog website** (`agora-workflows.dev` at v1 — see §6.4 for migration commitment). The discovery surface. A user lands here, browses collections by domain (writing, analysis, professional, future additions), reads what each does, and decides which to use. SEO matters because this is the entry-point surface; mostly-static pages with collection-per-page browsing; SvelteKit + adapter-static is the v1 implementation per ADR-007.
- **The chat UI** (subdomain or path under `agora-workflows.dev` — exact hostname pinned at Phase G `/plan` time). The working surface. Users select a collection from the catalog, configure it lightly, supply their own LLM API key, and run the collection's workflows interactively. Plain Svelte SPA, static-bundle target per ADR-007. Two modes inside one UI: run mode (the mass surface, per v6 §3.2), and configure-mode-naive picker (per ADR-003 Clause 1).

Both surfaces are agorá-branded, both in the hosted deployment and in the self-host bundle. There is no megálos-branded fallback. A user running `pip install megalos-server` and visiting `localhost` sees the agorá catalog and chat UI, branded identically to the hosted product. This is the GitLab-self-host analog: the product identity is the bundle, not the operator.

### 3.2 Workflows — the content layer

Workflows is the curated catalog of megálos MCP-server collections. v6 §3.1 commits the granularity (one collection equals one MCP server) and the curation discipline (closed at launch under sole-author curation; opens with mikrós-driven scale). v7 preserves both unchanged. What v7 changes is repo topology.

**One aggregator repository.** Workflows lives at the operator-pinned aggregator repo under `agora-creations` (exact name pinned in ADR-009). Each collection is a folder inside the repo: `writing/`, `analysis/`, `professional/`, plus future additions. The folder naming drops the `megalos-` prefix that prior repos carried — inside the aggregator the prefix is noise, and inside the post-inversion brand architecture the prefix references a layer (the runtime) the content layer doesn't represent.

**Per-collection MCP endpoints retained.** Each folder deploys to its own MCP server endpoint. Hostname pattern at v1: `writing.agora-workflows.dev`, `analysis.agora-workflows.dev`, `professional.agora-workflows.dev` (per Q2 of the predecessor /discuss). Self-hosters configure their own hostnames; the pattern is the operator's hosted-deployment convention, not a runtime constraint.

**Per-collection versioning retained.** Each collection has its own release tag at the folder level (`writing-v0.6.0`, `analysis-v0.4.2`, `professional-v0.5.1`). ADR-005's account-bound version-binding model operates on per-collection versions; the aggregator-repo structure does not change ADR-005's commitments.

**OSS commitment unchanged.** Every collection is OSS at the source level under the aggregator repo. v6 §6.6's OSS scope holds — runtime, Workflows, mikrós skill library, and agorá UI source are open in perpetuity; the operational layer is the operator's commercial code.

The structural reversal — three repos to one — has operational reasons that ADR-009 records. v7 commits the *pattern*; ADR-009 commits the *reasoning*.

### 3.3 Two consumption paths

A collection is consumed in one of two ways. v6 named only the first; v7 adds the second.

**Path 1 — MCP-connect.** The user (or their AI agent) connects to a deployed MCP server endpoint and runs the collection's workflows. Hosted users connect to operator-deployed endpoints (`writing.agora-workflows.dev`, etc.); self-hosters deploy their own (or use someone else's). This is v6 §3.2's path, unchanged.

**Path 2 — File-download.** The user runs an `npx`-style command (or, for hosted users, clicks "Use in agorá") that drops the collection's YAML files directly into their `megalos-server` workflows directory (or their hosted agorá account). The runtime loads them exactly as it would load any hand-authored workflow. No new schema, no special path in the runtime, no privileged API. The downloaded YAML is identical to what's served at the MCP endpoint — this is a distribution mechanism, not an alternative content shape.

The file-download path serves users who want to:

- **Run the collection locally without deploying an MCP server.** A Shape 1 or Shape 2 user developing in their own environment doesn't need a hosted MCP endpoint; the local `megalos-server` already runs the collection.
- **Customize the collection beyond what configure mode (Phase J, deferred per ADR-003) would allow.** A downloaded collection is regular YAML workflows — the user can edit them freely, version-control them, fork them. The original collection on the catalog is unaffected.
- **Inspect the collection's contents before running.** The YAML is the source of truth; downloading it makes the contract visible without requiring an MCP connection first.

The hosted "Use in agorá" affordance is the same path served differently: the user's hosted agorá account gets the collection added, with the same opt-in upgrade and version-binding semantics ADR-005 commits.

### 3.4 megálos and mikrós — the technical layer

**megálos** is the runtime. The Python package is `megalos-server`; the runtime is "the megálos runtime" in technical contexts. It is not a consumer-facing brand. It is the implementation that runs Workflows collections, regardless of whether they're served via MCP-connect or loaded via file-download. Self-hosters install `pip install megalos-server`; hosted-product operators run the same package on their managed infrastructure. `megalos-server` is OSS in perpetuity per v6 §6.6.

**mikrós** is the agent-skills library at `agora-creations/mikros`. Its consumers are AI coding agents (Claude Code, Gemini CLI, future adapters) and the developers who configure them. mikrós is developer-tooling, not consumer-facing. It stays externally visible under existing naming. Phase F's v0.2.1 release is grandfathered as-is — its references to megálos as the runtime are correct under the v7 framing because megálos *is* the runtime; the inversion doesn't reach into developer-tooling layer.

The brand-reframe sits cleanly because the three layers (consumer / content / technical) were already structurally distinct; v7 makes the naming match the architecture.

### 3.5 The three layers — how they relate

| Layer | Brand | Surface |
|-------|-------|---------|
| **Consumer surface** | agorá | Catalog website + chat UI. What end users see. |
| **Content layer** | Workflows (aggregator repo under `agora-creations`) | Curated MCP-server collections with workflows. What agorá serves to users. |
| **Technical layer** | megálos (runtime) + mikrós (skills) | Implementation, schema, agent-skill library. What developers and contributors see. |

A user encounters agorá and never needs to know about megálos or mikrós. A self-host operator encounters all three because they install the runtime that serves the consumer surface. A Shape 1 contributor authoring a collection encounters all three plus mikrós for AI assistance. Each layer addresses its own audience without bleeding into the others.

---

## 4. Customer shapes (unchanged from v6)

v6's five customer shapes carry forward without amendment. Restated tersely with the new naming:

- **Shape 1 — Technical YAML authors.** Author Workflows candidates. Use shipped runtime and authoring DX. May self-host any combination of Workflows and agorá. Do not pay for hosted agorá unless they value its operational maturity.
- **Shape 2 — Small teams and indie developers.** Build domain-specific workflows with mikrós assistance. May contribute collections back to Workflows. May self-host or use paid agorá.
- **Shape 3 — Enterprise self-hosters.** Self-host agorá plus Workflows on their own infrastructure. Phase H serves them.
- **Shape 4 — Hosted-plan customers.** Use paid agorá, pick a collection, BYOK. The primary paying audience.
- **Shape 5 — Non-technical configurers.** Use paid agorá, pick a collection, configure it lightly. Audience deferred per ADR-003 (Phase J shipping decision).

The shapes-as-gradient framing from v6 §4 holds — "build their own" (Shape 1) to "pick and configure" (Shape 5) — with agorá and Workflows shared across all five.

---

## 5. What v7 preserves from v6

The following v6 positions carry forward unchanged and are re-asserted:

- **The technical thesis** (v6 §2). Unchanged.
- **Catalog granularity** (v6 §3.1). One collection equals one MCP server. The repo-topology reversal in v7 §6.1 does not change this.
- **Curation discipline** (v6 §3.1). Closed at launch under sole-author curation; opens with mikrós-driven scale; mikrós-walked end-to-end and real-LLM-verified before shipping.
- **Workflows is OSS** (v6 §3.1, §6.6). Every collection is open-source under the `agora-creations` aggregator repo.
- **agorá (formerly megálos in v6 prose) is paid for infrastructure** (v6 §3.2, §6.2). Inference stays BYOK in perpetuity. Self-hosting stays a first-class supported path.
- **megálos and Phase G/Phase I coupling** (v6 §6.5). Phase G builds the chat UI surface; Phase I deploys it on Phase H'd infrastructure with billing, auth, and managed operations. v7 renames the surface (now agorá) but keeps the coupling.
- **Phase J scope shrunk to configure mode and deferred** (v6 §6.4 + ADR-003). Phase J's eventual reopening per ADR-003's T1/T2/T3 triggers is unchanged. Configure mode in Phase J serves Shape 5.
- **OSS commitment** (v6 §6.6). Runtime, Workflows, mikrós skill library, and consumer-surface UI source are OSS. Operational layer is the operator's commercial code.
- **Inference is BYOK in perpetuity** (v6 §5, §6.2). The runtime never sees billing.
- **The five customer shapes** (v6 §4). Unchanged in audience, slightly amended in surface naming.
- **The expressiveness ceiling** (v6 §2, §5). Unchanged.
- **All ADRs to date** (ADR-001 through ADR-006). Carry forward without disturbance. ADR-005's per-folder versioning operates on the new aggregator-repo folder structure unchanged.

---

## 6. New decisions in v7

### 6.1 Repo consolidation (Reversal 1)

The three current collection repositories — `agora-creations/megalos-writing`, `-analysis`, `-professional` — collapse into one aggregator under `agora-creations` (exact name pinned in ADR-009). Each collection becomes a sibling folder: `writing/`, `analysis/`, `professional/`. Future collections are added as sibling folders without further repo proliferation.

**Server-level catalog granularity is preserved.** v6 §3.1 commits "one collection equals one MCP server"; v7 holds this commitment. Each folder deploys to its own MCP endpoint. The reversal targets only the multi-repo *structural* pattern, not the catalog granularity itself.

**Per-collection versioning retained.** Each collection tags its own releases (`writing-v0.6.0`, `analysis-v0.4.2`, etc.). ADR-005's account-bound collection-version binding operates on per-folder versions. The aggregator-repo structure does not collapse versioning to a single repo-level version.

**Per-collection MCP deployment retained.** Each folder deploys independently. The deployment hostname pattern is `<folder>.agora-workflows.dev` (per §6.4). Self-hosters configure their own hostnames.

**Migration handling for existing repos** is predecessor-execution work, not v7 strategic commitment. Issues, PRs, stars, watchers carry over via GitHub's repo-archive-and-redirect or repo-rename-then-merge mechanisms; the operational details land at the predecessor-work-execution gate.

ADR-009 records the operational reasoning behind the consolidation pattern.

### 6.2 Brand inversion (Reversal 2)

agorá is the consumer-facing brand for both surfaces (catalog website and chat UI) and both deployments (self-host and hosted). megálos demotes to the runtime's technical name — `megalos-server` at the package level, "the megálos runtime" in technical contexts where disambiguation matters. mikrós stays at the developer-tooling layer under existing naming. `agora-creations` remains the GitHub-organization brand.

This reverses v6 §9 Q1 (which resolved "megálos" as the consumer-facing brand) and supersedes v6 §9 Q8's deferral of the consumer brand for the legal/billing entity. Inline amendment-markers in v6 point readers at this section.

The three-layer architecture (consumer / content / technical) is now named consistently:

- **Consumer:** agorá. End users encounter this name on the catalog website, in the chat UI, in marketing materials, in self-host bundles. The product identity travels with the bundle, not with the operator — a self-hoster sees agorá branding on their `localhost`, the same way a self-hosted GitLab instance is branded GitLab.
- **Content:** Workflows, hosted at the operator-pinned aggregator repo under `agora-creations` (exact name pinned in ADR-009). The repository sits inside the `agora-creations` org; folder names inside it (`writing/`, `analysis/`, `professional/`) are content-descriptive without brand prefix.
- **Technical:** megálos (runtime) and mikrós (skills). Greek-named, technical-tool addressed at developers and AI agents. Not consumer-facing.

ADR-008 records the strategic reasoning behind the brand-architecture decision.

### 6.3 File-download consumption path (Addition)

v6 §3.2 framed collection consumption as MCP-connect-only — users connect to a deployed MCP server endpoint and run collections via FastMCP Client. v7 adds a second path: file-download.

**The npx-style install path.** A user runs a command that drops a collection's YAML into the user's local `megalos-server` workflows directory. The runtime loads it as a regular workflow on next startup (or via a hot-reload if MH4 is shipped). No new schema, no special runtime path, no privileged loading semantics. The downloaded YAML is byte-identical to the YAML the MCP endpoint would serve.

**The hosted-side "Use in agorá" affordance.** On the catalog website, each collection has a "Use in agorá" button alongside the existing MCP-connect option. Clicking it adds the collection to the user's hosted agorá account, applying ADR-005's account-bound version-binding from the moment of capture.

The file-download path is *additive*. It does not replace MCP-connect; both coexist. The consumer chooses based on use case:

- MCP-connect for "I want to run this against an LLM agent right now without managing local infrastructure."
- File-download for "I want this collection in my own deployment, my own version control, my own modification path."

Implementation is bounded — the path is essentially "fetch raw YAML from the catalog, write to disk." The runtime requires no changes to load YAML it didn't author. The catalog website and the MCP-deployment infrastructure both serve the same source files.

### 6.4 External surface and migration commitment

The operator-owned base domain at v1 is **`agora-workflows.dev`**. The catalog website lives at the apex; MCP endpoints follow the `<folder>.agora-workflows.dev` pattern (`writing.agora-workflows.dev`, etc.); the chat UI's subdomain or path is pinned at Phase G `/plan` time.

The bare-name domain `agora.{dev,run,tools}` is the **preferred long-term shape** but unobtainable at v7 ship. All three are registered with active NS records, dormant on HTTP — held by parties who have not made them publicly purchasable. v7 commits to `agora-workflows.dev` as the v1 external surface and names bare-name domain acquisition as a future opportunity. If at any future point one of `agora.{dev,run,tools}` becomes acquirable at acceptable cost, the migration triggers a domain-migration amendment to v7 (or a successor vision document) — the structural commitments do not change; only the specific TLD in external-surface references migrates.

This deferral pattern follows v6 §6.4 (consumer-subscription onramp removal — name the principle, defer the specifics) and v6 §9 Q3 (pricing model — commit the constraint, defer the value). Vision documents pin the architecture; specific resource acquisitions land as amendments when their triggers fire.

### 6.5 Predecessor work as a phase

Predecessor work formalizes v7's three changes operationally before Phase H MH1 begins. It is not Phase G; it is not Phase H; it is its own phase between the current state (post-M012, post-Phase-F) and Phase H MH1. Phase G's chat UI assumes the catalog website already exists — predecessor work ships the catalog so that Phase G has an entry point.

Predecessor work has its own ordered sub-sequence:

1. **Brand resolution.** Resolved in the predecessor /discuss of 2026-04-27. The five Q1–Q5 outputs are the input to this vision-v7 document.
2. **vision-v7.** This document.
3. **Repo consolidation and per-folder deploy migration.** Move three repos into one; migrate deploy infrastructure to per-folder endpoints under the new domain.
4. **Catalog website MVP.** Static site at `agora-workflows.dev`, collection-per-page browsing, both consumption paths surfaced.

Predecessor work has no roadmap document yet. Its scope is what's enumerated here; a roadmap document may follow once the brand-resolution and repo-consolidation slices are in execution. The shape of this phase is not GSD-2 milestone-scaled in the same way M001–M012 were; it is closer in shape to "ship the rescoping operationally before downstream phases consume it."

### 6.6 OSS commitment (preserved from v6 §6.6)

Restated for completeness. The runtime (`megalos-server`), Workflows (the operator-pinned aggregator repo under `agora-creations`), the mikrós skill library, and agorá's UI source are committed open-source in perpetuity. The operational layer — billing, auth, deployment automation, observability infrastructure, fleet management — is the operator's commercial code and is not open-source. ADR-004's (C)/(O)/(B) framework is the categorization discipline.

Renaming consumer-surface from megálos to agorá does not change the OSS scope. Every component v6 committed as OSS remains OSS.

---

## 7. Relationship to the roadmap

The roadmap phases keep their letters. What changes is the predecessor work (new) and naming-surface adjustments throughout.

**M001–M012 (shipped).** Runtime, post-parity authoring DX, workflow versioning, dry-run inspector, IDE support. Unchanged.

**Phase F (shipped).** mikrós external library at `agora-creations/mikros`. Claude Code v1 empirically certified at v0.2.1 on 2026-04-26. v0.2.1 is grandfathered as-is per the predecessor /discuss Q5 resolution. Future adapters (Gemini CLI / OpenCode at v1.1, Codex at v1.2) proceed under the existing portability protocol.

**Predecessor work (next).** Repo consolidation, brand-architecture rollout, catalog website MVP at `agora-workflows.dev`. Lands before Phase H MH1.

**Phase G (after predecessor work).** agorá's chat UI. Run mode plus configure-mode-naive picker. Self-host-capable from day one. Assumes the catalog at `agora-workflows.dev` exists as the user's entry point. Roadmap document to be drafted after the four (P) /discusses identified in the Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) resolve. Tech stack and distribution shape: ADR-007 (drafted last, after this v7 ships, with stable naming references throughout).

**Phase H (after predecessor work).** Distribution hardening, MH1 → MH6 per the Phase H roadmap. Scope unchanged from v6. Now sits behind predecessor work as well as Phase G in the dependency graph.

**Phase I (after Phase H MH2–MH4).** Hosted agorá platform. Phase G's UI deployed on Phase H'd infrastructure with billing, auth, and managed operations. The paid product. Pricing model is a Phase I `/discuss` deliverable (v6 §9 Q3, unchanged).

**Phase J (deferred indefinitely per ADR-003).** Configure mode, layered on Phase G. Reopens per ADR-003's T1/T2/T3 triggers.

**Workflows curation (parallel sustained track).** Not a phase. Ongoing. Now operates on the consolidated aggregator with sibling folders rather than on three separate repos.

---

## 8. Out of scope for v7

These belong in later documents, remain rejected, or are downstream details:

- **The chat UI's exact subdomain or path** (e.g., `app.agora-workflows.dev` vs `agora-workflows.dev/run`). Phase G `/plan` time.
- **The `agora-ui` repo question** (where the chat UI source lives — separate repo bundled as package data, or inside `megalos-server`). Predecessor-work `/plan` time, before Phase G's MG1 begins.
- **The Workflows aggregator repo migration mechanics** (issue carryover, archive of old repos, redirect handling). Predecessor-work execution detail.
- **The bare-name domain acquisition timeline.** Indefinite. Not on any phase's critical path.
- **Detailed scope of configure mode.** Phase J work, deferred per ADR-003.
- **Exact pricing model.** Phase I scoping, v6 §9 Q3, deferred.
- **Workflow-marketplace mechanics.** Curation is closed at launch; opening to third-party submissions is downstream of mikrós-driven scale arrival.
- **Mobile agorá.** Web-first at v1. Mobile is deferred until web shows user signal.
- **A second runtime, a second schema, or GUI-specific schema extensions.** Rejected (carryover from v6).
- **Python or arbitrary-code escape hatches in YAML.** Rejected (carryover from v6).

---

## 9. Open questions

The following should be resolved during the relevant phase's `/discuss` gate, not preemptively. Inherited from v6 with status updates plus one new addition.

1. **The naming question — RESOLVED in v7.** v6 §9 Q1's resolution (megálos as consumer-facing brand) is superseded by §6.2 above. Consumer brand is **agorá**; runtime technical name is **megálos** (`megalos-server`); developer-tooling skill library is **mikrós**; GitHub-org brand is **agora-creations** (unchanged). Inline amendment-marker in v6 §9 Q1 points readers here.

2. **OAuth feasibility for consumer-subscription onramp — RESOLVED (negative) in v6 §9 Q2.** Carries forward from v6 unchanged. Quarterly re-check remains standing operator discipline.

3. **The pricing model for agorá** (formerly "for megálos"). Per-server-hosted, per-active-collection, flat-tier, freemium-with-metered-LLM-passthrough, hybrid. Phase I scoping question. Carries forward from v6 §9 Q3 unchanged in substance; only the surface name changed.

4. **Self-host vs paid: explicit value asymmetry — RESOLVED in v6 §9 Q4 → ADR-004.** Carries forward unchanged.

5. **The minimum Workflows catalog size for agorá launch.** v6 §6.1's 5-to-10-collection floor carries forward. Empirical question; resolved by user signal post-launch.

6. **The embedded agent's failure modes** (Phase J). Deferred with Phase J per ADR-003.

7. **Workflows quality enforcement at opened curation.** Future document. Closed curation is sufficient at v1.

8. **Consumer brand for the operator entity — RESOLVED in v7.** v6 §9 Q8's deferral collapses: consumer brand is **agorá**; legal/billing entity name is still operationally deferred but no longer strategically open. Inline amendment-marker in v6 §9 Q8 points readers here.

9. **Run-mode session persistence in paid agorá — RESOLVED in v6 §9 Q9 → ADR-002.** Carries forward unchanged. ADR-006 confirms commitment 4's decoupling.

10. **Collection versioning visible to the user — RESOLVED in v6 §9 Q10 → ADR-005.** Carries forward unchanged. The aggregator-repo structure does not disturb ADR-005's per-folder versioning. (v6 prose framed this as "Library entry versioning"; v7 vocabulary refresh treats "collection version" as the renamed canonical phrase.)

11. **Phase J's economic case under API-key-only — RESOLVED in v6 §9 Q11 → ADR-003.** Carries forward unchanged.

12. **Bare-name domain acquisition trigger.** New in v7. Under what conditions does the operator pursue acquisition of `agora.{dev,run,tools}`? §6.4 names it as a future opportunity without timeline. Concrete trigger conditions (e.g., revenue threshold; brand-conflict event; serendipitous availability) are operator-amendable and not committed at v7 ship.

---

## 10. Summary

Vision-v7 reorganizes the consumer surface, the content layer, and the technical layer into three cleanly-named architectural levels: **agorá** (consumer), **Workflows** (content, hosted at the operator-pinned aggregator repo under `agora-creations`; ADR-009 pins the exact name), and **megálos**/**mikrós** (technical and developer-tooling). The v6 product narrative — open-source content with paid infrastructure for operational maturity, BYOK inference in perpetuity, self-hosting first-class — carries forward unchanged.

The three changes from v6 are: repo consolidation (three collection repos collapse to one aggregator with sibling folders, granularity preserved); brand inversion (agorá replaces megálos as consumer-facing brand for both surfaces and both deployments, megálos demotes to runtime technical name); file-download consumption path added alongside MCP-connect.

The technical thesis is unchanged. The five customer shapes are unchanged. Every guardrail v6 inherited from v5 carries forward. ADR-001 through ADR-006 carry forward without disturbance.

**Domain commitment.** v1 base domain is `agora-workflows.dev` (operator-registered, ~$15/yr). Bare-name `agora.{dev,run,tools}` is the preferred long-term shape; current registration status precludes acquisition at v7 ship. Future acquisition triggers a domain-migration amendment.

**Predecessor work** (brand resolution → this vision-v7 document → repo consolidation + per-folder deploy migration → catalog website MVP) lands before Phase H MH1 begins. Phase G's chat UI assumes the catalog at `agora-workflows.dev` already exists.

The reversal of v6 is in surface architecture, not in technical commitment. v7 preserves every guardrail v6 named, sharpens the three-layer brand structure that v6 left implicit, and pins the rescoping operationally so downstream phases consume it from a stable frame.

---

*End of vision-v7. Brand-architecture commitment recorded separately in ADR-008; repo-consolidation operational reasoning recorded separately in ADR-009. v6 is retained as historical reference; inline amendment-markers in v6 §9 Q1 and Q8 point readers here.*
