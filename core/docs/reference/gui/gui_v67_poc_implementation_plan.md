# GUI v6.7 POC — Implementation Plan

**Date:** 2026-08-27
**Status:** Ready for implementation
**Prerequisite:** `docs/gui_v67_poc_requirements.md` (requirements & design decisions)
**Constraint:** No changes to the ROS2K runtime architecture. POC only.

---

## 1. Scope

### Core Build (this pass)

| Component | File | Est. lines | Status |
|-----------|------|-----------|--------|
| Supervisor | `tools/r2k_supervisor.py` | ~600 | NEW |
| Frontend HTML | `tools/gui/index.html` | ~120 | REWRITE |
| Frontend CSS | `tools/gui/style.css` | ~250 | NEW (extracted + extended) |
| Frontend JS | `tools/gui/app.js` | ~500 | NEW (reactive store + renderers) |
| Launcher | `launch_gzweb.sh` | 1 line | MODIFY |

### Follow-Up (deferred)

- System tree (sidebar dots + detail panel)
- Toast notifications
- Button highlighting
- Assistant panel (Ollama dialogue)
- SSE event stream
- Reboot bring-up buttons
- Replay view
- Probe browser
- KPI dashboard
- Prompt viewer

---

## 2. r2k_supervisor.py — Implementation Detail

### 2.1 Module Structure

```python
#!/usr/bin/env python3
"""r2k_supervisor.py — PID-tracked process manager + state machine + file-bus backend.

Replaces ws_backend.py. Runs inside the r2k_gzweb Docker container on port 8765.
Does NOT modify the ROS2K runtime architecture — it launches and monitors the
same processes that launch_gzweb.sh launches, but tracks them by PID.
"""

import asyncio, json, os, time, glob, subprocess, mimetypes
from dataclasses import dataclass, field
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
FILES_TO_MONITOR = ["Worldstate.json", "current_strategy.json"]
PORT = 8765
SOURCE_CMD = "cd /workspace && source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash"

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
        proc = await asyncio.create_subprocess_shell(
            cmd,
            env=full_env,
            stdout=log_file,
            stderr=subprocess.STDOUT)
        mp = ManagedProc(name=name, proc=proc, started_at=time.time())
        mp.log_path = log_path
        mp.log_file = log_file
        self.children[name] = mp
        return mp

    async def stop(self, name, timeout=3.0):
        """Stop a child by PID. SIGTERM → wait → SIGKILL."""
        mp = self.children.get(name)
        if not mp or not mp.proc:
            return True
        mp.proc.terminate()  # SIGTERM
        try:
            await asyncio.wait_for(mp.proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            mp.proc.kill()  # SIGKILL
            await mp.proc.wait()
        if hasattr(mp, 'log_file'):
            mp.log_file.close()
        del self.children[name]
        return True

    async def stop_all(self):
        """Stop all children in parallel."""
        names = list(self.children.keys())
        await asyncio.gather(*[self.stop(n) for n in names], return_exceptions=True)

    def is_alive(self, name):
        mp = self.children.get(name)
        return mp and mp.proc and mp.proc.returncode is None
```

### 2.2 Supervisor Class

```python
class Supervisor:
    def __init__(self):
        self.pm = ProcessManager()
        self.state = S.IDLE
        self.lock = asyncio.Lock()
        self.current_model = None
        self.ws_clients = set()

    async def transition(self, new_state):
        async with self.lock:
            self.state = new_state
            self._broadcast_ws({"type": "state", "data": new_state.value})

    # -- Launch --
    async def launch(self, scenario, strategy, model, explain, duration):
        # 1. Validate scenario
        if not self._scenario_exists(scenario):
            return web.json_response(
                {"status":"error","detail":f"Scenario '{scenario}' not found"}, status=400)
        # 2. Check state
        if self.state != S.IDLE:
            return web.json_response(
                {"status":"error","detail":"Match running — press DONE first"}, status=409)
        await self.transition(S.LAUNCHING)
        try:
            await self._teardown_existing()
            self._clean_state_files()
            await self._run_setup(scenario, strategy, model, explain)
            await self._start_gzserver()
            await self._spawn_bots()
            await self._start_gzbridge()
            await self._start_ros2_nodes(scenario, strategy, model, explain)
            self.current_model = model
            await self.transition(S.RUNNING)
            if duration and duration != "0":
                asyncio.create_task(self._auto_stop(int(duration)))
            return web.json_response({"status":"launched", "scenario":scenario, "model":model})
        except Exception as e:
            await self.pm.stop_all()
            await self.transition(S.IDLE)
            return web.json_response({"status":"error","detail":str(e)}, status=500)

    # -- Done --
    async def done(self):
        if self.state != S.RUNNING:
            return web.json_response(
                {"status":"error","detail":"No match running"}, status=409)
        await self.transition(S.TEARING_DOWN)
        await self.pm.stop_all()
        await self._unload_ollama()
        self.current_model = None
        await self.transition(S.IDLE)
        return web.json_response({"status":"match stopped"})

    # -- Ollama unload --
    async def _unload_ollama(self):
        """Unload ALL loaded Ollama models from VRAM.

        Uses asyncio.create_subprocess_exec (non-blocking) — subprocess.run
        would freeze the event loop for 8s per model."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", "curl -s -m 3 http://127.0.0.1:11434/api/ps",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            models = [m["name"] for m in json.loads(stdout.decode()).get("models", [])]
        except Exception:
            models = []
        if self.current_model and self.current_model not in models:
            models.append(self.current_model)
        for m in models:
            try:
                unload_proc = await asyncio.create_subprocess_exec(
                    "bash", "-c",
                    f'curl -s -m 5 http://127.0.0.1:11434/api/generate '
                    f'-d \'{{"model":"{m}","keep_alive":0}}\'',
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
                await asyncio.wait_for(unload_proc.wait(), timeout=8)
            except Exception:
                pass

    # -- Health checks are in §2.5 (health monitor loop) --
```

### 2.3 Endpoint Registration

```python
async def main():
    sup = Supervisor()
    app = web.Application()
    # API routes FIRST — the catch-all static handler MUST be registered last
    # or it would shadow these endpoints.
    app.router.add_get('/catalog', sup.handle_catalog)
    app.router.add_get('/state', lambda r: web.json_response({"state": sup.state.value}))
    app.router.add_get('/health', lambda r: web.json_response(await sup.health()))
    app.router.add_get('/launch', sup.handle_launch)
    app.router.add_get('/done', sup.handle_done)
    app.router.add_get('/runs', sup.handle_runs)
    app.router.add_get('/git/commits', sup.handle_git_commits)
    app.router.add_get('/session/digest', sup.handle_session_digest)
    app.router.add_get('/reboot/check', lambda r: web.json_response(await sup.health()))
    app.router.add_get('/ws', sup.handle_ws)
    # Static file handler — MUST be last (catch-all for index.html, style.css, app.js)
    app.router.add_get('/', lambda r: sup.handle_static(r))
    app.router.add_get('/{path:.*}', lambda r: sup.handle_static(r))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Supervisor on http://0.0.0.0:{PORT}")
    # Start health monitor task
    asyncio.create_task(sup.health_monitor_loop())
    await asyncio.Future()  # run forever
```

### 2.4 Static File Handler (with no-cache)

```python
async def handle_static(self, request):
    rel = request.match_info.get('path', '') or 'index.html'
    rel = rel.replace('..', '').lstrip('/')
    # Map: '' → index.html, 'app.js' → app.js, 'style.css' → style.css
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
```

### 2.5 Health Monitor Loop

```python
async def health_monitor_loop(self):
    """Push health updates to all WS clients every 2s.

    Each check runs concurrently with a 2s timeout. If a check (e.g.
    nvidia-smi, Ollama curl) hangs, it returns {"status":"timeout"}
    instead of stalling the loop."""
    last_health = None
    while True:
        h = await self.health()
        if h != last_health:
            last_health = h
            self._broadcast_ws({"type": "health", "data": h})
        await asyncio.sleep(2)

async def health(self):
    """Run all health checks concurrently. Each is capped at 2s."""
    async def _safe(check_fn, *args):
        try:
            return await asyncio.wait_for(check_fn(*args), timeout=2)
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
        "ros2_nodes": {n: self.pm.is_alive(n) for n in
                      ["tracker","referee","score","reward",
                       "rule_evaluator_red","state_aggregator","bridge","evaluator"]},
        "gpu": results[2],
        "file_bus": self._check_file_bus(),
        "state": self.state.value,
    }
```

### 2.6 Catalog (mode-grouped strategies)

```python
async def handle_catalog(self, request):
    scenarios = []
    modes_set = set()
    for path in sorted(glob.glob(os.path.join(SCENARIO_DIR, "*.json"))):
        d = await self._read_json(path)
        if not d: continue
        name = os.path.splitext(os.path.basename(path))[0]
        mode = d.get("mode") or d.get("scene_type") or "?"
        label = d.get("tactical_situation") or d.get("label") or name
        n_entities = len(d.get("entities", {}))
        scenarios.append({"name":name,"mode":mode,"label":label,"bots":n_entities})
        modes_set.add(mode)
    # For each mode, list available strategies from fragment files
    modes = {}
    for mode in sorted(modes_set):
        strategies = []
        # strat_<mode> if rules_<mode>.txt exists
        if os.path.isfile(os.path.join(STRATEGY_FRAG_DIR, f"rules_{mode}.txt")):
            strategies.append(f"strat_{mode}")
        # strat_aggro is the universal default
        if "strat_aggro" not in strategies:
            strategies.append("strat_aggro")
        modes[mode] = {"strategies": strategies}
    # Models
    models = await self._get_ollama_models()
    return web.json_response({"scenarios":scenarios,"modes":modes,"models":models})
```

---

## 3. Frontend — Implementation Detail

### 3.1 index.html (structure only)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ROS2K — Simulation GUI</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="topbar">...</div>
  <div id="main">
    <div id="sidebar">...</div>
    <div id="content">
      <div id="wf-bar">...</div>
      <div id="dock"></div>
      <div id="text-pane"></div>
      <div id="selbar">...</div>
    </div>
  </div>
  <div id="overlay">...</div>
  <script src="app.js"></script>
</body>
</html>
```

### 3.2 app.js — Reactive Store

```javascript
const Store = {
  supervisorState: 'idle',
  world: {entities:{}, match_state:{}, tactical_score:{}},
  strategy: {assignments:{}, latency_ms:null, model_name:null},
  momentum: [], matchEvents: [],
  health: {}, catalog: {scenarios:[], modes:{}, models:[]},
  commits: [], runs: [], sessionDigest: '',
  activeWorkflow: 'home',
  _subs: {},

  on(key, fn) { (this._subs[key] ||= []).push(fn); },
  set(key, val) {
    this[key] = val;
    (this._subs[key]||[]).forEach(fn => fn(val));
  },
  resetMatch() {
    this.world = {entities:{}, match_state:{}, tactical_score:{}};
    this.strategy = {assignments:{}, latency_ms:null, model_name:null};
    this.momentum = []; this.matchEvents = [];
  },
  saveSelection() {
    localStorage.setItem('r2k_sel', JSON.stringify({
      scenario: document.getElementById('sel-scenario')?.value,
      strategy: document.getElementById('sel-strategy')?.value,
      model: document.getElementById('sel-model')?.value,
    }));
  },
  loadSelection() {
    try { return JSON.parse(localStorage.getItem('r2k_sel') || '{}'); }
    catch { return {}; }
  }
};
```

### 3.3 app.js — WebSocket Handler

```javascript
const BACKEND = location.origin;
const WS_URL = BACKEND.replace('http','ws') + '/ws';

function connectWS() {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => { /* update dot */ };
  ws.onclose = () => { /* update dot, reconnect in 1.5s */ };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'state') {
      Store.set('supervisorState', msg.data);
      updateLaunchButton(msg.data);
    } else if (msg.type === 'health') {
      Store.set('health', msg.data);
      if (Store.activeWorkflow === 'home') renderHomepage();
    } else if (msg.file === 'Worldstate.json') {
      Store.set('world', msg.data);
      onWorld(msg.data);
    } else if (msg.file === 'current_strategy.json') {
      Store.set('strategy', msg.data);
      onStrategy(msg.data);
    }
  };
}
connectWS();
```

### 3.4 app.js — Canvas Renderers

The `drawWorld()` and `drawMomentum()` functions are reused from the existing
`index.html` with one change: they read from `Store.world` and `Store.momentum`
instead of bare globals, and they are called by the store subscription callback
instead of being called imperatively from `onWorld()`.

### 3.5 app.js — Catalog + Scenario-Strategy Filtering

```javascript
async function loadCatalog() {
  const r = await fetch(BACKEND + '/catalog');
  const cat = await r.json();
  Store.set('catalog', cat);
  const saved = Store.loadSelection();

  // Populate scenario dropdown
  const ss = document.getElementById('sel-scenario');
  ss.innerHTML = cat.scenarios.map(s =>
    `<option value="${s.name}">${s.name} (${s.mode}, ${s.bots} bots) — ${s.label}</option>`
  ).join('');
  // Restore last selection (no hardcoded default)
  if (saved.scenario) ss.value = saved.scenario;

  // Populate model dropdown
  const ms = document.getElementById('sel-model');
  ms.innerHTML = cat.models.map(m => `<option value="${m}">${m}</option>`).join('');
  if (saved.model) ms.value = saved.model;

  // Filter strategies by selected scenario's mode
  filterStrategies();
  ss.addEventListener('change', filterStrategies);
}

function filterStrategies() {
  const scenarioName = document.getElementById('sel-scenario').value;
  const scenario = Store.catalog.scenarios.find(s => s.name === scenarioName);
  if (!scenario) return;
  const modeData = Store.catalog.modes[scenario.mode];
  const strategies = modeData ? modeData.strategies : ['strat_aggro'];
  const strat = document.getElementById('sel-strategy');
  strat.innerHTML = strategies.map(s => `<option value="${s}">${s}</option>`).join('');
  const saved = Store.loadSelection();
  if (saved.strategy && strategies.includes(saved.strategy)) strat.value = saved.strategy;
}
```

### 3.6 app.js — Launch / Done

```javascript
document.getElementById('btn-launch').addEventListener('click', async () => {
  const sc = document.getElementById('sel-scenario').value;
  const st = document.getElementById('sel-strategy').value;
  const md = document.getElementById('sel-model').value;
  const ex = document.getElementById('sel-explain').value;
  const du = document.getElementById('sel-duration').value;
  Store.saveSelection();  // persist for next page load
  Store.resetMatch();     // clear stale entities immediately

  const btn = document.getElementById('btn-launch');
  btn.disabled = true; btn.textContent = 'LAUNCHING…';
  try {
    const r = await fetch(`${BACKEND}/launch?scenario=${encodeURIComponent(sc)}&strategy=${encodeURIComponent(st)}&model=${encodeURIComponent(md)}&explain=${ex}&duration=${du}`);
    const d = await r.json();
    if (d.status === 'launched') {
      btn.textContent = 'RUNNING';
      selectWorkflow('play-game');
      // Reload GZWeb iframe (gzbridge restarted with new match)
      setTimeout(() => {
        const iframe = document.getElementById('gz-iframe');
        if (iframe) iframe.src = iframe.src;
      }, 3000);
    } else {
      btn.textContent = 'LAUNCH';
      alert('Launch failed: ' + (d.detail || 'unknown'));
    }
  } catch(e) {
    btn.textContent = 'LAUNCH';
    alert('Launch error: ' + e);
  }
  btn.disabled = false;
});

document.getElementById('btn-done').addEventListener('click', async () => {
  document.getElementById('overlay').classList.add('show');
  try {
    const r = await fetch(BACKEND + '/done');
    const d = await r.json();
    document.getElementById('btn-launch').textContent = 'LAUNCH';
    Store.resetMatch();
    setTimeout(() => document.getElementById('overlay').classList.remove('show'), 2000);
  } catch(e) {
    document.getElementById('ov-text').textContent = 'Teardown failed: ' + e;
    setTimeout(() => document.getElementById('overlay').classList.remove('show'), 3000);
  }
});
```

### 3.7 app.js — Homepage Renderer

```javascript
function renderHomepage() {
  const dock = document.getElementById('dock');
  const h = Store.health;
  const commits = Store.commits;
  const runs = Store.runs;
  const digest = Store.sessionDigest;

  dock.innerHTML = `
    <div class="home-grid">
      <div class="home-card">
        <div class="home-card-title">Recent Commits</div>
        <div class="home-card-body">${commits.map(c => `<div class="commit">${c}</div>`).join('')}</div>
      </div>
      <div class="home-card">
        <div class="home-card-title">System Health</div>
        <div class="home-card-body">${renderHealthCards(h)}</div>
      </div>
      <div class="home-card">
        <div class="home-card-title">Recent Runs</div>
        <div class="home-card-body">${runs.map(r => `<div class="run">${r}</div>`).join('')}</div>
      </div>
      <div class="home-card">
        <div class="home-card-title">Quick Launch</div>
        <div class="home-card-body">
          <button onclick="quickLaunch('3vs3_default')">▶ 3vs3 Default</button>
          <button onclick="quickLaunch('2vs2_default')">▶ 2vs2 Default</button>
        </div>
      </div>
      <div class="home-card home-wide">
        <div class="home-card-title">Session Digest</div>
        <div class="home-card-body digest">${digest}</div>
      </div>
    </div>
  `;
}

function renderHealthCards(h) {
  if (!h || !h.ollama) return 'Loading…';
  const card = (label, ok, detail) => `
    <div class="health-card ${ok?'ok':'down'}">
      <span class="dot ${ok?'on':'off'}"></span>
      <span class="label">${label}</span>
      <span class="detail">${detail}</span>
    </div>`;
  return [
    card('Ollama', h.ollama.up, h.ollama.models || ''),
    card('Docker', h.docker, h.docker ? 'up' : 'down'),
    card('gzserver', h.gzserver, h.gzserver ? 'alive' : 'down'),
    card('GPU', true, h.gpu ? `${h.gpu.temp}°C ${h.gpu.util}%` : '—'),
    card('FileBus', h.file_bus, h.file_bus ? 'fresh' : 'stale'),
  ].join('');
}
```

---

## 4. launch_gzweb.sh — Change

One line: replace `ws_backend.py` with `r2k_supervisor.py`.

```diff
- docker exec -d $CONTAINER_NAME bash -c 'cd /workspace && python3 tools/ws_backend.py' > /dev/null 2>&1
+ docker exec -d $CONTAINER_NAME bash -c 'cd /workspace && python3 tools/r2k_supervisor.py' > /dev/null 2>&1
```

Everything else in `launch_gzweb.sh` stays the same — the watchdog, teardown
trap, Ollama check, and Docker launch sequence are unchanged. The supervisor
takes over the file-bus WebSocket role AND the launch/done process management
that was previously split between `ws_backend.py` (HTTP endpoints) and
`launch_gzweb.sh` (process spawning).

Note: `launch_gzweb.sh` still spawns gzserver, gzbridge, and ROS2 nodes directly
when run from the command line. The supervisor's process manager is used only
when launching from the GUI (via `/launch`). Both paths can coexist — the
supervisor's `stop_all()` only stops processes it started (tracked by PID),
not ones started by `launch_gzweb.sh`.

---

## 5. Build Order

| Step | File | What | Depends on |
|------|------|------|------------|
| 1 | `tools/r2k_supervisor.py` | Full supervisor: ProcessManager, StateMachine, all endpoints, health monitor, WS push, catalog with mode grouping, static file handler with no-cache | — |
| 2 | `tools/gui/style.css` | Extract styles from old `index.html` + add homepage grid, health card styles | — |
| 3 | `tools/gui/index.html` | Rewrite: HTML structure only, link to style.css + app.js | Step 2 |
| 4 | `tools/gui/app.js` | Reactive store, WS handler, canvas renderers, catalog + filtering, launch/done, homepage renderer, workflow switching | Steps 1, 3 |
| 5 | `launch_gzweb.sh` | Change 1 line | Step 1 |
| 6 | Restart + test | Verify: 3vs3 launches correctly, DONE kills all + unloads GPU, dropdown retains selection, homepage shows health/commits/runs | All |

---

## 6. Verification Checklist

After implementation:

| # | Check | Expected result |
|---|-------|-----------------|
| 1 | `python3 -m py_compile tools/r2k_supervisor.py` | OK |
| 2 | `curl localhost:8765/health` | JSON with all subsystem statuses |
| 3 | `curl localhost:8765/catalog` | Scenarios with mode-grouped strategies |
| 4 | `curl "localhost:8765/launch?scenario=3vs3_default&..."` | `{"status":"launched","scenario":"3vs3_default"}` |
| 5 | `curl localhost:8765/done` | `{"status":"match stopped"}` |
| 6 | After DONE: `nvidia-smi` GPU memory | <200 MiB (just Xorg) |
| 7 | After DONE: `curl localhost:11434/api/ps` | `{"models":[]}` |
| 8 | Browser: select 3vs3, launch | 3D scene shows 6 bots, 2D widget shows 7 entities |
| 9 | Browser: select 3vs2, hard refresh | Dropdown still shows 3vs2 (localStorage) |
| 10 | Browser: homepage shows commits + health + runs | Yes |
| 11 | Browser: invalid scenario (e.g. "n_vs_m") | Error message, no match starts |
| 12 | `python3 -m pytest tests/ --skip-slow -q --ignore=tests/test_adaptive_horizon.py --ignore=tests/test_i3_sweep.py` | No new failures |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `asyncio.create_subprocess_shell` not available in container Python 3.10 | Low | High | Python 3.10 supports it. Dockerfile uses `osrf/ros:humble-desktop` (Python 3.10). |
| GZWeb iframe doesn't reconnect after gzbridge restart | Medium | Medium | Force-reload iframe after 3s delay. If still broken, user can manually refresh. |
| `ros2 launch` inside `asyncio.create_subprocess_shell` loses ROS env vars | — | — | **Fixed:** ProcessManager inherits `os.environ.copy()` + merges override vars. See §2.1. |
| Supervisor and `launch_gzweb.sh` both try to manage processes | Low | Medium | Supervisor only stops processes it started (PID-tracked). `launch_gzweb.sh` processes are invisible to the supervisor. |
| Health monitor loop blocks the event loop | — | — | **Fixed:** All checks run concurrently via `asyncio.gather()` with 2s per-check timeout. See §2.5. |
| `localStorage` not available (private browsing) | Low | Low | Graceful fallback: no persistence, defaults to first scenario in list. |
| Ollama unload freezes supervisor during `/done` | — | — | **Fixed:** Uses `asyncio.create_subprocess_exec` (non-blocking) instead of `subprocess.run`. See §2.2. |
| gzserver not ready before bot spawn (hardcoded sleep) | — | — | **Fixed:** Poll for gzserver readiness up to 15s instead of `sleep(6)`. See requirements §3.6 step 6. |
| Silent child crashes (stdout=DEVNULL) | — | — | **Fixed:** Each child logs to `/tmp/supervisor_<name>.log`. See §2.1. |
| API routes shadowed by static catch-all | — | — | **Fixed:** Catch-all registered LAST, after all API routes. See §2.3. |

---

## 8. Out of Scope (Explicit)

- No changes to `launch_r2k.sh` (production launcher)
- No changes to any ROS2 node code
- No changes to `setup_r2k.py` (prompt compiler)
- No changes to `docker-compose.gzweb.yml` or `Dockerfile.gzweb`
- No new pip dependencies (aiohttp + aiofiles already installed)
- No opencode integration (deferred)
- No W&B integration (ADR-A03 stays — rejected)
- No Trello integration (deferred)
- No three-pillar navigation (deferred — Simulation pillar only)
- No two-level nav bar (deferred — after pillars)
- No production deployment — POC only

---

## 9. v7 Use Cases — Reference

Detailed in `gui_v67_poc_requirements.md` §7. These are NOT in scope for the
core build or follow-up. They are documented to ensure the architecture
doesn't preclude them.

| UC# | Title | Role | AI mode | Scope |
|-----|-------|------|---------|-------|
| 11 | Improve system prompt by watching failures | LLM Designer | C + B | v7 |
| 12 | Evaluate a candidate LLM model | Experimentation, QA | B + C | v7 |
| 13 | Probe a prompt variant in seconds | LLM Designer | B | v7 |
| 14 | Benchmark: which fragment helped? | QA, Experimentation | C | v7 |
| 15 | Extend the world model systematically | Experimentation, Admin | B | v7 |
| 16 | Eye-in-the-sky calibration | Support, Experimentation | A | v7 |
| 17 | Video recording review | QA, Experimentation | C | v7 |

### 9.1 AI Integration Modes (To Be Discussed)

Detailed in `gui_v67_poc_requirements.md` §6.1.

| Mode | Name | Trigger | LLM | Technical req |
|------|------|---------|-----|---------------|
| A | Supervisor | Passive (system events) | Optional (alert text only) | SSE stream + local rule engine |
| B | Copilot | User asks | qwen2.5:7b + META-ROUTER | Assistant panel + context injection |
| C | Analyst | On demand or post-match | qwen2.5:7b (long generation) | Subprocess task runner + structured output parsing |

### 9.2 Additional v7 Candidates (To Be Discussed)

From `gui_v67_poc_requirements.md` §7.1:

- TeamCaptain integration (two decision levels visible)
- Robot-to-robot communication (message stream view)
- STT voice input for demo mode
- K1 image recognition (multi-source world model)
- Scalability / "automatischer Wilhelm" (project registry)
- Reboot management (full bring-up automation)