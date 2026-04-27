# ADR-001 — Workflow Versioning Stance

**Status:** Accepted
**Canonicalisation:** load-then-canonical-JSON (see *Mechanism → Fingerprint*)
**Date:** 2026-04-22
**Deciders:** Diego Marono
**Supersedes:** —

---

## Context

A session created via `start_workflow` stores its workflow reference as a
plain string (`sessions.workflow_type`) — the workflow's `name` field.
The in-memory workflow dict is populated once, at `create_app()` time,
from a glob over the configured workflow directory; no reload path
exists. Every session-touching tool resolves its workflow by looking up
that name in the closed-over dict at request time.

The consequence is that a workflow YAML can mutate under a live session
in ways the runtime does not detect: step renames, insertions,
deletions, directive or schema rewrites, branch-target edits, `call:`
target shuffles. A companion discovery report
([`docs/discovery/workflow-versioning-current-behavior.md`](../discovery/workflow-versioning-current-behavior.md))
characterises seven concrete scenarios and finds that the runtime's
current handling is inconsistent — ranging from typed errors
(`schema_violation` in `get_guidelines`) to silent degradation
(`current_step: None, progress: "unknown"` in `get_state`) to a
well-shaped empty artifact returned as "success" (`generate_artifact`
when the final step was renamed).

The public deployment today masks the problem: the SQLite store lives
on container-local filesystem (see `megalos_server/db.py:DEFAULT_DB_PATH`),
and container redeploys wipe the store wholesale. The scenarios are
reachable only when (a) the session store persists across a process
restart, and (b) a YAML edit has landed between the two lifetimes —
i.e., enterprise self-hosted deployments with a mounted volume, or
local iteration with the default path. Public deployment is not the
load-bearing case.

This ADR picks the stance the runtime takes when a workflow has
mutated under a live session.

## Decision

**Strict detection with a typed error. The server fingerprints each
workflow at session-start time, re-fingerprints on every
session-touching tool call, and returns a typed `workflow_changed`
envelope when the fingerprints disagree. The affected session is
terminal — no automatic snapshot, no migration, no repair path. The
client restarts.**

## Mechanism

### Fingerprint

- Fingerprint = `sha256(canonical_bytes)` where
  `canonical_bytes = json.dumps(yaml.safe_load(raw_yaml), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")`.
- The load-then-canonical-JSON approach reduces the YAML to its parsed
  data structure before hashing, which sidesteps every YAML formatting
  quirk (comments, quote style, flow vs. block, anchors, line
  endings): two YAML files that parse to the same Python object
  produce identical fingerprints; two files that parse differently
  produce different ones.
- Deliberate trade-off: a comment-only edit does not trigger
  `workflow_changed`, because comments do not affect runtime
  behaviour. Editing a directive template, a gate list, a step id, or
  any other runtime-significant field does trigger, because those
  fields survive `yaml.safe_load` into the parsed object.
- `schema_version` participates by construction because it is a field
  in the parsed object; a `schema_version` bump therefore produces a
  different fingerprint even if downstream content is identical. This
  is deliberate — see *Non-goals* on migration semantics.
- Held alongside the workflow dict in memory; computed once per
  `create_app()` invocation, not per request.

### Session storage

- New column: `sessions.workflow_fingerprint TEXT NOT NULL`.
- Populated by `state.create_session` from the in-memory fingerprint
  at the moment the session is created. Immutable for the session's
  lifetime.
- Child sessions spawned via `enter_sub_workflow` or `push_flow`
  capture their own fingerprint at spawn time, against whichever
  child workflow is in memory at that moment. Parent and child
  fingerprints are independent: a child-workflow edit between
  parent-start and child-spawn surfaces as a fresh mismatch at spawn
  time rather than being invisibly accepted.
- Migrations: existing rows in an already-populated database are
  backfilled with the sentinel `"pre-versioning"`. On first
  `_resolve_session` for such a row, the fingerprint mismatch fires
  exactly once, moving the session to the `workflow_changed` terminal
  state. That is the correct behaviour — pre-versioning sessions
  carry no version-correctness guarantee.

### Re-check point

- Planted in `tools._resolve_session` — the single funnel every
  session-touching tool already routes through (`get_state`,
  `get_guidelines`, `submit_step`, `revise_step`,
  `enter_sub_workflow`, `push_flow`, `pop_flow`,
  `generate_artifact`).
- `delete_session` bypasses the re-check deliberately: an operator
  deleting a stuck session must not be blocked by the same condition
  that made it stuck. **Invariant:** `delete_session` must remain the
  sole recovery path for `workflow_changed` sessions, and therefore
  must not route through `_resolve_session`. Future refactors of the
  session-touching tool surface must preserve this property —
  otherwise a mutated session becomes undeletable and the only
  recovery is manual DB surgery.
- `list_sessions` does not re-check: it is a pure enumeration and does
  not resolve step-level content. It surfaces the mismatch via the
  terminal-state annotation (below).

### Terminal state

- New `current_step` sentinel: `__workflow_changed__` (mirrors the
  existing `__complete__` convention).
- When `_resolve_session` detects a fingerprint mismatch, it writes
  `current_step = __workflow_changed__` and returns the
  `workflow_changed` envelope. Subsequent calls against the same
  session re-observe the sentinel and return the same envelope without
  re-hashing.
- `list_sessions` reports these rows with `status: "workflow_changed"`
  alongside the existing `active` and `completed` statuses, so
  operators can answer "what did the last deploy kill?" without
  forensic DB surgery.
- `delete_session` is the only way out.

### Contract split: `workflow_changed` vs `workflow_not_loaded`

The re-check funnel produces `workflow_changed` for one specific
condition: the workflow under the session's `workflow_type` is still
loaded but its content fingerprint has changed since session start.
The adjacent case — the workflow is no longer loaded at all (file
deleted, renamed, or never registered) — is handled by the
pre-existing `workflow_not_loaded` envelope, which this ADR
deliberately does not touch. The split:

- `workflow_changed` = same name, different content.
- `workflow_not_loaded` = name disappearance.

Two envelopes, two conditions, no overlap. A session whose workflow
YAML is deleted between start and next call routes through the
existing `workflow_not_loaded` path without involving the fingerprint
re-check. Sessions whose workflow is rewritten under the same name
route through `workflow_changed`. Clients that distinguish the two
error codes can tell renames from content edits without additional
diagnostic keys.

### Envelope shape

```json
{
  "status": "error",
  "error": "workflow_changed",
  "message": "Workflow 'research' has changed since this session was started. The session is terminal; start a new one.",
  "session_fingerprint": "a1b2c3d4e5f6",
  "workflow_type": "research",
  "previous_fingerprint": "11223344...",
  "current_fingerprint": "aabbccdd..."
}
```

The four diagnostic keys — `session_fingerprint`, `workflow_type`,
`previous_fingerprint`, `current_fingerprint` — are the minimum
sufficient surface for an operator to locate the file on disk, confirm
it is the workflow they think it is, and correlate against the session
log without access to the raw `session_id` capability token.

### Test coverage

Every scenario in the discovery report gets a test asserting the
envelope is produced, the session lands in `__workflow_changed__`, and
no tool returns silently-degraded state. Explicit additions:

- A session with checkpointed `intermediate_artifacts` plus a
  post-start YAML mutation: must return `workflow_changed`, not stale
  `artifact_checkpoints`.
- A session at `__complete__` whose workflow was then mutated:
  `generate_artifact` must return `workflow_changed` rather than a
  well-shaped empty artifact.
- A call-frame parent whose child-workflow YAML was mutated:
  `enter_sub_workflow` and all child-side tools must return
  `workflow_changed` for the child; parent's own fingerprint check is
  independent.

## Alternatives considered

### A — Snapshot at start

Session stores the workflow content (or a content hash plus an
immutable registry entry) at start. Server uses the snapshotted
version for that session's lifetime, regardless of what the YAML on
disk says later.

**Rejected because:** introduces a new persisted artifact shape
(per-session YAML blob, or a session-keyed registry row) that the
runtime has no precedent for, and answers a question — "how do two
concurrent sessions on the same `workflow_type` relate when the YAML
has changed between them?" — that no user has asked. The storage cost
grows with the session cap. No migration seam is any cheaper to
design against snapshots than against fingerprints; the snapshot is a
strict superset of the fingerprint and we can add it later if needed.

### B — Content-addressable workflows

Workflows registered by content hash; sessions reference by hash.
Server keeps a registry of every hash ever loaded.

**Rejected because:** the design's real cost is not schema — it is the
registry-lifetime policy. When does an old hash age out? What does
`list_workflows` report during a staged rollout? How does the operator
intentionally evict a version? These are questions with genuine
user-visible behaviour, and v0.x has no signal to answer them. The
architecture fits a product direction — parallel-version visibility,
staged rollouts, cohort-based deployment — that megálos has not
committed to.

Notably: the fingerprint column installed by this ADR is the natural
join key if B is later justified by user signal. Adding B on top of C
is a `workflows_registry` table with `(fingerprint, name, yaml,
first_seen, last_used, active_session_count)` and a session-side
change that is cosmetic. Deferring B costs us nothing; deferring the
rest of the stance costs us silent drift in every new composition
feature.

## Consequences

**For the author.** Editing a workflow YAML on a host with persisted
sessions ends those sessions loudly. The failure mode is legible — the
client sees a typed error naming the workflow and both fingerprints —
not a wrong artifact or a stuck-without-explanation session.

**For the operator.** `list_sessions` gains a third status.
`workflow_changed` rows accumulate until pruned. The operational
discipline that scales is "drain sessions before shipping YAML edits,
or accept that in-flight sessions end." There is no middle ground the
runtime enforces.

**For the client.** One new error code to recognise. The recovery is
always the same: `start_workflow` again.

**For the runtime.** A single detection site consolidates the
inconsistent step-resolution handling the discovery report
characterised. `get_state`, `submit_step`, and `generate_artifact`
stop degrading silently because the `_resolve_session` check short-
circuits before any step-resolution code runs.

**For forward compatibility.** The fingerprint column is the lookup
key for both A and B. If user signal later justifies either — staged
rollouts, cross-deploy session migration, parallel-version cohorts —
this ADR's installed surface is the point of departure, not the thing
that has to be torn out.

## Non-goals

1. **Today's public deployment is not in scope.** The SQLite store on
   container-local filesystem masks every scenario under routine
   redeploy. This ADR is load-bearing for self-hosted deployments with
   persistent volumes and for local iteration; it is not load-bearing
   for the current public deploy shape.
2. **No schema-version compatibility matrix.** `schema_version`
   participates in the fingerprint by construction (it is a field in
   the canonicalised YAML). A future migration seam that tolerates
   same-major-version edits would live in a separate axis; introducing
   it now in the absence of a user asking for cross-version migration
   would be speculative design.
3. **No migration semantics.** A mutated session is terminal. There
   is no re-keying, no step-map rewriting, no "advance past the
   renamed step" heuristic. The contract is: restart.
4. **No parallel-version visibility.** `list_workflows` reports one
   entry per `name`, matching the current in-memory dict. Two
   concurrent versions of the same `workflow_type` are not
   expressible. Registry-lifetime, eviction, and GC of old versions
   are explicitly deferred.

## References

- [`docs/discovery/workflow-versioning-current-behavior.md`](../discovery/workflow-versioning-current-behavior.md)
  — Phase 1 discovery report. Seven-scenario taxonomy, deployment-model findings, behavioural patterns.
- `megalos_server/state.py` — session persistence.
- `megalos_server/__init__.py:create_app` — workflow dict population.
- `megalos_server/tools.py:_resolve_session` — single re-check funnel.
