#!/usr/bin/env python3
# ws_backend.py -- WebSocket + HTTP server for the ROS2K GUI.
# Launched by launch_gzweb.sh inside the r2k_gzweb container.
#
# Serves on http://0.0.0.0:8765:
#   GET  /                  -> static files (gui/index.html + assets)
#   GET  /catalog           -> JSON {scenarios, models, strategies} from disk
#   GET  /state             -> JSON snapshot of all shared_state files
#   WS   /ws                -> push Worldstate.json / current_strategy.json / waypoints.json
#
# One port for everything (no separate http.server needed).

import asyncio
import json
import os
import glob
import urllib.parse
import mimetypes
from aiohttp import web
import aiofiles

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SHARED_STATE_DIR = os.environ.get("R2K_SHARED_STATE", "/workspace/shared_state")
SCENARIO_DIR = "/workspace/scenario"
STRATEGY_FRAG_DIR = "/workspace/strategy/fragments"
GUI_DIR = "/workspace/tools/gui"
FILES_TO_MONITOR = ["Worldstate.json", "current_strategy.json", "waypoints.json"]
PORT = 8765

# ---------------------------------------------------------------------------
# Catalog (scenarios / models / strategies from disk)
# ---------------------------------------------------------------------------

async def _read_json(path):
    try:
        async with aiofiles.open(path, 'r') as f:
            return json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


async def handle_catalog(request):
    """List scenarios, strategies, and available Ollama models from disk."""
    # Scenarios: scan scenario/*.json, extract mode + label/situation
    scenarios = []
    for path in sorted(glob.glob(os.path.join(SCENARIO_DIR, "*.json"))):
        d = await _read_json(path)
        if not d:
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        mode = d.get("mode") or d.get("scene_type") or "?"
        label = d.get("tactical_situation") or d.get("label") or name
        n_entities = len(d.get("entities", {}))
        scenarios.append({"name": name, "mode": mode, "label": label,
                          "bots": n_entities})
    # Strategies: the evaluator uses strat_<name> artifacts, but the
    # selectable "strategy" is really the scenario mode (which picks
    # rules_<mode>.txt + samples_<mode>.txt). We expose the mode list.
    modes = sorted(set(s["mode"] for s in scenarios if s["mode"] != "?"))
    # Models: query Ollama's /api/tags (host = 172.17.0.1 from container, or
    # 127.0.0.1 via network_mode host). Fall back to a static list.
    models = []
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
        ollama_host = None
    if ollama_host:
        try:
            import urllib.request
            with urllib.request.urlopen(
                f"http://{ollama_host}:11434/api/tags", timeout=2) as r:
                tags = json.loads(r.read())
            models = [m["name"] for m in tags.get("models", [])]
        except Exception:
            models = []
    return web.json_response({
        "scenarios": scenarios,
        "modes": modes,
        "models": models,
    })


# ---------------------------------------------------------------------------
# State snapshot
# ---------------------------------------------------------------------------

async def handle_state(request):
    snap = {}
    for fn in FILES_TO_MONITOR:
        d = await _read_json(os.path.join(SHARED_STATE_DIR, fn))
        if d is not None:
            snap[fn] = d
    return web.json_response(snap)


# ---------------------------------------------------------------------------
# Static file serving (gui/index.html + assets)
# ---------------------------------------------------------------------------

async def handle_static(request):
    rel = request.match_info.get('path', '')
    # default to index.html
    if not rel or rel == '/':
        rel = 'index.html'
    # prevent path traversal
    rel = rel.replace('..', '').lstrip('/')
    file_path = os.path.join(GUI_DIR, rel)
    if not os.path.isfile(file_path):
        return web.Response(status=404, text="Not found: " + rel)
    mime, _ = mimetypes.guess_type(file_path)
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    # No-cache headers so the browser always gets fresh HTML/JS
    headers = {'Cache-Control': 'no-cache, no-store, must-revalidate'}
    return web.Response(text=content, content_type=mime or 'text/html', headers=headers)


# ---------------------------------------------------------------------------
# WebSocket: push monitored files on change
# ---------------------------------------------------------------------------

ws_clients = set()

async def _push_current(ws):
    for fn in FILES_TO_MONITOR:
        d = await _read_json(os.path.join(SHARED_STATE_DIR, fn))
        if d is not None:
            await ws.send_str(json.dumps({"type": "state_update", "file": fn, "data": d}))


async def handle_ws(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    ws_clients.add(ws)
    await _push_current(ws)
    last_mod = {f: 0 for f in FILES_TO_MONITOR}
    while not ws.closed:
        for fn in FILES_TO_MONITOR:
            path = os.path.join(SHARED_STATE_DIR, fn)
            try:
                mtime = os.path.getmtime(path)
                if mtime > last_mod[fn]:
                    last_mod[fn] = mtime
                    d = await _read_json(path)
                    if d is not None:
                        await ws.send_str(json.dumps(
                            {"type": "state_update", "file": fn, "data": d}))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        await asyncio.sleep(0.1)
    ws_clients.discard(ws)
    return ws


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

async def _unload_ollama_model(model_name, ollama_url):
    """Unload ALL resident Ollama models from VRAM (keep_alive=0).

    Queries /api/ps to find every loaded model, then sends keep_alive=0 for
    each. This handles the case where the demo compiler (7b) loaded a different
    model than the executor (3b). Without this, models stay resident for 30m
    (the keep_alive set by the evaluator/compiler), keeping GPU elevated."""
    import subprocess
    # With network_mode: host, 127.0.0.1 is the correct address (not 172.17.0.1)
    for host in ["127.0.0.1", "172.17.0.1"]:
        try:
            r = subprocess.run(
                ["bash", "-c", f'curl -s -m 3 http://{host}:11434/api/ps'],
                timeout=5, capture_output=True, text=True)
            data = json.loads(r.stdout) if r.stdout else {}
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            if models:
                break
        except Exception:
            models = []
    # Fallback: unload the tracked model if /api/ps didn't respond
    if not models and model_name:
        models = [model_name]
    for m in models:
        try:
            subprocess.run(
                ["bash", "-c",
                 f'curl -s -m 5 http://127.0.0.1:11434/api/generate '
                 f'-d \'{{"model":"{m}","keep_alive":0}}\' > /dev/null 2>&1'],
                timeout=8, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


async def handle_done(request):
    """Stop the running match and free all resources (VRAM, GPU, processes).

    Kills AI/ROS nodes + gzserver + gzclient + GZWeb gzbridge (server.js).
    Unloads the Ollama model(s) from VRAM (keep_alive=0) so GPU usage drops to
    idle. The container and ws_backend stay alive; /launch restarts everything
    fresh."""
    import subprocess
    try:
        global _launch_running, _current_model
        model_to_unload = _current_model
        _launch_running = False
        _current_model = None
        # Kill match nodes
        for proc in ["r2k_evaluator", "ollama_sandbox_bridge", "referee_node",
                     "score_node", "reward_node", "rule_evaluator_red",
                     "state_aggregator", "r2k_world_model", "json_spawner"]:
            subprocess.run(["pkill", "-f", proc], timeout=3,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Kill gzserver + gzclient with SIGKILL (SIGTERM may not be enough)
        subprocess.run(["pkill", "-9", "-f", "gzserver"], timeout=5,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "-f", "gzclient"], timeout=3,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Kill GZWeb gzbridge (server.js) — it polls gzserver and keeps GPU busy
        subprocess.run(["pkill", "-9", "-f", "server.js 8080"], timeout=3,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Unload the Ollama model(s) from VRAM (frees GPU memory)
        await _unload_ollama_model(model_to_unload, None)
        return web.json_response({"status": "match stopped"})
    except Exception as e:
        return web.json_response({"status": "error", "detail": str(e)}, status=500)


# ---------------------------------------------------------------------------
# /launch — start a match from the GUI (no terminal needed)
# ---------------------------------------------------------------------------

_launch_running = False
_current_model = None  # track for VRAM unload on /done

SOURCE_CMD = "cd /workspace && source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash"

async def _run_bg(cmd):
    """Run a command in the background (fully detached via setsid)."""
    import subprocess
    subprocess.Popen(
        ["setsid", "bash", "-c", cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )

async def _run_fg(cmd, timeout=30):
    """Run a command and wait for it."""
    import subprocess
    try:
        r = subprocess.run(["bash", "-c", cmd], timeout=timeout,
                           capture_output=True, text=True)
        return r.returncode == 0, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


async def handle_launch(request):
    """Start a real AI match inside the container. Query params:
    scenario, model, explain (0/1), duration (seconds, 0=∞).
    Tears down any running match first, then starts all nodes."""
    global _launch_running, _current_model
    import subprocess, time, urllib.parse as up

    scenario = request.query.get("scenario", "2vs2_default")
    strategy = request.query.get("strategy", "strat_aggro")
    model = request.query.get("model", "qwen2.5:3b")
    explain = request.query.get("explain", "0")
    duration = request.query.get("duration", "0")

    # Validate scenario exists on disk BEFORE touching any state.
    # Without this, an invalid scenario name (e.g. "n_vs_m") makes setup_r2k.py
    # exit(1), but the stale active_scenario.json survives → gzserver spawns the
    # previous match's bots (typically 2vs2_default).
    scenario_path = None
    for candidate in [f"{SCENARIO_DIR}/{scenario}.json",
                      f"{SCENARIO_DIR}/{scenario}/scenario.json"]:
        if os.path.isfile(candidate):
            scenario_path = candidate
            break
    if not scenario_path:
        return web.json_response(
            {"status": "error",
             "detail": f"Scenario '{scenario}' not found. "
                       f"Check /catalog for available scenarios."}, status=400)

    if _launch_running:
        # Force reset — a previous launch may have died without /done
        _launch_running = False

    _launch_running = True
    _current_model = model

    # 1. Teardown any existing processes (SIGKILL — SIGTERM may not kill gzserver)
    for proc in ["gzserver", "gzclient", "r2k_evaluator", "ollama_sandbox_bridge",
                 "referee_node", "score_node", "reward_node", "rule_evaluator_red",
                 "state_aggregator", "r2k_world_model", "server.js 8080"]:
        subprocess.run(["pkill", "-9", "-f", proc], timeout=3,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2)

    # 2. Clean shared state (including stale active_scenario.json — without this
    #    a failed setup_r2k.py leaves the previous match's scenario active)
    for fn in ["Worldstate.json", "current_strategy.json", "waypoints.json",
               "task_input.json", "active_scenario.json"]:
        try: os.remove(os.path.join(SHARED_STATE_DIR, fn))
        except FileNotFoundError: pass
    # Also remove the copy in ai_tactics/ (setup_r2k.py writes there)
    for fn in ["active_scenario.json", "active_relay.json", "system_prompt.txt"]:
        try: os.remove(os.path.join(os.path.dirname(SHARED_STATE_DIR), "ai_tactics", fn))
        except FileNotFoundError: pass
    os.makedirs(os.path.join(SHARED_STATE_DIR, "logs"), exist_ok=True)

    # 3. Run setup_r2k.py (compile prompt + relay)
    explain_flag = "--explain" if explain == "1" else "--no-explain"
    relay = "only_sim_bots"
    ok, out = await _run_fg(
        f"cd /workspace && python3 setup_r2k.py --scenario {scenario} "
        f"--strategy {strategy} --model {model} --relay {relay} {explain_flag}",
        timeout=15)
    if not ok:
        _launch_running = False
        return web.json_response({"status": "error", "detail": "setup failed: " + out}, status=500)

    # 4. Start gzserver (headless) — needs extra time to load the world
    await _run_bg(f'{SOURCE_CMD} && ros2 launch r2k_scenario_spawner soccer_match.launch.py headless:=true')
    await asyncio.sleep(6)

    # 5. Spawn bots (needs gzserver fully loaded)
    ok, out = await _run_fg(f"{SOURCE_CMD} && python3 ai_tactics/json_spawner.py", timeout=20)

    # 6. Start GZWeb gzbridge
    await _run_bg('cd /opt/gzweb/gzbridge && ./server.js 8080')
    await asyncio.sleep(1)

    # 7. Start realtime nodes
    await _run_bg(f"{SOURCE_CMD} && ros2 run r2k_world_model tracker")
    await _run_bg(f"{SOURCE_CMD} && python3 referee_node.py")
    await _run_bg(f"{SOURCE_CMD} && python3 score_node.py")
    await _run_bg(f"{SOURCE_CMD} && python3 reward_node.py")
    await _run_bg(f"{SOURCE_CMD} && python3 rule_evaluator_red.py")
    run_id = f"{scenario}_{strategy.replace('strat_','')}_{int(time.time())}"
    await _run_bg(f'{SOURCE_CMD} && R2K_RUN_ID={run_id} python3 state_aggregator.py')

    # 8. Start bridge + evaluator
    await _run_bg(f'{SOURCE_CMD} && R2K_RUN_ID={run_id} python3 ai_tactics/ollama_sandbox_bridge.py')
    ollama_url = "http://172.17.0.1:11434/api/generate"
    await _run_bg(
        f'{SOURCE_CMD} && PYTHONUNBUFFERED=1 R2K_OLLAMA_MODEL={model} '
        f'R2K_OLLAMA_URL={ollama_url} R2K_RUN_ID={run_id} R2K_EXPLAIN={explain} '
        f'python3 -u ai_tactics/r2k_evaluator.py')

    # 9. Auto-terminate if duration set
    if duration and duration != "0":
        async def _auto_stop():
            await asyncio.sleep(int(duration))
            global _launch_running, _current_model
            model_to_unload = _current_model
            _launch_running = False
            _current_model = None
            for proc in ["gzserver", "gzclient", "server.js 8080",
                         "r2k_evaluator", "ollama_sandbox_bridge",
                         "referee_node", "score_node", "reward_node",
                         "rule_evaluator_red", "state_aggregator", "r2k_world_model"]:
                subprocess.run(["pkill", "-f", proc], timeout=3,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await _unload_ollama_model(model_to_unload, None)
        asyncio.create_task(_auto_stop())

    return web.json_response({
        "status": "launched",
        "run_id": run_id,
        "scenario": scenario,
        "model": model,
        "explain": explain,
        "duration": duration
    })


async def main():
    app = web.Application()
    app.router.add_get('/catalog', handle_catalog)
    app.router.add_get('/state', handle_state)
    app.router.add_get('/done', handle_done)
    app.router.add_get('/launch', handle_launch)
    app.router.add_get('/ws', handle_ws)
    app.router.add_get('/', handle_static)
    app.router.add_get('/{path:.*}', handle_static)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"GUI backend on http://0.0.0.0:{PORT}  (ws://0.0.0.0:{PORT}/ws)")
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())