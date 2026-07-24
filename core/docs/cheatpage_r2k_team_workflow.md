**Cheat Page — R2K Team Workflow mit opencode, Continue & Copilot**

> **Zweck:** Kompakte Übersicht für Teammitglieder: welche Files, Pfade und
> Configs wo liegen, wie Sessions und Knowledge-Base funktionieren, und welche
> Best Practices projektübergreifend gelten. Deutsch mit englischen
> IT-Begriffen. Jeder Abschnitt zwischen `***` Trennern ist self-contained
> und kann in eine eigene Trello-Karte kopiert werden.

***

**1 — Setup: Configs, Prompts und Provider**

**Motivation**

ROS2K nutzt drei LLM-gestützte Development-Tools parallel: **opencode**
(standalone TUI), **Continue** (VSCode-Plugin) und **GitHub Copilot**.
Alle drei sollen dieselben Architektur-Axiome und dieselbe Knowledge Base
konsultieren, bevor sie Code generieren oder analysieren. Um Drift zwischen
den Tools zu vermeiden, gibt es eine kanonische Prompt-Quelle
(`agent_prompt_de.txt`) und eine kanonische Knowledge-Base
(`ros2k_knowledge/`). Jedes Tool referenziert diese Quellen über seinen
eigenen Mechanismus. Die Tool-Configs sind voneinander isoliert — Änderungen
an einem Tool haben keinen Einfluss auf die anderen.

**Shared Prompt Source**

- **`agent_prompt_de.txt`** (`core/src/ros2k_knowledge/agent_prompt_de.txt`):
  Kanonische Quelle: 68 Zeilen ROS2K-Agent-Instructions (Rolle, 10 Axiome,
  RAG-Routing, Formatierung). Alle Tools referenzieren dieses File.

**Startup-Chain: Wie jedes Tool `agent_prompt_de.txt` lädt**

- **opencode**: (a) `AGENTS.md` auto-load (Build-Commands, File-Layout,
  Conventions, Gotchas + Cross-Reference auf `agent_prompt_de.txt`) +
  (b) `.opencode/opencode.json → instructions` lädt `agent_prompt_de.txt` +
  `SESSION_CHANGELOG.md` + `META_KNOWLEDGE_ROUTER.md`. Liest
  `.opencode/opencode.json`: **Ja**. Liest `core/AGENTS.md`: **Ja**
  (auto-discovery via Verzeichnis-Traversierung).
- **Continue**: `continue.json.current → systemMessage:
  "@file ~/R2K-HSL/core/src/ros2k_knowledge/agent_prompt_de.txt"`.
  Liest `.opencode/opencode.json`: **Nein**. Liest `core/AGENTS.md`: **Nein**.
- **Copilot**: Auto-read `core/.github/copilot-instructions.md` →
  **Symlink** → `agent_prompt_de.txt`. Liest `.opencode/opencode.json`:
  **Nein**. Liest `core/AGENTS.md`: **Nein**.

> **Impact-Isolation:** Änderungen an `.opencode/opencode.json` haben
> **zero impact** auf Continue und Copilot. Beide Tools lesen die Datei
> nicht — sie haben ihre eigenen Mechanismen, um `agent_prompt_de.txt` zu
> laden (`@file` bzw. Symlink). Umgekehrt liest opencode weder
> `continue.json.current` noch `.github/copilot-instructions.md`. Die drei
> Tools sind **isoliert** — Änderungen an einem Tool-Config haben keinen
> Einfluss auf die anderen.

**opencode (standalone TUI)**

- **Project config** (`.opencode/opencode.json`): `instructions` Array:
  lädt `SESSION_CHANGELOG.md` + `META_KNOWLEDGE_ROUTER.md` +
  `agent_prompt_de.txt` eager bei jedem Session-Start.
- **Global config** (`~/.config/opencode/opencode.json`): **Provider +
  API-Keys**: Ollama local, Uni Mainz, Gemini.
- **Auth tokens** (`~/.local/share/opencode/auth.json`): Ollama Cloud API-Key.
- **AGENTS.md** (`core/AGENTS.md`): opencode's native project-rules file:
  Build/Test-Commands, File-Layout, Conventions, Gotchas, Session-Protokoll.
  Cross-Reference auf `agent_prompt_de.txt` für die 10 Axiome. Wird von
  opencode **automatisch** geladen.

**VSCode + Continue**

- **Continue config** (`core/.vscode/continue.json.current`):
  `systemMessage` referenziert `agent_prompt_de.txt` via `@file`.
  `/check_ros2k` Custom Command. `tabAutocompleteModel`.
- **VSCode agents** (`core/.vscode/agents.md`): 11-Zeilen-Stub:
  `@file agent_prompt_de.txt` + `@file META_KNOWLEDGE_ROUTER.md` +
  4 Axiom-Bullets.

**GitHub Copilot**

- **Copilot instructions** (`core/.github/copilot-instructions.md`):
  **Symlink** → `../src/ros2k_knowledge/agent_prompt_de.txt`. Copilot liest
  das File automatisch; durch den Symlink immer synchron mit der kanonischen
  Quelle.

**Provider-Übersicht (Default-Launch-relevant)**

Default-Launch: `./launch_r2k.sh --scenario 2vs2_default --relay only_sim_bots`
verwendet `qwen2.5-coder:3b` lokal via Ollama.

- **Ollama local** (`http://127.0.0.1:11434/v1`): kein Key nötig. Model:
  `qwen2.5-coder:3b`.
- **Ollama Cloud** (`https://ollama.com/v1`): API-Key in
  `~/.local/share/opencode/auth.json` + `continue.json.current`. Model:
  `qwen3-coder-next`.
- **Uni Mainz** (`https://ki-chat.uni-mainz.de/api`): API-Key in
  `~/.config/opencode/opencode.json` + `continue.json.current`. Model:
  `Qwen3 235B Thinking`.

***

**2 — Angewandte Konzepte**

**Session Memory (`SESSION_CHANGELOG.md`)**

- **Location:** `core/docs/SESSION_CHANGELOG.md`
- **Read first bei jedem Session-Start.** `AGENTS.md` listet es als erste
  Knowledge-Source. opencode lädt es via `.opencode/opencode.json → instructions`
  automatisch.
- **Append-only.** Jede Session mit relevanter Arbeit bekommt einen Eintrag.
- **7 Pflichtfelder** pro Eintrag: Datum + Ziel, Done (mit `file:line`
  Evidence), Files touched, Files deleted, Not yet done, Next (ein nächster
  Schritt), Blockers.
- **Generator:** `./docs/session_entry.sh` erzeugt einen datierten Stub mit
  Git-Diff-Summary. Session füllt die Narrative aus.
- **Anti-pattern:** Keine alten Einträge editieren (Audit-Trail). Keine
  Architektur-Fakten hier ablegen (die gehören in die Knowledge Base).

**RAG Knowledge Base (`ros2k_knowledge/`)**

- **Location:** `core/src/ros2k_knowledge/`
- **7 Power-Files** + 1 Router + 1 FAQ:
  - `1_CORE_ARCHITECTURE_AND_SYNC.md` — Atomic file writes, Thread-Closures, Trace-Logging
  - `2_ROS2_PROTOCOLS_AND_FRAMES.md` — `/gazebo/model_states`, V5/V6 Engine Nodes, Fouls, Set-Pieces
  - `3_AI_LOGIC_AND_EDGE_CASES.md` — Flat-JSON, Qwen-3B, Prompt-Disentanglement, Goalie-Idle, Red P1-P5
  - `4_EDGE_HARDWARE_SIM2REAL.md` — K1 RPC, ESP32, Namespace-Isolation, micro-ROS
  - `5_HYBRID_INFRASTRUCTURE_V5.md` — U22 native, U24 Docker, Xid 31, Headless Gazebo
  - `6_DATA_SCHEMAS_AND_LIFECYCLE.md` — Worldstate, `match_state`, Trace-Schemas, 14 KPIs
  - `META_KNOWLEDGE_ROUTER.md` — **Inverted Index**: Symptom/Keyword → Power-File
  - `ROS2K_GEM_FAQ.md` — 23 Q&As, Deutsch, team-facing
- **Anti-Hallucination:** Jedes File enthält explizite Constraints ("Do NOT
  invent `/odom` topics", "Explicitly removes OOP HALs"). opencode und Continue
  lesen diese Files, bevor sie technische Fragen beantworten.
- **Versionierung:** Frontmatter mit `version: v6.1` / `v6.2` und Tag-Liste.
- **Wie der Routing funktioniert:** Query erwähnt Keyword (z.B.
  `"JSONDecodeError"`) → Router verweist auf File 1 → opencode/Continue liest
  File 1 → Antwort grounded in Axiomen, nicht in LLM-Weights.

**Alternative: opencode Agent Skills (nicht verwendet)**

opencode hat ein natives Skill-System (`.opencode/skills/<name>/SKILL.md`),
das Power-Files lazily lädt. **Aber:** Skills sind opencode-spezifisch und
funktionieren nicht in Continue. Wir behalten `ros2k_knowledge/*.md` als
kanonische Quelle. Beide Tools referenzieren dieselben Files auf ihre eigene
Weise.

***

**3 — ROS2K Knowledge Base: wofür ist sie gut?**

**Wann Knowledge Base konsultieren**

- "Wie funktioniert der Referee?" → **Ja** — File 2 + Router
- "Was bedeutet `os.replace`?" → **Ja** — File 1 + FAQ Q8
- "Welche K1 API-Codes gibt es?" → **Ja** — File 4
- "Welche Xid-31 Kernel-Parameter?" → **Ja** — File 5 + FAQ Q10
- "Was wurde in der letzten Session gemacht?" → Nein → `SESSION_CHANGELOG.md` lesen
- "Wie ist die aktuelle Match-Score?" → Nein → `shared_state/Worldstate.json` lesen
- "Wie kompiliere ich den ROS-2-Workspace?" → Nein → `AGENTS.md` → "Run / build / test commands"

**Die 10 Architektur-Axiome (Kurzfassung)**

1. **Keine OOP HALs** — Bridge nutzt dynamische Thread-Closures (`def task`)
2. **Ground Truth = `/gazebo/model_states` only** — keine `/odom`, kein TF2
3. **Tmpfs-Decoupling** — LLM ↔ ROS via `shared_state/*.json`, `os.replace` atomic writes
4. **`ROS_DOMAIN_ID=0` + `rmw_fastrtps_cpp`** — `launch_r2k.sh` überschreibt alle lokalen Env-Vars
5. **Ollama user-space only** — kein systemd, Watchdog braucht `pkill -9`
6. **Hybrid OS** — U22 native, U24 Docker, niemals micro-ROS in Docker auf U22
7. **Hardware-First Teardown** — 0.2s Watchdog: Twist-zero/API 2000 dann `pkill -9`
8. **Xid 31 Suspend Bug** — LLM-Latenz >7000ms → Nvidia-Treiber, nicht Python
9. **Strikte Nomenklatur** — nie blind Dateinamen übernehmen, gegen Knowledge Base verifizieren
10. **Zero-Tolerance Abweichungen** — falscher Name → sofort korrigieren

**Anti-Patterns: Knowledge Base**

- **Keine Runtime-Prompts in der Knowledge Base** — `strategy/fragments/*.txt`
  ist für den Robot-LLM, nicht für den Dev-Assistant.
- **Keine Session-State in der Knowledge Base** — "was gestern passiert ist"
  gehört in `SESSION_CHANGELOG.md`, nicht in ein Power-File.
- **Keine ungebundenen Appends** — Power-Files kondensieren, nicht wachsen
  lassen.

**Anti-Patterns: Code**

- **Keine hard-wired Thresholds im Code** — Schwellwerte (Distanzen,
  Geschwindigkeiten, Winkel, Timeouts) nicht als Magic Numbers im Code
  verstreuen. Als benannte Modul-Konstanten am Dateianfang definieren
  (`PUSHING_MIN_DIST = 0.3`, nicht `if dist < 0.3:`). Ermöglicht Tuning ohne
  Code-Archäologie und dokumentiert Intent.

***

**4 — Best Practices**

**Sessions**

- **Session-Start:** `SESSION_CHANGELOG.md` lesen (oder opencode macht es
  automatisch via `instructions`). Letzten "Next" + "Blockers" picken.
- **Session-Ende:** `./docs/session_entry.sh` ausführen, Eintrag
  vervollständigen. Wenn die Session nichts sinnvolles gemacht hat → keinen
  Eintrag.
- **Plan Mode:** Bei nicht-trivialen Änderungen erst Plan (opencode:
  Tab-Taste), dann Build. Verhindert teure Iterationen.
- **Trace-Logs:** `logs/llm_trace_<run_id>.jsonl` +
  `logs/world_trace_<run_id>.jsonl` werden pro Match geschrieben. KPIs mit
  `tools/analyze_trace.py` ausgewertet. Logs sind gitignored, werden nicht
  gecloned.

**Git & Machine Portability**

- **Configs maschinenportabel halten.** Kein `/home/username` hardcodieren.
  Stets `~/` oder `$PWD` verwenden.
- **`AGENTS.md` committen.** opencode liest es automatisch aus dem Repo.
  Teammitglieder beim Clonen haben sofort dieselben Build/Test-Commands.
- **API-Keys sind per-User.** Liegen in `~/.config/opencode/` und
  `~/.local/share/opencode/`, nicht im Repo. Tar-Transfer für Machine-Wechsel
  (siehe `opencode_takeover.tar.gz` Workflow).
- **`agent_prompt_de.txt` ist kanonisch.** Copilot via Symlink, Continue via
  `@file`, opencode via `instructions`. Nur an einer Stelle editieren.
- **Keine Secrets committen.** API-Keys in `continue.json.current` sind
  inline (Known Issue). `continue.json.current` ist gitignored,
  `continue.expanded.json` ebenfalls.

**Cross-Tool**

- **Drei Tools, eine Knowledge-Source.** `ros2k_knowledge/*.md` ist
  kanonisch. opencode, Continue und Copilot referenzieren dieselben Files
  auf ihre Weise.
- **`/init` in opencode nicht nötig.** Unser `AGENTS.md` ist reicher als
  das, was `/init` generieren würde. Nicht überschreiben lassen.
- **Continue `systemMessage` Update-Test.** Ob `@file` in Continue's
  `systemMessage`-Feld aufgelöst wird, muss nach jeder Continue-Version
  verifiziert werden. Wenn nicht → auf inline-`systemMessage` zurückfallen
  und manuell synchron halten.

**Team-Workflow**

- **Eine Änderung pro Branch.** Branch-Naming: `prefix/Name` (prefixes:
  `feature`, `tools`, `bugfix`, `refactor`, `docs`, `projects`). Name in
  CamelCase, Englisch, keine Umlaute.
- **Commit-Messages: Englisch.** Team-interne Doku: Deutsch. AI-Prompts
  in Code: Englisch. AI-Prompts fürs Team: Deutsch.
- **Knowledge-Base-Update bei Architekturänderung.** Wer einen neuen Node,
  ein neues Topic oder eine neue Axiom-Exception einführt, aktualisiert das
  betroffene Power-File + bumpt die Version im Frontmatter.
- **Session-Changelog-Update bei jeder Session.** Keine Ausnahme. Auch
  kurze Sessions loggen, damit der nächste Developer weiß, was schon
  probiert wurde.

***

**5 — opencode DX: Quick Wins**

> **DX = Developer Experience:** DX-Features sind opencode-Konfigurationen,
> die den Arbeitsalltag erleichtern: weniger Tippen, weniger versehentliche
> zerstörerische Commands, weniger Noise. Diese Features sind **nicht
> aktiv** — sie sind Empfehlungen für die nächste Setup-Runde.

opencode bietet Features, die wir aktuell nicht konfiguriert haben. Hier die
Quick Wins und was wir bewusst nicht nutzen.

**Quick Wins (sollten wir einrichten)**

- **Custom Commands** (`.opencode/commands/run-match.md` etc.): `/run-match`,
  `/analyze-kpis`, `/check-architecture` — Ein-Tasten-Shortcuts für
  wiederkehrende Tasks (wie Continue's `/check_ros2k`).
- **Permissions** (`.opencode/opencode.json → permission`): `grep *`,
  `git status *`, `git diff *` auto-allow; `git push *`, `rm *`, `pkill *`
  ask. Verhindert versehentliche zerstörerische Commands.
- **`watcher.ignore`** (`.opencode/opencode.json → watcher.ignore`):
  `ros2_ws/build/`, `ros2_ws/install/`, `logs/`, `shared_state/` vom
  File-Watcher ausschließen — reduziert Noise.
- **`small_model`** (`~/.config/opencode/opencode.json → small_model`):
  Günstiges Modell (`qwen2.5-coder:3b`) für Title-Generierung und Compaction
  statt des Hauptmodells.
- **`{file:}` / `{env:}` für Keys**
  (`~/.config/opencode/opencode.json → provider.options.apiKey`): API-Keys
  in `~/.secrets/` oder via Env-Vars, nicht inline in Config. Sauberer,
  sicherer, austauschbar.

**Bewusst nicht genutzt**

- **Agent Skills** (`.opencode/skills/`): opencode-spezifisch, nicht portabel
  zu Continue. Wir behalten `ros2k_knowledge/*.md` als kanonische Quelle
  (siehe Part 2).
- **MCP servers**: Overkill für aktuelles Team-Setup.
- **Plugins**: Kein Bedarf aktuell — Future Work.
- **`server` mode**: Interessant für Workshop-Demos, aber nicht für Daily
  Work.