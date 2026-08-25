#!/usr/bin/env python3
"""Tournament variant runner: applies a variant config, runs text-probe, restores.

Each variant is identified by a key. The runner:
1. Saves current fragment files
2. Applies the variant (modifies fragments or bridge)
3. Runs text-probe
4. Restores original files

Usage:
  python3 tools/tournament.py --gen 0 --corpus /tmp/corpus_easy_medium.jsonl --reps 3
  python3 tools/tournament.py --gen 0 --variant m1_kick_fallback --gazebo 5
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
FRAG_DIR = os.path.join(BASE_DIR, "strategy", "fragments")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
BACKUP_DIR = "/tmp/tournament_backup"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Variant definitions ---
# Each variant: list of (filename, content_or_None)
# content=None means "keep original", content=str means "replace with this"
# Bridge variants are handled separately (no fragment changes)

VARIANTS = {
    "m0_baseline": {
        "label": "M0: Baseline (C7, no change)",
        "fragments": {},
        "bridge_patch": None,
    },
    "m1_kick_fallback": {
        "label": "M1: Bridge kick fallback to Move when dist>1.5m",
        "fragments": {},
        "bridge_patch": "kick_fallback",
    },
    "m2_reposition": {
        "label": "M2: Bridge dynamic repositioning (nudge parked bots)",
        "fragments": {},
        "bridge_patch": "reposition",
    },
    "m3_ball_out_sample": {
        "label": "M3: Create samples_ball_out.txt (1 example)",
        "fragments": {
            "samples_ball_out.txt": """--- EXAMPLE 1: KICK-IN FROM SIDELINE ---
INPUT: {"soccer_ball": {"x": -2.0, "y": -2.9}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -2.5, "y": -2.5}, "blue_3": {"x": 1.0, "y": 0.0}, "red_1": {"x": 0.0, "y": -2.0}, "red_2": {"x": 2.0, "y": 0.0}, "red_3": {"x": 4.0, "y": 1.0}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.0, "y": -0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": 2.5, "y": -0.5}
  }
}
""",
        },
        "bridge_patch": None,
    },
    "m4_corner_sample": {
        "label": "M4: Create samples_corner_kick_in.txt (1 example)",
        "fragments": {
            "samples_corner_kick_in.txt": """--- EXAMPLE 1: CORNER KICK-IN ---
INPUT: {"soccer_ball": {"x": -4.3, "y": -2.8}, "blue_1": {"x": -4.0, "y": 0.0}, "blue_2": {"x": -4.0, "y": -2.5}, "blue_3": {"x": 0.0, "y": -1.0}, "red_1": {"x": -2.0, "y": -1.5}, "red_2": {"x": 1.0, "y": 0.0}, "red_3": {"x": 3.0, "y": 0.5}}
OUTPUT: {
  "assignments": {
    "blue_1": {"role": "goalie", "action": "Move", "x": -4.2, "y": 0.5},
    "blue_2": {"role": "attacker", "action": "Kick"},
    "blue_3": {"role": "attacker", "action": "Move", "x": -1.0, "y": -1.5}
  }
}
""",
        },
        "bridge_patch": None,
    },
    "m5_pass_gate": {
        "label": "M5: Pass rule gated to opponent half only",
        "fragments": {
            "rules_3vs3.txt": """3vs3 FULL SQUAD STRATEGY:
- You control THREE blue bots ("blue_1", "blue_2", "blue_3") against three opponents.
- The closest bot moves to the ball and kicks toward the opponent goal (X=4.5).
- One bot covers the goal line (X=-4.0) and follows the ball's Y position.
- One bot holds midfield (X=-2.0) to intercept passes and block passing lanes.
- Do not cluster your bots. Keep them spread out to cover more field.
- GOALIE CLEARANCE: If the goalie is the closest bot to the ball and the ball is in your own half (X < 0), the goalie kicks to clear the danger. Assign the goalie the Kick action with role "goalie". The bridge kicks upfield automatically.
- PASSING: If you have the ball in the opponent half (X > 0) AND a teammate is open in the opponent half (no red bot close to the teammate), pass to them. Use Kick with target_x and target_y set to the teammate's position. Do not pass from your own half — kick at the goal instead. Do not pass to a teammate who is marked by a red bot.
""",
        },
        "bridge_patch": None,
    },
    "m6_kick_dist": {
        "label": "M6: Bridge kick trigger 0.4m -> 0.3m",
        "fragments": {},
        "bridge_patch": "kick_dist_03",
    },
    "m7_no_closest_rule": {
        "label": "M7: Remove 'closest bot kicks' rule",
        "fragments": {
            "rules_3vs3.txt": """3vs3 FULL SQUAD STRATEGY:
- You control THREE blue bots ("blue_1", "blue_2", "blue_3") against three opponents.
- One bot covers the goal line (X=-4.0) and follows the ball's Y position.
- One bot holds midfield (X=-2.0) to intercept passes and block passing lanes.
- Do not cluster your bots. Keep them spread out to cover more field.
- GOALIE CLEARANCE: If the goalie is the closest bot to the ball and the ball is in your own half (X < 0), the goalie kicks to clear the danger. Assign the goalie the Kick action with role "goalie". The bridge kicks upfield automatically.
- PASSING: If a teammate is open in the opponent half (no red bot close to the teammate), pass to them. Use Kick with target_x and target_y set to the teammate's position. The bot kicking stays at its position; the receiving teammate moves to the target. Do not pass to a teammate who is marked by a red bot — kick at the goal instead.
""",
        },
        "bridge_patch": None,
    },
}


def backup_fragments():
    """Save current fragment files to backup dir."""
    if os.path.exists(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR)
    os.makedirs(BACKUP_DIR)
    for f in os.listdir(FRAG_DIR):
        if f.endswith(".txt"):
            shutil.copy2(os.path.join(FRAG_DIR, f), os.path.join(BACKUP_DIR, f))
    print(f"  Backed up fragments to {BACKUP_DIR}")


def restore_fragments():
    """Restore fragment files from backup."""
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".txt"):
            shutil.copy2(os.path.join(BACKUP_DIR, f), os.path.join(FRAG_DIR, f))
    # Remove any new files that weren't in backup
    for f in os.listdir(FRAG_DIR):
        if f.endswith(".txt") and not os.path.exists(os.path.join(BACKUP_DIR, f)):
            os.remove(os.path.join(FRAG_DIR, f))


def apply_fragments(variant_key):
    """Apply fragment changes for a variant."""
    v = VARIANTS[variant_key]
    for fname, content in v.get("fragments", {}).items():
        path = os.path.join(FRAG_DIR, fname)
        with open(path, "w") as f:
            f.write(content)
    # For removed files (content=None in fragments dict), we skip


def apply_bridge_patch(patch_key):
    """Apply a bridge patch. Returns the original bridge content for restoration."""
    bridge_path = os.path.join(BASE_DIR, "ai_tactics", "ollama_sandbox_bridge.py")
    with open(bridge_path) as f:
        original = f.read()

    if patch_key == "kick_fallback":
        # In the kick action branch, if dist_to_ball > 1.5, treat as Move toward ball
        old = "                if action == 'kick':"
        new = """                if action == 'kick' and dist_to_ball > 1.5:
                    # Too far to kick — treat as Move toward the ball
                    action = 'move'
                    target_x, target_y = self.ball_pos.x, self.ball_pos.y
                if action == 'kick':"""
        patched = original.replace(old, new, 1)
        if patched == original:
            print("  WARNING: kick_fallback patch failed (pattern not found)")
            return original
        with open(bridge_path, "w") as f:
            f.write(patched)

    elif patch_key == "reposition":
        # Add dynamic repositioning: if bot within 0.3m of target for >2s, nudge
        old = "                dx, dy = target_x - cx, target_y - cy"
        new = """                # Dynamic repositioning: nudge parked bots toward ball Y
                if action != 'kick' and action != 'hold':
                    park_dist = math.hypot(target_x - cx, target_y - cy)
                    if park_dist < 0.3 and self.ball_pos:
                        target_y = target_y * 0.7 + self.ball_pos.y * 0.3
                dx, dy = target_x - cx, target_y - cy"""
        patched = original.replace(old, new, 1)
        if patched == original:
            print("  WARNING: reposition patch failed (pattern not found)")
            return original
        with open(bridge_path, "w") as f:
            f.write(patched)

    elif patch_key == "kick_dist_03":
        patched = original.replace("dist_to_ball <= 0.4", "dist_to_ball <= 0.3")
        if patched == original:
            print("  WARNING: kick_dist patch failed")
            return original
        with open(bridge_path, "w") as f:
            f.write(patched)

    return original


def restore_bridge(original_content):
    """Restore bridge to original content."""
    bridge_path = os.path.join(BASE_DIR, "ai_tactics", "ollama_sandbox_bridge.py")
    with open(bridge_path, "w") as f:
        f.write(original_content)


def run_text_probe(variant_key, corpus_path, reps, tag):
    """Run text-probe for a variant."""
    # Use probe_overnight with C7 config (production) only
    env = os.environ.copy()
    env["R2K_OLLAMA_MODEL"] = "qwen2.5:3b"
    cmd = [
        sys.executable, os.path.join(BASE_DIR, "tools", "probe_overnight.py"),
        "--corpus", corpus_path,
        "--tag", tag,
        "--reps", str(reps),
        "--configs", "C7",
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=7200)
    return result.stdout, result.stderr, result.returncode


def run_mini_gazebo(variant_key, n_matches, scenario="3vs3_default"):
    """Run mini Gazebo matches for a variant."""
    results = []
    for i in range(n_matches):
        env = os.environ.copy()
        env["R2K_OLLAMA_MODEL"] = "qwen2.5:3b"
        cmd = [
            os.path.join(BASE_DIR, "..", "launch_r2k.sh"),
            "--headless", "--duration", "60",
            "--scenario", scenario, "--relay", "only_sim_bots",
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
        # Extract run ID
        run_id = None
        for line in result.stdout.split("\n"):
            if "Run ID:" in line:
                run_id = line.split("Run ID:")[1].strip().split()[0]
                break
        if run_id:
            # Extract KPIs
            kpi_cmd = [sys.executable, os.path.join(BASE_DIR, "tools", "analyze_trace.py"),
                       "--run-id", run_id]
            kpi_result = subprocess.run(kpi_cmd, capture_output=True, text=True, timeout=60)
            results.append({"run_id": run_id, "kpi_output": kpi_result.stdout[:500]})
        else:
            results.append({"run_id": None, "error": "no run ID"})
    return results


def extract_metrics(probe_output):
    """Extract key metrics from probe output."""
    metrics = {}
    for line in probe_output.split("\n"):
        if "Goalie Kick rate" in line or "Goalie Recall" in line:
            metrics["goalie_recall"] = line
        elif "Pass (Kick+tgt)" in line or "Pass Recall" in line:
            metrics["pass_recall"] = line
        elif "Parse OK" in line:
            metrics["parse"] = line
        elif "Latency p50" in line:
            metrics["latency"] = line
    return metrics


def main():
    ap = argparse.ArgumentParser(description="Tournament variant runner")
    ap.add_argument("--gen", type=int, default=0, help="Generation number")
    ap.add_argument("--corpus", default="/tmp/corpus_easy_medium.jsonl")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--variants", default="", help="comma-separated variant keys (default: all)")
    ap.add_argument("--gazebo", type=int, default=0, help="mini-Gazebo matches for top variants (0=skip)")
    args = ap.parse_args()

    # Determine variants to run
    if args.variants:
        variants_to_run = args.variants.split(",")
    else:
        variants_to_run = list(VARIANTS.keys())

    print(f"=== Tournament Generation {args.gen} ===")
    print(f"Variants: {len(variants_to_run)} ({', '.join(variants_to_run)})")
    print(f"Corpus: {args.corpus}")
    print(f"Reps: {args.reps}")
    print()

    # Backup fragments
    backup_fragments()

    all_results = {}

    for vkey in variants_to_run:
        v = VARIANTS[vkey]
        print(f"\n--- {v['label']} ---")

        # Apply fragments
        apply_fragments(vkey)

        # Apply bridge patch
        original_bridge = None
        if v.get("bridge_patch"):
            original_bridge = apply_bridge_patch(v["bridge_patch"])

        # Run text-probe
        tag = f"gen{args.gen}_{vkey}"
        print(f"  Running text-probe (tag={tag})...")
        stdout, stderr, rc = run_text_probe(vkey, args.corpus, args.reps, tag)
        metrics = extract_metrics(stdout)
        print(f"  Text-probe result:")
        for k, v_str in metrics.items():
            print(f"    {v_str}")

        all_results[vkey] = {
            "label": v["label"],
            "metrics": metrics,
            "stdout": stdout[-500:],
        }

        # Restore bridge
        if original_bridge is not None:
            restore_bridge(original_bridge)

        # Restore fragments
        restore_fragments()

    # Restore fragments (final cleanup)
    restore_fragments()

    # Summary
    print(f"\n{'='*60}")
    print(f"Generation {args.gen} Summary:")
    print(f"{'='*60}")
    for vkey, result in all_results.items():
        print(f"\n{result['label']}:")
        for k, v_str in result["metrics"].items():
            print(f"  {v_str}")

    # Save results
    results_path = os.path.join(RESULTS_DIR, f"tournament_gen{args.gen}_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved: {results_path}")

    # Mini-Gazebo for top 2 (if requested)
    if args.gazebo > 0:
        # Pick top 2 by goalie_recall (simple heuristic)
        def parse_pct(s):
            try:
                return float(s.split(":")[1].strip().split("%")[0].strip())
            except:
                return 0.0

        scored = []
        for vkey, result in all_results.items():
            gk = parse_pct(result["metrics"].get("goalie_recall", "0%"))
            ps = parse_pct(result["metrics"].get("pass_recall", "0%"))
            score = gk + ps
            scored.append((vkey, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top2 = [s[0] for s in scored[:2]]
        print(f"\nTop 2 for mini-Gazebo: {top2}")

        for vkey in top2:
            v = VARIANTS[vkey]
            print(f"\n--- Mini-Gazebo: {v['label']} ---")
            apply_fragments(vkey)
            if v.get("bridge_patch"):
                original_bridge = apply_bridge_patch(v["bridge_patch"])
            results = run_mini_gazebo(vkey, args.gazebo)
            for r in results:
                print(f"  {r}")
            if original_bridge is not None:
                restore_bridge(original_bridge)
            restore_fragments()

    restore_fragments()
    print("\nDone. All fragments restored.")


if __name__ == "__main__":
    main()
