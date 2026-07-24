# Scenario Directory

## Naming Convention

Filenames follow the pattern `<mode>_<tactic>.json` where:

- **`<mode>`** (filename prefix before first `_`) selects prompt fragments in `setup_r2k.py:111`:
  `mode = args.scenario.split('_')[0]` → resolves `rules_{mode}.txt` and `samples_{mode}.txt` from `strategy/fragments/`.
- **`<tactic>`** is a free-form descriptive suffix for the tactical test situation.

Example: `3vs3_defensive_crisis.json` → mode `3vs3` → loads `rules_3vs3.txt` + `samples_3vs3.txt`.

**Warning:** When adding new scenarios, the filename prefix MUST match a mode whose `rules_<mode>.txt` and `samples_<mode>.txt` fragment files exist in `strategy/fragments/`, or `setup_r2k.py` will fall back to `rules_{mode}.txt` (which may not be the intended behavior).

## Two Schema Generations

### v5 (legacy, 8 files)

Keys: `scene_type`, `label`, `entities`.

Files: `0vs1_default.json`, `1vs0_default.json`, `1vs1_default.json`, `2vs1_default.json`, `2vs2_default.json`, `3vs1_default.json`, `3vs2_default.json`, `3vs3_default.json`.

These are retained for backward compatibility with pre-v6 launch configurations. Do not modify their schema.

### v6 (test matrix, 9 files)

Keys: `scenario_name`, `mode`, `tactical_situation`, `entities`.

Files: `3vs3_attack_center.json` (TC-01), `3vs3_attack_wing.json` (TC-02), `3vs3_defensive_crisis.json` (TC-03), `3vs3_fast_counter.json` (TC-04), `3vs3_pressing_trap.json` (TC-05), `3vs3_long_shot.json` (TC-06), `3vs3_contain_delay.json` (TC-07), `3vs3_def_transition.json` (TC-08), `3vs3_high_line.json` (TC-09).

`scenario_name` MUST match the filename (without `.json`) — `batch_evaluator.py` uses it for run identification. `mode` explicitly documents which prompt fragment set the scenario belongs to. `tactical_situation` is documentation only.

TC-10 (`3vs3_kick_in.json`) is deferred to Phase 5 pending referee v6 ball-out detection.

## Notable Overlap

`3vs3_default.json` (v5 schema) and `3vs3_attack_center.json` (v6 TC-01) share identical entity positions by design — TC-01 IS the baseline kickoff scenario. The v5 file uses `scene_type`/`label`; the v6 file uses `scenario_name`/`mode`/`tactical_situation`.

## Code Coupling

- `setup_r2k.py` — reads `entities` from JSON, derives `mode` from filename prefix, assembles prompt from `strategy/fragments/`.
- `test_integration_smoke.py` — accepts both v5 and v6 schemas (`scene_type` or `scenario_name`).
- `batch_evaluator.py` — uses `scenario_name` field for run identification (per spec §3.1).