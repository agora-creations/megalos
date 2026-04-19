"""Tests for the workflow-selection pool loader."""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.selection.pool import load_live_catalog

ANCHORS_PATH = (
    Path(__file__).parent.parent / "fixtures" / "workflow_selection" / "anchors.yaml"
)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


class TestLoadLiveCatalog:
    def test_parses_valid_workflow_files(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "writing" / "essay.yaml",
            {
                "name": "essay",
                "description": "Produce a long-form analytical essay.",
                "category": "writing",
            },
        )
        _write_yaml(
            tmp_path / "analysis" / "research.yaml",
            {
                "name": "research",
                "description": "Research a topic and produce a report.",
                "category": "analysis",
            },
        )

        entries = load_live_catalog(tmp_path)

        assert len(entries) == 2
        names = {e["name"] for e in entries}
        assert names == {"essay", "research"}
        for entry in entries:
            assert set(entry.keys()) == {"name", "description", "category"}

    def test_ignores_files_missing_required_fields(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "ok.yaml",
            {
                "name": "ok",
                "description": "A valid workflow.",
                "category": "writing",
            },
        )
        _write_yaml(tmp_path / "no_name.yaml", {"description": "missing name"})
        _write_yaml(tmp_path / "no_description.yaml", {"name": "no_desc"})
        _write_yaml(tmp_path / "empty_name.yaml", {"name": "", "description": "x"})

        entries = load_live_catalog(tmp_path)

        assert [e["name"] for e in entries] == ["ok"]

    def test_ignores_malformed_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "broken.yaml").write_text("name: ok\n  bad: [unterminated")
        _write_yaml(
            tmp_path / "good.yaml",
            {"name": "good", "description": "valid", "category": "writing"},
        )

        entries = load_live_catalog(tmp_path)

        assert [e["name"] for e in entries] == ["good"]

    def test_assigns_uncategorized_when_category_missing(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "no_cat.yaml",
            {"name": "no_cat", "description": "no category key"},
        )

        entries = load_live_catalog(tmp_path)

        assert entries == [
            {
                "name": "no_cat",
                "description": "no category key",
                "category": "uncategorized",
            }
        ]

    def test_categorizes_across_category_subdirs(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "writing" / "blog.yaml",
            {"name": "blog", "description": "Short blog post.", "category": "writing"},
        )
        _write_yaml(
            tmp_path / "analysis" / "decision.yaml",
            {
                "name": "decision",
                "description": "Reasoned recommendation.",
                "category": "analysis",
            },
        )
        _write_yaml(
            tmp_path / "professional" / "coding.yaml",
            {
                "name": "coding",
                "description": "Implement a feature from a spec.",
                "category": "professional",
            },
        )

        entries = load_live_catalog(tmp_path)

        by_name = {e["name"]: e["category"] for e in entries}
        assert by_name == {
            "blog": "writing",
            "decision": "analysis",
            "coding": "professional",
        }

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_live_catalog(tmp_path) == []


class TestCalibrationAnchorsFile:
    def test_anchors_file_parses(self) -> None:
        data = yaml.safe_load(ANCHORS_PATH.read_text())
        assert isinstance(data, dict)
        assert "anchors" in data
        assert isinstance(data["anchors"], list)

    def test_anchors_has_at_least_two_entries(self) -> None:
        data = yaml.safe_load(ANCHORS_PATH.read_text())
        assert len(data["anchors"]) >= 2

    def test_every_anchor_has_required_fields(self) -> None:
        data = yaml.safe_load(ANCHORS_PATH.read_text())
        required = {
            "pair_id",
            "description_A",
            "description_B",
            "operator_assigned_closeness",
            "rationale",
        }
        for anchor in data["anchors"]:
            assert required.issubset(anchor.keys()), (
                f"anchor {anchor.get('pair_id')} missing fields: "
                f"{required - anchor.keys()}"
            )
            score = anchor["operator_assigned_closeness"]
            assert isinstance(score, (int, float))
            assert 0.0 <= float(score) <= 1.0

    def test_anchors_span_closeness_bands(self) -> None:
        data = yaml.safe_load(ANCHORS_PATH.read_text())
        scores = [float(a["operator_assigned_closeness"]) for a in data["anchors"]]
        assert min(scores) < 0.4, "expected at least one low-closeness anchor"
        assert max(scores) > 0.6, "expected at least one high-closeness anchor"
