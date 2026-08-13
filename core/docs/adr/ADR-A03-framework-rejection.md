# ADR-A03: Framework Rejection — W&B, DSPy, Optuna → pytest+git

**Date:** 2026-07-22
**Status:** Accepted

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into robot commands. Runs at 10Hz. |
| **Spike project** | A design and architecture exploration — not a production system. Accepts minor measurement errors. No claim of statistical 100% correctness. |

## Context

The ROS2K evaluation needed an experiment-tracking and prompt-optimization framework. Four options were evaluated during the 2026-07-21/22 planning sessions:

1. **W&B (Weights & Biases)** — generic ML experiment tracker with dashboard + sweeps
2. **DSPy + GEPA** — Stanford NLP prompt optimization framework with automated prompt mutation
3. **Optuna** — black-box optimization framework
4. **pytest + git** — use tools the team already knows

## Decision

Reject all external frameworks (W&B, DSPy, Optuna). Use **pytest + git + local trial-and-error**.

## Rationale

### W&B — rejected because:
- Can't mutate text files (fragments) — W&B Sweeps sweep numeric/discrete parameters, not prompt fragments. The core RF learning action requires custom code regardless.
- Abstraction mismatch — W&B is designed for ML training loops (epochs, loss curves). ROS2K runs are 120s matches with no intermediate checkpoints. Hyperband early termination doesn't apply.
- Data format lock-in — W&B writes to its own directory format, not plain JSON. Data is locked in W&B's format.
- External dependency — `wandb` package must be installed, pinned, kept compatible. ~50MB to venv.
- Student complexity — students must learn W&B's API in addition to ROS2K's architecture.

### DSPy + GEPA — rejected (deferred to Phase 5.9) because:
- Requires wrapping `r2k_evaluator.py` as a DSPy module (~300 lines)
- Synchronous assumption conflicts with ROS2K's async architecture (file-polling, 10Hz bridge)
- Only justified if manual iteration becomes a bottleneck — not the case yet
- Conditional: can be added later (Phase 5.9) if manual iteration stalls

### Optuna — rejected (deferred alongside DSPy) because:
- Better fit than W&B for non-ML workflows (can sweep discrete variant dirs)
- But still can't mutate text — the fundamental limitation is the same
- Deferred alongside DSPy

### pytest + git — chosen because:
- **Uses tools students already know** — no new API to learn
- **Regression protection built-in** — `test_non_functional.py` slow tests catch behavioral regressions
- **Git log = experiment history** — meaningful improvements only are committed; the diff IS the change record
- **Zero external dependencies** — no pip install, no service to run, no API to learn
- **Accepted limitation:** may end in local minima. Requires thoughtful engineering, not brute-force search. This is acceptable for a spike project.

## Alternatives Considered

A hybrid approach was also evaluated: W&B for Tier 1 (parameter sweeps) + custom for Tier 2 (prompt mutation). Rejected because the hybrid means students learn TWO systems, not one, and the prompt-mutation half (the actual novel work) is custom regardless.

## Consequences

- **No experiment dashboard.** Run comparison is via `analyze_trace.py --stats` (Mann-Whitney U, bootstrap CIs) + manual markdown tables. Acceptable for a spike project.
- **No automated sweep runner.** Sweeps are run via `run_baseline.sh` / `run_sweep.py` — custom scripts, not a framework. Acceptable.
- **No automated prompt mutation.** Fragments are hand-edited by the engineer, tested via probes, committed if they win. This is the intended workflow — the engineer learns what works, not the optimizer.
- **DSPy/Optuna can be added later** (Phase 5.9) if manual iteration becomes a bottleneck. The door is not closed — just deferred.
- **The two-tier test system** (fast `--skip-slow` ~2s, slow full suite ~21min) serves as the regression suite. Commit only winners.

## References

- `core/docs/optimization_spec_v6.2.md` (2026-07-22 session, framework evaluation)
- `core/docs/SESSION_CHANGELOG.md` 2026-07-21 (RF learning architecture planning)
- `core/src/tools/analyze_trace.py` (`--stats` flag for statistical comparison)
- `core/src/tools/run_baseline.sh` (baseline runner, no framework)