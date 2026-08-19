# Pit of Nice Ideas — v7 Backlog

> Everything deferred from v6.5 that is worth revisiting in v7 or beyond.
> Moved here from the main repo tree to keep the working directory clean.

---

## 1. Watchdog Divergence Scenarios (Phase W)

**Source:** 2026-08-03 session, deferred from v6.4. 6 synthetic scenarios testing
LLM failure modes. Never run in Gazebo — diagnostic only.

**Location:** `docs/v7/scenarios/w1_*.md` .. `w6_*.md`

| Scenario | Failure mode |
|---|---|
| w1_goalie_abandonment | LLM sends goalie forward, leaving goal open |
| w2_clustering_trap | LLM clusters all 3 bots near ball, no spreading |
| w3_wrong_direction_kick | LLM kicks toward own goal instead of clearing |
| w4_unmarked_attacker | LLM ignores unmarked red attacker near goal |
| w5_boundary_violation | LLM sends bot out of bounds |
| w6_passivity_trap | LLM holds all bots, nobody challenges ball |

**Planned use:** Test watchdog re-prompt (Option A) vs second-model monitor (Option B)
in v7 TeamCaptain. Write decision report.

---

## 2. Score Function Leftovers

### Suggestion 5: last_toucher for possession attribution
- U22 analysis (2026-08-12) suggested using `match_state.last_toucher` instead of
  nearest-bot distance for possession.
- Authoritative (referee-tracked) vs geometric (nearest-bot flips every frame).
- Deferred — bigger change, higher risk.

### BALL_POSITION_GAIN tuning
- v6.5 used 1.5 (score clamped at ±10 when ball deep in one half).
- v6.5 fix reduced to 0.8 (leaves headroom for goal bonus).
- v7 could use a non-linear function: `ball_x × gain × (1 - |ball_x|/4.5)`
  so contribution decreases near goal lines (avoids clamping without losing signal).

### Goal bonus race condition
- match_cb vs pos_callback ordering is not guaranteed in ROS 2.
- Current workaround: apply bonus in both callbacks with a flag to prevent
  double-application. Still has 1-frame delay in some cases.
- v7 fix: score_node reads from aggregated Worldstate.json (merged by
  state_aggregator) instead of subscribing to /world_positions directly.

---

## 3. TeamCaptain Architecture (ADR-A07)

**Design:** CPU-only ROS 2 node. LLM produces end-points → TeamCaptain plans
paths → Bridge executes. Downward compatible (if TeamCaptain absent, Bridge
falls back to direct PID).

**Components:**
- Path executor (`ai_tactics/path_executor.py`)
- Watchdog (divergence detection, re-prompt trigger)
- Augmented world model (future projection, velocity decay)
- Kick-abort coordinator (ball motion change detection)
- Optimized path output (`optimized_path.json`)

**Open questions:**
- Path planner threshold (when to replan?)
- Nav2 evaluation (use ROS 2 Nav2 stack or custom?)
- K1 trajectory replay format (api_id 2028)
- Odometry drift handling (Yahboom, K1)

---

## 4. Behavioral v7 Priorities (from 100-match benchmark)

| Priority | Description | Evidence |
|---|---|---|
| Goalie kick (role swap) | 0/100 matches — Blue plays 2v3 | Goalie never kicks, role-locking persists |
| Passing | blue_3 advances 63.6% but never receives | Kick goes to goal, not teammate |
| Defensive recovery | high_line: 14 red goals in 10 matches | Bots don't recover after turnover |
| Match duration | 42% draw rate | Consider 180s+ matches |

**Key insight:** 3B model is good at positioning, bad at coordination.
Role assignment must move to CPU planner (TeamCaptain) in v7.

---

## 5. Hardware Tasks (scrum_tasks.md)

| Task | Description | Status |
|---|---|---|
| 3a | Add gaze direction to Worldstate.json | Deferred to v7 |
| 5 | Yahboom trailer hitch mechanism | Deferred |
| 9 | Tech debt: clustering, score metrics, commits | v7 |
| 10 | Implement TeamCaptain architecture | v7 |
| 11 | K1 kick abort via ball motion detection | v7 |

---

## 6. Benchmark Leftovers

- **Llama 100-match benchmark** — NOT STARTED (GPU time consumed by Qwen 150)
- **Text-probe all 15 scenarios** — NOT STARTED
- **Analysis report: U22 vs U24, Qwen vs Llama** — NOT STARTED
- **150-match Qwen re-run post-fix** — BLOCKED on score fix commit

---

## 7. C3 Inter-Lingua Leftovers

- **2vs2 config artifact** — phantom blue_3 in 2vs2 samples causes 0% hard-pass.
  Need `samples_2vs2.txt` with 2-bot examples, or exclude 2vs2 from aggregate.
- **emp_restart_006** — mislabeled as 3vs3 but has 2 bots/team.
- **3vs3_default + 3vs3_overload hard-fail** — 8/10 and 2/10 fail. Not blocking.

---

## 8. Infrastructure Leftovers

- `prompt_utils.py` — dead code (not imported anywhere). Duplicate of
  `_clean_json_samples` in `r2k_evaluator.py`. Delete or consolidate in v7.
- `tools/benchmark.sh` — untracked, needs to be committed or recreated.
- `src/results/u22_qwen_150_raw.json` — untracked 150-match pre-fix baseline.
  Needed for before/after comparison. If lost, reconstructable from 150 logs.
- `umschaltmomente.jsonl` — deleted in 2026-08-11 cleanup. Reconstructable
  via `tools/umschalt_extractor.py` against match traces.

---

## 9. Calibration (v6.6 → v7)

**v6.6 implemented** (2026-08-19): `--demo` flag, interactive CLI, sequence
tracking (arrival detection, no weg queue), 3B executor + 7B compiler
two-model architecture. See `docs/calibration_cheat_sheet.md` for the full
command reference and model capabilities.

**v7 calibration tasks:**

| Task | Description | Design doc |
|---|---|---|
| Rotation/Face action | `face north/south/east/west`, `turn left/right`, `rotate N degrees` — bridge reads yaw from Gazebo, no tracker/colcon change needed | `docs/v7/calibration_rotation_design.md` (Option D) |
| Yaw in Worldstate | `tracker_node.py` adds yaw to `/world_positions` — enables compiler to know bot heading for relative commands | scrum Task 3a |
| Visual markers in Gazebo | Static SDF markers (red gate, blue cone, yellow marker, green pylon) in world file — requires colcon build | — |
| K1 relay profile | `relay/single_k1.json` — single K1 bot, no Gazebo sim | — |
| 14B/32B model testing | Probe calibration commands on qwen2.5:14b (9GB) and qwen2.5:32b Q3 (14GB) — both fit on 5090 | — |
| Dynamic entity spawning | Custom entities in scenario.json (markers, gates) — 4 code blockers (spawner, tracker, referee substring, score substring) | explore agent findings |
| Interactive compiler latency | Async compiler call (threading) — bot keeps moving during ~1.2s compilation | — |

**Probe results (2026-08-19, 26 tasks):**

| Model | Overall | Landmarks | Shapes | Coords | Ball | Combos |
|---|---|---|---|---|---|---|
| qwen2.5:3b | 73% (19/26) | 70% | 80% | 67% | 0% | 50% |
| qwen2.5:7b | 85% (22/26) | 90% | 100% | 100% | 100% | 50% |

**Key v6.6 lessons (see `LESSONS_LEARNED.md` §v6.6):**
- 3B is a transducer (string lookup), not a reasoner (no trig/distances/state)
- "stop" needs active brake (zero velocity), not skip (coasting unsafe)
- Waypoint table in user prompt (dynamic), not system prompt (cached)
- Grid-cell symbolic approach rejected (3B scored 0/20)
- Time-indexed CSV schedule rejected (boundary failures at thresholds)
- Wing = opponent half (Y positive = left from own goal POV)