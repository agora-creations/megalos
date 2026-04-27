# ADR-005 — Library entry versioning UX

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-26-megalos-vision-v6.md`](../vision/2026-04-26-megalos-vision-v6.md)
**Resolves:** vision-v6 §9 Q10 (Library entry versioning visible to the user)
**Related:** ADR-001 (workflow versioning, `docs/adr/001-workflow-versioning.md` — pins within-session versioning, which this ADR's cross-session reasoning rests on); ADR-002 (run-mode session persistence, `docs/adr/002-run-mode-session-persistence.md` — the session-store interface this ADR extends with per-user entry-version binding); ADR-004 (paid-vs-self-host value asymmetry, `docs/adr/004-paid-vs-self-host-value-asymmetry.md` — the (C)/(O)/(B) framework this ADR applies); Phase H roadmap MH2 (`SessionStore` interface).

---

## 1. Context

Vision-v6 §3.1 names Library entries as the curated catalog: "Each entry is a single domain repository — `megalos-writing`, `megalos-analysis`, `megalos-professional`, plus future additions — bundling related workflows behind one MCP server with a single deploy story." Curation is closed at launch and opens with mikrós-driven scale; each entry ships only after the four-skill mikrós ladder has been walked end-to-end and after independent verification against a real LLM has confirmed workflow completion against spec.

That curation discipline implies deliberate, tested releases — but releases happen. A user who picks an entry today and returns next week may find that the curator has shipped a new tagged version. Workflow contents may have been improved, the workflow set may have changed (additions or removals), the schema version may have been bumped, the runtime version requirement may have moved. v6 §9 Q10 named the strategic question: what does the user experience when an entry updates upstream — silent migration, opt-in upgrade, or version pinning?

ADR-001 already pins the within-session answer: at session create time, the workflow's canonical fingerprint is snapshotted; mid-session changes to the underlying YAML produce a terminal `workflow_changed` envelope. So within a session, the workflow is pinned by construction. Q10 is the *cross-session* question: when user U starts a new session against entry E and E has been updated since U's last session, what does U experience?

Granularity note: "Library entry version" most naturally means the curator's tagged release of the entry's domain repo (e.g., `megalos-writing v0.6.0`). The /discuss treats "entry was updated" as "curator shipped a new tagged release"; concrete deployment-model questions (multiple versions deployed in parallel? rolling upgrade?) are Phase G/I scoping work, not Q10's strategic answer.

ADR-004's framework (the (C)/(O)/(B) categorization for paid-vs-self-host value asymmetry) applies as the second lens. The versioning UX *behavior* must be the same default both tiers — that's a (C) Capability commitment under v6 §6.6's OSS scope. *Operational tooling around it* (managed roll-outs, scheduled upgrade windows, multi-version hosting infrastructure, audit-trail retention, version-history archive) is (O) Operational layer — paid runs it operationally, self-host operates equivalent themselves. The Q10 /discuss focused on the (C) default behavior; (O) follow-on tooling is Phase I scoping.

A focused /discuss session of 2026-04-27 walked the three named positions plus a hybrid against six criteria, anchored against five user archetypes, and identified position (b) — opt-in upgrade with account-bound entry version, plus a narrow critical-fix carve-out — as the leading candidate. This ADR encodes that /discuss's outputs.

## 2. Decision

Six commitments. They hold together; weakening any one weakens the others.

**1. Cross-session entry version is account-bound.** A user's account remembers the last-used Library entry version per entry. New sessions resolve to that version unless the user takes action to change it. The binding is per-(user, entry) — a user can be on different versions of different entries simultaneously.

**2. New-version prompt at session start.** When a session against entry E starts and V_current(E) > V_user(E), the UI surfaces a non-blocking "newer version available" prompt with [Upgrade] / [Stay on V_user] options. **Default action: "Stay on V_user"** — no surprise behavior change without an explicit user click. The prompt is informational by default; it does not block session start.

**3. Critical-fix carve-out for auto-migration.** A narrowly-scoped category of updates auto-migrates without prompt: security fixes, correctness regressions where the prior version produces demonstrably wrong outputs, schema-incompatibility resolutions where the prior version cannot run against the current runtime. The curator marks the release as critical at publication time; the runtime honors the marker. Operator commitment: use the marker sparingly. Abuse erodes user trust in the (b) default and converts the product to effective (a) silent migration. The boundary discipline is hard but defensible (CVE-class fixes only) and is itself a curator-side ADR-005 commitment, not a runtime decision.

**4. Version-binding log is a first-class feature.** Each session records which version was active at session start. Users (and self-host operators) can review the log per their account / per their deployment. Log emission is **(C) Capability** under ADR-004 — lives in the runtime, both tiers emit identically. Long-term retention, audit-export tooling, and per-user history UI are **(O) Operational layer** — paid runs the audit operationally, self-host operates equivalent against the same emission interface.

**5. No multi-version parallel hosting commitment for paid at v1.** Paid hosts the latest version of each entry, plus the Nth-most-recent versions users are still bound to (specific N is Phase G/I scoping). The "indefinite hosting of every historical version" mode is not committed; users on stale versions may eventually be force-migrated with notice. This bounds the operational cost of (b) on the paid side and prevents the framework from accreting a multi-version hosting commitment that grows unboundedly with curator iteration cadence.

**6. Self-host pins by deployment.** Self-host operators control their own deployment cadence; "version" for self-host is "whatever the operator deployed." The cross-session prompt logic still runs in self-host — users see "newer is available upstream" — but the operator decides when to update the deployment. This is the architectural-vs-code self-host equivalence pattern from ADR-004 commitment 5: paid manages multi-version hosting operationally; self-host manages it by deployment cadence. Same default behavior; different operational answer.

## 3. Implementation sequencing

Three forward-looking sequencing commitments, recorded so they bind future work explicitly rather than being left for future authors to derive.

**Phase G UX work designs the prompt and version-display surface.** Phase G's `/discuss` gate must scope: the "newer version available" prompt copy and placement, the version-display surface (where "I'm on V_user" appears in the chat UI), the upgrade flow (one-click, confirmation modal, etc.), the version-binding log UI for users to review their own history. Phase G `/discuss` adopts these as launch-time commitments alongside ADR-002's session-resumption affordance and ADR-003's configure-mode-naive design + analytics instrumentation.

**Phase H session-store schema accommodates per-user entry-version binding.** The MH2 `/discuss` gate (per the existing Phase H roadmap) was already required to verify the `SessionStore` interface against ADR-002's commitments. ADR-005 adds a binding requirement: per-(user, entry) version binding must be storable, lookupable, and updatable as a first-class data model. Whether this lives in the same schema as session step-state or in a separate account-level table is a Phase H implementation detail; the requirement is that the model exists.

**Curator discipline for the critical-fix marker.** A standing operator commitment: the critical-fix marker (commitment 3) is a power that requires restraint. The boundary is CVE-class fixes, demonstrably-wrong-output regressions, schema-incompatibility resolutions — not "we shipped a better prompt and want everyone to see it." Curator decisions to mark a release as critical sit alongside Library curation decisions (per v6 §3.1) and inherit the same operator-discipline weight. If the discipline lapses, ADR-005 reopens.

ADR-002's §3 framed implementation sequencing across the Phase G → Phase I window because ADR-002 commits to building. ADR-005's §3 is similar in shape: it commits to UX surfaces (Phase G) and schema extensions (Phase H) plus an ongoing operator discipline (curator restraint).

## 4. Consequences

**What this commits megálos to.**

- Phase G UX work for the version-prompt surface, version-display surface, upgrade flow, and version-binding log UI. Phase G `/discuss` adopts these.
- Phase H MH2 session-store schema accommodates per-user entry-version binding. Verified at MH2 `/discuss` alongside ADR-002's requirements.
- Library entry version becomes a first-class concept — exposed in UI, logged in session metadata, persisted in account binding. Not just an internal release tag.
- Curator discipline: critical-fix marker (commitment 3) is a power requiring operator restraint. Sits in the same discipline register as v6 §3.1's curation quality bar.
- Phase I scoping: the version-binding log's audit-export tooling is (O) per ADR-004 — Phase I scaffolding includes it as a paid-tier operational feature.

**What this forecloses.**

- Silent migration as the default (except the narrow critical-fix carve-out per commitment 3).
- Pinning-by-default. Users don't pre-pick versions; binding is a side effect of first use.
- Full position (c) version-pinning UI complexity at v1. May arrive later if post-launch signal demands; T1/T3 in §6 are the natural reopen paths.
- Indefinite multi-version parallel hosting on paid (per commitment 5). Operational cost is bounded; users on stale versions may be force-migrated with notice.
- A "you can run any historical version forever" claim in marketing. Paid commits to the latest plus the Nth-most-recent; self-host commits to whatever they deploy.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**Library curators ship far more often than v6 §3.1's deliberate-release discipline implies.** If mikrós-driven authoring scale produces curator iteration cadences in the dozens per year per entry, prompt fatigue from constant "upgrade available" nudges drives users toward (i) auto-accepting (effectively becoming silent migration), (ii) ignoring everything (running far-behind versions), or (iii) demanding pinning (push toward position (c) or (d)). The (b) default rests on curators shipping deliberately. If they don't, the framework needs revision toward (d) — add a per-user "always upgrade" / "never auto-prompt" toggle as opt-in evolution.

**The critical-fix marker is abused or never used.** If abused (curator marks every release as critical), users lose trust in (b)'s default and the carve-out becomes effective auto-migration. If never used, the carve-out doesn't earn its complexity and the operator should accept that some users will run vulnerable versions until they opt to upgrade. Either failure mode warrants reopening commitment 3.

**Compliance-sensitive enterprise self-hosters bounce.** If self-host enterprise users find that ADR-005's (b) default doesn't ship enough version-discipline UI by default — they need explicit pinning, version-locking, multi-environment version coordination — and they bounce as a segment, the right response is to reopen toward (c)-for-self-host or to add an admin-toggled pinning mode for self-host deployments. (b)'s default holds for the casual / SMB / teacher / freelancer segments; if it fails enterprise self-host as a whole segment, the framework needs a paid-vs-self-host split that ADR-004's (C) commitment doesn't currently allow.

## 6. Trigger conditions for revisit

- **T1 — Phase G post-launch prompt-fatigue signal.** Measurements show >50% of users ignore upgrade prompts after first month of Phase G + Phase I operation. Reopen toward hybrid (d) — add per-user "always upgrade" / "never auto-prompt, I'll pin manually" toggles as opt-in evolution of (b).
- **T2 — Library cadence outpaces curator discipline.** Quarterly review shows >12 tagged releases per entry per year. May indicate v6 §3.1 curation discipline isn't holding; revisit (b)'s assumption about deliberate releases.
- **T3 — Self-host enterprise audit-trail complaint becomes dominant for that segment.** Reopen with (c)-for-self-host or admin-toggled-pinning branch. May require an ADR-004 amendment to allow paid-vs-self-host behavioral split (currently ADR-004 commits to same (C) default both tiers).
- **T4 — Library opens to third-party submissions** (per v6 §3.1 mikrós-driven scale opening to third-party contributions). Curator discipline becomes harder to enforce uniformly; (b)'s assumption about deliberate releases weakens; may need per-entry curator-discipline metadata or a stricter default for less-vetted entries.
- **T5 — ADR-001 reopens** (per its own conditions). Within-session pinning is the foundation of cross-session reasoning here; reopening one would require reopening Q10 alongside.

## 7. References

- vision-v6 §3.1 (Library curation discipline that this ADR's (b) default rests on).
- vision-v6 §6.1 (v1 Library scale of 5–10 domain repos — bounds operational cost of commitment 5).
- vision-v6 §6.6 (OSS scope: runtime, Library, mikrós, UI source open; operational layer closed).
- vision-v6 §9 Q10 (the question this ADR resolves; §9 Q10's prose now points at this ADR per the amendment recorded alongside this commit).
- ADR-001 (`docs/adr/001-workflow-versioning.md`) — within-session workflow fingerprint pinning; foundation for cross-session reasoning.
- ADR-002 (`docs/adr/002-run-mode-session-persistence.md`) — `SessionStore` interface that ADR-005 commitment 4 extends with per-user entry-version binding requirements.
- ADR-004 (`docs/adr/004-paid-vs-self-host-value-asymmetry.md`) — (C)/(O)/(B) framework applied here: versioning UX behavior is (C), audit-export tooling is (O), self-host's "pin by deployment" is the architectural-vs-code self-host equivalence pattern from commitment 5.
- Phase H roadmap (`docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`) — MH2 session-store interface accommodates per-user entry-version binding.

---

*End of ADR-005. This ADR's commitments hold conditional on Library curators maintaining the discipline established in v6 §3.1 (deliberate, tested releases) and the curator-side critical-fix-marker discipline (commitment 3, used sparingly). If either lapses, the (b) default loses its load-bearing premise — prompt fatigue from over-frequent releases or trust collapse from over-marked releases both reopen this ADR.*
