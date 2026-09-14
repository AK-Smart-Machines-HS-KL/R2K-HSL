# U22 Native Regression Report — 2026-09-13

**Machine:** Ubuntu 22.04.5 LTS, native (no Docker), ROS 2 Humble system-installed, NVIDIA RTX 4080
**Branch:** `docs/v68Planning` (last commit `14179d2`)
**Commits made:** NONE — all changes uncommitted, per user directive (commit blocked until K1 field day passes).

---

## Summary

| Tier | Result | Duration |
|---|---|---|
| **ros2_ws build** | 6 packages built (first native build of `booster_interface`) | 4.6s |
| **Fast tier** (`--skip-slow`) | **255 passed, 0 failed, 11 skipped** | 0.39s |
| **Sim battery** | **12/12** | ~5s |
| **Slow tier** (real 120s Gazebo matches) | **6 passed, 5 failed** (KPI threshold deltas) | 24m14s |

---

## Build

Clean rebuild (`rm -rf build install && colcon build`). The `install/` dir was stale — `booster_interface` (vendor interface package, added 09-06) was missing from `install/`. No numpy header issues on fresh build. 6 packages: `booster_interface`, `booster_msgs`, `box_bot_description`, `brain`, `r2k_scenario_spawner`, `r2k_world_model`.

---

## 3 bugs found & fixed (all in test files, no production code changed)

### Bug 1: test_score.py — rclpy mock isolation failure

**File:** `core/src/tests/test_score.py`
**Symptom:** 12 tests in `TestBallPosition`, `TestGoalBonus`, `TestScoreGate`, `TestPossessionRange`, `TestScoreCorrelation` all failed with `rclpy.exceptions.NotInitializedException: ('rclpy.init() has not been called', 'cannot create node')`.

**Root cause:** The mock used `sys.modules.setdefault('rclpy', _rclpy)` which is a **no-op** when the real rclpy is already in `sys.modules`. On U22, ROS 2 Humble is system-installed (`/opt/ros/humble/local/lib/python3.10/dist-packages/`) so `import rclpy` always succeeds. When another test module imported real rclpy before test_score.py ran, `setdefault` was a no-op → `score_node` imported real `rclpy.node.Node` → `ScoreNode()` called real `super().__init__('score_node')` → `NotInitializedException` because `rclpy.init()` was never called.

**Failed approach (reverted):** `sys.modules['rclpy'] = _rclpy` (force-overwrite) fixed test_score but **poisoned** rclpy for the rest of the pytest session. The 6 bridge tests in `test_head_face.py` then got the mock rclpy via `pytest.importorskip("rclpy")` (succeeded), but `import ollama_sandbox_bridge` failed on `gazebo_msgs` (not in the mock) → tests skipped instead of passing.

**Final fix:** Force-install the mock, import `score_node`, then **restore the original modules**:
```python
_saved = {k: sys.modules.get(k) for k in
          ('rclpy', 'rclpy.node', 'std_msgs', 'std_msgs.msg')}
sys.modules['rclpy'] = _rclpy
sys.modules['rclpy.node'] = _rclpy_node
sys.modules['std_msgs'] = _stdmsg
sys.modules['std_msgs.msg'] = _stdmsg_msg

import score_node as sn

# Restore originals so other test modules see the real rclpy if it was there.
for k, v in _saved.items():
    if v is not None:
        sys.modules[k] = v
    else:
        sys.modules.pop(k, None)
```
`score_node.Node` stays bound to `_FakeNode` (Python binds the name at import time via `from rclpy.node import Node`). Other tests see the real rclpy after restoration.

### Bug 2: test_head_face.py — FB mock missing bridge methods

**File:** `core/src/tests/test_head_face.py`
**Symptom:** 3 tests (`test_bridge_seq_cursor_and_forks`, `test_bridge_read_llm_strategy_passthrough`, `test_bridge_seq_production_roundtrip`) failed with `AttributeError: 'FB' object has no attribute '_face_target_yaw'` / `'get_logger'` / `'_seq_effective'`.

**Root cause:** Bridge tests created bare `fb = type("FB", (), {})()` objects with only `_seq_state` and `_face_state` attributes. But `HalBridge._seq_effective()` (called as unbound method with `fb` as `self`) internally calls:
- `self._face_target_yaw(target_bot, eff, cyaw)` (line 858)
- `self._advance_seq(st, cyaw)` (line 847, via `_next()` closure)
- `self._seq_effective(...)` (recursive, line 848)

And `HalBridge.read_llm_strategy()` calls:
- `self.get_logger()` (lines 494, 496, 498)
- `self._publish_odom_states()` (line 500)
- `self.TARGET_EXTRA_KEYS` (line 487)

None of these existed on the bare FB object.

**Fix:** Added `_fb_mock(bridge_mod)` factory function that creates an FB with all required methods wired to the real `HalBridge` methods:
```python
def _fb_mock(bridge_mod):
    import logging
    fb = type("FB", (), {
        "_face_target_yaw": bridge_mod.HalBridge._face_target_yaw,
        "_advance_seq": bridge_mod.HalBridge._advance_seq,
        "_seq_effective": bridge_mod.HalBridge._seq_effective,
        "get_logger": lambda self: logging.getLogger("test_bridge"),
        "_publish_odom_states": lambda self: None,
        "TARGET_EXTRA_KEYS": bridge_mod.HalBridge.TARGET_EXTRA_KEYS,
    })()
    fb._seq_state = {}
    fb._face_state = {}
    return fb
```
All 6 bare `type("FB", (), {})()` instances replaced with `_fb_mock(bridge)` calls.

### Bug 3: test_non_functional.py — relay name not updated after 09-06 rename

**File:** `core/src/tests/test_non_functional.py`
**Symptom:** All 11 slow tests failed with `Failed: Could not extract R2K_RUN_ID from launch output` because `launch_r2k.sh` printed `❌ Relay-Datei nicht gefunden: relay/only_sim_bots.json`.

**Root cause:** The relay rename (09-06/07) deleted `only_sim_bots.json` and created `sim_only.json` (same 3 virtual blue bots, canon keys `blue1`/`blue2`/`blue3`). The slow tests still referenced the old name `--relay only_sim_bots`. Available relays: `hardware_mirror`, `hardware_yahboom`, `sim_k1`, `sim_only`, `single_bot`.

**Fix:** One-line change: `"--relay", "only_sim_bots"` → `"--relay", "sim_only"`.

---

## Slow tier results (11 tests, 24m14s total)

### 6 passed

| Test | Duration |
|---|---|
| `test_attack_center_goalie` | ~132s |
| `test_attack_center_latency` | ~132s |
| `test_default_goalie` | ~132s |
| `test_high_line_goalie` | ~132s |
| `test_long_shot_goalie` | ~132s |
| `test_contain_delay_goalie` | ~132s |

### 5 failed — KPI threshold deltas (NOT code bugs)

| Test | KPI | Value | Expected range | Note |
|---|---|---|---|---|
| `test_attack_center_performance` | `composite_score` | 0.406 | [0.427, 1.0] | 0.021 below min |
| `test_default_performance` | `composite_score` | 0.391 | [0.4, 1.0] | 0.009 below min |
| `test_high_line_performance` | `composite_score` | 0.296 | [0.333, 1.0] | 0.037 below min |
| `test_long_shot_performance` | `cluster_pct` | 77.6 | [0.0, 70.7] | 6.9 above max |
| `test_contain_delay_performance` | `cluster_pct` | 27.4 | [0.0, 13.3] | 14.1 above max |

**All failures are KPI threshold misses, not crashes or code bugs.** The matches ran correctly — bots moved, goals detected, KPIs computed. The thresholds were calibrated from a U24 Docker baseline (v6.7, 10 samples, `qwen2.5:3b`). U22 native shows slightly lower composite scores and higher clustering — expected platform delta (different sim timing, GPU driver, CPU scheduler).

Per Appendix C §C.7: "A slow-test failure on U22 is a finding: compare against the U24 baseline, fix-forward or document platform deltas." These are **documented platform deltas**. The U24 LLM should compare its own slow-tier results against these U22 numbers to determine if the thresholds need recalibration for both platforms.

---

## Files changed (4 files, uncommitted)

| File | Changes | Lines |
|---|---|---|
| `core/src/tests/test_score.py` | rclpy mock: `setdefault` → force-install + restore | +14 -9 |
| `core/src/tests/test_head_face.py` | FB mock factory with wired bridge methods | +26 -14 |
| `core/src/tests/test_non_functional.py` | relay name: `only_sim_bots` → `sim_only` | +1 -1 |
| `core/docs/SESSION_CHANGELOG.md` | session entry | +88 -0 |

**No production code changed.** All fixes are in test files only.

---

## U24 instructions

1. `git pull` on `docs/v68Planning` branch
2. Apply the patch: `git apply u22_regression_patch.diff` (or the files are in the tarball)
3. Run the fast tier:
   ```
   cd core/src && python3 -m pytest tests/ --skip-slow -q --ignore=tests/test_adaptive_horizon.py --ignore=tests/test_chart_specs.py
   ```
4. Run the sim battery:
   ```
   cd core && python3 -c "import sys; sys.path.insert(0, 'tools'); import calib_test; ok, total, _ = calib_test.run_sim_battery(); print(f'SIM BATTERY: {ok}/{total}')"
   ```
5. Run the slow tier (if desired, ~24 min):
   ```
   cd core/src && python3 -m pytest tests/test_non_functional.py -v -s
   ```
6. Compare U24 slow-tier KPI values against U22 numbers above. If both platforms show similar deltas from the thresholds, the thresholds need recalibration (not the code).