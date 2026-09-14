"""A2bot scope 1: per-bot demo targets, prefix parsing, coordinate fast-path.

Fast-tier: no ROS, no Ollama. Paths are monkeypatched to tmp_path.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_tactics'))

import r2k_evaluator as ev


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    ev._demo_state.clear()
    def _no_network(*a, **k):
        raise AssertionError("test attempted a real Ollama call")
    monkeypatch.setattr(ev.requests, "post", _no_network)
    yield
    ev._demo_state.clear()


@pytest.fixture
def paths(tmp_path, monkeypatch):
    wp = tmp_path / "waypoints.json"
    strat = tmp_path / "current_strategy.json"
    monkeypatch.setattr(ev, "WAYPOINTS_PATH", str(wp))
    monkeypatch.setattr(ev, "STRATEGY_PATH", str(strat))
    return {"wp": wp, "strat": strat}


ENTS_2VS0 = {"soccer_ball": {"x": 1.0, "y": 1.0},
             "blue1": {"x": 0.0, "y": 0.0},
             "blue2": {"x": 0.0, "y": 1.0}}


def seed_wp(bot, wps):
    st = ev._demo_bot_state(bot)
    st["waypoints"] = ev._norm_demo_waypoints(wps)
    return st


def test_parse_task_bot_prefix():
    assert ev._parse_task_bot("blue_2 go to (2,0)") == ("blue2", "go to (2,0)", True)
    assert ev._parse_task_bot("blue_1 draw a circle") == ("blue1", "draw a circle", True)
    assert ev._parse_task_bot("k1 goto 1,1") == ("k1", "goto 1,1", True)
    assert ev._parse_task_bot("k1_bot goto 1,1") == ("k1", "goto 1,1", True)


def test_parse_task_no_prefix_defaults_to_blue_1():
    assert ev._parse_task_bot("go to (2, 0)") == ("blue1", "go to (2, 0)", False)
    assert ev._parse_task_bot("draw a hexagon 2m sides") == ("blue1", "draw a hexagon 2m sides", False)


def test_parse_task_scope_all():
    bot, text, prefixed = ev._parse_task_bot("(all) yahbooms goto 2,2")
    assert bot == "ALL_BOTS"
    assert text == "goto 2,2"
    assert prefixed
    bot, text, _ = ev._parse_task_bot("all bots go to the right wing")
    assert bot == "ALL_BOTS"
    assert text == "go to the right wing"
    bot, text, _ = ev._parse_task_bot("both go to (2, 2)")
    assert bot == "ALL_BOTS"
    assert text == "go to (2, 2)"


def test_coord_regex_matches():
    for text, (x, y) in [("go to (2,0)", (2.0, 0.0)), ("goto 2,2", (2.0, 2.0)),
                         ("move to -1.5, 3", (-1.5, 3.0)),
                         ("go to ( -2 , 3 )", (-2.0, 3.0))]:
        m = ev.DEMO_COORD_RE.match(text)
        assert m, text
        assert (float(m.group(1)), float(m.group(2))) == (x, y)


def test_coord_regex_rejects_non_coords():
    for text in ["draw a circle center (0,0) radius 1m", "go to the wing",
                 "patrol between (1,1) and (2,2)", "approach the ball"]:
        assert ev.DEMO_COORD_RE.match(text) is None, text


def test_per_bot_arrival_isolation():
    seed_wp("blue1", [{"label": "FIRST", "x": 0.0, "y": 0.0},
                       {"label": "SECOND", "x": 2.0, "y": 0.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 0.0, "y": 1.0},
                       {"label": "SECOND", "x": 2.0, "y": 1.0}])
    assert ev._demo_target_for_bot("blue1", 0.1, 0.0) == "SECOND"
    assert ev._demo_target_for_bot("blue2", 3.0, 1.0) == "FIRST"
    assert ev._demo_bot_state("blue1")["target_idx"] == 1
    assert ev._demo_bot_state("blue2")["target_idx"] == 0


def test_waypoints_legacy_schema_loads_as_blue_1(paths):
    paths["wp"].write_text(json.dumps(
        {"waypoints": [{"label": "FIRST", "x": 1.0, "y": 1.0}]}))
    ev._load_demo_waypoints()
    assert len(ev._demo_bot_state("blue1")["waypoints"]) == 1
    assert "blue2" not in ev._demo_state


def test_waypoints_bots_schema_loads_per_bot(paths):
    paths["wp"].write_text(json.dumps({"bots": {
        "blue1": {"waypoints": [{"label": "FIRST", "x": 1.0, "y": 1.0}]},
        "blue2": {"waypoints": [{"label": "FIRST", "x": 2.0, "y": 2.0}]}}}))
    ev._load_demo_waypoints()
    assert ev._demo_bot_state("blue1")["waypoints"][0]["x"] == 1.0
    assert ev._demo_bot_state("blue2")["waypoints"][0]["x"] == 2.0


def test_write_waypoints_file_keeps_other_bots(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0}])
    ev._write_waypoints_file()
    data = json.loads(paths["wp"].read_text())
    assert data["bots"]["blue1"]["waypoints"][0]["x"] == 1.0
    assert data["bots"]["blue2"]["waypoints"][0]["x"] == 2.0


def test_strategy_write_merges_other_bots(paths):
    ev._write_hold_strategy("blue1")
    ev._write_move_strategy("blue2", 1.0, 2.0)
    data = json.loads(paths["strat"].read_text())
    assert data["assignments"]["blue1"] == {"action": "Hold"}
    assert data["assignments"]["blue2"] == {"action": "Move", "x": 1.0, "y": 2.0}


def test_stop_all_bots_clears_every_bot(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0}])
    ev._handle_task_clause("stop all bots", ENTS_2VS0)
    for bot in ("blue1", "blue2"):
        st = ev._demo_bot_state(bot)
        assert st["waypoints"] == []
        assert st["fast_cmd"] == {"action": "Hold"}
    data = json.loads(paths["strat"].read_text())
    assert data["assignments"]["blue1"] == {"action": "Hold"}
    assert data["assignments"]["blue2"] == {"action": "Hold"}


def test_unprefixed_stop_is_fleet_wide(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0}])
    ev._handle_task_clause("stop", ENTS_2VS0)
    for bot in ("blue1", "blue2"):
        st = ev._demo_bot_state(bot)
        assert st["waypoints"] == []
        assert st["fast_cmd"] == {"action": "Hold"}


def test_unprefixed_go_home_is_fleet_wide(paths):
    ev._demo_bot_state("blue2")["start_pos"] = (0.0, 1.0)
    ev._handle_task_clause("go home", ENTS_2VS0)
    # go home seeds a one-waypoint waypath per bot (proven arrival/park
    # machinery) — each bot drives to ITS captured start position
    assert ev._demo_bot_state("blue1")["waypoints"] == [
        {"label": "HOME", "x": 0.0, "y": 0.0, "hold_duration": 0.0}]
    assert ev._demo_bot_state("blue2")["waypoints"] == [
        {"label": "HOME", "x": 0.0, "y": 1.0, "hold_duration": 0.0}]
    assert ev._demo_bot_state("blue1")["fast_cmd"] is None


def test_quoted_task_hits_coord_fastpath(paths, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("quoted coord task must bypass the compiler")
    monkeypatch.setattr(ev, "_compile_demo_task", boom)
    paths["task"] = paths["wp"].parent / "task_input.json"
    monkeypatch.setattr(ev, "TASK_INPUT_PATH", str(paths["task"]))
    paths["task"].write_text(json.dumps({"task": '"goto 1,-1"'}))
    ev._check_task_input(ENTS_2VS0, {})
    st = ev._demo_bot_state("blue1")
    # coordinate fast-path = one-waypoint waypath (evaluator parks at 0.2m)
    assert st["waypoints"] == [
        {"label": "FIRST", "x": 1.0, "y": -1.0, "hold_duration": 0.0}]
    assert st["fast_cmd"] is None


def test_coord_fastpath_targets_only_prefixed_bot(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    ev._handle_task_clause("blue_2 goto 2,2", ENTS_2VS0)
    assert ev._demo_bot_state("blue2")["waypoints"] == [
        {"label": "FIRST", "x": 2.0, "y": 2.0, "hold_duration": 0.0}]
    assert ev._demo_bot_state("blue1")["waypoints"][0]["x"] == 1.0


def test_coord_fastpath_scope_all_hits_every_bot(paths):
    ev._handle_task_clause("(all) yahbooms goto 2,2", ENTS_2VS0)
    for bot in ("blue1", "blue2"):
        st = ev._demo_bot_state(bot)
        assert st["waypoints"] == [
            {"label": "FIRST", "x": 2.0, "y": 2.0, "hold_duration": 0.0}]
        assert st["fast_cmd"] is None


def test_scope_only_clause_ignored(paths, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("compiler must not be called for verb-less clauses")
    monkeypatch.setattr(ev, "_compile_demo_task", boom)
    ev._handle_task_clause("simulated bots only", ENTS_2VS0)
    assert ev._demo_state == {}


def test_compile_routed_to_prefixed_bot(paths, monkeypatch):
    calls = []

    def fake_compile(bot, text, ents):
        calls.append((bot, text))
        return True
    monkeypatch.setattr(ev, "_compile_demo_task", fake_compile)
    ev._handle_task_clause("blue_2 draw a circle center (0,0) radius 1m", ENTS_2VS0)
    assert calls == [("blue2", "draw a circle center (0,0) radius 1m")]


def test_fast_cmd_cleared_on_compile(paths):
    ev._handle_task_clause("blue_2 stop", ENTS_2VS0)
    assert ev._demo_bot_state("blue2")["fast_cmd"] == {"action": "Hold"}
    seed_wp("blue2", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    st = ev._demo_bot_state("blue2")
    st["fast_cmd"] = None
    assert st["fast_cmd"] is None


def test_inject_targets_single_strips_other_bots():
    seed_wp("blue1", [{"label": "FIRST", "x": -1.0, "y": 1.5},
                       {"label": "SECOND", "x": 1.0, "y": 1.5}])
    min_ents = {k: {"x": v["x"], "y": v["y"]} for k, v in ENTS_2VS0.items()}
    ev._demo_inject_targets(min_ents, ENTS_2VS0)
    assert min_ents["targets"] == {"blue1": "FIRST"}
    assert "blue2" not in min_ents, "non-targeted bot must be stripped"
    assert min_ents["waypoints"]["FIRST"] == {"x": -1.0, "y": 1.5}


def test_inject_targets_multi_prefixed_labels():
    seed_wp("blue1", [{"label": "FIRST", "x": -1.0, "y": 1.5}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": -2.0}])
    min_ents = {k: {"x": v["x"], "y": v["y"]} for k, v in ENTS_2VS0.items()}
    ev._demo_inject_targets(min_ents, ENTS_2VS0)
    assert min_ents["targets"] == {"blue1": "B1_FIRST", "blue2": "B2_FIRST"}
    assert min_ents["waypoints"]["B1_FIRST"] == {"x": -1.0, "y": 1.5}
    assert min_ents["waypoints"]["B2_FIRST"] == {"x": 2.0, "y": -2.0}


def test_inject_targets_no_active_bots_strips_all():
    """Post-park hallucination hole (2026-09-05): when NO bot has an active
    waypath, all blue bots must be STRIPPED — unstripped, the 3B assigned
    every visible bot soccer-style (roles, 'Move to ball', phantom blue_3),
    overriding parked Hold/gesture fast_cmds -> both bots drove off."""
    min_ents = {k: {"x": v["x"], "y": v["y"]} for k, v in ENTS_2VS0.items()}
    ev._demo_inject_targets(min_ents, ENTS_2VS0)
    assert "targets" not in min_ents
    assert "blue1" not in min_ents and "blue2" not in min_ents
    assert "soccer_ball" in min_ents      # ball stays (context only)


def test_fast_cmd_overrides_hallucinated_assignments():
    """Fast-path authority: a bot under a fast_cmd (Hold/Head/Face) is
    controlled exclusively by it — the executor's (possibly hallucinated)
    assignment for that bot must be REPLACED, not just gap-filled."""
    ev._demo_bot_state("blue2")["fast_cmd"] = {"action": "Head", "gesture": "yes", "id": 7}
    data = {"assignments": {"blue2": {"action": "Move", "x": -2.5, "y": 0.0},
                           "blue3": {"action": "Move", "x": 1.0, "y": 1.0}}}
    ev._demo_reinject_fast_cmds(data)
    assert data["assignments"]["blue2"]["action"] == "Head"
    assert data["assignments"]["blue2"]["id"] == 7
    # phantom bots pass through untouched (no hw entry maps them in the bridge)
    assert data["assignments"]["blue3"]["action"] == "Move"


def test_write_assignment_drops_stale_metadata(paths):
    paths["strat"].write_text(json.dumps(
        {"assignments": {"blue2": {"action": "Hold"}},
         "latency_ms": 417, "model_name": "qwen2.5:3b"}))
    ev._write_move_strategy("blue1", 3.0, 3.0)
    data = json.loads(paths["strat"].read_text())
    assert data == {"assignments": {"blue2": {"action": "Hold"},
                                    "blue1": {"action": "Move", "x": 3.0, "y": 3.0}}}


def test_waypath_completion_parks_bot(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 0.0, "y": 0.0}])
    assert ev._demo_target_for_bot("blue1", 0.4, 0.0) == "FIRST"
    assert ev._demo_bot_state("blue1")["waypoints"]
    assert ev._demo_target_for_bot("blue1", 0.1, 0.0) is None
    st = ev._demo_bot_state("blue1")
    assert st["waypoints"] == []
    assert st["fast_cmd"] == {"action": "Hold"}
    assert st["stopped_idx"] == 0
    data = json.loads(paths["strat"].read_text())
    assert data["assignments"]["blue1"] == {"action": "Hold"}


def test_resume_after_completion_replays_from_start(paths):
    paths["wp"].write_text(json.dumps({"waypoints": [
        {"label": "FIRST", "x": 1.0, "y": 1.0},
        {"label": "SECOND", "x": 2.0, "y": 2.0}]}))
    seed_wp("blue1", [{"label": "FIRST", "x": 0.0, "y": 0.0}])
    assert ev._demo_target_for_bot("blue1", 0.1, 0.0) is None
    assert ev._demo_bot_state("blue1")["waypoints"] == []
    ev._demo_resume_bot("blue1")
    st = ev._demo_bot_state("blue1")
    assert len(st["waypoints"]) == 2
    assert st["target_idx"] == 0
    assert st["fast_cmd"] is None


def test_prefixed_control_verb_targets_only_that_bot(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0}])
    # "blue_2 stop" must halt ONLY blue_2 (lab 2026-08-31: prefixed control
    # verbs were fleet-wide -> both bots executed the last movement)
    ev._handle_task_clause("blue_2 stop", ENTS_2VS0)
    assert ev._demo_bot_state("blue2")["waypoints"] == []
    assert ev._demo_bot_state("blue2")["fast_cmd"] == {"action": "Hold"}
    assert ev._demo_bot_state("blue1")["waypoints"]      # untouched
    assert ev._demo_bot_state("blue1")["fast_cmd"] is None


def test_prefixed_redo_targets_only_that_bot(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0},
                       {"label": "SECOND", "x": 3.0, "y": 3.0}])
    # blue_2 reaches its first waypoint -> target_idx advances
    ev._demo_target_for_bot("blue2", 2.0, 2.0)
    assert ev._demo_bot_state("blue2")["target_idx"] == 1
    # "blue_2 redo" must replay ONLY blue_2 (the lab regression)
    ev._handle_task_clause("blue_2 redo", ENTS_2VS0)
    assert ev._demo_bot_state("blue2")["target_idx"] == 0    # replayed
    assert ev._demo_bot_state("blue1")["target_idx"] == 0    # untouched
    assert ev._demo_bot_state("blue1")["waypoints"]


def test_bare_control_verb_still_fleet_wide(paths):
    seed_wp("blue1", [{"label": "FIRST", "x": 1.0, "y": 1.0}])
    seed_wp("blue2", [{"label": "FIRST", "x": 2.0, "y": 2.0}])
    ev._demo_bot_state("blue2")["target_idx"] = 1  # mid-waypath
    ev._handle_task_clause("redo", ENTS_2VS0)
    assert ev._demo_bot_state("blue1")["target_idx"] == 0
    assert ev._demo_bot_state("blue2")["target_idx"] == 0  # both replayed


def test_go_home_uses_captured_start_pos(paths):
    st = ev._demo_bot_state("blue2")
    st["start_pos"] = (0.0, 1.0)
    ev._handle_task_clause("blue_2 go home", ENTS_2VS0)
    assert st["waypoints"] == [
        {"label": "HOME", "x": 0.0, "y": 1.0, "hold_duration": 0.0}]
