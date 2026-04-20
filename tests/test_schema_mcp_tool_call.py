"""Tests for the `mcp_tool_call` step type: load-time validation + registry cross-check."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from megalos_server.mcp_registry import Registry, ServerConfig, AuthConfig
from megalos_server.schema import validate_workflow


# --- Fixtures --------------------------------------------------------------


def _registry(*names: str) -> Registry:
    servers = {
        n: ServerConfig(
            name=n,
            url=f"https://{n}.example.com",
            transport="http",
            auth=AuthConfig(type="bearer", token_env=f"{n.upper()}_TOKEN"),
        )
        for n in names
    }
    return Registry(servers=servers)


def _write(yaml_str: str, tmp_path: Path | None = None) -> str:
    if tmp_path is None:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        Path(path).write_text(yaml_str)
        return path
    p = tmp_path / "wf.yaml"
    p.write_text(yaml_str)
    return str(p)


def _validate(yaml_str: str, registry: Registry | None = None) -> list[str]:
    path = _write(yaml_str)
    try:
        errors, _ = validate_workflow(path, registry=registry)
        return errors
    finally:
        os.unlink(path)


# --- Happy paths -----------------------------------------------------------


def test_mcp_tool_call_scalar_args_passes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      city: Paris
      units: metric
      count: 3
      verbose: true
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


def test_mcp_tool_call_nested_object_and_list_args_passes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      filters:
        region: eu
        cities: [Paris, Lyon]
      options:
        - key: x
          value: 1
        - key: y
          value: 2
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


def test_mcp_tool_call_ref_path_arg_passes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: ask
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      city: "${step_data.intake.city}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


def test_mcp_tool_call_ref_path_nested_passes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: ask
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      items:
        - name: first
          ref: "${step_data.intake.first}"
        - name: second
          ref: "${step_data.intake.second}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


def test_mcp_tool_call_timeout_int_and_float_pass():
    for timeout_val in ("5", "1.5"):
        yaml_str = f"""\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {{city: Paris}}
    timeout: {timeout_val}
"""
        errors = _validate(yaml_str, registry=_registry("weather"))
        assert errors == [], errors


def test_mcp_tool_call_with_precondition_and_branches_composes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: ask
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {city: Paris}
    precondition:
      when_present: step_data.intake
    branches:
      - next: done
        condition: ok
    default_branch: done
  - id: done
    title: Done
    directive_template: d
    gates: [done]
    anti_patterns: [none]
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


# --- Mutex violations ------------------------------------------------------


@pytest.mark.parametrize(
    "mutex_field,mutex_value,expected_code",
    [
        ("directive_template", '"prompt"', "mcp_tool_call_with_directive_template"),
        ("gates", "[done]", "mcp_tool_call_with_gates"),
        ("anti_patterns", "[none]", "mcp_tool_call_with_anti_patterns"),
        ("call", "child_wf", "mcp_tool_call_with_call"),
        ("collect", "true", "mcp_tool_call_with_collect"),
        (
            "output_schema",
            "{type: object, properties: {a: {type: string}}}",
            "mcp_tool_call_with_output_schema",
        ),
    ],
)
def test_mcp_tool_call_mutex_fields_rejected(
    mutex_field: str, mutex_value: str, expected_code: str
):
    yaml_str = f"""\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {{city: Paris}}
    {mutex_field}: {mutex_value}
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any(expected_code in e for e in errors), errors


# --- Literal-only checks ---------------------------------------------------


def test_mcp_tool_call_server_interpolation_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: d
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: "${step_data.intake.srv}"
    tool: get_forecast
    args: {}
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("mcp_tool_call_server_not_literal" in e for e in errors), errors


def test_mcp_tool_call_tool_interpolation_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: d
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: "${step_data.intake.t}"
    args: {}
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("mcp_tool_call_tool_not_literal" in e for e in errors), errors


# --- Mixed interpolation ---------------------------------------------------


def test_mcp_tool_call_mixed_interpolation_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: d
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      greeting: "hello ${step_data.intake.name}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any(
        "mcp_tool_call_mixed_interpolation_not_supported" in e for e in errors
    ), errors


def test_mcp_tool_call_suffix_after_ref_rejected():
    # explicitly validates the "${step_data.x} suffix" corner
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: intake
    title: Intake
    directive_template: d
    gates: [done]
    anti_patterns: [none]
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      field: "${step_data.intake.x} extra"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any(
        "mcp_tool_call_mixed_interpolation_not_supported" in e for e in errors
    ), errors


def test_mcp_tool_call_pure_literal_no_dollar_brace_passes():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      note: "no refs here"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert errors == [], errors


# --- Malformed ref-paths ---------------------------------------------------


def test_mcp_tool_call_ref_path_missing_step_data_prefix_rejected():
    # A `${...}`-wrapped string whose inner path doesn't begin with `step_data.`
    # doesn't match the ref-path regex, so it trips the mixed-interpolation
    # check (the regex is the single source of truth for "looks like a ref-path").
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      city: "${foo.bar}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any(
        "mcp_tool_call_mixed_interpolation_not_supported" in e for e in errors
    ), errors


def test_mcp_tool_call_ref_path_with_invalid_segment_rejected():
    # This one DOES match the outer regex but has an illegal segment inside,
    # so it trips the ref-path grammar check.
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      city: "${step_data..dup}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("mcp_tool_call_invalid_ref_path" in e for e in errors), errors


def test_mcp_tool_call_malformed_ref_nested_list_reports_location():
    # ref lives inside args.options[1].ref — location string must include that path.
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args:
      options:
        - ref: "${step_data.intake.ok}"
        - ref: "${notastep.bar}"
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    matching = [e for e in errors if "mcp_tool_call_mixed_interpolation_not_supported" in e
                or "mcp_tool_call_invalid_ref_path" in e]
    assert matching, errors
    assert any(".options[1].ref" in e for e in matching), matching


# --- Registry cross-check --------------------------------------------------


def test_mcp_tool_call_unknown_server_rejected_with_available_names():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: nonexistent
    tool: get_forecast
    args: {}
"""
    errors = _validate(yaml_str, registry=_registry("weather", "news"))
    matching = [e for e in errors if "mcp_tool_call_unknown_server" in e]
    assert matching, errors
    assert any("nonexistent" in e for e in matching), matching
    assert any("weather" in e and "news" in e for e in matching), matching


def test_mcp_tool_call_registry_absent_with_mcp_step_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {}
"""
    errors = _validate(yaml_str, registry=None)
    assert any("mcp_tool_call_registry_required" in e for e in errors), errors


def test_workflow_without_mcp_steps_passes_without_registry():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Plain
    directive_template: d
    gates: [done]
    anti_patterns: [none]
"""
    errors = _validate(yaml_str, registry=None)
    assert errors == [], errors


# --- timeout ---------------------------------------------------------------


def test_mcp_tool_call_timeout_bool_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {}
    timeout: true
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("timeout must be a number" in e for e in errors), errors


def test_mcp_tool_call_timeout_non_positive_rejected():
    for bad in ("0", "-1"):
        yaml_str = f"""\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {{}}
    timeout: {bad}
"""
        errors = _validate(yaml_str, registry=_registry("weather"))
        assert any("timeout must be positive" in e for e in errors), errors


# --- Missing / bad shape ---------------------------------------------------


def test_mcp_tool_call_missing_server_and_tool_and_args_all_reported():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("missing required key 'server'" in e for e in errors), errors
    assert any("missing required key 'tool'" in e for e in errors), errors
    assert any("missing required key 'args'" in e for e in errors), errors


def test_mcp_tool_call_args_non_mapping_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: [1, 2, 3]
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("args must be a mapping" in e for e in errors), errors


def test_mcp_tool_call_unknown_field_rejected():
    yaml_str = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {}
    typo_field: 42
"""
    errors = _validate(yaml_str, registry=_registry("weather"))
    assert any("unknown field" in e for e in errors), errors


# --- CLI tests -------------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    # Strip pytest-cov's subprocess hooks. chdir-based tests otherwise cause
    # coverage files to be written into transient tmp dirs with inconsistent
    # branch-mode settings, which trips combine_parallel_data on teardown.
    env = dict(os.environ)
    for k in ("COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE",
              "COV_CORE_BRANCH", "COV_CORE_CONTEXT"):
        env.pop(k, None)
    return subprocess.run(
        [sys.executable, "-m", "megalos_server.validate", *args],
        capture_output=True,
        text=True,
        env=env,
    )


_WF_WITH_MCP = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Fetch
    action: mcp_tool_call
    server: weather
    tool: get_forecast
    args: {}
"""

_WF_NO_MCP = """\
name: wf
description: ""
category: t
output_format: text
steps:
  - id: s1
    title: Plain
    directive_template: d
    gates: [done]
    anti_patterns: [none]
"""

_REGISTRY_YAML = """\
servers:
  - name: weather
    url: https://weather.example.com
    transport: http
    auth:
      type: bearer
      token_env: WEATHER_TOKEN
"""


def test_cli_with_registry_flag_validates(tmp_path):
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_WITH_MCP)
    reg = tmp_path / "registry.yaml"
    reg.write_text(_REGISTRY_YAML)
    res = _run_cli(str(wf), "--registry", str(reg))
    assert res.returncode == 0, res.stderr
    assert "Valid." in res.stdout


def test_cli_registry_next_to_workflow_picked_up(tmp_path):
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_WITH_MCP)
    (tmp_path / "mcp_servers.yaml").write_text(_REGISTRY_YAML)
    res = _run_cli(str(wf))
    assert res.returncode == 0, res.stderr


def test_cli_registry_cwd_fallback(tmp_path, monkeypatch):
    wf_dir = tmp_path / "wf_dir"
    wf_dir.mkdir()
    wf = wf_dir / "wf.yaml"
    wf.write_text(_WF_WITH_MCP)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "mcp_servers.yaml").write_text(_REGISTRY_YAML)
    monkeypatch.chdir(cwd)
    res = _run_cli(str(wf))
    assert res.returncode == 0, res.stderr


def test_cli_no_registry_mcp_step_errors(tmp_path, monkeypatch):
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_WITH_MCP)
    # chdir somewhere with no mcp_servers.yaml
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    res = _run_cli(str(wf))
    assert res.returncode == 1
    assert "mcp_tool_call_registry_required" in res.stderr


def test_cli_workflow_without_mcp_validates_without_registry(tmp_path, monkeypatch):
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_NO_MCP)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    res = _run_cli(str(wf))
    assert res.returncode == 0, res.stderr


def test_cli_malformed_registry_file_fails_fast(tmp_path):
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_WITH_MCP)
    bad_reg = tmp_path / "bad.yaml"
    bad_reg.write_text("servers:\n  - name: weather\n    url: https://x\n")  # missing transport + auth
    res = _run_cli(str(wf), "--registry", str(bad_reg))
    assert res.returncode == 1
    assert "ERROR" in res.stderr


# --- In-process coverage of the discovery helper ---------------------------


def test_discover_registry_picks_next_to_workflow(tmp_path, monkeypatch):
    from megalos_server.validate import _discover_registry
    wf = tmp_path / "wf.yaml"
    wf.write_text(_WF_NO_MCP)
    (tmp_path / "mcp_servers.yaml").write_text(_REGISTRY_YAML)
    assert _discover_registry(str(wf)) == tmp_path / "mcp_servers.yaml"


def test_discover_registry_falls_back_to_cwd(tmp_path, monkeypatch):
    from megalos_server.validate import _discover_registry
    wf_dir = tmp_path / "wf_dir"
    wf_dir.mkdir()
    wf = wf_dir / "wf.yaml"
    wf.write_text(_WF_NO_MCP)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "mcp_servers.yaml").write_text(_REGISTRY_YAML)
    monkeypatch.chdir(cwd)
    assert _discover_registry(str(wf)) == cwd / "mcp_servers.yaml"


def test_discover_registry_returns_none_when_absent(tmp_path, monkeypatch):
    from megalos_server.validate import _discover_registry
    wf_dir = tmp_path / "wf_dir"
    wf_dir.mkdir()
    wf = wf_dir / "wf.yaml"
    wf.write_text(_WF_NO_MCP)
    empty_cwd = tmp_path / "empty"
    empty_cwd.mkdir()
    monkeypatch.chdir(empty_cwd)
    assert _discover_registry(str(wf)) is None
