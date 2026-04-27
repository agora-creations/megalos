# ADR-006 — Artifact retention decoupling

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-26-megalos-vision-v6.md`](../vision/2026-04-26-megalos-vision-v6.md)
**Resolves:** Phase G `/discuss` blocker named in [ADR-002](002-run-mode-session-persistence.md) §2 commitment 4 — "artifact retention can be cleanly decoupled from session retention at acceptable cost."
**Related:** ADR-001 (workflow versioning, `001-workflow-versioning.md`); ADR-002 (run-mode session persistence, `002-run-mode-session-persistence.md` — this ADR confirms its commitment 4); ADR-003 (Phase J shipping decision, `003-phase-j-shipping-decision.md`); ADR-004 (paid-vs-self-host value asymmetry, `004-paid-vs-self-host-value-asymmetry.md` — (C)/(O)/(B) framework applied here); ADR-005 (Library entry versioning UX, `005-library-entry-versioning-ux.md`); Phase H roadmap MH2 (`SessionStore` interface, `../vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`); Phase G roadmap scoping (`../vision/2026-04-27-phase-g-roadmap-scoping.md`).

---

## 1. Context

ADR-002 §2 commitment 4 committed that "artifact retention is decoupled from session retention. Workflow outputs that the user values as work product — committed artifacts, files surfaced for download, structured outputs the user has explicitly captured — persist beyond the 7-day session TTL." The same paragraph named this a Phase G `/discuss` blocker: "If artifact retention cannot be cleanly decoupled from session retention in Phase G's design, this ADR's Level 1 commitment collapses — Level 1 becomes indistinguishable from Level 0 the moment the TTL expires for any user who values their output."

The Phase G roadmap scoping (`docs/vision/2026-04-27-phase-g-roadmap-scoping.md`) classified this question as a (P) pre-roadmap investigation — the only one that can invalidate ADR-002 retroactively. The investigation was run on 2026-04-27 against the current artifact-storage architecture.

**Current state.** Artifacts in megálos's current architecture are not first-class objects with their own lifetime. They exist in three forms, all coupled to the session row by construction:

- `step_data` (user step responses) — column on the `sessions` table.
- `artifact_checkpoints` (intermediate per-step checkpoints, used for resumption) — column on the `sessions` table.
- The final artifact returned by `generate_artifact` — computed on-demand from `step_data`, not separately persisted; ephemeral once returned.

`expire_sessions` deletes the session row entirely on TTL expiry. All three vanish together. Under this architecture, "session TTL = 7 days" means "all user work product = 7 days" — the exact failure mode ADR-002 §2 commitment 4 named.

**Investigation outcome.** Decoupling is achievable at acceptable cost. The architectural pattern — a separate `ArtifactStore` parallel to MH2's `SessionStore`, populated by user-explicit capture actions — is well-precedented and structurally parallel to work Phase H is already doing. The total cost is approximately one milestone-equivalent of work, distributed across Phase G (UI surface) and Phase H (storage interface). Investigation did not surface any architecturally novel risk.

This ADR encodes the investigation's conclusion as a strategic decision so the design specifics — the `ArtifactStore` pattern, the user-captured-explicit model, the pre-Phase-I identity-binding behavior, the (C)/(O) split — are pinned for downstream Phase G slices and Phase H MH2 to reference.

## 2. Decision

Six commitments. They hold together; weakening any one weakens the others.

**1. `ArtifactStore` as a separate interface parallel to `SessionStore`.** Phase H MH2 builds a `SessionStore` interface with SQLite default and Postgres adapter under a conformance test suite; this ADR commits the same architectural shape for artifacts. `ArtifactStore` is an abstract interface (or `Protocol`) covering the surface the runtime needs (write, list-by-owner, get-by-id, delete). The default implementation lives at `megalos_server/store/sqlite_artifacts.py`; the Postgres adapter ships in MH2's extras package. The interface is independent of `SessionStore` — artifacts and sessions are separate stores, separate tables, separate lifetimes, separate retention regimes. They share the storage backend (same Postgres deployment, same SQLite file) but not the row.

**2. User-captured-explicit model.** Artifacts are persisted only when the user takes an explicit capture action. The capture triggers are: (a) calling `generate_artifact` (already produces the definitive output; this becomes the canonical capture path); (b) any UI affordance Phase G adds for mid-session capture ("save this output," download-then-save-server-side flow). Auto-persisting `step_data` as long-lived artifacts is rejected — it conflates session-resumption state with work-product retention, triples storage cost, and serves no observed user need. Session-TTL-extension when an artifact exists ("keep the session alive because the user might want to resume to download") is rejected — it makes session and artifact lifetimes diverge anyway, just messily.

**3. (C)/(O) split per ADR-004.** The `ArtifactStore` interface is **(C) Capability**: OSS, identical in both tiers, default behavior is the same, admin-tunable artifact-retention TTL via envvar. Operational tooling around the store — backup automation, point-in-time restore, deletion-on-request workflow tooling, audit-export, multi-replica artifact replication — is **(O) Operational layer**: paid-only, closed-source. This mirrors the (C)/(O) split for session storage that ADR-004 §3 Group 1 already records. The yearly audit per ADR-004 §4 catches drift.

**4. Pre-Phase-I: artifacts inherit Level 0 alongside sessions.** Account binding is a Phase I commitment per ADR-002 §3. Pre-Phase-I, paid megálos has no account system; artifacts cannot bind to a stable user identity. The pre-Phase-I shape: persistent artifact storage lights up with account binding at Phase I, exactly as Level 1 session persistence does. Pre-Phase-I, users access their artifact via `generate_artifact`'s return value during the session and can download the content to their disk before TTL expiry. This is the initial paid-product state, not a regression — it is what shipping a UI before shipping accounts looks like, applied consistently to artifacts and sessions. Self-host reaches full Level 1 the day MH5 ships per ADR-002 §3; artifacts ride the same identity-propagation path.

**5. Intermediate artifacts (`artifact_checkpoints`) stay session-bound.** The existing `artifact_checkpoints` column on the `sessions` table is step-level resumption state, not user-captured work product. It is correctly bound to session lifetime: when the session expires, intermediate checkpoints expire with it. No change to the current architecture for this surface. The `ArtifactStore` is for *captured* artifacts only; the resumption-state column remains where it is.

**6. Artifact retention has its own TTL, distinct from session TTL.** Specific values are Phase I `/discuss` work (alongside ADR-002's session TTL). The floor is "longer than session TTL" — if artifact TTL ≤ session TTL, the decoupling buys nothing. The ceiling is "indefinite, admin-configurable for self-host" per ADR-004 (C); paid hosting has an operator-set bound to keep the (O) operational cost finite, similar to ADR-005 commitment 5's bounded multi-version hosting framing. Phase G UX must surface the distinction clearly: users see a separate "your conversation has expired" message and "your saved artifacts are still here" affordance.

## 3. Implementation sequencing

**Phase G owns the UI surface.** A Phase G milestone slice (likely within MG2 or MG4 per the Phase G roadmap scoping's working breakdown) implements the artifact gallery / "saved outputs" surface, the in-chat capture affordance (if Phase G adds one beyond `generate_artifact`'s implicit capture), and the UX distinction between session expiry and artifact persistence per commitment 6. Phase G `/discuss` adopts these as launch-time commitments alongside ADR-002's session-resumption affordance, ADR-003's analytics instrumentation, and ADR-005's version-prompt UX.

**Phase H owns the storage interface.** The `ArtifactStore` interface is sequenced alongside MH2's `SessionStore`. Two viable shapes — both acceptable, decided at MH2's `/discuss` gate:

- **Shape A:** MH2 expands to include `ArtifactStore` as an additional slice (MH2 S06 — "ArtifactStore interface and SQLite default"). Adds one slice to MH2; total MH2 LOC budget grows by ~400–600.
- **Shape B:** A new MH7-shaped milestone owns `ArtifactStore` independently, sequenced after MH2 ships. MH2 stays scoped to sessions; artifacts get their own milestone with their own conformance suite.

Shape A is structurally simpler; Shape B preserves MH2's current scope. The MH2 `/discuss` gate picks. Either way, the conformance test suite, Postgres adapter, and migration CLI surfaces follow MH2's pattern exactly.

**Phase I owns the operational tooling.** Backup automation, point-in-time restore, audit-export, deletion-on-request workflow, retention-TTL specifics — all (O) per commitment 3 — are Phase I scoping work. Phase I scaffolding consumes ADR-006 §2's mapping the same way it consumes ADR-004 §3 Group 1.

ADR-002's §3 framed implementation sequencing across the Phase G → Phase I window because ADR-002 commits to building. This ADR's §3 has the same shape because it commits to building parallel infrastructure on the same timeline.

## 4. Consequences

**What this commits megálos to.**

- A `ArtifactStore` interface in `megalos_server/store/`, with SQLite default and a Postgres adapter shipped in MH2's extras package (or MH7 if Shape B is chosen). The interface is part of the runtime's public Python API surface that adapters must satisfy.
- `generate_artifact` writes its output to the `ArtifactStore` keyed by user identity (or pre-Phase-I session-keyed) before returning. Existing return-shape contract is preserved.
- Phase G UI surfaces an artifact gallery / saved-outputs view with a clear distinction between session lifetime and artifact lifetime (commitment 6).
- Phase G `/discuss` adopts the user-captured-explicit model and the pre-Phase-I = Level 0 posture for artifacts (commitments 2 and 4) as launch-time commitments.
- Phase H MH2 `/discuss` picks Shape A or Shape B for the `ArtifactStore` sequencing. The picked shape lands in this ADR via amendment.
- Phase I scoping references commitment 3's (C)/(O) split when scaffolding paid-tier operational tooling for artifacts, alongside ADR-004 §3 Group 1 for sessions.
- The yearly ADR-004 audit (per ADR-004 §4 third paragraph) extends to the artifact surface — categorization stays in (C)/(O) and doesn't drift.
- The artifact-retention TTL value lands in Phase I `/discuss` alongside the session TTL value and the pricing model (v6 §9 Q3).

**What this forecloses.**

- Auto-persisting `step_data` as long-lived artifacts. The user-captured-explicit model is load-bearing for the (b) decoupling shape; auto-persist is named here as rejected so the decision doesn't drift into "well, every step response is technically work product."
- Session-TTL-extension as a substitute for decoupling. A session with an artifact does not get a longer TTL just because an artifact exists. Session and artifact lifetimes are independent by construction.
- A combined `Store` interface that handles sessions and artifacts together. Two separate interfaces, two separate stores. The hybrid-feature pattern from ADR-004 commitment 4 is the right lens: capability layer (the interface) is named per concept, not per bundle.
- Indefinite paid hosting of every captured artifact with no bound. Commitment 6's ceiling is "operator-set bound for paid"; users on stale artifacts may eventually be force-archived with notice. This bounds the operational cost of (O) for the paid tier.
- A retention story where intermediate `artifact_checkpoints` outlive the session that produced them. The resumption-state column stays session-bound (commitment 5).

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**The `ArtifactStore` interface turns out to require a substantively different shape from `SessionStore`.** The architectural-parity argument rests on the two interfaces having similar surfaces — write, lookup-by-owner, get-by-id, delete, with a TTL-based expiry path. If artifacts turn out to need substantially different access patterns (full-text search, large-blob streaming, immutable versioning), the parallel-interface framing weakens and the cost estimate increases. Mitigation: the MH2 `/discuss` gate that picks Shape A or Shape B verifies the interface surface against actual use cases before committing. If divergence is significant, this ADR reopens; the hybrid-feature pattern from ADR-004 commitment 4 is the first-line response (split capability + operational layers more granularly).

**User signal shows that `generate_artifact` is rarely invoked, and users primarily value step responses as work product.** If post-Phase-I telemetry shows users almost never call `generate_artifact` and instead expect their step-by-step conversation history to persist as the artifact, the user-captured-explicit model fails its premise — the capture trigger isn't being exercised. Two responses are possible: (a) Phase G UX adds friction-reducing capture affordances (auto-prompt at session end, "save this conversation" inline); (b) the auto-persist model the ADR rejected gets reopened. The first is design tuning within commitment 2; the second reopens this ADR.

**Phase I user research shows users expect auto-persist as the default.** ADR-002's §5 already names a related condition for browseable history; this ADR's analog is auto-persist. If hosted-megálos users consistently expect every output to persist without explicit capture and consistently churn over the friction of "click save to keep this," commitment 2's user-captured-explicit model is wrong for the audience and ADR-006 reopens. The right response is to reopen this ADR rather than bolt auto-persist on top of the existing commitment, because the privacy and storage-cost posture changes interact with every other surface.

## 6. Trigger conditions for revisit

- **T1 — ADR-002 reopens.** This ADR's existence resolves ADR-002's Phase G blocker; the two are cross-coupled. If ADR-002 reopens (per its own trigger conditions in §6), reopen this ADR alongside to re-examine whether the decoupling commitments still hold under whatever shape ADR-002 takes after reopening.
- **T2 — MH2 implementation reveals interface divergence.** During Phase H MH2 implementation, if the `ArtifactStore` interface turns out to require a substantively different shape from `SessionStore` (per §5 first condition), reopen to either accept divergence (and document it) or restructure (per ADR-004's hybrid-feature pattern).
- **T3 — Post-Phase-I user research shows auto-persist demand.** If hosted-megálos users consistently expect auto-persist of step responses and consistently churn over user-captured-explicit friction, reopen commitment 2.
- **T4 — Storage cost in paid tier exceeds projection.** The user-captured-explicit model bounds storage cost by user-explicit action; if in practice users capture so prolifically that the (O) operational cost outpaces revenue, reopen commitment 6 (the ceiling) and Phase I pricing.
- **T5 — ADR-004 yearly audit surfaces drift.** Per ADR-004 §4, the yearly audit catches feature-mapping drift. If artifact-side features have crept across the (C)/(O) line (e.g., a feature originally (C) that grew operational tooling around it), reopen commitment 3 and amend §3 of this ADR.

## 7. References

- vision-v6 §3.2 (megálos run mode + configure mode definitions; the artifact-retention question lives here).
- vision-v6 §6.5 (Phase G + Phase I tight coupling — relevant because pre-Phase-I behavior is part of this ADR).
- vision-v6 §6.6 (OSS scope: runtime, Library, mikrós, UI source open; operational layer closed — applied to artifact surface here).
- vision-v6 §9 Q3 (pricing model — artifact retention TTL is a Phase I `/discuss` deliverable consuming this ADR).
- ADR-001 (`001-workflow-versioning.md`) — for tone, structure, and the workflow-fingerprint contract (the artifact store lives alongside the session store in the same database; the fingerprint pattern is precedent).
- ADR-002 (`002-run-mode-session-persistence.md`) — the ADR this resolves the Phase G blocker for; commitment 4 specifically.
- ADR-003 (`003-phase-j-shipping-decision.md`) — same elevation-of-Q4 frame applies; configure-mode features that produce artifacts (if Phase J reopens) consume the same `ArtifactStore`.
- ADR-004 (`004-paid-vs-self-host-value-asymmetry.md`) — the (C)/(O)/(B) framework applied here; §3 Group 1 (session storage) is the precedent for the artifact-storage mapping this ADR adds.
- ADR-005 (`005-library-entry-versioning-ux.md`) — the version-binding log is itself an artifact-shaped object; commitment 4 of ADR-005 ((C) emission, (O) audit retention) parallels this ADR's commitment 3.
- Phase H roadmap (`../vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`) — MH2 is the structural template for `ArtifactStore`'s interface + adapter pattern.
- Phase G roadmap scoping (`../vision/2026-04-27-phase-g-roadmap-scoping.md`) — the (P) classification that produced this ADR's investigation.

---

*End of ADR-006. This ADR's commitments hold conditional on the `ArtifactStore` interface remaining structurally parallel to `SessionStore` and on the user-captured-explicit model matching observed user behavior. If MH2 implementation surfaces interface divergence, or post-Phase-I telemetry surfaces auto-persist demand, this ADR is reopened, not patched.*
