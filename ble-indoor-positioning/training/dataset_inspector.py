"""Indoor Positioning — Dataset Inspection & Schema Validator.

Inspects raw and engineered observation datasets, verifies feature columns,
detects missing/infinite values, and summarizes distance distributions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd


class DatasetInspector:
    """Provides analytical inspection and validation of datasets before model training."""

    EXPECTED_CRITICAL_FEATURES = [
        "rssi_mean", "rssi_median", "rssi_std", "rssi_min", "rssi_max",
        "distance", "anchor"
    ]

    @staticmethod
    def inspect(filepath: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Inspect a CSV dataset and return structured health metrics."""
        if not filepath.exists():
            return False, f"File not found: {filepath}", {}

        try:
            df = pd.read_csv(filepath)
            total_rows = len(df)
            total_cols = len(df.columns)

            if total_rows < 10:
                return False, f"Insufficient rows ({total_rows}). Minimum 10 observations required.", {"rows": total_rows}

            # Check for critical features with alias support
            missing_critical = []
            for col in ["rssi_mean", "rssi_median", "rssi_std", "rssi_min", "rssi_max"]:
                if col not in df.columns:
                    missing_critical.append(col)

            has_anchor = "anchor" in df.columns or "anchor_id" in df.columns
            if not has_anchor:
                missing_critical.append("anchor (or anchor_id)")

            has_distance = "distance" in df.columns or "distance_m" in df.columns
            if not has_distance:
                missing_critical.append("distance (or distance_m)")

            # Null / Inf checks
            null_counts = int(df.isna().sum().sum())

            # Distance distribution
            distances = []
            dist_col = "distance" if "distance" in df.columns else ("distance_m" if "distance_m" in df.columns else None)
            if dist_col:
                distances = sorted([round(float(d), 2) for d in df[dist_col].dropna().unique()])

            # Anchors
            anchors = []
            anchor_col = "anchor" if "anchor" in df.columns else ("anchor_id" if "anchor_id" in df.columns else None)
            if anchor_col:
                anchors = list(df[anchor_col].dropna().unique())

            stats = {
                "rows": total_rows,
                "columns": total_cols,
                "column_names": list(df.columns),
                "null_values": null_counts,
                "distances": distances,
                "anchors": anchors,
                "missing_critical": missing_critical,
                "has_schema_mismatch": len(missing_critical) > 0,
            }

            if missing_critical:
                return False, f"Schema mismatch: Missing critical columns {missing_critical}", stats

            return True, f"Dataset nominal: {total_rows:,} rows, {total_cols} features.", stats

        except Exception as e:
            return False, f"Failed to read CSV: {e}", {}
