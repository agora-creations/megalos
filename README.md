# megálos

> μεγάλος (ancient Greek: *big*, *great*)

**A deterministic runtime for authored AI conversations.** YAML is the source code. An MCP server is the runtime. The LLM is a replaceable text engine that gets constrained, not unleashed.

---

## The thesis

LLMs are more useful when constrained through authored conversational programs than when left to free-associate. The value is not in making LLMs do *more* — it is in making them do *exactly what a workflow author intended*, step by step, with mechanical enforcement at each transition.

Determinism lives in the runtime, not the prompt. The server rejects out-of-order submissions, invalidates downstream data on revision, caps active sessions, validates structured output against JSON Schema, and injects do-not rules into every directive. Any LLM that reads English and calls MCP tools can execute the workflow — no provider adapter, no per-LLM prompt translation. The separation of concerns is sharp: the LLM interprets what the user wants and produces text; the runtime decides what happens next.

## Contents

- [Quickstart](#quickstart)
- [Architecture — three layers](#architecture--three-layers)
- [The YAML schema](#the-yaml-schema)
- [Authoring DX](#authoring-dx)
- [What the runtime guarantees](#what-the-runtime-guarantees)
- [Public API + the MCP tool surface](#public-api--the-mcp-tool-surface)
- [Domain servers](#domain-servers)
- [Authoring a new domain repo](#authoring-a-new-domain-repo)
- [Ecosystem](#ecosystem)
- [Status / What's next](#status--whats-next)
- [License](#license)

## Quickstart

Requires Python 3.10+. The runtime ships as `megalos-server`; install from the published git URL or check out this repo for development.

```bash
# Add to a project (Python ≥ 3.10).
uv add "megalos-server @ git+https://github.com/agora-creations/megalos.git@v0.4.0"
# or:
pip install "megalos-server @ git+https://github.com/agora-creations/megalos.git@v0.4.0"
```

Validate the bundled reference workflow:

```bash
python -m megalos_server.validate megalos_server/workflows/example.yaml
```

Step through it without calling an LLM (sets the dry-run inspector's required DB path; see [issue #41](https://github.com/agora-creations/megalos/issues/41) for why `:memory:` is rejected):

```bash
export MEGALOS_DB_PATH=$(mktemp -t megalos-dryrun.XXXXXX).db
python -m megalos_server.dryrun megalos_server/workflows/example.yaml
```

Run the server:

```python
from megalos_server import create_app

mcp = create_app(workflow_dir="./workflows")  # defaults to the bundled example.yaml
mcp.run(transport="streamable-http")
```

## Architecture — three layers

| Layer | What it is | Status |
|-------|------------|--------|
| **megálos** (this repo) | YAML schema, MCP server runtime (`megalos-server` package), validator, visualization, dry-run inspector, JSON Schema export | live |
| **megálos-{domain}** | Per-domain MCP servers built on the runtime — each pins a `megalos-server` version and ships its own workflow set | live: writing, analysis, professional |
| **Reference client** | A megálos-aware chat client for end-users (Phase G, vision-v6 §3.2 + §4 Shape 2) | deferred |

## The YAML schema

The schema is the API surface. One YAML file equals one workflow. Adding a workflow means adding a file, not writing code. Full reference in [`megalos_server/SCHEMA.md`](megalos_server/SCHEMA.md); the exported JSON Schema 2020-12 lives at [`schemas/megalos-workflow.schema.json`](schemas/megalos-workflow.schema.json) for IDE binding. Default `schema_version` is `"0.4"` (see [`megalos_server/schema.py`](megalos_server/schema.py)).

**Top level.** `name`, `description`, `category`, `output_format`, `steps`, optional `schema_version`, optional `guardrails`, optional `conversation_repair`.

**Per step.** `id`, `title`, `directive_template`, `gates`, `anti_patterns`, plus any of the behavioural primitives the runtime supports:

| Field | Meaning |
|---|---|
| `output_schema` | JSON Schema validating the LLM's structured submission, with a retry budget |
| `inject_context` | Earlier steps whose output the directive sees |
| `branches` + `default_branch` | Non-linear next step chosen by the LLM from a declared option set |
| `intermediate_artifacts` | Multi-checkpoint validation within a single step |
| `precondition` (`when_equals` / `when_present`) | Declarative step-skip against prior `step_data` with cascade semantics |
| `call` + `call_context_from` | Declarative sub-workflow composition — child runs to completion, artifact propagates back to the parent |
| `action: mcp_tool_call` | Non-LLM step that invokes an external MCP tool through a registry |

No Turing-complete escape hatches. No Python. No `link:` gotos. The schema expresses what authoring actually needs and stops there. The full authoring guide — primitives, design principles, sub-workflow composition, push/pop digressions, common mistakes, a worked example — lives in [`docs/AUTHORING.md`](docs/AUTHORING.md).

## Authoring DX

The runtime is not the product. The product is a workflow someone can read, review, and trust. Four surfaces serve that goal.

**Validator.** `python -m megalos_server.validate <workflow.yaml>` exits non-zero on any structural or cross-step failure — forward-ref preconditions, dangling branch targets, unresolved call targets, cyclic call graphs, malformed `output_schema`, unresolved MCP registry references. Add `--diagram` to print a Mermaid `flowchart TD` block alongside the validation report.

**Dry-run inspector.** `python -m megalos_server.dryrun <workflow.yaml>` steps through a workflow interactively without calling an LLM, driving `start_workflow` + `submit_step` against a real `create_app` instance. Branch selection, precondition skips, sub-workflow descent and ascent, and decoded error envelopes all render in the REPL. Pass `--responses-file <yaml>` to drive a scripted run from a recorded response set; useful for regression replays at zero LLM cost. Requires `MEGALOS_DB_PATH` set to a file path before invocation.

**Visualization.** `python -m megalos_server.diagram <workflow.yaml>` emits a Mermaid `flowchart TD` block: sequential steps as nodes, branches as labelled edges, preconditions as dotted gating edges, sub-workflow calls as named `subgraph` references (never inlined), `mcp_tool_call` steps in a visually distinct subroutine shape. Paste into any GitHub PR comment, README, or docs page. See [`docs/VISUALIZATION.md`](docs/VISUALIZATION.md).

**IDE binding.** The schema is exported as JSON Schema 2020-12 at [`schemas/megalos-workflow.schema.json`](schemas/megalos-workflow.schema.json). Bind it in the Red Hat YAML extension (VS Code), JetBrains' built-in JSON Schema Mappings, or the YAML LSP shipped with Neovim and Helix for autocomplete, hover docs, and error squiggles at keystroke time. Setup walk-throughs for each editor in [`docs/IDE_SETUP.md`](docs/IDE_SETUP.md). A parity test fails CI if the export ever drifts from `megalos_server/schema.py`.

If you want an AI coding agent to do the authoring instead, see [mikrós](https://github.com/agora-creations/mikros) — a Markdown skill library that teaches coding agents the megálos authoring path end-to-end.

## What the runtime guarantees

- **Order.** `submit_step` rejects out-of-order submissions.
- **Revision correctness.** `revise_step` invalidates every downstream `step_data` entry. No stale reads survive a revision.
- **Workflow versioning.** Every session snapshots the workflow's canonical fingerprint at create time. If the on-disk YAML changes underneath an active session, the next tool call returns a terminal `workflow_changed` envelope — no silent execution against a different program. The funnel lives in `_resolve_session` ([`megalos_server/tools.py`](megalos_server/tools.py)).
- **Bounded load.** Active sessions cap at five with TTL expiration; the sub-workflow stack depth caps at three ([`megalos_server/tools.py`](megalos_server/tools.py)). Session-axis rate limiting sits in middleware; content / artifact / YAML payloads have explicit byte caps.
- **Output validity.** Steps carrying `output_schema` run their submission through `jsonschema` with a configurable retry budget before advancing.
- **Guardrails.** Top-level `guardrails` evaluate keyword / count / revisit / output-length triggers and can `warn`, `force_branch`, or `escalate` (irrecoverable).
- **Capability-token identity.** `session_id` is a 256-bit cryptographically random token (`secrets.token_urlsafe(32)`). Possession of the token is authorisation; the server performs no inbound authentication, which matches the "public deploy, BYOK at the client" threat model documented in [`SECURITY.md`](SECURITY.md).
- **Crash recovery.** In-process crashes within a single container lifetime do not lose sessions; SQL transactions replace hand-rolled locks on the read-modify-write hot paths.
- **Hermetic runtime.** A hermeticity test fails CI if any runtime module imports anything beyond the three declared dependencies.
- **Static performance baseline.** A pytest-benchmark suite records hot-path and cold-start numbers; see [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## Public API + the MCP tool surface

- **Distribution:** `megalos-server` (pinned via git URL in consumers).
- **Import:** `megalos_server`.
- **Runtime dependencies:** three — `fastmcp >= 3.2.3`, `pyyaml >= 6.0`, `jsonschema >= 4.23`. Hermeticity enforced by test.
- **Zero LLM imports.** The server never calls a model. There is no OpenAI or Anthropic in the runtime dependency graph.

```python
from megalos_server import create_app

mcp = create_app(workflow_dir="./workflows")
mcp.run(transport="streamable-http")
```

Twelve MCP tools, grouped by lifecycle:

- **Discovery / start.** `list_workflows`, `start_workflow`.
- **Step loop.** `get_state`, `get_guidelines`, `submit_step`, `revise_step`.
- **Composition.** `enter_sub_workflow` (author-declared child via step `call:`).
- **Digressions.** `push_flow` / `pop_flow` (client-initiated, auto-resumed on completion).
- **Session lifecycle.** `list_sessions`, `delete_session`, `generate_artifact`.

Tool responses are plain dicts. Every step response carries the `directive`, `gates`, `anti_patterns`, and seven global `_DO_NOT_RULES` that tell the LLM what never to do — skip ahead, submit silently, reveal step numbers to the user, ask multiple questions at once. No prompt engineering. Just mechanics.

Session state is SQLite-backed (stdlib, single file). Sessions carry `session_id`, `workflow_type`, `current_step`, `step_data`, retry and visit counters, timestamps, the workflow fingerprint, and — when nested — a `session_stack` row linking them to their root with a frame-type flag. Two frame types share one stack primitive: **call-frames** (author-declared via `call:`, author-resumed with artifact propagation) and **digression-frames** (client-pushed via `push_flow`, auto-resumed on child completion). A detached-snapshot invariant applies: reads return freshly-constructed dicts, so mutations only persist through dedicated update helpers.

## Domain servers

Workflows group by **category**, and each category lives in its own MCP server — a thin wrapper around `megalos-server` that exposes the workflows for that category. Mix and match — connect to one server, several, or all:

| Server | Category | Workflows | Remote |
|--------|----------|-----------|--------|
| `megalos-writing` | writing & communication | essay, blog | [github.com/agora-creations/megalos-writing](https://github.com/agora-creations/megalos-writing) |
| `megalos-analysis` | analysis & decision | research, decision | [github.com/agora-creations/megalos-analysis](https://github.com/agora-creations/megalos-analysis) |
| `megalos-professional` | professional | coding | [github.com/agora-creations/megalos-professional](https://github.com/agora-creations/megalos-professional) |

This repo bundles only `megalos_server/workflows/example.yaml` (a minimal two-step reference) plus the fixture suite under `tests/fixtures/workflows/`. Production workflows live exclusively in their category repos.

## Authoring a new domain repo

The pattern is mechanical. Replicate an existing domain repo and:

1. Create an empty GitHub repo.
2. Clone, add `pyproject.toml` pinning `megalos-server@v0.4.0`, a flat `main.py` calling `create_app(workflow_dir=Path(__file__).parent / "workflows")`, your YAMLs under `workflows/`, and tests under `tests/` (with their own conftest constructing an app via `create_app(workflow_dir=...)`).
3. `pip install -e ".[test]" && pytest && python main.py` to verify.
4. Push.

Authoring mechanics — directive quality, context injection, gates, branches, sub-workflows, push/pop flows, common mistakes, a walked-through worked example — live in [`docs/AUTHORING.md`](docs/AUTHORING.md).

## Ecosystem

- **mikrós** — [github.com/agora-creations/mikros](https://github.com/agora-creations/mikros). Markdown skill library that teaches AI coding agents the megálos authoring path. Not a runtime, not a CLI, not a package — content an agent reads. The Phase F onramp for Shape 2 (small teams / indie developers).
- **megalos-writing**, **megalos-analysis**, **megalos-professional** — domain MCP servers; see the table above.
- **`megalos_panel` (optional extra).** Batches multiple LLM providers (Claude, OpenAI) against the same prompt for measurement and fixture-authoring work; not part of the runtime. Install via `pip install "megalos-server[panel]"` (or `uv sync --extra panel`). API in [`docs/panel.md`](docs/panel.md). The hermeticity test enforces that the core server never imports it, so the three-dependency runtime claim stays load-bearing.

## Status / What's next

| Phase | What it covers | Status |
|---|---|---|
| M001–M012 | Runtime hardening, sub-workflows, multi-flow sessions, MCP-tool-call actions, capability-token security, performance baseline, Mermaid visualization, workflow versioning (M010), dry-run inspector (M011), authoring IDE support (M012) | shipped |
| Phase F — mikrós | Agent-skills library for AI-coding-agent authoring | shipped (external repo) |
| M013 — megalos-vscode extension | First-class VS Code extension built on the schema export | placeholder, not yet discussed |
| Phase G — reference client | Megálos-aware chat client for end-users | deferred |
| Phase H — distribution hardening | Pluggable backends + multi-replica deploy story for self-hosters (Shape 3) | scaffolded — see [`docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md`](docs/vision/2026-04-22-phase-h-distribution-hardening-roadmap.md) |
| Phase I — Horizon Developer+ | Managed hosting tier for Shape 4 | deferred |
| Phase J — configure mode | Shape 5 surface (vision-v6 §3.2 + §4) | deferred indefinitely — see [`docs/adr/003-phase-j-shipping-decision.md`](docs/adr/003-phase-j-shipping-decision.md) |

The canonical strategic document is [`docs/vision/2026-04-26-megalos-vision-v6.md`](docs/vision/2026-04-26-megalos-vision-v6.md). Five user shapes, six guardrails, the rationale for every phase above.

## License

MIT. See [`LICENSE`](LICENSE).
