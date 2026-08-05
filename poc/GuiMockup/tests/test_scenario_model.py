"""Tests for ScenarioModel — filesystem discovery."""

import json

import pytest

from models.scenario_model import ScenarioModel


@pytest.fixture
def model(repo_root):
    return ScenarioModel(repo_root)


class TestDiscover:
    def test_empty_dir(self, repo_root, scenario_dir):
        m = ScenarioModel(repo_root)
        assert len(m.names()) == 0

    def test_flat_json(self, repo_root, scenario_dir):
        (scenario_dir / "test_scenario.json").write_text('{"entities":[]}')
        m = ScenarioModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "test_scenario" in names

    def test_package_json(self, repo_root, scenario_dir):
        pkg = scenario_dir / "my_package"
        pkg.mkdir()
        (pkg / "scenario.json").write_text('{"entities":[]}')
        m = ScenarioModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "my_package" in names

    def test_package_priority(self, repo_root, scenario_dir):
        """Package takes priority over flat JSON of same name."""
        (scenario_dir / "shared.json").write_text('{"entities":[]}')
        pkg = scenario_dir / "shared"
        pkg.mkdir()
        (pkg / "scenario.json").write_text('{"entities":[]}')
        m = ScenarioModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert names.count("shared") == 1

    def test_label_from_filename(self, repo_root, scenario_dir):
        (scenario_dir / "my_test.json").write_text('{"entities":[]}')
        m = ScenarioModel(repo_root)
        labels = [s["label"] for s in m.names()]
        assert "My Test" in labels

    def test_label_from_analysis_md(self, repo_root, scenario_dir):
        pkg = scenario_dir / "special"
        pkg.mkdir()
        (pkg / "scenario.json").write_text('{"entities":[]}')
        (pkg / "analysis.md").write_text("# Custom Label\nSome analysis text.\n")
        m = ScenarioModel(repo_root)
        labels = [s["label"] for s in m.names()]
        assert "Custom Label" in labels

    def test_no_scenario_dir(self, repo_root):
        """Works even if scenario dir doesn't exist."""
        m = ScenarioModel(repo_root)
        assert m.names() == []


class TestIsLoaded:
    def test_initially_loaded(self, repo_root, scenario_dir):
        m = ScenarioModel(repo_root)
        assert m.is_loaded is False  # empty dir

    def test_loaded_after_discover(self, repo_root, scenario_dir):
        (scenario_dir / "test.json").write_text('{"entities":[]}')
        m = ScenarioModel(repo_root)
        assert m.is_loaded is True


class TestRefresh:
    def test_refresh_rescans(self, repo_root, scenario_dir):
        m = ScenarioModel(repo_root)
        assert len(m.names()) == 0
        (scenario_dir / "new.json").write_text('{"entities":[]}')
        m.refresh()
        assert len(m.names()) == 1
