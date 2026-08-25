import json, os, sys, time, bisect, argparse
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from collections import deque
from matplotlib.lines import Line2D

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    # Stub so the class definition doesn't fail when rclpy is unavailable
    class Node:
        pass

plt.rcParams['toolbar'] = 'None'
BASE_DIR = os.getenv('ROS2K_WS', '.')
STRAT_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")
WAYPOINTS_PATH = os.path.join(BASE_DIR, "shared_state", "waypoints.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

latest_world_state = {}
latest_tactical_score = {}
latest_match_state = {}
last_wp_mtime = 0
current_waypoints = []

# Momentum history tracking
momentum_history = deque(maxlen=1200)  # 120s at 10Hz
game_start_time = None
goal_events = []
foul_events = []
referee_events = deque(maxlen=50)  # Recent referee decisions
last_match_status = "playing"

MAX_BOTS = 6
MAX_ARROWS = 6
MAX_REF_ROWS = 8

# Annotation markers for momentum timeline (set by main_replay, read by update_figure)
# List of (t_seconds, annotation_index) tuples
annotation_markers = []

_artists = {}
_initialized = False


class VisualizerROSNode(Node):
    def __init__(self):
        super().__init__('r2k_visualizer_node')
        self.sub_pos = self.create_subscription(String, '/world_positions', self.positions_callback, 10)
        self.sub_score = self.create_subscription(String, '/tactical_score', self.score_callback, 10)
        self.sub_match = self.create_subscription(String, '/match_state', self.match_callback, 10)

    def positions_callback(self, msg):
        global latest_world_state
        try: latest_world_state = json.loads(msg.data)
        except: pass

    def score_callback(self, msg):
        global latest_tactical_score, momentum_history, game_start_time
        try:
            latest_tactical_score = json.loads(msg.data)
            if game_start_time is None:
                game_start_time = time.time()
            elapsed = time.time() - game_start_time
            score = latest_tactical_score.get('current_numerical_score', 0.0)
            momentum_history.append((elapsed, score))
        except: pass

    def match_callback(self, msg):
        global latest_match_state
        try:
            latest_match_state = json.loads(msg.data)
            elapsed = time.time() - game_start_time if game_start_time else 0
            process_match_state(latest_match_state, elapsed)
        except: pass


def process_match_state(match_data, t_sim):
    """Detect referee status transitions and populate event lists.
    Extracted from match_callback so both live mode and replay mode can call it.
    Uses t_sim (timestamp) instead of time.time() - game_start_time.
    """
    global goal_events, foul_events, referee_events, last_match_status
    current_status = match_data.get('status', 'playing')

    if current_status == 'goal' and last_match_status != 'goal':
        blue_goals = match_data.get('blue', 0)
        red_goals = match_data.get('red', 0)
        team = "blue" if blue_goals > red_goals else "red"
        goal_events.append((t_sim, team, blue_goals, red_goals))
        referee_events.append((t_sim, "GOAL", f"Blue {blue_goals} - {red_goals} Red", "#4caf50"))
        kicking = "red" if team == "blue" else "blue"
        referee_events.append((t_sim, "KICKOFF", kicking.capitalize(), "#ff9800"))

    if match_data.get('foul') and current_status == 'foul_penalty' and last_match_status != 'foul_penalty':
        foul_data = match_data['foul']
        foul_type = foul_data.get('type', 'unknown')
        offender = foul_data.get('offender', 'unknown')
        team = "blue" if "blue" in offender else "red"
        foul_events.append((t_sim, team, foul_type))
        short_foul = "BLOCK" if "block" in foul_type else foul_type.upper()
        referee_events.append((t_sim, "FOUL", f"{short_foul} {offender}", "#FF4136"))

    if current_status == 'ball_out' and last_match_status != 'ball_out':
        restart_team = match_data.get('restart_team', 'unknown')
        restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
        foul_data = match_data.get('foul')
        offender = foul_data.get('offender', 'unknown') if foul_data else 'unknown'
        referee_events.append((t_sim, "BALL OUT", f"{offender} >> {restart_team_display}", "#ff9800"))

    if current_status == 'goal_kick' and last_match_status != 'goal_kick':
        restart_team = match_data.get('restart_team', 'unknown')
        restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
        referee_events.append((t_sim, "GOAL KICK", restart_team_display, "#ff9800"))

    if current_status == 'corner_kick_in' and last_match_status != 'corner_kick_in':
        restart_team = match_data.get('restart_team', 'unknown')
        restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
        referee_events.append((t_sim, "CORNER", restart_team_display, "#ff9800"))

    if current_status == 'playing' and last_match_status in ('goal', 'goal_kick', 'corner_kick_in'):
        referee_events.append((t_sim, "BALL FREE", "", "#4caf50"))

    last_match_status = current_status


def to_plot(val):
    return (val * 10.0) + 50.0


def init_figure(fig):
    """Create all axes, static elements, and empty dynamic artists ONCE.
    Stores everything in the module-level _artists dict.
    """
    a = {}

    # --- Main pitch area (top) ---
    a['ax_pitch'] = fig.add_axes([0.05, 0.48, 0.65, 0.47])
    a['pitch'] = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100,
                       pitch_color='#1e2a22', line_color='#fafafa')
    a['pitch'].draw(ax=a['ax_pitch'])

    # Ball scatter (single point, white)
    a['ball_scatter'] = a['ax_pitch'].scatter([], [], c='white', s=150, zorder=5, edgecolors='black')

    # Bot scatters — separate per team for color
    a['blue_scatter'] = a['ax_pitch'].scatter([], [], c='#0074D9', s=250, zorder=4, edgecolors='black')
    a['red_scatter'] = a['ax_pitch'].scatter([], [], c='#FF4136', s=250, zorder=4, edgecolors='black')

    # Bot label texts (pre-create MAX_BOTS, show/hide as needed)
    a['bot_labels'] = []
    for i in range(MAX_BOTS):
        txt = a['ax_pitch'].text(0, 0, '', color='white', fontsize=14, weight='bold',
                                 bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=2))
        txt.set_visible(False)
        a['bot_labels'].append(txt)

    # Arrow annotations (pre-create MAX_ARROWS, show/hide)
    a['arrows'] = []
    for i in range(MAX_ARROWS):
        arr = a['ax_pitch'].annotate("", xy=(0, 0), xytext=(0, 0),
                                     arrowprops=dict(arrowstyle="->", color="#ffeb3b",
                                                     lw=2, ls='--', alpha=0.8))
        arr.set_visible(False)
        a['arrows'].append(arr)

    # Waypath polyline (cyan dotted — demo mode calibration path)
    a['waypath_line'], = a['ax_pitch'].plot([], [], color='#00e5ff', lw=1.5,
                                            ls=':', alpha=0.6, marker='o',
                                            markersize=4, markerfacecolor='#00e5ff')
    a['waypath_line'].set_visible(False)

    # --- Momentum sub-panel (bottom, full width) ---
    a['ax_mom'] = fig.add_axes([0.05, 0.05, 0.92, 0.18])
    a['ax_mom'].set_facecolor('#1e2a22')
    a['ax_mom'].set_xlim(0, 120)
    a['ax_mom'].set_ylim(-10, 10)
    a['ax_mom'].set_xlabel('Game Time (s)', color='white', fontsize=9)
    a['ax_mom'].set_ylabel('Score', color='white', fontsize=9)
    a['ax_mom'].set_title('Momentum Timeline (120s)', color='white', fontsize=13, weight='bold')
    a['ax_mom'].tick_params(colors='white', labelsize=8)
    a['ax_mom'].grid(True, alpha=0.2, color='white')
    a['ax_mom'].axhspan(0, 10, facecolor='#0074D9', alpha=0.08, zorder=0)
    a['ax_mom'].axhspan(-10, 0, facecolor='#FF4136', alpha=0.08, zorder=0)

    # Momentum line (single plot, updated each frame)
    a['mom_line'], = a['ax_mom'].plot([], [], color='white', linewidth=1.5, linestyle=':', zorder=2)
    a['ax_mom'].axhline(y=0, color='white', linestyle='--', alpha=0.3, linewidth=0.5)

    # Momentum fill collections (updated via remove+redraw each frame — lightweight on this small axes)
    a['mom_fills'] = []

    # Momentum markers (foul triangles + goal circles) — separate scatters
    a['mom_foul_scatter'] = a['ax_mom'].scatter([], [], marker='v', s=80, zorder=5, alpha=0.8)
    a['mom_goal_scatter'] = a['ax_mom'].scatter([], [], marker='o', s=100, zorder=5, edgecolors='white', linewidths=1.5)
    # Annotation markers (yellow diamonds at top of momentum panel)
    a['mom_annot_scatter'] = a['ax_mom'].scatter([], [], marker='D', s=60, zorder=6,
                                                   color='#ffeb3b', edgecolors='white', linewidths=0.5)

    # Momentum legend (static)
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#0074D9', markersize=6, label='Blue Goal'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF4136', markersize=6, label='Red Goal'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#0074D9', markersize=6, label='Blue Foul'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF4136', markersize=6, label='Red Foul'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#ffeb3b', markersize=5, label='Note'),
    ]
    a['ax_mom'].legend(handles=legend_elements, loc='upper left', fontsize=7,
                       facecolor='#1e2a22', edgecolor='white', labelcolor='white', framealpha=0.9)

    # --- HUD text bar (top) ---
    a['hud_cur'] = fig.text(0.05, 0.94, '', fontsize=15, weight='heavy',
                            bbox=dict(facecolor='black', alpha=0.8, pad=6))
    a['hud_avg'] = fig.text(0.15, 0.94, '', fontsize=15, weight='heavy',
                            bbox=dict(facecolor='black', alpha=0.8, pad=6))
    a['hud_match'] = fig.text(0.50, 0.94, '', fontsize=15, weight='bold', ha='center',
                              bbox=dict(facecolor='black', alpha=0.8, pad=6))

    # --- AI analysis text panel (right top) ---
    a['ax_text'] = fig.add_axes([0.72, 0.50, 0.25, 0.45])
    a['ax_text'].axis('off')
    a['ai_text'] = a['ax_text'].text(0, 0.95, '', color='white', fontsize=12, wrap=True, va='top',
                                     fontfamily='monospace')

    # --- Annotation note panel (right middle, above referee) ---
    a['ax_annot'] = fig.add_axes([0.72, 0.45, 0.25, 0.04])
    a['ax_annot'].axis('off')
    a['ax_annot'].set_title("Note", color='#ffeb3b', fontsize=10, weight='bold', pad=2)
    a['annot_text'] = a['ax_annot'].text(0.02, 0.95, '', color='#ffeb3b', fontsize=9,
                                          wrap=True, va='top', fontfamily='monospace',
                                          transform=a['ax_annot'].transAxes,
                                          bbox=dict(facecolor='#2a1e0a', alpha=0.9,
                                                    edgecolor='#ffeb3b', pad=3,
                                                    boxstyle='round,pad=0.2'))
    a['annot_text'].set_visible(False)

    # --- Referee events panel (right, above momentum) ---
    a['ax_ref'] = fig.add_axes([0.72, 0.26, 0.25, 0.16])
    a['ax_ref'].set_facecolor('#1e2a22')
    a['ax_ref'].axis('off')
    a['ax_ref'].set_title("Referee Decisions", color='#ffeb3b', fontsize=13, weight='bold', pad=4)

    # Kickoff popup (1 text, show/hide)
    a['kickoff_popup'] = a['ax_ref'].text(0.5, 0.90, '', color='#ffeb3b', fontsize=12,
                                          weight='bold', ha='center', va='top',
                                          transform=a['ax_ref'].transAxes,
                                          bbox=dict(facecolor='#2a1e0a', alpha=0.9,
                                                    edgecolor='#ffeb3b', pad=4, boxstyle='round,pad=0.3'))
    a['kickoff_popup'].set_visible(False)

    # "No events" placeholder
    a['no_events'] = a['ax_ref'].text(0.5, 0.5, 'No events yet', color='white', fontsize=11,
                                      ha='center', va='center', alpha=0.5, transform=a['ax_ref'].transAxes)
    a['no_events'].set_visible(True)

    # Referee event rows: MAX_REF_ROWS × 3 text artists (timestamp, type, detail)
    a['ref_rows'] = []
    for i in range(MAX_REF_ROWS):
        ts_txt = a['ax_ref'].text(0.02, 0.85, '', color='#888888', fontsize=9,
                                  fontfamily='monospace', transform=a['ax_ref'].transAxes)
        type_txt = a['ax_ref'].text(0.15, 0.85, '', color='white', fontsize=10,
                                    weight='bold', transform=a['ax_ref'].transAxes)
        detail_txt = a['ax_ref'].text(0.42, 0.85, '', color='white', fontsize=9,
                                      transform=a['ax_ref'].transAxes, clip_on=True)
        for t in (ts_txt, type_txt, detail_txt):
            t.set_visible(False)
        a['ref_rows'].append((ts_txt, type_txt, detail_txt))

    _artists.update(a)
    return _artists


def update_figure(fig, state, score_data, match_data, decision, last_strat_time):
    """Update existing artist data — NO clf(), NO recreation."""
    a = _artists

    # --- Read data ---
    num_score = score_data.get("current_numerical_score", 0.0)
    avg_score = score_data.get("average_numerical_score", 0.0)
    blue_goals = match_data.get("blue", 0)
    red_goals = match_data.get("red", 0)

    score_color = '#4caf50' if num_score >= 0 else '#f44336'
    avg_color = '#4caf50' if avg_score >= 0 else '#f44336'

    # --- HUD text ---
    a['hud_cur'].set_text(f"CUR: {num_score:+.2f}")
    a['hud_cur'].set_color(score_color)
    a['hud_avg'].set_text(f"AVG: {avg_score:+.2f}")
    a['hud_avg'].set_color(avg_color)

    time_since_last_strat = time.time() - last_strat_time if last_strat_time > 0 else 999.9
    status_color = 'white' if time_since_last_strat < 2.0 else 'red'
    lat = decision.get('latency_ms', 0) if decision else 0
    model = decision.get('model_name', 'Waiting...') if decision else 'N/A'
    a['hud_match'].set_text(f"Match: Blue {blue_goals} : {red_goals} Red    |    Lat: {lat}ms    |    AI: {model}")
    a['hud_match'].set_color(status_color)

    # --- Pitch: bots and ball ---
    ents = state.get('entities', {})
    assignments = decision.get("assignments", {}) if decision else {}

    ball_pts = []
    blue_pts = []
    red_pts = []
    bot_label_data = []  # (x, y, text, color)
    blue_names = []
    red_names = []

    for name, p in ents.items():
        if 'x' not in p or 'y' not in p:
            continue
        px, py = to_plot(p['x']), to_plot(p['y'])
        if 'ball' in name:
            ball_pts.append((px, py))
        elif 'blue' in name:
            blue_pts.append((px, py))
            blue_names.append(name)
            bot_num = name.split('_')[-1]
            bot_role = assignments.get(name, {}).get("role", "")
            role_char = bot_role[0].lower() if bot_role else "-"
            bot_label_data.append((px, py, f"{bot_num}-{role_char}", '#0074D9'))
        elif 'red' in name:
            red_pts.append((px, py))
            red_names.append(name)
            bot_num = name.split('_')[-1]
            bot_label_data.append((px, py, bot_num, '#FF4136'))

    # Ball
    if ball_pts:
        a['ball_scatter'].set_offsets(ball_pts)
        a['ball_scatter'].set_visible(True)
    else:
        a['ball_scatter'].set_visible(False)

    # Blue bots
    if blue_pts:
        a['blue_scatter'].set_offsets(blue_pts)
        a['blue_scatter'].set_visible(True)
    else:
        a['blue_scatter'].set_visible(False)

    # Red bots
    if red_pts:
        a['red_scatter'].set_offsets(red_pts)
        a['red_scatter'].set_visible(True)
    else:
        a['red_scatter'].set_visible(False)

    # Bot labels
    for i, label_txt in enumerate(a['bot_labels']):
        if i < len(bot_label_data):
            lx, ly, ltext, lcolor = bot_label_data[i]
            label_txt.set_position((lx + 2.0, ly + 2.0))
            label_txt.set_text(ltext)
            label_txt.set_color(lcolor)
            label_txt.set_visible(True)
        else:
            label_txt.set_visible(False)

    # --- Arrows ---
    arrow_idx = 0
    if decision and "assignments" in decision:
        for bot, action in decision["assignments"].items():
            if bot not in ents:
                continue
            start_p = ents[bot]
            if 'x' not in start_p or 'y' not in start_p:
                continue
            tx, ty = None, None
            if isinstance(action, dict):
                if "x" in action and "y" in action:
                    tx, ty = action["x"], action["y"]
                elif "target_x" in action and "target_y" in action:
                    tx, ty = action["target_x"], action["target_y"]
                elif "target" in action and isinstance(action["target"], dict):
                    t = action["target"]
                    if "x" in t and "y" in t:
                        tx, ty = t["x"], t["y"]
            if tx is not None and ty is not None and arrow_idx < MAX_ARROWS:
                try:
                    sx, sy = to_plot(start_p['x']), to_plot(start_p['y'])
                    ptx, pty = to_plot(float(tx)), to_plot(float(ty))
                    arr = a['arrows'][arrow_idx]
                    arr.set_position((sx, sy))
                    arr.xy = (ptx, pty)
                    arr.set_visible(True)
                    arrow_idx += 1
                except:
                    pass

    # Hide unused arrows
    for i in range(arrow_idx, MAX_ARROWS):
        a['arrows'][i].set_visible(False)

    # --- Waypath polyline (demo mode) ---
    if current_waypoints:
        wp_xs = [to_plot(w['x']) for w in current_waypoints]
        wp_ys = [to_plot(w['y']) for w in current_waypoints]
        a['waypath_line'].set_data(wp_xs, wp_ys)
        a['waypath_line'].set_visible(True)
    else:
        a['waypath_line'].set_visible(False)

    # --- Momentum panel ---
    # Remove old fills
    for fill in a['mom_fills']:
        try:
            fill.remove()
        except:
            pass
    a['mom_fills'] = []

    if momentum_history:
        times = [t for t, s in momentum_history]
        scores = [s for t, s in momentum_history]
        a['mom_line'].set_data(times, scores)

        # Redraw fills (lightweight on this small axes)
        pos_mask = [s >= 0 for s in scores]
        neg_mask = [s < 0 for s in scores]
        if any(pos_mask):
            fill_pos = a['ax_mom'].fill_between(times, scores, 0, where=pos_mask,
                                                color='#0074D9', alpha=0.25, zorder=1)
            a['mom_fills'].append(fill_pos)
        if any(neg_mask):
            fill_neg = a['ax_mom'].fill_between(times, scores, 0, where=neg_mask,
                                                color='#FF4136', alpha=0.25, zorder=1)
            a['mom_fills'].append(fill_neg)
    else:
        a['mom_line'].set_data([], [])

    # Foul markers
    if foul_events:
        foul_x = [ft for ft, _, _ in foul_events]
        foul_y = [0] * len(foul_events)
        foul_colors = ['#0074D9' if t == 'blue' else '#FF4136' for _, t, _ in foul_events]
        a['mom_foul_scatter'].set_offsets(list(zip(foul_x, foul_y)))
        a['mom_foul_scatter'].set_color(foul_colors)
        a['mom_foul_scatter'].set_visible(True)
    else:
        a['mom_foul_scatter'].set_visible(False)

    # Goal markers
    if goal_events:
        goal_x = [gt for gt, _, _, _ in goal_events]
        goal_y = [bg - rg for _, _, bg, rg in goal_events]
        goal_colors = ['#0074D9' if t == 'blue' else '#FF4136' for _, t, _, _ in goal_events]
        a['mom_goal_scatter'].set_offsets(list(zip(goal_x, goal_y)))
        a['mom_goal_scatter'].set_color(goal_colors)
        a['mom_goal_scatter'].set_visible(True)
    else:
        a['mom_goal_scatter'].set_visible(False)

    # Annotation markers (yellow diamonds at top of momentum panel)
    if annotation_markers:
        annot_x = [t for t, _ in annotation_markers]
        annot_y = [9.5] * len(annot_x)  # near top of the -10..+10 y range
        a['mom_annot_scatter'].set_offsets(list(zip(annot_x, annot_y)))
        a['mom_annot_scatter'].set_visible(True)
    else:
        a['mom_annot_scatter'].set_visible(False)

    # --- AI analysis text ---
    if decision and "analysis" in decision:
        analysis = decision.get('analysis', '')
        oracle = decision.get('oracle', '')
        if not isinstance(oracle, str):
            oracle = "(invalid - JSON in oracle field)"
        if not isinstance(analysis, str):
            analysis = "(invalid - JSON in analysis field)"
        a['ai_text'].set_text(f"### ANALYSIS ###\n\n{analysis}\n\n### ORACLE ###\n\n{oracle}")
    else:
        a['ai_text'].set_text("FAST EXECUTION MODE\n\n(No explanation requested)")

    # --- Referee panel ---
    kickoff_active = match_data.get('status') == 'goal'
    if kickoff_active:
        scoring = "blue" if blue_goals > red_goals else "red"
        kicking = "red" if scoring == "blue" else "blue"
        a['kickoff_popup'].set_text(f"KICKOFF {kicking.capitalize()}")
        a['kickoff_popup'].set_visible(True)
    else:
        a['kickoff_popup'].set_visible(False)

    recent_events = list(referee_events)[-MAX_REF_ROWS:] if referee_events else []
    a['no_events'].set_visible(not recent_events and not kickoff_active)

    y_start = 0.58 if kickoff_active else 0.85
    for i, (ts_txt, type_txt, detail_txt) in enumerate(a['ref_rows']):
        if i < len(recent_events):
            event_time, event_type, event_detail, event_color = recent_events[i]
            mins = int(event_time // 60)
            secs = event_time % 60
            timestamp = f"[{mins:02d}:{secs:04.1f}]"
            y_pos = y_start - i * 0.14
            ts_txt.set_position((0.02, y_pos))
            ts_txt.set_text(timestamp)
            type_txt.set_position((0.15, y_pos))
            type_txt.set_text(f"{event_type}:")
            type_txt.set_color(event_color)
            detail_txt.set_position((0.42, y_pos))
            detail_txt.set_text(event_detail)
            for t in (ts_txt, type_txt, detail_txt):
                t.set_visible(True)
        else:
            for t in (ts_txt, type_txt, detail_txt):
                t.set_visible(False)

    # --- Trigger redraw ---
    fig.canvas.draw_idle()
    fig.canvas.flush_events()


def _load_jsonl(path):
    if not os.path.exists(path):
        return []
    records = []
    with open(path) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return records


def _parse_llm_decision(rec):
    """Extract assignments/analysis/oracle/latency from an llm_trace record."""
    raw = rec.get("raw_response", "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    data = {}
    if start >= 0 and end >= 0:
        try:
            data = json.loads(raw[start:end + 1])
        except Exception:
            pass
    return {
        "assignments": data.get("assignments", {}),
        "analysis": data.get("analysis", ""),
        "oracle": data.get("oracle", ""),
        "latency_ms": rec.get("latency_ms", 0),
        "model": rec.get("model", ""),
    }


def load_replay_data(run_id):
    """Load world_trace, llm_trace, and annotations for a run_id.
    Returns (world_recs, llm_recs, annot_recs) or None if world_trace missing.
    """
    world_path = os.path.join(LOG_DIR, f"world_trace_{run_id}.jsonl")
    llm_path = os.path.join(LOG_DIR, f"llm_trace_{run_id}.jsonl")
    annot_path = os.path.join(LOG_DIR, f"annotations_{run_id}.jsonl")

    world_recs = _load_jsonl(world_path)
    if not world_recs:
        print(f"❌ No world_trace found at {world_path}")
        return None

    llm_recs = _load_jsonl(llm_path)
    annot_recs = _load_jsonl(annot_path)

    print(f"Replay: {run_id}")
    print(f"  World trace: {len(world_recs)} records ({world_path})")
    print(f"  LLM trace:   {len(llm_recs)} records ({llm_path})")
    print(f"  Annotations: {len(annot_recs)} records ({annot_path})")

    return world_recs, llm_recs, annot_recs


def find_latest_llm_before(llm_recs, llm_times, t_norm):
    """Find the most recent LLM record at or before t_norm. Returns (idx, decision_dict) or (-1, {})."""
    idx = bisect.bisect_right(llm_times, t_norm) - 1
    if idx < 0:
        return -1, {}
    return idx, _parse_llm_decision(llm_recs[idx])


def _rebuild_state_to(world_recs, world_times, target_t):
    """Replay all world frames from 0 to target_t to repopulate momentum,
    goal_events, foul_events, referee_events, and last_match_status.
    Called on annotation jump so the panels reflect everything up to the jump point.
    """
    global momentum_history, goal_events, foul_events, referee_events, last_match_status
    momentum_history.clear()
    goal_events.clear()
    foul_events.clear()
    referee_events.clear()
    last_match_status = "playing"
    for i in range(len(world_recs)):
        if world_times[i] > target_t:
            break
        w = world_recs[i]
        w_t = world_times[i]
        match_data = w.get("match_state", {})
        score_data = w.get("tactical_score", {})
        process_match_state(match_data, w_t)
        num_score = score_data.get("current_numerical_score", 0.0)
        momentum_history.append((w_t, num_score))


def main_replay(run_id, speed=1.0, start_time=0.0, nav=True):
    """Replay a saved match from trace files — no ROS 2 required.

    Nav controls (f/b/SPACE/q) are always enabled in replay mode.
    """
    global game_start_time, momentum_history, goal_events, foul_events
    global referee_events, last_match_status, _initialized

    data = load_replay_data(run_id)
    if data is None:
        sys.exit(1)
    world_recs, llm_recs, annot_recs = data

    # Normalize timestamps: seconds from first world_trace record.
    # Use t_wall (wall-clock) as the common timeline — sim-time (t) is 0.0
    # in all existing traces (libgazebo_ros_init.so was added but not yet
    # rebuilt/deployed when these traces were recorded).
    t0 = world_recs[0].get("t_wall", world_recs[0].get("t", time.time()))
    world_times = [r.get("t_wall", r.get("t", 0)) - t0 for r in world_recs]
    llm_times = [r.get("t", 0) - t0 for r in llm_recs]
    annot_times = [a.get("t_wall", 0) - t0 for a in annot_recs]

    match_duration = world_times[-1] if world_times else 0.0
    print(f"  Log: {run_id}")
    print(f"  Duration: {match_duration:.1f}s | Speed: {speed:.1f}x")

    if not annot_recs:
        print("  ⚠️ No annotations in this run — f/b have nothing to jump to.")
    else:
        print(f"  📝 {len(annot_recs)} annotations available")
    print("  Controls: ←/→ seek ±5s, SPACE=pause/resume, "
          "f=next annotation, b=prev annotation, q=quit (ctrl+f=fullscreen)")

    # Pre-parse all LLM decisions so we don't re-parse on every frame
    llm_decisions = [_parse_llm_decision(r) for r in llm_recs]

    # Pre-sort annotations by time for overlay + navigation
    annot_sorted = sorted(zip(annot_times, annot_recs)) if annot_recs else []
    annot_times_sorted = [a_t for a_t, _ in annot_sorted]

    # Clear matplotlib default keybindings that conflict with nav controls
    # (f=fullscreen, b=back). Must be set BEFORE plt.show() so the backend
    # picks up the overrides when it initializes its keypress handler.
    if nav:
        plt.rcParams['keymap.fullscreen'] = ['ctrl+f']
        plt.rcParams['keymap.back'] = ['c']
        plt.rcParams['keymap.forward'] = ['v']

    plt.ion()
    fig = plt.figure(figsize=(16, 9), facecolor='#121212')
    fig.canvas.manager.set_window_title(f"R2K Replay — {run_id}")

    momentum_history.clear()
    goal_events.clear()
    foul_events.clear()
    referee_events.clear()
    last_match_status = "playing"
    game_start_time = 0.0  # relative timeline
    annotation_markers.clear()
    for a_t, a_rec in (annot_sorted if annot_recs else []):
        annotation_markers.append((a_t, a_rec.get("annotation_index", 0)))

    plt.show(block=False)

    w_idx = 0
    llm_idx = -1
    current_decision = {}
    last_strat_time_abs = 0.0
    active_annotation = None
    annot_display_until = 0.0

    # --- Nav mode state ---
    replay_paused = False
    seek_target = None      # timestamp to jump to
    seek_annotation = None  # annotation record to display after jump

    SEEK_STEP = 5.0  # seconds per arrow-key seek

    def on_key(event):
        nonlocal replay_paused, seek_target, seek_annotation

        if event.key == 'q':
            plt.close(fig)
            return

        if event.key == ' ':
            if replay_paused:
                replay_paused = False
                print("▶ Resumed")
            else:
                replay_paused = True
                print("⏸ Paused")
            return

        # Arrow-key seek: jump ±SEEK_STEP seconds (clamped to match duration)
        if event.key in ('right', 'left'):
            cur_t = world_times[w_idx] if w_idx < len(world_times) else 0.0
            match_end = world_times[-1] if world_times else 0.0
            if event.key == 'right':
                seek_target = min(cur_t + SEEK_STEP, match_end)
                print(f"⏩ Seek +{SEEK_STEP:.0f}s -> t={seek_target:.1f}s")
            else:
                seek_target = max(cur_t - SEEK_STEP, 0.0)
                print(f"⏪ Seek -{SEEK_STEP:.0f}s -> t={seek_target:.1f}s")
            seek_annotation = None
            return

        if event.key not in ('f', 'b'):
            return

        if not annot_sorted:
            print("⛔ No annotations in this run")
            return

        cur_t = world_times[w_idx] if w_idx < len(world_times) else 0.0

        if event.key == 'f':
            # Find next annotation strictly after current position.
            # Skip the annotation we're currently on (within seek slack).
            jump_idx = bisect.bisect_right(annot_times_sorted, cur_t + 0.01)
            if jump_idx < len(annot_sorted) and abs(annot_times_sorted[jump_idx] - cur_t) < 0.5:
                jump_idx += 1
            if jump_idx >= len(annot_sorted):
                print("⛔ No more annotations (already at last)")
                return
        else:  # 'b'
            # Find previous annotation strictly before current position.
            # bisect_right - 1 skips the annotation we're currently sitting on
            # (after an f-jump, cur_t lands just past the annotation's world-time).
            jump_idx = bisect.bisect_right(annot_times_sorted, cur_t + 0.01) - 1
            if jump_idx >= 0 and abs(annot_times_sorted[jump_idx] - cur_t) < 0.5:
                jump_idx -= 1
            if jump_idx < 0:
                print("⛔ Already at first annotation")
                return

        a_t, a_rec = annot_sorted[jump_idx]
        comment = a_rec.get("comment", "")
        a_idx = a_rec.get("annotation_index", "?")
        seek_target = a_t
        seek_annotation = a_rec
        replay_paused = True
        print(f"{'⏩' if event.key == 'f' else '⏪'} Annotation #{a_idx + 1} t={a_t:.1f}s: \"{comment}\"")

    if nav:
        fig.canvas.mpl_connect('key_press_event', on_key)

    # Seek to start_time
    if start_time > 0:
        w_idx = bisect.bisect_left(world_times, start_time)
        if w_idx >= len(world_recs):
            w_idx = 0

    wall_start = time.time()
    start_offset = world_times[w_idx] if w_idx < len(world_times) else 0.0

    while plt.fignum_exists(fig.number):
        # Handle seek (f/b jump)
        if seek_target is not None:
            _rebuild_state_to(world_recs, world_times, seek_target)
            w_idx = bisect.bisect_left(world_times, seek_target)
            if w_idx >= len(world_recs):
                w_idx = len(world_recs) - 1
            # Reset clock so playback continues from here when resumed
            start_offset = world_times[w_idx]
            wall_start = time.time()
            active_annotation = seek_annotation
            annot_display_until = float('inf')  # stays visible while paused
            seek_target = None
            seek_annotation = None

        # Advance replay clock (only if not paused)
        if replay_paused:
            replay_clock = world_times[w_idx]
        else:
            real_elapsed = time.time() - wall_start
            replay_clock = start_offset + real_elapsed * speed

        # Advance w_idx to the last record at or before replay_clock
        if not replay_paused:
            while w_idx + 1 < len(world_recs) and world_times[w_idx + 1] <= replay_clock:
                w_idx += 1

        if not replay_paused and w_idx >= len(world_recs) - 1 and replay_clock >= world_times[-1]:
            print(f"\n✅ Replay finished — {match_duration:.1f}s played.")
            break

        w_rec = world_recs[w_idx]
        w_t = world_times[w_idx]

        # Find the latest LLM decision at or before this world frame
        new_llm_idx = bisect.bisect_right(llm_times, w_t) - 1
        if new_llm_idx >= 0 and new_llm_idx != llm_idx:
            llm_idx = new_llm_idx
            current_decision = llm_decisions[llm_idx]
            last_strat_time_abs = w_t
            # Print to terminal for copyable output (matches live mode)
            analysis = current_decision.get("analysis", "")
            oracle = current_decision.get("oracle", "")
            if analysis:
                print(f"[STRATEGY] {analysis}")
            if oracle:
                print(f"[ORACLE]   {oracle}")

        # Check for annotations at this timestamp (natural playback, not jumping)
        if not replay_paused:
            for a_t, a_rec in annot_sorted:
                if a_t <= w_t and a_t > (w_t - 0.5):  # within 0.5s window
                    if active_annotation != a_rec:
                        active_annotation = a_rec
                        annot_display_until = w_t + 5.0  # show for 5s
                        comment = a_rec.get("comment", "")
                        idx_label = a_rec.get("annotation_index", "?")
                        print(f"\n📝 Annotation #{idx_label + 1} (t={w_t:.1f}s): \"{comment}\"")

        # Build state/score/match dicts from world_trace record
        ents = w_rec.get("entities", {})
        match_data = w_rec.get("match_state", {})
        score_data = w_rec.get("tactical_score", {})
        state = {"entities": ents}

        # Process match state transitions (populates goal_events, referee_events, etc.)
        process_match_state(match_data, w_t)

        # Update momentum history from tactical_score (only during natural playback)
        if not replay_paused:
            num_score = score_data.get("current_numerical_score", 0.0)
            momentum_history.append((w_t, num_score))

        if not _initialized:
            init_figure(fig)
            _initialized = True

        # Show/hide annotation note panel
        if active_annotation and w_t <= annot_display_until:
            comment = active_annotation.get("comment", "")
            a_idx = active_annotation.get("annotation_index", "?")
            _artists['annot_text'].set_text(
                f"#{a_idx + 1} t={w_t:.1f}s\n{comment}")
            _artists['annot_text'].set_visible(True)
        else:
            _artists['annot_text'].set_visible(False)

        try:
            update_figure(fig, state, score_data, match_data,
                          current_decision, last_strat_time_abs)
        except Exception as e:
            print(f"[Visualizer render error] {e}", flush=True)

        plt.pause(0.01)

    print("Replay mode exited.")


def main():
    global game_start_time, momentum_history, goal_events, foul_events, referee_events, _initialized

    parser = argparse.ArgumentParser(description="R2K Visualizer (live or replay mode)")
    parser.add_argument("--replay", metavar="RUN_ID", nargs="?", const="", default=None,
                        help="Replay a saved match from trace files (no ROS 2 required). "
                             "Without RUN_ID, defaults to the last game. "
                             "RUN_ID matches the R2K_RUN_ID used during the match.")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Replay playback speed multiplier (default: 1.0 = real time)")
    parser.add_argument("--start", type=float, default=0.0,
                        help="Replay start time in seconds from match start (default: 0.0)")
    parser.add_argument("--live", action="store_true",
                        help="Run in live mode (subscribes to live ROS 2 topics). "
                             "Without this flag, defaults to replaying the last saved match.")
    parser.add_argument("--nav", action="store_true",
                        help=argparse.SUPPRESS)  # deprecated: nav is always on in replay mode
    args = parser.parse_args()

    # Default behavior (no --replay, no --live): replay the last saved match.
    # launch_r2k.sh passes --live explicitly for the live path.
    if not args.live:
        run_id = args.replay
        if not run_id:
            # Default to last game: newest world_trace_* file
            traces = sorted(
                [f for f in os.listdir(LOG_DIR) if f.startswith("world_trace_")],
                key=lambda f: os.path.getmtime(os.path.join(LOG_DIR, f)),
                reverse=True,
            )
            if not traces:
                print("❌ No saved matches found in logs/. Run a match first "
                      "(or use --live for live mode).")
                sys.exit(1)
            run_id = traces[0].replace("world_trace_", "").replace(".jsonl", "")
            print(f"Replaying last game: {run_id}")
        main_replay(run_id, speed=args.speed, start_time=args.start, nav=True)
        return

    if not HAS_ROS2:
        print("❌ rclpy not available. Use --replay RUN_ID to replay a saved match.")
        sys.exit(1)

    print("Starting Single-Threaded R2K Visualizer (blitted mode)...")
    rclpy.init(args=None)
    node = VisualizerROSNode()

    plt.ion()
    fig = plt.figure(figsize=(16, 9), facecolor='#121212')

    game_start_time = time.time()
    momentum_history.clear()
    goal_events.clear()
    foul_events.clear()
    referee_events.clear()

    plt.show(block=False)

    last_strat_mtime = 0
    current_decision = {}
    last_strat_time_abs = 0.0

    while plt.fignum_exists(fig.number):
        rclpy.spin_once(node, timeout_sec=0.001)

        render_needed = False
        state_copy = dict(latest_world_state)
        score_copy = dict(latest_tactical_score)
        match_copy = dict(latest_match_state)

        if state_copy:
            render_needed = True

        if os.path.exists(STRAT_PATH):
            try:
                strat_mtime = os.path.getmtime(STRAT_PATH)
                if strat_mtime > last_strat_mtime:
                    last_strat_mtime = strat_mtime
                    with open(STRAT_PATH, 'r') as f:
                        current_decision = json.load(f)
                        last_strat_time_abs = time.time()
                        render_needed = True
            except: pass

        global last_wp_mtime, current_waypoints
        if os.path.exists(WAYPOINTS_PATH):
            try:
                wp_mtime = os.path.getmtime(WAYPOINTS_PATH)
                if wp_mtime > last_wp_mtime:
                    last_wp_mtime = wp_mtime
                    with open(WAYPOINTS_PATH, 'r') as f:
                        wp_data = json.load(f)
                    current_waypoints = wp_data.get("waypoints", [])
                    render_needed = True
            except: pass

        if render_needed:
            if not _initialized:
                init_figure(fig)
                _initialized = True
            try:
                update_figure(fig, state_copy, score_copy, match_copy,
                              current_decision, last_strat_time_abs)
            except Exception as e:
                print(f"[Visualizer render error] {e}", flush=True)

        plt.pause(0.01)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()