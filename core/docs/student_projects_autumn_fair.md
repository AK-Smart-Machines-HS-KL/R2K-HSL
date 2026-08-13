# ROS2K Student Projects — Demos & POCs

> [!info] Zweck
> Projektbeschreibungen für die Studenten-Rekrutierung. Jeder Projektabschnitt
> ist selbst-contained: er enthält die allgemeinen Projektinfos, den Kontext
> und die Support-Struktur. Für Trello: jeden Abschnitt zwischen den `---`
> Trennern in eine eigene Karte kopieren. Summary-Tabelle am Ende für das
> Board-Overview.

---

## P1 — Sprachgesteuerte K1-Robotersteuerung auf Deutsch

### Über das Projekt

Das [ROS2K-Projekt](https://github.com/AK-Smart-Machines-HS-KL/R2K-HSL) der
Studententeams **R2K-HSL / RWEI KICKERS** an der Hochschule Kaiserslautern ist
ein Hybrid-Robotics-Testbed: ein lokales LLM steuert simulierte und physische
Roboter ([Booster K1](https://www.boosterrobotics.com/) Biped,
[Yahboom](https://www.yahboom.com/) ESP32-Rover) über [ROS 2](https://docs.ros.org/).
Robotik-Labor in **Raum O 02**, **dedizierte GPU-Laptops** für die Projektdauer,
Mentoring durch das erfahrene R2K-Team.

### Ziele

Funktionierende Voice-Command-Loop: ein Mensch spricht Deutsch mit dem
[Booster K1](https://www.boosterrobotics.com/) ("Kev1n, fahr zu Position drei"),
der Roboter versteht, führt aus und antwortet mit Sprache + Körpersprache.
Ziel ist ein demo-reifer Prototyp (POC).

### Approach

Pipeline: Mikrofon -> Speech-to-Text -> LLM Intent-Parsing -> ROS-2-Kommando
an den K1 -> Text-to-Speech-Antwort -> Geste. Start mit 10-20 festen
Kommandos, dann Open-Vocabulary. Körpersprache (vordefinierte Gesten) bei
Bestätigung, Fehler und Idle.

### Tools & Methoden

[Whisper](https://openai.com/research/whisper) (lokal, Deutsch),
[Ollama](https://ollama.com/) (lokales LLM),
[Piper TTS](https://github.com/rhasspy/piper) (Deutsch),
[ROS 2 Humble](https://docs.ros.org/en/humble/), Python. K1-Hardware im
Labor O 02.

### Teamgröße

1-2 Studierende.

---

## P2 — K1 als Lager-Assistent: Bilderkennung und chat-geführte Navigation

### Über das Projekt

Das [ROS2K-Projekt](https://github.com/AK-Smart-Machines-HS-KL/R2K-HSL) der
Studententeams **R2K-HSL / RWEI KICKERS** an der Hochschule Kaiserslautern ist
ein Hybrid-Robotics-Testbed: ein lokales LLM steuert simulierte und physische
Roboter ([Booster K1](https://www.boosterrobotics.com/) Biped,
[Yahboom](https://www.yahboom.com/) ESP32-Rover) über [ROS 2](https://docs.ros.org/).
Robotik-Labor in **Raum O 02**, **dedizierte GPU-Laptops** für die Projektdauer,
Mentoring durch das erfahrene R2K-Team.

### Ziele

Der [Booster K1](https://www.boosterrobotics.com/) agiert als
Handling-Assistent in einem Lager/Produktionsszenario: Nutzer zeigt ein
Ersatzteil -> K1 identifiziert es -> K1 navigiert zum richtigen Lagerfach ->
bestätigt. End-to-Ende-Demo (POC): Foto -> Erkennung -> Navigation -> Ankunft.

### Approach

Kamera -> Bilderkennung (fine-tuned auf ~10-20 Ersatzteile) -> LLM mappt
Teil zu Lagerort -> K1 läuft zu den Koordinaten -> Bestätigung per TTS oder
Chat. Start mit 5 Teilen, Skalierung auf 15-20.

### Tools & Methoden

[YOLOv8](https://docs.ultralytics.com/) oder
[MobileNetV3](https://paperswithcode.com/method/mobilenetv3) (Transfer
Learning), [OpenCV](https://opencv.org/),
[ROS 2 Humble](https://docs.ros.org/en/humble/),
[Ollama](https://ollama.com/), Python. K1-Hardware + Labormöblierung in O 02.

### Teamgröße

1-2 Studierende.

---

## P3 — Yahboom-Roboter zieht K1-Displaystand: ROS-2-Relay-Positionierung

### Über das Projekt

Das [ROS2K-Projekt](https://github.com/AK-Smart-Machines-HS-KL/R2K-HSL) der
Studententeams **R2K-HSL / RWEI KICKERS** an der Hochschule Kaiserslautern ist
ein Hybrid-Robotics-Testbed: ein lokales LLM steuert simulierte und physische
Roboter ([Booster K1](https://www.boosterrobotics.com/) Biped,
[Yahboom](https://www.yahboom.com/) ESP32-Rover) über [ROS 2](https://docs.ros.org/).
Robotik-Labor in **Raum O 02**, **dedizierte GPU-Laptops** für die Projektdauer,
Mentoring durch das erfahrene R2K-Team.

### Ziele

Ein [Yahboom](https://www.yahboom.com/) ESP32-Rover zieht einen A0-großen
Displaystand mit [Booster K1](https://www.boosterrobotics.com/)-Lebensbild
(physischer Platzhalter/"Text Dummy") zu vordefinierten Positionen. Ziel ist
eine zuverlässige Positionierung via ROS-2-Architektur — demo-reifer Prototyp.

### Approach

Yahboom zieht den Stand über eine physische Anhängerkupplung. Navigation zu
3-4 Wegpunkten, zunächst Open-Loop, später optional mit Kamera-Feedback
(projektübergreifend mit P4 "Eye in the Sky"). ROS-2-Relay mappt
Bewegungskommandos auf den Yahboom.

### Tools & Methoden

[ROS 2 Humble](https://docs.ros.org/en/humble/), Python, bestehende
Relay-Profile. Physischer Aufbau: A0-Schaumstoffstand + leichte
Anhängerkupplung + [Yahboom](https://www.yahboom.com/)-Rover. Test im Labor O 02.

### Teamgröße

1 Studierender (handwerklich orientiert) oder 2 (ein Hardware, ein Software).

---

## P4 — Eye in the Sky: Kamerabasierte Ground-Truth-Erfassung für ROS2K

### Über das Projekt

Das [ROS2K-Projekt](https://github.com/AK-Smart-Machines-HS-KL/R2K-HSL) der
Studententeams **R2K-HSL / RWEI KICKERS** an der Hochschule Kaiserslautern ist
ein Hybrid-Robotics-Testbed: ein lokales LLM steuert simulierte und physische
Roboter ([Booster K1](https://www.boosterrobotics.com/) Biped,
[Yahboom](https://www.yahboom.com/) ESP32-Rover) über [ROS 2](https://docs.ros.org/).
Robotik-Labor in **Raum O 02**, **dedizierte GPU-Laptops** für die Projektdauer,
Mentoring durch das erfahrene R2K-Team.

### Ziele

Eine Overhead-Kamera überwacht das Spielfeld und liefert unabhängige
Ground-Truth-Positionen für Roboter, Ball, Torpfosten und Feldlinien.
Validierung gegen die Gazebo-Simulation. Basis für zukünftiges
Closed-Loop-Perception-Research (Kalman-Filter, echte Feldtests ohne
Gazebo). Höchster Langzeitwert aller vier Projekte.

### Approach

Overhead-Kamera -> OpenCV-Bildverarbeitung (Farb-Blobs für Roboter, Hough
Circle für Ball, Edge Detection für Feldlinien) -> Koordinatentransformation
Pixel zu Feldkoordinaten -> ROS-2-Publisher. Validierung gegen
Simulations-Ground-Truth, dann Feldtest ohne Simulation.

### Tools & Methoden

[OpenCV](https://opencv.org/) (Python),
[ROS 2 Humble](https://docs.ros.org/en/humble/), Kamera-Kalibrierung
(Checkerboard), Perspektiv-Transformation. Hardware: 1080p-USB-Kamera +
Stativ/Deckenmontage. Testfeld in O 02.

### Teamgröße

1 Studierender (CV-Fokus) oder 2 (ein CV, ein ROS-2-Integration).

---

## Summary

| # | Projekt | Tools | Team |
|---|---------|-------|------|
| P1 | Sprachgesteuerte K1-Steuerung (Deutsch) | Whisper, Ollama, Piper, ROS 2 | 1-2 |
| P2 | K1 Lager-Assistent (Bilderkennung) | YOLOv8/MobileNet, OpenCV, Ollama | 1-2 |
| P3 | Yahboom + K1-Displaystand | ROS 2, Yahboom, Physischer Aufbau | 1-2 |
| P4 | Eye in the Sky (Kamera-Ground-Truth) | OpenCV, ROS 2, Kamera-Kalibrierung | 1-2 |

### Abhängigkeiten

- **P3 (Yahboom)** profitiert von **P4 (Eye in the Sky)** für Closed-Loop-Positionierung — kann aber unabhängig Open-Loop laufen.
- **P2 (Lager)** und **P1 (Voice)** teilen sich den K1 — Laborzeit koordinieren.
- **P4 (Eye in the Sky)** ist die Basis für das 6-Monats-Praktikum (Closed-Loop-Perception) — höchster Langzeitwert.

### Notes für Trello

- Jeder `##`-Abschnitt ist self-contained — zwischen zwei `---` Trennern in eine eigene Trello-Karte kopieren.
- Das "Über das Projekt"-Subsegment wiederholt sich in jeder Karte (gewollt — für physische Verteilung).
- Suggested Labels: `student-project`, `demo`, `2-month`.
- P4 hat den höchsten Forschungswert; P1 und P2 sind die sichtbarsten Demos; P3 ist der hardware-lastigste.