import json, os, sys, time
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

plt.rcParams['toolbar'] = 'None' 
BASE_DIR = os.getenv('ROS2K_WS', '.')
STRAT_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")

latest_world_state = {}
latest_tactical_score = {}
latest_match_state = {}

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
        global latest_tactical_score
        try: latest_tactical_score = json.loads(msg.data)
        except: pass

    def match_callback(self, msg):
        global latest_match_state
        try: latest_match_state = json.loads(msg.data)
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
    ax_pitch = draw_empty_pitch(fig, "")
    
    # Werte auslesen
    num_score = score_data.get("current_numerical_score", 0.0)
    avg_score = score_data.get("average_numerical_score", 0.0)
    blue_goals = match_data.get("blue", 0)
    red_goals = match_data.get("red", 0)
    
    # Rot/Grün Logik für die Scores
    score_color = '#4caf50' if num_score >= 0 else '#f44336' # Grün wenn >=0, Rot wenn <0
    avg_color = '#4caf50' if avg_score >= 0 else '#f44336'
    
    # Getrennte Textboxen für individuelle Farben oben links
    fig.text(0.05, 0.94, f"CUR: {num_score:+.2f}", color=score_color, fontsize=15, weight='heavy', bbox=dict(facecolor='black', alpha=0.8, pad=6))
    fig.text(0.15, 0.94, f"AVG: {avg_score:+.2f}", color=avg_color, fontsize=15, weight='heavy', bbox=dict(facecolor='black', alpha=0.8, pad=6))
    
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

    ax_text = fig.add_axes([0.72, 0.05, 0.25, 0.85])
    ax_text.axis('off')
    
    if decision and "analysis" in decision:
        analysis = decision.get('analysis', '')
        oracle = decision.get('oracle', '')
        text_content = f"### AI ANALYSIS ###\n\n{analysis}\n\n### STRATEGY ORACLE ###\n\n{oracle}"
    else:
        text_content = "⚡ FAST EXECUTION MODE\n\n(No explanation requested)"
        
    ax_text.text(0, 0.9, text_content, color='white', fontsize=14, wrap=True, va='top')

    fig.canvas.draw_idle()
    fig.canvas.flush_events()

def main():
    print("📺 Starting Single-Threaded R2K Visualizer...")
    rclpy.init(args=None)
    node = VisualizerROSNode()

    plt.ion()
    fig = plt.figure(figsize=(16, 9), facecolor='#121212')
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
