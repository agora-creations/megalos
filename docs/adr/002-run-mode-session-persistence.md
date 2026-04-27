# ADR-002 — Run-mode session persistence in megálos

**Status:** Accepted, 2026-04-26
**Supersedes:** none
**Governing vision:** [`2026-04-26-megalos-vision-v6.md`](../vision/2026-04-26-megalos-vision-v6.md)
**Resolves:** vision-v6 §9 Q9 (run-mode session persistence in paid megálos)
**Related:** ADR-001 (workflow versioning, `docs/adr/001-workflow-versioning.md`); Phase H roadmap MH2 and MH5 (`docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`).

---

## 1. Context

Vision-v6 §3.2 commits megálos to two modes inside one UI: run mode (the user picks a Library entry, BYOKs an LLM API key, and drives workflows interactively) and configure mode (the embedded agent walks a non-technical user through bounded modifications of a Library entry). v6 §9 Q9 named run-mode session persistence as UNDECIDED at v6 promotion: if a user starts a workflow, leaves, and returns, what is persisted — session state, conversation history, the picked-and-configured Library entry, none, all? The operator did not have a working position on this question at v6 promotion.

The question is not cosmetic. It binds three downstream surfaces. Phase H MH2 (`SessionStore` interface plus Postgres adapter) needs to know whether the backend is storing only step-state or also conversation history, whether sessions have a TTL, whether the schema must accommodate user-account binding. Phase I (hosted megálos with billing) needs to know whether "session" is a billing-meaningful unit. Phase G's run-mode UI needs to know what "leave and come back" looks like — silent resumption, an in-product affordance, an account-bound history list, nothing at all.

The OAuth feasibility investigation completed 2026-04-26 (`docs/discovery/2026-04-26-oauth-feasibility-investigation.md`) removed the consumer-subscription onramp from v6 commitments (§6.4 amendment) and elevated v6 §9 Q4 (paid-vs-self-host value asymmetry) to higher priority. The session-persistence question is now load-bearing for the paid claim: with no consumer-subscription onramp to anchor the paid pitch, the operational-maturity story has to carry more weight, and "your in-flight work survives a closed tab" is one of the more concrete operational guarantees a hosted product can make.

This ADR resolves §9 Q9 in the form the operator and Claude reached during the 2026-04-26 `/discuss` session, with three operator-approved tightenings applied during ADR drafting.

## 2. Decision

Four commitments. They hold together; weakening any one weakens the others.

**1. Paid megálos commits to Level 1 persistence: account-bound, in-flight resumption, no browseable history.** A session in paid megálos has a 7-day TTL from last activity. Within that window, the user can return — from a different tab, a different device, after a closed-tab-and-reopened-browser — and resume the session at the step it was at, with the prior conversation history visible up to that step. Sessions are bound to the user's megálos account; binding requires Phase I infrastructure (see §3 below). Resumption surfaces as a single-click affordance per Library entry the user has an in-flight session against — not a ChatGPT-shaped sidebar of every session the user has ever run. After the 7-day TTL elapses, the session is garbage-collected. Artifacts produced by the session are subject to a separate retention regime (see commitment 4); session expiry does not delete the user's work product.

**2. Self-host runs the same code path with admin-tunable TTL.** Self-host megálos uses the same `SessionStore` implementation as paid megálos. Default TTL is 7 days, identical to paid. Self-host admins can tune `MEGALOS_SESSION_TTL` from 24 hours (a defensible floor for shared-tenant deployments where session lifetime is a security surface) up to indefinite (a defensible ceiling for solo or trusted-team deployments where there is no operational reason to expire sessions at all). Self-host admins set bounds; users do not. Paid megálos uses operator-set bounds; the user-facing TTL is fixed at 7 days at v6 ship.

The TTL parity at defaults is deliberate. Paid megálos's differentiator over self-host is the operational layer around session storage — managed Postgres deployment, backups, observability, deletion-on-request handling, GDPR export tooling, multi-replica session-state replication — not the TTL value itself. A paid product whose value-add is "we set `MEGALOS_SESSION_TTL=7d` for you" is not a defensible operational maturity pitch; a self-host admin reading the docs would replicate it in five seconds. By keeping TTL parity, the paid claim rests on operational stack maturity, which is genuinely hard to replicate. This also aligns with v6 §6.6's commitment that the OSS code (runtime, Library, mikrós, UI source) covers capability and the closed operational layer covers maturity. TTL is capability; operational stack is maturity. The split sits cleanly on this line.

This is the answer v6 §9 Q4 ("self-host vs paid: explicit value asymmetry") demands for the session-persistence slice of the surface. The general Q4 question remains open across all paid features; this ADR pins it for one feature.

**3. Session is not a billing-meaningful unit at v6 ship.** Phase I's pricing model (still open per v6 §9 Q3) does not bill per session, per session-day, or per active-session count. Session is an operational unit — the thing the `SessionStore` indexes — not a metered consumption unit. The user pays for hosted megálos (whatever shape the Phase I pricing decision takes); they do not pay more for keeping a session open longer or pay less for short sessions. This forecloses a category of pricing model (per-session metering) that would have been technically tractable but creates incentives the product does not want — incentives to abandon sessions early, to avoid TTL extensions, to game session boundaries.

**4. Artifact retention is decoupled from session retention.** Workflow outputs that the user values as work product — committed artifacts, files surfaced for download, structured outputs the user has explicitly captured — persist beyond the 7-day session TTL. The exact retention regime for artifacts is a Phase G `/discuss` deliverable; what is committed here is the decoupling: a user whose session TTL elapses has not lost their work, only the ability to resume the conversation that produced it.

**This decoupling is a Phase G blocker, not a follow-up.** If artifact retention cannot be cleanly decoupled from session retention in Phase G's design, this ADR's Level 1 commitment collapses — Level 1 becomes indistinguishable from Level 0 (no persistence) the moment the TTL expires for any user who values their output. Phase G's `/discuss` must confirm that the decoupling is buildable at acceptable cost before this ADR's commitments hold. If Phase G surfaces that the decoupling is substantially more expensive than expected, this ADR is reopened, not patched. That is the explicit dependency.

## 3. Implementation sequencing

Paid megálos cannot deliver Level 1 until Phase I ships. Account-bound resumption requires an account system; the account system is Phase I infrastructure. The honest framing is that paid megálos has a transition story.

**During the Phase G → Phase I window**, paid megálos run mode operates at effective Level 0. There is no account binding because there is no account system. The Phase G chat UI exposes a "Resume in this tab" affordance using browser-local `session_id` storage where possible, so a user who keeps the same tab open (or returns to the browser session before cookies expire) can resume. A closed tab plus cleared cookies makes the session unreachable. **This is the initial paid-product state, not a regression.** It is what shipping a UI before shipping accounts looks like.

**At Phase I delivery**, account binding lights up. New sessions from Phase I onward are account-bound and resumable per this ADR's §2 commitment 1. Existing in-flight sessions from before Phase I do not retroactively bind to accounts — there is no migration path because there is no prior account to bind them to, and by the time Phase I ships any pre-Phase-I session will have been GC'd by its 7-day TTL anyway. Phase I does not need a session-migration story.

**The Phase G UI must signal this transition.** A pre-Phase-I user should see a clear in-product affordance that resumption is coming with the managed-tier launch — not "this feature is broken" but "this feature ships with billing." The exact copy and placement is a Phase G design deliverable; the requirement that it exist is committed here so that Phase G's UI does not silently ship in a state where Level 1 persistence appears to be missing rather than pending.

Self-host gets the full `SessionStore` path the day MH2 ships. Self-host does not need an account system to bind sessions because self-host already has identity propagation via MH5's header middleware (`X-Forwarded-User`); the upstream reverse proxy is the account system. A self-host deployment running MH2 + MH5 has Level 1 persistence end-to-end from the day MH5 ships, which precedes Phase I.

## 4. Consequences

**What this commits megálos to.**

- Phase H MH2's `SessionStore` interface must accommodate user-identity-keyed lookup, TTL with last-activity touch, conversation-history persistence (not just step-state), and an envvar-tunable TTL bound. The MH2 `/discuss` gate must verify these requirements against the interface design before MH2 S01 lands.
- Phase G's run mode must implement single-click resume per Library entry the user has an in-flight session against. The UI surface is bounded — one entry-point per Library entry the user is mid-session on, no deeper history surface.
- Phase G's `/discuss` must confirm that artifact retention can be decoupled from session retention. This is a blocker, not a follow-up, per §2 commitment 4.
- Phase I's pricing model (v6 §9 Q3) is constrained to non-per-session metering. The pricing-model `/discuss` may consider per-server-hosted, per-user, per-active-Library-entry, flat-tier, freemium-with-metered-LLM-passthrough — but not per-session. This is a real foreclosure and is named explicitly so the Phase I pricing conversation does not have to re-litigate it.
- Self-host documentation must explain that paid megálos and self-host run the same `SessionStore` code path with the same default TTL, and that the paid claim rests on the operational layer, not the persistence value itself. The README and any "why pay for hosted megálos" prose must not lean on TTL as a differentiator.

**What this forecloses.**

- A ChatGPT-shaped browseable history sidebar — every session the user has ever run, indexed by Library entry, browseable as a left-rail list. This is the user-experience model paid megálos is not building. The reasons it is not building it: it implies indefinite retention (which the 7-day TTL contradicts), it implies a privacy posture the operator does not want to commit to (every prompt the user has ever typed retained for casual browsing), and it implies a UI surface (search-across-sessions, session metadata, tagging) that is not in scope at v6 ship. Users who want this shape of history can self-host with `MEGALOS_SESSION_TTL=indefinite` and build the surface themselves; paid megálos does not.
- A consumer expectation that paid megálos is a long-term archive of past conversations. The product's persistence guarantee is "your in-flight work survives," not "your past work is browsable." Marketing copy and onboarding flows must not promise the latter.
- Per-session billing as a Phase I option, per §2 commitment 3.

## 5. What would have to be true for this to be wrong

Three conditions, named honestly because the decision is not unconditional.

**Phase G `/discuss` reveals that artifact retention cannot be cleanly decoupled from session retention.** If artifact retention turns out to require the same backend, the same indexing, and the same TTL machinery as session retention — to the point that decoupling is substantially more expensive than coupling — then commitment 4 fails and Level 1 collapses into Level 0 for any user whose work product matters to them. This ADR must be reopened, not patched, in that case. The §2 commitment 4 framing makes this dependency visible at the Phase G `/discuss` gate where the question gets answered.

**Phase I user research reveals that the missing browseable-history shape is the dominant complaint.** If hosted-megálos users consistently expect ChatGPT-shaped history and consistently churn over its absence, the foreclosure named in §4 is the wrong call. The right response is to reopen this ADR rather than bolt history on top of the Level 1 commitment, because the privacy and retention posture changes (indefinite retention, indexed prompts, search) interact with every other surface and need a coherent re-decision, not a feature addition.

**The 7-day TTL turns out to be wrong by an order of magnitude.** If real-user signal shows that median session lifetime is ~90 days (a much heavier-weight workflow shape than v6 anticipates) or ~12 hours (a much lighter conversational shape), the TTL number is mis-set and persistence semantics need to be re-tuned. This is a numerical revisit, not a structural one — it does not invalidate the ADR's shape, only the constant — but it would warrant an ADR amendment rather than a silent envvar default change.

## 6. Trigger conditions for revisit

- **Phase G `/discuss` cannot decouple artifact retention from session retention** at acceptable cost. Reopen this ADR rather than patch around it.
- **Phase I pricing-model `/discuss` surfaces a strong reason to bill per session.** The §2 commitment 3 foreclosure is load-bearing; reversing it requires this ADR to be reopened, not just a Phase I pricing decision.
- **User research after Phase I ships shows persistent demand for browseable history.** Reopen the privacy and retention posture decision; do not bolt history onto the current commitment.
- **Provider OAuth landscape shifts** (per v6 §6.4 and §9 Q2 quarterly re-check) and consumer-subscription onramp returns to v6 commitments. Shape 5's audience expands, and the persistence story for non-API-key-paying users may need different defaults than the API-key-paying audience this ADR scopes against.

## 7. References

- vision-v6 §3.2 (megálos run mode and configure mode definitions).
- vision-v6 §6.5 (Phase G/Phase I coupling).
- vision-v6 §6.6 (OSS scope and the open-content / closed-operations split).
- vision-v6 §9 Q4 (paid-vs-self-host value asymmetry — the question this ADR answers for the session-persistence slice; elevated priority per the OAuth-investigation amendment).
- vision-v6 §9 Q9 (run-mode session persistence — the question this ADR resolves; §9 Q9's prose now points at this ADR).
- vision-v6 §9 Q11 (Phase J's economic case under API-key-only — relevant because if Phase J defers, Shape 5's persistence needs change and this ADR's Shape-5-implicit assumptions may need revisiting).
- ADR-001 (`docs/adr/001-workflow-versioning.md`) — for tone, structure, and the workflow-fingerprint contract that the `SessionStore` interface inherits.
- Phase H roadmap (`docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`) — MH2 (`SessionStore` interface and Postgres adapter) and MH5 (header-middleware identity propagation, which lets self-host reach Level 1 without an account system).

---

*End of ADR-002. This ADR's commitments hold conditional on Phase G's `/discuss` confirming that artifact retention can be decoupled from session retention. If Phase G surfaces that the decoupling is substantially more expensive than expected, this ADR is reopened, not patched.*
