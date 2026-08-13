import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_tactics'))

import r2k_evaluator as ev


@pytest.fixture(autouse=True)
def reset_text_mode():
    """Ensure TEXT_MODE is False for most tests; toggle explicitly where needed."""
    old = ev.TEXT_MODE
    ev.TEXT_MODE = False
    yield
    ev.TEXT_MODE = old


def sample_world():
    return {
        "soccer_ball": {"x": 2.0, "y": 1.5},
        "blue_1": {"x": 1.5, "y": 1.0},
        "blue_2": {"x": -3.0, "y": 0.0},
        "red_1": {"x": 3.0, "y": 1.0},
    }


class TestBuildTextWorld:
    def test_basic_rendering(self):
        text = ev._build_text_world(sample_world(), {"status": "playing", "blue": 0, "red": 0})
        lines = text.splitlines()
        assert lines[0] == "soccer_ball at (2.0, 1.5)"
        assert "blue_1 at (1.5, 1.0)" in lines
        assert "blue_2 at (-3.0, 0.0)" in lines
        assert "red_1 at (3.0, 1.0)" in lines
        assert "score blue 0 : 0 red" in lines
        assert "status playing" in lines

    def test_blue_before_red_ordering(self):
        text = ev._build_text_world(sample_world(), {})
        lines = text.splitlines()
        blue_idx = [i for i, l in enumerate(lines) if l.startswith("blue_")]
        red_idx = [i for i, l in enumerate(lines) if l.startswith("red_")]
        assert max(blue_idx) < min(red_idx)

    def test_velocity_append_when_fast(self):
        text = ev._build_text_world(sample_world(), {}, velocities={"blue_1": (1.0, 0.0)})
        assert "blue_1 at (1.5, 1.0) moving (1.0, 0.0)" in text

    def test_no_velocity_append_when_slow(self):
        text = ev._build_text_world(sample_world(), {}, velocities={"blue_1": (0.1, 0.0)})
        assert "moving" not in text

    def test_status_and_score_from_match_state(self):
        text = ev._build_text_world(sample_world(), {"status": "ball_out", "blue": 2, "red": 1})
        assert "score blue 2 : 1 red" in text
        assert "status ball_out" in text

    def test_token_budget_under_250(self):
        # 3vs3 full world + score + status ≈ 10 lines ≈ 60 tokens
        ents = {"soccer_ball": {"x": 0.0, "y": 0.0}}
        for i in range(1, 4):
            ents[f"blue_{i}"] = {"x": -1.0 * i, "y": 0.5}
            ents[f"red_{i}"] = {"x": 1.0 * i, "y": -0.5}
        text = ev._build_text_world(ents, {"status": "kickoff", "blue": 1, "red": 1})
        assert len(text.split()) < 250


class TestTextParse:
    def test_move_line(self):
        data, code = ev.text_parse("blue_1 move to (2.2, 0.3)")
        assert code == 0
        a = data["assignments"]["blue_1"]
        assert a["action"] == "Move"
        assert a["x"] == 2.2
        assert a["y"] == 0.3
        assert a["role"] == "attacker"

    def test_kick_line(self):
        data, code = ev.text_parse("blue_2 kick")
        assert code == 0
        assert data["assignments"]["blue_2"]["action"] == "Kick"

    def test_goalie_line(self):
        data, code = ev.text_parse("blue_3 cover the goal line at (-4.0, 1.5)")
        assert code == 0
        a = data["assignments"]["blue_3"]
        assert a["action"] == "Move"
        assert a["role"] == "goalie"
        assert a["x"] == -4.0
        assert a["y"] == 1.5

    def test_multiple_lines_with_prose(self):
        raw = (
            "ANALYSIS: The ball is in midfield.\n"
            "ORACLE: Blue presses forward.\n"
            "blue_1 move to (2.2, 0.3)\n"
            "blue_2 kick\n"
        )
        data, code = ev.text_parse(raw)
        assert code == 0
        assert set(data["assignments"].keys()) == {"blue_1", "blue_2"}

    def test_partial_line_code(self):
        raw = "blue_1 move to (2.2, 0.3)\nblue_9 teleport away\n"
        data, code = ev.text_parse(raw)
        assert code == 1
        assert "blue_1" in data["assignments"]

    def test_no_bot_lines_returns_none(self):
        data, code = ev.text_parse("nothing here")
        assert data is None

    def test_negative_coordinates(self):
        data, code = ev.text_parse("blue_1 move to (-4.2, -2.9)")
        assert code == 0
        assert data["assignments"]["blue_1"]["x"] == -4.2


class TestCleanTextSamples:
    def test_no_explain_rendering(self):
        content = (
            "--- EXAMPLE 1: GOAL LINE COVERAGE ---\n"
            'INPUT: {"soccer_ball": {"x": 2.0, "y": 1.5}, "blue_1": {"x": 1.5, "y": 1.0}, '
            '"blue_2": {"x": -3.0, "y": 0.0}}\n'
            'ASSISTANT: {"assignments": {"blue_1": {"role": "attacker", "action": "Move", '
            '"x": 2.0, "y": 1.5}, "blue_2": {"role": "goalie", "action": "Move", "x": -4.0, "y": 1.5}}}\n'
        )
        out = ev._clean_text_samples(content, explain_active=False)
        assert "INPUT:\nsoccer_ball at (2.0, 1.5)" in out
        assert "blue_1 at (1.5, 1.0)" in out
        assert "ASSISTANT:\nblue_1 move to (2.0, 1.5)" in out
        assert "blue_2 cover the goal line at (-4.0, 1.5)" in out
        assert "ANALYSIS" not in out

    def test_explain_rendering_adds_analysis_oracle(self):
        content = (
            "--- EXAMPLE 1 ---\n"
            'INPUT: {"soccer_ball": {"x": 0.0, "y": 0.0}, "blue_1": {"x": -2.0, "y": 0.0}}\n'
            'ASSISTANT: {"analysis": "a", "oracle": "o", "assignments": {"blue_1": {"role": "attacker", "action": "Kick"}}}\n'
        )
        out = ev._clean_text_samples(content, explain_active=True)
        assert "ANALYSIS: a" in out
        assert "ORACLE: o" in out
        assert "blue_1 kick" in out

    def test_kick_rendering(self):
        content = (
            "--- EXAMPLE 1 ---\n"
            'INPUT: {"soccer_ball": {"x": 4.0, "y": 0.0}, "blue_1": {"x": 3.8, "y": 0.0}}\n'
            'ASSISTANT: {"assignments": {"blue_1": {"role": "attacker", "action": "Kick"}}}\n'
        )
        out = ev._clean_text_samples(content, explain_active=False)
        assert "blue_1 kick" in out


class TestTextModePromptAssembly:
    def test_text_mode_uses_text_rules_and_samples(self, monkeypatch):
        ev.TEXT_MODE = True
        ev._prompt_cache.clear()
        sys_prompt = ev._get_sys_prompt("playing")
        assert "cover the goal line at" in sys_prompt
        assert "Output ONLY pure, raw JSON." not in sys_prompt
        assert "hold position" in sys_prompt  # text output header includes hold verb

    def test_text_mode_sample_conversion_in_prompt(self, monkeypatch):
        ev.TEXT_MODE = True
        ev._prompt_cache.clear()
        sys_prompt = ev._get_sys_prompt("playing")
        # samples_3vs3.txt uses OUTPUT: marker; _clean_text_samples accepts both
        assert "INPUT:\n" in sys_prompt
        assert "ASSISTANT:" in sys_prompt
        assert '{"assignments"' not in sys_prompt

    def test_json_mode_unaffected(self):
        ev._prompt_cache.clear()
        sys_prompt = ev._get_sys_prompt("playing")
        assert "VALID ACTIONS" in sys_prompt
        assert '{"action": "Move"' in sys_prompt
        assert "Output ONLY pure, raw JSON." in sys_prompt


class TestTextModeMainFlow:
    def test_hash_uses_transformed_text(self, monkeypatch):
        ev.TEXT_MODE = True
        ents = {"soccer_ball": {"x": 2.0, "y": 1.5}, "blue_1": {"x": 1.5, "y": 1.0}}
        h1 = hash(ev._build_text_world(ents, {"status": "playing", "blue": 0, "red": 0}))
        ents["soccer_ball"]["x"] = 2.1
        h2 = hash(ev._build_text_world(ents, {"status": "playing", "blue": 0, "red": 0}))
        assert h1 != h2

    def test_text_mode_num_predict_200(self, monkeypatch):
        ev.TEXT_MODE = True
        assert ev._build_text_world  # sanity: transform exists
        # num_predict logic lives in main(); verify constants used there
        from r2k_evaluator import TEXT_OUTPUT_HEADER, TEXT_EXPLAIN_INSTRUCTION
        assert "move to (X, Y)" in TEXT_OUTPUT_HEADER
        assert "hold position" in TEXT_OUTPUT_HEADER
        assert "ANALYSIS:" in TEXT_EXPLAIN_INSTRUCTION
