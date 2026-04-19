"""Unit tests for the single-model synthetic workflow-selection generator CLI.

Mirrors the structure of ``test_generate_synthetic.py`` but scoped to the
single-model authoring path (D026). Cross-model-specific tests (role
alternation, filter round) have no analog here and are intentionally
absent. All tests drive ``tests.selection.generate_synthetic_groq.main``
directly — no subprocess — so we can capture stdout/stderr via ``capsys``
and mock ``panel_query`` via ``unittest.mock.create_autospec`` per D016.
"""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest  # type: ignore[import-not-found]

from megalos_panel import panel_query
from tests.selection import generate_synthetic_groq
from tests.selection.generate_synthetic import (
    PROMPT_TEMPLATE_VERSION,
    SYNTHETIC_GENERATOR_PROMPTS,
)
from tests.selection.generate_synthetic_groq import (
    DEFAULT_AUTHORING_MODEL,
    JSON_OUTPUT_INSTRUCTION,
    PAIRS_PER_BATCH,
    PARSE_FAILURE,
    SCOPE_ERROR,
    _groq_model_id_at_runtime,
    _write_fixture_yaml,
    _write_sidecar_yaml,
    main,
    parse_pair_response,
)


# --- dry-run plan shape ---------------------------------------------------


def test_dry_run_all_bands_prints_full_plan(capsys):
    exit_code = main(
        ["--dry-run", "--band", "all", "--n-per-band", "20", "--seed", "42"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out

    # Header lines are present verbatim and byte-compatible with the
    # cross-model generator's header (minus the added authoring_model line).
    assert f"prompt_template_version: {PROMPT_TEMPLATE_VERSION}" in out
    assert "seed: 42" in out
    assert "bands: [1, 2, 3]" in out
    assert "n_per_band: 20" in out
    assert f"authoring_model: {DEFAULT_AUTHORING_MODEL}" in out

    # 20 pairs * 3 bands / 5 per batch = 12 batches. Single-model path:
    # one panel_query call per batch = 12 calls, 60 total PanelRequests
    # (no filter round).
    assert "total_batches: 12" in out
    assert "total_panel_query_calls: 12" in out
    assert "total_panel_requests: 60" in out
    assert f"pairs_per_batch: {PAIRS_PER_BATCH}" in out


def test_dry_run_single_band_limits_plan(capsys):
    exit_code = main(
        ["--dry-run", "--band", "1", "--n-per-band", "5", "--seed", "0"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "bands: [1]" in out
    # 5 pairs fits in one batch; one panel_query call total.
    assert "total_batches: 1" in out
    assert "total_panel_query_calls: 1" in out


# --- authoring-model surface ---------------------------------------------


def test_default_authoring_model_is_groq_llama_70b(capsys):
    main(["--dry-run", "--band", "1", "--n-per-band", "5"])
    out = capsys.readouterr().out
    assert "authoring_model: groq/llama-3.3-70b-versatile" in out
    # Per-batch line carries it too.
    assert "authoring_model=groq/llama-3.3-70b-versatile" in out


def test_custom_authoring_model_passes_through_unchanged(capsys):
    # Forward-compat: any model string registered in megalos_panel.adapters
    # should pass through. The generator must not special-case the groq/
    # prefix.
    main(
        [
            "--dry-run",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--authoring-model",
            "claude-opus-4-7",
        ]
    )
    out = capsys.readouterr().out
    assert "authoring_model: claude-opus-4-7" in out
    assert "authoring_model=claude-opus-4-7" in out


def test_non_groq_prefixed_model_accepted(capsys):
    # The generator is prefix-agnostic; strings without groq/ still work.
    main(
        [
            "--dry-run",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--authoring-model",
            "gpt-4o",
        ]
    )
    out = capsys.readouterr().out
    assert "authoring_model: gpt-4o" in out


# --- band-specific prompt phrasing (inherited from cross-model module) ----


def test_band1_prompt_contains_multi_marker_directive(capsys):
    main(["--dry-run", "--band", "1", "--n-per-band", "5"])
    out = capsys.readouterr().out
    assert "Band 1" in out
    assert "multiple markers" in out


def test_band2_prompt_contains_few_marker_directive(capsys):
    main(["--dry-run", "--band", "2", "--n-per-band", "5"])
    out = capsys.readouterr().out
    assert "Band 2" in out
    assert "few markers distinguish" in out


def test_band3_prompt_contains_one_minimal_marker_directive(capsys):
    main(["--dry-run", "--band", "3", "--n-per-band", "5"])
    out = capsys.readouterr().out
    assert "Band 3" in out
    assert "single minimal marker" in out


def test_prompts_imported_cover_every_band():
    # The module reuses SYNTHETIC_GENERATOR_PROMPTS by import, so this
    # pins the contract at the shared surface.
    assert set(SYNTHETIC_GENERATOR_PROMPTS.keys()) == {1, 2, 3}


# --- error paths ---------------------------------------------------------


def test_unknown_band_exits_nonzero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--dry-run", "--band", "4", "--n-per-band", "5"])
    assert excinfo.value.code != 0
    err = capsys.readouterr().err
    assert "unknown band" in err


def test_live_mode_refuses_with_scope_error(capsys):
    exit_code = main(["--band", "all", "--n-per-band", "20"])
    assert exit_code != 0
    err = capsys.readouterr().err
    assert SCOPE_ERROR in err
    assert "live generation requires" in err


def test_live_mode_does_not_invoke_panel_query(monkeypatch, capsys):
    # Belt-and-braces: even on the scope-error path, no panel_query call
    # must escape. Pin via autospec so a signature drift would fail fast.
    mock = create_autospec(panel_query)
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", mock)
    exit_code = main(["--band", "all", "--n-per-band", "20"])
    assert exit_code != 0
    assert mock.call_count == 0


def test_non_positive_n_per_band_rejected(capsys):
    with pytest.raises(SystemExit):
        main(["--dry-run", "--band", "all", "--n-per-band", "0"])


def test_negative_n_per_band_rejected(capsys):
    with pytest.raises(SystemExit):
        main(["--dry-run", "--band", "all", "--n-per-band", "-1"])


# --- determinism ---------------------------------------------------------


def test_dry_run_output_is_deterministic(capsys):
    main(["--dry-run", "--band", "all", "--n-per-band", "10", "--seed", "42"])
    first = capsys.readouterr().out
    main(["--dry-run", "--band", "all", "--n-per-band", "10", "--seed", "42"])
    second = capsys.readouterr().out
    assert first == second


# --- mock contract (D016): autospec binds to panel_query signature --------


def test_panel_query_autospec_matches_public_signature(monkeypatch):
    """Dry-run does not call panel_query, but when live execution lands
    the test double used by this module's tests must be bound to the real
    signature. Pin that invariant now so drift is caught early."""
    mock = create_autospec(panel_query)
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", mock)
    mock([], record_writer=None, max_workers=8)
    mock.assert_called_once()


def test_dry_run_does_not_invoke_panel_query(monkeypatch):
    mock = create_autospec(panel_query)
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", mock)
    exit_code = main(["--dry-run", "--band", "all", "--n-per-band", "20"])
    assert exit_code == 0
    assert mock.call_count == 0


# --- response-parser tests -----------------------------------------------


def test_parse_pair_response_valid_json():
    raw = '{"description_A": "alpha paragraph", "description_B": "beta paragraph"}'
    assert parse_pair_response(raw) == ("alpha paragraph", "beta paragraph")


def test_parse_pair_response_valid_json_with_surrounding_whitespace():
    raw = '\n\n  {"description_A": "a", "description_B": "b"}  \n'
    assert parse_pair_response(raw) == ("a", "b")


def test_parse_pair_response_json_code_fence_with_language_tag():
    raw = (
        "```json\n"
        '{"description_A": "a", "description_B": "b"}\n'
        "```"
    )
    assert parse_pair_response(raw) == ("a", "b")


def test_parse_pair_response_bare_code_fence():
    raw = (
        "```\n"
        '{"description_A": "a", "description_B": "b"}\n'
        "```"
    )
    assert parse_pair_response(raw) == ("a", "b")


def test_parse_pair_response_unterminated_fence():
    # LLMs sometimes truncate before the closing fence; parser should
    # still strip the opening one and try json.loads.
    raw = (
        "```json\n"
        '{"description_A": "a", "description_B": "b"}'
    )
    assert parse_pair_response(raw) == ("a", "b")


def test_parse_pair_response_malformed_json_returns_failure():
    raw = '{"description_A": "a", "description_B": '
    assert parse_pair_response(raw) == PARSE_FAILURE


def test_parse_pair_response_missing_description_a_returns_failure():
    raw = '{"description_B": "b"}'
    assert parse_pair_response(raw) == PARSE_FAILURE


def test_parse_pair_response_missing_description_b_returns_failure():
    raw = '{"description_A": "a"}'
    assert parse_pair_response(raw) == PARSE_FAILURE


def test_parse_pair_response_non_string_values_return_failure():
    raw = '{"description_A": 1, "description_B": 2}'
    assert parse_pair_response(raw) == PARSE_FAILURE


def test_parse_pair_response_non_dict_top_level_returns_failure():
    raw = '["a", "b"]'
    assert parse_pair_response(raw) == PARSE_FAILURE


def test_parse_pair_response_whitespace_only_returns_failure():
    assert parse_pair_response("   \n\t  ") == PARSE_FAILURE


def test_parse_pair_response_empty_string_returns_failure():
    assert parse_pair_response("") == PARSE_FAILURE


def test_parse_pair_response_does_not_raise_on_any_input():
    # Guard the no-crash invariant explicitly: any string -> tuple, no raise.
    for raw in ("", "not json", "```", "```json\n```", "null", '"just a string"'):
        result = parse_pair_response(raw)
        assert result == PARSE_FAILURE


def test_json_output_instruction_has_required_shape():
    # The augmentation must name both keys and forbid prose so the
    # parser has a prayer of succeeding.
    assert "description_A" in JSON_OUTPUT_INSTRUCTION
    assert "description_B" in JSON_OUTPUT_INSTRUCTION
    assert "JSON" in JSON_OUTPUT_INSTRUCTION


# --- YAML writer tests ----------------------------------------------------


def test_write_fixture_yaml_round_trip(tmp_path):
    import yaml as _yaml

    fixture_path = tmp_path / "band_1.yaml"
    pairs = [
        {
            "pair_id": "band1-000",
            "band": 1,
            "description_A": "alpha",
            "description_B": "beta",
            "authoring_model": "groq/llama-3.3-70b-versatile",
            "prompt_template_version": "generator-v1",
            "raw_response_id": "req-abc",
        }
    ]
    _write_fixture_yaml(fixture_path, pairs)
    loaded = _yaml.safe_load(fixture_path.read_text())
    assert list(loaded.keys()) == ["pairs"]
    assert len(loaded["pairs"]) == 1
    entry = loaded["pairs"][0]
    assert entry["pair_id"] == "band1-000"
    assert entry["band"] == 1
    assert entry["description_A"] == "alpha"
    assert entry["description_B"] == "beta"
    assert entry["authoring_model"] == "groq/llama-3.3-70b-versatile"
    assert entry["prompt_template_version"] == "generator-v1"
    assert entry["raw_response_id"] == "req-abc"


def test_write_fixture_yaml_empty_pairs_list(tmp_path):
    import yaml as _yaml

    fixture_path = tmp_path / "band_2.yaml"
    _write_fixture_yaml(fixture_path, [])
    loaded = _yaml.safe_load(fixture_path.read_text())
    assert loaded == {"pairs": []}


def test_write_fixture_yaml_creates_parent_dirs(tmp_path):
    fixture_path = tmp_path / "nested" / "deep" / "band_3.yaml"
    _write_fixture_yaml(fixture_path, [])
    assert fixture_path.exists()


def test_write_sidecar_yaml_carries_all_required_keys(tmp_path):
    import yaml as _yaml

    sidecar_path = tmp_path / "band_1.meta.yaml"
    sidecar = {
        "authoring_model": "groq/llama-3.3-70b-versatile",
        "groq_model_id_at_runtime": "llama-3.3-70b-versatile",
        "generation_date": "2026-04-19T12:00:00+00:00",
        "prompt_template_version": "generator-v1",
        "generator_seed": 42,
        "run_id": "run-xyz",
        "n_authored": 4,
        "n_parse_failures": 1,
        "panel_record_path": "runs/run-xyz/records/20260419T120000000000Z.jsonl",
    }
    _write_sidecar_yaml(sidecar_path, sidecar)
    loaded = _yaml.safe_load(sidecar_path.read_text())
    required = {
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
    assert required.issubset(loaded.keys())
    assert loaded["n_authored"] == 4
    assert loaded["n_parse_failures"] == 1


# --- groq model id resolver ----------------------------------------------


def test_groq_model_id_strips_groq_prefix():
    assert (
        _groq_model_id_at_runtime("groq/llama-3.3-70b-versatile")
        == "llama-3.3-70b-versatile"
    )


def test_groq_model_id_preserves_nested_openai_prefix():
    # groq/openai/gpt-oss-120b must land at openai/gpt-oss-120b.
    assert (
        _groq_model_id_at_runtime("groq/openai/gpt-oss-120b")
        == "openai/gpt-oss-120b"
    )


def test_groq_model_id_passes_through_non_groq_strings():
    assert _groq_model_id_at_runtime("gpt-4o") == "gpt-4o"


# --- live-mode gating + completion-report tests --------------------------


def _make_panel_query_stub(raw_texts_in_order):
    """Build a ``panel_query``-compatible callable that returns sequential
    raw_response strings across invocations. Tests feed this into
    monkeypatch to drive the live code path without touching the network.
    """
    from megalos_panel import PanelResult

    state = {"i": 0}

    def stub(requests, *, record_writer=None, max_workers=8):
        out = {}
        for req in requests:
            raw = raw_texts_in_order[state["i"] % len(raw_texts_in_order)]
            state["i"] += 1
            out[req.request_id] = PanelResult(
                selection=raw, raw_response=raw, error=None
            )
            if record_writer is not None:
                record_writer.write(
                    {
                        "request_id": req.request_id,
                        "model": req.model,
                        "prompt": req.prompt,
                        "selection": raw,
                        "raw_response": raw,
                        "error": None,
                        "attempts": 1,
                        "elapsed_ms": 1,
                        "timestamp": "2026-04-19T00:00:00+00:00",
                    }
                )
        return out

    return stub


def test_neither_flag_refuses_with_scope_error(capsys):
    exit_code = main(["--band", "1", "--n-per-band", "5"])
    assert exit_code != 0
    err = capsys.readouterr().err
    assert SCOPE_ERROR in err


def test_commit_flag_invokes_panel_query(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    stub = _make_panel_query_stub(
        ['{"description_A": "a", "description_B": "b"}']
    )
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", stub)
    exit_code = main(
        [
            "--commit",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--run-id",
            "unit-run",
        ]
    )
    assert exit_code == 0
    # 5 pairs / band, 1 band -> 1 batch of 5, one panel_query call.
    # Staging fixture must exist and carry 5 pairs.
    fixture_path = tmp_path / "runs" / "unit-run" / "synthetic" / "band_1.yaml"
    assert fixture_path.exists()
    import yaml as _yaml

    loaded = _yaml.safe_load(fixture_path.read_text())
    assert len(loaded["pairs"]) == 5


def test_commit_flag_writes_sidecar_with_counts(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Three pairs parse cleanly, two fail — exercises the counts pathway.
    stub = _make_panel_query_stub(
        [
            '{"description_A": "a", "description_B": "b"}',
            '{"description_A": "a", "description_B": "b"}',
            '{"description_A": "a", "description_B": "b"}',
            "not json",
            "```json\nbroken",
        ]
    )
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", stub)
    exit_code = main(
        [
            "--commit",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--run-id",
            "unit-run-counts",
            "--seed",
            "7",
        ]
    )
    assert exit_code == 0
    sidecar_path = (
        tmp_path / "runs" / "unit-run-counts" / "synthetic" / "band_1.meta.yaml"
    )
    assert sidecar_path.exists()
    import yaml as _yaml

    loaded = _yaml.safe_load(sidecar_path.read_text())
    assert loaded["n_authored"] == 3
    assert loaded["n_parse_failures"] == 2
    assert loaded["generator_seed"] == 7
    assert loaded["run_id"] == "unit-run-counts"
    assert loaded["authoring_model"] == DEFAULT_AUTHORING_MODEL
    assert loaded["groq_model_id_at_runtime"] == "llama-3.3-70b-versatile"
    assert loaded["prompt_template_version"]  # non-empty
    assert loaded["panel_record_path"]  # non-empty
    assert loaded["generation_date"]


def test_commit_flag_completion_report_contains_expected_fields(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    stub = _make_panel_query_stub(
        ['{"description_A": "a", "description_B": "b"}']
    )
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", stub)
    main(
        [
            "--commit",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--run-id",
            "unit-run-report",
        ]
    )
    out = capsys.readouterr().out
    assert "=== live-run completion report ===" in out
    assert "bands: [1]" in out
    assert "n_per_band: 5" in out
    assert "total_pairs_requested: 5" in out
    assert "total_parse_ok: 5" in out
    assert "total_parse_failures: 0" in out
    assert "staging_dir:" in out
    assert "panel_record_path:" in out


def test_commit_flag_panel_query_call_count(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    mock = create_autospec(panel_query)
    from megalos_panel import PanelResult

    def side_effect(requests, *, record_writer=None, max_workers=8):
        return {
            r.request_id: PanelResult(
                selection='{"description_A": "a", "description_B": "b"}',
                raw_response='{"description_A": "a", "description_B": "b"}',
                error=None,
            )
            for r in requests
        }

    mock.side_effect = side_effect
    monkeypatch.setattr(generate_synthetic_groq, "panel_query", mock)
    exit_code = main(
        [
            "--commit",
            "--band",
            "all",
            "--n-per-band",
            "5",
            "--run-id",
            "unit-run-calls",
        ]
    )
    assert exit_code == 0
    # 5 pairs * 3 bands / 5 per batch = 3 batches = 3 panel_query calls.
    assert mock.call_count == 3


def test_commit_flag_with_panel_error_counts_as_parse_failure(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    from megalos_panel import PanelResult

    def stub(requests, *, record_writer=None, max_workers=8):
        # Simulate a provider-exhausted request alongside one success.
        out = {}
        for i, req in enumerate(requests):
            if i == 0:
                out[req.request_id] = PanelResult(
                    selection="", raw_response="", error="exhausted"
                )
            else:
                out[req.request_id] = PanelResult(
                    selection='{"description_A": "a", "description_B": "b"}',
                    raw_response='{"description_A": "a", "description_B": "b"}',
                    error=None,
                )
        return out

    monkeypatch.setattr(generate_synthetic_groq, "panel_query", stub)
    exit_code = main(
        [
            "--commit",
            "--band",
            "1",
            "--n-per-band",
            "5",
            "--run-id",
            "unit-run-errors",
        ]
    )
    assert exit_code == 0
    sidecar_path = (
        tmp_path / "runs" / "unit-run-errors" / "synthetic" / "band_1.meta.yaml"
    )
    import yaml as _yaml

    loaded = _yaml.safe_load(sidecar_path.read_text())
    assert loaded["n_authored"] == 4
    assert loaded["n_parse_failures"] == 1
