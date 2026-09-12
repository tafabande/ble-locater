"""Indoor Positioning — Administrator Diagnostic & Health Engine.

Executes infrastructure self-checks, model validation, database audits,
and maintains diagnostic event logging.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import MODELS_DIR, DATASETS_DIR, RAW_DATA_DIR, BACKEND_URL
from core.inference import load_distance_model, load_zone_model


@dataclass
class DiagnosticCheckResult:
    """Individual system health check item."""
    component: str
    status: str  # 'PASS', 'WARN', 'FAIL'
    details: str


class DiagnosticEngine:
    """Performs comprehensive system-wide diagnostics."""

    @staticmethod
    def run_self_check(is_backend_online: bool, backend_latency_ms: float = 0.0) -> List[DiagnosticCheckResult]:
        results = []

        # 1. Core API Gateway
        if is_backend_online:
            results.append(DiagnosticCheckResult(
                component="Core API Gateway",
                status="PASS",
                details=f"Connected at {BACKEND_URL} ({backend_latency_ms:.0f} ms latency)",
            ))
        else:
            results.append(DiagnosticCheckResult(
                component="Core API Gateway",
                status="FAIL",
                details=f"Cannot reach {BACKEND_URL}. Start backend service via Launcher.",
            ))

        # 2. ML Distance Estimator
        model, scaler, meta = load_distance_model(MODELS_DIR)
        if model is not None and scaler is not None:
            champ = meta.get("champion_model", "Loaded ML Pipeline") if meta else "Standard Model"
            mae = meta.get("metrics", {}).get("test_mae", 0.0) if meta else 0.0
            results.append(DiagnosticCheckResult(
                component="Distance ML Model",
                status="PASS",
                details=f"{champ} ready (Test MAE: {mae:.2f}m)",
            ))
        else:
            results.append(DiagnosticCheckResult(
                component="Distance ML Model",
                status="WARN",
                details="No champion model artifact found. Path-loss heuristic fallback active.",
            ))

        # 3. Zone Classifier
        z_model, z_scaler = load_zone_model(MODELS_DIR)
        if z_model is not None:
            results.append(DiagnosticCheckResult(
                component="Zone Classifier",
                status="PASS",
                details="Champion zone classifier loaded cleanly.",
            ))
        else:
            results.append(DiagnosticCheckResult(
                component="Zone Classifier",
                status="WARN",
                details="Zone classifier model not found. Spatial geometric bounding active.",
            ))

        # 4. Engineered Observations Dataset
        obs_path = DATASETS_DIR / "observations.csv"
        if obs_path.exists():
            try:
                with open(obs_path, "r", encoding="utf-8", errors="ignore") as f:
                    rows = sum(1 for _ in f) - 1
                results.append(DiagnosticCheckResult(
                    component="Observations Dataset",
                    status="PASS",
                    details=f"{rows:,} observations available for training.",
                ))
            except Exception as e:
                results.append(DiagnosticCheckResult(
                    component="Observations Dataset",
                    status="WARN",
                    details=f"Cannot read dataset: {e}",
                ))
        else:
            results.append(DiagnosticCheckResult(
                component="Observations Dataset",
                status="WARN",
                details="observations.csv not found. Collect data with Sensor Collector.",
            ))

        # 5. Position Database
        db_path = MODELS_DIR / "position_history.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                conn.close()
                results.append(DiagnosticCheckResult(
                    component="Position SQLite DB",
                    status="PASS",
                    details=f"Database nominal. Tables: {', '.join(tables) or 'ready'}",
                ))
            except Exception as e:
                results.append(DiagnosticCheckResult(
                    component="Position SQLite DB",
                    status="FAIL",
                    details=f"Database corrupted: {e}",
                ))
        else:
            results.append(DiagnosticCheckResult(
                component="Position SQLite DB",
                status="PASS",
                details="Database will initialize automatically on first tracking packet.",
            ))

        return results
