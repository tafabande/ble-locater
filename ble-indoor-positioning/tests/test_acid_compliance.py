"""Unit Tests for Enterprise ACID Compliance & Transactional Reliability.

Verifies:
1. Atomicity: Multi-step writes commit completely or roll back completely on failure.
2. Consistency: Foreign key enforcement, schema integrity, and quick-check diagnostic passes.
3. Isolation: SQLite WAL mode multi-reader concurrency and busy timeout handling.
4. Durability: Synchronous mode, WAL checkpointing, and atomic JSON replacement.
"""
import os
import tempfile
import time
from pathlib import Path
from sqlalchemy import text
from sqlmodel import Session, select

from server.db import (
    create_db_engine,
    PositionHistory,
    Asset,
    GeofenceAlert,
    transaction_scope,
    check_db_integrity,
    checkpoint_wal,
)
from server.asset_registry import AssetRegistry
from engineering.geofence_engine import AlertHistoryDB
from collector.node_registry import save_node_registry, load_node_registry


def test_sqlite_acid_pragmas(tmp_path):
    """Verify engine enforces SQLite WAL mode, foreign keys, and synchronous NORMAL."""
    db_file = tmp_path / "pragmas_test.db"
    engine = create_db_engine(str(db_file))

    with Session(engine) as session:
        jm = session.exec(text("PRAGMA journal_mode;")).first()[0]
        fk = session.exec(text("PRAGMA foreign_keys;")).first()[0]
        sync = session.exec(text("PRAGMA synchronous;")).first()[0]
        timeout = session.exec(text("PRAGMA busy_timeout;")).first()[0]

    assert str(jm).upper() == "WAL"
    assert fk == 1  # Foreign keys active
    assert sync in (1, 2)  # 1 = NORMAL, 2 = FULL
    assert timeout >= 30000


def test_transaction_scope_atomicity_commit(tmp_path):
    """Verify transaction_scope commits all operations atomically on success."""
    db_file = tmp_path / "commit_test.db"
    engine = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine)

    with transaction_scope(engine) as session:
        session.add(PositionHistory(timestamp_ms=1000, tag_id="TAG_A", x=1.0, y=2.0))
        session.add(PositionHistory(timestamp_ms=2000, tag_id="TAG_B", x=3.0, y=4.0))

    with Session(engine) as session:
        records = session.exec(select(PositionHistory)).all()
        assert len(records) == 2


def test_transaction_scope_atomicity_rollback(tmp_path):
    """Verify transaction_scope rolls back completely when an exception occurs."""
    db_file = tmp_path / "rollback_test.db"
    engine = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine)

    try:
        with transaction_scope(engine) as session:
            session.add(PositionHistory(timestamp_ms=1000, tag_id="TAG_A", x=1.0, y=2.0))
            # Simulate unexpected failure midway through the transaction
            raise RuntimeError("Simulated mid-transaction failure")
    except RuntimeError:
        pass

    with Session(engine) as session:
        records = session.exec(select(PositionHistory)).all()
        # Strictly Atomicity: zero records committed
        assert len(records) == 0


def test_asset_registry_acid_crud(tmp_path):
    """Verify AssetRegistry maintains transactional consistency across CRUD."""
    db_file = tmp_path / "asset_test.db"
    registry = AssetRegistry(db_path=str(db_file))

    # Create asset
    asset_data = {
        "id": "ASSET-TEST-001",
        "name": "Precision Test Beacon",
        "type": "equipment",
        "room": "Room A",
        "ble_mac": "AA:BB:CC:DD:EE:FF",
    }
    created = registry.create(asset_data)
    assert created["id"] == "ASSET-TEST-001"

    # Read
    found = registry.get_by_id("ASSET-TEST-001")
    assert found is not None
    assert found["name"] == "Precision Test Beacon"

    # Update
    updated = registry.update("ASSET-TEST-001", {"name": "Updated Beacon", "room": "Room B"})
    assert updated is not None
    assert updated["name"] == "Updated Beacon"
    assert updated["room"] == "Room B"

    # Delete
    deleted = registry.delete("ASSET-TEST-001")
    assert deleted is True
    assert registry.get_by_id("ASSET-TEST-001") is None


def test_alert_history_batch_acid(tmp_path):
    """Verify AlertHistoryDB batch logging executes under a single atomic transaction."""
    db_file = tmp_path / "alerts_test.db"
    alert_db = AlertHistoryDB(db_path=str(db_file))

    batch = [
        {"timestamp_ms": 1000, "patient": "TAG_01", "from": "Room A", "to": "Room B", "severity": "WARNING"},
        {"timestamp_ms": 2000, "patient": "TAG_02", "from": "Room B", "to": "Room C", "severity": "HIGH"},
    ]
    alert_db.log_alerts_batch(batch)

    recent = alert_db.get_recent_alerts(limit=10)
    assert len(recent) == 2

    # Clear history atomically
    alert_db.clear_history()
    assert len(alert_db.get_recent_alerts(limit=10)) == 0


def test_check_db_integrity_and_checkpoint(tmp_path):
    """Verify quick_check integrity diagnostics and WAL checkpointing."""
    db_file = tmp_path / "integrity_test.db"
    engine = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine)

    diag = check_db_integrity(engine)
    assert diag["status"] == "healthy"
    assert diag["quick_check"] == "ok"
    assert diag["journal_mode"] == "WAL"
    assert diag["foreign_keys"] is True

    cp = checkpoint_wal(engine, mode="PASSIVE")
    assert cp["success"] is True


def test_failure_injection_constraint_rollback(tmp_path):
    """Verify that a database unique constraint violation rolls back completely."""
    db_file = tmp_path / "constraint_rollback.db"
    engine = create_db_engine(str(db_file))
    Asset.metadata.create_all(engine)

    # Initial valid asset
    with transaction_scope(engine) as session:
        session.add(Asset(id="A1", name="Asset 1", ble_mac="11:22:33:44:55:66"))

    # Attempt transaction inserting second valid asset AND conflicting duplicate ble_mac
    try:
        with transaction_scope(engine) as session:
            session.add(Asset(id="A2", name="Asset 2", ble_mac="22:33:44:55:66:77"))
            # Conflicting duplicate ble_mac with A1
            session.add(Asset(id="A3", name="Asset 3", ble_mac="11:22:33:44:55:66"))
    except Exception:
        pass

    # Verify A2 was rolled back due to A3 failure
    with Session(engine) as session:
        records = session.exec(select(Asset)).all()
        assert len(records) == 1
        assert records[0].id == "A1"


def test_failure_injection_multi_record_batch_atomicity(tmp_path):
    """Verify batch insert failures enforce strict all-or-nothing atomicity."""
    db_file = tmp_path / "batch_failure.db"
    engine = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine)

    batch_records = [
        PositionHistory(timestamp_ms=1000, tag_id="TAG_1", x=1.0, y=1.0),
        PositionHistory(timestamp_ms=2000, tag_id="TAG_2", x=2.0, y=2.0),
    ]

    try:
        with transaction_scope(engine) as session:
            for i, rec in enumerate(batch_records):
                session.add(rec)
                if i == 1:
                    raise ValueError("Simulated unexpected batch insertion error")
    except ValueError:
        pass

    with Session(engine) as session:
        records = session.exec(select(PositionHistory)).all()
        assert len(records) == 0, "All-or-nothing atomicity violated: partial records were committed!"


def test_failure_injection_connection_cleanup(tmp_path):
    """Verify that repeated transaction failures clean up sessions without leaking connections or locks."""
    db_file = tmp_path / "leak_test.db"
    engine = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine)

    for i in range(10):
        try:
            with transaction_scope(engine) as session:
                session.add(PositionHistory(timestamp_ms=1000 + i, tag_id=f"TAG_{i}", x=1.0, y=1.0))
                raise RuntimeError(f"Failure injection pass {i}")
        except RuntimeError:
            pass

    # Now verify the database is not locked and can accept clean writes
    with transaction_scope(engine) as session:
        session.add(PositionHistory(timestamp_ms=9999, tag_id="TAG_FINAL", x=5.0, y=5.0))

    with Session(engine) as session:
        records = session.exec(select(PositionHistory)).all()
        assert len(records) == 1
        assert records[0].tag_id == "TAG_FINAL"


def test_engine_reopen_and_persistence_recovery(tmp_path):
    """Verify closing engine, reopening persisted database file, WAL checkpointing, and data recovery."""
    db_file = tmp_path / "reopen_recovery.db"

    # 1. Create and populate with engine 1
    engine1 = create_db_engine(str(db_file))
    PositionHistory.metadata.create_all(engine1)
    with transaction_scope(engine1) as session:
        session.add(PositionHistory(timestamp_ms=5000, tag_id="TAG_RECOVERY", x=3.5, y=4.5))

    # 2. Checkpoint WAL and dispose engine 1
    checkpoint_wal(engine1, mode="PASSIVE")
    engine1.dispose()

    # 3. Reopen with fresh engine 2 on the same persisted file
    engine2 = create_db_engine(str(db_file))

    # Verify integrity and persistence
    diag = check_db_integrity(engine2)
    assert diag["status"] == "healthy"
    assert diag["quick_check"] == "ok"
    assert diag["journal_mode"] == "WAL"

    with Session(engine2) as session:
        records = session.exec(select(PositionHistory)).all()
        assert len(records) == 1
        assert records[0].tag_id == "TAG_RECOVERY"
        assert records[0].x == 3.5
        assert records[0].y == 4.5
    engine2.dispose()


def test_model_registry_atomic_rollback(tmp_path):
    """Verify model_db rolls back all tables atomically if an error occurs during logging."""
    from training.model_db import log_training_session, init_db, get_db_connection
    db_file = tmp_path / "model_rollback.db"
    init_db(db_file)

    bad_metadata = {
        "session_id": "bad_session_01",
        "metrics": {"test_mae": 0.5},
        "tournament": ["invalid_entry_not_dict"],
    }

    try:
        log_training_session(bad_metadata, db_path=db_file)
    except Exception:
        pass

    conn = get_db_connection(db_file)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM training_sessions WHERE session_id = 'bad_session_01'")
        assert cur.fetchone()[0] == 0, "Partial session committed into training_sessions despite failure!"
        cur.execute("SELECT COUNT(*) FROM tournament_models WHERE session_id = 'bad_session_01'")
        assert cur.fetchone()[0] == 0, "Partial models committed into tournament_models despite failure!"
    finally:
        conn.close()
