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
