"""Unit tests for wireless UDP telemetry ingestion and multi-node synchronization."""
import json
import queue
import socket
import tempfile
import time
from pathlib import Path
import pytest

from collector.recording import RecordingEngine
from collector.session_manager import SessionConfig


def test_udp_wireless_stream_and_sync():
    packet_q = queue.Queue()
    engine = RecordingEngine(packet_q)
    # Use an unreserved local test port to avoid conflicts
    engine.udp_port = 5098

    try:
        engine.start_stream(port="Wireless Wi-Fi (UDP :5098)")
        time.sleep(0.3)  # Allow socket bind

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 1. Send heartbeats from Node A and Node B
        hb_a = json.dumps({"type": "heartbeat", "node": "NODE_A", "mac": "24:6F:28:1A:4C:01"})
        hb_b = json.dumps({"type": "heartbeat", "node": "NODE_B", "mac": "24:6F:28:1A:4C:02"})
        client.sendto(hb_a.encode("utf-8"), ("127.0.0.1", 5098))
        client.sendto(hb_b.encode("utf-8"), ("127.0.0.1", 5098))

        time.sleep(0.2)
        status = engine.get_nodes_sync_status()
        assert status["online_count"] == 2
        assert status["nodes"]["NODE_A"]["online"] is True
        assert status["nodes"]["NODE_B"]["online"] is True
        assert status["in_sync"] is False  # Only 2 of 4 online so far

        # 2. Send observations from all 4 nodes
        for node_id in ("NODE_A", "NODE_B", "NODE_C", "NODE_D"):
            obs = json.dumps({
                "type": "raw",
                "node": node_id,
                "tag": "52:06:26:03:01:DA",
                "rssi": -65,
                "timestamp": int(time.time() * 1000)
            })
            client.sendto(obs.encode("utf-8"), ("127.0.0.1", 5098))

        time.sleep(0.3)
        final_status = engine.get_nodes_sync_status()
        assert final_status["online_count"] == 4
        assert final_status["in_sync"] is True

        # 3. Check packet queue receipt
        received_nodes = []
        while not packet_q.empty():
            pkt = packet_q.get_nowait()
            received_nodes.append(pkt.get("node_key"))

        assert "NODE_A" in received_nodes
        assert "NODE_B" in received_nodes
        assert "NODE_C" in received_nodes
        assert "NODE_D" in received_nodes

        client.close()
    finally:
        engine.stop_all()


def test_udp_recording_to_dataset():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        session = SessionConfig(
            session_name="test_wireless_01",
            raw_dir=tmp_path,
            target_mac="52:06:26:03:01:DA",
            distance_m=2.5,
            anchor_id="ALL_ANCHORS",
            condition="Line-of-Sight (LOS)",
            tag_height_m=1.0,
            notes="Wireless unit test",
            target_samples=10,
            obstacle="No",
            obstacle_type="None",
            motion="stationary",
            data_source="Wireless Wi-Fi",
        )

        packet_q = queue.Queue()
        engine = RecordingEngine(packet_q)
        engine.udp_port = 5099

        try:
            engine.start_recording(session, port="Wireless Wi-Fi (UDP :5099)")
            time.sleep(0.3)

            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(5):
                obs = json.dumps({
                    "type": "raw",
                    "node": "NODE_A",
                    "tag": "52:06:26:03:01:DA",
                    "rssi": -60,
                    "timestamp": int(time.time() * 1000)
                })
                client.sendto(obs.encode("utf-8"), ("127.0.0.1", 5099))
                time.sleep(0.05)

            time.sleep(0.3)
            summary = engine.stop_recording()
            assert summary["total_samples"] >= 1
            assert session.target_file_path.exists()
            assert session.target_file_path.stat().st_size > 0
            client.close()
        finally:
            engine.stop_all()


def test_udp_ignores_collector_self_announce_loopback():
    """The collector's own COLLECTOR_ANNOUNCE broadcast loops back on the local host
    (Windows delivers 255.255.255.255 broadcasts to the sender) and must never be
    ingested as anchor telemetry, otherwise NODE_A appears online with no board."""
    packet_q = queue.Queue()
    engine = RecordingEngine(packet_q)
    try:
        announce = json.dumps({
            "cmd": "COLLECTOR_ANNOUNCE",
            "host_ip": "192.168.1.50",
            "port": 5005,
            "timestamp": int(time.time() * 1000),
        })
        engine._process_incoming_wireless_packet(announce, "192.168.1.50")

        # Typeless junk is not anchor telemetry either
        engine._process_incoming_wireless_packet(json.dumps({"foo": "bar"}), "192.168.1.50")

        status = engine.get_nodes_sync_status()
        assert status["online_count"] == 0
        assert status["nodes"]["NODE_A"]["online"] is False
        assert engine.node_health["NODE_A"]["packets"] == 0
        assert packet_q.empty()
    finally:
        engine.stop_all()


def test_wireless_packets_attributed_by_hardware_mac_not_claimed_id(monkeypatch):
    """A board whose silicon MAC is bound to NODE_A must be attributed to NODE_A
    even when its firmware claims a different node ID (misprovisioned board)."""
    packet_q = queue.Queue()
    engine = RecordingEngine(packet_q)
    try:
        import collector.recording as rec
        bound_mac = "AA:BB:CC:11:22:33"
        monkeypatch.setattr(
            rec, "get_node_by_mac",
            lambda mac: ("NODE_A", {"anchor_id": "ANCHOR_01", "mac": mac}) if mac == bound_mac else None,
        )

        spoofed = json.dumps({
            "type": "raw",
            "node": "NODE_B",
            "mac": bound_mac,
            "tag": "52:06:26:03:01:DA",
            "rssi": -70,
            "timestamp": int(time.time() * 1000),
        })
        engine._process_incoming_wireless_packet(spoofed, "192.168.1.55")

        assert engine.node_health["NODE_A"]["online"] is True
        assert engine.node_health["NODE_A"]["packets"] == 1
        assert engine.node_health["NODE_B"]["online"] is False
        assert engine.node_identity_conflicts.get("NODE_A", 0) >= 1

        pkt = packet_q.get_nowait()
        assert pkt["node_key"] == "NODE_A"
    finally:
        engine.stop_all()

