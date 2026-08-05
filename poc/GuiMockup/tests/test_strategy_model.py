"""Tests for StrategyModel — fragment filtering."""

import pytest

from models.strategy_model import StrategyModel


@pytest.fixture
def model(repo_root):
    return StrategyModel(repo_root)


class TestDiscover:
    def test_empty_dir(self, repo_root, fragments_dir):
        m = StrategyModel(repo_root)
        assert len(m.names()) == 0

    def test_included_mode(self, repo_root, fragments_dir):
        (fragments_dir / "rules_3vs3.txt").write_text("Be aggressive")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "3vs3" in names

    def test_excluded_core(self, repo_root, fragments_dir):
        (fragments_dir / "rules_core.txt").write_text("Core rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "core" not in names

    def test_excluded_ball_out(self, repo_root, fragments_dir):
        (fragments_dir / "rules_ball_out.txt").write_text("Ball out rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "ball_out" not in names

    def test_excluded_goal_kick(self, repo_root, fragments_dir):
        (fragments_dir / "rules_goal_kick.txt").write_text("Goal kick rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "goal_kick" not in names

    def test_excluded_corner_kick_in(self, repo_root, fragments_dir):
        (fragments_dir / "rules_corner_kick_in.txt").write_text("Corner rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "corner_kick_in" not in names

    def test_excluded_kickoff(self, repo_root, fragments_dir):
        (fragments_dir / "rules_kickoff.txt").write_text("Kickoff rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "kickoff" not in names

    def test_unknown_mode_excluded(self, repo_root, fragments_dir):
        (fragments_dir / "rules_custom.txt").write_text("Custom rules")
        m = StrategyModel(repo_root)
        names = [s["name"] for s in m.names()]
        assert "custom" not in names

    def test_all_8_modes(self, repo_root, fragments_dir):
        for mode in ["3vs3", "2vs2", "1vs1", "3vs1", "2vs1", "1vs0", "0vs1", "recover"]:
            (fragments_dir / f"rules_{mode}.txt").write_text(f"Rules for {mode}")
        m = StrategyModel(repo_root)
        names = sorted([s["name"] for s in m.names()])
        assert names == ["0vs1", "1vs0", "1vs1", "2vs1", "2vs2", "3vs1", "3vs3", "recover"]

    def test_label_is_uppercase(self, repo_root, fragments_dir):
        (fragments_dir / "rules_3vs3.txt").write_text("Be aggressive")
        m = StrategyModel(repo_root)
        labels = [s["label"] for s in m.names()]
        assert "3VS3" in labels


class TestIsLoaded:
    def test_initially_loaded(self, repo_root, fragments_dir):
        m = StrategyModel(repo_root)
        assert m.is_loaded is False  # empty dir

    def test_loaded_after_discover(self, repo_root, fragments_dir):
        (fragments_dir / "rules_3vs3.txt").write_text("Be aggressive")
        m = StrategyModel(repo_root)
        assert m.is_loaded is True


class TestRefresh:
    def test_refresh_rescans(self, repo_root, fragments_dir):
        m = StrategyModel(repo_root)
        assert len(m.names()) == 0
        (fragments_dir / "rules_2vs2.txt").write_text("Be defensive")
        m.refresh()
        assert len(m.names()) == 1
