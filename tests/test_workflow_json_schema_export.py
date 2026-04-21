"""Parity test for the exported JSON Schema.

The megálos workflow JSON Schema at `schemas/megalos-workflow.schema.json`
is a build artifact — not generated, hand-maintained. This test detects
drift: every fixture that the imperative validator (`validate_workflow`
in `megalos_server.schema`) accepts must also validate against the
exported JSON Schema.

The reverse direction (JSON Schema rejects ⇒ validator rejects) is not
tested because JSON Schema is a strict subset of the validator — it
cannot express cross-step constraints (forward-refs, target existence,
call cycles). That is documented in `docs/IDE_SETUP.md`.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from megalos_server.mcp_registry import AuthConfig, Registry, ServerConfig
from megalos_server.schema import validate_workflow


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "megalos-workflow.schema.json"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "workflows"
PRODUCTION_WORKFLOW_DIR = REPO_ROOT / "megalos_server" / "workflows"


def _load_exported_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


def _stub_registry() -> Registry:
    """Registry populated with a single 'stub' server — matches the fixture
    convention used by test_mcp_tool_call_workflows. Required because
    mcp_tool_call fixtures fail to validate without a registry."""
    return Registry(
        servers={
            "stub": ServerConfig(
                name="stub",
                url="http://localhost:0",
                transport="http",
                auth=AuthConfig(type="bearer", token_env="STUB_TOKEN"),
                timeout_default=None,
            )
        }
    )


def _all_fixture_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in ("*.yaml", "**/*.yaml"):
        paths.extend(FIXTURE_DIR.glob(pattern))
    if PRODUCTION_WORKFLOW_DIR.exists():
        paths.extend(PRODUCTION_WORKFLOW_DIR.glob("*.yaml"))
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in sorted(paths):
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
    return unique


def test_exported_schema_is_valid_json_schema():
    schema = _load_exported_schema()
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("fixture_path", _all_fixture_paths(), ids=lambda p: p.name)
def test_validator_accepted_fixture_passes_exported_schema(fixture_path: Path):
    registry = _stub_registry()
    errors, doc = validate_workflow(str(fixture_path), registry=registry)
    if errors:
        pytest.skip(f"fixture intentionally invalid under validate_workflow: {errors[0]}")
    assert doc is not None

    # validate_workflow injects schema_version when absent. Re-parse raw so the
    # JSON Schema check runs against the authoring surface, not the normalized form.
    raw = yaml.safe_load(fixture_path.read_text())
    schema = _load_exported_schema()
    jsonschema.validate(instance=raw, schema=schema)
