# Pit of Nice Ideas — Trello version (team-friendly, 2026-09-14)

> Paste-ready for the team Trello board (Trello renders headings, bold, lists,
> code blocks — not tables). Source of truth: `pit_of_nice_ideas.md` §9 (same
> content, table form). Branch names follow the repo git rules; none exist
> unless a status says otherwise. Every term is explained on first use per the
> repo writing rule (AGENTS.md, "Writing style").

---

**P1 — LIDAR ball-detection node**
The robot should find the ball with its LIDAR distance sensor instead of needing the ball at a fixed demo spot. The Yahboom MS200 LIDAR and the simulator sensor produce identical data, so one code path works in both worlds. The design is already written and the demo ball sizes were picked at the lab session.
Branch: `feature/LidarBallNode` — not started

**P2 — Trailer demo: choreography + trailer detection by LIDAR**
Two-part robot demo: drive a trailer through a choreographed sequence (reverse into the fork hitch, push straight, rotate 45°), and detect the trailer's position with the LIDAR alone (two reflective posts, known geometry) instead of the unreliable camera stream. Both were displaced from the 6.8 phase by the robot field-day work; the choreography design is fully written.
Branch: `feature/TrailerDemo` — not started

**P3 — K1 camera vision (real ball and goal perception)**
Let the K1 humanoid see the ball and goals with its own camera (the vendor ships an image-analysis stack with a trained model). This is needed for playing on a real field without the simulator feeding positions. Blocked on a team decision: how to merge their pull request #17, which contains this stack but also a conflicting copy of the robot message definitions (see the "PR #17 merge check" Trello card, 2026-09-14).
Branch: `feature/import_vision` — exists, PR #17 open (team-owned)

**P4 — Score-function leftovers**
Three small fixes in the match scoring node: use the referee-tracked "last toucher" for ball possession instead of geometric distance (which flips every frame), replace the linear field-position score with a curve that stops saturating near the goal lines, and fix a race condition where the goal bonus can be applied twice or one frame late.
Branch: `refactor/ScoreLeftovers` — not started

**P5 — Per-bot state unification (code cleanup)**
The control bridge keeps five parallel dictionaries per robot (raw odometry, position estimate, subscriptions, last publish time). Unifying them into one record per robot removes the copy-paste seams that five new features have already duplicated. Deliberately deferred past the field day: medium risk, cleanup payoff.
Branch: `refactor/BotStateUnification` — not started

**P6 — Team-message protocol (vendor pattern)**
The vendor's RoboCup brain lets robots broadcast their state to teammates ("I am kicking now", my cost for chasing the ball) so they coordinate without a central planner. Worth studying for a multi-K1 fleet in v7; our current analog is the shared world-state file plus the LLM.
Branch: `feature/TeamMessages` — not started (vendor pattern documented 2026-09-12)

**P7 — Yahboom camera stream (udp-cam) rework**
The camera stream from the Yahboom robot itself (transmitted over udp-cam — not the simulator's GZWeb viewer) is unreliable, with documented connection and latency problems. A separate track, only relevant if the IFA-style demo returns; the LIDAR (P1) and K1 vision (P3) alternatives cover the same need.
Branch: `tools/UdpCamRework` — not started

**P8 — Silent prompt-change detection**
The fast regression tests fail on purpose whenever the LLM prompt fragments change without the frozen experiment baseline being refreshed — this is the only protection against unacknowledged prompt edits (the baseline = a snapshot of the prompt as it was during the v6.3 prompt-variant experiment). The fix: refresh the snapshot as part of every intentional prompt change, so "tests green" always means "prompt is exactly the version the team last reviewed".
Branch: `tests/SweepSnapshotRefresh` — not started

**P9 — opencode favorites cleanup**
Remove the underperforming NVIDIA nemotron models from the opencode editor's model-favorites list. Leftover from the v6.3 model-comparison experiments: they scored below the qwen baseline and carried a configuration inconsistency (different models received different output-format settings).
Branch: `tools/OpencodeFavorites` — not started

**P10 — GZWeb/GUI follow-ups (in development)**
The browser-based control-center prototype (web supervisor, 3D scene viewer, buttons) still needs hardening and follow-up widgets before it replaces the terminal workflows. The prototype code lives on its own branch and is already merged into the working line.
Branch: `feature/gzweb-experimental` — exists, in development

**P11 — User documentation pass**
The 40-file technical documentation drifted from reality (example: the Booster K1 integration spec still claims the odometry topic is silently relayed — disproven by the field day). One documentation pass to align all user-facing docs with what the system actually does now.
Branch: `docs/UserDocsPass` — not started

**P12 — Behavioral priorities (reference — owned by the TeamCaptain work, not an independent task)**
Evidence from the 100-match benchmark: the goalie never kicked in 100 matches, the third bot received 95% of all scoring passes, defensive recovery is missing after ball losses, 42% of matches end in a draw. These are resolved by the planned TeamCaptain node's role locks and pass coordination (v7 item 26 in the overview) — kept here so the evidence is not lost.
Branch: — (covered by the v7 TeamCaptain node)

---

**Dropped (2026-09-14):** the "--odom CSV watch" idea — superseded by the per-bot
odometry state files and the belief feedback already shipped in the calibration CLI.
**Merged out (2026-09-14):** the goalie-distribution sub-rule → became v6.9 item 21b
in the overview (same code site as the kick-aim quality work: `resolve_pass_target`).

**Living plans:** `PLANS_v6_v7_overview.md` (the index) · `post_field_test_plan.md`
(the execution plan) · this file (the backlog).
