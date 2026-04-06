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

**Name**:
- Soll kurz die Aufgabe des aktuellen Branches beschreiben
- Soll CamelCase befolgen (d.h. jedes Wort im Namen beginnt mit einem Großbuchstaben, aber wir lassen keine Leerzeichen)
- Soll keine Sonderzeichen oder Umlaute beinhalten (z.B ä -> ae)
- Soll in Englisch gehalten werden

**Beispiele**:
- `feature/RobotKick`
- `bugfix/FixedLeftDriftOfKick`
- `refactor/ChangedKickMovement`
- `docs/AddedDescriptionOfKick`

**Anmerkung**:
Branches werden Feature-basierend erstellt. Also jeder Branch beinhaltet nur **eine** zusammenhängende Änderung! 
