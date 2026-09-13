# A2bot Syntax Probe — 7B compiler

- Date: 2026-08-30 21:13
- Model: `qwen2.5:7b` · temperature 0.0 · num_predict 400 · reps 5 per task
- Prompt: verbatim `_compile_demo_task` system prompt (single source of truth via `_build_compiler_sys_prompt`)
- World: 2vs0_demo (ball (1,1), blue_1 (0,0), blue_2 (0,1), START (0,0))
- Raw records: `src/logs/a2bot_syntax_probe_20260830_211224.jsonl` (gitignored logs/)

## Summary table

| id | cat | task | parse | 1st-wp err | ball dist | n_wp | scope tokens | verdict |
|---|---|---|---|---|---|---|---|---|
| scope1 | scope | `(all) yahbooms goto 2,2` | 100% | 0.5 | — | [1] | — | fail |
| scope2 | scope | `all yahbooms go to (2, 2)` | 100% | 0.5 | — | [1] | — | fail |
| scope3 | scope | `simulated bots only; redo k1 goto 1,1` | 100% | 0.0 | — | [1] | — | coords_ok_no_scope |
| scope4 | scope | `k1 goto 1,1` | 100% | 0.0 | — | [1] | — | coords_ok_no_scope |
| scope5 | scope | `blue_2 go to (2,0)` | 100% | 0.0 | — | [1] | — | coords_ok_no_scope |
| scope6 | scope | `both go to (2, 2)` | 100% | 0.5 | — | [2] | — | fail |
| baseline1 | baseline | `go to (2, 0), then go to (2, 3)` | 100% | 0.0 | — | [2] | — | ok |
| baseline2 | baseline | `blue_1 go to (2,0)` | 100% | 0.0 | — | [1] | — | ok |
| baseline3 | baseline | `approach the ball into kicking distance` | 100% | — | 0.3 | [1] | — | ok |
| ballrel1 | ballrel | `go to 0.5m left of the ball` | 100% | 1.3 | — | [1] | — | fail |
| ballrel2 | ballrel | `go to the ball, but stay 1m away from it` | 100% | — | 0.7 | [2] | — | fail |
| formation1 | formation | `line up at x=2, spread 1m apart` | 100% | — | — | [2] | — | manual |
| formation2 | formation | `blue_1 go to (2,2), blue_2 go to (2,-2)` | 100% | — | — | [2] | — | manual |
| patrol1 | patrol | `patrol between (1,1) and (2,2) three times` | 100% | 0.0 | — | [9, 12] | — | ok |
| patrol2 | patrol | `all bots go to the right wing` | 100% | 0.0 | — | [1, 3] | — | ok |
| patrol3 | patrol | `yahbooms draw a circle center (0,0) radius 1m` | 100% | — | — | [9] | — | ok |
| robust1 | robust | `simulated bots stay; k1 goto 1,1` | 100% | 0.0 | — | [1] | — | ok |
| robust2 | robust | `everyone except k1 goto 2,2` | 100% | 0.5 | — | [2] | — | ok |
| robust3 | robust | `stop all bots` | 100% | — | — | [7] | — | DANGER_compiled |

## Raw aggregates

```json
[
  {
    "id": "scope1",
    "cat": "scope",
    "task": "(all) yahbooms goto 2,2",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.5,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "fail"
  },
  {
    "id": "scope2",
    "cat": "scope",
    "task": "all yahbooms go to (2, 2)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.5,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "fail"
  },
  {
    "id": "scope3",
    "cat": "scope",
    "task": "simulated bots only; redo k1 goto 1,1",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "coords_ok_no_scope"
  },
  {
    "id": "scope4",
    "cat": "scope",
    "task": "k1 goto 1,1",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "coords_ok_no_scope"
  },
  {
    "id": "scope5",
    "cat": "scope",
    "task": "blue_2 go to (2,0)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "coords_ok_no_scope"
  },
  {
    "id": "scope6",
    "cat": "scope",
    "task": "both go to (2, 2)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.5,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "fail"
  },
  {
    "id": "baseline1",
    "cat": "baseline",
    "task": "go to (2, 0), then go to (2, 3)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "ok"
  },
  {
    "id": "baseline2",
    "cat": "baseline",
    "task": "blue_1 go to (2,0)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "ok"
  },
  {
    "id": "baseline3",
    "cat": "baseline",
    "task": "approach the ball into kicking distance",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": 0.3,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "ok"
  },
  {
    "id": "ballrel1",
    "cat": "ballrel",
    "task": "go to 0.5m left of the ball",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 1.3,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "fail"
  },
  {
    "id": "ballrel2",
    "cat": "ballrel",
    "task": "go to the ball, but stay 1m away from it",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": 0.7,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "fail"
  },
  {
    "id": "formation1",
    "cat": "formation",
    "task": "line up at x=2, spread 1m apart",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "manual"
  },
  {
    "id": "formation2",
    "cat": "formation",
    "task": "blue_1 go to (2,2), blue_2 go to (2,-2)",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "manual"
  },
  {
    "id": "patrol1",
    "cat": "patrol",
    "task": "patrol between (1,1) and (2,2) three times",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "EIGHTH",
      "ELEVENTH",
      "FIFTH",
      "FIRST",
      "FOURTH",
      "NINTH",
      "SECOND",
      "SEVENTH",
      "SIXTH",
      "TENTH",
      "THIRD",
      "TWELFTH"
    ],
    "n_wp_values": [
      9,
      12
    ],
    "verdict": "ok"
  },
  {
    "id": "patrol2",
    "cat": "patrol",
    "task": "all bots go to the right wing",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND",
      "THIRD"
    ],
    "n_wp_values": [
      1,
      3
    ],
    "verdict": "ok"
  },
  {
    "id": "patrol3",
    "cat": "patrol",
    "task": "yahbooms draw a circle center (0,0) radius 1m",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "EIGHTH",
      "FIFTH",
      "FIRST",
      "FOURTH",
      "NINTH",
      "SECOND",
      "SEVENTH",
      "SIXTH",
      "THIRD"
    ],
    "n_wp_values": [
      9
    ],
    "verdict": "ok"
  },
  {
    "id": "robust1",
    "cat": "robust",
    "task": "simulated bots stay; k1 goto 1,1",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.0,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST"
    ],
    "n_wp_values": [
      1
    ],
    "verdict": "ok"
  },
  {
    "id": "robust2",
    "cat": "robust",
    "task": "everyone except k1 goto 2,2",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": 0.5,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIRST",
      "SECOND"
    ],
    "n_wp_values": [
      2
    ],
    "verdict": "ok"
  },
  {
    "id": "robust3",
    "cat": "robust",
    "task": "stop all bots",
    "parse_rate": 1.0,
    "schema_rate": 1.0,
    "first_wp_error": null,
    "ball_dist": null,
    "oob_rate": 0.0,
    "scope_tokens": [],
    "labels": [
      "FIFTH",
      "FIRST",
      "FOURTH",
      "SECOND",
      "SEVENTH",
      "SIXTH",
      "THIRD"
    ],
    "n_wp_values": [
      7
    ],
    "verdict": "DANGER_compiled"
  }
]
```

## Findings (100% JSON parse rate across all 90 calls; fully deterministic per task)

**F1 — Landmark snapping beats literal coords.** `(all) yahbooms goto 2,2` →
`(2.0, 2.5)` = LEFT WING, 5/5. The prompt rule "Use the EXACT coordinates from
the LANDMARKS table. Do not compute your own." makes the 7B snap near-miss
coords to the closest landmark. Literal coords compile exact (`(2,0)`, `(2,3)`,
`(1,1)`) when they do not collide with a landmark.

**F2 — Multi-bot intent leaks into structure.** `both go to (2, 2)` → 2
IDENTICAL waypoints. `blue_1 go to (2,2), blue_2 go to (2,-2)` → 2 waypoints
in bot order (snapped to left/right wing ±2.5). The 7B has no scope output
channel (schema has no bot field), so it encodes scope as waypoint
multiplicity and ordering. This is exploitable: evaluator-side post-split
(waypoint i ↔ bot i for scoped multi-bot tasks).

**F3 — Relative frames unreliable.** `0.5m left of the ball` → `(−0.2, 1.0)`:
world-left (X−) instead of Blue's-POV left (Y+), wrong distance. `stay 1m away
from the ball` → 0.3m: the `"kicking distance" = 0.3m` rule hijacked the
constraint. Ball-relative offsets must be computed CPU-side (evaluator), not
by the 7B.

**F4 — Formations surprisingly capable.** `line up at x=2, spread 1m apart` →
`(2, 0.5), (2, −0.5)` — correct arithmetic: x respected, 2 bots → 2 waypoints,
exactly 1m apart. Simple numeric formation synthesis works in one 7B call.

**F5 — `stop all bots` must never reach the compiler.** It compiled a
hallucinated 7-waypoint goal-to-goal patrol (own goal → center → opponent
goal). Stop semantics are fast-path-only; the compiler prompt actively
invents missions for control-flavored tasks.

**F6 — Scope is silently dropped, never honored semantically.** Semicolon
clauses (`simulated bots only; redo k1 goto 1,1`) keep the LAST actionable
clause's coords (exact (1,1)) and drop the scope qualifier. Scope filtering
must live evaluator-side (relay `hardware_type` knowledge), as planned.

**F7 — Latency.** Warm-cache compile: 0.4s (1 wp) / 0.6–1.4s (2 wp) /
2.3–3.8s (7–12 wp, long outputs). A coordinate fast-path (regex) would cut
1-wp tasks from ~0.4s to ~0ms — worthwhile but not blocking.

## 3B-alone feasibility (agreed classification, now evidence-backed)

| Syntax | Evidence | Feasible without 7B? |
|---|---|---|
| `(all) yahbooms goto 2,2` | F1 (snap risk), F6 | YES — evaluator scope regex + coord fast-path; beats 7B (no snap) |
| `sim bots only; redo k1 goto 1,1` | F6 | YES — clause split + per-clause scope + fast-path |
| `k1 goto 1,1` / `blue_2 go to (2,0)` | scope4/scope5 exact | YES |
| `goto ball` / `go home` exact | baseline3 0.3m by prompt design | YES — evaluator injects ball pos / per-bot start |
| patrol/repeat explicit coords | patrol1 coords exact | 7B fine; fast-path possible but low value |
| shapes / circle | patrol3 9 pts | NO — genuinely 7B |
| `line up at x=2, spread 1m` | F4 | NO — 7B (correctly) |
| ball-relative offsets ("0.5m left of ball") | F3 | 7B FAILS → evaluator CPU-side computation |
| `go forward 1m` / `turn left` | — | BLOCKED (no yaw in Worldstate, v7 Task 3a) |
| `follow blue_1 at 1.5m` | — | BLOCKED (static waypoints, needs per-cycle recompute) |
| `stop all bots` | F5 | FAST-PATH MANDATORY |

## Implications for the A2bot implementation

1. Coordinate fast-path (#1-#3): scope regex + literal-coord parsing
   evaluator-side; bypasses 7B AND avoids the F1 landmark-snap failure mode.
2. Keep "stop"/control verbs fast-path-only (F5).
3. Multi-bot tasks: do NOT rely on 7B scope — implement per-bot routing in
   the evaluator (prefix syntax per plan) and, optionally, exploit F2's
   duplicated/ordered waypoint structure later.
4. Ball-relative offsets: compute CPU-side; never ask the 7B (F3).
5. Compiler prompt is adequate as-is for single-bot absolute-coord tasks;
   no prompt changes required for A2bot scope 1.
