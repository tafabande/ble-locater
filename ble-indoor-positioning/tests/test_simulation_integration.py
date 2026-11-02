"""Integration tests for the Dual-Source BLE Positioning Pipeline.

Validates:
1. Synthetic measurement ingestion and database persistence.
2. Separation of Simulation and Real records in SQLite WAL database.
3. Idempotent retry handling (no duplicate records).
4. History API source-filtering (?source=simulation vs ?source=real).
5. Ground truth preservation and error calculation.
"""
import time
import pytest
from server.app import (
    shared,
    SimulatedTelemetryPayload,
    ingest_simulated_telemetry,
    ingest_simulated_batch,
    get_position_history
)

def test_simulation_telemetry_ingest_and_persistence():
    ts = int(time.time() * 1000)
    tag_id = "SIM-TAG-001"
    payload = SimulatedTelemetryPayload(
        timestamp_ms=ts,
        tag_id=tag_id,
        source="simulation",
        x=2.50,
        y=3.10,
        floor=0,
        true_x=2.45,
        true_y=3.00,
        error_m=0.11,
        uncertainty=0.45,
        gdop=1.25,
        zone="Assembly Floor",
        room="Room-A",
        status="current",
        algorithm="damped_gauss_newton",
        selected_anchors=["ANCHOR_01", "ANCHOR_02", "ANCHOR_03"],
        raw_readings={"ANCHOR_01": -64, "ANCHOR_02": -71, "ANCHOR_03": -68},
        selection_rationale="top3_los_geometric_spread"
    )

    # 1. Post to simulation ingestion endpoint
    resp = ingest_simulated_telemetry(payload)
    assert resp["status"] == "success"
    assert resp["tag_id"] == tag_id

    # 2. Verify record in history
    hist_resp = get_position_history(tag_id=tag_id, source="simulation")
    records = hist_resp["history"]
    assert len(records) >= 1
    latest = records[0]
    assert latest["tag_id"] == tag_id
    assert latest["source"] == "simulation"
    assert pytest.approx(latest["x"], abs=0.01) == 2.50
    assert pytest.approx(latest["y"], abs=0.01) == 3.10
    assert pytest.approx(latest["true_x"], abs=0.01) == 2.45
    assert pytest.approx(latest["true_y"], abs=0.01) == 3.00
    assert pytest.approx(latest["error_m"], abs=0.01) == 0.11
    assert latest["algorithm"] == "damped_gauss_newton"
    assert "ANCHOR_01" in latest["selected_anchors"]
    assert latest["selection_rationale"] == "top3_los_geometric_spread"


def test_simulation_idempotency_prevents_duplicates():
    ts = int(time.time() * 1000)
    tag_id = "SIM-TAG-IDEMPOTENT"
    payload = SimulatedTelemetryPayload(
        timestamp_ms=ts,
        tag_id=tag_id,
        source="simulation",
        x=4.0,
        y=4.0,
        true_x=4.0,
        true_y=4.0,
        error_m=0.0,
        uncertainty=0.2
    )

    # Post initial record
    resp1 = ingest_simulated_telemetry(payload)
    assert resp1["status"] == "success"

    # Post exact retry within tolerance window
    resp2 = ingest_simulated_telemetry(payload)
    assert resp2["status"] == "success"

    # Verify only 1 record exists
    hist = get_position_history(tag_id=tag_id, source="simulation")["history"]
    matching = [r for r in hist if abs(r["timestamp_ms"] - ts) <= 50]
    assert len(matching) == 1, f"Expected 1 record, got {len(matching)} (duplicate not rejected)"


def test_separation_of_simulation_and_real_records():
    ts_now = int(time.time() * 1000)

    # 1. Log a Real record (simulate real hardware observation cycle)
    real_tag = "REAL-ESP32-TAG"
    shared['position_db'].log_position(
        tag_id=real_tag,
        position={"x": 1.20, "y": 2.20, "uncertainty": 0.6, "gdop": 1.4, "zone": "Lab", "room": "Lab-1"},
        timestamp_ms=ts_now,
        source="real",
        algorithm="ml_regressor"
    )

    # 2. Log a Simulation record
    sim_tag = "SIM-TAG-SEPARATE"
    shared['position_db'].log_position(
        tag_id=sim_tag,
        position={"x": 3.80, "y": 4.80, "uncertainty": 0.3, "gdop": 1.0, "zone": "Yard", "room": "Outside"},
        timestamp_ms=ts_now,
        source="simulation",
        true_x=3.75,
        true_y=4.75,
        error_m=0.07,
        algorithm="damped_gauss_newton"
    )

    # 3. Query source=real
    real_hist = get_position_history(tag_id=real_tag, source="real")["history"]
    assert len(real_hist) >= 1
    assert all(r["source"] == "real" for r in real_hist)
    # Real records must NOT possess synthetic ground truth
    assert real_hist[0]["true_x"] is None
    assert real_hist[0]["true_y"] is None

    # 4. Query source=simulation
    sim_hist = get_position_history(tag_id=sim_tag, source="simulation")["history"]
    assert len(sim_hist) >= 1
    assert all(r["source"] == "simulation" for r in sim_hist)
    assert sim_hist[0]["true_x"] == 3.75

    # 5. Query cross-filtering returns empty
    cross_check = get_position_history(tag_id=real_tag, source="simulation")["history"]
    assert len(cross_check) == 0


def test_simulation_batch_ingestion():
    ts_base = int(time.time() * 1000)
    batch = []
    for i in range(5):
        batch.append(SimulatedTelemetryPayload(
            timestamp_ms=ts_base + i * 100,
            tag_id=f"BATCH-TAG-{i}",
            source="simulation",
            x=1.0 + i * 0.5,
            y=2.0 + i * 0.5,
            floor=0,
            true_x=1.05 + i * 0.5,
            true_y=1.95 + i * 0.5,
            error_m=0.07,
            algorithm="damped_gauss_newton",
            selected_anchors=["ANCHOR_01", "ANCHOR_02", "ANCHOR_03"],
            selection_rationale="top3_los_geometric_spread"
        ))

    resp = ingest_simulated_batch(batch)
    assert resp["status"] == "success"
    assert resp["count"] == 5

    # Verify records persisted
    hist = get_position_history(tag_id="BATCH-TAG-0", source="simulation")["history"]
    assert len(hist) >= 1
    assert hist[0]["source"] == "simulation"


def test_consecutive_rapid_measurements_not_dropped():
    """Verify legitimate rapid successive measurements are not discarded by idempotency."""
    ts_base = int(time.time() * 1000)
    tag_id = "RAPID-TAG-01"

    # Measurement 1 at t=0
    payload1 = SimulatedTelemetryPayload(
        timestamp_ms=ts_base,
        tag_id=tag_id,
        source="simulation",
        x=10.0,
        y=12.0
    )
    # Measurement 2 at t+20ms with updated coordinate
    payload2 = SimulatedTelemetryPayload(
        timestamp_ms=ts_base + 20,
        tag_id=tag_id,
        source="simulation",
        x=10.15,
        y=12.08
    )

    ingest_simulated_telemetry(payload1)
    ingest_simulated_telemetry(payload2)

    hist = get_position_history(tag_id=tag_id, source="simulation")["history"]
    rapid_records = [r for r in hist if abs(r["timestamp_ms"] - ts_base) <= 50]
    assert len(rapid_records) == 2, f"Expected 2 rapid measurements, got {len(rapid_records)}"
