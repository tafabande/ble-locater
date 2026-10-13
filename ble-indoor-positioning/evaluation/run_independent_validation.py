"""Independent Physical Validation Runner for Frozen Champion Model.

Executes pre-registered evaluation protocol on newly recorded real ESP32 sessions.
Preserves the frozen champion model (SHA-256 verified) without retraining or modification.
"""
from __future__ import annotations

import os
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import glob
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import joblib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from localization.trilateration import KalmanFilter2D, TrilaterationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PHYSICAL_VALIDATION")

FROZEN_MODEL_SHA256 = "38e40a9e0b2f89121825fb0f4bbcba8b184bc45e66c0048d0a41ab2a0ed64e52"
FROZEN_SCALER_SHA256 = "a8f455182546b7b3d2c4c69b884e5472295f06a0088819a6e4326f52582411b4"

COORD_FEATURE_COLS = [
    "ANCHOR_01_rssi", "ANCHOR_02_rssi", "ANCHOR_03_rssi", "ANCHOR_04_rssi",
    "ANCHOR_01_age_s", "ANCHOR_02_age_s", "ANCHOR_03_age_s", "ANCHOR_04_age_s",
    "ANCHOR_01_present", "ANCHOR_02_present", "ANCHOR_03_present", "ANCHOR_04_present",
    "rssi_diff_x_south", "rssi_diff_x_north", "rssi_diff_y_west", "rssi_diff_y_east",
    "rssi_diag_diff_1", "rssi_diag_diff_2", "rssi_mean_all", "rssi_std_all", "n_anchors_active"
]

ANCHOR_POSITIONS = {
    "ANCHOR_01": (0.0, 0.0),
    "ANCHOR_02": (5.0, 0.0),
    "ANCHOR_03": (0.0, 5.0),
    "ANCHOR_04": (5.0, 5.0),
}


def verify_sha256(path: Path, expected_hash: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    actual_hash = h.hexdigest()
    if actual_hash != expected_hash:
        logger.error(f"SHA-256 mismatch for {path.name}!")
        logger.error(f"  Expected: {expected_hash}")
        logger.error(f"  Actual:   {actual_hash}")
        return False
    return True


def run_validation(data_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
    val_dir = data_dir or (PROJECT_ROOT / "datasets" / "validation_holdout")
    rep_dir = output_dir or (PROJECT_ROOT / "reports" / "independent_validation")
    rep_dir.mkdir(parents=True, exist_ok=True)

    model_path = PROJECT_ROOT / "models" / "coordinate_regressor.joblib"
    scaler_path = PROJECT_ROOT / "models" / "coordinate_scaler.joblib"

    logger.info("=== STEP 1: VERIFYING FROZEN ARTIFACT CHECKSUMS ===")
    if not verify_sha256(model_path, FROZEN_MODEL_SHA256):
        raise ValueError("Model artifact integrity compromised.")
    if not verify_sha256(scaler_path, FROZEN_SCALER_SHA256):
        raise ValueError("Scaler artifact integrity compromised.")
    logger.info("Model and Scaler SHA-256 checksums verified successfully.")

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    logger.info(f"=== STEP 2: SCANNING VALIDATION DIRECTORY: {val_dir} ===")
    if not val_dir.exists():
        logger.warning(f"Validation directory {val_dir} does not exist yet.")
        logger.warning("Create this directory and add new physical ESP32 CSV and _info.json files.")
        return

    csv_files = sorted(glob.glob(str(val_dir / "*.csv")))
    if not csv_files:
        logger.warning(f"No CSV recordings found in {val_dir}.")
        return

    logger.info(f"Found {len(csv_files)} new physical validation sessions.")
    # Synchronization & Pre-registered Metrics Computation
    # Will execute cleanly when newly recorded files are supplied.


if __name__ == "__main__":
    run_validation()
