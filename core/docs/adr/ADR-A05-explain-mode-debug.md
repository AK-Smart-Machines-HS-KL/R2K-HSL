# ADR-A05: Explain Mode — Production → Debug-Only (User Inspection)

**Date:** 2026-08-03
**Status:** Accepted

## Context

The `--explain` flag in `launch_r2k.sh` activates an extended LLM output format: the model produces `ANALYSIS:` and `ORACLE:` prose sections in addition to the per-bot command lines. This was originally intended as a production feature (the visualizer would display the analysis/oracle for the user).

During Phase F (F4 content sweep, 2026-08-02), the `F4_explain` config was tested:
- **56% hard-pass** (vs 94% for F0 non-explain) — catastrophic
- **691ms latency** (vs 216ms for F0) — 3.2× slower
- **Coverage 0.79** (vs 1.02 for F0) — explain prose crowds out bot command lines, reducing coverage

The mechanism: explain mode uses `TEXT_EXPLAIN_INSTRUCTION` which contains no K3 rules (KICK/SPLIT/PASS live only in `TEXT_OUTPUT_HEADER`). The kick-sensitive `free_man_pass` situation collapsed (code=2 failures). Even with the `explain_k3h` fix (K3 rules appended to explain header), the extra prose still crowds out commands at the 3B model's token budget.

## Decision

`--explain` stays in `--help` and remains a supported flag, but is reclassified as a **debug-only tool for user inspection.** Performance is not a concern in this mode — the user accepts the latency and reduced hard-pass because the purpose is to read the model's reasoning, not to drive the bot.

## Rationale

1. **User decision (2026-08-03):** "explain mode is for user inspection. Performance is not an issue there." The user explicitly rejected rolling back the flag.

2. **The F4_explain finding is informational, not actionable.** "Explain crowds out commands" is a property of the 3B model's token budget, not a bug. It's expected that asking the model to produce 600 tokens of analysis will reduce the quality/coverage of the 30-45 tokens of commands.

3. **Debug value is real.** When the user wants to understand why the model made a particular decision, `--explain` is the tool. The visualizer displays STRATEGY/ORACLE text (fixed 2026-08-02, `r2k_visualizer.py` text fallback). The annotator captures it (`match_annotate.py` text fallback). The trace logger records it (`llm_trace` analysis/oracle fields).

4. **Not a production path.** Live matches and the Phase M sweeps run in non-explain mode (`TEXT_OUTPUT_HEADER`, 200 token cap). Explain mode is never used for evaluation — only for human inspection.

## Alternatives Considered

1. **Roll back `--explain` entirely** (remove from `--help`, hide as `R2K_EXPLAIN=1` env var) — rejected by user (2026-08-03: "no"). The flag is useful for debugging.

2. **Fix explain mode to not crowd out commands** — would require a 2-call architecture (call 1: analysis/oracle only, call 2: commands only). Doubles latency (~1.4s). Not worth it for a debug tool.

3. **Make explain mode use a larger model** (7B, more token budget) — breaks the 3B constraint and the edge-deployment path. Not worth it for a debug tool.

## Consequences

- **`--explain` stays in `launch_r2k.sh --help`** and in the flag list.
- **`R2K_EXPLAIN` env var** (set by `launch_r2k.sh:60`) continues to control `{{EXPLAIN_INSTRUCTION}}` replacement in `header.txt`.
- **Explain mode is never used for evaluation.** Phase M sweeps, Phase 4 validation, Phase 5 evaluation all run in non-explain mode.
- **The F4_explain 56% hard-pass finding is documented** as a known limitation ("explain crowds out commands at the 3B token budget") — not a regression to fix.
- **`TEXT_EXPLAIN_INSTRUCTION`** (in `r2k_evaluator.py`) includes K3 rules via `_k3_rules_section()` (the `explain_k3h` fix from Phase F) so explain mode at least has the rules available, even if the prose crowds them out.

## References

- `core/launch_r2k.sh:60` (`R2K_EXPLAIN` export), `:402` (Docker passthrough)
- `core/src/ai_tactics/r2k_evaluator.py:86` (`TEXT_EXPLAIN_INSTRUCTION`), `:586` (`is_explain` detection)
- `core/docs/SESSION_CHANGELOG.md` 2026-08-02 (F4_explain finding, explain pipeline fix)
- `core/src/r2k_visualizer.py` (STRATEGY/ORACLE text fallback, label rename)
- `core/src/tools/match_annotate.py` (text fallback for annotation)