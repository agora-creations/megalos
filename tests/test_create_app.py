"""Verify the create_app factory works for bundled defaults and external workflow dirs."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from mikros_server import create_app


BUILT_IN_NAMES = {"coding", "essay", "blog", "decision", "research"}


def _list_workflow_names(app):
    result = asyncio.run(app.call_tool("list_workflows", {}))
    data = result.structured_content
    return {w["name"] for w in data.get("workflows", [])}


def test_default_loads_bundled_workflows():
    app = create_app()
    names = _list_workflow_names(app)
    assert BUILT_IN_NAMES.issubset(names), f"missing built-ins: {BUILT_IN_NAMES - names}"


def test_external_workflow_dir_loads_only_that_dir():
    minimal_yaml = """name: toy
description: tiny test workflow
category: test
output_format: text
steps:
  - id: only
    title: Only step
    directive_template: Do the thing.
    gates: []
    anti_patterns: []
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "toy.yaml").write_text(minimal_yaml)
        app = create_app(workflow_dir=tmpdir)
        names = _list_workflow_names(app)
        assert names == {"toy"}, f"expected only 'toy', got {names}"


def test_empty_workflow_dir_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(RuntimeError, match="No workflow YAML"):
            create_app(workflow_dir=tmpdir)
