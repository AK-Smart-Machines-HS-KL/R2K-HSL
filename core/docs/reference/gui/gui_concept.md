# ROS2K GUI Concept — Control Center for New Team Members

```mermaid
graph TB
    subgraph ROS2K["ROS2K Control Center"]
        subgraph NAV["Navigation Sidebar"]
            N1["Match"]
            N2["Probe"]
            N3["Scenarios"]
            N4["Tools"]
            N5["Knowledge Base"]
            N6["System Status"]
            N7["Regression Tests"]
            N8["Experiments"]
        end

        subgraph MAIN["Main Panel"]
            subgraph LIVE["Live Match View"]
                L1["Gazebo field render<br/>bots + ball + yellow arrows"]
                L2["Score: B 2 : 1 R<br/>Status: playing"]
            end

            subgraph LLM["LLM Decision Stream"]
                D1["blue_1 cover goal line<br/>blue_2 kick<br/>blue_3 move to -0.5,-0.5"]
                D2["Latency: 342ms<br/>Calls: 87<br/>Predict horizon: 0.38s"]
            end

            subgraph SCORE["Score and Momentum"]
                S1["Bar chart: t+0.7s t+1.4s t+2.1s"]
                S2["Current: +3.30<br/>Momentum: improving<br/>Trend: +0.08"]
            end

            subgraph SYS["System Status"]
                SS1["Ollama: online<br/>qwen2.5:3b<br/>GPU: 54C VRAM:2.4G"]
                SS2["Gazebo: running<br/>Container: core_gazebo"]
                SS3["Docker: up<br/>Bridge: active<br/>Referee: active"]
            end
        end
    end

    subgraph PANELS["Panel Details - click nav"]

        subgraph P_MATCH["Match Panel"]
            M1["Scenario dropdown<br/>Relay dropdown<br/>Model dropdown"]
            M2["no-explain / explain toggle<br/>Duration input<br/>Headless checkbox<br/>Analyze checkbox"]
            M3["LAUNCH / STOP / PAUSE<br/>REPLAY LAST / Speed / Start"]
        end

        subgraph P_PROBE["Probe Panel"]
            PR1["Scenario checkboxes<br/>17 hand-crafted + 33 empirical"]
            PR2["Repeats: 10<br/>Config: F0 baseline"]
            PR3["Results table<br/>Scenario / Hard% / Score / Cluster%"]
            PR4["Summary: 14/15 hard-pass 93%"]
        end

        subgraph P_SCEN["Scenario Browser"]
            SC1["Field diagram<br/>with yellow vectors"]
            SC2["Expert Analysis<br/>Oracle Strategy<br/>Output to bridge<br/>Score chart"]
            SC3["Prev / Next navigation<br/>Run 8s test / Probe"]
        end

        subgraph P_TOOLS["Tools Dashboard"]
            T1["analyze_trace.py<br/>KPI analysis"]
            T2["dump_prompt.py<br/>Prompt inspector"]
            T3["match_annotate.py<br/>Live annotation"]
            T4["replay_trace.py<br/>Post-match review"]
            T5["gen_diagrams.py<br/>Field diagrams"]
            T6["gen_score_chart.py<br/>Score bar charts"]
            T7["auto_loop.py<br/>Prompt optimization"]
            T8["cluster_experiment.py<br/>Cluster measurement"]
            T9["start_ollama.sh<br/>Manual Ollama start"]
            T10["reduce_empirical.py<br/>74 to 33 reduction"]
            T11["gen_all_analysis.py<br/>Generate analysis.md"]
            T12["regression_runner.py<br/>8s test runner"]
        end

        subgraph P_KB["Knowledge Base"]
            K1["10 Power Files<br/>1_CORE through 8_C3<br/>META_ROUTER<br/>FAQ"]
            K2["Docs<br/>optimization_spec_v6.4<br/>referee_rulebook<br/>c3_dictionary<br/>playbook<br/>scrum_tasks<br/>6 ADRs"]
            K3["Search bar"]
        end

        subgraph P_SYS["System Status"]
            SY1["Ollama card<br/>online / model / GPU temp / VRAM"]
            SY2["Gazebo card<br/>running / container / 10Hz physics"]
            SY3["Docker card<br/>up / container name / ROS Humble"]
            SY4["Bridge card<br/>active / 10Hz / 3 bots controlled"]
            SY5["Evaluator card<br/>polling / content-hash skip / 64%"]
            SY6["Trace logs card<br/>771 files / 122k calls"]
            SY7["Start Ollama / Restart Gazebo / Clear logs"]
        end

        subgraph P_REG["Regression Tests"]
            R1["Test suite checkboxes<br/>17 hand-crafted + 33 empirical"]
            R2["Duration: 8s per test<br/>Prediction: ON"]
            R3["Progress bar with ETA"]
            R4["Results table<br/>Test / Delta / Pass / Time"]
            R5["Pass rate: 46/50 92%"]
        end

        subgraph P_EXP["Experiments"]
            E1["Tabs: Auto-loop / Cluster / M-variants<br/>Baselines / C-series / K2-K3"]
            E2["Goals B:R line chart<br/>Best: iter 19 B:3 R:2<br/>Avg goal diff: -0.2"]
            E3["Cluster rate bar chart<br/>Batch 1: 47%<br/>Batch 4: 0%"]
        end
    end

    NAV --> PANELS
    LIVE --> LLM
    LLM --> SCORE
    SCORE --> SYS
```

## Implementation Notes

- **Technology:** Web-based (Python Flask + HTML/CSS/JS) — runs on localhost, no internet needed
- **Architecture:** Flask server reads trace files, runs tools, launches matches; browser frontend renders results
- **Scope:** Viewer + launcher + regression runner (not a replacement for the visualizer or annotator)
- **Priority:** Nice-to-have for onboarding, not blocking tournament preparation
- **Target audience:** New team members who need to understand the system without reading 4+ changelog entries or memorizing 15+ CLI flags