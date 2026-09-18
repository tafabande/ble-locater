"""Indoor Positioning — Data Collection Session Management.

Handles session configuration, metadata validation, target parameters,
canonical raw CSV dataset formatting, companion JSON metadata,
session history indexing, dataset coverage auditing, and crash recovery.
"""
from __future__ import annotations

import csv
import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RAW_DATA_DIR


# Standard canonical headers strictly expected by feature_engineering/engineer.py
CANONICAL_RAW_HEADERS = [
    "timestamp",
    "anchor",
    "mac",
    "rssi",
    "name",
    "distance_m",
    "obstacle",
    "obstacle_type",
    "height_m",
    "motion",
]

TARGET_DISTANCES = [0.5, 1.0, 2.0, 3.0, 5.0]


@dataclass
class SessionConfig:
    """Metadata and parameter specification for a single collection session."""
    session_name: str
    target_mac: str
    distance_m: float
    anchor_id: str = "ALL_ANCHORS"
    condition: str = "Line-of-Sight (LOS)"
    obstacle: str = "No"
    obstacle_type: str = "None"
    motion: str = "stationary"
    tag_height_m: float = 0.96
    notes: str = ""
    target_samples: int = 100
    data_source: str = "Simulated Stream"
    raw_dir: Path = field(default_factory=lambda: RAW_DATA_DIR)
    environment_layout: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    session_id: str = field(default_factory=lambda: f"dataset_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
    is_finalized: bool = False

    def validate(self) -> Tuple[bool, str]:
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
    def filename(self) -> str:
        """Returns the canonical filename for this session."""
        return f"{self.session_id}.csv"

    @property
    def target_file_path(self) -> Path:
        """Full path to the raw dataset CSV."""
        return self.raw_dir / self.filename

    @property
    def metadata_file_path(self) -> Path:
        """Full path to companion JSON metadata."""
        return self.raw_dir / f"{self.session_id}_info.json"

    def save_metadata(self, sample_count: int, duration_sec: float = 0.0, stats: Optional[Dict[str, Any]] = None) -> Path:
        """Save companion JSON metadata for the session including complete environment snapshot."""
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = {
            "session_filename": self.filename,
            "session_name": self.session_name,
            "start_timestamp": self.created_at,
            "end_timestamp": end_time,
            "duration_sec": round(duration_sec, 1),
            "distance_m": float(self.distance_m),
            "height_m": float(self.tag_height_m),
            "motion": self.motion,
            "obstacle": self.obstacle,
            "obstacle_type": self.obstacle_type,
            "dirty_environment_mode": self.condition,
            "target_mac": self.target_mac,
            "anchor_configuration": self.anchor_id,
            "data_source": self.data_source,
            "total_samples": int(sample_count),
            "target_samples": int(self.target_samples),
            "notes": self.notes,
            "schema_version": "2.0",
            "stats": stats or {},
            "environment_layout": self.environment_layout,
        }
        self.metadata_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return self.metadata_file_path


class SessionManager:
    """Manages active, historical, and unfinished collection sessions."""

    def __init__(self, raw_dir: Optional[Path] = None) -> None:
        self.raw_dir = Path(raw_dir) if raw_dir else RAW_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: Optional[SessionConfig] = None

    def create_session(
        self,
        name: str,
        mac: str,
        distance_m: float,
        anchor_id: str = "ALL_ANCHORS",
        condition: str = "Line-of-Sight (LOS)",
        tag_height_m: float = 0.96,
        notes: str = "",
        target_samples: int = 100,
        obstacle: str = "No",
        obstacle_type: str = "None",
        motion: str = "stationary",
        data_source: str = "Simulated Stream",
        environment_layout: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SessionConfig]]:
        """Create and initialize a new data collection session."""
        cfg = SessionConfig(
            session_name=name,
            target_mac=mac,
            distance_m=distance_m,
            anchor_id=anchor_id,
            condition=condition,
            obstacle=obstacle,
            obstacle_type=obstacle_type,
            motion=motion,
            tag_height_m=tag_height_m,
            notes=notes,
            target_samples=target_samples,
            data_source=data_source,
            raw_dir=self.raw_dir,
            environment_layout=environment_layout,
        )
        is_valid, msg = cfg.validate()
        if not is_valid:
            return False, msg, None

        # Guarantee unique file on disk
        target_path = cfg.target_file_path
        if target_path.exists():
            # Disambiguate with subsecond microsecond tag
            cfg.session_id = f"dataset_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S_%f')}"
            target_path = cfg.target_file_path

        # Initialize CSV file with canonical headers
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CANONICAL_RAW_HEADERS)

        self.active_session = cfg
        return True, f"Session initialized: {cfg.filename}", cfg

    def finalize_session(
        self,
        session: SessionConfig,
        sample_count: int,
        duration_sec: float = 0.0,
        stats: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Finalize a collection session and save metadata."""
        try:
            session.is_finalized = True
            session.save_metadata(sample_count=sample_count, duration_sec=duration_sec, stats=stats)
            return True
        except Exception:
            return False

    def get_past_sessions(self) -> List[Dict[str, Any]]:
        """Index all existing raw CSV dataset sessions in the raw directory."""
        if not self.raw_dir.exists():
            return []

        results = []
        for csv_path in sorted(self.raw_dir.glob("dataset_*.csv"), reverse=True):
            try:
                stat = csv_path.stat()
                size_kb = round(stat.st_size / 1024, 1)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                # Companion metadata
                info_path = csv_path.with_name(f"{csv_path.stem}_info.json")
                distance_m = "Unknown"
                condition = "Unknown"
                obstacle_type = "None"
                samples = 0
                notes = ""

                if info_path.exists():
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            distance_m = f"{meta.get('distance_m', 'Unknown')}m"
                            condition = meta.get("dirty_environment_mode", meta.get("condition", "Unknown"))
                            obstacle_type = meta.get("obstacle_type", "None")
                            samples = meta.get("total_samples", 0)
                            notes = meta.get("notes", "")
                    except Exception:
                        pass

                if samples == 0:
                    # Read directly from CSV
                    try:
                        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                            reader = csv.DictReader(f)
                            rows = list(reader)
                            samples = len(rows)
                            if rows and "distance_m" in rows[0]:
                                distance_m = f"{rows[0]['distance_m']}m"
                            if rows and "obstacle_type" in rows[0]:
                                obstacle_type = rows[0].get("obstacle_type", "None")
                    except Exception:
                        pass

                results.append({
                    "filename": csv_path.name,
                    "stem": csv_path.stem,
                    "path": str(csv_path),
                    "info_path": str(info_path) if info_path.exists() else None,
                    "distance": distance_m,
                    "condition": condition,
                    "obstacle_type": obstacle_type,
                    "samples": samples,
                    "size_kb": size_kb,
                    "modified": mtime,
                    "notes": notes,
                })
            except Exception:
                pass

        return results

    def get_session_layout(self, csv_path: Path) -> Optional[Dict[str, Any]]:
        """Extract and reconstruct visual environment layout dict from companion metadata JSON."""
        info_path = csv_path.with_name(f"{csv_path.stem}_info.json")
        if not info_path.exists():
            return None
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("environment_layout")
        except Exception:
            return None

    def read_session_preview(self, filepath: Path, max_rows: int = 50) -> Tuple[List[str], List[List[str]]]:
        """Read header and first N rows of a dataset CSV for fast preview without loading full file."""
        if not filepath.exists():
            return [], []

        headers = []
        rows = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    rows.append(row)
        except Exception:
            pass
        return headers, rows

    def detect_unfinished_sessions(self) -> List[Dict[str, Any]]:
        """Detect interrupted or unfinalized sessions on application startup."""
        unfinished = []
        for csv_path in self.raw_dir.glob("dataset_*.csv"):
            info_path = csv_path.with_name(f"{csv_path.stem}_info.json")
            if not info_path.exists():
                try:
                    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                        row_count = max(0, sum(1 for _ in f) - 1)
                    if row_count > 0:
                        stat = csv_path.stat()
                        unfinished.append({
                            "filename": csv_path.name,
                            "path": str(csv_path),
                            "samples": row_count,
                            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        })
                except Exception:
                    pass
        return unfinished

    def get_dataset_coverage(self) -> Dict[str, Any]:
        """Calculate distribution of accumulated observations across distances, conditions, and anchors."""
        distance_counts = {d: 0 for d in TARGET_DISTANCES}
        distance_counts["Other"] = 0
        anchor_counts = {"ANCHOR_01": 0, "ANCHOR_02": 0, "ANCHOR_03": 0, "ANCHOR_04": 0}
        condition_counts: Dict[str, int] = {}
        total_samples = 0

        for csv_path in self.raw_dir.glob("dataset_*.csv"):
            try:
                with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total_samples += 1
                        # Distance
                        try:
                            dist = float(row.get("distance_m", -1))
                            nearest = min(TARGET_DISTANCES, key=lambda x: abs(x - dist))
                            if abs(nearest - dist) < 0.05:
                                distance_counts[nearest] += 1
                            else:
                                distance_counts["Other"] += 1
                        except (ValueError, TypeError):
                            distance_counts["Other"] += 1

                        # Anchor
                        anc = row.get("anchor") or row.get("anchor_id", "")
                        anc_clean = anc.strip().upper()
                        if anc_clean in anchor_counts:
                            anchor_counts[anc_clean] += 1
                        elif anc_clean:
                            anchor_counts[anc_clean] = anchor_counts.get(anc_clean, 0) + 1

                        # Condition / Obstacle
                        cond = row.get("obstacle_type") or row.get("condition") or "LOS"
                        cond_clean = str(cond).strip()
                        condition_counts[cond_clean] = condition_counts.get(cond_clean, 0) + 1
            except Exception:
                pass

        # Check for coverage imbalance
        imbalance_warnings = []
        valid_preset_counts = [distance_counts[d] for d in TARGET_DISTANCES]
        max_dist_count = max(valid_preset_counts) if valid_preset_counts else 0

        for d in TARGET_DISTANCES:
            cnt = distance_counts[d]
            if cnt == 0:
                imbalance_warnings.append(f"Missing ground truth distance: {d}m has 0 observations.")
            elif max_dist_count > 0 and cnt < (max_dist_count * 0.25):
                imbalance_warnings.append(f"Underrepresented distance: {d}m has only {cnt:,} samples ({round(cnt / max_dist_count * 100)}% of peak).")

        # Anchor balance check
        anc_vals = [anchor_counts.get(f"ANCHOR_{i:02d}", 0) for i in range(1, 5)]
        max_anc = max(anc_vals) if anc_vals else 0
        for i in range(1, 5):
            anc_id = f"ANCHOR_{i:02d}"
            cnt = anchor_counts.get(anc_id, 0)
            if max_anc > 200 and cnt < (max_anc * 0.4):
                imbalance_warnings.append(f"Anchor imbalance: {anc_id} has {cnt:,} samples (substantially lower than peak {max_anc:,}).")

        return {
            "total_samples": total_samples,
            "distance_counts": distance_counts,
            "anchor_counts": anchor_counts,
            "condition_counts": condition_counts,
            "imbalance_warnings": imbalance_warnings,
        }
