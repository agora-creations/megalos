"""YAML workflow schema parsing."""

import yaml
from pathlib import Path


REQUIRED_STEP_KEYS = {"id", "title", "directive_template", "gates", "anti_patterns"}


def validate_workflow(path: str) -> tuple[list[str], dict | None]:
    """Validate a workflow YAML file. Returns (errors, parsed_doc). Empty errors = valid."""
    try:
        raw = Path(path).read_text()
    except (OSError, FileNotFoundError) as e:
        return [str(e)], None
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"], None
    errors = []
    if not isinstance(doc, dict):
        return [f"Workflow YAML must be a mapping, got {type(doc).__name__}"], None
    for key in ("name", "description", "category", "output_format"):
        if key not in doc:
            errors.append(f"Workflow missing required key: '{key}'")
    if "steps" not in doc or not isinstance(doc.get("steps"), list):
        errors.append("Workflow missing required key: 'steps' (must be a list)")
        return errors, None
    if len(doc["steps"]) == 0:
        errors.append("Workflow must have at least one step")
        return errors, None
    for i, step in enumerate(doc["steps"]):
        if not isinstance(step, dict):
            errors.append(f"Step {i} must be a mapping")
            continue
        missing = REQUIRED_STEP_KEYS - step.keys()
        if missing:
            errors.append(f"Step {i} ('{step.get('id', '?')}') missing keys: {sorted(missing)}")
        if "gates" in step and not isinstance(step["gates"], list):
            errors.append(f"Step '{step.get('id', i)}' gates must be a list")
        if "anti_patterns" in step and not isinstance(step["anti_patterns"], list):
            errors.append(f"Step '{step.get('id', i)}' anti_patterns must be a list")
    return errors, doc


def load_workflow(path: str) -> dict:
    """Load and validate a workflow YAML file. Returns plain dict."""
    errors, doc = validate_workflow(path)
    if errors:
        raise ValueError(errors[0])
    assert doc is not None
    return doc
