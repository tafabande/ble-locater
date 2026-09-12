"""Unit tests for indoor positioning shared core library modules."""
import os
import sys
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    BACKEND_PORT, DASHBOARD_PORT, DEFAULT_ANCHORS_CONFIG,
    load_anchor_config, load_anchor_metadata, get_python_executable
)
from core.ble import (
    parse_stream_line, calculate_log_distance, RawPacket, WindowObservation
)
from core.telemetry import NodeTelemetry, SystemTelemetryManager
from core.inference import validate_feature_schema, predict_distance
from core.data import init_raw_dataset_file, append_raw_record, validate_dataset_for_training


def test_core_config_defaults():
    assert BACKEND_PORT > 0
    assert DASHBOARD_PORT > 0
    assert "ANCHOR_01" in DEFAULT_ANCHORS_CONFIG
    assert len(DEFAULT_ANCHORS_CONFIG) >= 4

    anchors = load_anchor_config()
    assert "ANCHOR_01" in anchors
    assert len(anchors["ANCHOR_01"]) == 2

    meta = load_anchor_metadata()
    assert "ANCHOR_01" in meta
    assert "mac" in meta["ANCHOR_01"]

    py_exe = get_python_executable()
    assert os.path.exists(py_exe)


def test_core_ble_packet_parsing():
    # 1. JSON Observation line
    json_obs = '{"type": "observation", "anchor_id": "ANCHOR_01", "device_mac": "AA:BB:CC:DD:EE:FF", "packet_count": 12, "rssi_mean": -65.4}'
    rec_type, parsed = parse_stream_line(json_obs)
    assert rec_type == "observation"
    assert parsed["anchor_id"] == "ANCHOR_01"
    assert parsed["packet_count"] == 12
    assert parsed["rssi_mean"] == -65.4

    # 2. JSON Raw line
    json_raw = '{"anchor_id": "ANCHOR_02", "mac": "11:22:33:44:55:66", "rssi": -72}'
    rec_type, parsed = parse_stream_line(json_raw)
    assert rec_type == "raw_packet"
    assert parsed["anchor_id"] == "ANCHOR_02"
    assert parsed["rssi"] == -72

    # 3. CSV raw line
    csv_line = "1700000000000,ANCHOR_03,AA:BB:CC:11:22:33,-58,2.5,4.0"
    rec_type, parsed = parse_stream_line(csv_line)
    assert rec_type == "raw_packet"
    assert parsed["anchor_id"] == "ANCHOR_03"
    assert parsed["rssi"] == -58
    assert parsed["true_x"] == 2.5
    assert parsed["true_y"] == 4.0

    # 4. Invalid line
    rec_type, parsed = parse_stream_line("invalid gibberish with no commas")
    assert rec_type is None
    assert parsed is None


def test_core_ble_log_distance():
    d_close = calculate_log_distance(-59.0, tx_power_1m=-59.0, path_loss_exponent=2.7)
    assert pytest.approx(d_close, abs=0.05) == 1.0

    d_far = calculate_log_distance(-86.0, tx_power_1m=-59.0, path_loss_exponent=2.7)
    assert d_far > 5.0

    # Test edge cases (non-positive or nan)
    assert calculate_log_distance(0.0) == 0.1
    assert calculate_log_distance(float("nan")) == 0.1


def test_core_telemetry_node_tracking():
    node = NodeTelemetry(anchor_id="ANCHOR_TEST")
    assert node.status == "OFFLINE"

    # Record packets
    node.record_packet(-60)
    node.record_packet(-62)
    node.record_packet(-58)
    assert node.status == "ONLINE"
    assert node.packet_count == 3
    assert pytest.approx(node.average_rssi, abs=0.1) == -60.0

    node.record_drop()
    assert node.dropped_packets == 1

    d = node.to_dict()
    assert d["anchor_id"] == "ANCHOR_TEST"
    assert d["packet_count"] == 3
    assert d["dropped_packets"] == 1


def test_core_telemetry_system_manager():
    mgr = SystemTelemetryManager(["ANCHOR_01", "ANCHOR_02"])
    assert len(mgr.nodes) == 2

    node1 = mgr.get_or_create_node("ANCHOR_01")
    node1.record_packet(-65)

    tele = mgr.get_full_telemetry()
    assert tele["total_nodes"] == 2
    assert tele["online_nodes"] == 1
    assert tele["total_packets"] == 1
    assert "host_resources" in tele


def test_core_inference_schema_validation():
    required_cols = ["rssi_mean", "rssi_std", "rssi_min"]
    features_valid = {"rssi_mean": -65.0, "rssi_std": 1.5, "rssi_min": -70, "extra": 42}
    valid, missing = validate_feature_schema(features_valid, required_cols)
    assert valid is True
    assert missing == []

    features_invalid = {"rssi_mean": -65.0}
    valid, missing = validate_feature_schema(features_invalid, required_cols)
    assert valid is False
    assert "rssi_std" in missing
    assert "rssi_min" in missing


def test_core_data_raw_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test_session.csv"
        init_raw_dataset_file(csv_path)
        assert csv_path.exists()

        append_raw_record(
            filepath=csv_path,
            anchor_id="ANCHOR_01",
            device_mac="AA:BB:CC:DD:EE:FF",
            rssi=-68,
            distance_m=1.5,
            condition="LOS",
            notes="Test record",
        )

        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2  # header + 1 record
            assert "ANCHOR_01" in lines[1]
            assert "AA:BB:CC:DD:EE:FF" in lines[1]
            assert "-68" in lines[1]
            assert "1.5" in lines[1]
