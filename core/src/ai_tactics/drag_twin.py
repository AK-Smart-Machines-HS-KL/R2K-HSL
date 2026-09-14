#!/usr/bin/env python3
"""Drag-Twin: move a sim bot in Gazebo (drag) -> its hardware mirror walks there.

Standalone ROS2 node, started only in demo mode (launch_r2k.sh --demo).

ARCHITECTURE FACT (lab-verified 2026-08-31): a sim bot and its hardware
mirror share ONE command stream -- /blue_N/cmd_vel drives the Gazebo
diff-drive plugin AND the Yahboom driver. The bridge PD reference is the
SIM bot's Gazebo-truth position. Dispatching "goto <drop>" for the
dragged bot is therefore self-referential (reference == target -> zero
velocity): the hardware twin never marches. The only way to march the
twin to the dropped position is to move the PD reference AWAY from the
target first.

Fix ("teleport-back + march"): when the drag settles, the sim bot is
teleported back to its pre-drag position (where the hardware twin stands)
via /gazebo/set_entity_state (same service as phantom kicks), THEN the
goto is dispatched. The PD walks the sim bot AND its hardware mirror
from there to the dropped position -- the twin marches, the sim bot ends
at the drop as the marker. Bots without a hardware twin (virtual-only
relay) keep the old behavior: the dragged position IS the position, no
teleport.

Detection: two passive channels (no jump thresholds):
1. Waypath watch: while a bot has an active Move target, sustained growth
   of its distance-to-target means something external moved it (drag/push
   against the PD) -> abort the waypath.
2. Idle watch: while a bot has NO Move target (parked/held), any drift
   away from its anchor position is external (the PD publishes zeros).

Both channels dispatch through the evaluator task-input path
(shared_state/task_input.json): detection -> "<bot> stop" (instant waypath
abort + active brake), settle -> "<bot> goto <final sim pose>" (coordinate
fast-path, instant per-bot Move). Dragging never touches other bots.
"""
import json
import math
import os
import time

try:
    import rclpy
    from rclpy.node import Node
    from gazebo_msgs.msg import ModelStates
    from gazebo_msgs.srv import SetEntityState
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORLD_STATE_PATH = os.path.join(BASE_DIR, "shared_state", "Worldstate.json")
TASK_INPUT_PATH = os.path.join(BASE_DIR, "shared_state", "task_input.json")
STRATEGY_PATH = os.path.join(BASE_DIR, "shared_state", "current_strategy.json")
RELAY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "active_relay.json")

EXTERNAL_MOVE_M = 0.3       # displacement treated as an external move (drag/push)
STABLE_EPS_M = 0.08          # per-tick movement considered "holding still"
TRACK_SETTLE_S = 0.4         # quiet time before the dragged position counts as final
AWAIT_TARGET_TIMEOUT_S = 2.0  # goto dispatched but strategy Move never appears
DRAG_COOLDOWN_S = 1.0        # min time between drag-event starts per bot
TASK_ROUNDING = 0.05         # coordinate rounding for the dispatched goto task
TARGET_REFRESH_S = 0.5       # how often commanded targets are re-read from current_strategy.json


def hardware_twins_from_relay(relay_data):
    """Sim bot names that have a hardware mirror (teleport-back applies).
    A relay entry with hardware_type != virtual mirrors the sim bot named
    by mirror_of (or the entry name itself) -- those sim bots get the
    teleport-back treatment so their hardware twin marches."""
    twins = set()
    for hw_name, info in (relay_data.get("mapping") or {}).items():
        if not isinstance(info, dict):
            continue
        if str(info.get("hardware_type", "virtual")).lower() == "virtual":
            continue
        twins.add(info.get("mirror_of", hw_name))
    return twins


class DragDetector:
    """Pure state machine: feed commanded targets + sim poses, get tasks.

    Drag protocol:
      detection  -> "<bot> stop" (instant waypath abort + active brake);
                    drag_origin = the bot's position one tick before the
                    displacement (where the hardware twin stands)
      tracking   -> follow the sim bot until it holds still for
                    TRACK_SETTLE_S (user may keep dragging)
      settle     -> "<bot> goto <final sim pose>" dispatched; detector
                    enters "awaiting_target" (detection suppressed) until
                    the strategy Move appears (or timeout) so the
                    teleport-back + march is never read as a new drag.
    """

    def __init__(self, status_fn=None, now_fn=time.time):
        self._status_fn = status_fn or (lambda: "playing")
        self._now_fn = now_fn
        self._watch = {}  # bot -> state dict (see note_target)

    def note_target(self, name, target):
        """Feed the commanded target (None = parked/held) from the strategy.
        Re-arms the watches whenever the target changes. A pending goto
        (awaiting_target) is released when its Move lands in the strategy."""
        st = self._watch.setdefault(
            name, {"target": None, "min_dist": float("inf"), "anchor": None,
                   "phase": None, "track_pos": None, "track_t": 0.0,
                   "last_pos": None, "drag_origin": None, "await_t": 0.0})
        if st["target"] != target:
            st["target"] = target
            st["min_dist"] = float("inf")
            st["anchor"] = None
            if st["phase"] == "awaiting_target" and target is not None:
                st["phase"] = None

    def check_move(self, name, x, y):
        """Detect an external move of the sim bot; returns a task or None."""
        st = self._watch.get(name)
        if st is None:
            return None
        task = self._check_state(name, st, x, y)
        st["last_pos"] = (x, y)
        return task

    def _check_state(self, name, st, x, y):
        if self._status_fn() != "playing":
            return None
        now = self._now_fn()
        if st["phase"] == "awaiting_target":
            # Detection suppressed: the teleport-back + march must not be
            # read as a new drag. Released by note_target (Move appears) or
            # timeout (evaluator failed to write the Move) -- the release
            # tick falls through so the watches arm at the current position.
            if now - st["await_t"] >= AWAIT_TARGET_TIMEOUT_S:
                st["phase"] = None
                st["anchor"] = None
                st["min_dist"] = float("inf")
            else:
                return None
        if st["phase"] == "tracking":
            if math.hypot(x - st["track_pos"][0], y - st["track_pos"][1]) > STABLE_EPS_M:
                st["track_pos"] = (x, y)
                st["track_t"] = now
            elif now - st["track_t"] >= TRACK_SETTLE_S:
                st["phase"] = "awaiting_target"
                st["await_t"] = now
                return self._goto_task(name, x, y)
            return None
        displaced = False
        if st["target"] is not None:
            d = math.hypot(x - st["target"][0], y - st["target"][1])
            if d < st["min_dist"]:
                st["min_dist"] = d
            elif d - st["min_dist"] > EXTERNAL_MOVE_M:
                st["min_dist"] = d
                displaced = True
        else:
            if st["anchor"] is None:
                st["anchor"] = (x, y)
            elif math.hypot(x - st["anchor"][0], y - st["anchor"][1]) > EXTERNAL_MOVE_M:
                st["anchor"] = (x, y)
                displaced = True
        if displaced:
            st["drag_origin"] = st["last_pos"] or (x, y)
            st["phase"] = "tracking"
            st["track_pos"] = (x, y)
            st["track_t"] = now
            return f"{name} stop"
        return None

    def drag_origin(self, name):
        """Pre-drag position of the bot (where its hardware twin stands)."""
        st = self._watch.get(name)
        return st.get("drag_origin") if st else None

    def _goto_task(self, name, x, y):
        fx = round(x / TASK_ROUNDING) * TASK_ROUNDING
        fy = round(y / TASK_ROUNDING) * TASK_ROUNDING
        return f"{name} goto {fx:.2f},{fy:.2f}"


if ROS_AVAILABLE:

    class DragTwinNode(Node):
        def __init__(self):
            super().__init__('drag_twin')
            self.detector = DragDetector(status_fn=self._match_status)
            self._last_dispatch = {}
            self._teleport_bots = self._load_teleport_bots()
            self._set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
            self.create_subscription(ModelStates, '/gazebo/model_states', self.cb, 10)
            self.create_timer(TARGET_REFRESH_S, self._refresh_targets)
            self.get_logger().info(
                "🪏 Drag-Twin online: drag a sim blue bot in Gazebo -> its hardware "
                f"mirror marches there (teleport-back bots: {sorted(self._teleport_bots) or 'none'})")

        def _load_teleport_bots(self):
            """Sim bots with a hardware twin (relay hardware_type != virtual)."""
            try:
                with open(RELAY_PATH, 'r') as f:
                    return hardware_twins_from_relay(json.load(f))
            except Exception as e:
                self.get_logger().warning(
                    f"Relay profile unreadable ({e}) -- no teleport-back, "
                    "dragged sim bots keep the self-referential goto (sim-only behavior)")
                return set()

        def _match_status(self):
            try:
                with open(WORLD_STATE_PATH, 'r') as f:
                    return json.load(f).get("match_state", {}).get("status", "playing")
            except Exception:
                return "unknown"

        def _refresh_targets(self):
            """Read commanded targets and arm the watches per bot."""
            try:
                with open(STRATEGY_PATH, 'r') as f:
                    assignments = json.load(f).get("assignments", {})
            except Exception:
                return
            for name, task in assignments.items():
                if not name.startswith("blue"):
                    continue
                target = None
                if isinstance(task, dict) and task.get("action", "").lower() == "move" \
                        and "x" in task and "y" in task:
                    target = (float(task["x"]), float(task["y"]))
                self.detector.note_target(name, target)

        def cb(self, msg):
            try:
                for name, pose in zip(msg.name, msg.pose):
                    if not name.startswith("blue"):
                        continue
                    task = self.detector.check_move(name, pose.position.x, pose.position.y)
                    if task:
                        is_goto = " goto " in task
                        if is_goto:
                            # Teleport FIRST (fire-and-forget): while the goto
                            # travels through the evaluator (~100ms), the
                            # strategy still holds Hold -> nothing moves until
                            # both the teleport and the Move are in effect.
                            self._teleport_to_origin(name, pose)
                        self._dispatch(name, task, urgent=is_goto)
            except Exception as e:
                self.get_logger().error(f"Drag-Twin error: {e}")

        def _teleport_to_origin(self, name, pose):
            """Put the dragged sim bot back at its pre-drag position so the
            bridge PD walks it (and its hardware mirror) to the drop."""
            if name not in self._teleport_bots:
                return
            origin = self.detector.drag_origin(name)
            if origin is None:
                return
            req = SetEntityState.Request()
            req.state.name = name
            req.state.reference_frame = 'world'
            req.state.pose.position.x = float(origin[0])
            req.state.pose.position.y = float(origin[1])
            req.state.pose.position.z = pose.position.z
            req.state.pose.orientation = pose.orientation  # keep current heading
            self._set_state_client.call_async(req)
            self.get_logger().info(
                f"🪏 Teleported {name} back to its twin at "
                f"({origin[0]:.2f}, {origin[1]:.2f}) -- marching to the drop next")

        def _dispatch(self, name, task, urgent=False):
            now = time.time()
            if not urgent and now - self._last_dispatch.get(name, 0.0) < DRAG_COOLDOWN_S:
                return
            if urgent:
                self._last_dispatch[name] = now
            try:
                payload = {"task": task, "timestamp": now}
                with open(TASK_INPUT_PATH + ".tmp", 'w') as f:
                    json.dump(payload, f)
                os.replace(TASK_INPUT_PATH + ".tmp", TASK_INPUT_PATH)
                # The stack may run mixed-identity (docker root / native user);
                # keep the task-input handoff writable by both sides.
                try:
                    os.chmod(TASK_INPUT_PATH, 0o666)
                except OSError:
                    pass
                self.get_logger().info(f"🪏 Dispatched: \"{task}\"")
            except Exception as e:
                self.get_logger().error(f"Dispatch failed: {e}")


def main():
    if not ROS_AVAILABLE:
        raise SystemExit("drag_twin requires ROS 2 (rclpy) — run inside the ROS 2 environment")
    rclpy.init()
    node = DragTwinNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()