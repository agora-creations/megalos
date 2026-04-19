# megalos_panel — cross-model LLM invocation utility

`megalos_panel` is a small internal utility for invoking multiple LLM
providers (Claude, OpenAI) in a single batched call. It is used by megalos
**measurement** slices — the S04 authoring-fixture cross-model panel is the
first consumer — to gather selections from several models against the same
prompt set.

**It is not a server capability.** The MCP server runtime
(`megalos_server`) never imports `megalos_panel`; structural enforcement
lives in `tests/test_import_hermeticity.py`. The zero-LLM-imports posture
on the core runtime is intentional and load-bearing for the
"3-dependency-runtime" positioning claim.

## Install

`megalos_panel` ships in the same distribution as `megalos_server`, but its
provider-SDK dependencies are declared as an optional extra so they do not
leak into the default install.

```bash
pip install "megalos[panel]"
```

Local development (workspace checkout):

```bash
uv sync --extra panel
```

The bare `pip install megalos` (no extras) installs the server module only;
importing `megalos_panel.adapters.claude` or `.openai` without `[panel]`
raises a `ModuleNotFoundError` carrying an explicit `pip install
megalos[panel]` hint (see `D019`).

## API keys

Each adapter reads its key from a conventional environment variable:

- `ANTHROPIC_API_KEY` — Claude adapter
- `OPENAI_API_KEY` — OpenAI adapter
- `GROQ_API_KEY` — Groq adapter (routes via Groq's OpenAI-compatible
  endpoint at `https://api.groq.com/openai/v1` — no separate SDK)

Panel calls that find no key raise the adapter's native configuration error
eagerly; retry logic does not cover configuration failures.

### Model-prefix routing

`dispatch()` picks an adapter by longest-prefix match on `PanelRequest.model`:

| Prefix    | Adapter         | Example model string                 |
|-----------|-----------------|--------------------------------------|
| `claude-` | `ClaudeAdapter` | `claude-opus-4-7`                    |
| `gpt-`    | `OpenAIAdapter` | `gpt-4o`                             |
| `groq/`   | `GroqAdapter`   | `groq/llama-3.3-70b-versatile`       |

The Groq adapter strips the `groq/` prefix and passes the remainder to the
Groq API unchanged, so three-segment identifiers like
`groq/openai/gpt-oss-120b` resolve to a Groq API call with
`model="openai/gpt-oss-120b"`. No new pip dependency is required — Groq
reuses the `openai` SDK already declared in the `[panel]` extra.

```python
from megalos_panel import panel_query
from megalos_panel.types import PanelRequest

results = panel_query([
    PanelRequest(prompt="…", model="groq/llama-3.3-70b-versatile"),
    PanelRequest(prompt="…", model="groq/openai/gpt-oss-120b"),
])
```

## Public API

The panel is batch-oriented. Callers build a list of `PanelRequest`
objects, hand them to `panel_query`, and get back a dict of `PanelResult`
keyed by `request_id`.

```python
from megalos_panel import panel_query
from megalos_panel.types import PanelRequest

requests = [
    PanelRequest(prompt="…", model="claude-sonnet-…"),
    PanelRequest(prompt="…", model="gpt-4o-…"),
]
results = panel_query(requests)
for req_id, result in results.items():
    if result.error is None:
        print(result.selection)
```

### Types (`megalos_panel.types`)

- `PanelRequest(prompt: str, model: str, request_id: str = <uuid4 hex>)`
  — stable `request_id` correlates request to result across the batch.
- `PanelResult(selection: str, raw_response: str, error: str | None)`
  — `selection` is the parsed selected text, `raw_response` the full
  provider response text, `error` the provider-exhaustion reason (or
  `None` on success).

### Errors (`megalos_panel.errors`)

- `PanelProviderError(model, attempts, last_error)` — raised when a single
  provider call exhausts its retry budget. Carries the model identifier,
  the number of attempts, and the last underlying error message.
- `RateLimitError`, `TransientError` — internal adapter taxonomy. Adapters
  translate provider-specific SDK exceptions into one of these two, and
  the retry layer picks the right budget by class. Never surface to
  callers; retry either succeeds or wraps the last attempt into
  `PanelProviderError`.

### Retry budget (`megalos_panel.retry`)

- `RATE_LIMIT_ATTEMPTS = 3` — 429/rate-limit retries.
- `TRANSIENT_ATTEMPTS = 5` — timeout, connection reset, 5xx retries.
- `BACKOFF_CAP_SECONDS = 30` — exponential-backoff per-retry ceiling
  (base `BACKOFF_BASE_SECONDS = 1`).

Per decision `D017`: gate-level verification of the retry contract checks
the declared form (constants exist with these values). Behavioral
verification — that a real 429 stream actually triggers the right budget,
with the right backoff curve — requires a live provider and is performed
in nightly cron, not in the standard per-PR gate.

## CI story — three mechanisms

Per decision `D015`, panel correctness is validated at three distinct
altitudes, and which mechanism runs at which time is intentional.

1. **Standard unit tests** — run on every PR in the default CI gate.
   Verify code shape: class names, type fields, constant values, record
   format, and the SDK-free import invariant (subprocess-based, covered by
   `tests/test_panel_adapters_hermeticity.py`). No network, no API keys.
   Fast, hermetic, blocks merges on regression.
2. **Live provider tests (`@pytest.mark.live`)** — skipped by default
   (`addopts` carries `-m 'not live'`). Run in a nightly cron with real
   `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` secrets. Verify real-API
   behavior: actual rate-limit headers, real transient failures, real
   backoff. This is where behavioral validation of the retry contract
   lives.
3. **JSON-lines measurement records** — every panel run emits a
   `.jsonl` file under the (gitignored) runs directory. Line 1 is the
   schema marker `{"schema_version": "1"}`; subsequent lines carry one
   record per request (see `megalos_panel/record.py` for the field list).
   These records are the audit artifact for measurement slices: an
   external reviewer can reproduce a slice's selection counts from the
   raw provider responses without re-running the panel.

The three mechanisms are complementary. The per-PR gate cannot verify
behavioral retry semantics (no live traffic); the nightly cron cannot
block a PR (too slow, secret-bound); the measurement records are
after-the-fact evidence, not a gate at all. Treating them as one layer
would either over-block PRs or under-validate behavior.

## Hermeticity invariants

Two tests enforce the module boundary structurally; both live under
`tests/`:

- `tests/test_panel_adapters_hermeticity.py` — importing
  `megalos_panel.adapters` (the package, not a specific adapter module)
  must not transitively load `anthropic` or `openai`. Runs in a
  subprocess because the main pytest suite has SDKs in `sys.modules`
  already. Backed by decision `D019`.
- `tests/test_import_hermeticity.py` — extended beyond the original
  "server import doesn't create a DB file" check to also assert (a) no
  `megalos_server/*.py` imports `megalos_panel`, and (b) no `test_*.py`
  file mixes imports from both, with the exception that `test_panel_*.py`
  may import `megalos_panel` but must not import `megalos_server`.

Both tests are cheap, run on every PR, and keep the module boundary as a
build-time guarantee rather than a convention.
