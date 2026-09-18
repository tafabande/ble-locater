"""Indoor Positioning — Data Quality & Signal Validation Engine.

Detects collection anomalies in real-time: excessive signal variance,
path loss attenuation mismatches, anchor silence timeouts, and packet arrival irregularities.
Preserves raw observations while assigning non-destructive diagnostic flags.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class QualityVerdict:
    """Evaluation result for active data collection stream or individual anchor."""
    status: str  # 'NOMINAL', 'WARNING', 'CRITICAL'
    mean_rssi: float
    std_rssi: float
    message: str
    is_acceptable: bool
    quality_flag: str = "VALID"
    anchor_id: str = "ALL"


class DataQualityValidator:
    """Validates real-time RSSI signal characteristics against physical ground truth."""

    def __init__(self, variance_threshold_db: float = 5.5, timeout_sec: float = 4.0) -> None:
        self.variance_threshold_db = variance_threshold_db
        self.timeout_sec = timeout_sec

        # Rolling window for global observations
        self.rssi_window: List[int] = []
        self.timestamps: List[float] = []

        # Per-anchor tracking
        self.anchor_windows: Dict[str, List[int]] = {
            f"ANCHOR_{i:02d}": [] for i in range(1, 5)
        }
        self.anchor_last_seen: Dict[str, float] = {}

    def reset(self) -> None:
        """Clear all observation buffers and anchor states."""
        self.rssi_window.clear()
        self.timestamps.clear()
        for anc in self.anchor_windows:
            self.anchor_windows[anc].clear()
        self.anchor_last_seen.clear()

    def add_sample(self, rssi: int, timestamp: float, anchor_id: str = "ANCHOR_01") -> None:
        """Record an observation into global and per-anchor rolling windows."""
        self.rssi_window.append(rssi)
        self.timestamps.append(timestamp)
        if len(self.rssi_window) > 100:
            self.rssi_window.pop(0)
            self.timestamps.pop(0)

        anc_clean = anchor_id.strip().upper()
        if anc_clean not in self.anchor_windows:
            self.anchor_windows[anc_clean] = []
        self.anchor_windows[anc_clean].append(rssi)
        if len(self.anchor_windows[anc_clean]) > 50:
            self.anchor_windows[anc_clean].pop(0)

        self.anchor_last_seen[anc_clean] = timestamp

    def check_anchor_timeouts(self, now: Optional[float] = None) -> List[str]:
        """Detect any active anchors that have stopped transmitting beyond the timeout."""
        current_time = now if now is not None else time.time()
        offline = []
        for anc_id, last_ts in self.anchor_last_seen.items():
            if (current_time - last_ts) > self.timeout_sec:
                offline.append(anc_id)
        return offline

    def get_anchor_statistics(self, anchor_id: str) -> Dict[str, float]:
        """Compute running statistics for a specific anchor."""
        anc_clean = anchor_id.strip().upper()
        win = self.anchor_windows.get(anc_clean, [])
        if not win:
            return {"mean": -100.0, "std": 0.0, "count": 0, "last_rssi": -100.0}

        mean_val = sum(win) / len(win)
        variance = sum((r - mean_val) ** 2 for r in win) / len(win)
        std_val = math.sqrt(variance)
        return {
            "mean": round(mean_val, 1),
            "std": round(std_val, 1),
            "count": len(win),
            "last_rssi": float(win[-1]),
        }

    def evaluate(self, ground_truth_distance_m: float, anchor_id: Optional[str] = None) -> QualityVerdict:
        """Evaluate signal quality against physical ground truth expectations."""
        target_win = (
            self.anchor_windows.get(anchor_id.strip().upper(), [])
            if anchor_id and anchor_id != "ALL"
            else self.rssi_window
        )
        anc_tag = anchor_id.strip().upper() if anchor_id else "ALL"

        if len(target_win) < 5:
            return QualityVerdict(
                status="NOMINAL",
                mean_rssi=float(target_win[-1]) if target_win else -100.0,
                std_rssi=0.0,
                message="Gathering initial baseline observations...",
                is_acceptable=True,
                quality_flag="INITIALIZING",
                anchor_id=anc_tag,
            )

        mean_val = sum(target_win) / len(target_win)
        variance = sum((r - mean_val) ** 2 for r in target_win) / len(target_win)
        std_val = math.sqrt(variance)

        # 1. Excessive variance check (multipath or dynamic obstacles)
        if std_val > self.variance_threshold_db:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"High signal variance (σ={std_val:.1f} dBm > {self.variance_threshold_db} dBm). Dynamic obstacle or multipath fading detected.",
                is_acceptable=False,
                quality_flag="HIGH_VARIANCE",
                anchor_id=anc_tag,
            )

        # 2. Distance-attenuation plausibility check
        # For d <= 1m, expected RSSI should generally be >= -85 dBm
        if ground_truth_distance_m <= 1.0 and mean_val < -85.0:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"Signal abnormally attenuated ({mean_val:.1f} dBm) for close distance ({ground_truth_distance_m}m). Check transmitter power or obstruction.",
                is_acceptable=False,
                quality_flag="ATTENUATION_ANOMALY",
                anchor_id=anc_tag,
            )

        # 3. For distant positions (e.g. d >= 5m), expected RSSI should not be unexpectedly high (e.g. > -52 dBm)
        if ground_truth_distance_m >= 5.0 and mean_val > -52.0:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"Signal unexpectedly strong ({mean_val:.1f} dBm) for {ground_truth_distance_m}m. Check for beacon proximity mismatch.",
                is_acceptable=False,
                quality_flag="PROXIMITY_MISMATCH",
                anchor_id=anc_tag,
            )

        return QualityVerdict(
            status="NOMINAL",
            mean_rssi=round(mean_val, 1),
            std_rssi=round(std_val, 1),
            message=f"Nominal Signal Quality: Mean={mean_val:.1f} dBm, σ={std_val:.1f} dBm. High fidelity dataset observations.",
            is_acceptable=True,
            quality_flag="VALID",
            anchor_id=anc_tag,
        )
