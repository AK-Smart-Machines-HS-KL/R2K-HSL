"""Tests for LauncherController — CLI assembly, auto-advance, anticipate."""

import pytest
from PySide6.QtCore import QObject

from controllers.launcher_controller import LauncherController
from models.scenario_model import ScenarioModel
from models.strategy_model import StrategyModel
from models.model_model import ModelModel


@pytest.fixture
def controller(repo_root):
    return LauncherController(repo_root)


@pytest.fixture
def controller_with_repos(repo_root, scenario_dir, fragments_dir):
    scenario_repo = ScenarioModel(repo_root)
    strategy_repo = StrategyModel(repo_root)
    model_repo = ModelModel(parent=None)
    return LauncherController(
        repo_root,
        scenario_repo=scenario_repo,
        strategy_repo=strategy_repo,
        model_repo=model_repo,
    )


# -- _build_cmd_str tests ---------------------------------------------------


class TestBuildCmdStr:
    def test_basic_command(self, controller):
        controller._selected_scenario = "3vs3_attack_center"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "qwen2.5-coder:3b"
        cmd = controller._build_cmd_str()
        assert "launch_r2k.sh" in cmd
        assert "--scenario" in cmd
        assert "3vs3_attack_center" in cmd
        assert "--strategy strat_3vs3" in cmd
        assert "--model qwen2.5-coder:3b" in cmd

    def test_relay_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._selected_relay = "hardware_mirror"
        cmd = controller._build_cmd_str()
        assert "--relay hardware_mirror" in cmd

    def test_explain_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._explain = True
        cmd = controller._build_cmd_str()
        assert "--explain" in cmd
        assert "--no-explain" not in cmd

    def test_no_explain_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._explain = False
        cmd = controller._build_cmd_str()
        assert "--no-explain" in cmd

    def test_headless_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._headless = True
        cmd = controller._build_cmd_str()
        assert "--headless" in cmd

    def test_no_headless_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._headless = False
        cmd = controller._build_cmd_str()
        assert "--headless" not in cmd

    def test_duration_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._duration = 120
        cmd = controller._build_cmd_str()
        assert "--duration 120" in cmd

    def test_duration_zero_omits_flag(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller._duration = 0
        cmd = controller._build_cmd_str()
        assert "--duration" not in cmd

    def test_cd_to_core(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        cmd = controller._build_cmd_str()
        assert cmd.startswith("cd \"")


# -- select_* auto-advance tests -------------------------------------------


class TestSelectAutoAdvance:
    def test_select_scenario_advances(self, controller):
        assert controller.current_step == 0
        controller.select_scenario("test")
        assert controller.current_step == 1

    def test_select_strategy_advances(self, controller):
        controller._step = 1
        controller.select_strategy("3vs3")
        assert controller.current_step == 2

    def test_select_model_advances(self, controller):
        controller._step = 2
        controller.select_model("qwen2.5-coder:3b")
        assert controller.current_step == 3

    def test_select_relay_advances(self, controller):
        controller._step = 3
        controller.select_relay("only_sim_bots")
        assert controller.current_step == 4

    def test_select_explain_advances(self, controller):
        controller._step = 4
        controller.set_explain(True)
        assert controller.current_step == 5

    def test_select_headless_advances(self, controller):
        controller._step = 5
        controller.set_headless(True)
        assert controller.current_step == 6

    def test_set_duration_does_not_advance(self, controller):
        controller._step = 6
        controller.set_duration(120)
        assert controller.current_step == 6

    def test_same_selection_still_advances(self, controller):
        """select_* always calls go_forward(), even for same value."""
        controller._selected_scenario = "test"
        controller.select_scenario("test")
        assert controller.current_step == 1


# -- navigation tests -------------------------------------------------------


class TestNavigation:
    def test_go_forward(self, controller):
        assert controller.current_step == 0
        controller.go_forward()
        assert controller.current_step == 1

    def test_go_backward(self, controller):
        controller._step = 2
        controller.go_back()
        assert controller.current_step == 1

    def test_go_forward_at_end(self, controller):
        controller._step = controller.step_count - 1
        controller.go_forward()
        assert controller.current_step == controller.step_count - 1

    def test_go_backward_at_start(self, controller):
        controller._step = 0
        controller.go_back()
        assert controller.current_step == 0

    def test_go_to_step(self, controller):
        controller.go_to_step(5)
        assert controller.current_step == 5


# -- reset tests -----------------------------------------------------------


class TestReset:
    def test_reset_clears_selections(self, controller):
        controller._selected_scenario = "test"
        controller._selected_strategy = "3vs3"
        controller._selected_model = "test"
        controller.reset()
        assert controller.selected_scenario == ""
        assert controller.selected_strategy == ""
        assert controller.selected_model == ""

    def test_reset_goes_to_step_zero(self, controller):
        controller._step = 5
        controller.reset()
        assert controller.current_step == 0


# -- _anticipate tests ------------------------------------------------------


class TestAnticipate:
    def test_anticipate_step0_discover_strategy(self, repo_root, fragments_dir):
        (fragments_dir / "rules_3vs3.txt").write_text("Be aggressive")
        c = LauncherController(
            repo_root,
            strategy_repo=StrategyModel(repo_root),
            model_repo=ModelModel(parent=None),
        )
        c._strategy_repo._items = []
        c._anticipate(0)
        assert len(c._strategy_repo._items) > 0

    def test_anticipate_step1_discover_model(self, controller_with_repos):
        c = controller_with_repos
        c._model_repo._items = []
        c._anticipate(1)
        assert len(c._model_repo._items) > 0

    def test_anticipate_step0_skips_if_loaded(self, controller_with_repos):
        c = controller_with_repos
        original_count = len(c._strategy_repo._items)
        c._anticipate(0)
        assert len(c._strategy_repo._items) == original_count
