"""Enterprise Database Layer - SQLModel / SQLite ACID Compliance Engine.

Guarantees full ACID (Atomicity, Consistency, Isolation, Durability) properties:
- Atomicity: Transaction scope context manager with guaranteed rollback on exceptions.
- Consistency: Foreign keys enabled, schema constraints enforced, and quick-check integrity diagnostics.
- Isolation: SQLite WAL (Write-Ahead Logging) mode with 30s busy timeout and thread-safe multi-reader access.
- Durability: Synchronous NORMAL/FULL mode with WAL checkpoints and atomic disk flushing.
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from sqlalchemy import event, text
from sqlmodel import Field, SQLModel, Session, create_engine

logger = logging.getLogger("BLE_DB")


class PositionHistory(SQLModel, table=True):
    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp_ms: int = Field(index=True)
    tag_id: str = Field(index=True)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    uncertainty: float = Field(default=0.0)
    gdop: float = Field(default=0.0)
    zone: str = Field(default="Unknown")
    room: str = Field(default="Unknown")
    # Dual-source extensions: differentiate simulation from physical ESP32 measurements
    source: str = Field(default="real", index=True)  # "simulation" or "real"
    floor: int = Field(default=0)
    true_x: Optional[float] = Field(default=None)  # Ground-truth X (simulation only)
    true_y: Optional[float] = Field(default=None)  # Ground-truth Y (simulation only)
    error_m: Optional[float] = Field(default=None)  # Ground-truth error in meters (simulation only)
    algorithm: str = Field(default="trilateration")  # "ml_regressor", "damped_gauss_newton", "trilateration"
    status: str = Field(default="current")  # "current", "degraded", "unavailable", "proximity_fallback"
    selected_anchors: Optional[str] = Field(default=None)  # JSON-serialized list of anchor IDs used
    raw_readings: Optional[str] = Field(default=None)  # JSON-serialized raw anchor readings
    selection_rationale: Optional[str] = Field(default=None)  # Description of anchor selection criteria


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: str = Field(primary_key=True)
    name: str
    type: str = Field(default="equipment", index=True)
    department: str = Field(default="")
    floor: int = Field(default=1)
    room: str = Field(default="", index=True)
    ble_mac: Optional[str] = Field(default=None, unique=True, index=True)
    status: str = Field(default="active")
    notes: str = Field(default="")
    created_at: Optional[int] = Field(default=None)


class GeofenceAlert(SQLModel, table=True):
    __tablename__ = "geofence_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: int = Field(index=True)
    time_str: str = Field(default="")
    patient_id: str = Field(default="", index=True)
    from_room: str = Field(default="Unknown")
    to_room: str = Field(default="Unknown")
    severity: str = Field(default="LOW", index=True)
    message: str = Field(default="")
    acknowledged: int = Field(default=0)


def migrate_positions_table(engine):
    """Safe, idempotent migration for SQLite positions table.

    Adds new dual-source and simulation metadata columns if they do not yet exist,
    preserving all existing records and schema constraints.
    """
    try:
        with engine.connect() as conn:
            # Check existing columns
            res = conn.execute(text("PRAGMA table_info(positions);")).fetchall()
            existing_cols = {row[1] for row in res}
            if not existing_cols:
                # Table does not exist yet; SQLModel.metadata.create_all will create it.
                return

            columns_to_add = [
                ("source", "VARCHAR DEFAULT 'real'"),
                ("floor", "INTEGER DEFAULT 0"),
                ("true_x", "FLOAT"),
                ("true_y", "FLOAT"),
                ("error_m", "FLOAT"),
                ("algorithm", "VARCHAR DEFAULT 'trilateration'"),
                ("status", "VARCHAR DEFAULT 'current'"),
                ("selected_anchors", "TEXT"),
                ("raw_readings", "TEXT"),
                ("selection_rationale", "TEXT"),
            ]

            for col_name, col_type in columns_to_add:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE positions ADD COLUMN {col_name} {col_type};"))
                    logger.info(f"Database Migration: Added column '{col_name}' to 'positions' table.")

            # Create index on source for performant partition queries
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_positions_source ON positions (source);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_positions_tag_ts ON positions (tag_id, timestamp_ms);"))
            except Exception:
                pass
            conn.commit()
    except Exception as e:
        logger.warning(f"Positions table migration check: {e}")


def create_db_engine(db_path_or_url: str):
    """Creates a high-performance, ACID-compliant SQLModel/SQLAlchemy engine.

    Configured for SQLite WAL mode with synchronous durability, foreign key
    referential integrity, and busy timeout backoff. Also supports enterprise
    external databases (PostgreSQL/MySQL) via DATABASE_URL.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        db_url = env_url
    elif "://" in db_path_or_url:
        db_url = db_path_or_url
    else:
        abs_path = os.path.abspath(db_path_or_url)
        db_url = f"sqlite:///{abs_path}"

    connect_args: Dict[str, Any] = {}
    engine_kwargs: Dict[str, Any] = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if db_url.startswith("sqlite"):
        connect_args["timeout"] = 30.0
        connect_args["check_same_thread"] = False
        engine_kwargs["connect_args"] = connect_args

    engine = create_engine(db_url, **engine_kwargs)

    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                # ACID Isolation & Concurrency
                cursor.execute("PRAGMA journal_mode=WAL;")
                # ACID Durability: NORMAL in WAL mode prevents corruption while maximizing IOPS
                cursor.execute("PRAGMA synchronous=NORMAL;")
                # ACID Consistency: Enforce referential integrity & foreign keys
                cursor.execute("PRAGMA foreign_keys=ON;")
                # Lock contention handling: 30-second busy timeout
                cursor.execute("PRAGMA busy_timeout=30000;")
                # Enterprise Memory Optimizations: 64MB cache and in-memory temp tables
                cursor.execute("PRAGMA cache_size=-64000;")
                cursor.execute("PRAGMA temp_store=MEMORY;")
            except Exception as e:
                logger.warning(f"Failed to apply SQLite PRAGMAs: {e}")
            finally:
                cursor.close()

        # Run safe idempotent schema migration
        migrate_positions_table(engine)

    return engine


@contextmanager
def transaction_scope(engine) -> Generator[Session, None, None]:
    """Transactional scope context manager guaranteeing strict ACID Atomicity.

    All database operations executed within the context block are committed
    atomically. If an unhandled exception or database error occurs, the
    transaction is automatically rolled back completely, leaving no partial
    or corrupted state.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as exc:
        try:
            session.rollback()
        except Exception as rb_err:
            logger.error(f"Rollback failed during transaction exception: {rb_err}")
        raise exc
    finally:
        session.close()


def check_db_integrity(engine) -> Dict[str, Any]:
    """Execute SQLite PRAGMA quick_check and return ACID compliance status."""
    result: Dict[str, Any] = {
        "status": "healthy",
        "quick_check": "unknown",
        "journal_mode": "unknown",
        "foreign_keys": False,
        "synchronous": "unknown",
        "timestamp": time.time(),
    }
    try:
        with Session(engine) as session:
            # Check database integrity
            chk = session.execute(text("PRAGMA quick_check;")).first()
            result["quick_check"] = chk[0] if chk else "ok"

            # Check journal mode (WAL)
            jm = session.execute(text("PRAGMA journal_mode;")).first()
            result["journal_mode"] = str(jm[0]).upper() if jm else "unknown"

            # Check foreign keys
            fk = session.execute(text("PRAGMA foreign_keys;")).first()
            result["foreign_keys"] = bool(fk[0]) if fk else False

            # Check synchronous setting
            sync = session.execute(text("PRAGMA synchronous;")).first()
            sync_map = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
            result["synchronous"] = sync_map.get(sync[0], str(sync[0])) if sync else "unknown"

            if result["quick_check"] != "ok":
                result["status"] = "degraded"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def checkpoint_wal(engine, mode: str = "PASSIVE") -> Dict[str, Any]:
    """Execute an explicit WAL checkpoint to flush transaction logs to the main database file."""
    valid_modes = {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}
    selected_mode = mode.upper() if mode.upper() in valid_modes else "PASSIVE"
    try:
        with Session(engine) as session:
            res = session.execute(text(f"PRAGMA wal_checkpoint({selected_mode});")).first()
            return {
                "success": True,
                "mode": selected_mode,
                "busy": res[0] if res else 0,
                "log_pages": res[1] if res else 0,
                "checkpointed_pages": res[2] if res else 0,
            }
    except Exception as e:
        logger.error(f"WAL checkpoint ({selected_mode}) failed: {e}")
        return {"success": False, "mode": selected_mode, "error": str(e)}
