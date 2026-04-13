"""YAML workflow schema parsing."""

import jsonschema
import yaml
from pathlib import Path


REQUIRED_STEP_KEYS = {"id", "title", "directive_template", "gates", "anti_patterns"}


def _validate_step_optional_fields(step: dict, label: str, errors: list[str]) -> None:
    """Validate optional output_schema, max_retries, validation_hint on a step."""
    if "output_schema" in step:
        schema = step["output_schema"]
        if not isinstance(schema, dict):
            errors.append(f"Step '{label}' output_schema must be a JSON Schema object (dict)")
        else:
            try:
                jsonschema.Draft202012Validator.check_schema(schema)
            except jsonschema.SchemaError as e:
                errors.append(f"Step '{label}' output_schema is not valid JSON Schema: {e.message}")
    if "max_retries" in step:
        mr = step["max_retries"]
        if not isinstance(mr, int) or mr < 1:
            errors.append(f"Step '{label}' max_retries must be a positive integer")
    if "validation_hint" in step:
        if not isinstance(step["validation_hint"], str):
            errors.append(f"Step '{label}' validation_hint must be a string")
    if "inject_context" in step:
        ic = step["inject_context"]
        if not isinstance(ic, list):
            errors.append(f"Step '{label}' inject_context must be a list")
        else:
            for j, entry in enumerate(ic):
                if not isinstance(entry, dict):
                    errors.append(f"Step '{label}' inject_context[{j}] must be a mapping")
                    continue
                if "from" not in entry:
                    errors.append(f"Step '{label}' inject_context[{j}] missing required key 'from'")
                elif not isinstance(entry["from"], str):
                    errors.append(f"Step '{label}' inject_context[{j}] 'from' must be a string")
                if "fields" in entry and not isinstance(entry["fields"], list):
                    errors.append(f"Step '{label}' inject_context[{j}] 'fields' must be a list")
                if "summary" in entry and not isinstance(entry["summary"], bool):
                    errors.append(f"Step '{label}' inject_context[{j}] 'summary' must be a boolean")
    if "directives" in step:
        d = step["directives"]
        if not isinstance(d, dict):
            errors.append(f"Step '{label}' directives must be a mapping")
        else:
            for key in ("tone", "strategy", "persona"):
                if key in d and not isinstance(d[key], str):
                    errors.append(f"Step '{label}' directives.{key} must be a string")
            if "constraints" in d:
                if not isinstance(d["constraints"], list):
                    errors.append(f"Step '{label}' directives.constraints must be a list")
                elif not all(isinstance(c, str) for c in d["constraints"]):
                    errors.append(f"Step '{label}' directives.constraints entries must be strings")


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
        label = step.get("id", str(i))
        _validate_step_optional_fields(step, label, errors)
    # Cross-reference: inject_context 'from' must point to an existing step ID
    all_step_ids = {s.get("id") for s in doc["steps"] if isinstance(s, dict)}
    for step in doc["steps"]:
        if not isinstance(step, dict) or "inject_context" not in step:
            continue
        label = step.get("id", "?")
        for entry in step["inject_context"]:
            if isinstance(entry, dict) and "from" in entry and isinstance(entry["from"], str):
                if entry["from"] not in all_step_ids:
                    errors.append(f"Step '{label}' inject_context references nonexistent step '{entry['from']}'")
    return errors, doc


def load_workflow(path: str) -> dict:
    """Load and validate a workflow YAML file. Returns plain dict."""
    errors, doc = validate_workflow(path)
    if errors:
        raise ValueError(errors[0])
    assert doc is not None
    return doc
