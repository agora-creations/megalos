# GSD-2 upstream issue: MCP bridge boolean / parameter coercion drops values silently

**Severity:** Medium — blocks `gsd_complete_milestone`; also surfaces on `gsd_save_decision` with the `when_context` parameter under unclear conditions.

**Affected tools:**
- `mcp__gsd__gsd_complete_milestone` / `mcp__gsd__gsd_milestone_complete`
- `mcp__gsd__gsd_save_decision`

**Failure manifestations (from M005 close, 2026-04-19):**

## (1) `gsd_complete_milestone` rejects `verificationPassed: true`

Multiple attempts were made with full-content and minimal-content calls, passing `verificationPassed` as the literal string `"true"` (standard for JSONSchema boolean coercion). Every attempt returned:

```
Error completing milestone: verification did not pass — milestone completion blocked. verificationPassed must be explicitly set to true after all verification steps succeed
```

The error message says "must be explicitly set to true" which reads as a value check — but the client IS passing "true". The most likely root cause is that the MCP bridge is dropping the parameter or failing to coerce the string to a boolean, so the server sees `verificationPassed=undefined` or `verificationPassed=false` and returns the "must be set" error.

## (2) `gsd_save_decision` rejects with SQLite parameter bind error on `when_context`

On the same milestone-close turn, `gsd_save_decision` returned:

```
Error saving decision: Provided value cannot be bound to SQLite parameter 6.
```

This persisted across minimum-content and fuller-content attempts. Removing the `when_context` parameter (optional per schema) unblocked the save. Parameter 6 in the insert order is plausibly `when_context`; the bind error is consistent with the server receiving a value type SQLite cannot bind (e.g., `undefined` vs empty string, or a type-coerced-wrong value).

The two symptoms are likely the same bug class: MCP parameter-layer coercion silently producing `undefined`/wrong types for specific parameter shapes.

## Reproduction

Both failures reproduced reliably during M005 close on 2026-04-19 with tool versions as installed via the project's current GSD-2 runtime state. Exact input payloads are in the conversation transcript at `/Users/diegomarono/.claude/projects/-Users-diegomarono-megalos/0c51d2cd-1f3f-4d7a-84da-1e094d76df8a.jsonl`.

## Workaround (project-side)

- For `gsd_save_decision`: drop `when_context` from the payload and retry. Successful saves without the parameter. If full provenance is needed, save a follow-up decision that explicitly supersedes the minimal one and carries the intended `when_context` as narrative content. Precedent: D024 (minimal stub) → D025 (fuller form, explicit supersede).
- For `gsd_complete_milestone`: no project-side workaround identified. The tool cannot be invoked successfully under these conditions. Milestone formal-state lags `main`'s functional-state until upstream fix lands. Document the lag in the milestone's deferred-work archive README so future readers do not mistake stale GSD state for authoritative state.

## Expected fix

Audit the MCP bridge's parameter serialization and coercion path for:
- JSON-schema `boolean` fields receiving `true`/`false` as strings (common when the client composes via text-mode tool-use)
- JSON-schema `string` fields receiving content that trips SQLite binding (null, undefined, or non-string types after coercion)

Both symptoms likely resolve with one audit pass and a uniform coercion strategy at the bridge layer.

## Links to observed precedent

- D024 and D025 in `.gsd/DECISIONS.md` — saved-decision workaround
- `.gsd/deferred/M005/S04/README.md` — milestone formal-state-lag documentation
- Commit history on main from `1b501c0` onward — M005 functional-state as source of truth during the lag
