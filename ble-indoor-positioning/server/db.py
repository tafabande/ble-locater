import os
import time
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import event

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
    timestamp: int
    time_str: str = Field(default="")
    patient_id: str = Field(default="")
    from_room: str = Field(default="Unknown")
    to_room: str = Field(default="Unknown")
    severity: str = Field(default="LOW")
    message: str = Field(default="")
    acknowledged: int = Field(default=0)

def create_db_engine(db_path_or_url: str):
    """
    Creates a SQLModel/SQLAlchemy engine supporting SQLite (with WAL & timeout)
    or external databases via DATABASE_URL environment variable.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        db_url = env_url
    elif "://" in db_path_or_url:
        db_url = db_path_or_url
    else:
        abs_path = os.path.abspath(db_path_or_url)
        db_url = f"sqlite:///{abs_path}"

    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["timeout"] = 30.0
        connect_args["check_same_thread"] = False

    engine = create_engine(db_url, connect_args=connect_args, echo=False)

    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
            except Exception:
                pass
            finally:
                cursor.close()

    return engine
