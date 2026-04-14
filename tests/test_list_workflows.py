"""Tests for list_workflows tool."""

from tests.conftest import call_tool


class TestListWorkflows:
    def test_list_all(self):
        r = call_tool("list_workflows", {})
        # Post-M007 production workflows live in domain repos. Mikros bundles
        # only example.yaml. Other test modules may inject demo fixtures into
        # the shared WORKFLOWS dict — assert example is present, not specifics.
        assert r["total"] >= 1
        names = {w["name"] for w in r["workflows"]}
        assert "example" in names

    def test_filter_unknown_category(self):
        r = call_tool("list_workflows", {"category": "nonexistent"})
        assert r["workflows"] == []
        assert r["total"] == 0

    def test_each_workflow_has_category(self):
        r = call_tool("list_workflows", {})
        for wf in r["workflows"]:
            assert wf["category"], f"{wf['name']} missing category"
            assert wf["steps"] > 0
            assert wf["description"]
