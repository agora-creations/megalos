# ADR-008 — Brand architecture

**Status:** Accepted, 2026-04-27
**Supersedes:** none (but inverts v6 §9 Q1 and supersedes v6 §9 Q8's deferral; both questions get inline amendment-markers pointing here)
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](../vision/2026-04-27-megalos-vision-v7.md)
**Resolves:** v7 §6.2 brand inversion — pins the strategic reasoning behind the three-layer brand architecture
**Related:** ADR-001 through ADR-006 (carry forward without disturbance); ADR-009 (repo consolidation, `009-repo-consolidation.md` — sibling reversal in the same predecessor /discuss); v6 §9 Q1 (naming question, superseded by this ADR's commitment 1); v6 §9 Q8 (consumer brand entity, superseded by this ADR's commitment 1).

---

## 1. Context

Vision-v6 §9 Q1 resolved naming as: "the curated catalog is the Library; the hosted chat UI is megálos." Under that resolution, "megálos" was the consumer-facing brand of the paid product specifically. v6 §9 Q8 deferred the legal/billing-entity brand question while noting "likely `agora-creations` remains the GitHub-organization brand and 'megálos' is the consumer-facing product brand."

That resolution had two structural problems that emerged in subsequent strategic conversation:

**The Greek-naming layer collision.** v6's resolution made "megálos" overload two distinct concepts: (a) the runtime (`megalos-server`, the Python package authors and self-hosters interact with), and (b) the consumer-facing chat UI (the surface end users encounter). Same name, two layers, different audiences. The collision was tractable in v6 because no third surface had been named yet.

**The catalog-website-as-second-frontend pressure.** Predecessor strategic work introduced a sister frontend — the catalog website that serves as the discovery surface, distinct from the chat UI. Two consumer-facing surfaces, both needing a brand. Calling the catalog "megálos" too is awkward (it's not the chat UI); calling it something else fragments the brand. The cleanest path is one consumer brand for both surfaces, distinct from the runtime's technical name.

A focused predecessor /discuss session of 2026-04-27 walked the brand-architecture options against the three-layer structure (consumer / content / technical), the five customer shapes (v6 §4), the OSS commitment (v6 §6.6), and the file-download consumption path (v7 §6.3 addition). The /discuss surfaced that the v6 resolution had been correct under v6's information state but is wrong under v7's expanded surface. v7 §6.2 inverts the brand: agorá becomes consumer-facing; megálos demotes to runtime technical name.

This ADR encodes the inversion's strategic reasoning so future surfaces, future ADRs, and future operator decisions can test against the principle rather than re-litigating it.

## 2. Decision

Six commitments. They hold together; weakening any one weakens the others.

**1. agorá is the consumer-facing brand.** Both surfaces — the catalog website at `agora-library.dev` (per v7 §6.4) and the chat UI (subdomain or path under `agora-library.dev`, pinned at Phase G `/plan` time) — carry the agorá brand. Both deployments — hosted and self-host — show identical agorá branding. There is no megálos-branded fallback for self-host: a user running `pip install megalos-server` and visiting `localhost` sees agorá, exactly as a self-hosted GitLab instance is branded GitLab. **The product identity travels with the bundle, not with the operator** (the GitLab-analogy commitment).

**2. megálos demotes to the runtime's technical name.** The Python package is `megalos-server`. The runtime is "the megálos runtime" in technical contexts where disambiguation matters. It is not consumer-facing. End users encountering agorá do not see "megálos" anywhere in the UI surface. Developers, contributors, and self-host operators encounter "megálos" because they install the runtime that serves the consumer surface — the technical layer is theirs to address.

**3. mikrós stays at the developer-tooling layer under existing naming.** `agora-creations/mikros` remains externally visible. Its consumers — AI coding agents (Claude Code, Gemini CLI, future adapters) and the developers configuring them — are the technical-layer audience that the brand inversion explicitly does not reach. Phase F's v0.2.1 release is grandfathered as-is; its references to megálos as the runtime are correct under the v7 framing because megálos *is* the runtime. The brand inversion does not require backwards-compatible mikrós work.

**4. agora-creations remains the GitHub-org brand.** Unchanged. The org name is the legal/operational entity that hosts the open-source repositories — `megalos-server`, `agora-library`, `mikros`, future additions. agorá-the-consumer-brand is distinct from `agora-creations`-the-org-brand by one accent and by a hyphen, but they are intentionally aligned: the consumer brand and the org brand share a Greek root, signaling that the org is the operator behind agorá the product.

**5. Three-layer architecture is the boundary discipline.** Future naming or rebranding decisions test against this layered structure:

| Layer | Audience | Brand | Examples |
|-------|----------|-------|----------|
| **Consumer surface** | End users running workflows | **agorá** | Catalog website, chat UI, hosted product, self-host bundle visible to non-technical users |
| **Content layer** | Library curators + consumers of the Library catalog | **the Library** (at `agora-creations/agora-library`) | The MCP-server entries (`writing/`, `analysis/`, `professional/`, future), their contents, the curation discipline |
| **Technical / developer-tooling layer** | Developers, contributors, AI agents, self-host operators | **megálos** (runtime), **mikrós** (skills) | `megalos-server` Python package, schema, runtime tools, mikrós AGENTS.md, mikrós skills |

A new surface added later is named by the layer it addresses, not by the surface it superficially resembles. A future authoring CLI is technical-layer (megálos-flavored); a future enterprise console is consumer-layer (agorá-flavored); a future AI-agent integration is developer-tooling-layer (mikrós-flavored). When ambiguity surfaces between layers, the audience is the disambiguator: if end users encounter it, it's consumer; if developers configure it, it's technical; if it serves authors of Library content, it's content layer.

**6. The brand inversion targets surfaces, not artifacts at rest.** Existing artifacts that reference "megálos" in the runtime sense remain correct. Documentation, code comments, ADRs, vision documents, and historical conversation logs that say "megálos" continue to say "megálos" where the reference is to the runtime. Surface-level marketing copy (catalog website headline, chat UI title bar, README hero text) gets agorá branding. The discipline is layer-targeted: rename consumer-facing surfaces; leave technical-layer references unchanged.

## 3. Implementation sequencing

The brand inversion's operational rollout is predecessor-work execution, not strategic /discuss output. This ADR commits the strategy; specific rollout work happens at the predecessor-execution gate.

**Phase G UI (under construction) consumes this ADR directly.** Phase G's chat UI must surface agorá branding from MG1's foundation slice. ADR-007 (Phase G tech stack and distribution shape, drafted last per the predecessor /discuss sequencing) cites this ADR for naming references throughout. Self-host bundle ships with agorá branding from day one — there is no transitional megálos-branded build.

**Catalog website MVP** (predecessor work, before Phase H MH1) ships agorá-branded from inception. The website is greenfield; no rebrand work is needed because no prior consumer-surface artifact exists to migrate.

**Existing megalos-* repos** (`megalos-writing`, `-analysis`, `-professional`) collapse into `agora-library` per ADR-009. The repo migration is the visible surface where "megalos-" prefix disappears. Folder names inside the aggregator carry no prefix per ADR-009's commitment 2.

**Existing megalos-server** (Python package) keeps its name. Renaming the package is rejected because the package is the technical-layer artifact; the brand inversion does not reach into the technical layer (commitment 2). PyPI installation, import paths, and developer-facing references to `megalos_server` continue unchanged.

**README and surface documentation** get pass-by-pass updates as files are touched for other reasons. A standalone "rebrand sweep PR" is rejected — the discipline is layer-targeted (commitment 6); blanket find-and-replace would damage technical-layer references that should remain. Updates land alongside other work on the relevant file.

## 4. Consequences

**What this commits megálos to.**

- agorá-branded UI source in the chat UI repo (per ADR-007). Both self-host and hosted bundles serve identical agorá branding.
- agorá-branded catalog website at `agora-library.dev`.
- `megalos-server` PyPI package keeps its name; `megalos-server` directory in the aggregator stays unchanged at the technical-layer level.
- mikrós at `agora-creations/mikros` keeps its name and existing surface; no rebrand work.
- README, marketing materials, and operator-facing copy get pass-by-pass updates per commitment 6's layer-targeted discipline.
- New surfaces added after v7 ship are categorized against the three-layer table (commitment 5) at design time. Categorization sits in the surface's design record (ADR, /discuss output, or PR description).
- v6 §9 Q1 and Q8's prose carries inline amendment-markers pointing readers at this ADR + v7 §6.2.

**What this forecloses.**

- A "megálos for paid, agorá for self-host" split-brand model. Both deployments serve the same agorá-branded UI.
- A megálos-branded transitional fallback during the brand-inversion rollout. Phase G ships agorá-branded from MG1; no transitional state is supported.
- Renaming `megalos-server` the Python package. The technical layer's name is megálos and remains so; commitment 2's "demotes to technical name" means the name stays at the technical level, not that it disappears.
- Renaming mikrós inward. Commitment 3 explicitly preserves mikrós's surface; the brand inversion does not reach developer-tooling layer.
- Selling "agorá" as anything other than the consumer-facing surface. agorá is what end users see; documentation that refers to "the agorá runtime" or "the agorá schema" violates the layer discipline.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**Self-host operators reject seeing agorá branding.** Enterprise self-hosters in particular often want white-labeling — their internal users see "Acme Workflows" or generic naming, not the upstream product brand. If self-host adoption surfaces persistent demand for white-label support and the GitLab-analogy commitment becomes a market liability, this ADR's commitment 1 reopens. The right response is likely an admin-toggleable white-label mode (enterprise feature, (O) per ADR-004), not a megálos-fallback default. The GitLab-analogy precedent is the model: GitLab supports enterprise white-labeling without changing the OSS-default branding.

**The agorá brand attracts a competitor or legal challenge.** "Agora" is a common Greek noun; trademarks tend to be country-specific and class-specific. If a regional or class-specific trademark conflict surfaces (a competitor in workflow automation, an existing US trademark in software services, etc.) and the operator faces a forced rebrand, this ADR's commitment 1 reopens. A pre-launch trademark search would mitigate this; deferred to predecessor-work-execution gate, not committed here.

**The three-layer architecture breaks down as the product evolves.** Commitment 5 assumes consumer / content / technical-developer-tooling are the layers that matter. If a new product surface emerges that genuinely doesn't fit any of the three (e.g., a partner-integration surface that's neither end-user nor developer-facing; a marketplace mechanic that bridges consumer and content), the framework needs revision. Hybrid-feature pattern from ADR-004 commitment 4 is the first-line response: split the surface across multiple layers. If the hybrid pattern doesn't resolve, the framework reopens.

## 6. Trigger conditions for revisit

- **T1 — Self-host white-label demand becomes dominant for enterprise segment.** Reopen commitment 1 toward admin-toggleable white-label mode. Likely a (C) capability addition (the white-label code) plus an (O) operational layer (managed white-label support for enterprise tier).
- **T2 — Trademark / brand conflict surfaces.** Reopen commitment 1 fundamentally — may force agorá → alternative brand. Concrete trigger: legal counsel surfaces an actionable conflict, or a competitor surfaces with confusable brand at a scale that affects user discoverability.
- **T3 — A new surface doesn't fit the three layers.** Reopen commitment 5's table. Hybrid-feature pattern (split across layers) is first-line; framework revision if hybrids don't resolve.
- **T4 — Bare-name domain acquisition** (per v7 §6.4). Triggers a *domain-migration amendment* to v7 (or successor vision), not a reopen of this ADR. Brand commitments are independent of TLD.
- **T5 — `agora-creations` org rename.** Hypothetical: if the GitHub-org gets renamed (e.g., to `agora` if `github.com/agora` becomes available), this ADR's commitment 4 amends. Not foreseen at v7 ship; named here so the amendment path exists.
- **T6 — A future ADR generates a layer-classification dispute.** When a future feature's layer assignment is genuinely ambiguous and the hybrid-feature pattern doesn't resolve it, reopen commitment 5.

## 7. References

- vision-v7 §6.2 (brand inversion — the strategic reasoning this ADR pins).
- vision-v7 §3 (three-layer product structure: agorá / Library / megálos+mikrós).
- vision-v7 §6.4 (external surface and `agora-library.dev` v1 commitment).
- vision-v7 §9 Q1 + Q8 (superseded; this ADR is the replacement reasoning).
- vision-v6 §9 Q1 (the resolution this ADR inverts; v6 carries an inline amendment-marker pointing here).
- vision-v6 §9 Q8 (the deferral this ADR collapses; v6 carries an inline amendment-marker pointing here).
- vision-v6 §6.6 (OSS commitment unchanged; renaming consumer surface from megálos to agorá doesn't change OSS scope).
- ADR-001 (`001-workflow-versioning.md`) — for tone and ADR pattern.
- ADR-002 (`002-run-mode-session-persistence.md`) — naming references update from "megálos run mode" to "agorá run mode" in surface copy; technical-layer references stay megálos.
- ADR-003 (`003-phase-j-shipping-decision.md`) — same surface-vs-technical update.
- ADR-004 (`004-paid-vs-self-host-value-asymmetry.md`) — the (C)/(O)/(B) framework operationalizes commitment 1's "no capability withholding" principle; white-label support per §5/T1 would be an (O) feature.
- ADR-005 (`005-library-entry-versioning-ux.md`) — references to "megálos UX" in surface copy update to "agorá UX"; runtime references stay megálos.
- ADR-006 (`006-artifact-retention-decoupling.md`) — same surface-vs-technical update.
- ADR-009 (`009-repo-consolidation.md`) — sibling reversal; the repo-naming pattern (`agora-library` aggregator, no `megalos-` folder prefix) is the visible artifact of this brand inversion.

---

*End of ADR-008. This ADR's commitments hold conditional on the GitLab-analogy framing being acceptable to self-host operators and on the three-layer architecture remaining a clean fit for new surfaces. If self-host adoption surfaces persistent white-label demand, or a future surface genuinely doesn't fit the three layers, this ADR reopens, not patches.*
