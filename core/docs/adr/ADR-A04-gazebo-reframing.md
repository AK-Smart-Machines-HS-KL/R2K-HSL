# ADR-A04: Gazebo Reframing — Measurement → More Demo Than Measurement

**Date:** 2026-08-03
**Status:** Accepted

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into robot commands. Runs at 10Hz. |
| **Inter-lingua** | The controlled-vocabulary intermediate language between the LLM and the bridge: verb+noun+coordinate sentences instead of JSON. |
| **KV-cache non-determinism** | At temperature 0.0, the LLM is not bit-exact across calls — identical prompts can produce different token streams depending on KV-cache state. Semantics stay stable, but raw-output comparisons are unreliable. |
| **Spike project** | A design and architecture exploration — not a production system. Accepts minor measurement errors. No claim of statistical 100% correctness. |
| **Text-probe** | A synthetic world-state sent to the LLM, with the output parsed and scored (hard pass, soft score, gap diagnostics). No Gazebo needed — pure LLM text-output analysis. ~80× faster than Gazebo. The primary evaluation instrument. |
| **K2 sweep** | Phase K experiment: 10 cumulative prompt-content variants (v0–v9). Result: v0 (current fragments, no additions) wins at 100% hard-pass; all additions regressed. Static-context lengthening rejected. |
| **F3 sweep** | Phase F experiment: 4 prompt architectures. Result: F0 (global rules + separate samples) wins at 93% hard-pass / 217ms; interwoven variants scored 56–62% at ~940ms. |
| **F0** | The winning prompt config: global rules + 1 separate sample + K3 header, non-explain. The current production prompt. |
| **Gap diagnostic** | Soccer-semantic check in `i3_battery.py` that the soft score misses: `gapC` (competition — exactly ONE bot targets the ball) and `gapP` (pass — kick present AND ≥1 non-kicker moves forward of the ball). |

## Context

ROS2K has used Gazebo as its primary evaluation instrument since v5. The 27-run baseline (2026-07-27, 2026-07-31), `test_non_functional.py` slow tests, `kpi_targets.json` thresholds, `run_baseline.sh`, and `analyze_trace.py` (18 KPIs) were all built as Gazebo-based measurement infrastructure.

During the 2026-08-03 QA review, three problems were identified:

1. **Gazebo physics is not deterministic.** Standard Gazebo (ODE solver) has non-deterministic contact-resolution ordering and floating-point accumulation. Seeding the world file does not freeze this. The ball (restitution=1.0, friction=0.01) is a chaotic system — microscopic perturbations compound into different trajectories within seconds.

2. **Variance is extreme.** Measured CV (coefficient of variation) on the 27-run qwen2.5:3b baseline:
   - latency p50: 0.7% (rock-solid, infrastructure deterministic)
   - goalie_tactical_pct: 12.1% (moderate)
   - cluster_pct: 91.2% (terrible — 1.7% to 73.2% across 3 runs of the same scenario)
   - oob_pct: 90.1% (terrible)
   - shots_on_goal: 83.9% (terrible)
   - goals_blue: 129.1% (terrible — 0 or 1, basically random)

3. **Statistical power is low.** At CV=90–129%, n=17 can only detect effects ≥3× on goals/shots/OOB. Below that, differences are within noise. n=30 would still only detect ~2× effects. Affordable n cannot make Gazebo a precision instrument.

## Decision

Reframe Gazebo from "measurement instrument" to **"more demo than measurement."** This is a design and architecture spike project — no claim of statistical 100% correctness. We accept the risk of minor measurement errors.

The **text-probe suite** (`i3_battery.py`, `llm_probe.py`, 81–150 state corpus, hard-pass/soft-score/gap diagnostics) is the **primary evaluation instrument.** Gazebo provides **supplementary quantitative data with caveats** (directional, not statistical).

## Rationale

1. **The text-probe suite already works.** 100% hard-pass on v0 TEXT (K2 sweep), 93% on F0 (F3 sweep), gap diagnostics (gapC/gapP) catch soccer-semantic failures that soft scores miss. Text probes are deterministic (temp 0.0, KV-cache caveats aside), reproducible, and ~80× faster than Gazebo.

2. **Gazebo still has value.** It validates end-to-end integration (does the bridge execute commands? does the referee work? does the ball physics produce realistic trajectories?). It catches emergent tactical failures (shape, timing, transition) that text probes structurally cannot. It's needed for sim-to-real sanity and workshop demos.

3. **Spike project framing.** The project is a design and architecture spike — exploring whether a 3B LLM can drive robots via a controlled-vocabulary inter-lingua. It is not a production system claiming statistical rigor. Minor measurement errors in Gazebo are acceptable; the text-probe results are the evidence, Gazebo is the demo.

4. **The user explicitly chose this framing:** "more demo than measurement" (2026-08-03), accepting minor measurement-error risk. Not "demo, not measurement" (too harsh) — Gazebo data is still reported, just with caveats.

## Alternatives Considered

1. **Gazebo as measurement (status quo)** — but CV=90–129% makes statistical claims unreliable at affordable n. Would need n=100+ per scenario per config — infeasible (~8h per scenario).

2. **Gazebo as pure demo (no quantitative reporting)** — too harsh. The 27-run baseline, KPI tables, and slow tests have value as directional indicators even without statistical claims. Throwing away the infrastructure wastes prior investment.

3. **Drop Gazebo entirely** — all evaluation is text-only. But then sim-to-real validation is lost. The bot might drive into a wall in Gazebo and we'd never know. Phase 4 is the critical gate.

4. **Fix Gazebo determinism first** (Phase G) — but standard Gazebo doesn't provide deterministic physics. The user investigated seeding (preset initial conditions, fixed LLM seed, headless) and confirmed: "No, standard Gazebo does not provide fully deterministic physics out of the box." Seeding the world file doesn't freeze ODE contact-resolution ordering.

## Consequences

- **Composite score** (`test_non_functional.py`) — softened from hard gate to **soft gate with widened tolerances (±50%)**. Smoke-test assertions (scored ≥1? no crash? no OOB > 50%?) remain the hard gate. Spike-project caveat added in code comment.
- **`kpi_targets.json`** (11 files) — re-calibrated from 3-run baseline; labeled "directional, not statistical" in file header. Used as demo quality bars, not hard thresholds.
- **`run_baseline.sh`** — documented as "3–5 runs for demo regression," not "27 runs for statistical baseline." The 27-run baseline (2026-07-31) remains as a one-time reference, not a repeatable standard.
- **`analyze_trace.py`** (18 KPIs) — kept as demo diagnostics. Useful for eyeballing, not for statistical claims.
- **Phase 4** (Gazebo validation) — 3–10 runs per config, eyeball + H2 coach comments + supplementary quantitative data with caveats (means ± ranges, no significance tests). 3× effects noted as "likely real"; <1.5× as "within noise."
- **Phase 5** (full evaluation) — final KPI table includes text-probe results (primary, n=30) + Gazebo results (supplementary, n=3–5, labeled "directional, not statistical").
- **Text-probe suite is the primary instrument.** The 210,000-probe Phase M sweep (n=30, 150 states, full factorial) is where statistical rigor lives.

## References

- `core/docs/optimization_spec_v6.4.md` §0 (Gazebo framing), §1 RB-1 (composite softening)
- `core/docs/SESSION_CHANGELOG.md` 2026-08-03 (QA review, Gazebo reframing decision)
- `core/src/tools/analyze_trace.py` (18 KPIs — now demo diagnostics)
- `core/src/tools/i3_battery.py` (text-probe — now primary instrument)
- Baseline CV data: `results/baseline_qwen25_3b_summary.md`