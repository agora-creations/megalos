# IDE Setup — Workflow YAML Authoring

The megálos workflow schema is exported as `schemas/megalos-workflow.schema.json`, a JSON Schema 2020-12 document suitable for binding in any IDE that honours the `$schema` convention. With the schema bound, authors get autocomplete, hover documentation, and error squiggles at typing time — no round-trip to the validator required.

This covers the structural checks JSON Schema can express. Cross-step reference checks (precondition forward-refs, branch target existence, call target existence, call cycles, `inject_context` source existence) remain enforced by `megalos_server.validate` at load time; a full IDE diagnostic coverage of those is the future `megalos-vscode` extension.

## VS Code (Red Hat YAML extension)

Install the [YAML extension by Red Hat](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) if you do not already have it.

Add a workspace-level binding to `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    "https://raw.githubusercontent.com/agora-creations/megalos/main/schemas/megalos-workflow.schema.json": [
      "workflows/*.yaml",
      "workflows/*.yml",
      "megalos_server/workflows/*.yaml",
      "tests/fixtures/workflows/**/*.yaml"
    ]
  }
}
```

Adjust the glob patterns to match where your workflows live. For pinned, offline-safe use, check the schema file into your repo and replace the URL with a relative path:

```json
{
  "yaml.schemas": {
    "./schemas/megalos-workflow.schema.json": ["workflows/*.yaml"]
  }
}
```

## JetBrains family (PyCharm, IntelliJ, WebStorm, GoLand)

JetBrains IDEs ship with built-in JSON Schema support for YAML. No plugin required.

1. **Settings → Languages & Frameworks → Schemas and DTDs → JSON Schema Mappings**.
2. Click **+** to add a new mapping.
3. Name: `Megalos Workflow`.
4. Schema file or URL: `https://raw.githubusercontent.com/agora-creations/megalos/main/schemas/megalos-workflow.schema.json` (or a local path if you vendored the schema).
5. Schema version: `JSON Schema Version 2020-12`.
6. Add file patterns (one per row): e.g., `workflows/*.yaml`, `tests/fixtures/workflows/**/*.yaml`.

Inline schema binding via a file-top comment is also supported by some JetBrains releases:

```yaml
# $schema: ../schemas/megalos-workflow.schema.json
name: my_workflow
# ...
```

## Neovim (yaml-language-server via nvim-lspconfig)

Install [yaml-language-server](https://github.com/redhat-developer/yaml-language-server) (`npm i -g yaml-language-server`) and wire it up through `nvim-lspconfig`. This is the same language server the VS Code Red Hat extension wraps, so the binding shape is identical.

Add to your Neovim config (`init.lua`):

```lua
require("lspconfig").yamlls.setup({
  settings = {
    yaml = {
      schemas = {
        ["https://raw.githubusercontent.com/agora-creations/megalos/main/schemas/megalos-workflow.schema.json"] = {
          "workflows/*.yaml",
          "workflows/*.yml",
          "megalos_server/workflows/*.yaml",
          "tests/fixtures/workflows/**/*.yaml",
        },
      },
    },
  },
})
```

For `coc.nvim` users, install `coc-yaml` and place the same `yaml.schemas` map in `:CocConfig`. The inline `# yaml-language-server: $schema=./schemas/megalos-workflow.schema.json` comment at the top of a workflow file is also honoured and avoids per-project config entirely.

## Helix

Helix ships with built-in LSP support. Install `yaml-language-server` (`npm i -g yaml-language-server`) and bind the schema in `~/.config/helix/languages.toml`:

```toml
[language-server.yaml-language-server.config.yaml]
schemas = { "https://raw.githubusercontent.com/agora-creations/megalos/main/schemas/megalos-workflow.schema.json" = [
  "workflows/*.yaml",
  "workflows/*.yml",
  "megalos_server/workflows/*.yaml",
  "tests/fixtures/workflows/**/*.yaml",
] }

[[language]]
name = "yaml"
language-servers = ["yaml-language-server"]
```

As with the other editors, the `# yaml-language-server: $schema=./schemas/megalos-workflow.schema.json` top-of-file comment is an inline alternative that binds a single workflow without touching global config.

## What the schema checks (and what it doesn't)

**Checked at typing time via the schema:**

- Required top-level fields: `name`, `description`, `category`, `output_format`, `steps`.
- `steps` must be a non-empty list.
- Per-step required fields differ by step type:
  - LLM steps need `id`, `title`, `directive_template`, `gates`, `anti_patterns`.
  - `action: mcp_tool_call` steps need `id`, `title`, `action`, `server`, `tool`, `args`.
- `mcp_tool_call` mutex rules — the schema rejects `directive_template`, `gates`, `anti_patterns`, `call`, `collect`, `output_schema` on a `mcp_tool_call` step.
- `mcp_tool_call` literal-only rules — `server` and `tool` reject strings containing `${`.
- `precondition` structure — exactly one of `when_equals` / `when_present`, with the ref-path regex enforced inline.
- `call` + `collect: true` rejected.
- `call` + `intermediate_artifacts` rejected.
- `call` + `branches` without `default_branch` rejected.
- `output_from` requires `intermediate_artifacts` on the same step.
- `call_context_from` requires `call` on the same step.
- Guardrail `trigger.type` must be one of `keyword_match` / `step_count` / `step_revisit` / `output_length`.
- Guardrail `action` must be one of `warn` / `force_branch` / `escalate`; `force_branch` requires `target_step`.
- `conversation_repair` keys are restricted to the four known behaviors.

**Enforced by `megalos_server.validate` (not expressible in pure JSON Schema):**

- `precondition` cannot reference a forward step (index-based check against the current step's position).
- `precondition` sub-path refs require the source step to have `output_schema` or `collect: true` (or be an `mcp_tool_call` step with its implicit envelope).
- `branches[].next` / `default_branch` must point to an existing step ID in the same workflow.
- `inject_context[].from` must point to an existing step ID in the same workflow.
- `guardrails[].target_step` must point to an existing step ID.
- `call` targets must resolve against the loaded workflow set; the `call` graph must be acyclic.
- `mcp_tool_call` `server` values must resolve against the MCP registry (`mcp_servers.yaml`).
- `output_schema` and `intermediate_artifacts[].schema` content must themselves be valid JSON Schema (checked via `jsonschema.Draft202012Validator.check_schema`).

For the full error-code catalogue and cross-step semantics, see [`megalos_server/SCHEMA.md`](../megalos_server/SCHEMA.md).

## Keeping the schema in sync

The exported schema is a build artifact under version control (`schemas/megalos-workflow.schema.json`). Drift between the schema and the imperative validator in `megalos_server/schema.py` is detected by the parity test in `tests/test_workflow_json_schema_export.py`: every fixture that passes `validate_workflow` must also validate against the exported JSON Schema. A change to `schema.py` that widens or narrows structural constraints will require a matching edit to the JSON Schema, or the test will fail.
