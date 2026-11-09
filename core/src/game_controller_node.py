#!/usr/bin/env python3
"""ROS2K GameController receiver / presence announcer.

Compatible with the official RoboCup Humanoid Soccer League GameController
(https://github.com/RoboCup-HumanoidSoccerLeague/GameController).

Scope of this module (session 2026-11-09):
  * RECEIVE the 2 Hz control broadcast (RoboCupGameControlData, UDP 3838).
  * ANNOUNCE robot presence to the GC by sending RoboCupGameControlReturnData
    return packets (UDP 3939, ~2 Hz) so the robot shows up online in the GC UI.
  * Publish the decoded game state as gc_msgs/GCState on /gc/game_state
    (QoS BEST_EFFORT, ROS_DOMAIN_ID=0) for future referee integration.

Out of scope here: the team-message channel (UDP 10000+team) and any
integration into referee_node.py / the bridge. ROS 2 publishing is guarded
so the node also runs headless (decode + return packets) when rclpy or the
gc_msgs package are unavailable (e.g. before the K1 colcon build is done).

Run (laptop smoke / K1, after `source ros2_ws/install/setup.bash`):
    python3 game_controller_node.py --team 50 --player 1
"""
import argparse
import os
import socket
import struct
import sys
import threading
import time

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from std_msgs.msg import Header
    from gc_msgs.msg import GCState
    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False
    Node = object  # type: ignore

# === Protocol constants (mirror game_controller_msgs/headers/RoboCupGameControlData.h) ===
GC_DATA_PORT = 3838          # GC -> robots, UDP broadcast
GC_RETURN_PORT = 3939        # robots -> GC, UDP unicast
GC_STRUCT_HEADER = b"RGme"   # RoboCupGameControlData magic
GC_STRUCT_VERSION = 20
MAX_NUM_PLAYERS = 20
KICKING_TEAM_NONE = 255

GC_RETURN_HEADER = b"RGrt"   # RoboCupGameControlReturnData magic
GC_RETURN_VERSION = 4

# State enums (for human-readable logging only — decoding uses raw bytes).
STATE_NAMES = {
    0: "INITIAL", 1: "READY", 2: "SET", 3: "PLAYING", 4: "FINISHED",
}
SET_PLAY_NAMES = {
    0: "NONE", 1: "DIRECT_FREE_KICK", 2: "INDIRECT_FREE_KICK",
    3: "PENALTY_KICK", 4: "THROW_IN", 5: "GOAL_KICK", 6: "CORNER_KICK",
}
GAME_PHASE_NAMES = {
    0: "NORMAL", 1: "PENALTY_SHOOT_OUT", 2: "EXTRA_TIME", 3: "TIMEOUT",
}
PENALTY_NAMES = {
    0: "NONE", 1: "ILLEGAL_POSITIONING", 2: "MOTION_IN_SET",
    3: "MOTION_IN_STOP", 4: "LOCAL_GAME_STUCK", 5: "INCAPABLE_ROBOT",
    6: "PICK_UP", 7: "BALL_HOLDING", 8: "LEAVING_THE_FIELD",
    9: "PLAYING_WITH_ARMS_HANDS", 10: "PUSHING", 11: "CAUTIONED",
    12: "SENT_OFF", 13: "SUBSTITUTE",
}

# === Behavior tuning ===
RETURN_RATE_HZ = 2.0                       # presence announce rate (rules: 0.5..2 Hz)
GC_STALE_TIMEOUT_S = 5.0                   # stop returning when no GC packet for this long
RECV_BUF_SIZE = 2048

# struct formats — little-endian, fixed-size control packet.
# RoboCupGameControlData: 4s + 10*B + 2h = 18 bytes, then TeamInfo[2].
#   TeamInfo = 6*B (teamNumber..penaltyShot) + 2*H (singleShots, messageBudget)
#              + 20*RobotInfo(3*B) = 6 + 4 + 60 = 70 bytes.
#   Total control packet = 18 + 2*70 = 158 bytes.
_CTRL_HEADER_FMT = "<4sBBBBBBBBBBhh"
_CTRL_HEADER_SIZE = struct.calcsize(_CTRL_HEADER_FMT)
_TEAM_FMT = "<BBBBBBHH" + "BBB" * MAX_NUM_PLAYERS
_TEAM_SIZE = struct.calcsize(_TEAM_FMT)
_CONTROL_PACKET_SIZE = _CTRL_HEADER_SIZE + 2 * _TEAM_SIZE

# Return packet: header[4] + version + playerNum + teamNum + fallen (4 B)
#                + pose[3] (3 floats) + ballAge (float) + ball[2] (2 floats)
#                = 4 + 4 + 12 + 4 + 8 = 32 bytes.
_RETURN_FMT = "<4sBBBB3ff2f"
_RETURN_SIZE = struct.calcsize(_RETURN_FMT)


class GCDecodeError(ValueError):
    """Raised when a control packet fails header/version/size validation."""


def decode_control_packet(data: bytes) -> dict:
    """Decode a RoboCupGameControlData (v20) byte blob into a dict.

    Raises GCDecodeError on bad magic, wrong version, or wrong size.
    Pure stdlib — safe to import from tests without rclpy.
    """
    if len(data) != _CONTROL_PACKET_SIZE:
        raise GCDecodeError(
            f"size {len(data)} != expected {_CONTROL_PACKET_SIZE}")
    (header, version, packet_number, players_per_team, competition_type,
     stopped, game_phase, state, set_play, first_half, kicking_team,
     secs_remaining, secondary_time) = struct.unpack_from(_CTRL_HEADER_FMT, data, 0)
    if header != GC_STRUCT_HEADER:
        raise GCDecodeError(f"bad header magic {header!r}")
    if version != GC_STRUCT_VERSION:
        raise GCDecodeError(f"unsupported version {version} (need {GC_STRUCT_VERSION})")

    teams = []
    offset = _CTRL_HEADER_SIZE
    for _ in range(2):
        (team_number, field_player_colour, goalkeeper_colour, goalkeeper,
         score, penalty_shot, single_shots, message_budget) = struct.unpack_from(
            "<BBBBBBHH", data, offset)
        players = []
        poff = offset + 10  # 6*B + 2*H team header
        for _p in range(MAX_NUM_PLAYERS):
            penalty, secs_till_unpenalised, cautions = struct.unpack_from(
                "<BBB", data, poff)
            players.append({
                "penalty": penalty,
                "secs_till_unpenalised": secs_till_unpenalised,
                "cautions": cautions,
            })
            poff += 3
        teams.append({
            "team_number": team_number,
            "field_player_colour": field_player_colour,
            "goalkeeper_colour": goalkeeper_colour,
            "goalkeeper": goalkeeper,
            "score": score,
            "penalty_shot": penalty_shot,
            "single_shots": single_shots,
            "message_budget": message_budget,
            "players": players,
        })
        offset += _TEAM_SIZE

    return {
        "header": header.decode("ascii", "replace"),
        "version": version,
        "packet_number": packet_number,
        "players_per_team": players_per_team,
        "competition_type": competition_type,
        "stopped": bool(stopped),
        "game_phase": game_phase,
        "state": state,
        "set_play": set_play,
        "first_half": bool(first_half),
        "kicking_team": kicking_team,
        "secs_remaining": secs_remaining,
        "secondary_time": secondary_time,
        "teams": teams,
    }


def build_return_packet(player_num: int, team_num: int,
                        fallen: int = 0,
                        pose=(0.0, 0.0, 0.0),
                        ball_age: float = -1.0,
                        ball=(0.0, 0.0)) -> bytes:
    """Serialize a RoboCupGameControlReturnData (v4) presence packet."""
    return struct.pack(
        _RETURN_FMT,
        GC_RETURN_HEADER,
        GC_RETURN_VERSION,
        int(player_num) & 0xFF,
        int(team_num) & 0xFF,
        int(fallen) & 0xFF,
        float(pose[0]), float(pose[1]), float(pose[2]),
        float(ball_age),
        float(ball[0]), float(ball[1]),
    )


def _find_own_entry(decoded: dict, team_num: int, player_num: int) -> dict | None:
    """Locate this robot's own RobotInfo entry; returns None if not present."""
    player_index = player_num - 1  # GC player numbers are 1-based
    if player_index < 0 or player_index >= MAX_NUM_PLAYERS:
        return None
    for team in decoded["teams"]:
        if team["team_number"] == team_num:
            return team["players"][player_index]
    return None


class _Announcer:
    """Independent return-packet sender thread.

    Announces presence to the GC by unicasting RoboCupGameControlReturnData
    to the address the last control packet came from. Stops returning when
    the GC has not been heard from for GC_STALE_TIMEOUT_S.
    """

    def __init__(self, player_num: int, team_num: int):
        self.player_num = player_num
        self.team_num = team_num
        self._gc_addr: tuple[str, int] | None = None
        self._last_gc_seen = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def note_gc_address(self, addr: tuple[str, int]) -> None:
        with self._lock:
            self._gc_addr = addr
            self._last_gc_seen = time.monotonic()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        period = 1.0 / RETURN_RATE_HZ
        while not self._stop.is_set():
            with self._lock:
                gc_addr = self._gc_addr
                stale = (time.monotonic() - self._last_gc_seen
                         > GC_STALE_TIMEOUT_S) if gc_addr else True
            if gc_addr and not stale:
                pkt = build_return_packet(self.player_num, self.team_num)
                try:
                    self._sock.sendto(pkt, (gc_addr[0], GC_RETURN_PORT))
                except OSError:
                    pass  # transient; next tick retries
            self._stop.wait(period)


class GameControllerNode(Node):
    """rclpy node (used only when rclpy + gc_msgs are importable)."""

    def __init__(self, player_num: int, team_num: int,
                 port_in: int = GC_DATA_PORT):
        super().__init__('game_controller_node')
        self.player_num = player_num
        self.team_num = team_num
        qos = QoSProfile(depth=10,
                         reliability=ReliabilityPolicy.BEST_EFFORT)
        self.pub = self.create_publisher(GCState, '/gc/game_state', qos)
        self._last_state = None
        self._last_penalty = None
        self._announcer = _Announcer(player_num, team_num)
        self._recv_sock = self._make_recv_sock(port_in)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop,
                                        args=(port_in,), daemon=True)
        self._thread.start()
        self._announcer_thread = threading.Thread(
            target=self._announcer.run, daemon=True)
        self._announcer_thread.start()
        self.get_logger().info(
            f"GameController node up: team={team_num} player={player_num} "
            f"listen=0.0.0.0:{port_in} return->{GC_RETURN_PORT}Hz"
            f"{RETURN_RATE_HZ}")

    def _make_recv_sock(self, port_in: int) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("0.0.0.0", port_in))
        s.settimeout(0.5)
        return s

    def _recv_loop(self, port_in: int) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._recv_sock.recvfrom(RECV_BUF_SIZE)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            decoded = decode_control_packet(data)
        except GCDecodeError as exc:
            self.get_logger().warning(
                f"dropped control packet from {addr}: {exc}")
            return
        self._announcer.note_gc_address(addr)
        self._announce_transitions(decoded)
        self._publish(decoded)

    def _announce_transitions(self, decoded: dict) -> None:
        state = decoded["state"]
        if state != self._last_state:
            self._last_state = state
            name = STATE_NAMES.get(state, f"UNKNOWN({state})")
            sp = SET_PLAY_NAMES.get(decoded["set_play"], "?")
            gp = GAME_PHASE_NAMES.get(decoded["game_phase"], "?")
            self.get_logger().info(
                f"GC state -> {name} (phase={gp} set_play={sp} "
                f"kicking_team={decoded['kicking_team']} "
                f"secs_remaining={decoded['secs_remaining']})")
        own = _find_own_entry(decoded, self.team_num, self.player_num)
        if own is not None:
            pen = own["penalty"]
            if pen != self._last_penalty:
                self._last_penalty = pen
                pname = PENALTY_NAMES.get(pen, f"UNKNOWN({pen})")
                self.get_logger().info(
                    f"own penalty -> {pname} "
                    f"(secs_till_unpenalised={own['secs_till_unpenalised']})")

    def _publish(self, decoded: dict) -> None:
        msg = GCState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "gc"
        msg.packet_number = decoded["packet_number"]
        msg.players_per_team = decoded["players_per_team"]
        msg.competition_type = decoded["competition_type"]
        msg.stopped = decoded["stopped"]
        msg.game_phase = decoded["game_phase"]
        msg.state = decoded["state"]
        msg.set_play = decoded["set_play"]
        msg.first_half = decoded["first_half"]
        msg.kicking_team = decoded["kicking_team"]
        msg.secs_remaining = decoded["secs_remaining"]
        msg.secondary_time = decoded["secondary_time"]
        msg.team_number = [decoded["teams"][0]["team_number"],
                           decoded["teams"][1]["team_number"]]
        msg.score = [decoded["teams"][0]["score"],
                     decoded["teams"][1]["score"]]
        msg.message_budget = [decoded["teams"][0]["message_budget"],
                              decoded["teams"][1]["message_budget"]]
        own = _find_own_entry(decoded, self.team_num, self.player_num)
        if own is not None:
            msg.penalty = own["penalty"]
            msg.secs_till_unpenalised = own["secs_till_unpenalised"]
        self.pub.publish(msg)

    def shutdown(self) -> None:
        self._stop.set()
        self._announcer.stop()
        try:
            self._recv_sock.close()
        except OSError:
            pass


class _HeadlessRunner:
    """Fallback runner when rclpy / gc_msgs are not available.

    Same receive + announce behavior, console logging only.
    """

    def __init__(self, player_num: int, team_num: int,
                 port_in: int = GC_DATA_PORT):
        self.player_num = player_num
        self.team_num = team_num
        self._last_state = None
        self._last_penalty = None
        self._announcer = _Announcer(player_num, team_num)
        self._recv_sock = self._make_recv_sock(port_in)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop,
                                        args=(port_in,), daemon=True)
        self._announcer_thread = threading.Thread(
            target=self._announcer.run, daemon=True)
        print(f"[game_controller_node] headless: team={team_num} "
              f"player={player_num} listen=0.0.0.0:{port_in} "
              f"return->{GC_RETURN_PORT}@{RETURN_RATE_HZ}Hz")

    def _make_recv_sock(self, port_in: int) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("0.0.0.0", port_in))
        s.settimeout(0.5)
        return s

    def _recv_loop(self, port_in: int) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._recv_sock.recvfrom(RECV_BUF_SIZE)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            decoded = decode_control_packet(data)
        except GCDecodeError as exc:
            print(f"[game_controller_node] dropped packet from {addr}: {exc}")
            return
        self._announcer.note_gc_address(addr)
        self._announce_transitions(decoded)

    def _announce_transitions(self, decoded: dict) -> None:
        state = decoded["state"]
        if state != self._last_state:
            self._last_state = state
            name = STATE_NAMES.get(state, f"UNKNOWN({state})")
            sp = SET_PLAY_NAMES.get(decoded["set_play"], "?")
            gp = GAME_PHASE_NAMES.get(decoded["game_phase"], "?")
            print(f"[game_controller_node] GC state -> {name} "
                  f"(phase={gp} set_play={sp} "
                  f"kicking_team={decoded['kicking_team']} "
                  f"secs_remaining={decoded['secs_remaining']})")
        own = _find_own_entry(decoded, self.team_num, self.player_num)
        if own is not None:
            pen = own["penalty"]
            if pen != self._last_penalty:
                self._last_penalty = pen
                pname = PENALTY_NAMES.get(pen, f"UNKNOWN({pen})")
                print(f"[game_controller_node] own penalty -> {pname} "
                      f"(secs_till_unpenalised="
                      f"{own['secs_till_unpenalised']})")

    def run(self) -> None:
        self._thread.start()
        self._announcer_thread.start()
        try:
            while not self._stop.is_set():
                self._stop.wait(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop.set()
        self._announcer.stop()
        try:
            self._recv_sock.close()
        except OSError:
            pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", type=int, default=50,
                        help="team number (default 50 = R-ZWEI KICKERS)")
    parser.add_argument("--player", type=int, required=True,
                        help="player number, 1-based (1..MAX_NUM_PLAYERS)")
    parser.add_argument("--port-in", type=int, default=GC_DATA_PORT,
                        help=f"UDP port to listen for GC control (default {GC_DATA_PORT})")
    parser.add_argument("--port-out", type=int, default=GC_RETURN_PORT,
                        help=f"UDP port to send return packets to (default {GC_RETURN_PORT})")
    args = parser.parse_args(argv)

    if not (1 <= args.player <= MAX_NUM_PLAYERS):
        print(f"--player must be in 1..{MAX_NUM_PLAYERS}", file=sys.stderr)
        return 2

    if HAS_RCLPY:
        rclpy.init(args=[])
        node = GameControllerNode(args.player, args.team, args.port_in)
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.shutdown()
            rclpy.shutdown()
        return 0

    runner = _HeadlessRunner(args.player, args.team, args.port_in)
    runner.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
