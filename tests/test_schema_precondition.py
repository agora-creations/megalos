"""Tests for step-level precondition grammar and parse-time rejects."""

import os
import tempfile

from megalos_server.schema import validate_workflow


def _write_and_validate(yaml_str: str) -> list[str]:
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(yaml_str)
        errors, _ = validate_workflow(path)
        return errors
    finally:
        os.unlink(path)


def test_precondition_parses_when_equals():
    yaml_str = """\
name: pc_eq
description: precondition when_equals parses
category: testing
output_format: text
steps:
  - id: step_1
    title: First
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
  - id: step_2
    title: Second
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
    precondition:
      when_equals:
        ref: step_data.step_1.field_a
        value: yes
"""
    errors = _write_and_validate(yaml_str)
    assert errors == [], errors


def test_precondition_parses_when_present():
    yaml_str = """\
name: pc_pres
description: precondition when_present parses
category: testing
output_format: text
steps:
  - id: step_1
    title: First
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
  - id: step_2
    title: Second
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
    precondition:
      when_present: step_data.step_1
"""
    errors = _write_and_validate(yaml_str)
    assert errors == [], errors


def test_precondition_rejects_malformed_grammar():
    yaml_str = """\
name: pc_bad
description: when_equals missing value
category: testing
output_format: text
steps:
  - id: step_1
    title: First
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
  - id: step_2
    title: Second
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
    precondition:
      when_equals:
        ref: step_data.step_1
"""
    errors = _write_and_validate(yaml_str)
    assert any(
        "step_2" in e and "precondition.when_equals" in e and "'value'" in e
        for e in errors
    ), errors


def test_precondition_rejects_dotted_ref_path():
    yaml_str = """\
name: pc_dotref
description: dotted/escaped ref-path rejected
category: testing
output_format: text
steps:
  - id: step_1
    title: First
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
  - id: step_2
    title: Second
    directive_template: do it
    gates: [done]
    anti_patterns: [none]
    precondition:
      when_equals:
        ref: 'step_data.step_1."field.with.dots"'
        value: x
"""
    errors = _write_and_validate(yaml_str)
    assert any(
        "step_2" in e and "precondition.when_equals.ref is not a valid ref-path" in e
        for e in errors
    ), errors
