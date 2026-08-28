#!/usr/bin/env python3
"""r2k_supervisor.py — PID-tracked process manager + state machine + file-bus backend.

Replaces ws_backend.py. Runs inside the r2k_gzweb Docker container on port 8765.
Does NOT modify the ROS2K runtime architecture — it launches and monitors the
same processes that launch_gzweb.sh launches, but tracks them by PID.

Endpoints (aiohttp, one port):
  GET /catalog          scenarios (mode-grouped strategies) + Ollama models
  GET /state            JSON snapshot of shared_state files
  GET /health           all subsystem statuses
  GET /launch           start a match (scenario, strategy, model, explain, duration, demo)
  GET /done             teardown + VRAM unload
  GET /runs             recent run ids (trace logs)
  GET /git/commits      last commits (repo root NOT mounted — degraded)
  GET /session/digest   SESSION_CHANGELOG tail (NOT mounted — degraded)
  GET /reboot/check     alias of /health
  WS  /ws               push: state transitions, health, file-bus updates
  GET / and /{path}     static GUI files (registered LAST — catch-all)

Gotchas honored (docs/SESSION_CHANGELOG 2026-08-24, gui_v67_discussion ANNEX):
  - PID-tracked children instead of pkill pattern matching (race-free teardown)
  - stale active_scenario.json cleaned before setup (old bots must not respawn)
  - Ollama unload via non-blocking asyncio (subprocess.run would freeze 8s/model)
  - API routes registered BEFORE the static catch-all
"""

import asyncio
import glob
import json
import mimetypes
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import Enum

from aiohttp import web
import aiofiles

# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------
SHARED_STATE_DIR = os.environ.get("R2K_SHARED_STATE", "/workspace/shared_state")
SCENARIO_DIR = "/workspace/scenario"
STRATEGY_FRAG_DIR = "/workspace/strategy/fragments"
GUI_DIR = "/workspace/tools/gui"
LOG_DIR = "/workspace/logs"
REPO_DOCS_DIR = "/workspace/docs"  # only present if repo root ever gets mounted
PORT = 8765
SOURCE_CMD = "cd /workspace && source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash"

FILES_TO_MONITOR = ["Worldstate.json", "current_strategy.json", "waypoints.json"]
CLEANUP_FILES = ["Worldstate.json", "current_strategy.json", "waypoints.json",
                 "task_input.json", "active_scenario.json"]

GZSERVER_READY_TIMEOUT_S = 15
GZSERVER_PROBE_PORT = 11345
SETUP_TIMEOUT_S = 15
SPAWN_TIMEOUT_S = 20
TEARDOWN_SETTLE_S = 2.0
HEALTH_INTERVAL_S = 2.0
HEALTH_CHECK_TIMEOUT_S = 2.0
FILE_POLL_INTERVAL_S = 0.2
FILE_BUS_STALE_S = 5.0
OLLAMA_PS_TIMEOUT_S = 3
OLLAMA_UNLOAD_TIMEOUT_S = 8
OLLAMA_URLS = ["http://127.0.0.1:11434", "http://172.17.0.1:11434"]
OLLAMA_GENERATE_URL = os.environ.get(
    "R2K_OLLAMA_URL", "http://172.17.0.1:11434/api/generate")

RELAY = "only_sim_bots"  # fixed: GUI is sim-only (like launch_gzweb.sh)
RUNS_MAX = 10
DIGEST_TAIL_LINES = 30

# Assistant panel (v7 Copilot seed, mode B): persona + META-ROUTER context
# are host-dumped into shared_state/assistant_ctx/ by launch_gzweb.sh —
# the knowledge base itself is NOT mounted in the container.
ASSISTANT_CTX_DIR = os.path.join(SHARED_STATE_DIR, "assistant_ctx")
ASSISTANT_CTX_FILES = ["agent_prompt_de.txt", "META_KNOWLEDGE_ROUTER.md"]
ASSISTANT_DEFAULT_MODEL = os.environ.get("R2K_ASSISTANT_MODEL", "qwen2.5:7b")
ASSISTANT_TIMEOUT_S = 90
ASSISTANT_NUM_PREDICT = 512
ASSISTANT_TEMPERATURE = 0.3
ASSISTANT_SNAPSHOT_MAX_CHARS = 8000

# Foreign-process teardown patterns (leftovers from a launch_gzweb.sh run —
# the supervisor cannot PID-track processes it did not start).
FOREIGN_PATTERNS = ["gzserver", "gzclient", "server.js 8080", "r2k_evaluator",
                    "ollama_sandbox_bridge", "referee_node", "score_node",
                    "reward_node", "rule_evaluator_red", "state_aggregator",
                    "r2k_world_model", "json_spawner"]

ROS2_NODE_NAMES = ["tracker", "referee", "score", "reward",
                   "rule_evaluator_red", "state_aggregator", "bridge", "evaluator"]

# Bridge feature flags (same defaults as launch_gzweb.sh)
BRIDGE_FLAGS = {
    "R2K_TEAMCAPTAIN": os.environ.get("R2K_TEAMCAPTAIN", "0"),
    "R2K_KICK_BEHIND_GATE": os.environ.get("R2K_KICK_BEHIND_GATE", "1"),
    "R2K_PASS_RESOLVE": os.environ.get("R2K_PASS_RESOLVE", "0"),
    "R2K_WING_STAGE": os.environ.get("R2K_WING_STAGE", "0"),
}


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
class S(Enum):
    IDLE = "idle"
    LAUNCHING = "launching"
    RUNNING = "running"
    TEARING_DOWN = "tearing_down"


# ---------------------------------------------------------------------------
# Process Manager
# ---------------------------------------------------------------------------
@dataclass
class ManagedProc:
    name: str
    proc: asyncio.subprocess.Process | None = None
    started_at: float = 0.0
    log_path: str | None = None
    log_file: object | None = None


class ProcessManager:
    """Tracks child processes by PID. No pkill, no pattern matching.

    Each child's stdout/stderr is piped to /tmp/supervisor_<name>.log so
    crash diagnostics are visible. stdout=DEVNULL is a mistake from the
    first-shot GUI — silent crashes were invisible."""

    def __init__(self):
        self.children: dict[str, ManagedProc] = {}

    async def start(self, name, cmd, env=None):
        """Start a child process. Returns the ManagedProc.

        env: dict of override vars. The child ALWAYS inherits the parent
        environment (os.environ.copy()) — an empty env={} would strip
        PATH, HOME, ROS_DOMAIN_ID, and break `source` in the command string.
        Override vars are merged on top of the inherited env."""
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        log_path = f"/tmp/supervisor_{name}.log"
        log_file = open(log_path, 'w')
        # executable="/bin/bash": create_subprocess_shell defaults to /bin/sh
        # (dash on Ubuntu) which does not understand `source` in SOURCE_CMD.
        # start_new_session: the child becomes a process-group leader so stop()
        # can kill the whole tree — `ros2 launch`/`ros2 run` spawn grandchildren
        # (gzserver, node executables) that would otherwise survive as orphans.
        proc = await asyncio.create_subprocess_shell(
            cmd,
            executable="/bin/bash",
            env=full_env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True)
        mp = ManagedProc(name=name, proc=proc, started_at=time.time())
        mp.log_path = log_path
        mp.log_file = log_file
        self.children[name] = mp
        return mp

    async def stop(self, name, timeout=3.0):
        """Stop a child by process GROUP. SIGTERM → wait → SIGKILL.

        The child was started with start_new_session=True, so killpg reaches
        the whole tree (ros2 launch → gzserver, ros2 run → node executable)."""
        mp = self.children.get(name)
        if not mp or not mp.proc:
            return True
        try:
            pgid = os.getpgid(mp.proc.pid)
        except ProcessLookupError:
            pgid = None
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(mp.proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass  # leader stuck — SIGKILL below handles it
        # SIGKILL the remaining group unconditionally: grandchildren like
        # gzserver trap/ignore SIGTERM and would otherwise outlive the leader.
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            mp.proc.kill()  # belt & suspenders for the direct child
            await mp.proc.wait()
        except ProcessLookupError:
            pass
        if hasattr(mp, 'log_file') and mp.log_file:
            mp.log_file.close()
        del self.children[name]
        return True

    async def stop_all(self):
        """Stop all children in parallel."""
        names = list(self.children.keys())
        await asyncio.gather(*[self.stop(n) for n in names], return_exceptions=True)

    def is_alive(self, name):
        mp = self.children.get(name)
        return bool(mp and mp.proc and mp.proc.returncode is None)


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------
class Supervisor:
    def __init__(self):
        self.pm = ProcessManager()
        self.state = S.IDLE
        self.lock = asyncio.Lock()
        self.current_model = None
        self.ws_clients = set()

    # -- WS helpers ---------------------------------------------------------
    async def _broadcast_ws(self, msg: dict):
        if not self.ws_clients:
            return
        data = json.dumps(msg)
        results = await asyncio.gather(
            *[ws.send_str(data) for ws in list(self.ws_clients)],
            return_exceptions=True)
        for ws, res in zip(list(self.ws_clients), results):
            if isinstance(res, Exception):
                self.ws_clients.discard(ws)

    async def transition(self, new_state):
        async with self.lock:
            self.state = new_state
        await self._broadcast_ws({"type": "state", "data": new_state.value})

    # -- Launch -------------------------------------------------------------
    def _scenario_exists(self, scenario):
        for candidate in [f"{SCENARIO_DIR}/{scenario}.json",
                          f"{SCENARIO_DIR}/{scenario}/scenario.json"]:
            if os.path.isfile(candidate):
                return candidate
        return None

    async def _teardown_existing(self):
        """Stop our own children by PID, then pkill foreign leftovers
        (e.g. processes from a launch_gzweb.sh run we cannot track)."""
        await self.pm.stop_all()
        for pattern in FOREIGN_PATTERNS:
            proc = await asyncio.create_subprocess_exec(
                "pkill", "-9", "-f", pattern,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()
        await asyncio.sleep(TEARDOWN_SETTLE_S)

    async def _clean_state_files(self):
        """Remove stale shared_state + ai_tactics transient files.

        Without this a failed setup_r2k.py leaves the previous match's
        active_scenario.json behind → gzserver spawns the OLD match's bots."""
        for fn in CLEANUP_FILES:
            try:
                os.remove(os.path.join(SHARED_STATE_DIR, fn))
            except FileNotFoundError:
                pass
        at_dir = os.path.join(os.path.dirname(SHARED_STATE_DIR), "ai_tactics")
        for fn in ["active_scenario.json", "active_relay.json", "system_prompt.txt"]:
            try:
                os.remove(os.path.join(at_dir, fn))
            except FileNotFoundError:
                pass
        os.makedirs(os.path.join(SHARED_STATE_DIR, "logs"), exist_ok=True)

    async def _run_fg(self, cmd, timeout=30):
        """Run a command to completion. subprocess.run would block the event
        loop — delegate to a thread."""
        def _run():
            try:
                r = subprocess.run(["bash", "-c", cmd], timeout=timeout,
                                   capture_output=True, text=True)
                return r.returncode == 0, (r.stdout + r.stderr)
            except subprocess.TimeoutExpired:
                return False, "timeout"
            except Exception as e:
                return False, str(e)
        return await asyncio.to_thread(_run)

    async def _run_setup(self, scenario, strategy, model, explain, demo):
        explain_flag = "--explain" if explain else "--no-explain"
        demo_flag = "--demo" if demo else ""
        ok, out = await self._run_fg(
            f"cd /workspace && python3 setup_r2k.py --scenario {scenario} "
            f"--strategy {strategy} --model {model} --relay {RELAY} "
            f"{explain_flag} {demo_flag}".strip(),
            timeout=SETUP_TIMEOUT_S)
        if not ok:
            raise RuntimeError(f"setup_r2k.py failed: {out.strip()[-400:]}")

    async def _start_gzserver(self):
        await self.pm.start(
            "gzserver",
            f"{SOURCE_CMD} && ros2 launch r2k_scenario_spawner "
            f"soccer_match.launch.py headless:=true")
        # Poll Gazebo's API port instead of a hardcoded sleep — readiness
        # varies with world size and disk cache.
        deadline = time.time() + GZSERVER_READY_TIMEOUT_S
        while time.time() < deadline:
            if self.pm.is_alive("gzserver") is False:
                raise RuntimeError("gzserver died during startup "
                                   f"(log: /tmp/supervisor_gzserver.log)")
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", GZSERVER_PROBE_PORT),
                    timeout=1.0)
                writer.close()
                await writer.wait_closed()
                return
            except (OSError, asyncio.TimeoutError):
                await asyncio.sleep(0.5)
        if not self.pm.is_alive("gzserver"):
            raise RuntimeError("gzserver not ready in "
                               f"{GZSERVER_READY_TIMEOUT_S}s and process dead")
        # Alive but port never opened — proceed anyway (world may still load).

    async def _spawn_bots(self):
        ok, out = await self._run_fg(
            f"{SOURCE_CMD} && python3 ai_tactics/json_spawner.py",
            timeout=SPAWN_TIMEOUT_S)
        if not ok:
            raise RuntimeError(f"json_spawner failed: {out.strip()[-400:]}")

    async def _start_gzbridge(self):
        await self.pm.start("gzbridge", "cd /opt/gzweb/gzbridge && ./server.js 8080")
        await asyncio.sleep(1)

    async def _start_ros2_nodes(self, scenario, strategy, model, explain, demo):
        run_id = f"{scenario}_{strategy}_{time.strftime('%Y%m%d_%H%M%S')}"
        await self.pm.start("tracker", f"{SOURCE_CMD} && ros2 run r2k_world_model tracker")
        if not demo:  # demo mode skips referee/score/reward (like launch_gzweb.sh)
            await self.pm.start("referee", f"{SOURCE_CMD} && python3 referee_node.py")
            await self.pm.start("score", f"{SOURCE_CMD} && python3 score_node.py")
            await self.pm.start("reward", f"{SOURCE_CMD} && python3 reward_node.py")
            await self.pm.start("rule_evaluator_red",
                                f"{SOURCE_CMD} && python3 rule_evaluator_red.py")
        await self.pm.start(
            "state_aggregator", f"{SOURCE_CMD} && python3 state_aggregator.py",
            env={"R2K_RUN_ID": run_id})
        await self.pm.start(
            "bridge",
            f"{SOURCE_CMD} && python3 ai_tactics/ollama_sandbox_bridge.py",
            env={**BRIDGE_FLAGS, "R2K_RUN_ID": run_id})
        await self.pm.start(
            "evaluator",
            f"{SOURCE_CMD} && PYTHONUNBUFFERED=1 python3 -u ai_tactics/r2k_evaluator.py",
            env={"R2K_OLLAMA_MODEL": model,
                 "R2K_OLLAMA_URL": OLLAMA_GENERATE_URL,
                 "R2K_RUN_ID": run_id,
                 "R2K_EXPLAIN": "1" if explain else "0"})
        return run_id

    async def _auto_stop(self, seconds):
        await asyncio.sleep(seconds)
        if self.state == S.RUNNING:
            await self.done()

    async def handle_launch(self, request):
        scenario = request.query.get("scenario", "2vs2_default")
        strategy = request.query.get("strategy", "strat_aggro")
        model = request.query.get("model", "qwen2.5:3b")
        explain = request.query.get("explain", "0") == "1"
        demo = request.query.get("demo", "0") == "1"
        duration = request.query.get("duration", "0")

        # Validate scenario BEFORE touching any state — otherwise a bad name
        # leaves the previous match's active_scenario.json alive (old bots).
        if not self._scenario_exists(scenario):
            return web.json_response(
                {"status": "error",
                 "detail": f"Scenario '{scenario}' not found"},
                status=400)
        if self.state != S.IDLE:
            return web.json_response(
                {"status": "error", "detail": "Match running — press DONE first"},
                status=409)

        await self.transition(S.LAUNCHING)
        try:
            await self._teardown_existing()
            await self._clean_state_files()
            await self._run_setup(scenario, strategy, model, explain, demo)
            await self._start_gzserver()
            await self._spawn_bots()
            await self._start_gzbridge()
            run_id = await self._start_ros2_nodes(
                scenario, strategy, model, explain, demo)
            self.current_model = model
            await self.transition(S.RUNNING)
            if duration and duration != "0":
                asyncio.create_task(self._auto_stop(int(duration)))
            return web.json_response({"status": "launched", "run_id": run_id,
                                      "scenario": scenario, "model": model})
        except Exception as e:
            await self.pm.stop_all()
            await self.transition(S.IDLE)
            return web.json_response({"status": "error", "detail": str(e)},
                                     status=500)

    # -- Done ---------------------------------------------------------------
    async def handle_done(self, request):
        result = await self.done()
        return web.json_response(result)

    async def done(self):
        if self.state != S.RUNNING:
            return {"status": "error", "detail": "No match running"}
        await self.transition(S.TEARING_DOWN)
        await self.pm.stop_all()
        await self._unload_ollama()
        self.current_model = None
        await self.transition(S.IDLE)
        return {"status": "match stopped"}

    async def _unload_ollama(self):
        """Unload ALL loaded Ollama models from VRAM (keep_alive=0).

        Uses asyncio.create_subprocess_exec (non-blocking) — subprocess.run
        would freeze the event loop for 8s per model."""
        models = []
        for host in OLLAMA_URLS:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "bash", "-c", f"curl -s -m {OLLAMA_PS_TIMEOUT_S} {host}/api/ps",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL)
                stdout, _ = await asyncio.wait_for(proc.communicate(),
                                                   timeout=OLLAMA_PS_TIMEOUT_S + 2)
                models = [m["name"] for m in json.loads(stdout.decode()).get("models", [])]
                if models:
                    break
            except Exception:
                continue
        if self.current_model and self.current_model not in models:
            models.append(self.current_model)
        for m in models:
            try:
                unload = await asyncio.create_subprocess_exec(
                    "bash", "-c",
                    f"curl -s -m 5 {OLLAMA_GENERATE_URL} "
                    f"-d '{{\"model\":\"{m}\",\"keep_alive\":0}}'",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
                await asyncio.wait_for(unload.wait(), timeout=OLLAMA_UNLOAD_TIMEOUT_S)
            except Exception:
                pass

    # -- Health -------------------------------------------------------------
    async def health(self):
        """Run all health checks concurrently. Each is capped at 2s."""
        async def _safe(check_fn, *args):
            try:
                return await asyncio.wait_for(check_fn(*args),
                                              timeout=HEALTH_CHECK_TIMEOUT_S)
            except (asyncio.TimeoutError, Exception):
                return {"status": "timeout"}
        results = await asyncio.gather(
            _safe(self._check_ollama),
            _safe(self._check_docker),
            _safe(self._check_gpu),
            return_exceptions=True,
        )
        return {
            "ollama": results[0],
            "docker": results[1],
            "gzserver": self.pm.is_alive("gzserver"),
            "ros2_nodes": {n: self.pm.is_alive(n) for n in ROS2_NODE_NAMES},
            "gpu": results[2],
            "file_bus": await self._check_file_bus(),
            "state": self.state.value,
        }

    async def _check_ollama(self):
        for host in OLLAMA_URLS:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "bash", "-c",
                    f"curl -s -m {OLLAMA_PS_TIMEOUT_S} {host}/api/ps",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL)
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=OLLAMA_PS_TIMEOUT_S + 1)
                models = [m["name"] for m in
                          json.loads(stdout.decode()).get("models", [])]
                return {"up": True, "models": models}
            except Exception:
                continue
        return {"up": False, "models": []}

    async def _check_docker(self):
        # We ARE inside the container — health = workspace mount present.
        return {"up": os.path.isdir("/workspace")}

    async def _check_gpu(self):
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            stdout, _ = await asyncio.wait_for(proc.communicate(),
                                               timeout=HEALTH_CHECK_TIMEOUT_S)
            parts = [p.strip() for p in stdout.decode().splitlines()[0].split(",")]
            return {"available": True, "temp": int(parts[0]),
                    "util": int(parts[1]), "mem_mb": int(parts[2])}
        except FileNotFoundError:
            # POC limitation: container image has no nvidia-smi (no compose
            # changes allowed). Host-side VRAM checks remain manual.
            return {"available": False,
                    "detail": "nvidia-smi not available in container"}

    async def _check_file_bus(self):
        try:
            mtime = os.path.getmtime(os.path.join(SHARED_STATE_DIR,
                                                  "Worldstate.json"))
            age = time.time() - mtime
            return {"fresh": age < FILE_BUS_STALE_S, "age_s": round(age, 1)}
        except FileNotFoundError:
            return {"fresh": False, "age_s": None}

    async def health_monitor_loop(self):
        """Push health updates to all WS clients every 2s."""
        last_health = None
        while True:
            h = await self.health()
            if h != last_health:
                last_health = h
                await self._broadcast_ws({"type": "health", "data": h})
            await asyncio.sleep(HEALTH_INTERVAL_S)

    # -- File-bus watcher ---------------------------------------------------
    async def _read_json(self, path):
        try:
            async with aiofiles.open(path, 'r') as f:
                return json.loads(await f.read())
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    async def _read_text(self, path):
        try:
            async with aiofiles.open(path, 'r') as f:
                return await f.read()
        except FileNotFoundError:
            return None

    async def file_watcher_loop(self):
        """Single poller broadcasting shared_state changes to ALL WS clients
        (ws_backend.py ran one poller per client)."""
        last_mod = {f: 0.0 for f in FILES_TO_MONITOR}
        while True:
            for fn in FILES_TO_MONITOR:
                path = os.path.join(SHARED_STATE_DIR, fn)
                try:
                    mtime = os.path.getmtime(path)
                    if mtime > last_mod[fn]:
                        last_mod[fn] = mtime
                        d = await self._read_json(path)
                        if d is not None:
                            await self._broadcast_ws(
                                {"type": "state_update", "file": fn, "data": d})
                except FileNotFoundError:
                    pass
            await asyncio.sleep(FILE_POLL_INTERVAL_S)

    async def handle_ws(self, request):
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self.ws_clients.add(ws)
        # initial snapshot: state + current files
        await ws.send_str(json.dumps({"type": "state", "data": self.state.value}))
        for fn in FILES_TO_MONITOR:
            d = await self._read_json(os.path.join(SHARED_STATE_DIR, fn))
            if d is not None:
                await ws.send_str(json.dumps(
                    {"type": "state_update", "file": fn, "data": d}))
        try:
            async for msg in ws:  # keep open; data flows via broadcast
                pass
        finally:
            self.ws_clients.discard(ws)
        return ws

    # -- Catalog ------------------------------------------------------------
    async def _get_ollama_models(self):
        import socket
        for host in ["127.0.0.1", "172.17.0.1"]:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, 11434), timeout=1.5)
                writer.close()
                await writer.wait_closed()
                ollama_host = host
                break
            except (OSError, asyncio.TimeoutError):
                continue
        else:
            return []
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", f"curl -s -m 3 http://{ollama_host}:11434/api/tags",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            return [m["name"] for m in json.loads(stdout.decode()).get("models", [])]
        except Exception:
            return []

    async def handle_catalog(self, request):
        scenarios = []
        modes_set = set()
        for path in sorted(glob.glob(os.path.join(SCENARIO_DIR, "*.json"))):
            d = await self._read_json(path)
            if not d:
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            mode = d.get("mode") or d.get("scene_type") or "?"
            label = d.get("tactical_situation") or d.get("label") or name
            n_entities = len(d.get("entities", {}))
            scenarios.append({"name": name, "mode": mode, "label": label,
                              "bots": n_entities})
            modes_set.add(mode)
        # For each mode, list available strategies from fragment files
        modes = {}
        for mode in sorted(modes_set):
            strategies = []
            if os.path.isfile(os.path.join(STRATEGY_FRAG_DIR, f"rules_{mode}.txt")):
                strategies.append(f"strat_{mode}")
            if "strat_aggro" not in strategies:
                strategies.append("strat_aggro")
            modes[mode] = {"strategies": strategies}
        models = await self._get_ollama_models()
        return web.json_response(
            {"scenarios": scenarios, "modes": modes, "models": models})

    # -- Info endpoints -----------------------------------------------------
    async def handle_state(self, request):
        snap = {}
        for fn in FILES_TO_MONITOR:
            d = await self._read_json(os.path.join(SHARED_STATE_DIR, fn))
            if d is not None:
                snap[fn] = d
        return web.json_response(snap)

    async def handle_runs(self, request):
        """Recent run ids from trace logs (llm_trace_<run_id>.jsonl), newest first."""
        runs = []
        if os.path.isdir(LOG_DIR):
            for path in glob.glob(os.path.join(LOG_DIR, "llm_trace_*.jsonl")):
                run_id = os.path.basename(path)[len("llm_trace_"):-len(".jsonl")]
                runs.append({"run_id": run_id, "mtime": os.path.getmtime(path)})
        runs.sort(key=lambda r: -r["mtime"])
        return web.json_response({"runs": runs[:RUNS_MAX]})

    async def handle_git_commits(self, request):
        """Last commits. The container mounts core/src only — the .git dir is
        NOT available here. Fall back to a host-provided file if it exists."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", "/workspace", "log", "--oneline", "-5",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            if proc.returncode == 0:
                return web.json_response(
                    {"commits": stdout.decode().splitlines()})
        except Exception:
            pass
        fb = os.path.join(SHARED_STATE_DIR, "git_commits.txt")
        if os.path.isfile(fb):
            async with aiofiles.open(fb) as f:
                return web.json_response(
                    {"commits": (await f.read()).splitlines()})
        return web.json_response(
            {"commits": [],
             "detail": "repo root not mounted in container (POC limitation)"})

    async def handle_session_digest(self, request):
        """Tail of SESSION_CHANGELOG.md — also not mounted (see /git/commits)."""
        for path in [os.path.join(REPO_DOCS_DIR, "SESSION_CHANGELOG.md"),
                     os.path.join(SHARED_STATE_DIR, "session_digest.txt")]:
            if os.path.isfile(path):
                async with aiofiles.open(path) as f:
                    content = await f.read()
                lines = content.splitlines()
                return web.json_response({"digest": "\n".join(
                    lines[-DIGEST_TAIL_LINES:])})
        return web.json_response(
            {"digest": "",
             "detail": "docs/ not mounted in container (POC limitation)"})

    # -- Assistant panel (mode B copilot) -----------------------------------
    async def handle_assistant_ask(self, request):
        """Answer a question via Ollama with repo knowledge + live match
        context. Blocking LLM call runs as async subprocess (curl), so the
        supervisor event loop stays responsive."""
        q = request.query.get("q", "").strip()
        if not q:
            return web.json_response(
                {"status": "error", "detail": "empty question"}, status=400)
        model = request.query.get("model", ASSISTANT_DEFAULT_MODEL)

        parts = []
        for fn in ASSISTANT_CTX_FILES:
            text = await self._read_text(os.path.join(ASSISTANT_CTX_DIR, fn))
            if text:
                parts.append(text)
        world = await self._read_json(os.path.join(SHARED_STATE_DIR, "Worldstate.json"))
        strat = await self._read_json(os.path.join(SHARED_STATE_DIR, "current_strategy.json"))
        if world or strat:
            snapshot = json.dumps(
                {"worldstate": world, "strategy": strat}, ensure_ascii=False)
            parts.append("CURRENT MATCH STATE (live JSON):\n"
                         + snapshot[:ASSISTANT_SNAPSHOT_MAX_CHARS])
        system = "\n\n---\n".join(parts)

        payload = json.dumps({
            "model": model,
            "prompt": q,
            "system": system,
            "stream": False,
            "options": {"temperature": ASSISTANT_TEMPERATURE,
                        "num_predict": ASSISTANT_NUM_PREDICT},
        })
        started = time.time()
        answer, detail = None, ""
        for host in OLLAMA_URLS:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-m", str(ASSISTANT_TIMEOUT_S),
                    f"{host}/api/generate", "-d", payload,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL)
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=ASSISTANT_TIMEOUT_S + 2)
                data = json.loads(stdout.decode())
                answer = data.get("response", "").strip()
                break
            except Exception as exc:
                detail = str(exc)
                continue
        elapsed_ms = int((time.time() - started) * 1000)
        if answer is None:
            return web.json_response(
                {"status": "error", "detail": f"Ollama unreachable: {detail}"},
                status=502)
        return web.json_response(
            {"answer": answer, "model": model, "elapsed_ms": elapsed_ms})

    # -- Static files -------------------------------------------------------
    async def handle_health(self, request):
        return web.json_response(await self.health())

    async def handle_static(self, request):
        rel = request.match_info.get('path', '') or 'index.html'
        rel = rel.replace('..', '').lstrip('/')
        file_path = os.path.join(GUI_DIR, rel)
        if not os.path.isfile(file_path):
            return web.Response(status=404, text="Not found: " + rel)
        mime, _ = mimetypes.guess_type(file_path)
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
        return web.Response(
            text=content,
            content_type=mime or 'text/html',
            headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
async def main():
    sup = Supervisor()
    app = web.Application()
    # API routes FIRST — the catch-all static handler MUST be registered last
    # or it would shadow these endpoints.
    app.router.add_get('/catalog', sup.handle_catalog)
    app.router.add_get('/state', sup.handle_state)
    app.router.add_get('/health', sup.handle_health)
    app.router.add_get('/launch', sup.handle_launch)
    app.router.add_get('/done', sup.handle_done)
    app.router.add_get('/runs', sup.handle_runs)
    app.router.add_get('/git/commits', sup.handle_git_commits)
    app.router.add_get('/session/digest', sup.handle_session_digest)
    app.router.add_get('/assistant/ask', sup.handle_assistant_ask)
    app.router.add_get('/reboot/check', sup.handle_health)
    app.router.add_get('/ws', sup.handle_ws)
    # Static file handler — MUST be last (catch-all for index.html, style.css, app.js)
    app.router.add_get('/', sup.handle_static)
    app.router.add_get('/{path:.*}', sup.handle_static)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Supervisor on http://0.0.0.0:{PORT}")
    asyncio.create_task(sup.health_monitor_loop())
    asyncio.create_task(sup.file_watcher_loop())
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
