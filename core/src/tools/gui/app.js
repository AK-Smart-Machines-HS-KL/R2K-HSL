/* ROS2K Simulation GUI — app.js (v6.7 POC)
   Reactive store + WS handler + canvas renderers + catalog + launch/done +
   homepage renderer. Backend: r2k_supervisor.py on :8765. */

const BACKEND = location.origin;
const WS_URL = BACKEND.replace('http', 'ws') + '/ws';
const FX_MIN = -4.5, FX_MAX = 4.5, FY_MIN = -3.0, FY_MAX = 3.0,
      GOAL_Y = 0.9, GOAL_AREA_X = 3.5, GOAL_AREA_Y = 1.0;

// ---- reactive store ----
const Store = {
  supervisorState: 'idle',
  world: {entities:{}, match_state:{}, tactical_score:{}},
  strategy: {assignments:{}, latency_ms:null, model_name:null},
  momentum: [], matchEvents: [],
  health: {}, catalog: {scenarios:[], modes:{}, models:[]},
  commits: [], runs: [], sessionDigest: '',
  activeWorkflow: 'home',
  lastStatus: 'playing', gameStart: null,
  _subs: {},

  on(key, fn) {
    if (!this._subs[key]) this._subs[key] = [];
    this._subs[key].push(fn);
  },
  set(key, val) {
    this[key] = val;
    (this._subs[key] || []).forEach(fn => fn(val));
  },
  resetMatch() {
    this.world = {entities:{}, match_state:{}, tactical_score:{}};
    this.strategy = {assignments:{}, latency_ms:null, model_name:null};
    this.momentum = []; this.matchEvents = [];
    this.lastStatus = 'playing'; this.gameStart = null;
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

// ---- workflow definitions ----
const WF = {
  'home': {
    title: 'Home', live: 'home',
    desc: 'System overview and quick launch.'
  },
  'play-game': {
    title: 'Play › Game', live: true,
    desc: 'Live AI match: LLM-driven blue team vs Python red. Select scenario + model, then launch. Watch the 3D scene, 2D world model, LLM stream, and referee events in real time.'
  },
  'play-demo': {
    title: 'Play › Demo / Calibration', live: true, demo: true,
    desc: 'Waypoint-based calibration mode for fairs and hardware tests. A single bot executes compiled waypoint tasks. Referee/score nodes are skipped in demo mode.'
  },
  'play-replay': {
    title: 'Play › Replay', live: false,
    desc: 'Step through a recorded run (world_trace + llm_trace). Same widgets as live, but the clock is the trace timeline. Deferred to the follow-up pass.',
    mockup: `┌─ Replay controls ─────────────────────────────┐
│  ⏪ ◀  ⏸  ▶  ⏩     t: 45.2s / 120.0s          │
│  annotation: "Blue loses possession"           │
└────────────────────────────────────────────────┘`
  },
  'build-prompt': {
    title: 'Build › Prompt Designer', live: false,
    desc: 'Inspect the assembled system prompt per match_state.status. Deferred to the follow-up pass.',
    mockup: `┌─ Prompt viewer — status: ball_out ────────────┐
│ header.txt      ████████████████████████ 45tok │
│ rules_ball_out  ████     ← status-specific     │
└───────────────────────────────────────────────┘`
  },
  'build-probe': {
    title: 'Build › Probe', live: false,
    desc: 'Text-predicate corpus runner — no Gazebo needed. Deferred to the follow-up pass.',
    mockup: `┌─ Probe results ───────────────────────────────┐
│ goalie_kick_own_half    18/20  ✅  90%          │
│ defending_deep           9/15  ❌  60%          │
└───────────────────────────────────────────────┘`
  },
  'analyze-debrief': {
    title: 'Analyze › Match Debrief', live: false,
    desc: 'Post-match review: replay, score/momentum timeline, referee decisions. Deferred to the follow-up pass.',
    mockup: `┌─ Debrief — Run 3vs3_default_…1825 ────────────┐
│ Goals: Blue 2 – Red 1 · 2 goals · 1 foul       │
└───────────────────────────────────────────────┘`
  },
  'analyze-kpi': {
    title: 'Analyze › KPI Dashboard', live: false,
    desc: 'Traffic-light dashboard: each KPI vs kpi_targets.json. Deferred to the follow-up pass.',
    mockup: `┌─ QA dashboard ────────────────────────────────┐
│ possession       58%      ●                    │
│ latency p50      658ms    ◐  (≤750)            │
└───────────────────────────────────────────────┘`
  },
  'analyze-benchmark': {
    title: 'Analyze › Benchmark', live: false,
    desc: 'A/B comparison of prompt variants across scenarios. Deferred to the follow-up pass.',
    mockup: `┌─ A/B Benchmark — V1 vs baseline ──────────────┐
│ composite           0.52        0.71   +0.19   │
└───────────────────────────────────────────────┘`
  },
  'know-search': {
    title: 'Know › Router Search', live: false,
    desc: 'Inverted-index search across the knowledge base. Deferred to the follow-up pass.',
    mockup: `┌─ Router search ───────────────────────────────┐
│ 🔍 goalie leaves goal → 8_C3_SOCCER §V1        │
└───────────────────────────────────────────────┘`
  },
  'know-assistant': {
    title: 'Know › Assistant', live: 'assistant',
    desc: 'Copilot dialogue (mode B): local Ollama model with the META-ROUTER knowledge base and the live match state as context. Answers are grounded in the repo — symptoms are routed to the right power file.'
  },
  'know-tour': {
    title: 'Know › Onboarding Tour', live: false,
    desc: 'Five-station guided tour for freshmen. Deferred to the follow-up pass.',
    mockup: `① Watch a match → ② World state & prompt → ③ Probe`
  }
};

// ---- live dock panels ----
function buildDock() {
  const dock = document.getElementById('dock');
  dock.innerHTML = `
    <div class="panel" id="p-3d"><div class="ph">3D Scene <span class="hint">· GZWeb live</span></div><div class="pb"><iframe id="gz-iframe" src="http://localhost:8080"></iframe></div></div>
    <div class="panel" id="p-world"><div class="ph">World Model <span class="hint">· 2D pitch + intent</span></div><div class="pb"><canvas id="c-world"></canvas></div></div>
    <div class="panel" id="p-llm"><div class="ph">LLM Stream <span class="hint">· assignments</span></div><div class="pb" id="llm-body"><div class="empty" style="color:var(--text-dim)">waiting…</div></div></div>
    <div class="panel" id="p-referee"><div class="ph">Referee <span class="hint">· events</span></div><div class="pb" id="ref-body"><div class="empty">No events</div></div></div>
    <div class="panel" id="p-momentum"><div class="ph">Momentum <span class="hint">· score</span></div><div class="pb"><canvas id="c-mom"></canvas></div></div>
  `;
}

// ---- homepage ----
async function loadHomeData() {
  try {
    const [c, r, d] = await Promise.all([
      fetch(BACKEND + '/git/commits').then(x => x.json()).catch(() => ({})),
      fetch(BACKEND + '/runs').then(x => x.json()).catch(() => ({})),
      fetch(BACKEND + '/session/digest').then(x => x.json()).catch(() => ({})),
    ]);
    Store.set('commits', c.commits || []);
    Store.set('runs', (r.runs || []).map(x => x.run_id));
    Store.set('sessionDigest', d.digest || (d.detail || ''));
    if (Store.activeWorkflow === 'home') renderHomepage();
  } catch (e) { console.error('home data', e); }
}

function renderHomepage() {
  const dock = document.getElementById('dock');
  const h = Store.health;
  const commits = Store.commits;
  const runs = Store.runs;
  const digest = Store.sessionDigest;

  dock.innerHTML = `
    <div class="home-grid">
      <div class="home-card">
        <div class="home-card-title">System Health</div>
        <div class="home-card-body">${renderHealthCards(h)}</div>
      </div>
      <div class="home-card">
        <div class="home-card-title">Quick Launch</div>
        <div class="home-card-body">
          <button onclick="quickLaunch('3vs3_default')">▶ 3vs3 Default</button>
          <button onclick="quickLaunch('2vs2_default')">▶ 2vs2 Default</button>
        </div>
      </div>
      <div class="home-card">
        <div class="home-card-title">Recent Commits</div>
        <div class="home-card-body">${commits.length ? commits.map(c => `<div class="commit">${c}</div>`).join('') : '<i>—</i>'}</div>
      </div>
      <div class="home-card">
        <div class="home-card-title">Recent Runs</div>
        <div class="home-card-body">${runs.length ? runs.map(r => `<div class="run"><span class="run-id">${r}</span></div>`).join('') : '<i>—</i>'}</div>
      </div>
      <div class="home-card home-wide">
        <div class="home-card-title">Session Digest</div>
        <div class="home-card-body digest">${digest ? digest.replace(/</g, '&lt;') : '<i>—</i>'}</div>
      </div>
    </div>
  `;
}

function renderHealthCards(h) {
  if (!h || !h.ollama) return 'Loading…';
  const card = (label, ok, detail) => `
    <div class="health-card ${ok ? 'ok' : 'down'}">
      <span class="dot ${ok ? 'on' : 'off'}"></span>
      <span class="label">${label}</span>
      <span class="detail">${detail || ''}</span>
    </div>`;
  const gpuOk = h.gpu && h.gpu.available !== false && h.gpu.temp !== undefined;
  const gpuDetail = h.gpu ? (h.gpu.detail || (gpuOk ? `${h.gpu.temp}°C ${h.gpu.util}% ${h.gpu.mem_mb}MB` : '')) : '';
  const nodes = h.ros2_nodes ? Object.entries(h.ros2_nodes).filter(([, v]) => v).map(([n]) => n).join(',') : '';
  return [
    card('Ollama', h.ollama.up, (h.ollama.models || []).join(', ')),
    card('Docker', h.docker && h.docker.up !== false ? 'up' : 'down', ''),
    card('gzserver', h.gzserver, h.gzserver ? 'alive' : 'down'),
    card('GPU', gpuOk, gpuDetail),
    card('FileBus', h.file_bus && h.file_bus.fresh, h.file_bus ? (h.file_bus.fresh ? 'fresh' : `stale ${h.file_bus.age_s ?? '?'}s`) : ''),
    card('Nodes', nodes.length > 0, nodes),
  ].join('');
}

async function quickLaunch(scenario) {
  const cat = Store.catalog;
  const sc = cat.scenarios.find(s => s.name === scenario);
  const mode = sc ? sc.mode : null;
  const modeData = mode ? cat.modes[mode] : null;
  const strategy = modeData ? modeData.strategies[0] : 'strat_aggro';
  const model = document.getElementById('sel-model').value || 'qwen2.5:3b';
  selectWorkflow('play-game');
  await doLaunch(scenario, strategy, model, '0', '0');
}

// ---- workflow switching ----
function selectWorkflow(wfKey) {
  const info = WF[wfKey]; if (!info) return;
  Store.activeWorkflow = wfKey;
  document.querySelectorAll('#sidebar .nav-item').forEach(r => r.classList.remove('active'));
  document.querySelector(`[data-wf="${wfKey}"]`)?.classList.add('active');
  document.querySelector(`[data-wf="${wfKey}"]`)?.closest('.nav-group')?.classList.remove('collapsed');

  document.getElementById('wf-title').textContent = info.title;
  document.getElementById('wf-desc').textContent = info.desc;

  const dock = document.getElementById('dock');
  const textPane = document.getElementById('text-pane');
  if (info.live === 'home') {
    dock.classList.remove('hide'); textPane.classList.remove('show'); textPane.classList.add('hide');
    renderHomepage();
  } else if (info.live === 'assistant') {
    dock.classList.add('hide'); textPane.classList.remove('hide'); textPane.classList.add('show');
    renderAssistantChat();
  } else if (info.live) {
    buildDock();
    dock.classList.remove('hide'); textPane.classList.remove('show'); textPane.classList.add('hide');
    drawWorld(); drawMomentum(); renderLLM(Store.strategy); renderReferee();
  } else {
    dock.classList.add('hide'); textPane.classList.remove('hide'); textPane.classList.add('show');
    let html = `<h2>${info.title}</h2><p>${info.desc}</p>`;
    if (info.mockup) html += `<h3>Mockup</h3><div class="mockup">${info.mockup.replace(/</g, '&lt;')}</div>`;
    textPane.innerHTML = html;
  }
}

// ---- nav wiring ----
document.querySelectorAll('.ng-header').forEach(h => {
  h.addEventListener('click', () => h.parentElement.classList.toggle('collapsed'));
});
document.querySelectorAll('#sidebar .nav-item').forEach(el => {
  el.addEventListener('click', () => selectWorkflow(el.dataset.wf));
});

// ---- catalog + scenario-strategy filtering ----
async function loadCatalog() {
  const r = await fetch(BACKEND + '/catalog');
  const cat = await r.json();
  Store.set('catalog', cat);
  const saved = Store.loadSelection();

  const ss = document.getElementById('sel-scenario');
  ss.innerHTML = cat.scenarios.map(s =>
    `<option value="${s.name}">${s.name} (${s.mode}, ${s.bots} bots) — ${s.label}</option>`
  ).join('');
  if (saved.scenario && cat.scenarios.some(s => s.name === saved.scenario)) ss.value = saved.scenario;

  const ms = document.getElementById('sel-model');
  ms.innerHTML = (cat.models || []).map(m => `<option value="${m}">${m}</option>`).join('');
  if (saved.model && (cat.models || []).includes(saved.model)) ms.value = saved.model;

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

// ---- launch / done ----
async function doLaunch(scenario, strategy, model, explain, duration) {
  Store.saveSelection();
  Store.resetMatch();

  const btn = document.getElementById('btn-launch');
  btn.disabled = true; btn.textContent = 'LAUNCHING…';
  try {
    const demo = WF[Store.activeWorkflow]?.demo ? '1' : '0';
    const r = await fetch(`${BACKEND}/launch?scenario=${encodeURIComponent(scenario)}&strategy=${encodeURIComponent(strategy)}&model=${encodeURIComponent(model)}&explain=${explain}&duration=${duration}&demo=${demo}`);
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
  } catch (e) {
    btn.textContent = 'LAUNCH';
    alert('Launch error: ' + e);
  }
  btn.disabled = false;
}

document.getElementById('btn-launch').addEventListener('click', () => {
  doLaunch(
    document.getElementById('sel-scenario').value,
    document.getElementById('sel-strategy').value,
    document.getElementById('sel-model').value,
    document.getElementById('sel-explain').value,
    document.getElementById('sel-duration').value,
  );
});

document.getElementById('btn-done').addEventListener('click', async () => {
  document.getElementById('overlay').classList.add('show');
  document.getElementById('ov-text').textContent = 'Teardown…';
  try {
    const r = await fetch(BACKEND + '/done');
    const d = await r.json();
    document.getElementById('ov-text').textContent =
      d.status === 'match stopped' ? 'Match stopped.' : ('Teardown issue: ' + (d.detail || d.status));
    document.getElementById('btn-launch').textContent = 'LAUNCH';
    Store.resetMatch();
    renderLLM(Store.strategy); renderReferee(); drawWorld(); drawMomentum();
    setTimeout(() => document.getElementById('overlay').classList.remove('show'), 2000);
  } catch (e) {
    document.getElementById('ov-text').textContent = 'Teardown failed: ' + e;
    setTimeout(() => document.getElementById('overlay').classList.remove('show'), 3000);
  }
});

// ---- WebSocket ----
const wsDot = document.getElementById('ws-dot'), wsState = document.getElementById('ws-state');
function connectWS() {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => { wsDot.className = 'dot on'; wsState.textContent = 'connected'; };
  ws.onclose = () => { wsDot.className = 'dot off'; wsState.textContent = 'reconnecting…'; setTimeout(connectWS, 1500); };
  ws.onerror = () => ws.close();
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'state') {
      Store.set('supervisorState', msg.data);
      updateLaunchButton(msg.data);
    } else if (msg.type === 'health') {
      Store.set('health', msg.data);
      if (Store.activeWorkflow === 'home') renderHomepage();
    } else if (msg.file === 'Worldstate.json') {
      onWorld(msg.data);
    } else if (msg.file === 'current_strategy.json') {
      onStrategy(msg.data);
    }
  };
}
function updateLaunchButton(state) {
  const btn = document.getElementById('btn-launch');
  if (state === 'running') btn.textContent = 'RUNNING';
  else if (state === 'idle') btn.textContent = 'LAUNCH';
  else if (state === 'launching' || state === 'tearing_down') btn.textContent = state.toUpperCase() + '…';
}
connectWS();
fetch('http://localhost:8080/').then(() => document.getElementById('gz-dot').className = 'dot on').catch(() => document.getElementById('gz-dot').className = 'dot off');

// ---- data handlers ----
function onWorld(d) {
  Store.world = d;
  const ms = d.match_state || {}, ts = d.tactical_score || {};
  document.getElementById('t-status').textContent = (ms.status || '—');
  document.getElementById('t-blue').textContent = ms.blue ?? 0;
  document.getElementById('t-red').textContent = ms.red ?? 0;
  document.getElementById('t-poss').textContent = ts.ball_possession_fact ? 'POS ' + ts.ball_possession_fact : '';
  document.getElementById('t-fact').textContent = ts.fact_label || '';
  const now = performance.now() / 1000;
  if (Store.gameStart === null && ts.current_numerical_score !== undefined) Store.gameStart = now;
  if (ts.current_numerical_score !== undefined) {
    Store.momentum.push({t: now - Store.gameStart, s: ts.current_numerical_score});
    if (Store.momentum.length > 1200) Store.momentum.shift();
  }
  processMatch(ms, now - (Store.gameStart || 0));
  drawWorld(); drawMomentum();
}
function onStrategy(d) {
  Store.strategy = d;
  document.getElementById('t-run').textContent = `lat: ${d.latency_ms != null ? d.latency_ms + 'ms' : '—'} | model: ${d.model_name || '—'}`;
  renderLLM(d); drawWorld();
}
function processMatch(ms, t) {
  const st = ms.status || 'playing';
  if (st === 'goal' && Store.lastStatus !== 'goal') {
    const team = (ms.blue > ms.red) ? 'blue' : 'red';
    addEv(t, 'GOAL', `Blue ${ms.blue} – ${ms.red} Red`, '#4caf50');
    addEv(t, 'KICKOFF', (team === 'blue' ? 'red' : 'blue') + ' restart', '#ff9800');
  }
  if (st === 'foul_penalty' && Store.lastStatus !== 'foul_penalty' && ms.foul) {
    const f = ms.foul, ty = (f.type || '').includes('block') ? 'BLOCK' : (f.type || 'foul').toUpperCase();
    addEv(t, 'FOUL', `${ty} ${f.offender || ''}`, '#FF4136');
  }
  if (st === 'ball_out' && Store.lastStatus !== 'ball_out') addEv(t, 'BALL OUT', `${ms.foul?.offender || ''} → ${ms.restart_team || ''}`, '#ff9800');
  if (st === 'goal_kick' && Store.lastStatus !== 'goal_kick') addEv(t, 'GOAL KICK', ms.restart_team || '', '#ff9800');
  if (st === 'corner_kick_in' && Store.lastStatus !== 'corner_kick_in') addEv(t, 'CORNER', ms.restart_team || '', '#ff9800');
  if (st === 'playing' && Store.lastStatus !== 'playing' && !ms.foul) addEv(t, 'BALL FREE', '', '#4caf50');
  Store.lastStatus = st; renderReferee();
}
function addEv(t, type, detail, color) {
  Store.matchEvents.push({t, type, detail, color});
  if (Store.matchEvents.length > 50) Store.matchEvents.shift();
}
function renderReferee() {
  const b = document.getElementById('ref-body'); if (!b) return;
  if (!Store.matchEvents.length) { b.innerHTML = '<div class="empty">No events</div>'; return; }
  b.innerHTML = Store.matchEvents.slice(-8).reverse().map(e =>
    `<div class="ev"><span class="t">${e.t.toFixed(1)}s</span><span class="ty" style="color:${e.color}">${e.type}</span><span class="d">${e.detail || ''}</span></div>`).join('');
}
function renderLLM(d) {
  const b = document.getElementById('llm-body'); if (!b) return;
  const a = d.assignments || {};
  const rows = Object.keys(a).map(bot => {
    const r = a[bot] || {};
    const tgt = (r.action === 'Kick' || r.action === 'Move') ? `→ (${r.x?.toFixed(2)}, ${r.y?.toFixed(2)})` : '';
    return `<div class="a-row"><span class="bot">${bot}</span> <span class="act">${r.action || ''}</span> <span style="color:var(--text-dim)">[${r.role || ''}]</span> <span class="tgt">${tgt}</span></div>`;
  }).join('');
  b.innerHTML = rows + `<div class="meta">model: ${d.model_name || '—'} · latency: ${d.latency_ms != null ? d.latency_ms + 'ms' : '—'}</div>`;
}

// ---- canvases (ported from first-shot index.html; read Store.*) ----
function fitCanvas(c) {
  if (!c) return 0;
  const r = c.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(2, r.width * dpr), h = Math.max(2, r.height * dpr);
  c.width = w; c.height = h;
  return dpr;
}
function drawWorld() {
  const c = document.getElementById('c-world'); if (!c) return;
  const dpr = fitCanvas(c); if (!dpr) return;
  const W = c.width, H = c.height, ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  const mx = 40 * dpr, my = 30 * dpr, sx = (W - 2 * mx) / (FX_MAX - FX_MIN), sy = (H - 2 * my) / (FY_MAX - FY_MIN),
        s = Math.max(1, Math.min(sx, sy)),
        ox = mx + (W - 2 * mx - s * (FX_MAX - FX_MIN)) / 2, oy = my + (H - 2 * my - s * (FY_MAX - FY_MIN)) / 2;
  const X = x => ox + (x - FX_MIN) * s, Y = y => oy + (FY_MAX - y) * s;
  const R = r => Math.max(0.5, r);
  ctx.strokeStyle = '#5a6070'; ctx.lineWidth = 1.5 * dpr;
  ctx.strokeRect(X(FX_MIN), Y(FY_MAX), s * (FX_MAX - FX_MIN), s * (FY_MAX - FY_MIN));
  ctx.setLineDash([4 * dpr, 4 * dpr]); ctx.strokeStyle = '#444';
  ctx.beginPath(); ctx.moveTo(X(0), Y(FY_MIN)); ctx.lineTo(X(0), Y(FY_MAX)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(X(FX_MIN), Y(0)); ctx.lineTo(X(FX_MAX), Y(0)); ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath(); ctx.arc(X(0), Y(0), R(1.5 * s), 0, 2 * Math.PI); ctx.strokeStyle = '#444'; ctx.stroke();
  ctx.strokeStyle = '#5a6070';
  for (const [gx, dir] of [[FX_MAX, 1], [FX_MIN, -1]]) {
    ctx.strokeRect(Math.min(X(gx), X(gx - dir * GOAL_AREA_X)), Y(GOAL_AREA_Y), s * GOAL_AREA_X, s * 2 * GOAL_AREA_Y);
    ctx.fillStyle = gx > 0 ? '#e74c3c' : '#3498db';
    ctx.beginPath(); ctx.arc(X(gx), Y(GOAL_Y), R(3 * dpr), 0, 2 * Math.PI); ctx.fill();
    ctx.beginPath(); ctx.arc(X(gx), Y(-GOAL_Y), R(3 * dpr), 0, 2 * Math.PI); ctx.fill();
  }
  const ents = Store.world.entities || {}, a = Store.strategy.assignments || {};
  for (const bot of Object.keys(a)) {
    const e = ents[bot]; if (!e) continue;
    const asg = a[bot];
    if (asg.action === 'Move' || asg.action === 'Kick') {
      ctx.strokeStyle = asg.action === 'Kick' ? '#ffeb3b' : '#9ad';
      ctx.lineWidth = 2 * dpr; ctx.setLineDash([6 * dpr, 4 * dpr]);
      ctx.beginPath(); ctx.moveTo(X(e.x), Y(e.y)); ctx.lineTo(X(asg.x), Y(asg.y)); ctx.stroke();
      ctx.setLineDash([]);
      const ang = Math.atan2(Y(asg.y) - Y(e.y), X(asg.x) - X(e.x));
      ctx.beginPath(); ctx.moveTo(X(asg.x), Y(asg.y));
      ctx.lineTo(X(asg.x) - R(6 * dpr) * Math.cos(ang - .4), Y(asg.y) - R(6 * dpr) * Math.sin(ang - .4));
      ctx.lineTo(X(asg.x) - R(6 * dpr) * Math.cos(ang + .4), Y(asg.y) - R(6 * dpr) * Math.sin(ang + .4));
      ctx.closePath();
      ctx.fillStyle = asg.action === 'Kick' ? '#ffeb3b' : '#9ad'; ctx.fill();
    }
  }
  for (const [name, e] of Object.entries(ents)) {
    if (name === 'soccer_ball') {
      ctx.fillStyle = '#fff';
      ctx.beginPath(); ctx.arc(X(e.x), Y(e.y), R(4 * dpr), 0, 2 * Math.PI); ctx.fill();
      ctx.fillStyle = '#888'; ctx.font = `${9 * dpr}px sans-serif`;
      ctx.fillText('ball', X(e.x) + 6 * dpr, Y(e.y) - 4 * dpr);
    } else {
      const blue = name.startsWith('blue');
      ctx.fillStyle = blue ? '#3498db' : '#e74c3c';
      ctx.beginPath(); ctx.arc(X(e.x), Y(e.y), R(7 * dpr), 0, 2 * Math.PI); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = `bold ${9 * dpr}px sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(name.replace(/blue_|red_/, ''), X(e.x), Y(e.y));
      ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
    }
  }
}
function drawMomentum() {
  const c = document.getElementById('c-mom'); if (!c) return;
  const dpr = fitCanvas(c); if (!dpr) return;
  const W = c.width, H = c.height, ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#11141b'; ctx.fillRect(0, 0, W, H);
  const momentum = Store.momentum;
  if (momentum.length < 2) {
    ctx.fillStyle = '#555'; ctx.font = `${11 * dpr}px sans-serif`;
    ctx.fillText('collecting…', 12 * dpr, 20 * dpr); return;
  }
  const tMax = Math.max(120, momentum[momentum.length - 1].t), pad = 30 * dpr,
        X = t => pad + (t / tMax) * (W - 2 * pad);
  let sMin = Math.min(...momentum.map(m => m.s)), sMax = Math.max(...momentum.map(m => m.s));
  if (sMax - sMin < 2) { sMax += 1; sMin -= 1; }
  const Y = s => H - pad - ((s - sMin) / (sMax - sMin)) * (H - 2 * pad);
  if (sMin < 0 && sMax > 0) {
    ctx.strokeStyle = '#333'; ctx.setLineDash([3 * dpr, 3 * dpr]);
    ctx.beginPath(); ctx.moveTo(pad, Y(0)); ctx.lineTo(W - pad, Y(0)); ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.strokeStyle = '#1db954'; ctx.lineWidth = 2 * dpr;
  ctx.beginPath();
  momentum.forEach((m, i) => { const x = X(m.t), y = Y(m.s); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke();
  for (const ev of Store.matchEvents) {
    if (ev.t > tMax) continue;
    ctx.fillStyle = ev.color;
    ctx.beginPath(); ctx.arc(X(ev.t), pad, Math.max(1, 4 * dpr), 0, 2 * Math.PI); ctx.fill();
  }
  ctx.fillStyle = '#888'; ctx.font = `${10 * dpr}px sans-serif`;
  ctx.fillText('score', 6 * dpr, 14 * dpr);
  ctx.fillText(tMax.toFixed(0) + 's', W - 30 * dpr, H - 4 * dpr);
}
window.addEventListener('resize', () => { drawWorld(); drawMomentum(); });

// ---- assistant chat (mode B copilot) ----
// chat history: {role:'user'|'bot', text, meta} — persists across workflow switches
if (!Store.chat) Store.chat = [];

function renderAssistantChat() {
  const textPane = document.getElementById('text-pane');
  const models = (Store.catalog.models || []);
  const modelOptions = models.map(m =>
    `<option value="${m}" ${m === 'qwen2.5:7b' ? 'selected' : ''}>${m}</option>`).join('');
  textPane.innerHTML = `
    <h2>Assistant</h2>
    <p>${WF['know-assistant'].desc}</p>
    <div id="chat-messages" class="chat-messages"></div>
    <div class="chat-input-row">
      <select id="chat-model">${modelOptions}</select>
      <input id="chat-input" type="text" placeholder="Ask anything about ROS2K… (e.g. 'Warum bleibt der Goalie im Tor?')" autocomplete="off">
      <button id="chat-send">SEND</button>
    </div>`;
  renderChatMessages();
  document.getElementById('chat-send').addEventListener('click', sendAssistantMsg);
  document.getElementById('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendAssistantMsg();
  });
}

function renderChatMessages() {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  if (!Store.chat.length) {
    box.innerHTML = '<div class="chat-empty">No messages yet — ask something.</div>';
    return;
  }
  box.innerHTML = Store.chat.map(m => `
    <div class="chat-msg ${m.role}">
      <div class="chat-bubble">${m.text.replace(/</g, '&lt;')}</div>
      ${m.meta ? `<div class="chat-meta">${m.meta}</div>` : ''}
    </div>`).join('');
  box.scrollTop = box.scrollHeight;
}

async function sendAssistantMsg() {
  const input = document.getElementById('chat-input');
  const q = input.value.trim();
  if (!q) return;
  const model = document.getElementById('chat-model').value;
  Store.chat.push({role: 'user', text: q});
  Store.chat.push({role: 'bot', text: '…thinking…'});
  renderChatMessages();
  input.value = '';
  try {
    const r = await fetch(`${BACKEND}/assistant/ask?q=${encodeURIComponent(q)}&model=${encodeURIComponent(model)}`);
    const d = await r.json();
    Store.chat.pop(); // remove placeholder
    if (d.answer !== undefined) {
      Store.chat.push({role: 'bot', text: d.answer, meta: `${d.model} · ${d.elapsed_ms}ms`});
    } else {
      Store.chat.push({role: 'bot', text: 'Error: ' + (d.detail || 'unknown'), meta: 'failed'});
    }
  } catch (e) {
    Store.chat.pop();
    Store.chat.push({role: 'bot', text: 'Request failed: ' + e, meta: 'failed'});
  }
  renderChatMessages();
}

// ---- init ----
selectWorkflow('home');
loadCatalog();
loadHomeData();
