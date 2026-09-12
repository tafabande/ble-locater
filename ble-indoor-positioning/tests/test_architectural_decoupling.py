"""Unit and integration tests for architectural decoupling, modular components, and error resilience."""
import os
import sys
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
for p in (str(PROJECT_ROOT), str(WORKSPACE_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# 1. Collector Modular Components
from collector.session_manager import SessionManager, SessionConfig
from collector.validation import DataQualityValidator, QualityVerdict

def test_collector_session_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = SessionManager(raw_dir=Path(tmpdir))
        # Valid session
        ok, msg, cfg = mgr.create_session(
            name="test_run_01",
            mac="11:22:33:44:55:66",
            distance_m=1.0,
            anchor_id="ANCHOR_01",
            condition="LOS",
            tag_height_m=1.0,
            notes="Lab test",
            target_samples=50,
        )
        assert ok is True
        assert cfg is not None
        assert cfg.target_file_path.exists()

        # Invalid session (negative distance)
        bad_ok, bad_msg, _ = mgr.create_session(
            name="bad_run",
            mac="11:22:33:44:55:66",
            distance_m=-2.0,
            anchor_id="ANCHOR_01",
            condition="LOS",
        )
        assert bad_ok is False
        assert "Invalid distance" in bad_msg


def test_collector_data_quality_validator():
    validator = DataQualityValidator(variance_threshold_db=5.5)

    # 1. Stable signal around -60 dBm
    for _ in range(10):
        validator.add_sample(-60, 1.0)
    verdict = validator.evaluate(ground_truth_distance_m=1.0)
    assert verdict.status == "NOMINAL"
    assert verdict.is_acceptable is True

    # 2. High variance test
    validator.reset()
    for val in (-40, -85, -45, -90, -42, -88):
        validator.add_sample(val, 1.0)
    verdict_noisy = validator.evaluate(ground_truth_distance_m=1.0)
    assert verdict_noisy.status == "WARNING"
    assert "High signal variance" in verdict_noisy.message


# 2. Trainer Modular Components
from training.dataset_inspector import DatasetInspector
from training.model_exporter import ModelExporter

def test_trainer_dataset_inspector():
    # Test on real observations.csv
    obs_path = PROJECT_ROOT / "datasets" / "observations.csv"
    if obs_path.exists():
        ok, msg, stats = DatasetInspector.inspect(obs_path)
        assert ok is True
        assert stats["rows"] > 0
        assert "rssi_mean" in stats["column_names"]

    # Test on missing file
    ok_missing, msg_missing, _ = DatasetInspector.inspect(Path("non_existent_dataset.csv"))
    assert ok_missing is False
    assert "File not found" in msg_missing


def test_trainer_model_exporter():
    from sklearn.dummy import DummyRegressor
    from sklearn.preprocessing import StandardScaler

    dummy_model = DummyRegressor(strategy="mean")
    dummy_model.fit([[1.0]], [1.0])
    dummy_scaler = StandardScaler()
    dummy_scaler.fit([[1.0]])

    with tempfile.TemporaryDirectory() as tmpdir:
        ok, msg, meta = ModelExporter.export_champion_model(
            candidate_model=dummy_model,
            candidate_scaler=dummy_scaler,
            metadata={"champion_model": "Dummy", "metrics": {"test_mae": 0.5}},
            version_tag="v_test_01",
            target_dir=Path(tmpdir),
        )
        assert ok is True
        assert (Path(tmpdir) / "distance_estimator.joblib").exists()
        assert (Path(tmpdir) / "scaler.joblib").exists()
        assert (Path(tmpdir) / "model_metadata.json").exists()
        assert meta["version_tag"] == "v_test_01"


# 3. Admin Modular Components
from admin.connection_monitor import ConnectionMonitor
from admin.diagnostics import DiagnosticEngine

def test_admin_connection_monitor():
    mon = ConnectionMonitor(backend_url="http://127.0.0.1:9999")  # Unreachable port
    status = mon.ping_backend(timeout_sec=0.5)
    assert status.is_online is False
    assert "failed" in status.message.lower()

    stats = mon.get_connection_statistics()
    assert stats["total_attempts"] == 1
    assert stats["failed_attempts"] == 1


def test_admin_diagnostic_engine():
    results = DiagnosticEngine.run_self_check(is_backend_online=False)
    assert len(results) >= 4
    components = [r.component for r in results]
    assert "Core API Gateway" in components
    assert "Distance ML Model" in components
