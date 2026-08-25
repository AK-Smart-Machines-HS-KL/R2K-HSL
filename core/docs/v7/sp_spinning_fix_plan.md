# SP Experiment Plan — Prompt-Only Spinning Fix ("Focus the Ball")

> **Status:** EXECUTED 2026-08-22 (late session) — **NEGATIVE RESULT, no arm
> qualified.** Full report: `src/results/probe_sp_report.md`. B13 remains
> applied; no SP variant shipped. Key insight: spinning = goalie-Y limit
> cycle + kicker flapping + physics jitter defeating the content-hash skip —
> prompt cannot remove it; durable fix is the v7 TeamCaptain (CPU planner).
> **Control:** B13 samples (currently applied to `samples_3vs3.txt`).
> **Hard constraint:** fragments/samples ONLY — NO bridge/evaluator changes.

## Diagnosis (2026-08-22, user match `3vs3_default` 19:37)

| Bot | Path | Net displacement | Micro-jitter windows |
|---|---|---|---|
| blue_1 | 34m | 0.1m | 54% |
| blue_2 | 30m | 0.1m | 59% |
| blue_3 | 45m | 3.7m | 34% |

- Ball quasi-static (p50: 2mm/0.2s) → spinning is NOT ball-chasing.
- Mechanism: LLM re-derives targets every ~684ms; slightly different targets
  land outside the bridge's 0.15m deadband → yaw re-aim churn (the visible
  spinning) → 5cm nudge → next call moves target again.
- Root cause: **targets are an unstable function of world state**.
- Hypothesis: ball-relative default targets are a SMOOTH function of ball
  position → static ball ⇒ identical targets ⇒ evaluator content-hash skip
  fires ⇒ no LLM call ⇒ bots fully stop. Drifting ball ⇒ proportional,
  same-direction target drift ⇒ smooth re-aim.

## Arms (6)

| Arm | Change | Tests |
|---|---|---|
| SP0 | B13 as-is | control |
| SP1 | + DEFAULT POSITIONING rule in `rules_3vs3.txt`: non-kicking field bot → point between ball and own goal, 1.5m from ball, computed from the ball's position in the input | ball-relative anchoring |
| SP2t | + `{"action": "Hold"}` in VALID ACTIONS (`rules_core.txt`) + **tight gate**: "Hold only when already within 1m of your ball-relative position AND the ball is more than 2m from you" | Hold, passivity-gated |
| SP2l | Same + **loose gate**: "a bot already in a good position holds" | Hold, trust-the-model |
| SP3 | SP1 + better of SP2t/SP2l | combination |
| SP4 | B13 samples reworked: non-kicker Move targets moved onto ball-relative geometry (kicker identities + goalie anchors UNTOUCHED — preserve B13's tuned patterns) | sample channel |

## Sequence probe (extend `tools/probe_s1.py`)

Simulate the closed loop textually — 10 base situations × 5 successive states:
- **Drift test**: ball moves 0.2m/state, bots step toward previous targets →
  metrics: target displacement per step, heading swing (spinning proxy)
- **Freeze test**: ball static, bots at previous targets →
  metric: target reproduction rate (predicts content-hash skip → full stop)

## Metrics & pre-registered success criteria

| Metric | Pass criterion |
|---|---|
| Drift target displacement | ≤50% of SP0 |
| Heading swing | ≥50% reduction |
| Freeze index (static-ball target drift) | ≈0 |
| Hold rate | SP2t < SP2l (gate validation); no >30% team-freeze |
| Canaries (ff_gk, goalie, pass, last_man) | B13 profile survives: ff ≤20%, goalie canary ≥67%, last_man ≥92% |
| Latency | ≤+40 tokens |

Budget: ~300 sequence calls + ~170 canary calls for the 2 finalists ≈ 6 min GPU.

## Live follow-up (separate decision)

6-8 matches vs the existing B13 10-match baseline (`s1_live_b13_raw.json`),
oscillation metrics (path-vs-net, reversals, jitter) + goals.

## Risks

- Hold passivity: A2 showed static-zone default — ungated Hold could freeze
  the whole team (SP2t vs SP2l isolates this).
- Rule-pattern interference: S1 finding 3 — every combo needs its own
  re-probe (canaries on ALL arms).
- SP4 is the riskiest edit (sample brittleness; S1 iteration-2 evidence).
