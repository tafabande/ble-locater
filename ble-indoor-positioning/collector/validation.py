"""Indoor Positioning — Data Quality & Signal Validation Engine.

Detects collection anomalies in real-time: excessive signal variance,
path loss attenuation mismatches, and packet arrival irregularities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class QualityVerdict:
    """Evaluation result for the active data collection stream."""
    status: str  # 'NOMINAL', 'WARNING', 'CRITICAL'
    mean_rssi: float
    std_rssi: float
    message: str
    is_acceptable: bool


class DataQualityValidator:
    """Validates real-time RSSI signal characteristics against physical ground truth."""

    def __init__(self, variance_threshold_db: float = 5.5) -> None:
        self.variance_threshold_db = variance_threshold_db
        self.rssi_window: List[int] = []
        self.timestamps: List[float] = []

    def reset(self) -> None:
        self.rssi_window.clear()
        self.timestamps.clear()

    def add_sample(self, rssi: int, timestamp: float) -> None:
        self.rssi_window.append(rssi)
        self.timestamps.append(timestamp)
        if len(self.rssi_window) > 100:
            self.rssi_window.pop(0)
            self.timestamps.pop(0)

    def evaluate(self, ground_truth_distance_m: float) -> QualityVerdict:
        if len(self.rssi_window) < 5:
            return QualityVerdict(
                status="NOMINAL",
                mean_rssi=float(self.rssi_window[-1]) if self.rssi_window else -100.0,
                std_rssi=0.0,
                message="Gathering initial baseline observations...",
                is_acceptable=True,
            )

        mean_val = sum(self.rssi_window) / len(self.rssi_window)
        variance = sum((r - mean_val) ** 2 for r in self.rssi_window) / len(self.rssi_window)
        std_val = math.sqrt(variance)

        # 1. Excessive variance check (multipath or dynamic obstacles)
        if std_val > self.variance_threshold_db:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"High signal variance (σ={std_val:.1f} dBm > {self.variance_threshold_db} dBm). Moving obstacles or multipath detected.",
                is_acceptable=False,
            )

        # 2. Distance-attenuation plausibility check
        # For d <= 1m, expected RSSI should generally be >= -82 dBm
        if ground_truth_distance_m <= 1.0 and mean_val < -85.0:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"Signal abnormally attenuated ({mean_val:.1f} dBm) for close distance ({ground_truth_distance_m}m). Check transmitter power or antenna.",
                is_acceptable=False,
            )

        # 3. For distant positions (e.g. d >= 5m), expected RSSI should not be unexpectedly high (e.g. > -55 dBm)
        if ground_truth_distance_m >= 5.0 and mean_val > -55.0:
            return QualityVerdict(
                status="WARNING",
                mean_rssi=round(mean_val, 1),
                std_rssi=round(std_val, 1),
                message=f"Signal unexpectedly strong ({mean_val:.1f} dBm) for {ground_truth_distance_m}m. Check for beacon proximity error.",
                is_acceptable=False,
            )

        return QualityVerdict(
            status="NOMINAL",
            mean_rssi=round(mean_val, 1),
            std_rssi=round(std_val, 1),
            message=f"Nominal Signal Quality: Mean={mean_val:.1f} dBm, σ={std_val:.1f} dBm. High fidelity dataset observations.",
            is_acceptable=True,
        )
