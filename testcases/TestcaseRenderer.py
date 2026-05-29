import sys
import os
import math
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ==========================================
# 1. Command Line Argument Parsing
# ==========================================
parser = argparse.ArgumentParser(description="Render a specific R2Kickers test case.")
# We use standard standard flag notation (e.g. --testcase 1)
parser.add_argument('--testcase', type=str, required=True, help="The test case number (e.g., 1 for Testcase1)")
args = parser.parse_args()

# ==========================================
# 2. Dynamic Import Logic
# ==========================================
TESTCASE_FOLDER = f"{args.testcase}.Testcase"
current_dir = os.path.dirname(os.path.abspath(__file__))
testcase_path = os.path.join(current_dir, TESTCASE_FOLDER)

# Check if the folder exists to prevent confusing errors
if not os.path.exists(testcase_path):
    print(f"Error: Could not find folder '{TESTCASE_FOLDER}' at {testcase_path}")
    sys.exit(1)

# Add the testcase folder to Python's system path
sys.path.append(testcase_path)

# Try to import the world state from that folder
try:
    # NOTE: This assumes the file inside the folder is always named 'Defensive_Krise_Worldstate.py'.
    # If the file names change per folder, we would need to dynamically search for the .py file!
    from worldstate import ws, WorldState
except ImportError:
    print(f"Error: Could not find 'Defensive_Krise_Worldstate.py' inside {TESTCASE_FOLDER}")
    sys.exit(1)


# ==========================================
# 3. The Field Viewer
# ==========================================
class FootballFieldViewer:
    def __init__(self):
        self.length = 14.0
        self.width = 9.0
        self.goal_depth = 1.0
        self.goal_width = 2.5
        self.goal_area_length = 1.0
        self.goal_area_width = 4.0
        self.penalty_area_length = 3.0
        self.penalty_area_width = 6.0
        self.penalty_mark_dist = 2.0
        self.center_circle_radius = 1.5
        self.corner_arc_radius = 0.5
        self.border_strip = 1.0
        
        self.line_width = 2      
        self.mark_radius = 0.05  
        
        self.field_color = 'limegreen'
        self.line_color = 'white'
        self.bg_color = 'dimgrey'

    def create_field(self):
        fig, ax = plt.subplots(figsize=(10, 7))
        fig.patch.set_facecolor(self.bg_color)
        ax.set_facecolor(self.bg_color)
        
        x_min, x_max = -self.length / 2, self.length / 2
        y_min, y_max = -self.width / 2, self.width / 2
        
        grass_rect = patches.Rectangle((x_min - self.border_strip, y_min - self.border_strip),
                                       self.length + (self.border_strip*2), self.width + (self.border_strip*2),
                                       linewidth=0, facecolor=self.field_color, zorder=1)
        ax.add_patch(grass_rect)
        
        def draw_rect(x, y, w, h):
            ax.add_patch(patches.Rectangle((x, y), w, h, linewidth=self.line_width, 
                                           edgecolor=self.line_color, facecolor='none', zorder=2))

        draw_rect(x_min, y_min, self.length, self.width)
        ax.plot([0, 0], [y_min, y_max], color=self.line_color, linewidth=self.line_width, zorder=2)
        ax.add_patch(patches.Circle((0, 0), self.center_circle_radius, linewidth=self.line_width, edgecolor=self.line_color, facecolor='none', zorder=2))
        ax.add_patch(patches.Circle((0, 0), self.mark_radius, color=self.line_color, zorder=2))
        
        draw_rect(x_min, -self.penalty_area_width/2, self.penalty_area_length, self.penalty_area_width)
        draw_rect(x_max - self.penalty_area_length, -self.penalty_area_width/2, self.penalty_area_length, self.penalty_area_width)
        draw_rect(x_min, -self.goal_area_width/2, self.goal_area_length, self.goal_area_width)
        draw_rect(x_max - self.goal_area_length, -self.goal_area_width/2, self.goal_area_length, self.goal_area_width)
        
        ax.add_patch(patches.Circle((x_min + self.penalty_mark_dist, 0), self.mark_radius, color=self.line_color, zorder=2))
        ax.add_patch(patches.Circle((x_max - self.penalty_mark_dist, 0), self.mark_radius, color=self.line_color, zorder=2))
        
        draw_rect(x_min - self.goal_depth, -self.goal_width/2, self.goal_depth, self.goal_width)
        draw_rect(x_max, -self.goal_width/2, self.goal_depth, self.goal_width)

        corners = [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]
        angles = [(0, 90), (270, 360), (90, 180), (180, 270)]
        for (cx, cy), (t1, t2) in zip(corners, angles):
            ax.add_patch(patches.Arc((cx, cy), self.corner_arc_radius*2, self.corner_arc_radius*2,
                                     theta1=t1, theta2=t2, color=self.line_color, linewidth=self.line_width, zorder=2))

        ax.set_aspect('equal')
        ax.set_xlim(x_min - self.border_strip - 1, x_max + self.border_strip + 1)
        ax.set_ylim(y_min - self.border_strip - 1, y_max + self.border_strip + 1)
        ax.axis('off')
        
        return fig, ax

# ==========================================
# 4. The Test Case Renderer
# ==========================================
class TestCaseRenderer:
    def __init__(self, ax):
        self.ax = ax
        self.team_color = 'dodgerblue'
        self.enemy_color = 'crimson'
        self.ball_color = 'white'
        self.robot_radius = 0.25 

    def convert_angle(self, theta_user):
        return (90 + theta_user) % 360

    def draw_robot(self, pose, color, label=""):
        x, y, theta = pose
        plot_angle_rad = math.radians(self.convert_angle(theta))
        
        robot_circle = patches.Circle((x, y), self.robot_radius, facecolor=color, edgecolor='black', zorder=3)
        self.ax.add_patch(robot_circle)
        
        dx = self.robot_radius * math.cos(plot_angle_rad)
        dy = self.robot_radius * math.sin(plot_angle_rad)
        self.ax.plot([x, x + dx], [y, y + dy], color='white', linewidth=2.5, zorder=4)

    def draw_state(self, state: WorldState):
        for pose in state.Position_Team:
            self.draw_robot(pose, self.team_color)
            
        for pose in state.Position_Enemie:
            self.draw_robot(pose, self.enemy_color)
            
        bx, by, b_theta, b_vel, b_prob = state.Ball_Vector
        ball = patches.Circle((bx, by), 0.12, facecolor=self.ball_color, edgecolor='black', zorder=5)
        self.ax.add_patch(ball)
        
        if b_vel > 0:
            b_plot_angle = math.radians(self.convert_angle(b_theta))
            arrow_len = b_vel * 0.3
            dx = arrow_len * math.cos(b_plot_angle)
            dy = arrow_len * math.sin(b_plot_angle)
            self.ax.arrow(bx, by, dx, dy, head_width=0.2, head_length=0.25, 
                          fc='gold', ec='black', zorder=4, length_includes_head=True)
            
        possession_text = f"Possession: {state.BallPossession} | Score: {state.Score}"
        self.ax.text(0, self.ax.get_ylim()[1] - 0.5, possession_text, 
                     color='white', fontsize=12, fontweight='bold',
                     ha='center', va='center', bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))

# ==========================================
# 5. Main Execution
# ==========================================
if __name__ == "__main__":
    field_viewer = FootballFieldViewer()
    fig, ax = field_viewer.create_field()
    
    renderer = TestCaseRenderer(ax)
    renderer.draw_state(ws)
    
    # We use the arg dynamically in the title too!
    plt.title(f"Testcase {args.testcase} - Worldstate Visualizer", color='white', pad=20, fontsize=16)
    plt.tight_layout()
    plt.show()