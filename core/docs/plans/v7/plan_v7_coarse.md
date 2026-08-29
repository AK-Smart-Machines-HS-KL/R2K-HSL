# v7 Coarse Plan (skeleton — assembled from mgt_v7.md at wrapping-up)

> Status: SKELETON. Content lands after mgt summaries are reviewed.
> Detailed v7 planning is explicitly OUT OF SCOPE for this session.

## Phase 0 — Entry gates
- [ ] v6.8 done: clamp alignment, kick placeholder removed, odom watch
- [ ] K1-PROBE hardware verification executed + logged (k1_kick_head_vendor_audit.md, 'Hardware probe protocol')
- [ ] PR #17 merged (vision stack on main); FastDDS patch merged
- [x] Fleet: 2x Education confirmed; Professional NOT ordered (budget request — justification chain below)

## Phase 1 — TeamCaptain core (WS 1+2)
- [ ] Requirements doc from SP/WIN reports + 100-match priorities
- [ ] W1-W6 watchdog scenarios: Option A (re-prompt) vs B (second model) decision report
- [ ] Path executor + augmented world model (optimized_path.json)
- [ ] Role assignment to CPU (goalie role-lock, passing, defensive recovery)
- [ ] Score-function leftovers (last_toucher, BALL_POSITION_GAIN, bonus race)

## Phase 2 — K1 integration (WS 3, parallel)
- [ ] Bridge kick action = kVisualKick (kV1/kV2 probe first)
- [ ] Soccer-mode (4) evaluation vs custom skills
- [ ] Odometry-closed control (odometer_state subscription + 2031 reset)
- [ ] Head control (2004/2043) in demo + match modes
- [ ] Vision stack integration (PR #17) for ball/field perception

## Phase 3 — Edge-LLM (WS 4, GPU-budget permitting)
- [ ] Stage 0: gpt-oss:20b + qwen3:30b quality probes vs 3B baseline
- [ ] Stage 1: vLLM latency calibration (4.4x bandwidth scaling)
- [ ] Stage 0/1 evidence -> budget decision -> order Professional (AGX Orin 32GB) -> on-robot deployment plan

## Phase 4 — Calibration & hardening (WS 5+6)
- [ ] Yaw in Worldstate (scrum 3a); visual markers; single_k1 relay
- [ ] 14B/32B calibration probes; async compiler
- [ ] Llama 100-match, 15-scenario text probe, U22/U24 report
- [ ] Dead code + untracked artifacts cleanup; C3 2vs2 fix

## Out of scope
GUI features, opencode offers, trailer hitch, anything needing K1-PROBE results before the verification session.
