# ADR-A01: Model Switch — qwen2.5-coder:3b → qwen2.5:3b

**Date:** 2026-07-31
**Status:** Accepted
**Decider:** User (with AI assistant analysis)

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into `Twist` commands (sim) or `RpcReqMsg` payloads (K1 hardware). Runs at 10Hz. |
| **Inter-lingua** | The controlled-vocabulary intermediate language between the LLM and the bridge: verb+noun+coordinate sentences instead of JSON. |

## Context

The ROS2K C3 inter-lingua project uses a local 3B-parameter LLM (via Ollama) to drive robot behavior in a soccer simulation. The original model was `qwen2.5-coder:3b` — a code-specialized variant of Qwen2.5.

During Phase 0 literature research (2026-07-31), the team investigated the Qwen2.5-Coder training corpus via the technical report (arxiv 2409.12186). The corpus composition is:

- 70% source code
- 20% text-code grounding
- 10% math

Soccer vocabulary (formation, wing play, zone defense, marking, passing lane, etc.) is **not in-distribution** for a code-specific model. The model's general knowledge of natural-language soccer terminology was expected to be weaker than a general-purpose model of the same size.

## Decision

Switch the default model from `qwen2.5-coder:3b` to `qwen2.5:3b` (Qwen2.5-3B-Instruct, general-purpose).

## Rationale

1. **Training-data alignment:** qwen2.5:3b has broader web/book/multilingual text exposure. Soccer vocabulary is in-distribution for a general-purpose model, out-of-distribution for a code-specialized model.

2. **Empirical evidence:** A 27-run Gazebo baseline was run with qwen2.5:3b (2026-07-31). Results:
   - 11 goals scored, 21 conceded (0.41 scored / 0.78 conceded per match)
   - Composite 0.32, latency p50 744ms
   - vs old qwen2.5-coder:3b C1+C9 baseline: 55 scored / 142 conceded across 153 runs (0.36 / 0.93 per match), win rate 11.8%
   - Goal-scoring rate slightly improved (0.41 vs 0.36), concession rate improved (0.78 vs 0.93)

3. **Architecture continuity:** same Qwen2.5 architecture, same parameter count. Evaluator, bridge, trace/logging all work identically. No code changes needed beyond the default model name.

## Alternatives Considered

1. **Keep qwen2.5-coder:3b** — the code model was already integrated and working. But soccer vocabulary is out-of-distribution; the model's hedging on dynamic role definitions (C2_striker_rule, Phase 1) confirmed the mismatch.

2. **Switch to a larger model (7B+)** — better soccer knowledge, but:
   - Latency: 7B on the RTX 5090 Laptop would be ~1.5–2× slower (~1.1–1.5s vs ~750ms)
   - VRAM: 7B needs ~4.5GB vs 3B's ~2.4GB — leaves less headroom for Phase W's dual-model watchdog (Option B)
   - Edge deployment: K1 onboard (Jetson AGX/Orin) can only run ≤3B comfortably
   - Rejected — 3B is the size class that fits the deployment target

3. **Switch to Llama-3.2-3B** — tested as Phase 4b (cross-model regression). Different architecture (Llama vs Qwen), validates inter-lingua generalizability. Not chosen as the primary model because the C3 dictionary was probed against qwen2.5:3b specifically.

## Consequences

- **All prior C-series baselines (qwen2.5-coder:3b) are invalidated.** The 11.8% win rate baseline no longer applies.
- **New baseline required:** the 27-run qwen2.5:3b baseline (2026-07-31) is the new reference.
- **C3 findings (interwoven loses, 1 sample sufficient) need cross-model validation** — Phase 4b tests this on Llama-3.2-3B.
- **Edge deployment path:** qwen2.5:3b fits Jetson AGX/Orin for K1 onboard processing.

## References

- `core/docs/c3_phase0_literature_and_plan.md` §1.1 (model switch analysis)
- `core/docs/SESSION_CHANGELOG.md` 2026-07-31 (baseline results)
- Qwen2.5 technical report: arxiv 2409.12186
- `core/launch_r2k.sh:12` (default model changed)