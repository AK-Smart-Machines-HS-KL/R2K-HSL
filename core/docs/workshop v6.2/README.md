# ROS2K v6.2 Workshop Material — Reviewer README

> **Purpose:** This package contains student-facing workshop material for the
> ROS2K v6.2 half-day team workshop (3.5 hours, 5 modules). It is submitted
> for review. Lecturer-internal material (timing, answers, fallback
> strategies) is excluded.

## What is ROS2K?

ROS2K is a hybrid robotics testbed where a local LLM (Qwen2.5-Coder:3b via
Ollama) drives Gazebo-simulated and physical robots (Yahboom, Booster K1)
via flat-JSON file polling on tmpfs. The workshop teaches team members the
v6.2 architecture — from the scoring ecosystem over the world model to
hardware integration and prompt engineering — through hands-on experiments
on their own GPU laptops.

## Package contents

| File | Type | Audience | Description |
|------|------|----------|-------------|
| `README.md` | This file | Reviewer | Orientation + review guide |
| `handout.md` | Handout | Student | 5-module workshop handout with experiments, fill-in KPI tables, key take-aways, glossary, opencode examples |
| `cheatpage.md` | Reference | Student | Launch flags, test commands, 14 KPI definitions, 10 test scenarios with oracle + KPI targets, quick-test recipes, file locations |
| `workshop_invitation.md` | Invitation | Team | 1-page team-facing overview: what you learn, 5 modules, prerequisites, what you take home |
| `part1_boot_ramp.pdf` | Diagram | Student | A4 portrait — Boot & Ramp Phase (CLI flags, setup_r2k.py, fragment assembly, Ollama warm-up, Gazebo launch, node ignition). Handoff marks ①-⑤ connect to Part 2. |
| `part2_running_system.pdf` | Diagram | Student | A4 portrait — Running System steady state (Gazebo → tracker → engine nodes → aggregator → evaluator ↔ Ollama → bridge → bots). All timings annotated. Handoff marks ①-⑤ connect from Part 1. |
| `rqt_graph_mockup.png` | Mockup | Student | rqt_graph-style ROS2 node graph: 7 nodes (ovals) + 9 topics (squares), blue = publish, green = subscribe, dark theme |

## What to review

- **Is the handout self-contained?** Can a student with GPU + Ollama + repo
  complete all 5 modules using only `handout.md` + `cheatpage.md` + the two
  PDF diagrams?
- **Are the diagrams readable on A4 printout?** Print `part1_boot_ramp.pdf`
  and `part2_running_system.pdf` — are node labels, edge annotations, and
  the ①-⑤ handoff marks legible at A4 size?
- **Are the opencode examples realistic?** Each module has 2-4 opencode
  prompts. Will they produce useful responses given the ROS2K knowledge base?
- **Does the cheat page cover all commands a student needs?** Launch flags,
  test commands, KPI analysis, experiment runner, quick recipes — anything
  missing?
- **Are the KPI targets reasonable?** Each of the 10 scenarios in
  `cheatpage.md` §4 has `kpi_targets.json` ranges. Do they match what a
  qwen2.5-coder:3b on GPU should produce?
- **Is the German/English mix consistent?** Per `git_rules.md`: code,
  comments, variables in English. Team-internal docs in German with English
  technical terms. AI prompts in code: English. Check all files follow this.
- **Are the key take-aways accurate?** Each module ends with 4-6 bullet
  points. Do they match the actual ROS2K v6.2 architecture and code?
- **Is the glossary complete?** 14 terms in `handout.md`. Are there terms
  used in the experiments that a student wouldn't know but aren't in the
  glossary?

## What is NOT in this package (intentionally excluded)

| Excluded file | Why |
|---------------|-----|
| `workshop_lecturer_guide.md` | Internal — contains answers, timing, fallback strategies, expected results |
| `workshop_memo.md` | Internal — planning memo for the opencode session producing deliverables |
| `runtime_architecture.*` | Superseded — the combined single diagram was split into `part1` + `part2` |
| `*.dot` source files | Build artifacts — only PDFs/PNGs are included for review |
| `rviz2_mockup.png` | Visual aid for lecturer demo, not referenced in handout or cheat page |

## File dependency map

```
handout.md
  ├─→ cheatpage.md (§1-§6 cross-referenced throughout)
  ├─→ part1_boot_ramp.pdf (diagram reading guide in front matter)
  ├─→ part2_running_system.pdf (diagram reading guide in front matter)
  ├─→ rqt_graph_mockup.png (referenced in Module 3)
  └─→ workshop_invitation.md (companion overview)

cheatpage.md
  ├─→ core/docs/referee_rulebook.md (referenced in §6 file locations)
  └─→ core/docs/optimization_spec_v6.2.md (referenced in §6 file locations)

workshop_invitation.md
  └─→ (standalone — no cross-references)
```

## Conventions

- **Language:** German with English technical terms (per `git_rules.md`).
  Code, comments, variables, commit messages: English. Team-internal docs:
  German. AI prompts in code: English.
- **Print target:** A4 portrait. Both diagrams fit A4 with margins for notes.
- **Handout design:** No answers (lecturer-only). Fill-in blanks (`_____`)
  for KPIs — the handout becomes each student's personal dataset.
- **Cross-references, not duplication:** Handout points to `cheatpage.md`
  sections instead of repeating content.
- **Shapes in diagrams:** Cylinder = Gazebo, rounded box = .py code,
  hexagon = .json data, note = .txt prompt, component = Ollama,
  box3d = sim bot, doubleoctagon = real bot.
- **Timing notation:** ⏱ symbol on every timing annotation in diagrams.
  ▶ = publisher (arrow source), ◀ = subscriber (arrow target).

## Version

All material is based on ROS2K v6.2 (2026-07-23). The architecture diagrams
reflect the codebase as of that date. The optimization spec
(`core/docs/optimization_spec_v6.2.md`) is the authoritative source for
phases, KPIs, and research directions.