# Workflow Versioning — Current Behaviour

**Status:** Phase 1 discovery report. Descriptive only. No changes proposed.
**Scope:** Characterise how the runtime behaves today when a workflow YAML is mutated between a session's creation and its next tool call. Covers the six session-mutating tools, plus `get_state`, plus `generate_artifact`, plus a confirming note on `list_sessions`.

---

## 1. What the state store persists about workflow identity

`megalos_server/state.py` persists sessions in SQLite with the following workflow-identity surface:

- `sessions.workflow_type` — the workflow's `name` field, a plain string.
- Nothing else. No content hash, no schema-version stamp, no inlined YAML, no registry-version pointer.

The column set hydrated by `_row_to_session` is `session_id, workflow_type, current_step, step_data, retry_counts, step_visit_counts, escalation, artifact_checkpoints, created_at, updated_at, called_session, parent_session_id` (see `state.py:104-109`). `step_data` stores per-step submission content keyed by the step's `id` string — again a name, not a content-addressable key. The `session_stack` companion table carries `frame_type` and `call_step_id` but likewise references the parent's step by id string only.

**Implication.** A session is pinned to a workflow *by name*. Whatever the in-memory workflow dict says that name means at the moment of a tool call is what the session sees.

## 2. When the in-memory workflow dict is populated

`megalos_server/main.py:8` calls `create_app()` at module import time. `create_app` in `megalos_server/__init__.py:47-50` globs `workflow_dir/*.yaml`, calls `load_workflow` on each, and builds a single `workflows: dict[str, dict]` indexed by the workflow's `name` field. It runs `validate_workflow_calls` across the set (rejecting unknown or cyclic `call:` targets), then passes the dict into `register_tools`. Every tool closure captures this same dict by reference.

There is no file-watcher, no mtime poll, no TTL-based reload, and no per-request re-read. The dict is populated exactly once per process lifetime. Tests mutate it via `mcp._megalos_workflows` (same object), which is the only supported mutation path — there is no public "reload" API.

**Implication.** Editing a workflow YAML in a running server has no observable effect on tool responses. The change takes effect only after a process restart that re-runs `create_app()`. This is the "caching semantic" the brief asked about.

## 3. How each session-touching tool resolves workflow + step

Every session-scoped tool funnels through `_resolve_session(session_id, workflows)` in `tools.py:297-330`:

1. Fetch the session row (`state.get_session` → `SessionNotFoundError` or dict).
2. Check caller identity against `session["owner_identity"]` (currently structural — both sides are `ANONYMOUS_IDENTITY`).
3. Look up `workflows.get(session["workflow_type"])`. If absent, return `workflow_not_loaded` with the session fingerprint.
4. Otherwise return `(session, wf)` — `wf` is whatever was loaded at startup.

From there, step resolution uses `_find_step(wf, step_id)` (`tools.py:289-294`), which linearly scans `wf["steps"]` matching on the step's `id` string. Missing steps return `(-1, None)` — and downstream code handles that sentinel inconsistently across tools (see Scenario 1).

The set of tools that run through `_resolve_session`: `get_state`, `get_guidelines`, `submit_step`, `revise_step`, `enter_sub_workflow`, `push_flow`, `pop_flow`, `generate_artifact`. `delete_session` intentionally bypasses it (it does not need the workflow object); `list_sessions` is purely a DB enumeration.

## 4. Scenario-by-scenario behaviour

Each scenario below assumes the edit has landed in the YAML on disk AND the server process has restarted (because mid-flight edits without restart are invisible — see §2). Without a restart, all seven scenarios degenerate to "no observable change." The interesting behaviour surfaces only when a restart makes the edit effective while persisted sessions survive across the restart.

### Scenario 1 — Step renamed (`id` change)

Suppose a session's `current_step` is `"old_id"` in DB, and the reloaded workflow has replaced that step with `"new_id"`.

Tool behaviour diverges by tool:

- **`get_state`:** `_find_step(wf, "old_id")` returns `(-1, None)`. The response reports `current_step: None` and `progress: "unknown"`. Does not raise. This is a **silent degradation** — the client sees a well-shaped response that happens to be useless.
- **`get_guidelines`:** Explicit `if not step: return schema_violation(...)` (`tools.py:847-852`). Returns a typed `schema_violation` error. Clean.
- **`submit_step`:** Two sub-paths.
  - If the client submits `step_id="old_id"`: the `step_id != current` check passes (both equal `"old_id"`), then `_find_step` returns `(-1, None)`, and the very next reference — `"call" in step` (line 943) — raises `TypeError` on `None`. The `_trap_errors("content")` decorator maps this to an `invalid_argument` envelope without `step_id` or `field="step"` context. **Confused error label.**
  - If the client submits `step_id="new_id"` (they refreshed their mental model): mismatches stored `current_step` → `out_of_order_submission`. Also misleading — it is not an ordering problem.
- **`revise_step`:** `target_idx, target_step = _find_step(wf, step_id)`; then `if target_idx < 0: return invalid_argument("Step not found in workflow")`. Typed, but still labelled `invalid_argument` rather than anything version-specific.
- **`generate_artifact`:** Only reachable once `current_step == COMPLETE`. It reads `wf["steps"][-1]["id"]` from the live workflow and pulls `step_data.get(that_id, "")`. If the final step was renamed, the lookup misses and the artifact is the empty string (or, under `output_format="text"`, a string with zero-content joins; under `"structured_code"`, a list whose `content` fields are all `""`). The session completes "successfully" and returns a wrong artifact. **This is the subtle failure mode the brief flagged.**

### Scenario 2 — Step inserted before `current_step`

Suppose a session is at `"step_3"` and the reloaded workflow becomes `[step_1, step_2, NEW, step_3, ...]`.

- Step resolution by id still works: `_find_step(wf, "step_3")` finds it at the new ordinal index (idx=3 where it was idx=2). `submit_step` proceeds normally; `progress: "step 4 of 6 complete"` silently jumps from what was previously "step 3 of 5 complete". No warning.
- The `NEW` step was never visited and is absent from `step_data`. `_compute_skipped_steps` walks the step list and treats a step absent from `step_data` *with no precondition* as "just not reached yet" — it is neither marked skipped nor flagged. If any later step has `inject_context: [{from: NEW}]`, `_assemble_context` returns `{"from": NEW, "content": None}` — the downstream step's directive sees `None` where it expected real content. **Silent content degradation.**
- If `NEW` carries a `precondition` referencing some prior step's output, the precondition evaluates — behaviour then depends on whether the reference resolves. An unmet precondition silently adds `NEW` to `skipped_steps`; a reference to an absent predecessor raises `_SkippedPredecessor`, which most paths translate to a typed `skipped_predecessor_reference` error.
- `get_state.pending_steps` recomputes against the new step list, so the client sees an expanded pending list without any indication the workflow shape changed.

### Scenario 3 — Step deleted after `current_step` but before workflow end

Suppose a session is at `"step_2"` and the reloaded workflow becomes `[step_1, step_2, step_4, ...]` (step_3 deleted).

- Linear advance after `step_2` submits goes to `step_4`. No error; the hop is invisible to the client.
- If any later step has `inject_context: [{from: step_3}]` or `precondition: {when_equals: {ref: "step_data.step_3...", ...}}`, resolution produces `None` / `_REF_ABSENT` → the precondition evaluates false → the step is silently added to `skipped_steps`, or the context is injected as `None`. **Silent degradation.**
- If some step's `branches[].next == "step_3"` or `default_branch == "step_3"` in the reloaded YAML (the branch dict still references the deleted target): `submit_step`'s validity check `target not in valid_targets` passes (the string `"step_3"` is still in the current `step["branches"]` array), so `next_step_id = "step_3"` is accepted. The subsequent `_apply_skip_loop` calls `_find_step(wf, "step_3")` which returns `(-1, None)`, and the next line `pc = step.get("precondition")` raises `AttributeError`. Caught by `_trap_errors` and returned as a generic `invalid_argument`. **Another confused error label.** (Note: `validate_workflow_calls` + per-workflow validation at startup would normally catch a dangling branch target — so this scenario only occurs if the validator fails to reject the edit at load time, which per the existing schema checks would be unusual.)

### Scenario 4 — Step's `gates`, `output_schema`, or `directive_template` changed

Step identity unchanged; semantics changed.

- **`directive_template` / `gates` / `anti_patterns` changed on the current step:** next `get_state` / `submit_step` response surfaces the new values. The client may see a different directive than it saw on the previous call with no indication anything was swapped. If the client submits content it was composing against the old directive, `submit_step` validates against the new `output_schema` (if present) — the submission may fail validation or pass against different rules than it was written for. Retry budget is consumed either way.
- **`output_schema` tightened on a previous step:** `step_data[that_step]` was validated against the looser old schema and stored as-is. No re-validation on retrieval. If a later step has `inject_context: [{from: that_step}]`, it silently sees data that does not conform to the current schema. Downstream steps that parse `step_data` via refs (in `precondition`, `call_context_from`, `mcp_tool_call` args) behave normally if the shape happens to still fit, or raise `_REF_ABSENT` / `_SkippedPredecessor` if the new constraint expected additional sub-fields. **Silent semantic drift.**
- **`revise_step` on an affected step:** returns the new directive / gates / schema, along with the old `previous_content` for reference. A subsequent resubmit validates against the new schema. This path is in fact honest — the client sees both the old content and the new contract.

### Scenario 5 — Sub-workflow `call` target renamed or removed

Two preconditions matter here: (a) whether the parent's YAML was also edited to match, and (b) whether `validate_workflow_calls` accepts the loaded set.

- **Child renamed, parent NOT edited:** parent's in-memory step still has `call: "old_name"`. Startup-time `validate_workflow_calls` fails — the loaded set does not contain `"old_name"`. `create_app` raises `ValueError` and the process does not start. Sessions referencing this parent are unreachable until the YAMLs are reconciled.
- **Child removed, parent NOT edited:** same as above — startup fails.
- **Child renamed or removed, parent ALSO edited to remove the call:** process starts cleanly. Any session already in-flight *above* the (removed) child — i.e. with a call-frame in `session_stack` pointing at a child session whose `workflow_type` is the old child name — persists in the DB. When a tool call is made against the parent, the `pending_child` guard (`tools.py:927-940`) fires `sub_workflow_pending` correctly. When a tool call is made against the orphaned child session, `_resolve_session` returns `workflow_not_loaded`. **The child session is an unreachable orphan; `delete_session` is the only way out.**
- **Child exists but parent's `call:` target string was edited** (e.g. typo fix that happens to change the target): if the new target exists in the loaded set, `validate_workflow_calls` passes. A session that previously reached the old call-step now sees the in-memory parent pointing at a different child. If the session has not yet called `enter_sub_workflow`, the next call resolves against the new target — the author-intended change applies transparently. If a call-frame already exists in `session_stack` pointing at a child of the old type, the orphan condition above applies.

### Scenario 6 — `branches` targets in current step changed

- `submit_step`'s `valid_targets = [b["next"] for b in step["branches"]]` is computed from the live in-memory step. If the client passes `branch="old_target"` and the old target is gone, validity check fails → `invalid_argument`. **Typed and honest.**
- If the client passes `branch=""` (use default), `step.get("default_branch", "")` returns whatever the new YAML says. Silent switch to the new default.
- If the new branch set contains a target that does not exist as a step id in the same workflow: `validate_workflow` at load time rejects dangling branch / default_branch targets. Process would not start. In the currently-running process, this scenario cannot arise.
- If an existing branch entry's `condition` label changed but the `next` stayed the same: purely cosmetic. The LLM may see a different set of options described in the response than it saw on the previous call.

### Scenario 7 — Workflow file deleted entirely

- **Startup gate:** if any other loaded workflow has `call: deleted_workflow`, `validate_workflow_calls` fails and `create_app` raises. Process does not start.
- **No remaining references, but persisted sessions use it:** startup succeeds. Every tool call against the orphaned sessions routes through `_resolve_session` and returns `workflow_not_loaded` with the session fingerprint and an `available_types` list. Typed, honest, unrecoverable short of `delete_session`.
- **`list_sessions`:** still enumerates the orphan. It reads from the DB and does not cross-check against the live workflow set (see §5 below).
- **`delete_session`:** succeeds — it bypasses `_resolve_session`, performs a DB delete, and drops any `session_stack` row for the session (`state.py:790-805`).

> **Postscript (added after ADR-001 implementation shipped).** The workflow-versioning stance deliberately does not touch the deleted-file path. The pre-existing `workflow_not_loaded` envelope is already the correct response for this scenario — it distinguishes "name disappearance" from "same name, different content" and the stance's `workflow_changed` envelope covers only the latter. The two envelopes are architecturally complementary; scenario 7 above remains accurate as a characterisation of the deleted-file path and is unaffected by the stance implementation. The test suite covers a renamed-variant of scenario 7 (`workflow_file_rewritten`) under the `workflow_changed` envelope to exercise the content-mutation path that the discovery report did not originally enumerate as a distinct sub-case.

## 5. `list_sessions` confirming note

`list_sessions` (`tools.py:1725-1729`, backed by `state.list_sessions` in `state.py:276-320`) is a pure SQLite enumeration. It returns metadata per row: `session_id`, `fingerprint`, `owner_identity`, `workflow_type`, `current_step`, `status`, `created_at`, `updated_at`, `parent_session_id`, `stack_depth`, `under_session_id`. It does not resolve the workflow object, does not call `_find_step`, does not consult the in-memory `workflows` dict. Orphaned sessions (workflow deleted / renamed without a compatible alias) appear here with their original `workflow_type` string intact — which is itself a useful diagnostic surface because an operator running `list_sessions` against a post-edit server will see the stale-name rows in plain text.

Its output surface is unaffected by this class of mid-flight change. Safe.

## 6. Deployment-model findings

**Horizon (today, the live deploy).** The SQLite DB defaults to `<repo>/server/megalos_sessions.db` (`db.py:11`), overridable via `MEGALOS_DB_PATH`. Horizon's ephemeral-container model means the filesystem is wiped on redeploy unless a persistent volume is mounted, and Horizon's free-tier path does not mount one. Concretely: every Horizon redeploy spawns a new container with a fresh filesystem, so `megalos_sessions.db` does not exist on startup, `db.py` creates it empty, and no pre-existing sessions are reattached to the freshly-loaded workflows. **The mid-flight mismatch scenarios in §4 are unreachable under the Horizon deployment model today** — every YAML change is necessarily accompanied by a redeploy that evacuates the session store.

**Local iteration loop.** Whatever command starts the server — `uv run python -m megalos_server.main`, `uv run fastmcp dev megalos_server/main.py:mcp`, or equivalent — the process executes `create_app()` once at import. Editing a workflow YAML and re-triggering any tool call serves the **cached startup version**. The new YAML is not seen until the process is restarted. There is no reload signal, no auto-reload, no watcher. On restart, the SQLite DB persists (it is at a stable path on the developer's local filesystem), so any sessions created before the edit are re-attached to the new workflow and hit the §4 behaviours.

**Enterprise self-hosted (future).** The scenario the brief flags. A self-hoster who (a) mounts a persistent volume for `megalos_sessions.db`, and (b) performs rolling restarts on YAML changes without draining sessions, will hit every §4 behaviour in production. The ephemeral-container mask is absent.

## 7. Observed patterns

Two patterns recur across §4:

1. **Typed-error coverage is incomplete and inconsistent.** `get_guidelines`, `revise_step`, and `enter_sub_workflow` emit structured, step-aware errors when a step can't be found. `submit_step` relies on `_trap_errors` to fall back to a generic `invalid_argument` envelope that does not carry `step_id`, `field`, or a version-mismatch label. `get_state` degrades silently (returns `current_step: None, progress: "unknown"` with no error flag). `generate_artifact` on a renamed final step returns an empty-string artifact with status "success".

2. **Reference-path resolution (`inject_context`, `precondition`, `call_context_from`, `mcp_tool_call` args) silently degrades to absent or `None`.** A later step whose directive / precondition / args reference a step that was renamed, inserted-around, or deleted will see `None` or behave as if the predecessor were "skipped" — even though the predecessor's real state is "exists under a different name" or "never existed in this version of the workflow." There is no ref-vs-version check.

These are not proposals. They are descriptive characterisations of how the current code path behaves under the scenarios the brief enumerated.

---

## 8. Open / uncharacterised

- **Concurrent restart during an active session:** the brief asks about Horizon-level reattachment. I did not exercise a restart while a session was literally mid-tool-call; the SQLite transactions in `state.py` would complete or rollback atomically by DB semantics, but the lifecycle-level question (does the client receive a usable error, or does the connection drop?) is client-transport-dependent and outside the scope of this report.
- **Schema-version field behaviour.** `schema_version` exists on the YAML top-level (defaults to `"0.4"`) but is not stamped into `step_data` or the session row. It is read at load time and discarded. A change in `schema_version` between versions does not produce any runtime signal. Noted for the stance discussion — today this field does not participate in any versioning decision.
- **`intermediate_artifacts` shape changes.** Not specifically probed. If an earlier step had checkpointed artifacts under an old `intermediate_artifacts[].id` that the reloaded step no longer declares, `state.get_artifacts(session_id, step_id)` returns the old dict verbatim (it is DB-keyed, not schema-checked). Downstream tool responses would surface stale `artifact_checkpoints` keys on `get_state` that the reloaded workflow no longer acknowledges. Mentioned here because it is another silent-drift surface but was not in the original scenario list.

Report ends. No changes proposed.
