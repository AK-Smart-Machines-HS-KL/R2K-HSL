# ADR-A06: Ollama — User-Space Axiom vs. systemd Override

**Date:** 2026-08-03
**Status:** Applied (2026-08-18 — axiom 5 updated in agent_prompt_de.txt, META_KNOWLEDGE_ROUTER.md, 3_AI_LOGIC_AND_EDGE_CASES.md, ROS2K_GEM_FAQ.md)

## Glossary

| Term | Meaning |
|---|---|
| **Bridge** | `ollama_sandbox_bridge.py` — the ROS 2 node that translates LLM output into robot commands. Runs at 10Hz. |

## Context

Axiom 5 in `core/src/ros2k_knowledge/agent_prompt_de.txt` states:

> **User-Space Exklusivitaet:** Ollama (qwen2.5-coder:3b) MUSS zwingend im lokalen User-Space ausgefuehrt werden. Systemd-Dienste sind streng verboten, da der 0.2s Asynchronous Watchdog ansonsten das "pkill -9 ollama" nicht ausfuehren kann.

Translation: Ollama MUST run in user-space. systemd services are strictly forbidden because the 0.2s watchdog can't `pkill -9 ollama` if it's managed by systemd.

However, `core/install.sh:77-84` (added 2026-07-27, U24 branch) explicitly creates a systemd drop-in override for `ollama.service`:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"' | \
    sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

This was added to fix the recurring "dead blue team" bug (2026-07-27, 4th occurrence): Ollama started by the official installer runs as a systemd service bound to `127.0.0.1`, which Docker containers can't reach. The override sets `OLLAMA_HOST=0.0.0.0` so the container can reach `172.17.0.1:11434`.

The axiom and the code **directly contradict each other.**

## Decision

**Reconcile the axiom with the code.** The axiom's intent (watchdog can kill Ollama) is preserved; the "strictly forbidden systemd" wording is updated.

### Resolution (applied 2026-08-18)

Update axiom 5 in `agent_prompt_de.txt` to:

> Ollama MUST be reachable at `0.0.0.0:11434` (not just `127.0.0.1`) so Docker containers can access it via `172.17.0.1`. This is achieved either by:
> - **Manual start:** `OLLAMA_HOST=0.0.0.0 ollama serve` (user-space, no systemd)
> - **systemd service with override:** `ollama.service` + `Environment="OLLAMA_HOST=0.0.0.0"` (via `install.sh` or `systemctl edit ollama`)
>
> The 0.2s watchdog's `pkill -9 -f "ollama serve"` works in both cases: user-space processes die immediately; systemd services restart (which is acceptable — the watchdog's purpose is to freeze the bots during teardown, not to keep Ollama down permanently).

## Rationale

1. **The watchdog still works with systemd.** `pkill -9 -f "ollama serve"` kills the process; systemd's `Restart=always` restarts it. The watchdog's purpose (send Twist-zero / API 2000 before killing ROS 2 nodes) is preserved — the brief Ollama restart doesn't affect the freeze.

2. **The bind-address bug is the real problem, not systemd.** 4 separate "dead blue team" incidents (2026-07-20, 07-23, 07-27, 07-31) were caused by Ollama binding to `127.0.0.1` (loopback only), not by systemd per se. The fix (`OLLAMA_HOST=0.0.0.0`) works regardless of whether Ollama is started manually or via systemd.

3. **systemd has advantages on U24:** auto-restart on crash, log management via journalctl, consistent startup. For a development machine that reboots, systemd is more reliable than a manual `nohup`.

4. **Manual start has advantages for debugging:** full env-var control (`OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`, `OLLAMA_KEEP_ALIVE`), no sudo needed, easy to kill and restart. The new `tools/start_ollama.sh` (Phase C) makes this convenient.

## Alternatives Considered

1. **Enforce user-space only** (remove the `install.sh` systemd override) — would re-introduce the bind-address bug on fresh U24 installs where Ollama was installed via the official installer (which creates a systemd service by default).

2. **Enforce systemd only** (remove the manual-start path) — would lose env-var flexibility for debugging and experimentation. The Phase M sweeps need precise control over Ollama env vars.

3. **Support both, document both** (the proposed resolution) — the most flexible and matches the actual code. The axiom becomes a reachability requirement (`0.0.0.0:11434`) rather than a process-management requirement.

## Consequences

- **`agent_prompt_de.txt` axiom 5 needs updating** — the "systemd strictly forbidden" wording is wrong per the code. Replace with the reachability requirement.
- **`AGENTS.md`** references axiom 5 — needs to be checked for consistency after the axiom update.
- **`install.sh:77-84`** stays as-is (systemd override for U24).
- **`tools/start_ollama.sh`** (Phase C) provides the manual-start path with all env vars.
- **`launch_r2k.sh:184`** exports `OLLAMA_HOST=0.0.0.0` before the Ollama check — this is the belt-and-suspenders that ensures the env var is set even if the systemd override is missing.
- **The watchdog (`launch_r2k.sh:142-144`)** `pkill -9 -f "ollama_sandbox_bridge"` etc. continues to work — it kills ROS 2 nodes and the bridge, not Ollama directly (Ollama is killed by `launch_r2k.sh:189`'s `nohup` path or left running under systemd).

## References

- `core/src/ros2k_knowledge/agent_prompt_de.txt` axiom 5 (the "strictly forbidden" wording)
- `core/install.sh:77-84` (systemd override — the code that contradicts the axiom)
- `core/launch_r2k.sh:184` (`export OLLAMA_HOST=0.0.0.0`), `:225-236` (container-reachability guard)
- `core/docs/SESSION_CHANGELOG.md` 2026-07-27 (bind-address bug + fix), 2026-08-03 (QA review flags contradiction)
- `core/tools/start_ollama.sh` (Phase C — manual start path, not yet implemented)