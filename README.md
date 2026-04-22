# megálos

> μεγάλος (ancient Greek: *big*, *great*)

**A deterministic runtime for authored AI conversations.** YAML is the source code. An MCP server is the runtime. The LLM is a replaceable text engine that gets constrained, not unleashed.

---

## The thesis

LLMs are more useful when constrained through authored conversational programs than when left to free-associate. The value is not in making LLMs do *more* — it is in making them do *exactly what a workflow author intended*, step by step, with mechanical enforcement at each transition.

Determinism lives in the runtime, not the prompt. The server rejects out-of-order submissions, invalidates downstream data on revision, caps active sessions, validates structured output against JSON Schema, and injects do-not rules into every directive. Any LLM that reads English and calls MCP tools can execute the workflow — no provider adapter, no per-LLM prompt translation.

The separation of concerns is sharp: the LLM interprets what the user wants and produces text; the runtime decides what happens next. megálos ships that separation as a three-dependency MCP server anyone can host for the price of a free-tier container.

## Contents

- [Architecture — three layers](#architecture--three-layers)
- [The YAML schema](#the-yaml-schema)
- [The MCP server runtime](#the-mcp-server-runtime)
- [What the runtime guarantees](#what-the-runtime-guarantees)
- [Authoring DX surfaces](#authoring-dx-surfaces)
- [Domain servers](#domain-servers)
- [Authoring a new domain repo](#authoring-a-new-domain-repo)
- [Cross-model panel (optional extra)](#cross-model-panel-optional-extra)
- [mikrós — future agent-skills library](#mikrós--future-agent-skills-library)
- [License](#license)

## Architecture — three layers

| Layer | What it is | Status |
|-------|------------|--------|
| **megálos** (this repo) | YAML schema, MCP server runtime (`megalos-server` package), validator, visualization, JSON Schema export | live |
| **megálos-{domain}** | Per-domain MCP servers built on the runtime | live: writing, analysis, professional |
| **agora-creations** | Bring-your-own-key chat client (BYOK) | future |

## The YAML schema

The schema is the API surface. One YAML file equals one workflow. Adding a workflow means adding a file, not writing code. Full reference in [`megalos_server/SCHEMA.md`](megalos_server/SCHEMA.md); the exported JSON Schema 2020-12 lives at [`schemas/megalos-workflow.schema.json`](schemas/megalos-workflow.schema.json) for IDE binding.

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

No Turing-complete escape hatches. No Python. No `link:` gotos. The schema expresses what authoring actually needs and stops there.

Validate a workflow file locally:

```bash
python -m megalos_server.validate path/to/workflow.yaml            # structural + cross-step
python -m megalos_server.validate path/to/workflow.yaml --diagram  # valid + Mermaid flowchart
```

## The MCP server runtime

- **Distribution:** `megalos-server` (pinned via git URL in consumers).
- **Import:** `megalos_server`.
- **Runtime dependencies:** three — `fastmcp`, `pyyaml`, `jsonschema`. Hermeticity enforced by test.
- **Zero LLM imports.** The server never calls a model. There is no OpenAI or Anthropic in the runtime dependency graph.

### Public API

```python
from megalos_server import create_app

mcp = create_app(workflow_dir="./workflows")  # defaults to the bundled reference workflow
mcp.run(transport="streamable-http")
```

Domain repos and downstream consumers pin the runtime via git URL:

```toml
[project]
dependencies = [
    "megalos-server @ git+https://github.com/agora-creations/megalos.git@v0.3.0",
]
```

Local development override: `pip install -e ../megalos`.

### The twelve MCP tools

Grouped by lifecycle:

- **Discovery / start.** `list_workflows`, `start_workflow`.
- **Step loop.** `get_state`, `get_guidelines`, `submit_step`, `revise_step`.
- **Composition.** `enter_sub_workflow` (author-declared child via step `call:`).
- **Digressions.** `push_flow` / `pop_flow` (client-initiated, auto-resumed on completion).
- **Session lifecycle.** `list_sessions`, `delete_session`, `generate_artifact`.

Tool responses are plain dicts. Every step response carries the `directive`, `gates`, `anti_patterns`, and seven global `_DO_NOT_RULES` that tell the LLM what never to do — skip ahead, submit silently, reveal step numbers to the user, ask multiple questions at once. No prompt engineering. Just mechanics.

### Session state

SQLite-backed (stdlib, single file — still trivially deployable). Sessions carry `session_id`, `workflow_type`, `current_step`, `step_data`, retry and visit counters, timestamps, and — when nested — a `session_stack` row linking them to their root with a frame-type flag. Two frame types share one stack primitive: **call-frames** (author-declared via `call:`, author-resumed with artifact propagation) and **digression-frames** (client-pushed via `push_flow`, auto-resumed on child completion). Stack depth is capped at three under a global five-active-session ceiling. A detached-snapshot invariant applies: reads return freshly-constructed dicts, so mutations only persist through dedicated update helpers.

## What the runtime guarantees

- **Order.** `submit_step` rejects out-of-order submissions.
- **Revision correctness.** `revise_step` invalidates every downstream `step_data` entry. No stale reads survive a revision.
- **Bounded load.** Active sessions cap at five with TTL expiration; session-axis rate limiting sits in middleware; content / artifact / YAML payloads have explicit byte caps.
- **Output validity.** Steps carrying `output_schema` run their submission through `jsonschema` with a configurable retry budget before advancing.
- **Guardrails.** Top-level `guardrails` evaluate keyword / count / revisit / output-length triggers and can `warn`, `force_branch`, or `escalate` (irrecoverable).
- **Capability-token identity.** `session_id` is a 256-bit cryptographically random token (`secrets.token_urlsafe(32)`). Possession of the token is authorisation; the server performs no inbound authentication, which matches the "public deploy, BYOK at the client" threat model documented in [`SECURITY.md`](SECURITY.md).
- **Crash recovery.** In-process crashes within a single container lifetime do not lose sessions; SQL transactions replace hand-rolled locks on the read-modify-write hot paths.
- **Hermetic runtime.** A hermeticity test fails CI if any runtime module imports anything beyond the three declared dependencies.
- **Static performance baseline.** A pytest-benchmark suite records hot-path and cold-start numbers; see [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## Authoring DX surfaces

The runtime is not the product. The product is a workflow someone can read, review, and trust. Three surfaces serve that goal:

**Validator.** `python -m megalos_server.validate <workflow.yaml>` exits non-zero on any structural or cross-step failure — forward-ref preconditions, dangling branch targets, unresolved call targets, cyclic call graphs, malformed `output_schema`, unresolved MCP registry references.

**Visualization.** `python -m megalos_server.diagram <workflow.yaml>` emits a Mermaid `flowchart TD` block: sequential steps as nodes, branches as labelled edges, preconditions as dotted gating edges, sub-workflow calls as named `subgraph` references (never inlined), `mcp_tool_call` steps in a visually distinct subroutine shape. Paste into any GitHub PR comment, README, or docs page — the renderer handles the rest. See [`docs/VISUALIZATION.md`](docs/VISUALIZATION.md).

**IDE binding.** The schema is exported as JSON Schema 2020-12 at [`schemas/megalos-workflow.schema.json`](schemas/megalos-workflow.schema.json). Bind it in the Red Hat YAML extension (VS Code) or via the built-in JSON Schema Mappings (JetBrains) for autocomplete, hover docs, and error squiggles at keystroke time. Step-by-step setup in [`docs/IDE_SETUP.md`](docs/IDE_SETUP.md). A parity test fails CI if the export ever drifts from `megalos_server/schema.py`.

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
2. Clone, add `pyproject.toml` pinning `megalos-server@vX.Y.Z`, a flat `main.py` calling `create_app(workflow_dir=Path(__file__).parent / "workflows")`, your YAMLs under `workflows/`, and tests under `tests/` (with their own conftest constructing an app via `create_app(workflow_dir=...)`).
3. `pip install -e ".[test]" && pytest && python main.py` to verify.
4. Push.

Authoring mechanics — directive quality, context injection, gates, branches, sub-workflows, push/pop flows, common mistakes — live in [`docs/AUTHORING.md`](docs/AUTHORING.md).

## Cross-model panel (optional extra)

`megalos_panel` batches multiple LLM providers (Claude, OpenAI) against the same prompt in a single call. It powers measurement and fixture-authoring work — not the server runtime. The core server never imports it; the boundary is enforced by a hermeticity test so the three-dependency runtime claim stays load-bearing.

```bash
pip install "megalos[panel]"   # or: uv sync --extra panel
```

```python
from megalos_panel import panel_query, PanelRequest

results = panel_query([
    PanelRequest(request_id="q1", prompt="...", model="claude-opus-4-7"),
    PanelRequest(request_id="q1", prompt="...", model="gpt-4o"),
])
```

Provider SDKs resolve by model-name prefix (`claude-` → Anthropic, `gpt-` → OpenAI). Retries, backoff, rate-limit classification, and JSON-lines record IO are built in. See [`docs/panel.md`](docs/panel.md) for the full API.

## mikrós — future agent-skills library

mikrós (ancient Greek: *small*) is a separate, future project: a lightweight agent-skills library for coding agents, inspired by [RasaHQ/rasa-agent-skills](https://github.com/RasaHQ/rasa-agent-skills). It will be a collection of markdown skill files that teach a coding agent how to author, test, and deploy megálos workflows. Not a package, not a runtime, not a deployment — just knowledge in the shape an agent can read. megálos is the platform; mikrós is how agents learn to use it.

## License

MIT. See [`LICENSE`](LICENSE).
