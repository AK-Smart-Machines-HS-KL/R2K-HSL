# R2K-HSL
Working code repository for the RoboCup-HSL team R-ZWEI KICKERS from UAS Kaiserslautern - Campus Zweibrücken

# Naming Conventions

## Branches

Branches werden nicht einfach willy-nilly benannt und auch die bisher verwendeten Namensschemen in früheren Projekten wurden nicht immer eingehalten. Daher nun folgende Anwweisung:

- Folgende Namensstruktur soll verwendet werden: `prefix/name`
  
**Prefix**: Wir unterscheiden zwischen den folgenden Fällen:
- `feature`:  Beschreibt **neue** Funktionalität
- `bugfix`:   Beschreibt **Fehlerbehebung** 
- `refactor`: Beschreibt die **Überarbeitung** von funktionierendem Code
- `docs`:     Beschreibt das Arbeiten an der Dokumentation
- `projects`: Für Studierendenprojekte (später leichter zu filtern für Löschung oder Intergration)

**Name**:
- Soll kurz die Aufgabe des aktuellen Branches beschreiben
- Soll CamelCase befolgen (d.h. jedes Wort im Namen beginnt mit einem Großbuchstaben, aber wir lassen keine Leerzeichen)
- Soll keine Sonderzeichen oder Umlaute beinhalten (z.B ä -> ae)
- Soll in Englisch gehalten werden (Sprach-Handhabung wird im Team noch diskutiert)
- Präsenz verwenden, Vergangenheitsform ist beim Vollenden für die Commit-Message

**Beispiele**:
- `feature/RobotKick`
- `bugfix/FixLeftDriftOfKick`
- `refactor/ChangeKickMovement`
- `docs/AddDescriptionOfKick`

**Anmerkung**:
Branches werden Feature-basierend erstellt. Also jeder Branch beinhaltet nur **eine** zusammenhängende Änderung! 

# Sprache

Sämtliche Codedokumentation soll auf Englisch gehalten werden (dazu zählt: Codevariablen und Codekommentare, Commitmessages und Branches)
Teamspezifische Sachen sollen auf deutsch formuliert werden (dazu zählt: Projektarbeiten, Teaminterne Infos)

**Sonderfälle**
- Testcases werden auf Deutsch gehalten, um nachvollziehbarer sind
- KI-Prompts sind englisch, wenn diese innerhalb des Codes leben
- KI-Prompts sind deutsch, wenn diese das Team nutzen

# About Us

Die R-ZWEI KICKERS wurden in den Covid-Zeiten im Jahr 2020 gegründet und begannen mit wenigen Robotern und einem Mini-Feld im Labor der Hochschule. Seitdem hat das Team stetig Fortschritte gemacht, bis hin zweifachen Vizeweltmeister in der Standard Platform League (SPL) -- Challenge Shield Division (CSD) 2023 und 2024.
In diesem Repository wird nun unsere Codebasis für die neu formierte Humanoid Soccer League (HSL) leben, in welcher wir in der Small Division bei der German Open 2026 bereits angetreten sind und wo wir mit den BoosterRobotics K1 Robotern als neue Plattfrom demnächst in die Middle Size Division einsteigen möchten. Dieses Repository hält somit unsere neuesten Anstregungen zur Forschung in der humanoiden Robotik und intelligenten Verhaltenssteuerung fest.

## Contact Us

**Discord**: [Link]
