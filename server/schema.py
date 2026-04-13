"""YAML workflow schema parsing."""

import yaml
from pathlib import Path


REQUIRED_STEP_KEYS = {"id", "title", "directive_template", "gates", "anti_patterns"}


def load_workflow(path: str) -> dict:
    """Load and validate a workflow YAML file. Returns plain dict."""
    raw = Path(path).read_text()
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise ValueError(f"Workflow YAML must be a mapping, got {type(doc).__name__}")
    if "name" not in doc:
        raise ValueError("Workflow missing required key: 'name'")
    if "steps" not in doc or not isinstance(doc["steps"], list):
        raise ValueError("Workflow missing required key: 'steps' (must be a list)")
    if len(doc["steps"]) == 0:
        raise ValueError("Workflow must have at least one step")
    for i, step in enumerate(doc["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} must be a mapping")
        missing = REQUIRED_STEP_KEYS - step.keys()
        if missing:
            raise ValueError(f"Step {i} ('{step.get('id', '?')}') missing keys: {sorted(missing)}")
        if not isinstance(step["gates"], list):
            raise ValueError(f"Step '{step['id']}' gates must be a list")
        if not isinstance(step["anti_patterns"], list):
            raise ValueError(f"Step '{step['id']}' anti_patterns must be a list")
    return doc
