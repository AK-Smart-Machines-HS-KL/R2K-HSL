# KPI Regression Analysis (2026-07-27, v6.3 baseline)

> Data source: 27 v6.3 baseline runs (9 scenarios × 3 runs × 120s).
> Method: variance analysis (coefficient of variation) + Pearson correlation matrix.

## 1. KPIs to give up (uninformative or redundant)

### Tier 1 — Give up (zero variance, no information)

| KPI | Mean | CV% | Why give up |
|-----|------|-----|-------------|
| `parse_error_rate` | 0.0% | **0.0%** | `qwen2.5-coder:3b` produces valid JSON 100% of the time. The fast_parse fallback never triggers. This KPI was useful when we tested different models/formats, but with a single stable model it's a dead metric. |
| `role_diversity` | 5.0 | **0.0%** | Always 5 (goalie, midfielder, striker, passer, receiver). The LLM always assigns all 5 roles. No discriminating power. |
| `avg_response_tokens` | 56.96 | **0.3%** | Stable at ~57 tokens (well under the 150 `num_predict` cap). No truncation, no verbosity variation. Uninformative. |

**Action:** Remove from `analyze_trace.py` summary output and `kpi_targets.json`. Keep the computation (trivial cost) for historical comparison, but stop asserting them in the regression suite.

### Tier 2 — Give up one (redundant pair)

| KPI pair | Correlation | Why give up one |
|----------|-------------|-----------------|
| `latency_p50` ↔ `latency_mean` | **r = 0.943** | Near-identical. `lat_p50` is the standard reporting metric. `lat_mean` adds nothing. |

**Action:** Drop `lat_mean` from summary output. Keep `lat_p50` (standard) + `lat_p95` (tail behavior) + `lat_max` (worst case).

### Tier 3 — Consider giving up (low variance after warm-up curl)

| KPI | Mean | CV% | Why |
|-----|------|-----|-----|
| `latency_p50` | 662ms | **0.8%** | Extremely stable after warm-up curl (was 7.8% in v6.2). Still useful for model comparison (Phase 3), but within a single model it's nearly constant. **Keep for Phase 3, consider dropping after.** |
| `latency_p95` | 710ms | **1.4%** | Same — stable. Keep for tail behavior monitoring. |
| `latency_max` | 2622ms | **3.9%** | Slightly more variance (cold-load tail). Keep as a watchdog signal. |

### Tier 4 — Keep but acknowledge redundancy

| KPI pair | Correlation | Note |
|----------|-------------|------|
| `goalie_tactical_pct` ↔ `oob_pct` | **r = -0.714** | Inverse correlation: when goalie is tactically positioned, OOB is lower. Not redundant enough to drop either (different failure modes). |
| `goalie_idle_pct` ↔ `goalie_tactical_pct` | not >0.7 | Both measure goalie behavior from different angles. `goalie_tactical_pct` is the primary (Phase 2a); `goalie_idle_pct` is kept for backward comparison. **Could drop `goalie_idle_pct` after Phase 3.** |

## 2. Phase 2.5 KPIs — all worth keeping

| KPI | CV% | Verdict |
|-----|-----|---------|
| `shots_on_goal` | 76.1% | ✅ High variance, captures attack intent. Core metric. |
| `shots_on_target` | 104.2% | ✅ High variance, captures shot quality. Core metric. |
| `pass_completion_pct` | 29.4% | ✅ Moderate variance, captures passing behavior. Keep. |
| `restart_recovery_time_s` | 69.7% | ✅ High variance, captures restart execution. Keep. |

All 4 new KPIs have sufficient variance and capture behavior the old KPIs couldn't see.

## 3. Candidate new KPIs — novelty check

Computed 6 candidates from existing trace data (no runtime changes). Checked correlation with all existing KPIs:

| Candidate | What it measures | Most correlated existing KPI | r | Novel? |
|-----------|-----------------|----------------------------|---|--------|
| `mean_ball_x` | Mean ball X position (field dominance) | `shots_on_goal` | 0.842 | ❌ NO |
| `opp_half_pct` | % time ball in opponent half | `shots_on_goal` | 0.868 | ❌ NO |
| `opp_third_pct` | % time ball in opponent third | `shots_on_goal` | 0.859 | ❌ NO |
| `own_third_pct` | % time ball in own third | `shots_on_goal` | -0.709 | ❌ NO |
| `shot_acc` | `shots_on_target / shots_on_goal` ratio | `shots_on_target` | 0.684 | **~ MAYBE** |
| `conv_rate` | `goals_blue / shots_on_goal` ratio | `goals_blue` | 0.729 | ❌ NO |

**Verdict:** The 4 Phase 2.5 KPIs already capture most of the available information in the trace data. The field-position candidates (`mean_ball_x`, `opp_half_pct`, etc.) are all highly correlated with `shots_on_goal` — they measure the same underlying dimension ("does blue push forward?"). Adding them would be KPI bloat.

**Only `shot_acc` (on_target/shots ratio) is borderline novel** (r=0.684 with `shots_on_target`). It captures shot *quality* independent of shot *volume*. A team could have many shots but low accuracy (spray-and-pray) vs. few shots but high accuracy (precision). However, it's a derived ratio of two existing KPIs — easy to compute post-hoc without adding it to `analyze_trace.py`.

## 4. Low-hanging fruit — what to actually change

### 4a. KPI cleanup (no re-run needed)
- **Remove from regression suite assertions:** `parse_error_rate`, `role_diversity`, `avg_response_tokens` (zero variance, can't fail)
- **Remove from summary output:** `lat_mean` (redundant with `lat_p50`)
- **Net KPI count:** 19 → 16 (drop 3 uninformative, drop 1 redundant)

### 4b. Add `shot_acc` as derived KPI (no re-run needed)
- Add to `analyze_trace.py`: `"shot_acc": round(shots_on_target / max(shots_on_goal, 1) * 100, 1)`
- One line, computed from existing KPIs, no trace re-processing.
- Useful for Phase 3: "does model X shoot more accurately, or just more?"

### 4c. What NOT to add
- Field position KPIs (`mean_ball_x`, `opp_half_pct`) — redundant with `shots_on_goal`
- `conv_rate` (goals/shots) — redundant with `goals_blue`, and noisy (0-2 goals per match makes the ratio unstable)

### 4d. The real gap (not low-hanging)
The trace data can't measure **defensive behavior** — we have no KPI for:
- Interceptions (blue steals ball from red)
- Shot blocks (blue prevents red shot)
- Goal-saving saves (goalie stops a shot)

These would require tracking red→blue possession transitions and ball trajectory analysis near the goal. Not low-hanging — deferred to Phase 5 (Kalman + predictive model enables this).

## 5. Recommendation: do we re-run the baseline?

**No.** The v6.3 baseline is valid and complete. The KPI cleanup (4a) and `shot_acc` addition (4b) can be computed post-hoc from the existing 27 trace files — no need for a re-run. The cleanup is purely cosmetic (stop asserting dead metrics, stop printing redundant latency).

**Re-run would only be needed if:**
- We add a new KPI that requires trace data we don't currently log (e.g., per-bot velocity for defensive KPIs)
- We change the dynamic injection logic (2.5b) or game-phase fragments (2.5c)
- We swap the model (Phase 3)

**Next action:** Apply 4a + 4b to `analyze_trace.py`, re-compute KPIs from existing traces (offline, ~30s), update `kpi_targets.json` thresholds for the cleaned-up KPI set, then proceed to Phase 3.