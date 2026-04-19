"""Workflow catalog pool loader for the selection-measurement slice.

Pure file-IO: reads workflow YAML files directly from disk. No runtime
dependency on megalos_server — the measurement harness must be able to
run against an arbitrary directory of workflow YAMLs without importing
the server package or its state layer.

Each returned entry is the shape the selection-measurement code consumes:

    {"name": str, "description": str, "category": str}

Malformed files (missing either `name` or `description`) are silently
skipped rather than failing the whole load. That keeps the loader useful
against in-progress catalogs where one file is mid-edit. Files whose
`category` is absent are assigned "uncategorized" — the measurement code
treats category as a grouping key, not a gate.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def load_live_catalog(workflow_dir: Path) -> list[dict]:
    """Load every workflow YAML under ``workflow_dir`` into selection entries.

    Recursive: sub-directories are walked so a catalog organized by
    category (writing/, analysis/, professional/) loads in one call.
    Files that fail YAML parsing or lack ``name``/``description`` are
    skipped without raising.
    """

    entries: list[dict] = []
    for path in sorted(workflow_dir.rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        description = data.get("description")
        if not isinstance(name, str) or not isinstance(description, str):
            continue
        if not name.strip() or not description.strip():
            continue
        category = data.get("category")
        if not isinstance(category, str) or not category.strip():
            category = "uncategorized"
        entries.append(
            {
                "name": name,
                "description": description,
                "category": category,
            }
        )
    return entries
