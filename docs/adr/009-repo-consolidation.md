# ADR-009 — Repo consolidation

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-27-megalos-vision-v7.md`](../vision/2026-04-27-megalos-vision-v7.md)
**Resolves:** v7 §6.1 repo consolidation — pins the operational reasoning behind the multi-repo-to-aggregator reversal
**Related:** ADR-008 (brand architecture, `008-brand-architecture.md` — the sibling reversal in the same predecessor /discuss; commitment 2 governs the Library → Workflows brand-language shift this ADR's vocabulary follows; the "no `megalos-` prefix on folders" decision derives from ADR-008's brand inversion); ADR-005 (collection versioning UX, `005-library-entry-versioning-ux.md` — operates on per-folder versioning, unchanged by this ADR); v6 §3.1 (Workflows granularity, preserved unchanged).

---

## Update (2026-04-27)

This ADR was originally drafted under v6 prose vocabulary ("Library", "Library entry"). Per **ADR-008 commitment 2** (brand architecture, source-of-truth for the brand-language shift), the consumer-content brand renames to **Workflows** and the folder-unit "Library entry" renames to **collection**. This Update applies that vocabulary throughout: "the Library" → "Workflows" (or "the Workflows catalog" / "Workflows collections" depending on grammatical context); "entry" → "collection" where it refers to the folder unit. **Commitment 1 also pins the previously-abstract aggregator name to `agora-creations/awesome-workflows`** — the v1 commitment to a concrete repo name lives here, not in vision-v7. The hostname pattern migrates from `agora-library.dev` to `agora-workflows.dev` per v7 §6.4. Quoted v6 prose retains "the Library" framing as historical record. Strategic and operational reasoning unchanged; rename + hostname migration + aggregator-name pin are the substantive content of this Update.

---

## 1. Context

Vision-v6 §3.1 commits granularity at the server level (v6 prose: "Library granularity"): "Each entry is a single domain repository — `megalos-writing`, `megalos-analysis`, `megalos-professional`, plus future additions — bundling related workflows behind one MCP server with a single deploy story." The repository-per-collection pattern was inherited from prior phases without explicit strategic justification — it was just how the collections had been organized when v6 was written.

Three operational frictions emerged as the Workflows catalog scaled past three collections in planning:

**Coordination burden across repos.** A schema bump that touches every collection simultaneously (e.g., M010's workflow_fingerprint propagation) requires N parallel PRs, N CI runs, N release tags, N deploy invocations. The marginal cost of each new collection is the same as the original three — N grows linearly, and curator effort grows with it.

**Catalog discoverability.** A user landing on `github.com/agora-creations` sees a flat list of repos with similar names and no obvious entry point. Workflows as a *unified* product surface is invisible at the org-level; users have to know which repo they want before they can find it. The catalog website (predecessor-work deliverable, v7 §3.1) compensates partially, but the GitHub surface remains fragmented.

**Issue-tracker fragmentation.** Cross-cutting concerns (a workflow improvement that applies to writing and analysis; a schema question that affects all collections) get raised in one repo's tracker and lost to the others. The Workflows catalog has no central issue tracker because it has no central repo.

The conceptual analog the operator validated is VoltAgent's `awesome-design-md` aggregator + `getdesign.md` website pattern. One aggregator repo, collection-per-folder, sibling website with collection-per-page browsing, two install paths. The pattern matches v7's three-layer architecture cleanly: the aggregator is the content layer, the website is the consumer layer.

A focused predecessor /discuss session of 2026-04-27 walked the consolidation against the granularity commitment in v6 §3.1, the per-folder MCP-deployment requirement, the per-folder versioning ADR-005 commits, and the migration mechanics for the existing three repos. The outcome — consolidate into one aggregator at `agora-creations/awesome-workflows`, sibling folders, server-level granularity preserved — is encoded here.

## 2. Decision

Six commitments. They hold together; weakening any one weakens the others.

**1. One aggregator repository, pinned name.** The Workflows catalog lives at `github.com/agora-creations/awesome-workflows`. The aggregator-repo name is pinned here (vision-v7 left it abstract; this ADR is the source-of-truth for the v1 commitment). The current three repositories — `megalos-writing`, `megalos-analysis`, `megalos-professional` — collapse into folders inside it. Future collections are added as sibling folders. There is no second aggregator, no per-cluster sub-repo, no parallel multi-repo path.

**2. Folder names drop the `megalos-` prefix.** Inside the aggregator, folders are `writing/`, `analysis/`, `professional/`, plus future additions. The prefix made sense when each repo stood alone establishing ecosystem membership; inside one aggregator the prefix is noise. Under ADR-008's brand inversion the prefix also references the wrong layer — `megalos-` is technical-layer naming attached to content-layer artifacts. Dropping it removes both frictions.

**3. Server-level catalog granularity is preserved.** v6 §3.1's commitment that "one entry equals one MCP server" (now read as "one collection equals one MCP server") carries forward unchanged. Each folder deploys to its own MCP server endpoint. The aggregator structure does not bundle collections into a single MCP server, does not collapse multiple workflows into one collection, and does not change consumer-facing granularity. This reversal targets the *multi-repo structural pattern* only.

**4. Per-collection MCP endpoints retained.** Each folder deploys independently. Hostname pattern at v1: `writing.agora-workflows.dev`, `analysis.agora-workflows.dev`, `professional.agora-workflows.dev` (per v7 §6.4). Self-hosters configure their own hostnames. The deployment infrastructure routes per-folder, not per-aggregator-repo — a folder edit triggers redeployment of only that folder's endpoint.

**5. Per-collection versioning retained.** Each collection tags its own releases (`writing-v0.6.0`, `analysis-v0.4.2`, `professional-v0.5.1`). Tag prefix is the folder name plus `-v`. ADR-005's account-bound collection-version binding operates on per-folder versions; the aggregator structure does not collapse versioning to a repo-level version. Curator releases are per-collection events, not per-repo events.

**6. Migration mechanics: archive-with-redirect plus accepted community-history loss for the v0.x phase.** The three legacy repositories (`megalos-writing`, `-analysis`, `-professional`) get archived after content migration to the aggregator. GitHub's repo-archive feature redirects clones and links to the aggregator. Issues, PRs, stars, and watchers carry over only to the extent GitHub's repo-rename-then-fork mechanism preserves them; for a clean fresh start under the aggregator structure the operator accepts partial community-history loss as the cost of the consolidation. Workflows is at v0.x — community history loss is bounded; the cost of a clean migration is cheaper than the cost of long-term repo-name-mismatch with the brand architecture.

## 3. Implementation sequencing

The repo consolidation is predecessor-execution work, sequenced after vision-v7 ships (this document) and after ADR-008 ships (the brand-architecture commitment that informs folder naming).

**Step 1 — Create `agora-creations/awesome-workflows`.** Empty repo with README naming the aggregator's purpose, a directory structure stub (`writing/`, `analysis/`, `professional/`), and CI scaffolding for per-folder deploy.

**Step 2 — Migrate content per folder.** Copy each existing repo's content into its destination folder. Preserve file history via `git filter-repo` or `git subtree` where the git-history-preservation cost is acceptable; otherwise accept fresh content under new folder paths. The decision per-folder: history preservation if the cost is bounded; clean import if the merge cost would be larger than the value preserved.

**Step 3 — Update deployment infrastructure.** The existing per-repo deploy targets (whatever hosts `megalos-writing.fastmcp.app` etc. today) get rebound to per-folder deploys from the aggregator. Hostnames migrate from `megalos-*.fastmcp.app` (or whatever the current pattern is) to `<folder>.agora-workflows.dev` (per v7 §6.4) once `agora-workflows.dev` is registered and DNS is configured.

**Step 4 — Archive legacy repos.** After content migration is verified and deploy infrastructure is rebound, the three legacy repos get archived with README updates pointing at the aggregator. GitHub's archive-with-redirect handles existing clone URLs; archived repos remain accessible (read-only) so that historical references in third-party docs continue to resolve.

**Step 5 — Catalog website MVP** (sequenced last in predecessor work) consumes the aggregator as its content source. Collection-per-page browsing reads from per-folder content; both consumption paths (MCP-connect via `<folder>.agora-workflows.dev`, file-download via raw YAML download) surface from per-folder structure.

The five steps are ordered because steps 2–4 have dependencies (content must migrate before deploy rebinds; deploy must rebind before legacy repos archive). Steps 1 and 5 are bookends — empty aggregator first; consumer surface last.

## 4. Consequences

**What this commits megálos to.**

- A single aggregator repository at `github.com/agora-creations/awesome-workflows` containing all Workflows collections as sibling folders.
- Folder naming convention: lowercase, no prefix, content-descriptive (`writing/`, `analysis/`, `professional/`, future additions).
- Per-folder MCP endpoint deployment under the `<folder>.agora-workflows.dev` hostname pattern.
- Per-folder release tagging convention: `<folder>-v<semver>` (e.g., `writing-v0.6.0`).
- Archive of the three legacy repositories after content migration; community-history loss accepted as v0.x consolidation cost.
- Future collections added as sibling folders without further repo proliferation. The aggregator is the single source of truth for Workflows at the content layer.
- ADR-005's per-folder versioning remains the correct model — the aggregator structure is invisible to ADR-005's account-bound collection-version binding mechanics.

**What this forecloses.**

- A multi-aggregator pattern (e.g., `awesome-workflows-creative` plus `awesome-workflows-business`). One aggregator at v0.x; sub-aggregation deferred until Workflows size justifies it (per §6 T2 below).
- Repo-level versioning. Each collection versions independently; there is no aggregator-level tag like `awesome-workflows-v1.0.0`.
- Restoring the three legacy repos as active. After archival they are read-only; future work happens in the aggregator only.
- A `megalos-` prefix on folder names. Per ADR-008 the prefix references the wrong layer; reversing this would re-introduce the layer-mismatch friction the consolidation removes.
- Cross-repo PRs against Workflows. There is one repo; PRs touch one or more folders within it.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**Workflows growth makes the aggregator unwieldy.** The v1 Workflows scale is 5–10 collections per v6 §6.1. At 5–10 folders the aggregator is comfortably navigable; at 30+ folders the flat-sibling structure degrades — discovery becomes harder, per-folder CI proliferates, the README's table-of-contents surface gets long. Mitigation lives in commitment 6 of v7 §6.1 (curation discipline) and in periodic structural review. If Workflows scales past ~25 collections without an obvious sub-clustering pattern emerging, this ADR's commitment 1 reopens toward sub-aggregation.

**Per-folder CI tooling friction proves dominant.** GitHub Actions (and similar) optimize for repo-scoped CI; per-folder routing requires conditional triggers and matrix configuration. If the per-folder CI configuration becomes a maintenance burden disproportionate to the curation effort it's enabling, the aggregator's value proposition weakens. Mitigation lives in the predecessor-work CI scaffolding step (Step 1 above) — demonstrating a clean per-folder CI pattern before content migration. If CI friction surfaces post-migration, the response is to revisit the CI implementation pattern, not to revert the consolidation.

**Community-history loss is more costly than expected.** Commitment 6 accepts partial loss of issues, PRs, stars, and watchers as the cost of clean migration. If post-migration analysis reveals that meaningful community engagement was on the legacy repos (e.g., a high-value issue thread that didn't carry over; external links to specific PRs that broke), the migration cost was underestimated. Mitigation: pre-migration audit of the legacy repos' tracker activity; explicit decision per high-value issue/PR whether to manually port or accept loss. v0.x bounds the cost — Workflows is pre-launch at consolidation; community engagement is small.

## 6. Trigger conditions for revisit

- **T1 — Workflows size growth.** Workflows scales past ~25 collections without sub-clustering pattern emerging. Reopen commitment 1 toward sub-aggregation (`awesome-workflows-creative`, `awesome-workflows-business`, etc.). Hybrid-feature pattern from ADR-004 commitment 4 is the first-line response — split content categories into sub-aggregators while preserving the per-folder structure within each.
- **T2 — Sub-domain emergence.** Within a single domain (e.g., writing), entries proliferate enough that sub-clusters emerge naturally (`writing/email/`, `writing/marketing/`, `writing/long-form/`). Reopen commitment 2 toward nested folder structure. Triggers a folder-naming convention amendment, not a structural reversal.
- **T3 — Per-folder CI friction dominant.** Per-folder CI configuration becomes the dominant maintenance cost. Reopen the CI implementation pattern; framework options include Nx, Turborepo, or custom matrix configuration. Does not reopen the consolidation itself.
- **T4 — Community migration to forks.** External contributors fork legacy repos to escape the consolidation. Indicates the migration's tracker handling was insufficient. Mitigation is post-hoc: re-engagement, history-port for high-value threads, or accepting fork-as-community-fragment.
- **T5 — ADR-005 reopens** (per its own conditions). Per-folder versioning is the foundation for ADR-005's account-bound entry-version binding; reopening one would require reopening commitment 5 here alongside.
- **T6 — A third-party Workflows aggregator emerges.** Hypothetical: a competing aggregator pattern from outside `agora-creations` that the operator adopts collections from. Triggers an ADR-005 amendment (per-aggregator versioning) and may amend this ADR's "single aggregator" commitment. Not foreseen at v7 ship; named here so the amendment path exists.

## 7. References

- vision-v7 §3.2 (Workflows — the content layer; aggregator structure described).
- vision-v7 §6.1 (repo consolidation — the strategic commitment this ADR pins operationally).
- vision-v7 §6.4 (`agora-workflows.dev` v1 base domain; `<folder>.agora-workflows.dev` MCP endpoint pattern).
- vision-v7 §6.5 (predecessor work as a phase; the consolidation lands within it).
- vision-v6 §3.1 (Library granularity, preserved unchanged in substance — server-level granularity, not multi-repo structure, was the v6 commitment; v7 vocabulary names this as Workflows granularity).
- ADR-001 (`001-workflow-versioning.md`) — for tone and ADR pattern.
- ADR-005 (`005-library-entry-versioning-ux.md`) — operates on per-folder versioning unchanged by this ADR; the aggregator structure is invisible to ADR-005's account-bound version-binding mechanics.
- ADR-008 (`008-brand-architecture.md`) — sibling reversal in the same predecessor /discuss; commitment 2 is the source-of-truth for the Library → Workflows brand-language shift this ADR's vocabulary follows, and it also licenses "no `megalos-` prefix on folders" via the brand inversion. The two ADRs hold together: brand inversion without repo consolidation would leave folders prefixed; repo consolidation without brand inversion would aggregate but keep `megalos-` prefixes that misname the layer.
- VoltAgent `awesome-design-md` repo + `getdesign.md` website (conceptual analog the operator validated).

---

*End of ADR-009. This ADR's commitments hold conditional on Workflows staying within the v6 §6.1 scale floor (5–10 collections) for the post-launch period and on per-folder CI tooling friction not becoming dominant. If Workflows growth or CI burden surface scale-mismatch with the aggregator pattern, this ADR reopens toward sub-aggregation; the consolidation's reversal would not.*
