# Projektvorschlag: On-Board-LLM für den K1

**Status:** Vorschlag — kein Beschluss. Emulation fruehestens nach v6.7-Abschluss.

---

## 1. Motivation — die gemessene "Small-Model-Decke"

Das 3B-Produktionsmodell (qwen2.5:3b) zeigt drei messbare Geometriefehler, die
promptseitig nicht behebbar sind (W7/W8-Probe, WIN/SP-Klaerung):

| Fehler | Live (n=24) | Text-Probe | Quelle |
|---|---|---|---|
| Falscher Kicker (nicht der Naechste) | 44-49% | 60-67% | `json_quality_report.md` |
| Torwart ueberlaeuft (>2m vom Tor) | 58-64% | — | `json_quality_report.md` |
| Degenerierte Ziele (Ziel == Ball) | 51-55% | — | `json_quality_report.md` |

Gleichzeitig hat das 14B-Modell in der v6.6-Kalibrierung Gitteraufgaben 20/20
geloest, an denen das 3B 0/20 scheiterte [LESSONS_LEARNED]. Die Loesung liegt
eine Modellgroessenklasse hoeher — aber die Latenz darf nicht linear skalieren.

## 2. Loesungsansatz: Edge-LLM auf dem Roboter

Statt die LLM-Entscheidung auf dem Host-PC (RTX 5090 Laptop) zu treffen, wird
sie **direkt auf dem K1** ausgefuehrt — auf einem Co-Prozessor der NVIDIA-Jetson-
Familie. Der ROS2K-Stack und das Evaluator-Interface aendern sich nicht: das
LLM gibt weiterhin flaches JSON mit `assignments` aus.

Der Unterschied ist die Modellklasse: **Mixture-of-Experts (MoE)**[^MoE] mit
21-30B Totalparametern bei nur **3.3-3.6B aktiven Parametern pro Token**.
Zehnfach mehr Wissen bei 3B-aehnlicher Inferenzgeschwindigkeit.

### Kandidaten M'

| Modell | Total | Aktiv | Groesse | Quantisierung | Kontext | Orin-Beleg |
|---|---|---|---|---|---|---|
| **gpt-oss:20b** (OpenAI) | 21B | 3.6B | ~14 GB | **MXFP4**[^MXFP4] | 128k | **offiziell: 40 tok/s** via vLLM [NVIDIA-Blog] |
| **Qwen3-30B-A3B** (Alibaba) | 30.5B | 3.3B | ~18 GB | W4A16 | 128k | Jetson AI Lab: laeuft auf Orin NX 16GB [Jetson-AI-Lab] |
| **Qwen3-8B** (dense, Fallback) | 8B | 8B | ~5 GB | Q4_K_M | 128k | Jetson AI Lab: Orin 16GB |

Warum MoE statt Dense? Der entscheidende Vorteil ist **memory-bandwidth-bound**
Latenz[^bandwidth]: weniger aktive Parameter pro Token = weniger Speicherzugriff
= schnellere Antwort. Auf dem Zielsystem (204.8 GB/s Speicherbandbreite)
skaliert die Tokenrate nahezu linear mit den aktiven Parametern.

### Runtime-Vergleich

| Engine | Orin-Toks/s (7B) | Setup-Aufwand | Vorteil |
|---|---|---|---|
| **TensorRT-LLM (NGC-Container)**[^TRT] | ~180 (Forum) | Hoch | Hoechster Durchsatz, NVIDIA-Kernel |
| **vLLM Jetson-Container** | ~40 (gpt-oss) | Mittel | OpenAI-API, NVIDIA-Dokumentation |
| llama.cpp | ~10-20 | Gering | Fuer <1s-Ziel zu langsam |
| Ollama (auf Jetson) | ~Ollama-basiert | Gering | Nur Qualitaetstests |

#### Latenzrechnung: <1s-Ziel auf AGX Orin 32GB

Modell | Engine | Tok/s (Orin) | ~50 Output-Tok | ~90 Output-Tok
---|---|---|---|---
gpt-oss:20b | vLLM | ~40 | **~1.3s** (mit reasoning=low) | ~2.3s
Qwen3-8B | TRT-LLM | ~100-180 | **~0.3-0.5s** ✓ | **~0.5-1.0s** ✓
Qwen3-30B-A3B | vLLM | ~40-50 | **~1.0-1.3s** | ~1.8-2.3s
Qwen3-4B | TRT-LLM | ~150-200 | **~0.25-0.3s** ✓ | ~0.45-0.6s ✓

**Fazit:** Mit einem 7-8B dichten Modell auf TRT-LLM ist <1s realistisch.
MoE-Modelle sind knapper, gewinnen aber durch kompakte Outputs (~30-50 Tokens),
die im Zuge eines algorithmisch verbesserten Weltmodells (TeamCaptain v7)
realistisch werden — die Geometrieberechnung wandert CPU-seitig.

### Hardware-Anforderung

Die benoetigte Zielhardware (NVIDIA Jetson AGX Orin 32GB):

- **GPU:** 2048 CUDA-Cores, 64 Tensor-Cores (Ampere)
- **Speicher:** 32 GB LPDDR5, 204.8 GB/s Bandbreite
- **TOPS:** 200-275 TOPS (INT8 sparse)
- **OS:** Ubuntu 22.04 via JetPack 6 — nativer Build, identisch U22-Erfahrung
- **Leistung:** ~15-30W im MAXN[^MAXN]-Modus; moderate Modes fuer Dauerbetrieb

Das aktuelle K1-Board verfuegt ueber keinen Co-Prozessor dieser Klasse — die
existierende MCU/ESP32-Architektur kann LLM-Inferenz nicht hosten.

## 3. Emulation auf der vorhandenen 5090 (vor Hardware-Investition)

Bevor Hardware beschafft wird, wird das gesamte Szenario auf dem vorhandenen
U24/Docker/RTX-5090-Laptop emuliert — in zwei Stufen.

### Stufe 0 — Qualitaetstests (heutige Toolchain)

`ollama pull gpt-oss:20b` (14 GB), `ollama pull qwen3:30b` (19 GB) → **dieselben
Gewichte** wie auf dem Jetson. Das existierende `probe_s1.py`-Instrument (28
Situationen, Kanarienvogelmetriken) misst direkt die Geometriefehler — ohne
eine Zeile Evaluator-Code zu aendern. Die Umgebungsvariable
`R2K_OLLAMA_MODEL=<M>` steuert das Modell.

**KV-Cache-Disziplin**[^KVCache] wird angewendet (Stoeraufruf + selbe-Sitzung-
Kontrolle) — Standardprotokoll aus S1/WIN/SP-Probes.

### Stufe 1 — Latenzkalibrierung

vLLM-Container auf der 5090 (`vllm/vllm-openai`, Port 8000) → Modell mit
denselben Einstellungen (Quantisierung, PagedAttention). **Der Ankerpunkt:**
NVIDIA hat gpt-oss-20b via vLLM auf AGX Orin mit 40 tok/s gemessen
[NVIDIA-Blog]. Auf der 5090 messen wir X tok/s → Skalierungsfaktor ≈4.4x
(Speicherbandbreite ~896 GB/s vs 204.8 GB/s). Dieser Faktor uebertraegt
sich auf alle anderen Kandidaten.

Zur Anbindung an den Probe: OpenAI-kompatibler Client (~30-50 Zeilen Python)
von `/api/generate` nach `/v1/chat/completions`. Kein Produktionscode.

## 4. Optionale Erweiterung: v7-Simulation

Synthetische CPU-Fakten (naechster Bot, offene Gassen) als Prompt-Injektion
in das existierende Pruefkorpus — simuliert die TeamCaptain-Welt ohne v7-Code.
Ermoeglicht die Messung eines "Fast-Selector"-Szenarios mit Output-Budget
~30-50 Tokens. Machbar durch den bestehenden Probe-Varianten-Mechanismus
(W7/W8-Varianten, WIN-Varianten).

## 5. Naechste Schritte (nach v6.7-Abschluss)

1. **`ollama pull gpt-oss:20b` (14 GB) + `qwen3:30b` (19 GB) + `qwen3:8b` (5 GB)**
2. **Stufe-0-Probes:** `R2K_OLLAMA_MODEL=<M> python3 src/tools/probe_s1.py b --out <ergebnis>`
   je Kandidat (~30 min, total ~2h, sequenziell). Kein GPU-Wettbewerb nach
   Benchmark-Ende.
3. **Stufe-1-Aufbau:** vLLM-Container + Latenzmessung (1 Session)
4. **Auswertung:** Reporting + Vergleich mit 3B-Baselines. Kriterien:
   - Kicker==Naechster ≥75% (Basis 55.7%)
   - Torwart-Ueberlauf ≤25% (Basis 57.8%)
   - Parse ≥98%, Kanarienvogel 100%

## 6. Risiken

| Risiko | Schwere | Mitigation |
|---|---|---|
| MoE-Kernel auf Orin unreifer als Dense | Mittel | vLLM-Tests + Jetson AI Lab Benchmarks |
| gpt-oss Reasoning-Token fressen Output-Budget | Mittel | `reasoning=low` setzen; `num_predict` erhoehen |
| Thermische Drosselung im MAXN-Betrieb | Gering | Moderatere Power-Modes im Dauerbetrieb |
| Probe-vs-Live-Gap (v6.3 bestaetigt: ~10pp) | Mittel | Akzeptieren; Live-Smoke als Folgephase |
| TRT-LLM-Setup-Aufwand (falls noetig) | Mittel | vLLM reicht fuer Entscheidungsqualitaet |

## 7. Quellen

| # | Quelle | Bezug |
|---|---|---|
| [json_quality_report] | `src/results/json_quality_report.md` | 3B-Blind-Spot (n=24) |
| [LESSONS_LEARNED] | `docs/LESSONS_LEARNED.md` $6.6 | 14B 20/20 grid probe |
| [W7W8] | `src/results/probe_w7w8_report.md` | Prompt-Channel-Klaerung |
| [OpenAI-gpt-oss] | `openai.com/index/introducing-gpt-oss` | gpt-oss Launch (August 2025), MXFP4, 128k |
| [HF-Qwen3-30B] | `huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507` | Architektur, IFEval 84.7, AIME 61.3 |
| [Jetson-AI-Lab] | `jetson-ai-lab.com/models/` | Offizielle Modellmatrix + SOM-Support |
| [NVIDIA-Blog] | `edge-ai-vision.com` (NVIDIA Gastbeitrag Jan 2026) Fig 1 | gpt-oss-20b auf AGX Orin: **40 tok/s** via vLLM |
| [NVIDIA-Forum] | `forums.developer.nvidia.com/t/343901` | TRT-LLM 7B ~180 tok/s Forum-Report |
| [Ollama-gpt-oss] | `ollama.com/library/gpt-oss` | gpt-oss:20b 14 GB, MXFP4, Ollama-integriert |
| [Ollama-qwen3] | `ollama.com/library/qwen3` | qwen3:30b 19 GB Q4_K_M, Tools, Thinking |
| [multimodalflow] | `multimodalflow.net/en/benchmark/` | Living Benchmark AGX Orin/Thor/Spark |
| [iotdigitaltwinplm] | `iotdigitaltwinplm.com/edge-llm-benchmark-jetson-orin-llama-phi-gemma-q2-2026/` | 5-Engine-Vergleich |

---

## Fussnoten

[^MoE]: **MoE (Mixture-of-Experts) Routing** – Architektur, bei der das Modell
aus Dutzenden von "Experten" (Subnetzen) pro Token nur eine Handvoll aktiviert.
Ein Gate-Mechanismus (Router) entscheidet, welche Experten zustaendig sind.
Ergebnis: 30B Gesamtwissen bei ~3B Rechenaufwand pro Token — der wichtigste
Skalierungshebel fuer LLMs auf Edge-Hardware.

[^MXFP4]: **MXFP4 (Microscaling FP4)** – 4-Bit-Gleitkomma-Quantisierung, die
OpenAI nativ fuer gpt-oss trainiert hat (keine nachtraegliche Quantisierung).
4.25 Bit pro Parameter. Nativ unterstuetzt in NVIDIAs Blackwell- und Ampere-
Architekturen. Erstmalig in der gpt-oss-Reihe eingesetzt.

[^bandwidth]: **Memory-bandwidth-bound** – Die Tokenerzeugung wird durch die
Speicherbandbreite limitiert, nicht durch Rechenleistung. Beim LLM-Decode muss
pro Token das Modell (bei MoE: die aktiven Experten) aus dem VRAM geladen
werden. Formel: Tokens/s ≈ Speicherbandbreite ÷ aktive Modellgrosse (Bytes).
Auf AGX Orin (204.8 GB/s) erklaert dies, warum MoE mit 3.3B aktiven (2-4 GB
Lesevolumen pro Token) ~5x schneller ist als ein 14B-dichtes Modell.

[^TRT]: **TRT-LLM (NGC-Container)** – NVIDIAs Optimierungsframework fuer
LLM-Inferenz. NGC (NVIDIA GPU Cloud) stellt vorgefertigte Container bereit
– fuer Jetson (`ghcr.io/nvidia-ai-iot/tensorrt-llm`) und fuer x86-Hosts.
TRT-LLM optimiert Attention-Kernel, KV-Cache und Quantisierung fuer die
Zielhardware. Hoehster Durchsatz, aber aufwaendigster Setup (Engine-Build pro
Modell + Plattform-Kombination).

[^MAXN]: **MAXN (Jetson Power Mode)** – Jetson-eigener Maximalleistungs-Modus.
GPU, Speichertakt und CPU laufen auf maximaler Stufe; thermische Limits werden
angehoben. Hoechste Rechenleistung bei ~30W. Fuer thermisch unkritische
Testlaenufe geeignet; im Dauerbetrieb auf dem Roboter wird ein moderaterer
Modus (z.B. 15W) gewaehlt, um Daempfung zu vermeiden. Der Begriff stammt aus
NVIDIAs Jetson-Power-Management-API (`nvpmodel -m 0`).

[^KVCache]: **KV-Cache-Disziplin (Distractor Call + Same-Session Control)** –
Standardisiertes Protokoll fuer reproduzierbare LLM-Proben. Schritt 1:
Stoeraufruf (distractor) mit irrelevantem Prompt → laedt Modell und waermt
Cache. Schritt 2: Erster gemessener Aufruf wird verworfen (Cache noch nicht
stabil). Schritt 3: Alle Folge-Aufrufe werden gemessen. *Same-Session-Control:*
Mehrere Arme (Modell-/Prompt-Varianten) in derselben Sitzung mit kontrolliertem
Cache-Zustand vergleichen. Notwendig, weil `temperature=0.0` nicht
bit-exakt-deterministisch ist (gemessener Effekt 2026-08-01: Versionsabhaengige
Tokensequenzen trotz identischer Parameter).

---

## Addendum 2026-08-29 — hardware resolution

The proposal's target hardware is a **standard catalog variant**: the K1 ships in
three variants (Geek: ARM-only / Education: Jetson Orin NX 8GB / **Professional:
Jetson AGX Orin 32GB, 200 TOPS**). Our fleet = 2x Education (confirmed 2026-08-28);
a Professional is a candidate acquisition whose feasibility THIS document explores
(Stage 0 quality + Stage 1 latency on the 5090 provide the evidence first).
The 2 Education units meanwhile cover hardware-team play; onboard vision (TRT
engines from the RoboCup stack) is plausible on the Orin NX 8GB class.
