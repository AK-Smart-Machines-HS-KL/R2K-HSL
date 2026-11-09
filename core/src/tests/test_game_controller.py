#!/usr/bin/env python3
"""Unit tests for game_controller_node.py — HSL GameController protocol codec.

Fast tier (no ROS 2 / no Gazebo required). Exercises the pure-stdlib
decode_control_packet / build_return_packet helpers and the transition
helpers against hand-crafted RoboCupGameControlData (v20) byte blobs.
"""
import os
import socket
import struct
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import game_controller_node as gcn  # noqa: E402


# === fixtures ============================================================
MAX_P = gcn.MAX_NUM_PLAYERS


def _team_bytes(team_number, score=0, message_budget=1200,
                player_penalties=None):
    """Build a 70-byte TeamInfo blob."""
    player_penalties = player_penalties or {}
    players = b""
    for i in range(MAX_P):
        pen, secs, caut = player_penalties.get(i, (0, 0, 0))
        players += struct.pack("<BBB", pen, secs, caut)
    return (struct.pack("<BBBBBBHH",
                        team_number & 0xFF, 0, 0, 1, score & 0xFF, 0, 0,
                        message_budget & 0xFFFF)
            + players)


def _control_packet(*, packet_number=0, players_per_team=3,
                    competition_type=2, stopped=0, game_phase=0,
                    state=3, set_play=0, first_half=1, kicking_team=50,
                    secs_remaining=600, secondary_time=0,
                    team0=None, team1=None):
    team0 = team0 if team0 is not None else _team_bytes(50, score=2)
    team1 = team1 if team1 is not None else _team_bytes(7, score=0)
    header = struct.pack(
        gcn._CTRL_HEADER_FMT, gcn.GC_STRUCT_HEADER, gcn.GC_STRUCT_VERSION,
        packet_number, players_per_team, competition_type, stopped,
        game_phase, state, set_play, first_half, kicking_team,
        secs_remaining, secondary_time)
    return header + team0 + team1


# === decode ==============================================================
def test_decode_basic_fields():
    d = gcn.decode_control_packet(_control_packet(
        packet_number=42, players_per_team=4, state=gcn.STATE_NAMES and 2,
        set_play=5, first_half=0, kicking_team=7, secs_remaining=300,
        secondary_time=15))
    assert d["packet_number"] == 42
    assert d["players_per_team"] == 4
    assert d["state"] == 2
    assert d["set_play"] == 5
    assert d["first_half"] is False
    assert d["kicking_team"] == 7
    assert d["secs_remaining"] == 300
    assert d["secondary_time"] == 15
    assert d["stopped"] is False
    assert len(d["teams"]) == 2
    assert d["teams"][0]["team_number"] == 50
    assert d["teams"][0]["score"] == 2
    assert d["teams"][1]["team_number"] == 7
    assert len(d["teams"][0]["players"]) == MAX_P


def test_decode_player_penalties():
    team0 = _team_bytes(50, player_penalties={
        0: (gcn.PENALTY_NAMES and 10, 30, 0),   # player 1: PUSHING, 30s
        4: (6, 0, 1),                            # player 5: PICK_UP, 1 caution
    })
    d = gcn.decode_control_packet(_control_packet(team0=team0))
    p1 = d["teams"][0]["players"][0]
    assert p1["penalty"] == 10
    assert p1["secs_till_unpenalised"] == 30
    p5 = d["teams"][0]["players"][4]
    assert p5["penalty"] == 6
    assert p5["cautions"] == 1


def test_decode_message_budget_uint16():
    team0 = _team_bytes(50, message_budget=1000)
    d = gcn.decode_control_packet(_control_packet(team0=team0))
    assert d["teams"][0]["message_budget"] == 1000


def test_decode_rejects_bad_magic():
    pkt = _control_packet()
    bad = bytearray(pkt)
    bad[0:4] = b"RGxx"
    with pytest.raises(gcn.GCDecodeError, match="bad header magic"):
        gcn.decode_control_packet(bytes(bad))


def test_decode_rejects_bad_version():
    pkt = _control_packet()
    bad = bytearray(pkt)
    bad[4] = 5
    with pytest.raises(gcn.GCDecodeError, match="unsupported version"):
        gcn.decode_control_packet(bytes(bad))


def test_decode_rejects_bad_size():
    with pytest.raises(gcn.GCDecodeError, match="size"):
        gcn.decode_control_packet(b"RGme" + b"\x00" * 10)


def test_control_packet_size_is_158():
    assert gcn._CONTROL_PACKET_SIZE == 158
    assert len(_control_packet()) == 158


# === return packet =======================================================
def test_return_packet_header_and_version():
    r = gcn.build_return_packet(1, 50)
    assert r[:4] == gcn.GC_RETURN_HEADER
    assert r[4] == gcn.GC_RETURN_VERSION
    assert len(r) == gcn._RETURN_SIZE


def test_return_packet_fields_roundtrip():
    r = gcn.build_return_packet(player_num=3, team_num=50, fallen=1,
                                pose=(100.0, -200.0, 1.5),
                                ball_age=2.5, ball=(300.0, 50.0))
    (_hdr, _ver, player, team, fallen, px, py, pth, ballage, bx, by) = \
        struct.unpack(gcn._RETURN_FMT, r)
    assert _hdr == gcn.GC_RETURN_HEADER
    assert _ver == gcn.GC_RETURN_VERSION
    assert (player, team, fallen) == (3, 50, 1)
    assert (px, py, pth) == (100.0, -200.0, 1.5)
    assert ballage == 2.5
    assert (bx, by) == (300.0, 50.0)


def test_return_packet_defaults_presence():
    r = gcn.build_return_packet(1, 50)
    (_hdr, _ver, player, team, fallen, px, py, pth, ballage, bx, by) = \
        struct.unpack(gcn._RETURN_FMT, r)
    assert fallen == 0
    assert (px, py, pth) == (0.0, 0.0, 0.0)
    assert ballage == -1.0
    assert (bx, by) == (0.0, 0.0)


# === presence announcer ==================================================
def test_announcer_sends_return_packet_to_gc_address():
    # Bind a sink on an ephemeral port to stand in for the GC's 3939.
    sink = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sink.bind(("127.0.0.1", 0))
    sink_port = sink.getsockname()[1]
    sink.settimeout(3.0)

    # Patch the announcer's return port to the sink port.
    ann = gcn._Announcer(player_num=4, team_num=50)
    orig_port = gcn.GC_RETURN_PORT
    gcn.GC_RETURN_PORT = sink_port
    try:
        ann.note_gc_address(("127.0.0.1", 3838))
        t = threading.Thread(target=ann.run, daemon=True)
        t.start()
        data, addr = sink.recvfrom(64)
        ann.stop()
        t.join(timeout=2.0)
    finally:
        gcn.GC_RETURN_PORT = orig_port
        sink.close()

    assert data[:4] == gcn.GC_RETURN_HEADER
    _hdr, _ver, player, team, fallen, *_ = struct.unpack(gcn._RETURN_FMT, data)
    assert (player, team) == (4, 50)


def test_announcer_stops_when_gc_goes_stale():
    ann = gcn._Announcer(player_num=1, team_num=50)
    # Never call note_gc_address -> no GC known -> must not send.
    sink = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sink.bind(("127.0.0.1", 0))
    sink.settimeout(0.6)
    gcn.GC_RETURN_PORT = sink.getsockname()[1]
    t = threading.Thread(target=ann.run, daemon=True)
    t.start()
    with pytest.raises(socket.timeout):
        sink.recvfrom(64)
    ann.stop()
    sink.close()


# === own-entry lookup ====================================================
def test_find_own_entry_present():
    team0 = _team_bytes(50, player_penalties={2: (10, 30, 0)})
    d = gcn.decode_control_packet(_control_packet(team0=team0))
    own = gcn._find_own_entry(d, team_num=50, player_num=3)
    assert own is not None
    assert own["penalty"] == 10


def test_find_own_entry_missing_team():
    d = gcn.decode_control_packet(_control_packet())
    assert gcn._find_own_entry(d, team_num=99, player_num=1) is None


def test_find_own_entry_player_out_of_range():
    d = gcn.decode_control_packet(_control_packet())
    assert gcn._find_own_entry(d, team_num=50, player_num=0) is None
    assert gcn._find_own_entry(d, team_num=50, player_num=MAX_P + 1) is None


# === end-to-end receive loop (headless) ==================================
def test_headless_runner_receives_and_announces(monkeypatch):
    # Bind the runner on an ephemeral port and feed it a crafted packet.
    runner = gcn._HeadlessRunner(player_num=1, team_num=50, port_in=0)
    in_port = runner._recv_sock.getsockname()[1]

    # Capture the GC address the announcer learns.
    captured = {}
    orig_note = runner._announcer.note_gc_address
    def spy(addr):
        captured["addr"] = addr
        orig_note(addr)
    runner._announcer.note_gc_address = spy

    runner._thread.start()
    runner._announcer_thread.start()

    # Sink for the return packet.
    sink = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sink.bind(("127.0.0.1", 0))
    sink.settimeout(3.0)
    gcn.GC_RETURN_PORT = sink.getsockname()[1]

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sender.sendto(_control_packet(state=1), ("127.0.0.1", in_port))
    sender.close()

    ret, _ = sink.recvfrom(64)
    assert ret[:4] == gcn.GC_RETURN_HEADER

    runner.shutdown()
    sink.close()
    assert captured["addr"][0] == "127.0.0.1"
