# ADR-A02: Role Condensation — 5 → 3 (goalie/attacker/defender)

**Date:** 2026-07-28
**Status:** Accepted (no A/B test — Phase M sub-exp 2 tests this)

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into `Twist` commands (sim) or `RpcReqMsg` payloads (K1 hardware). Runs at 10Hz. |
| **Goalie blending** | The bridge overrides the LLM's target position for the goalie bot, blending 70% tactical positioning with 30% LLM influence. Only triggered when `role == 'goalie'`. |
| **Inter-lingua** | The controlled-vocabulary intermediate language between the LLM and the bridge: verb+noun+coordinate sentences instead of JSON. |
| **Hedging** | The LLM produces a non-committal, qualifying answer instead of a crisp instruction ("could be considered... however... not necessarily"). Discovered in the C2_striker_rule probe — the model rejects dynamic role definitions and falls back to static semantics with hedging. |
| **Hard pass** | Binary gate from `i3_battery.py`: a probe output passes if all blue bots are assigned exactly once (coverage), all targets are in-field, and roles are in the whitelist. |

## Context

The original ROS2K prompt used 5 roles: `striker`, `midfielder`, `passer`, `receiver`, `supporter`. The bridge (`ollama_sandbox_bridge.py`) only checks `role == 'goalie'` for special behavior (goalie blending). All other roles were cosmetic labels with no consumer — the bridge treats every non-goalie role identically.

During Phase 1 vocabulary probing (2026-08-01), the C2_striker_rule probe revealed that the model rejects dynamic role definitions ("the striker is the bot closest to the ball") and falls back to static human-soccer semantics with hedging. This is the exact "contradictive argumentation" the inter-lingua must remove.

## Decision

Reduce roles from 5 to 3: `goalie`, `attacker`, `defender`.

## Rationale

1. **Bridge only reads `goalie`:** all non-goalie roles had identical bridge behavior. The 5-role system was generating tokens the consumer ignored — pure overhead.

2. **C2_striker_rule:** the model hedges on dynamic role definitions. Reducing to 3 static roles (which the model understands cleanly per A3_roles probe) eliminates the hedging source.

3. **Simplicity:** 3 roles map cleanly to the 3 tactical responsibilities (protect goal, attack opponent goal, defend). 5 roles created artificial distinctions (striker vs midfielder vs passer) that the 3B model couldn't usefully distinguish in a 3-bot team.

4. **KISS:** fewer roles = shorter prompt = fewer tokens = lower latency. The 3-role system is at the minimum needed for goalie blending to work.

## Alternatives Considered

1. **Keep 5 roles** — but the bridge ignores 4 of them, the model hedges on dynamic definitions, and the extra tokens cost latency. No benefit.

2. **Drop roles entirely** — the C3 inter-lingua prefers situation-triggered position verbs ("blue_2 move to the ball") over role labels. But the bridge still needs `role == 'goalie'` for blending. Phase M sub-exp 2 tests the zero-role variant.

3. **Use only `goalie` + `field`** — simpler, but `attacker`/`defender` are natively understood by the model (A3_roles probe) and cost only 2 tokens per bot.

## Consequences

- **No A/B test was run.** The condensation was applied based on architectural reasoning (bridge only reads goalie) + the C2_striker_rule finding. Phase M sub-exp 2 (role labels 0 vs 3) retroactively tests whether roles help at all in TEXT mode.
- **`role_diversity` KPI dropped** — the metric had CV=0% across all 27 v6.3 baseline runs (always 5.0 → always 3.0). It was a dead metric.
- **Pass detection changed** — `analyze_trace.py` now uses position-based pass detection (kicker NOT in opponent half = pass), not role-based (`role in ('passer','receiver','midfielder')`).
- **All fragments updated:** `rules_3vs3.txt`, `rules_3vs1.txt`, `rules_2vs2.txt`, `rules_2vs1.txt`, `rules_1vs1.txt`, and all `samples_*.txt` files.
- **If Phase M sub-exp 2 shows roles don't help (0 roles ≥ 3 roles in hard-pass),** roles should be dropped entirely — the C3 inter-lingua already prefers position verbs.

## References

- `core/src/ai_tactics/ollama_sandbox_bridge.py` (only checks `role == 'goalie'`)
- `core/docs/c3_vocabulary_dictionary.md` §3 (C2_striker_rule critical finding)
- `core/docs/SESSION_CHANGELOG.md` 2026-07-28 (role condensation)
- `core/src/tools/analyze_trace.py` (position-based pass detection, role_diversity dropped)