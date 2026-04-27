# ADR-004 — Paid vs self-host value asymmetry

**Status:** Accepted, 2026-04-27
**Supersedes:** none
**Governing vision:** [`2026-04-26-megalos-vision-v6.md`](../vision/2026-04-26-megalos-vision-v6.md)
**Resolves:** vision-v6 §9 Q4 (paid-vs-self-host value asymmetry, elevated priority post-OAuth resolution)
**Related:** ADR-001 (workflow versioning, `docs/adr/001-workflow-versioning.md`); ADR-002 (run-mode session persistence, `docs/adr/002-run-mode-session-persistence.md` — the test case for the principle this ADR generalizes); ADR-003 (Phase J shipping decision, `docs/adr/003-phase-j-shipping-decision.md` — same elevation-of-Q4 frame applies); Phase H roadmap MH4 (metrics surface) and MH5 (header-middleware identity propagation).

---

## 1. Context

Vision-v6 §6.6 commits the runtime (`megalos-server`), Library entries, mikrós skill library, and megálos's UI source as OSS in perpetuity. The operational layer — billing, auth, deployment automation, observability infrastructure, fleet management — is the operator's commercial code, not OSS. v6 §6.2 commits that "the paid claim is on operational maturity, not on capability withholding." Together these pin the principle but not the surface. v6 §9 Q4 asks: which features sit on which side of the line, and what is the standing discipline for new features added later?

The question's priority was elevated by the OAuth-investigation amendment (per v6 §9 Q4 amendment + §6.4). With the consumer-subscription onramp removed, "we handle the OAuth dance" is no longer a pillar of paid's value. Operational maturity now carries more weight as the paid pitch — making a coherent, defensible categorization more load-bearing. Paid cannot lean on a value axis that does not exist.

The question binds Phase I scoping. Phase I (the hosted-megálos managed product) cannot be scaffolded against an undefined value-asymmetry surface; the pricing-model `/discuss` (v6 §9 Q3) cannot proceed without knowing which features are billing-relevant. v6 §9 Q4 names this as "should be resolved before Phase I scaffold is drafted." This ADR is that resolution.

ADR-002 §2.2 already pinned the principle for the session-persistence slice: "Paid megálos's differentiator over self-host is the operational layer around session storage — managed Postgres deployment, backups, observability, deletion-on-request handling, GDPR export tooling, multi-replica session-state replication — not the TTL value itself." That paragraph is the model for this ADR's framework: a categorization that names operational tooling as the differentiator while preserving capability parity.

A focused /discuss session of 2026-04-27 walked the candidate feature surface, proposed three categorization axes, mapped each feature, and stress-tested the framework against under-thin paid value, over-thick paid value, boundary creep, and standard SaaS-vs-OSS competitive dynamics. This ADR encodes that /discuss's outputs.

## 2. Decision

Five commitments. They hold together; weakening any one weakens the others.

**1. Principle.** Paid megálos's value over self-host is operational maturity, not capability withholding. Capability parity is preserved across tiers; the differentiator is the operational layer that paid runs on the user's behalf. This generalizes ADR-002 §2.2's session-persistence-slice principle to the full feature surface.

**2. Categorization framework.** Three categories:
- **(C) Capability — OSS, identical in both tiers.** The code lives in the OSS surface (`megalos-server`, megálos UI source, mikrós, Library). Self-host runs it; paid runs it on the user's behalf. Functionality is the same.
- **(O) Operational layer — paid-only.** The code lives in the operator's closed-source commercial tooling. Self-host can build equivalent functionality themselves with effort, but does not get the operator's code. The self-host equivalent may be *architectural* rather than re-implementing the feature (see commitment 5).
- **(B) Bound by billing — paid-only by definition.** Features that exist only because there is a paid product. Self-host has no analog because self-host has no billing relationship.

**3. Boundary discipline.** Default new features to (C). Categorize as (O) only if the feature requires sustained operational investment to maintain quality, not just code. Categorize as (B) only if the feature is intrinsically billing-related. The discipline test: if a feature can be implemented with under one person-week of additional code and no ongoing operational investment, it should be (C), not (O). If it requires sustained operational investment to maintain quality, (O) is defensible.

**4. Hybrid-feature pattern.** Many features have a capability layer (the underlying surface, OSS) and an operational layer (the tooling around the surface, paid-only). When a feature has both shapes, name them separately rather than categorizing the bundle. Worked examples (from §3 below): session retention duration is **(C)** while automated long-term backup with retrieval guarantees is **(O)**; audit-log emission is **(C)** while audit-log retention and browsing UI are **(O)**. This pattern recurs and should be the default lens for any feature that resists single-category placement.

**5. Architectural-vs-code self-host equivalence.** Some (O) features have an architectural self-host answer rather than a code re-implementation. The canonical example: paid bundles an account system; self-host's equivalent is upstream identity propagation per ADR-002 §3 / Phase H MH5 (`X-Forwarded-User` header middleware, with the upstream reverse proxy serving as the identity layer). Self-host is not "missing" the account system — it has a different architectural commitment that supplies the same functional need. This is named explicitly so future categorization decisions don't confuse "different architecture" with "withheld capability."

## 3. Initial feature mapping

The v1 reference. Phase I scaffolding references this and adds to it as Phase I scoping reveals new features. Yearly audit catches drift.

**Group 1 — Session storage and persistence** (anchored by ADR-002):

| Feature | Category | Reasoning |
|---|---|---|
| Session-store backend (interface + adapters) | **(C)** | ADR-002 commits same code path with admin-tunable TTL for self-host. |
| TTL configuration | **(C)** | ADR-002 §2.2: TTL parity at defaults; admin-tunable from 24h to indefinite. |
| Multi-replica session-state replication | **(O)** | Replication is operational tooling — managing Postgres replicas, failover, lag monitoring. |
| Session backups + point-in-time restore | **(O)** | Backup automation is operational. Self-host can configure pg_basebackup themselves. |
| GDPR export tooling | **(O)** | Paid runs the export workflow on user request; self-host writes equivalent against the same `SessionStore` interface. |
| Deletion-on-request handling | **(O)** | Same shape as GDPR export — paid runs the workflow; self-host does it themselves. |

**Group 2 — Account system and auth:**

| Feature | Category | Reasoning |
|---|---|---|
| Account binding (sign-up / sign-in / password reset) | **(O)** | Self-host equivalent is *architectural*: upstream identity propagation via Phase H MH5's `X-Forwarded-User` header middleware. Cleanest example of commitment 5. |
| SSO | **(O)** | Self-host's SSO comes from the upstream proxy. |
| Multi-tenant isolation | **(O)** | Self-host is single-tenant by default (one self-host deployment per organization). |
| Role-based access | **(O)** | Self-host enforces roles via upstream proxy ACLs. |

**Group 3 — Library entry hosting and connection:**

| Feature | Category | Reasoning |
|---|---|---|
| Library entry deployment infrastructure | **(O)** | Paid runs Library entries on managed infrastructure; self-host deploys via Phase H deployment recipes. |
| One-click connection from run mode | **(C)** | The connection logic in megálos UI is OSS. Paid pre-configures entries via the (O) deployment infra; self-host configures connection strings themselves. |
| Per-user customized-entry storage | **(C)** if Phase J ships | Schema and storage interface OSS. |
| Library entry versioning UX | *deferred* | Resolves with v6 §9 Q10 (next /discuss). Initial mapping update follows Q10 resolution. |

**Group 4 — Observability and operations:**

| Feature | Category | Reasoning |
|---|---|---|
| Metrics endpoint exposure | **(C)** | Both tiers expose the same metrics surface (per Phase H MH4). |
| Dashboards, alerting, error tracking | **(O)** | Dashboards live in the paid operational stack. Self-host scrapes the metrics endpoint into their own Grafana. |
| Auto-updates with managed roll-outs | **(O)** | Paid runs canary deploys. Self-host updates via documented upgrade procedure. |
| Backup automation | **(O)** | Same shape as session backups. |

**Group 5 — Billing and usage:**

| Feature | Category | Reasoning |
|---|---|---|
| Billing infrastructure | **(B)** | By definition. |
| Usage tracking (billing-tied) | **(B)** | The metering for billing purposes is paid-only. |
| Per-step usage logs (observability) | **(C)** | What step ran, how long, what completed — observability output that paid surfaces and self-host can also use. Hybrid pattern with billing-tied metering. |
| Invoice generation, payment processing | **(B)** | By definition. |
| Plan-tier quotas | **(B)** | By definition. |

**Group 6 — Compliance and trust:**

| Feature | Category | Reasoning |
|---|---|---|
| SOC2 / similar certifications | **(O)** | Auditors audit operational practices; paid has the practices and the audit. Self-host inherits whatever practices their operator implements. |
| Audit-log emission | **(C)** | The emission lives in `megalos-server`. Hybrid with retention/UI. |
| Audit-log retention + browsing UI | **(O)** | Paid surfaces and retains the logs operationally; self-host has the logs and configures retention themselves. |
| Data residency | **(O)** | Paid commits to specific regions; self-host runs wherever they deploy. |

**Group 7 — Rate limiting and abuse:**

| Feature | Category | Reasoning |
|---|---|---|
| Rate-limit policy enforcement | **(C)** | Code is in `megalos-server` (per `docs/rate-limits.md`). Self-host configures policy via env; paid has an operator-set policy. |
| Abuse detection / mitigation tooling | **(O)** | Detection logic and mitigation runbooks are operational. Self-host doesn't have a multi-tenant abuse problem at most scales. |

**Group 8 — Configure mode** (deferred per ADR-003; pre-categorized for T1 reopening):

| Feature | Category | Reasoning |
|---|---|---|
| Configure-mode UI surface | **(C)** | Lives in megálos UI source. |
| Per-user customized-entry storage | **(C)** | Schema and storage interface OSS. |
| Embedded mikrós-reading agent | **(C)** | The agent prompt and mikrós-consumption logic OSS. Inference is BYOK in both tiers. |

## 4. Implementation sequencing

**Phase I scaffolding references this mapping as input.** When Phase I's scaffold document is drafted (per v6 §7 Phase I, owed after Phase H MH2–MH4 land), §3's mapping is the starting point for naming what paid offers concretely. The pricing-model `/discuss` (v6 §9 Q3) consumes this same mapping when deciding what is billable. Without ADR-004's mapping pinned, Phase I scaffolding would have to derive its own categorization implicitly — leading either to drift or to re-litigating the principle mid-Phase-I.

**New features get categorized at design time.** Every new feature added between now and Phase I ship gets walked against the (C)/(O)/(B) framework before it lands. Categorization sits in the feature's design record (ADR, /discuss output, or PR description — whichever is the natural artifact for the feature). The boundary discipline (commitment 3) is the standing test.

**Yearly audit catches drift.** A standing operator discipline: at least once per year, walk the §3 mapping against the current feature set. New features that landed without explicit categorization get categorized. Existing categorizations that have shifted in practice (e.g., a feature originally (C) that grew operational tooling around it) get split into hybrid (C) + (O) per commitment 4. The audit output is an updated §3 mapping, recorded as an ADR amendment.

**Phase I marketing depends on this.** The Step-5-stress-test "paid value too thin" risk is mitigated by Phase I marketing articulating the (O) features concretely — backups every N hours, point-in-time restore, multi-replica with N-second failover, audit logs retained for N days. The mapping in §3 is the basis for those concrete claims. Phase I copy that says "fully managed!" without enumerating what "fully managed" means is the failure mode this ADR is set up to prevent.

ADR-002's §3 framed implementation sequencing across the Phase G → Phase I window because ADR-002 commits to building. This ADR's §4 is similar in shape because it commits to *categorizing* — an ongoing operator discipline rather than a one-time build, but still a real commitment with downstream gates.

## 5. Consequences

**What this commits megálos to.**

- (C) features remain OSS in perpetuity per v6 §6.6. The (C) category is the operationalization of that commitment.
- (O) features stay closed-source. The operator's investment in operational tooling is the operator's commercial moat.
- New features are categorized at design time per commitment 3; categorization is part of the feature's design record.
- Phase I scaffolding references §3's mapping as input. If Phase I scoping reveals features not yet mapped, they get categorized as part of Phase I /discuss work and added to §3 via ADR amendment.
- Yearly audit per §4 third paragraph. The first audit lands roughly 12 months after Phase I ships, not 12 months after this ADR — the operator's feature-addition cadence is bound by Phase I work, not by ADR-004 calendar date.
- Phase I marketing copy enumerates (O) features concretely (backups, replication, monitoring, etc.) rather than relying on vague "fully managed" framing.

**What this forecloses.**

- A "paid features are better" tier (paid having higher-quality versions of (C) features). If quality differentiation becomes desirable, the right move is to name the operational tooling around the feature as a separate (O) — not to fork the (C) code into a paid-only enhanced version.
- Categorizing features as (O) for differentiation reasons absent operational investment. The (O) category is reserved for genuine operational tooling; using it as a competitive moat against self-host adoption violates the principle.
- Selling (O) features as "open-source" in marketing. The OSS commitment in v6 §6.6 covers (C) and the meta-claim "you can self-host the product" — it does not cover (O), and Phase I copy must not blur that line.
- Bundling (B) billing-bound features into the OSS surface. The OSS code does not include a billing layer; that surface lives in the operator's commercial code only.

## 6. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**The friction of self-host turns out to be so high that nobody actually self-hosts at scale.** If self-host adoption is structurally <X% of total deployments (where X is the operator's own threshold for "OSS commitment is meaningful in practice"), the (C) category is too thin in practice — nominal OSS, real product lock-in via deployment friction. The framework's principle holds but the principle is hollow. Mitigation lives in Phase H discipline (deployment recipes, MH1–MH6 must keep self-host genuinely viable for Shape 3) and in periodic adoption measurement.

**Paid revenue is so thin that the (O) category isn't pulling its weight.** If Phase I revenue at 12 months post-launch is below the operator's sustainable-solo-pace threshold *and* root-cause analysis attributes the shortfall to "users don't see (O) as worth paying for," the operational-maturity claim isn't justifying the price. May indicate (O) features need more concrete articulation in marketing, or that the gap between (C) capability and (O) operational tooling is genuinely too narrow for a paid product to sit on top.

**The (C)/(O)/(B) framework genuinely doesn't fit a class of features.** A new feature ships and the categorization conversation is genuinely stuck — the feature isn't (C) (paid has something self-host doesn't), isn't (O) (it's not operational tooling), and isn't (B) (it's not billing-bound). The hybrid-feature pattern (commitment 4) is the first response: split the feature into capability + operational layers and categorize each. If that doesn't resolve, the framework needs revision, not just the feature. The yearly audit is the natural venue for surfacing this kind of structural pressure.

## 7. Trigger conditions for revisit

- **T1 — Framework breakdown.** If the categorization fits >90% of new features cleanly for the first 12 months post-Phase-I-launch, then a wave of features doesn't fit, reopen the framework. The hybrid-feature pattern (commitment 4) is the first-line response; reopening only if hybrids don't resolve the friction.
- **T2 — Self-host adoption hollow.** Self-host adoption is structurally below the operator's threshold for "OSS commitment is meaningful in practice." Reopen the principle (commitment 1) — may indicate (C) is too thin in practice and the OSS commitment needs different operationalization.
- **T3 — Paid-tier marketing failure.** Paid-tier churn analysis surfaces "couldn't tell what I was paying for" or "I thought I was getting more than just managed hosting" as a dominant complaint. Indicates the operational-maturity claim isn't being articulated; reopen Phase I marketing/positioning rather than the framework.
- **T4 — ADR-002 reopens.** The session-persistence slice was the test case for this framework; if ADR-002 reopens (per its own trigger conditions), reopen this ADR alongside to re-examine whether the principle still generalizes.
- **T5 — A new ADR generates a feature category that requires framework revision.** When future ADRs (or new feature designs) surface a feature class that needs a fourth category, reopen rather than retroactively forcing fit.

## 8. References

- vision-v6 §6.2 (paid claim is operational maturity, not capability withholding — the principle this ADR generalizes).
- vision-v6 §6.6 (OSS scope: runtime, Library, mikrós, UI source open; operational layer closed).
- vision-v6 §9 Q3 (pricing model — depends on this ADR's mapping for billable-feature identification).
- vision-v6 §9 Q4 (the question this ADR resolves; §9 Q4's prose now points at this ADR per the amendment recorded alongside this commit).
- vision-v6 §9 Q10 (Library entry versioning UX — feature mapping deferred until Q10 resolves).
- ADR-001 (`docs/adr/001-workflow-versioning.md`) — for tone and the ADR pattern.
- ADR-002 (`docs/adr/002-run-mode-session-persistence.md`) — §2.2 is the precedent for the principle; the session-persistence slice is the test case this ADR generalizes from.
- ADR-003 (`docs/adr/003-phase-j-shipping-decision.md`) — same OAuth-resolution-elevates-Q4 frame applies; Configure-mode-related (C) categorizations in §3 hold conditional on ADR-003's reopen triggers.
- Phase H roadmap (`docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`) — MH4 (metrics endpoint surface) and MH5 (header-middleware identity propagation, which makes the architectural self-host answer for account-system viable per commitment 5).

---

*End of ADR-004. This ADR's commitments hold conditional on the operator maintaining the boundary discipline (commitment 3) at design time for new features. If the discipline lapses and (O) creeps into things that are genuinely capability, the OSS commitment in v6 §6.6 erodes by feature-addition rather than by explicit decision. The yearly audit per §4 is the standing safeguard against drift.*
