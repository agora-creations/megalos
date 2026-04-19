"""Live integration test for the single-model synthetic generator.

This test actually calls Groq. It is tagged ``@pytest.mark.live`` and
therefore skipped in the default ``pytest`` run (``addopts = "-m 'not live'"``
in ``pyproject.toml``). Run it manually when a ``GROQ_API_KEY`` is
available and a minimal live smoke check is wanted:

    uv run pytest tests/selection/test_generate_synthetic_groq_live.py -m live

The test uses ``groq/llama-3.1-8b-instant`` — the cheapest/fastest model in
the D026 panel — and requests a single pair for Band 1 only. Total cost
per run is a few hundred tokens. The authoring-model choice is intentional:
a smoke test should exercise the gating + writer machinery, not the
concordance envelope.
"""

from __future__ import annotations

import os
import random
import string

import pytest  # type: ignore[import-not-found]

import yaml

from tests.selection.generate_synthetic_groq import main


@pytest.mark.live
def test_generate_synthetic_groq_live_smoke(tmp_path, monkeypatch):
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set; skipping live smoke test")

    monkeypatch.chdir(tmp_path)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    run_id = f"test_live_{suffix}"

    exit_code = main(
        [
            "--commit",
            "--band",
            "1",
            "--n-per-band",
            "1",
            "--run-id",
            run_id,
            "--authoring-model",
            "groq/llama-3.1-8b-instant",
        ]
    )
    assert exit_code == 0

    staging_dir = tmp_path / "runs" / run_id / "synthetic"
    fixture_path = staging_dir / "band_1.yaml"
    sidecar_path = staging_dir / "band_1.meta.yaml"
    assert fixture_path.exists()
    assert sidecar_path.exists()

    sidecar = yaml.safe_load(sidecar_path.read_text())
    required_keys = {
        "authoring_model",
        "groq_model_id_at_runtime",
        "generation_date",
        "prompt_template_version",
        "generator_seed",
        "run_id",
        "n_authored",
        "n_parse_failures",
        "panel_record_path",
    }
    assert required_keys.issubset(sidecar.keys())
    assert sidecar["run_id"] == run_id
    assert sidecar["authoring_model"] == "groq/llama-3.1-8b-instant"

    records_dir = tmp_path / "runs" / run_id / "records"
    assert records_dir.exists()
    jsonl_files = list(records_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    # At least the schema-version line + one request line.
    lines = jsonl_files[0].read_text().splitlines()
    assert len(lines) >= 2
