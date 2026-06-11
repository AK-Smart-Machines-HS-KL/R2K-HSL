# Naming Conventions

## Branches

Branches werden nicht einfach willy-nilly benannt und auch die bisher verwendeten Namensschemen in früheren Projekten wurden nicht immer eingehalten. Daher nun folgende Anwweisung:

- Folgende Namensstruktur soll verwendet werden: `prefix/name`
  
**Prefix**: Wir unterscheiden zwischen den folgenden Fällen:
- `feature`:  Beschreibt **neue** Funktionalität für das Kernsystem
- `tools`: Beschreibt **neue** Funktionalität außerhalb des Kernsystems
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
