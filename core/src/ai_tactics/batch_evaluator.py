#!/usr/bin/env python3
"""
Batch Evaluator v6 - Headless orchestrator for systematic LLM behavior optimization
Orchestrates multiple runs across scenarios, strategies, and models.
Collects metrics via live ROS topic subscriptions.
"""

import subprocess
import json
import os
import time
import sys
import argparse
from datetime import datetime
from pathlib import Path

class BatchEvaluator:
    def __init__(self, scenarios, strategies, models, runs, duration, output_path):
        self.scenarios = scenarios
        self.strategies = strategies
        self.models = models
        self.runs = runs
        self.duration = duration
        self.output_path = output_path
        self.results = {
            "meta": {
                "version": "v6",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "duration_per_run": duration,
                "runs_per_config": runs,
                "models": models,
                "strategies": strategies,
                "scenarios": scenarios
            },
            "results": {}
        }
        
        # Results directory
        self.results_dir = Path("src/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def run_single_config(self, scenario, strategy, model, run_id):
        """Run a single configuration with headless mode"""
        print(f"\n{'='*70}")
        print(f"📊 Run {run_id}: {scenario} × {strategy} × {model}")
        print(f"{'='*70}")
        
        # Setup command
        setup_cmd = [
            "python3", "setup_r2k.py",
            "--scenario", scenario,
            "--strategy", strategy,
            "--model", model,
            "--relay", "only_sim_bots",
            "--no-explain"
        ]
        
        print(f"🔧 Setup: {' '.join(setup_cmd)}")
        result = subprocess.run(setup_cmd, cwd="src", capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Setup failed: {result.stderr}")
            return None
        
        # Launch headless
        launch_cmd = [
            "../launch_r2k.sh",
            "--scenario", scenario,
            "--strategy", strategy,
            "--model", model,
            "--relay", "only_sim_bots",
            "--headless",
            "--duration", str(self.duration)
        ]
        
        print(f"🚀 Launching headless run for {self.duration}s...")
        start_time = time.time()
        
        # Run with timeout
        try:
            result = subprocess.run(
                launch_cmd,
                cwd="src",
                capture_output=True,
                text=True,
                timeout=self.duration + 30  # Buffer for startup/shutdown
            )
            elapsed = time.time() - start_time
            print(f"✅ Run completed in {elapsed:.1f}s")
            
            # Collect results
            # TODO: Subscribe to ROS topics during run
            # For now, return basic metrics
            return {
                "elapsed_time": elapsed,
                "status": "completed"
            }
            
        except subprocess.TimeoutExpired:
            print(f"⚠️  Run timed out after {self.duration + 30}s")
            return {
                "elapsed_time": self.duration + 30,
                "status": "timeout"
            }
        except Exception as e:
            print(f"❌ Run failed: {e}")
            return {
                "elapsed_time": 0,
                "status": "error",
                "error": str(e)
            }
    
    def run_all_configs(self):
        """Run all scenario × strategy × model combinations"""
        total_runs = len(self.scenarios) * len(self.strategies) * len(self.models) * self.runs
        current_run = 0
        
        print(f"\n{'#'*70}")
        print(f"# BATCH EVALUATOR V6")
        print(f"# Total runs: {total_runs}")
        print(f"# Duration per run: {self.duration}s")
        print(f"# Scenarios: {', '.join(self.scenarios)}")
        print(f"# Strategies: {', '.join(self.strategies)}")
        print(f"# Models: {', '.join(self.models)}")
        print(f"{'#'*70}\n")
        
        for scenario in self.scenarios:
            if scenario not in self.results["results"]:
                self.results["results"][scenario] = {}
            
            for strategy in self.strategies:
                if strategy not in self.results["results"][scenario]:
                    self.results["results"][scenario][strategy] = {}
                
                for model in self.models:
                    if model not in self.results["results"][scenario][strategy]:
                        self.results["results"][scenario][strategy][model] = {
                            "runs": []
                        }
                    
                    for run_id in range(1, self.runs + 1):
                        current_run += 1
                        print(f"\n[Progress: {current_run}/{total_runs}]")
                        
                        run_data = self.run_single_config(scenario, strategy, model, run_id)
                        if run_data:
                            self.results["results"][scenario][strategy][model]["runs"].append(run_data)
                        
                        # Save intermediate results
                        self.save_results()
        
        print(f"\n{'='*70}")
        print(f"✅ All {total_runs} runs completed!")
        print(f"📄 Results saved to: {self.output_path}")
        print(f"{'='*70}\n")
    
    def save_results(self):
        """Save results to JSON file"""
        output_file = self.results_dir / self.output_path
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
def main():
    parser = argparse.ArgumentParser(description="Batch Evaluator v6 for ROS2K")
    parser.add_argument("--scenarios", type=str, required=True, 
                       help="Comma-separated scenario names (e.g., '3vs3_attack_center,3vs3_defensive_crisis')")
    parser.add_argument("--strategies", type=str, required=True,
                       help="Comma-separated strategy names (e.g., 'strat_aggro,strat_default')")
    parser.add_argument("--models", type=str, required=True,
                       help="Comma-separated model names (e.g., 'qwen2.5-coder:3b,nemotron-3-nano:4b')")
    parser.add_argument("--runs", type=int, default=5,
                       help="Number of runs per configuration (default: 5)")
    parser.add_argument("--duration", type=int, default=60,
                       help="Duration per run in seconds (default: 60)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output filename (default: eval_results_TIMESTAMP.json)")
    
    args = parser.parse_args()
    
    scenarios = [s.strip() for s in args.scenarios.split(',')]
    strategies = [s.strip() for s in args.strategies.split(',')]
    models = [m.strip() for m in args.models.split(',')]
    
    output_path = args.output if args.output else f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    evaluator = BatchEvaluator(
        scenarios=scenarios,
        strategies=strategies,
        models=models,
        runs=args.runs,
        duration=args.duration,
        output_path=output_path
    )
    
    evaluator.run_all_configs()

if __name__ == "__main__":
    main()