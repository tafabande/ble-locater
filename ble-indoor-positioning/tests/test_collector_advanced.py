"""Comprehensive unit and integration tests for the Data Collector GUI suite.

Tests SessionManager, DataQualityValidator, RecordingEngine, 4-anchor multi-receiver
acquisition, canonical schema compliance, companion JSON metadata, coverage calculations,
and crash recovery.
"""
import csv
import json
import queue
import tempfile
import time
from pathlib import Path
import pytest

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collector.session_manager import (
    SessionManager, SessionConfig, CANONICAL_RAW_HEADERS, TARGET_DISTANCES
)
from collector.validation import DataQualityValidator, QualityVerdict
from collector.recording import RecordingEngine


def test_session_config_validation():
    # Valid config
    cfg = SessionConfig(
        session_name="1m_LOS_01",
        target_mac="52:06:26:03:01:DA",
        distance_m=1.0,
        anchor_id="ALL_ANCHORS",
        condition="Line-of-Sight (LOS)",
        target_samples=100,
    )
    ok, msg = cfg.validate()
    assert ok is True
    assert "valid" in msg.lower()

    # Invalid empty name
    cfg_bad_name = SessionConfig(session_name="", target_mac="AA:BB:CC", distance_m=1.0)
    ok, msg = cfg_bad_name.validate()
    assert ok is False
    assert "name cannot be empty" in msg.lower()

    # Invalid distance
    cfg_bad_dist = SessionConfig(session_name="test", target_mac="AA:BB:CC", distance_m=-1.0)
    ok, msg = cfg_bad_dist.validate()
    assert ok is False
    assert "invalid distance" in msg.lower()

    # Low sample count
    cfg_bad_samples = SessionConfig(session_name="test", target_mac="AA:BB:CC", distance_m=1.0, target_samples=2)
    ok, msg = cfg_bad_samples.validate()
    assert ok is False
    assert "too low" in msg.lower()


def test_session_manager_lifecycle_and_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_dir = Path(tmpdir)
        mgr = SessionManager(raw_dir=raw_dir)

        # 1. Create Session
        ok, msg, session = mgr.create_session(
            name="test_run_01",
            mac="52:06:26:03:01:DA",
            distance_m=1.0,
            anchor_id="ALL_ANCHORS",
            condition="Line-of-Sight (LOS)",
            obstacle="No",
            obstacle_type="None",
            tag_height_m=0.96,
            notes="Lab benchmark",
            target_samples=50,
        )
        assert ok is True
        assert session is not None
        target_path = raw_dir / session.filename
        assert target_path.exists()

        # Check CSV header matches canonical required format
        with open(target_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == CANONICAL_RAW_HEADERS
            # Explicitly verify required cols for feature_engineering/engineer.py
            required_cols = {"timestamp", "anchor", "mac", "rssi", "distance_m"}
            assert required_cols.issubset(set(header))

        # 2. Finalize Session
        ok_fin = mgr.finalize_session(
            session=session,
            sample_count=50,
            duration_sec=12.5,
            stats={"mean_rssi": -62.4, "std_rssi": 1.8},
        )
        assert ok_fin is True
        meta_path = raw_dir / f"{session.session_id}_info.json"
        assert meta_path.exists()

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            assert meta["total_samples"] == 50
            assert meta["distance_m"] == 1.0
            assert meta["dirty_environment_mode"] == "Line-of-Sight (LOS)"
            assert meta["schema_version"] == "2.0"

        # 3. Discover Past Sessions
        past = mgr.get_past_sessions()
        assert len(past) == 1
        assert past[0]["filename"] == session.filename
        assert past[0]["distance"] == "1.0m"
        assert past[0]["samples"] == 50


def test_session_preview_and_coverage():
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_dir = Path(tmpdir)
        mgr = SessionManager(raw_dir=raw_dir)

        # Create two sample datasets with multiple rows
        ok, _, s1 = mgr.create_session("s1", "52:06:26:03:01:DA", distance_m=1.0)
        csv1 = raw_dir / s1.filename
        with open(csv1, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for i in range(20):
                writer.writerow([1000 + i, "ANCHOR_01", "52:06:26:03:01:DA", -60, "MFG", 1.0, "No", "None", 0.96, "stationary"])

        ok2, _, s2 = mgr.create_session("s2", "52:06:26:03:01:DA", distance_m=3.0)
        csv2 = raw_dir / s2.filename
        with open(csv2, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for i in range(15):
                writer.writerow([2000 + i, "ANCHOR_02", "52:06:26:03:01:DA", -75, "MFG", 3.0, "Yes", "Human body", 0.96, "stationary"])

        # Preview
        headers, rows = mgr.read_session_preview(csv1, max_rows=10)
        assert headers == CANONICAL_RAW_HEADERS
        assert len(rows) == 10

        # Coverage Analysis
        cov = mgr.get_dataset_coverage()
        assert cov["total_samples"] == 35
        assert cov["distance_counts"][1.0] == 20
        assert cov["distance_counts"][3.0] == 15
        assert cov["anchor_counts"]["ANCHOR_01"] == 20
        assert cov["anchor_counts"]["ANCHOR_02"] == 15
        assert len(cov["imbalance_warnings"]) > 0  # Missing 0.5m, 2.0m, 5.0m should trigger warnings


def test_crash_recovery_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_dir = Path(tmpdir)
        mgr = SessionManager(raw_dir=raw_dir)

        # Simulate an interrupted session: CSV with rows but no companion info.json
        interrupted_csv = raw_dir / "dataset_2026-09-12_120000.csv"
        with open(interrupted_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CANONICAL_RAW_HEADERS)
            writer.writerow([1000, "ANCHOR_01", "52:06:26:03:01:DA", -65, "MFG", 1.0, "No", "None", 0.96, "stationary"])
            writer.writerow([1100, "ANCHOR_01", "52:06:26:03:01:DA", -66, "MFG", 1.0, "No", "None", 0.96, "stationary"])

        unfinished = mgr.detect_unfinished_sessions()
        assert len(unfinished) == 1
        assert unfinished[0]["filename"] == "dataset_2026-09-12_120000.csv"
        assert unfinished[0]["samples"] == 2


def test_data_quality_validator_multi_anchor():
    val = DataQualityValidator(variance_threshold_db=5.5, timeout_sec=2.0)

    # 1. Baseline nominal feed
    now = time.time()
    for i in range(10):
        val.add_sample(rssi=-62 + (i % 2), timestamp=now + i * 0.2, anchor_id="ANCHOR_01")
        val.add_sample(rssi=-65 + (i % 2), timestamp=now + i * 0.2, anchor_id="ANCHOR_02")

    v = val.evaluate(ground_truth_distance_m=1.0)
    assert v.status == "NOMINAL"
    assert v.is_acceptable is True

    # Check anchor timeout detection
    timeouts = val.check_anchor_timeouts(now=now + 5.0)
    assert "ANCHOR_01" in timeouts
    assert "ANCHOR_02" in timeouts

    # 2. High variance anomaly detection
    val.reset()
    for rssi in [-40, -85, -45, -90, -42, -88, -41, -89]:
        val.add_sample(rssi=rssi, timestamp=time.time(), anchor_id="ANCHOR_01")

    v_var = val.evaluate(ground_truth_distance_m=1.0)
    assert v_var.status == "WARNING"
    assert v_var.quality_flag == "HIGH_VARIANCE"
    assert v_var.is_acceptable is False

    # 3. Abnormal attenuation detection for close distance
    val.reset()
    for _ in range(10):
        val.add_sample(rssi=-95, timestamp=time.time(), anchor_id="ANCHOR_01")

    v_att = val.evaluate(ground_truth_distance_m=0.5)
    assert v_att.status == "WARNING"
    assert v_att.quality_flag == "ATTENUATION_ANOMALY"


def test_recording_engine_4_anchor_simulation():
    q = queue.Queue()
    engine = RecordingEngine(packet_queue=q)

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_dir = Path(tmpdir)
        mgr = SessionManager(raw_dir=raw_dir)
        ok, _, session = mgr.create_session(
            name="sim_test",
            mac="52:06:26:03:01:DA",
            distance_m=2.0,
            anchor_id="ALL_ANCHORS",
            target_samples=15,
        )
        assert ok is True

        # Start simulated acquisition
        engine.start_recording(session, port="Simulated Stream")
        time.sleep(0.8)  # Let worker produce packets

        # Verify packets in queue
        assert not q.empty()
        pkt = q.get_nowait()
        assert "rssi" in pkt
        assert "anchor_id" in pkt
        assert pkt["anchor_id"].startswith("ANCHOR_")

        # Test pause and resume
        engine.pause_recording()
        assert engine.is_paused is True
        time.sleep(0.3)
        engine.resume_recording()
        assert engine.is_paused is False

        # Stop recording
        summary = engine.stop_recording()
        engine.stop_all()

        assert summary["total_samples"] > 0
        assert summary["duration_sec"] > 0
        assert "anchor_counts" in summary

        # Check that file on disk received records
        target_path = session.target_file_path
        assert target_path.exists()
        with open(target_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
            assert header == CANONICAL_RAW_HEADERS
            assert len(rows) == summary["total_samples"]
