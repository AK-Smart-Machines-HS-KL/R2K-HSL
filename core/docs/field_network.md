# K1 Field Network (WiFi profiles + static IPs)

Setup for one K1 fleet on a single WiFi network with fixed bot IPs
(RoboCup HSL Rules §3.9 context). Ubuntu 22.04 on the K1, NetworkManager.

## Files

```
core/config/field_profiles/
  lab.env                 # our lab network (committed)
  lab_hsl.env             # HSL team-subnet lab profile: 192.168.50.0/24, team 50 (see hsl_gamecontroller.md)
  venue_draft.env         # mystery TEMPLATE for competition sites (committed)
  venue_<city><year>.env  # real venue file — GITIGNORED (carries the wifi password)
utils/wifi/
  setup_K1_Network.sh     # laptop: push+install profile on K1s via SSH (pre-match!)
  set_field_wifi.sh       # K1: install the 'field' NM profile (called remotely)
  wifi_check.sh           # K1: validate rules + connectivity before a match
```

On each K1, provisioning installs everything under
`/home/booster/Workspace/r2k_wifi/` (persistent across reboots, mirrors
the `ros2_relay` deploy convention): `set_field_wifi.sh`, `wifi_check.sh`,
and the active `<profile>.env` (chmod 600 — it carries `FIELD_PASS`).

## Profile fields

| Field | Meaning |
|---|---|
| `VENUE` | `lab` (laptop debug allowed) or `match` (**`FIELD_DEBUG_IP` must be empty**) |
| `FIELD_SSID / FIELD_SECURITY / FIELD_PASS` | as announced by the organizers (§3.9.2) — `wpa-psk`/`sae`/`open` |
| `FIELD_PREFIX / FIELD_SUBNET` | team's assigned range (venue) or lab net |
| `FIELD_IP_N` | last octet for bot N → static IP `${FIELD_PREFIX}.${FIELD_IP_N}` |
| `FIELD_GATEWAY` | keep empty — field robots need no internet |
| `FIELD_BCAST` | forward-compat for the team UDP-broadcast channel (later session) |
| `FIELD_DEBUG_IP` | **MUST stay empty during real matches** — laptop access during play is a rule violation (§3.9); debug exception is wired-only ≤1 pkt/s/robot (§3.9.5). Lab use only. |

Provisioning refuses to install and `wifi_check.sh` fails if a `VENUE=match`
profile has a non-empty `FIELD_DEBUG_IP`.

## Provision (before a match / in the lab)

```bash
# First flash of ONE bot (bot reachable at its current IP, e.g. maker4 DHCP):
utils/wifi/setup_K1_Network.sh --bot 2 10.42.0.102 --exclusive

# Reconfigure ALL bots to a new venue (targets = profile statics):
utils/wifi/setup_K1_Network.sh --profile venue_lima26 --all --exclusive

# Install only, no activation, no reachability wait:
utils/wifi/setup_K1_Network.sh --profile lab --bot 3 192.168.0.103 --skip-up
```

Activation is ASYNC by default: the remote installer schedules
`nmcli con up field` via `nohup` with a 2s grace delay, so the SSH session
closes cleanly BEFORE the K1's wifi link flaps (the K1 cannot be
rebooted over SSH — manufacturer hardware limitation — so activation
must happen in place). Afterwards the laptop pings the bot's new static
IP for up to 60s (5s flap grace + 55s ping window) and reports
reachable / not reachable. Activation output lands in
`/tmp/r2k_activate.log` on the K1.

`--exclusive` is strongly recommended: without it, a failed `field`
activation can leave a competitor profile (autoconnect=yes, e.g. one
named after the SSID) holding the same IP, and the reachability wait
reports a false positive. The script warns when run without it.

Sudo password on the K1: env `BOT_SUDO_PASS` (default `123456`).
The active profile name is stored in `core/config/field_profiles/.current_profile`.

## Validate

```bash
ssh booster@192.168.0.102   # password 123456
sudo bash /home/booster/Workspace/r2k_wifi/wifi_check.sh \
    /home/booster/Workspace/r2k_wifi/lab.env --bot 2 --ping-peers
```

(`wifi_check.sh` is already on the K1 — pushed by `setup_K1_Network.sh`.)

Checks: active profile + SSID, managed mode (no ad-hoc, §3.9.3), static IP
matches the assignment, no default route, powersave off, permanent MAC, no
other autoconnecting profile, peer ping matrix, and the `FIELD_DEBUG_IP`
rule gate.

## New venue workflow

1. `cp core/config/field_profiles/venue_draft.env core/config/field_profiles/venue_<city><year>.env`
2. Fill every `_FILL_` from the organizer announcement (SSID, encryption, IP range, bot octets).
3. `setup_K1_Network.sh --profile venue_<city><year> --all --exclusive`
4. `wifi_check.sh` on each bot (`/home/booster/Workspace/r2k_wifi/`), `--ping-peers`.

Never commit a real venue file — git only tracks `lab.env` and `venue_draft.env`.

## Deferred validation (when hardware is available)

1. Dedicated router in AP mode, DHCP pool outside the bot IP block → provision 2 bots.
2. `wifi_check.sh --ping-peers` green on both.
3. Reboot a bot → auto-joins `field`, same IP.
4. Another AP in range with `autoconnect yes` → bot must NOT leave `field`.
5. Second profile file + `--profile` switch → bots follow the new SSID.

## Out of scope here (later sessions)

Laptop `launch_r2k.sh` hotspot removal · team UDP-broadcast channel + ROS 2
bridging · GameController game-state integration into ROS 2 — receiver/presence
module DONE (`core/src/game_controller_node.py` + `gc_msgs`, see
`hsl_gamecontroller.md` §"ROS2K GC receiver module"); feeding the decoded
state into `referee_node.py` / the bridge is still later · micro-ROS
agent relocation · `ROS_LOCALHOST_ONLY=1` (arrives with cross-robot ROS work).
