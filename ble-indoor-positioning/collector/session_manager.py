"""Indoor Positioning — Data Collection Session Management.

Handles session configuration, metadata validation, target parameters,
and session directory indexing.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RAW_DATA_DIR
from core.data import discover_raw_datasets, init_raw_dataset_file


@dataclass
class SessionConfig:
    """Metadata and parameter specification for a single collection session."""
    session_name: str
    target_mac: str
    distance_m: float
    anchor_id: str
    condition: str
    tag_height_m: float = 1.0
    notes: str = ""
    target_samples: int = 100
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def validate(self) -> tuple[bool, str]:
        """Validate that session parameters are well-formed before recording."""
        if not self.session_name.strip():
            return False, "Session name cannot be empty."
        if not self.target_mac.strip():
            return False, "Target beacon MAC cannot be empty."
        if self.distance_m <= 0.0 or self.distance_m > 50.0:
            return False, f"Invalid distance: {self.distance_m}m. Must be between 0.1m and 50m."
        if self.target_samples < 5:
            return False, f"Target sample count ({self.target_samples}) is too low (minimum 5)."
        return True, "Session configuration valid."

    @property
    def target_file_path(self) -> Path:
        clean_name = "".join(c for c in self.session_name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            clean_name = "session"
        return RAW_DATA_DIR / f"{clean_name}.csv"


class SessionManager:
    """Manages active and historical collection sessions."""

    def __init__(self, raw_dir: Optional[Path] = None) -> None:
        self.raw_dir = Path(raw_dir) if raw_dir else RAW_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: Optional[SessionConfig] = None

    def create_session(
        self,
        name: str,
        mac: str,
        distance_m: float,
        anchor_id: str,
        condition: str,
        tag_height_m: float = 1.0,
        notes: str = "",
        target_samples: int = 100,
    ) -> tuple[bool, str, Optional[SessionConfig]]:
        cfg = SessionConfig(
            session_name=name,
            target_mac=mac,
            distance_m=distance_m,
            anchor_id=anchor_id,
            condition=condition,
            tag_height_m=tag_height_m,
            notes=notes,
            target_samples=target_samples,
        )
        is_valid, msg = cfg.validate()
        if not is_valid:
            return False, msg, None

        # Initialize the CSV file on disk
        init_raw_dataset_file(cfg.target_file_path)
        self.active_session = cfg
        return True, "Session created successfully.", cfg

    def get_past_sessions(self) -> List[Dict[str, Any]]:
        """Index existing raw CSV files."""
        return discover_raw_datasets(self.raw_dir)
