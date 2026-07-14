import json, os, sys, time
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque
from matplotlib.lines import Line2D

plt.rcParams['toolbar'] = 'None'
BASE_DIR = os.getenv('ROS2K_WS', '.')
STRAT_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")

latest_world_state = {}
latest_tactical_score = {}
latest_match_state = {}

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
        global latest_match_state, goal_events, foul_events, referee_events, last_match_status
        try:
            latest_match_state = json.loads(msg.data)
            current_status = latest_match_state.get('status', 'playing')

            # Track goal events
            if current_status == 'goal' and last_match_status != 'goal':
                elapsed = time.time() - game_start_time if game_start_time else 0
                blue_goals = latest_match_state.get('blue', 0)
                red_goals = latest_match_state.get('red', 0)
                team = "blue" if blue_goals > red_goals else "red"
                goal_events.append((elapsed, team, blue_goals, red_goals))
                referee_events.append((elapsed, "GOAL", f"Blue {blue_goals} - {red_goals} Red", "#4caf50"))
                kicking = "red" if team == "blue" else "blue"
                referee_events.append((elapsed, "KICKOFF", kicking.capitalize(), "#ff9800"))

            # Track foul events
            if latest_match_state.get('foul') and current_status == 'foul_penalty' and last_match_status != 'foul_penalty':
                elapsed = time.time() - game_start_time if game_start_time else 0
                foul_data = latest_match_state['foul']
                foul_type = foul_data.get('type', 'unknown')
                offender = foul_data.get('offender', 'unknown')
                team = "blue" if "blue" in offender else "red"
                foul_events.append((elapsed, team, foul_type))
                short_foul = "BLOCK" if "block" in foul_type else foul_type.upper()
                referee_events.append((elapsed, "FOUL", f"{short_foul} {offender}", "#FF4136"))

            # Track ball-out events (sideline with known offender)
            if current_status == 'ball_out' and last_match_status != 'ball_out':
                elapsed = time.time() - game_start_time if game_start_time else 0
                restart_team = latest_match_state.get('restart_team', 'unknown')
                restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
                foul_data = latest_match_state.get('foul')
                offender = foul_data.get('offender', 'unknown') if foul_data else 'unknown'
                referee_events.append((elapsed, "BALL OUT", f"{offender} >> {restart_team_display}", "#ff9800"))

            # Track goal kick transitions
            if current_status == 'goal_kick' and last_match_status != 'goal_kick':
                elapsed = time.time() - game_start_time if game_start_time else 0
                restart_team = latest_match_state.get('restart_team', 'unknown')
                restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
                referee_events.append((elapsed, "GOAL KICK", restart_team_display, "#ff9800"))

            # Track corner kick-in transitions
            if current_status == 'corner_kick_in' and last_match_status != 'corner_kick_in':
                elapsed = time.time() - game_start_time if game_start_time else 0
                restart_team = latest_match_state.get('restart_team', 'unknown')
                restart_team_display = restart_team.capitalize() if restart_team in ('blue', 'red') else restart_team
                referee_events.append((elapsed, "CORNER", restart_team_display, "#ff9800"))

            # Ball free
            if current_status == 'playing' and last_match_status in ('goal', 'goal_kick', 'corner_kick_in'):
                elapsed = time.time() - game_start_time if game_start_time else 0
                referee_events.append((elapsed, "BALL FREE", "", "#4caf50"))

            last_match_status = current_status
        except: pass


def to_plot(val):
    return (val * 10.0) + 50.0


def init_figure(fig):
    """Create all axes, static elements, and empty dynamic artists ONCE.
    Stores everything in the module-level _artists dict.
    """
    a = {}

    # --- Main pitch area (top) ---
    a['ax_pitch'] = fig.add_axes([0.05, 0.30, 0.65, 0.65])
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

    # --- Momentum sub-panel (bottom) ---
    a['ax_mom'] = fig.add_axes([0.05, 0.05, 0.65, 0.20])
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

    # Momentum legend (static)
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#0074D9', markersize=6, label='Blue Goal'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF4136', markersize=6, label='Red Goal'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#0074D9', markersize=6, label='Blue Foul'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF4136', markersize=6, label='Red Foul'),
    ]
    a['ax_mom'].legend(handles=legend_elements, loc='upper left', fontsize=7,
                       facecolor='#1e2a22', edgecolor='white', labelcolor='white', framealpha=0.9)

    # --- HUD text bar (top) ---
    a['hud_cur'] = fig.text(0.05, 0.94, '', fontsize=15, weight='heavy',
                            bbox=dict(facecolor='black', alpha=0.8, pad=6))
    a['hud_avg'] = fig.text(0.15, 0.94, '', fontsize=15, weight='heavy',
                            bbox=dict(facecolor='black', alpha=0.8, pad=6))
    a['hud_mom'] = fig.text(0.25, 0.94, '', fontsize=15, weight='heavy',
                            bbox=dict(facecolor='black', alpha=0.8, pad=6))
    a['hud_match'] = fig.text(0.50, 0.94, '', fontsize=15, weight='bold', ha='center',
                              bbox=dict(facecolor='black', alpha=0.8, pad=6))

    # --- AI analysis text panel (right top) ---
    a['ax_text'] = fig.add_axes([0.72, 0.30, 0.25, 0.65])
    a['ax_text'].axis('off')
    a['ai_text'] = a['ax_text'].text(0, 0.95, '', color='white', fontsize=12, wrap=True, va='top',
                                     fontfamily='monospace')

    # --- Referee events panel (right bottom) ---
    a['ax_ref'] = fig.add_axes([0.72, 0.05, 0.25, 0.20])
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
    momentum_30s = score_data.get("momentum_30s", 0.0)
    momentum_trend = score_data.get("momentum_trend", "stable")
    blue_goals = match_data.get("blue", 0)
    red_goals = match_data.get("red", 0)

    score_color = '#4caf50' if num_score >= 0 else '#f44336'
    avg_color = '#4caf50' if avg_score >= 0 else '#f44336'
    trend_colors = {
        "ascending": "#4caf50", "improving": "#8bc34a", "stable": "#ffeb3b",
        "declining": "#ff9800", "collapsing": "#f44336"
    }
    trend_color = trend_colors.get(momentum_trend, "#ffeb3b")

    # --- HUD text ---
    a['hud_cur'].set_text(f"CUR: {num_score:+.2f}")
    a['hud_cur'].set_color(score_color)
    a['hud_avg'].set_text(f"AVG: {avg_score:+.2f}")
    a['hud_avg'].set_color(avg_color)
    a['hud_mom'].set_text(f"MOM: {momentum_30s:+.2f} ({momentum_trend})")
    a['hud_mom'].set_color(trend_color)

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

    # --- AI analysis text ---
    if decision and "analysis" in decision:
        analysis = decision.get('analysis', '')
        oracle = decision.get('oracle', '')
        a['ai_text'].set_text(f"### AI ANALYSIS ###\n\n{analysis}\n\n### STRATEGY ORACLE ###\n\n{oracle}")
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


def main():
    global game_start_time, momentum_history, goal_events, foul_events, referee_events, _initialized

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