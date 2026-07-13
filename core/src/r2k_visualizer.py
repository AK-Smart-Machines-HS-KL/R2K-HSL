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

plt.rcParams['toolbar'] = 'None' 
BASE_DIR = os.getenv('ROS2K_WS', '.')
STRAT_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")

latest_world_state = {}
latest_tactical_score = {}
latest_match_state = {}

# Momentum history tracking
momentum_history = deque(maxlen=1200)  # 120s at 10Hz
game_start_time = None
goal_events = []  # [(elapsed, team, blue_score, red_score)]
foul_events = []  # [(elapsed, team, foul_type)]
referee_events = deque(maxlen=50)  # Recent referee decisions
last_match_status = "playing"

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
            # Track momentum history
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
                # Determine which team scored
                team = "blue" if blue_goals > red_goals else "red"
                goal_events.append((elapsed, team, blue_goals, red_goals))
                referee_events.append((elapsed, "GOAL!", f"Blue {blue_goals} - {red_goals} Red", "#4caf50"))
                # Add kickoff event
                conceding = "red" if team == "blue" else "blue"
                referee_events.append((elapsed, "KICKOFF", f"{conceding.upper()} frozen 3s", "#ff9800"))
            
            # Track foul events (transition guard: only fire once per foul_penalty status)
            if latest_match_state.get('foul') and current_status == 'foul_penalty' and last_match_status != 'foul_penalty':
                elapsed = time.time() - game_start_time if game_start_time else 0
                foul_data = latest_match_state['foul']
                foul_type = foul_data.get('type', 'unknown')
                offender = foul_data.get('offender', 'unknown')
                victim = foul_data.get('victim', 'unknown')
                penalty = foul_data.get('penalty', 'unknown')
                
                # Determine offending team
                team = "blue" if "blue" in offender else "red"
                
                # Ball-out foul: special display
                if foul_type == 'ball_out':
                    restart_team = foul_data.get('restart_team', 'unknown')
                    foul_events.append((elapsed, team, foul_type))
                    referee_events.append((elapsed, "BALL OUT", f"{offender} pushed out", "#ff9800"))
                    referee_events.append((elapsed, "PENALTY", f"{offender} → 2m warp + freeze", "#ff5722"))
                    referee_events.append((elapsed, "RESTART", f"{restart_team}", "#0074D9"))
                else:
                    # Regular foul (pushing/blocking)
                    foul_events.append((elapsed, team, foul_type))
                    referee_events.append((elapsed, "FOUL", f"{foul_type.upper()} by {offender}", "#FF4136"))
                    # Show actual penalty from foul data
                    penalty_text = penalty if penalty and penalty != "unknown" else "sideline"
                    if "own_goal" in penalty_text:
                        referee_events.append((elapsed, "PENALTY", f"{offender} → own goal warp", "#FF9800"))
                    else:
                        referee_events.append((elapsed, "PENALTY", f"{offender} → sideline", "#FF9800"))
            
            # Track ball-out events (non-foul neutral restarts)
            if current_status == 'ball_out' and last_match_status != 'ball_out':
                elapsed = time.time() - game_start_time if game_start_time else 0
                ball_out = latest_match_state.get('ball_out_event', {})
                out_type = ball_out.get('type', 'unknown') if ball_out else 'unknown'
                restart_team = latest_match_state.get('restart_team', 'unknown')
                last_toucher = latest_match_state.get('last_toucher', 'unknown')
                referee_events.append((elapsed, "BALL OUT", f"{out_type}", "#ffeb3b"))
                referee_events.append((elapsed, "RESTART", f"{restart_team} ({last_toucher})", "#0074D9"))
            
            last_match_status = current_status
        except: pass

def to_plot(val):
    return (val * 10.0) + 50.0

def draw_empty_pitch(fig, message="WAITING FOR DATA..."):
    fig.clf()
    ax_pitch = fig.add_axes([0.05, 0.05, 0.65, 0.85])
    pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#1e2a22', line_color='#fafafa')
    pitch.draw(ax=ax_pitch)
    if message:
        fig.text(0.35, 0.94, message, color='#ffeb3b', fontsize=16, weight='bold', ha='center', bbox=dict(facecolor='black', alpha=0.8, pad=8))
    return ax_pitch

def visualize_tactics(fig, state, score_data, match_data, decision, last_strat_time):
    fig.clf()
    
    # Momentum sub-panel (bottom)
    ax_momentum = fig.add_axes([0.05, 0.05, 0.65, 0.20])
    ax_momentum.set_facecolor('#1e2a22')
    ax_momentum.set_xlim(0, 120)  # Extended to 120s
    ax_momentum.set_ylim(-10, 10)
    ax_momentum.set_xlabel('Game Time (s)', color='white', fontsize=9)
    ax_momentum.set_ylabel('Score', color='white', fontsize=9)
    ax_momentum.set_title('Momentum Timeline (120s)', color='white', fontsize=13, weight='bold')
    ax_momentum.tick_params(colors='white', labelsize=8)
    ax_momentum.grid(True, alpha=0.2, color='white')
    
    # Fill momentum chart with team colors (blue above 0, red below 0)
    ax_momentum.axhspan(0, 10, facecolor='#0074D9', alpha=0.08, zorder=0)
    ax_momentum.axhspan(-10, 0, facecolor='#FF4136', alpha=0.08, zorder=0)
    
    # Draw momentum history
    if momentum_history:
        times = [t for t, s in momentum_history]
        scores = [s for t, s in momentum_history]
        # Filled area: blue where score > 0, red where score < 0
        ax_momentum.fill_between(times, scores, 0, where=[s >= 0 for s in scores],
                                 color='#0074D9', alpha=0.25, zorder=1)
        ax_momentum.fill_between(times, scores, 0, where=[s < 0 for s in scores],
                                 color='#FF4136', alpha=0.25, zorder=1)
        ax_momentum.plot(times, scores, color='white', linewidth=1.5, linestyle=':', label='Score', zorder=2)
        ax_momentum.axhline(y=0, color='white', linestyle='--', alpha=0.3, linewidth=0.5)
    
    # Draw foul markers with team colors (triangles)
    for foul_time, team, foul_type in foul_events:
        team_color = '#0074D9' if team == 'blue' else '#FF4136'
        ax_momentum.scatter([foul_time], [0], marker='v', color=team_color, s=80, zorder=5, alpha=0.8)
    
    # Draw goal markers with team colors (circles)
    for goal_time, team, blue_g, red_g in goal_events:
        team_color = '#0074D9' if team == 'blue' else '#FF4136'
        score_diff = blue_g - red_g
        ax_momentum.scatter([goal_time], [score_diff], marker='o', color=team_color, s=100, zorder=5, edgecolors='white', linewidths=1.5)
    
    # Add legend for markers
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#0074D9', markersize=6, label='🔵 Blue Goal'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF4136', markersize=6, label='🔴 Red Goal'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#0074D9', markersize=6, label='🔵 Blue Foul'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#FF4136', markersize=6, label='🔴 Red Foul'),
    ]
    ax_momentum.legend(handles=legend_elements, loc='upper left', fontsize=7, facecolor='#1e2a22', edgecolor='white', labelcolor='white', framealpha=0.9)
    
    # Main pitch area (top)
    ax_pitch = fig.add_axes([0.05, 0.30, 0.65, 0.65])
    pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#1e2a22', line_color='#fafafa')
    pitch.draw(ax=ax_pitch)
    
    # Werte auslesen
    num_score = score_data.get("current_numerical_score", 0.0)
    avg_score = score_data.get("average_numerical_score", 0.0)
    momentum_30s = score_data.get("momentum_30s", 0.0)
    momentum_trend = score_data.get("momentum_trend", "stable")
    blue_goals = match_data.get("blue", 0)
    red_goals = match_data.get("red", 0)
    
    # Rot/Grün Logik für die Scores
    score_color = '#4caf50' if num_score >= 0 else '#f44336' # Grün wenn >=0, Rot wenn <0
    avg_color = '#4caf50' if avg_score >= 0 else '#f44336'
    
    # Momentum color coding
    trend_colors = {
        "ascending": "#4caf50",
        "improving": "#8bc34a",
        "stable": "#ffeb3b",
        "declining": "#ff9800",
        "collapsing": "#f44336"
    }
    trend_color = trend_colors.get(momentum_trend, "#ffeb3b")
    
    # Getrennte Textboxen für individuelle Farben oben links
    fig.text(0.05, 0.94, f"CUR: {num_score:+.2f}", color=score_color, fontsize=15, weight='heavy', bbox=dict(facecolor='black', alpha=0.8, pad=6))
    fig.text(0.15, 0.94, f"AVG: {avg_score:+.2f}", color=avg_color, fontsize=15, weight='heavy', bbox=dict(facecolor='black', alpha=0.8, pad=6))
    fig.text(0.25, 0.94, f"MOM: {momentum_30s:+.2f} ({momentum_trend})", color=trend_color, fontsize=15, weight='heavy', bbox=dict(facecolor='black', alpha=0.8, pad=6))
    
    # Statusleiste Rest (Match Score & Engine)
    time_since_last_strat = time.time() - last_strat_time if last_strat_time > 0 else 999.9
    status_color = 'white' if time_since_last_strat < 2.0 else 'red'
    lat = decision.get('latency_ms', 0) if decision else 0
    model = decision.get('model_name', 'Waiting...') if decision else 'N/A'
    
    hud_text = f"MATCH: BLUE {blue_goals} : {red_goals} RED    |    Lat: {lat}ms    |    AI: {model}"
    fig.text(0.50, 0.94, hud_text, color=status_color, fontsize=15, weight='bold', ha='center', bbox=dict(facecolor='black', alpha=0.8, pad=6))

    ents = state.get('entities', {})
    assignments = decision.get("assignments", {}) if decision else {}
    
    for name, p in ents.items():
        if 'x' not in p or 'y' not in p: continue
        px, py = to_plot(p['x']), to_plot(p['y'])
        
        if 'ball' in name:
            ax_pitch.scatter(px, py, c='white', s=150, zorder=5, edgecolors='black')
        else:
            is_blue = 'blue' in name
            team_color = '#0074D9' if is_blue else '#FF4136'
            ax_pitch.scatter(px, py, c=team_color, s=250, zorder=4, edgecolors='black')
            
            bot_num = name.split('_')[-1]
            if is_blue:
                bot_role = assignments.get(name, {}).get("role", "")
                role_char = bot_role[0].lower() if bot_role else "-"
                display_name = f"{bot_num}-{role_char}"
            else:
                display_name = f"{bot_num}"
            
            ax_pitch.text(px + 2.0, py + 2.0, display_name, color=team_color, fontsize=14, weight='bold',
                          bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=2))

    # --- EINZIGE ÄNDERUNG: Robuste Pfeil-Logik ---
    if decision and "assignments" in decision:
        for bot, action in decision["assignments"].items():
            if bot in ents:
                start_p = ents[bot]
                if 'x' not in start_p or 'y' not in start_p: continue
                
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
                
                if tx is not None and ty is not None:
                    try:
                        sx, sy = to_plot(start_p['x']), to_plot(start_p['y'])
                        ptx, pty = to_plot(float(tx)), to_plot(float(ty))
                        ax_pitch.annotate("", xy=(ptx, pty), xytext=(sx, sy),
                                          arrowprops=dict(arrowstyle="->", color="#ffeb3b", lw=2, ls='--', alpha=0.8))
                    except: pass
    # ---------------------------------------------

    # Text panel (right side)
    ax_text = fig.add_axes([0.72, 0.30, 0.25, 0.65])
    ax_text.axis('off')
    
    # Decision text (top half)
    if decision and "analysis" in decision:
        analysis = decision.get('analysis', '')
        oracle = decision.get('oracle', '')
        text_content = f"### AI ANALYSIS ###\n\n{analysis}\n\n### STRATEGY ORACLE ###\n\n{oracle}"
    else:
        text_content = "⚡ FAST EXECUTION MODE\n\n(No explanation requested)"
    
    ax_text.text(0, 0.95, text_content, color='white', fontsize=12, wrap=True, va='top', 
                  fontfamily='monospace')
    
    # Referee events panel (bottom half of right side)
    # Match momentum panel height so titles align
    ax_referee = fig.add_axes([0.72, 0.05, 0.25, 0.20])
    ax_referee.set_facecolor('#1e2a22')
    ax_referee.axis('off')
    
    # Referee event title — aligned with momentum title (both at top of their panels)
    ax_referee.set_title("⚖️  REFEREE DECISIONS", color='#ffeb3b', fontsize=13,
                         weight='bold', pad=4)
    
    # Show kickoff popup in a dedicated zone at the top of the panel
    # (above the event list, below the title — does not overlap event entries)
    kickoff_active = match_data.get('status') == 'goal'
    if kickoff_active:
        ax_referee.text(0.5, 0.90, "🥅 KICKOFF", color='#ffeb3b', fontsize=14,
                        weight='bold', ha='center', va='top', transform=ax_referee.transAxes,
                        bbox=dict(facecolor='#2a1e0a', alpha=0.9, edgecolor='#ffeb3b', pad=4, boxstyle='round,pad=0.3'))
        ax_referee.text(0.5, 0.72, "Conceding team frozen", color='white', fontsize=10,
                        ha='center', va='top', transform=ax_referee.transAxes)
    
    # Recent referee events (last 8) — start below kickoff popup zone
    recent_events = list(referee_events)[-8:] if referee_events else []
    y_pos = 0.58 if kickoff_active else 0.85
    for event_time, event_type, event_detail, event_color in recent_events:
        # Format timestamp as [MM:SS]
        mins = int(event_time // 60)
        secs = event_time % 60
        timestamp = f"[{mins:02d}:{secs:04.1f}]"
        
        # Timestamp (gray)
        ax_referee.text(0.02, y_pos, timestamp, color='#888888', fontsize=9,
                        fontfamily='monospace', transform=ax_referee.transAxes)
        # Event type (colored)
        ax_referee.text(0.18, y_pos, f"{event_type}:", color=event_color, fontsize=11, 
                        weight='bold', transform=ax_referee.transAxes)
        # Event detail (white)
        ax_referee.text(0.48, y_pos, event_detail, color='white', fontsize=10,
                        transform=ax_referee.transAxes)
        y_pos -= 0.16
        if y_pos < 0.05:
            break
    
    if not recent_events and not kickoff_active:
        ax_referee.text(0.5, 0.5, "No events yet", color='white', fontsize=11,
                        ha='center', va='center', alpha=0.5, transform=ax_referee.transAxes)

    fig.canvas.draw_idle()
    fig.canvas.flush_events()

def main():
    global game_start_time, momentum_history, goal_events, foul_events, referee_events
    
    print("📺 Starting Single-Threaded R2K Visualizer...")
    rclpy.init(args=None)
    node = VisualizerROSNode()

    plt.ion()
    fig = plt.figure(figsize=(16, 9), facecolor='#121212')
    
    # Reset tracking
    game_start_time = time.time()
    momentum_history.clear()
    goal_events.clear()
    foul_events.clear()
    referee_events.clear()
    
    draw_empty_pitch(fig)
    plt.show(block=False)

    last_strat_mtime = 0
    current_decision = {}
    last_strat_time_abs = 0.0

    while plt.fignum_exists(fig.number):
        rclpy.spin_once(node, timeout_sec=0.01)

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
            try: visualize_tactics(fig, state_copy, score_copy, match_copy, current_decision, last_strat_time_abs)
            except: pass
        
        plt.pause(0.04)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
