"""Indoor Positioning — Data Management & Schema Validation Core.

Handles dataset discovery, raw packet formatting, session persistence,
and schema validation.
"""
from __future__ import annotations

import csv
import datetime
import glob
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import DATASETS_DIR, RAW_DATA_DIR


RAW_CSV_HEADERS = [
    "date",
    "time",
    "timestamp",
    "anchor_id",
    "device_mac",
    "rssi",
    "distance_m",
    "condition",
    "tag_height_m",
    "notes",
    "raw_payload",
]


def discover_raw_datasets(raw_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Discover all raw collection CSVs in the raw dataset directory."""
    target_dir = Path(raw_dir) if raw_dir else RAW_DATA_DIR
    if not target_dir.exists():
        return []

    results = []
    for file_path in target_dir.glob("*.csv"):
        try:
            stat = file_path.stat()
            size_kb = round(stat.st_size / 1024, 1)
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # Quick row counting
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                row_count = max(0, sum(1 for _ in f) - 1)

            results.append({
                "filename": file_path.name,
                "path": str(file_path),
                "rows": row_count,
                "size_kb": size_kb,
                "modified": mtime,
            })
        except Exception:
            pass

    results.sort(key=lambda x: x["modified"], reverse=True)
    return results


def init_raw_dataset_file(filepath: Path, headers: Optional[List[str]] = None) -> None:
    """Initialize a new raw dataset CSV with standard headers if it does not exist."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not filepath.exists():
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers or RAW_CSV_HEADERS)


def append_raw_record(
    filepath: Path,
    anchor_id: str,
    device_mac: str,
    rssi: int,
    distance_m: float = 1.0,
    condition: str = "LOS",
    tag_height_m: float = 1.0,
    notes: str = "",
    raw_payload: str = "",
    timestamp_ms: Optional[int] = None,
) -> None:
    """Append a standardized raw observation to a dataset CSV."""
    init_raw_dataset_file(filepath)
    now = datetime.datetime.now()
    d_str = now.strftime("%Y-%m-%d")
    t_str = now.strftime("%H:%M:%S.%f")[:-3]
    ts = timestamp_ms or int(time.time() * 1000)

    row = [
        d_str,
        t_str,
        ts,
        anchor_id,
        device_mac,
        rssi,
        distance_m,
        condition,
        tag_height_m,
        notes,
        raw_payload or f"{ts},{anchor_id},{device_mac},{rssi}",
    ]

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def validate_dataset_for_training(dataset_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that an observations dataset is ready for machine learning training."""
    if not dataset_path.exists():
        return False, f"File not found: {dataset_path}", {}

    try:
        df = pd.read_csv(dataset_path)
        if len(df) < 10:
            return False, f"Dataset too small: only {len(df)} rows. Minimum 10 required.", {"rows": len(df)}

        required_cols = ["distance", "rssi_mean"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, f"Missing critical columns: {missing}", {"columns": list(df.columns)}

        stats = {
            "rows": len(df),
            "columns": len(df.columns),
            "distances": sorted([round(float(d), 2) for d in df["distance"].unique()]) if "distance" in df.columns else [],
            "anchors": list(df["anchor"].unique()) if "anchor" in df.columns else [],
            "has_nan": bool(df.isna().any().any()),
        }
        return True, "Dataset valid and ready for training.", stats
    except Exception as e:
        return False, f"Failed to read dataset: {e}", {}
