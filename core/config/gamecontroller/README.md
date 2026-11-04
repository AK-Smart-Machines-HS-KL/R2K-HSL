# HSL GameController configuration samples

Reference copies for running the official RoboCup HSL GameController
(https://github.com/RoboCup-HumanoidSoccerLeague/GameController) against
the K1 fleet in the lab. Full network setup:
`core/docs/hsl_gamecontroller.md`.

## Where the GC reads its configuration

The GC reads a **config directory** containing `teams.yaml` (the global
team list: name, number, jersey colors) plus one subdirectory per
competition (`<competition>/teams.yaml` = participating team numbers,
`<competition>/params.yaml` = competition constants). Candidates, first
match wins:

1. `--config-dir <dir>` (or env `GAMECONTROLLER_CONFIG`)
2. the user's directory on Linux: `~/.config/GameController` (with the
   config inside; the `args` file for persistent options sits next to it)
3. the config shipped with the installed app (`<prefix>/share/GameController/config`)
4. `config/` in the root of a source checkout (used by `cargo run`)

`GameController --show-paths` lists all candidates on your machine — the
GC also prints the used directory to stderr on start. Directories are
never combined: the chosen one must contain ALL files.
`GameController --install-config` copies the shipped configuration to
the user's directory so it can be edited (it is NOT overwritten on app
updates).

## What we need to change (team 50 = R-ZWEI KICKERS)

- **Global `teams.yaml`: NOTHING.** Team 50 ("R-ZWEI KICKERS") is
  already registered upstream (full default color palette). Verify
  after `--install-config`:
  `grep -A2 'R-ZWEI' <config-dir>/teams.yaml`
- **Competition `<competition>/teams.yaml`: add the line**
  `- 50  # R-ZWEI KICKERS`
  Upstream does NOT include team 50 in any competition list (verified
  2026-11-04), so without this edit the team cannot be selected in the
  launcher.

`large_advanced/teams.yaml` in this directory is a ready-to-copy
snapshot of the upstream list (2026-11-04) with our line appended. If we
play a different competition (small / middle / large, each in
foundation / advanced), apply the same one-line edit to that
competition's file instead.

## Jersey colors

The upstream global entry gives R-ZWEI KICKERS every available color:

- field players: red, blue, yellow, black, white, green, orange,
  purple, brown, gray
- goalkeepers: blue, yellow, black, white, green, orange, purple,
  brown, gray, red

Narrow these in the global `teams.yaml` once the actual jerseys are
fixed (the launcher enforces non-conflicting colors between the teams).