"""Synthetic workflow-selection fixture generator — single-model authorship.

Purpose
-------

Sibling of ``tests.selection.generate_synthetic`` (the cross-model generator
kept on disk as archived institutional memory from the D014 era). This
module implements the single-model authoring protocol adopted in D026: one
panel model authors each candidate pair in a single ``panel_query`` round,
with no propose/filter split. Default authoring model is
``groq/llama-3.3-70b-versatile`` (D026), but the generator itself is
provider-agnostic — the operator may pass any model string registered in
``megalos_panel.adapters`` via ``--authoring-model``.

Both the **dry-run** plan and the **live-execution** code path live here.
Live mode is gated behind ``--commit``; ``--dry-run`` keeps its
byte-identical plan output. Live mode writes fixtures + metadata sidecars
under ``runs/<run_id>/synthetic/`` (gitignored) alongside the
``RecordWriter`` JSONL trace; promotion into committed fixture paths is
the downstream live-run task's job.

Contract tie-in
---------------

Prompt text, prompt-template version, valid-band set, and band parsing
are imported from the cross-model generator module. That keeps both
generators on the same prompt revision so comparisons stay honest, and
avoids the drift trap of two prompt copies. Panel calls flow through
``megalos_panel.panel_query`` with ``PanelRequest`` instances; adapters
are never imported here. Tests pin the mock to the public surface via
``unittest.mock.create_autospec(panel_query)``.

The dry-run plan header keys mirror the cross-model generator's header
exactly so the downstream concordance-gate parser can read either
generator's output without special-casing. Per-batch lines carry
``authoring_model=<model>`` in place of the cross-model ``proposer=... filter=...``
field pair; every other header field is byte-compatible.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

import yaml

from megalos_panel import PanelRequest, RecordWriter, panel_query
from tests.selection.generate_synthetic import (
    PROMPT_TEMPLATE_VERSION,
    SYNTHETIC_GENERATOR_PROMPTS,
    VALID_BANDS,
    _expand_bands,
)

# Default authoring model per D026. The ``groq/`` prefix routes through
# the GroqAdapter registered in ``megalos_panel.adapters``. Overridable
# via ``--authoring-model`` — the generator itself is prefix-agnostic.
DEFAULT_AUTHORING_MODEL = "groq/llama-3.3-70b-versatile"

# Number of candidate pairs requested per panel_query batch. Matches
# the cross-model generator so batch arithmetic is identical.
PAIRS_PER_BATCH = 5


SCOPE_ERROR = (
    "Scope error: live generation requires provider keys and is the "
    "live-run task's responsibility. Use --dry-run to verify the code "
    "path, or dispatch the live-run task for live execution."
)


# Appended to each band prompt at call time. Kept as a module-level
# constant so tests can pin the exact augmentation and so T04a's prompt
# dict is never edited in place. Phrased to be tolerant of LLM tics:
# asks for bare JSON, but the parser strips ``` fences anyway.
JSON_OUTPUT_INSTRUCTION = (
    "\n\nReturn ONLY a valid JSON object matching this exact schema: "
    '{"description_A": "...", "description_B": "..."}. '
    "No prose outside the JSON object. No markdown code fences."
)


# Missing-pair marker returned by the parser on any failure mode. Two
# None entries lets callers unpack the tuple unconditionally; truthiness
# of either element flags the failure.
PARSE_FAILURE: tuple[None, None] = (None, None)


@dataclass(frozen=True)
class BatchPlan:
    """One batch of ``PAIRS_PER_BATCH`` candidate pairs for a single band.

    Single-model variant: one ``panel_query`` call per batch against
    ``authoring_model``, producing ``pairs`` candidate pairs. No filter
    round — the operator-authored anchors (T02) remain the scoring
    ground truth.
    """

    band: int
    batch_index: int
    pairs: int
    authoring_model: str
    authoring_prompt: str


def _plan_batches(
    bands: list[int], n_per_band: int, authoring_model: str
) -> list[BatchPlan]:
    """Expand (bands, n_per_band) into an ordered list of BatchPlan entries.

    Deterministic and seed-independent: single-model authorship has no
    role alternation to randomize. ``seed`` is still accepted at the CLI
    for symmetry with the cross-model generator and for future use (e.g.
    shuffling prompt variants) but does not affect the plan today.
    """
    planned: list[BatchPlan] = []
    global_batch_index = 0
    for band in bands:
        remaining = n_per_band
        while remaining > 0:
            size = min(PAIRS_PER_BATCH, remaining)
            planned.append(
                BatchPlan(
                    band=band,
                    batch_index=global_batch_index,
                    pairs=size,
                    authoring_model=authoring_model,
                    authoring_prompt=SYNTHETIC_GENERATOR_PROMPTS[band],
                )
            )
            remaining -= size
            global_batch_index += 1
    return planned


def _render_dry_run_plan(
    batches: list[BatchPlan],
    *,
    n_per_band: int,
    bands: list[int],
    seed: int,
    run_id: str | None,
    authoring_model: str,
    out: TextIO,
) -> None:
    """Print the execution plan in a shape compatible with the cross-model
    generator's output. Header keys match byte-for-byte so the downstream
    parser can read either generator's dry-run output without branching.
    Per-batch lines carry ``authoring_model`` in place of the cross-model
    ``proposer``/``filter`` pair.
    """
    total_calls = len(batches)  # one call per batch in the single-model path
    total_requests = sum(b.pairs for b in batches)
    print(f"prompt_template_version: {PROMPT_TEMPLATE_VERSION}", file=out)
    print(f"run_id: {run_id or '<unset>'}", file=out)
    print(f"seed: {seed}", file=out)
    print(f"bands: {bands}", file=out)
    print(f"n_per_band: {n_per_band}", file=out)
    print(f"authoring_model: {authoring_model}", file=out)
    print(f"total_batches: {len(batches)}", file=out)
    print(f"total_panel_query_calls: {total_calls}", file=out)
    print(f"total_panel_requests: {total_requests}", file=out)
    print(f"pairs_per_batch: {PAIRS_PER_BATCH}", file=out)
    print("", file=out)
    for batch in batches:
        print(
            f"batch {batch.batch_index}: band={batch.band} pairs={batch.pairs} "
            f"authoring_model={batch.authoring_model}",
            file=out,
        )
        print(f"  authoring_prompt: {batch.authoring_prompt}", file=out)


def parse_pair_response(raw: str) -> tuple[str | None, str | None]:
    """Parse a single panel response into a ``(description_A, description_B)``
    tuple, tolerating the common LLM output-format artefacts.

    Strategy: strip whitespace, strip optional ```json ... ``` or ``` ... ```
    fences, ``json.loads``, check for both required keys. Any failure mode
    returns ``PARSE_FAILURE`` (``(None, None)``) — callers surface the
    count in the completion report rather than aborting the batch.
    """
    if raw is None:
        return PARSE_FAILURE
    text = raw.strip()
    if not text:
        return PARSE_FAILURE
    if text.startswith("```"):
        # Drop the opening fence line (``` or ```json) and trailing fence.
        lines = text.splitlines()
        # First line is the opening fence; last line (if it's a closing
        # fence) is dropped. Be defensive: the closing fence may be
        # absent on truncated responses.
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text:
        return PARSE_FAILURE
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return PARSE_FAILURE
    if not isinstance(obj, dict):
        return PARSE_FAILURE
    a = obj.get("description_A")
    b = obj.get("description_B")
    if not isinstance(a, str) or not isinstance(b, str):
        return PARSE_FAILURE
    return a, b


def _groq_model_id_at_runtime(authoring_model: str) -> str:
    """Best-effort resolution of the provider-side model identifier.

    For this task we stub this as the authoring-model string with the
    ``groq/`` prefix (if present) stripped — that is what the GroqAdapter
    sends to the API. The live-run task may override this with the
    resolved ID read back from Groq's response payload once that field is
    surfaced in ``PanelResult``.
    """
    if authoring_model.startswith("groq/"):
        return authoring_model[len("groq/") :]
    return authoring_model


def _write_fixture_yaml(path: Path, pairs: list[dict]) -> None:
    """Write the per-band fixture YAML. Top-level key is ``pairs`` per the
    T04b contract; each entry carries pair_id, band, both descriptions,
    authoring_model, prompt_template_version, and the raw_response_id
    pointing into the panel-record JSONL file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump({"pairs": pairs}, fh, sort_keys=False)


def _write_sidecar_yaml(path: Path, sidecar: dict) -> None:
    """Write the per-band metadata sidecar YAML. Field order follows the
    contract in the T04e plan: authoring_model, groq_model_id_at_runtime,
    generation_date, prompt_template_version, generator_seed, run_id,
    n_authored, n_parse_failures, panel_record_path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(sidecar, fh, sort_keys=False)


def _print_completion_report(
    *,
    bands: list[int],
    n_per_band: int,
    totals_by_band: dict[int, dict[str, int]],
    staging_dir: Path,
    panel_record_path: Path | None,
    out: TextIO,
) -> None:
    """Emit a plain-text run summary to stdout for the live-run task and
    the operator. No YAML — just counts per band, totals, and where the
    artefacts landed.
    """
    total_requested = len(bands) * n_per_band
    total_ok = sum(v["ok"] for v in totals_by_band.values())
    total_fail = sum(v["fail"] for v in totals_by_band.values())
    print("=== live-run completion report ===", file=out)
    print(f"bands: {bands}", file=out)
    print(f"n_per_band: {n_per_band}", file=out)
    print(f"total_pairs_requested: {total_requested}", file=out)
    print(f"total_parse_ok: {total_ok}", file=out)
    print(f"total_parse_failures: {total_fail}", file=out)
    for band in bands:
        counts = totals_by_band.get(band, {"ok": 0, "fail": 0})
        print(
            f"  band {band}: parse_ok={counts['ok']} parse_failures={counts['fail']}",
            file=out,
        )
    print(f"staging_dir: {staging_dir}", file=out)
    print(
        f"panel_record_path: {panel_record_path if panel_record_path else '<none>'}",
        file=out,
    )


def _run_live(
    batches: list[BatchPlan],
    *,
    bands: list[int],
    n_per_band: int,
    seed: int,
    run_id: str,
    authoring_model: str,
    out: TextIO,
) -> int:
    """Execute all planned batches against ``panel_query``, parse results,
    and stage fixture + sidecar YAML per band under
    ``runs/<run_id>/synthetic/``. Prints a completion report at the end.

    Parse failures are counted, never raised: the operator sees them in
    the report and in the metadata sidecar's ``n_parse_failures`` field.
    """
    staging_dir = Path("runs") / run_id / "synthetic"
    staging_dir.mkdir(parents=True, exist_ok=True)
    run_record_dir = Path("runs") / run_id / "records"

    # Collect parsed pairs per band; counts accumulate across batches.
    pairs_by_band: dict[int, list[dict]] = {b: [] for b in bands}
    counts_by_band: dict[int, dict[str, int]] = {
        b: {"ok": 0, "fail": 0} for b in bands
    }

    panel_record_path: Path | None = None
    generation_date = datetime.now(timezone.utc).isoformat()

    with RecordWriter(run_record_dir) as writer:
        panel_record_path = writer.path
        for batch in batches:
            augmented_prompt = (
                SYNTHETIC_GENERATOR_PROMPTS[batch.band] + JSON_OUTPUT_INSTRUCTION
            )
            requests = [
                PanelRequest(prompt=augmented_prompt, model=batch.authoring_model)
                for _ in range(batch.pairs)
            ]
            results = panel_query(requests, record_writer=writer)
            for req in requests:
                result = results[req.request_id]
                raw = result.raw_response if result.error is None else ""
                desc_a, desc_b = parse_pair_response(raw)
                if desc_a is None or desc_b is None:
                    counts_by_band[batch.band]["fail"] += 1
                    continue
                pair_index = len(pairs_by_band[batch.band])
                pairs_by_band[batch.band].append(
                    {
                        "pair_id": f"band{batch.band}-{pair_index:03d}",
                        "band": batch.band,
                        "description_A": desc_a,
                        "description_B": desc_b,
                        "authoring_model": batch.authoring_model,
                        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                        "raw_response_id": req.request_id,
                    }
                )
                counts_by_band[batch.band]["ok"] += 1

    groq_model_id = _groq_model_id_at_runtime(authoring_model)

    for band in bands:
        fixture_path = staging_dir / f"band_{band}.yaml"
        sidecar_path = staging_dir / f"band_{band}.meta.yaml"
        _write_fixture_yaml(fixture_path, pairs_by_band[band])
        _write_sidecar_yaml(
            sidecar_path,
            {
                "authoring_model": authoring_model,
                "groq_model_id_at_runtime": groq_model_id,
                "generation_date": generation_date,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                "generator_seed": seed,
                "run_id": run_id,
                "n_authored": counts_by_band[band]["ok"],
                "n_parse_failures": counts_by_band[band]["fail"],
                "panel_record_path": (
                    str(panel_record_path) if panel_record_path else ""
                ),
            },
        )

    _print_completion_report(
        bands=bands,
        n_per_band=n_per_band,
        totals_by_band=counts_by_band,
        staging_dir=staging_dir,
        panel_record_path=panel_record_path,
        out=out,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_synthetic_groq",
        description=(
            "Author synthetic workflow-selection pairs under the "
            "single-model authoring protocol. --dry-run prints the plan; "
            "--commit runs panel_query live and stages fixtures."
        ),
    )
    parser.add_argument(
        "--band",
        default="all",
        help="Closeness band: 1, 2, 3, or 'all' (default: all).",
    )
    parser.add_argument(
        "--n-per-band",
        type=int,
        default=20,
        help="Number of pairs to author per band (default: 20).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the execution plan without invoking panel_query.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help=(
            "Run panel_query live and stage fixtures under "
            "runs/<run_id>/synthetic/. Requires provider keys."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Reserved for future use; recorded in the plan header (default: 0).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run identifier recorded in the plan header.",
    )
    parser.add_argument(
        "--authoring-model",
        default=DEFAULT_AUTHORING_MODEL,
        help=(
            "Panel model string used to author each candidate pair "
            f"(default: {DEFAULT_AUTHORING_MODEL}). Any prefix registered "
            "in megalos_panel.adapters is accepted."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    ``argv`` defaults to ``sys.argv[1:]`` when omitted so the tests can
    drive the parser without spawning subprocesses.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.n_per_band <= 0:
        parser.error("--n-per-band must be positive")

    try:
        bands = _expand_bands(args.band)
    except ValueError as exc:
        parser.error(str(exc))

    # Anchor the shared import so static analyzers don't mark it unused
    # and so the read is visible in coverage on the dry-run path.
    _ = VALID_BANDS

    if args.dry_run:
        batches = _plan_batches(bands, args.n_per_band, args.authoring_model)
        _render_dry_run_plan(
            batches,
            n_per_band=args.n_per_band,
            bands=bands,
            seed=args.seed,
            run_id=args.run_id,
            authoring_model=args.authoring_model,
            out=sys.stdout,
        )
        return 0

    if not args.commit:
        # Default path when neither --dry-run nor --commit is given:
        # refuse with a scoped error rather than silently running live.
        print(SCOPE_ERROR, file=sys.stderr)
        return 2

    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        "synthetic-%Y%m%dT%H%M%SZ"
    )
    batches = _plan_batches(bands, args.n_per_band, args.authoring_model)
    return _run_live(
        batches,
        bands=bands,
        n_per_band=args.n_per_band,
        seed=args.seed,
        run_id=run_id,
        authoring_model=args.authoring_model,
        out=sys.stdout,
    )


if __name__ == "__main__":  # pragma: no cover - CLI dispatch
    raise SystemExit(main())
