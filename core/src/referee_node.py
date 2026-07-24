#!/usr/bin/env python3
import rclpy
import json
import random
import time
import math
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from gazebo_msgs.srv import SetEntityState
from collections import deque

class RefereeNode(Node):
    def __init__(self):
        super().__init__('referee_node')
        self.sub = self.create_subscription(String, '/world_positions', self.pos_callback, 10)
        self.pub = self.create_publisher(String, '/match_state', 10)
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        
        self.score_blue = 0
        self.score_red = 0
        self.ball_was_in_goal = False
        
        # Foul detection thresholds
        self.PUSHING_VELOCITY_THRESHOLD = 0.5
        self.PUSHING_DISTANCE_THRESHOLD = 0.3
        self.BALL_PROXIMITY_THRESHOLD = 0.8
        self.BLOCKING_DISTANCE_THRESHOLD = 0.5
        self.OBSTRUCTION_ANGLE = 30
        self.BLOCKING_MIN_DURATION = 3.0  # seconds of sustained blocking before foul
        
        # Ball-out detection
        self.FIELD_X_MIN = -4.5
        self.FIELD_X_MAX = 4.5
        self.FIELD_Y_MIN = -3.0
        self.FIELD_Y_MAX = 3.0
        self.GOAL_Y_MIN = -0.9
        self.GOAL_Y_MAX = 0.9
        self.DEBOUNCE_FRAMES = 5
        
        # Last-touch tracking
        self.PROXIMITY_THRESHOLD = 0.8
        self.HYSTERESIS_FRAMES = 3
        self.last_toucher_frames = {}
        self.ball_out_frames = 0
        
        # Restart logic
        self.BALL_OUT_TIMEOUT = 3.0
        self.RESTART_FREEZE_TIME = 1.0
        self.restart_start_time = None
        
        # Ball-out foul penalty
        self.BALL_OUT_WARP_DISTANCE = 2.0
        self.BALL_OUT_FREEZE_TIME = 5.0
        self.BALL_OUT_REWARD_PENALTY = -0.5
        
        # Set-piece logic (unified: kickoff, goal kick, corner kick-in)
        self.SET_PIECE_COUNTDOWN = 5.0
        self.GOAL_AREA_X = 3.5      # 1m inward from goal line (±4.5)
        self.GOAL_AREA_Y = 1.0      # ±1.0m, 2m wide goal area
        self.SET_PIECE_WARP_RADIUS = 1.5   # opponents within this get warped away
        self.WARP_AWAY_DISTANCE = 2.0      # warp this far radially from ball
        
        # Kickoff logic
        self.kickoff_positions = {}  # Loaded from first world_positions
        self.kickoff_positions_loaded = False
        
        # Freeze enforcement
        self.freeze_pubs = {}
        self.frozen_bots = {}
        
        # State tracking
        self.status = "playing"
        self.ball_out_event = None
        self.restart_team = None
        self.restart_pos = None
        self.last_toucher = None
        self.foul_event = None
        self.foul_cooldown = {}
        self.blocking_timers = {}  # {blocker_id: start_time} for sustained blocking
        
        # Position history for velocity calculation
        self.position_history = deque(maxlen=10)
        
        self.get_logger().info("⚖️  Referee V6 Online: Goals + Fouls + Ball-out detection")
    
    def pos_callback(self, msg):
        try:
            data = json.loads(msg.data)
            entities = data.get('entities', {})
            ball = entities.get('soccer_ball')
            
            if not ball:
                return
            
            # Store position history for velocity calculation
            self.position_history.append((time.time(), entities))
            
            # Load kickoff positions from first world state
            if not self.kickoff_positions_loaded:
                self._store_kickoff_positions(entities)
            
            # 1. Goal detection
            self._check_goal(ball, entities)
            
            # 2. Ball-out detection
            if self.status == "playing":
                self._check_ball_out(ball)
            
            # 3. Last-touch tracking
            self._track_last_toucher(ball, entities)
            
            # 3b. Early restart termination: restart team touches the ball
            if self.status in ("goal", "ball_out", "goal_kick", "corner_kick_in") and self.restart_start_time and self.restart_team:
                for bot_id, bot_pos in entities.items():
                    if bot_id == 'soccer_ball':
                        continue
                    dist = math.hypot(bot_pos['x'] - ball['x'], bot_pos['y'] - ball['y'])
                    if dist < 0.3 and self.restart_team in bot_id:
                        self._end_restart()
                        break
            
            # 4. Foul detection
            if self.status == "playing":
                self._detect_fouls(entities)
            
            # 5. Restart handling
            if self.restart_start_time:
                elapsed = time.time() - self.restart_start_time
                timeout = self.SET_PIECE_COUNTDOWN if self.status in ("goal", "goal_kick", "corner_kick_in", "ball_out") else self.BALL_OUT_TIMEOUT
                if elapsed > timeout:
                    self.status = "playing"
                    self.restart_start_time = None
                    self.ball_out_event = None
                    self.foul_event = None
            
            # 6. Enforce freeze for ball-out fouls
            self._enforce_freeze()
            
            # Publish match state
            self._publish_state()
            
        except Exception as e:
            self.get_logger().error(f"Referee Error: {e}")
    
    def _check_goal(self, ball, entities):
        x, y = ball['x'], ball['y']
        
        # Blue scores: ball crosses red goal line AND within goal posts
        if x > self.FIELD_X_MAX and self.GOAL_Y_MIN <= y <= self.GOAL_Y_MAX and not self.ball_was_in_goal:
            self.score_blue += 1
            self.ball_was_in_goal = True
            self.status = "goal"
            self.get_logger().info(f"⚽ GOAL FOR BLUE! Score: {self.score_blue}:{self.score_red}")
            self._kickoff_reset(entities, scoring_team="blue")
        # Red scores: ball crosses blue goal line AND within goal posts
        elif x < self.FIELD_X_MIN and self.GOAL_Y_MIN <= y <= self.GOAL_Y_MAX and not self.ball_was_in_goal:
            self.score_red += 1
            self.ball_was_in_goal = True
            self.status = "goal"
            self.get_logger().info(f"⚽ GOAL FOR RED! Score: {self.score_blue}:{self.score_red}")
            self._kickoff_reset(entities, scoring_team="red")
        elif -4.0 <= x <= 4.0:
            self.ball_was_in_goal = False
    
    def _store_kickoff_positions(self, entities):
        """Store initial positions for kickoff reset."""
        for bot_id, bot_pos in entities.items():
            if bot_id != 'soccer_ball':
                self.kickoff_positions[bot_id] = {'x': bot_pos['x'], 'y': bot_pos['y']}
        self.kickoff_positions_loaded = True
        self.get_logger().info(f"📍 Stored {len(self.kickoff_positions)} kickoff positions")
    
    def _kickoff_reset(self, entities, scoring_team):
        """Reset ball to center and bots to kickoff. Scoring team frozen 5s."""
        # 1. Reset ball to center
        self._reset_ball(0.0, 0.0)
        
        # 2. Reset all bots to their kickoff positions
        for bot_id, pos in self.kickoff_positions.items():
            self._warp_bot(bot_id, pos['x'], pos['y'])
        
        # 3. Freeze scoring team for 5 seconds (unified set-piece countdown)
        self._freeze_team(scoring_team, entities, self.SET_PIECE_COUNTDOWN)
        
        # 4. Set restart timer
        self.restart_start_time = time.time()
        
        # 5. Clear event state
        self.ball_out_event = None
        self.restart_team = "red" if scoring_team == "blue" else "blue"
        self.foul_event = None
        
        self.get_logger().info(f"🥅 KICKOFF: Ball reset. {scoring_team.upper()} frozen {self.SET_PIECE_COUNTDOWN:.0f}s.")
    
    def _reset_after_goal(self):
        """Clear event state after goal (called by kickoff)."""
        self.ball_out_event = None
        self.restart_team = None
        self.restart_pos = None
        self.last_toucher = None
        self.foul_event = None
    
    def _end_restart(self):
        """End restart immediately — restart team touched the ball."""
        self.status = "playing"
        self.restart_start_time = None
        self.ball_out_event = None
        self.foul_event = None
        self.frozen_bots.clear()
        self.get_logger().info("BALL FREE (early — restart team touched ball)")
    
    def _check_ball_out(self, ball):
        x, y = ball['x'], ball['y']
        
        # Sideline out
        if abs(y) > self.FIELD_Y_MAX:
            self.ball_out_frames += 1
            if self.ball_out_frames >= self.DEBOUNCE_FRAMES:
                self._apply_ball_out_penalty(ball, "sideline")
                self.ball_out_frames = 0
        # Goal line out (no goal)
        elif abs(x) > self.FIELD_X_MAX and abs(y) > self.GOAL_Y_MAX:
            self.ball_out_frames += 1
            if self.ball_out_frames >= self.DEBOUNCE_FRAMES:
                self._apply_ball_out_penalty(ball, "goal_line")
                self.ball_out_frames = 0
        else:
            self.ball_out_frames = 0
    
    def _track_last_toucher(self, ball, entities):
        closest_bot = None
        closest_dist = float('inf')
        
        for bot_id, bot_pos in entities.items():
            if bot_id == 'soccer_ball':
                continue
            dist = ((bot_pos['x'] - ball['x'])**2 + (bot_pos['y'] - ball['y'])**2)**0.5
            if dist < closest_dist:
                closest_dist = dist
                closest_bot = bot_id
        
        if closest_dist < self.PROXIMITY_THRESHOLD:
            self.last_toucher_frames[closest_bot] = self.last_toucher_frames.get(closest_bot, 0) + 1
            for bot_id in list(self.last_toucher_frames.keys()):
                if bot_id != closest_bot:
                    self.last_toucher_frames[bot_id] = 0
        
        max_frames = max(self.last_toucher_frames.values()) if self.last_toucher_frames else 0
        for bot_id, frames in self.last_toucher_frames.items():
            if frames >= self.HYSTERESIS_FRAMES and frames == max_frames:
                self.last_toucher = bot_id
                break
    
    def _detect_fouls(self, entities):
        ball = entities.get('soccer_ball')
        if not ball:
            return
        
        current_time = time.time()
        
        # Detect pushing (same-team pairs excluded — teammates may cluster defensively)
        bots = [(bid, pos) for bid, pos in entities.items() if 'blue' in bid or 'red' in bid]
        
        for i, (bot_id_1, pos_1) in enumerate(bots):
            # Check cooldown
            if self.foul_cooldown.get(bot_id_1, 0) > current_time:
                continue
            
            for bot_id_2, pos_2 in bots[i+1:]:
                # Skip same-team pairs
                if ('blue' in bot_id_1) == ('blue' in bot_id_2):
                    continue
                
                # Check cooldown
                if self.foul_cooldown.get(bot_id_2, 0) > current_time:
                    continue
                
                # Calculate distance
                dist = ((pos_1['x'] - pos_2['x'])**2 + (pos_1['y'] - pos_2['y'])**2)**0.5
                
                # Check if both bots are far from ball
                dist_to_ball_1 = ((pos_1['x'] - ball['x'])**2 + (pos_1['y'] - ball['y'])**2)**0.5
                dist_to_ball_2 = ((pos_2['x'] - ball['x'])**2 + (pos_2['y'] - ball['y'])**2)**0.5
                
                # Pushing foul: two opposing bots close together, neither near ball
                if (dist < self.PUSHING_DISTANCE_THRESHOLD and 
                    dist_to_ball_1 > self.BALL_PROXIMITY_THRESHOLD and 
                    dist_to_ball_2 > self.BALL_PROXIMITY_THRESHOLD):
                    self._apply_foul(bot_id_1, bot_id_2, "pushing", pos_1, pos_2)
                    return
        
        # Detect blocking without ball (same-team already excluded via opponents filter)
        blue_bots = [(bid, pos) for bid, pos in entities.items() if 'blue' in bid]
        red_bots = [(bid, pos) for bid, pos in entities.items() if 'red' in bid]
        
        active_blockers = set()
        
        for blocker_id, blocker_pos in blue_bots + red_bots:
            if self.foul_cooldown.get(blocker_id, 0) > current_time:
                continue
            
            # Check if blocker is near ball
            dist_to_ball = ((blocker_pos['x'] - ball['x'])**2 + (blocker_pos['y'] - ball['y'])**2)**0.5
            if dist_to_ball < self.BALL_PROXIMITY_THRESHOLD:
                continue
            
            # Check if blocker obstructs opponent path to ball
            opponents = red_bots if 'blue' in blocker_id else blue_bots
            for opp_id, opp_pos in opponents:
                # Vector from opponent to ball
                opp_to_ball = (ball['x'] - opp_pos['x'], ball['y'] - opp_pos['y'])
                # Vector from blocker to opponent
                blocker_to_opp = (blocker_pos['x'] - opp_pos['x'], blocker_pos['y'] - opp_pos['y'])
                
                # Check distance
                blocker_dist = (blocker_to_opp[0]**2 + blocker_to_opp[1]**2)**0.5
                if blocker_dist > self.BLOCKING_DISTANCE_THRESHOLD:
                    continue
                
                # Check angle (simplified: blocker between opponent and ball)
                dot = opp_to_ball[0] * blocker_to_opp[0] + opp_to_ball[1] * blocker_to_opp[1]
                if dot > 0:  # Blocker in front of opponent relative to ball
                    # Sustained blocking: must persist for BLOCKING_MIN_DURATION seconds
                    active_blockers.add(blocker_id)
                    if blocker_id not in self.blocking_timers:
                        self.blocking_timers[blocker_id] = current_time
                    elif current_time - self.blocking_timers[blocker_id] >= self.BLOCKING_MIN_DURATION:
                        self._apply_foul(blocker_id, opp_id, "blocking_without_ball", blocker_pos, opp_pos)
                        del self.blocking_timers[blocker_id]
                        return
                    # else: still timing, do not fire yet
        
        # Clear timers for blockers no longer obstructing
        for blocker_id in list(self.blocking_timers.keys()):
            if blocker_id not in active_blockers:
                del self.blocking_timers[blocker_id]
    
    def _apply_foul(self, offender, victim, foul_type, offender_pos, victim_pos):
        # Set cooldown
        self.foul_cooldown[offender] = time.time() + 5.0
        self.blocking_timers.pop(offender, None)  # Clear any pending blocking timer
        
        if foul_type == "blocking_without_ball":
            # Warp blocking bot to a random position towards own goal
            if 'blue' in offender:
                # Blue's own goal is at X=-4.5, warp somewhere in own half
                warp_x = random.uniform(-4.3, -2.0)
            else:
                # Red's own goal is at X=+4.5, warp somewhere in own half
                warp_x = random.uniform(2.0, 4.3)
            warp_y = random.uniform(-2.8, 2.8)
            penalty_label = "own_half_warp"
        else:
            # Pushing foul: warp offender to sideline (original behavior)
            warp_x = -4.0 if 'blue' in offender else 4.0
            warp_y = random.uniform(-2.0, 2.0)
            penalty_label = "sideline_warp"
        
        # Warp the bot
        self._warp_bot(offender, warp_x, warp_y)
        
        # Create foul event
        self.foul_event = {
            "type": foul_type,
            "offender": offender,
            "victim": victim,
            "position": {"x": offender_pos['x'], "y": offender_pos['y']},
            "penalty": penalty_label
        }
        
        self.status = "foul_penalty"
        self.restart_start_time = time.time()
        
        self.get_logger().info(
            f"⚠️  FOUL: {offender} {foul_type} {victim}. "
            f"Warped to ({warp_x:.1f},{warp_y:.1f}) [{penalty_label}]."
        )
    
    def _apply_ball_out_penalty(self, ball, out_type):
        """Ball-out handler. Sideline → foul penalty. Goal-line → set piece (goal kick or corner kick-in)."""
        # Get current entities from position_history
        entities = self.position_history[-1][1] if self.position_history else {}
        offender = self.last_toucher
        offender_pos = entities.get(offender)
        
        if not offender_pos:
            return
        
        # Determine offending team
        offending_team = "blue" if "blue" in offender else "red"
        
        # Goal-line out → set piece (goal kick or corner kick-in)
        if out_type == "goal_line":
            goal_line_owner = "red" if ball['x'] > 0 else "blue"
            if offending_team == goal_line_owner:
                # Scenario B: defender kicked over own line → corner kick-in for attacker
                restart_team = "red" if offending_team == "blue" else "blue"
                ball_pos = self._corner_flag_position(ball)
                self._start_set_piece("corner_kick_in", ball_pos, restart_team, offending_team, entities)
                self.get_logger().info(
                    f"🚩 CORNER KICK-IN: {offender} kicked over own goal line. "
                    f"Ball at ({ball_pos[0]:.1f},{ball_pos[1]:.1f}). "
                    f"{offending_team.upper()} warped+frozen {self.SET_PIECE_COUNTDOWN:.0f}s. Restart: {restart_team}"
                )
            else:
                # Scenario A: attacker kicked over defender's line → goal kick for defender
                restart_team = goal_line_owner
                ball_pos = self._goal_area_corner(ball, goal_line_owner)
                self._start_set_piece("goal_kick", ball_pos, restart_team, offending_team, entities)
                self.get_logger().info(
                    f"🥅 GOAL KICK: {offender} kicked over opponent's goal line. "
                    f"Ball at ({ball_pos[0]:.1f},{ball_pos[1]:.1f}). "
                    f"{offending_team.upper()} warped+frozen {self.SET_PIECE_COUNTDOWN:.0f}s. Restart: {restart_team}"
                )
            return
        
        # Sideline out → existing foul penalty
        restart_team = "red" if offending_team == "blue" else "blue"
        
        # Compute warp position: 2m inward from boundary
        warp_x, warp_y = self._compute_warp_position(ball, offender_pos, out_type)
        
        # Warp offending bot
        self._warp_bot(offender, warp_x, warp_y)
        
        # Freeze all bots on offending team for 5 seconds
        now = time.time()
        for bot_id in entities:
            if offending_team in bot_id:
                self.frozen_bots[bot_id] = now + self.BALL_OUT_FREEZE_TIME
        
        # Place ball on the line
        ball_reset_x, ball_reset_y = self._clamp_ball_to_line(ball['x'], ball['y'], out_type)
        self._reset_ball(ball_reset_x, ball_reset_y)
        
        # Record foul event
        self.foul_event = {
            "type": "ball_out",
            "out_type": out_type,
            "offender": offender,
            "victim": None,
            "position": {"x": offender_pos['x'], "y": offender_pos['y']},
            "penalty": "warp_2m_freeze_5s",
            "restart_team": restart_team
        }
        
        # Set match state
        self.ball_out_event = {"type": out_type, "position": {"x": ball['x'], "y": ball['y']}}
        self.restart_team = restart_team
        self.restart_pos = {"x": ball_reset_x, "y": ball_reset_y}
        self.status = "ball_out"
        self.restart_start_time = now
        
        self.get_logger().info(
            f"📤 BALL OUT FOUL: {offender} pushed ball out. "
            f"Warped to ({warp_x:.1f},{warp_y:.1f}). "
            f"{offending_team.upper()} frozen 5s. Restart: {restart_team}"
        )
    
    def _compute_warp_position(self, ball, offender_pos, out_type):
        """Warp offender 2m inward from the touch line."""
        if out_type == "sideline":
            # Warp toward field center (Y=0), 2m from line
            sign = 1 if ball['y'] > 0 else -1
            warp_y = sign * (self.FIELD_Y_MAX - 0.1) - sign * self.BALL_OUT_WARP_DISTANCE
            warp_x = offender_pos['x']
        else:  # goal_line
            sign = 1 if ball['x'] > 0 else -1
            warp_x = sign * (self.FIELD_X_MAX - 0.1) - sign * self.BALL_OUT_WARP_DISTANCE
            warp_y = offender_pos['y']
        return warp_x, warp_y
    
    def _clamp_ball_to_line(self, x, y, out_type):
        """Ball reset position: on the line where it exited."""
        if out_type == "sideline":
            return x, self.FIELD_Y_MAX if y > 0 else -self.FIELD_Y_MAX
        else:  # goal_line — place at goal line
            return self.FIELD_X_MAX if x > 0 else -self.FIELD_X_MAX, 0.0
    
    def _goal_area_corner(self, ball, goal_line_owner):
        """Nearer corner of goal area: X=±3.5, Y=±1.0 nearest to ball exit Y."""
        x = self.GOAL_AREA_X if goal_line_owner == "red" else -self.GOAL_AREA_X
        y = self.GOAL_AREA_Y if ball['y'] > 0 else -self.GOAL_AREA_Y
        return (x, y)
    
    def _corner_flag_position(self, ball):
        """Corner flag just inside field at goal-line/sideline intersection."""
        x = 4.3 if ball['x'] > 0 else -4.3
        y = 2.8 if ball['y'] > 0 else -2.8
        return (x, y)
    
    def _warp_opponents_away(self, ball_pos, restart_team, entities):
        """Warp opponent bots within SET_PIECE_WARP_RADIUS radially away from ball."""
        for bot_id, bot_pos in entities.items():
            if bot_id == 'soccer_ball' or restart_team in bot_id:
                continue
            dist = math.hypot(bot_pos['x'] - ball_pos[0], bot_pos['y'] - ball_pos[1])
            if dist < self.SET_PIECE_WARP_RADIUS:
                if dist < 0.01:
                    angle = 0.0
                else:
                    angle = math.atan2(bot_pos['y'] - ball_pos[1], bot_pos['x'] - ball_pos[0])
                new_x = ball_pos[0] + math.cos(angle) * self.WARP_AWAY_DISTANCE
                new_y = ball_pos[1] + math.sin(angle) * self.WARP_AWAY_DISTANCE
                self._warp_bot(bot_id, new_x, new_y)
    
    def _freeze_team(self, team_to_freeze, entities, duration):
        """Freeze all bots on the given team for `duration` seconds."""
        now = time.time()
        for bot_id in entities:
            if team_to_freeze in bot_id:
                self.frozen_bots[bot_id] = now + duration
    
    def _start_set_piece(self, set_piece_type, ball_pos, restart_team, opponent_team, entities):
        """Unified set-piece: place ball, warp nearby opponents, freeze opponents, start countdown."""
        self._reset_ball(ball_pos[0], ball_pos[1])
        self._warp_opponents_away(ball_pos, restart_team, entities)
        self._freeze_team(opponent_team, entities, self.SET_PIECE_COUNTDOWN)
        self.status = set_piece_type
        self.restart_start_time = time.time()
        self.restart_team = restart_team
        self.restart_pos = {"x": ball_pos[0], "y": ball_pos[1]}
        self.ball_out_event = {"type": set_piece_type, "position": {"x": ball_pos[0], "y": ball_pos[1]}}
        self.foul_event = None
    
    def _warp_bot(self, bot_id, x, y):
        """Warp bot via Gazebo set_entity_state."""
        if not self.set_state_client.service_is_ready():
            return
        req = SetEntityState.Request()
        req.state.name = bot_id
        req.state.reference_frame = 'world'
        req.state.pose.position.x = float(x)
        req.state.pose.position.y = float(y)
        req.state.pose.position.z = 0.1
        req.state.twist.linear.x = 0.0
        req.state.twist.linear.y = 0.0
        req.state.twist.linear.z = 0.0
        self.set_state_client.call_async(req)
    
    def _reset_ball(self, x, y):
        """Place ball at restart position, stationary."""
        if not self.set_state_client.service_is_ready():
            return
        req = SetEntityState.Request()
        req.state.name = 'soccer_ball'
        req.state.reference_frame = 'world'
        req.state.pose.position.x = float(x)
        req.state.pose.position.y = float(y)
        req.state.pose.position.z = 0.10
        req.state.twist.linear.x = 0.0
        req.state.twist.linear.y = 0.0
        req.state.twist.linear.z = 0.0
        self.set_state_client.call_async(req)
    
    def _enforce_freeze(self):
        """Publish zero-twist for frozen bots."""
        now = time.time()
        for bot_id, unfreeze_time in list(self.frozen_bots.items()):
            if now < unfreeze_time:
                # Bot is still frozen → publish zero twist
                if bot_id not in self.freeze_pubs:
                    self.freeze_pubs[bot_id] = self.create_publisher(
                        Twist, f'/{bot_id}/cmd_vel', 10
                    )
                self.freeze_pubs[bot_id].publish(Twist())  # all-zero = stop
            else:
                # Freeze expired → remove
                del self.frozen_bots[bot_id]
    
    def _publish_state(self):
        state = {
            "blue": self.score_blue,
            "red": self.score_red,
            "status": self.status,
            "ball_out_event": self.ball_out_event,
            "restart_team": self.restart_team,
            "restart_pos": self.restart_pos,
            "last_toucher": self.last_toucher,
            "foul": self.foul_event
        }
        out_msg = String()
        out_msg.data = json.dumps(state)
        self.pub.publish(out_msg)

def main():
    rclpy.init()
    node = RefereeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()