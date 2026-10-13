"""Serialize the Multi-Anchor Coordinate Regression Champion.

Trains ExtraTrees (Coord) on the FULL synchronized multi-anchor dataset
(1,961 windows × 21 features → (x, y)) and saves production artifacts.

These artifacts power the real-time inference in server/app.py when ≥3
anchors are active. Falls back to per-anchor distance regression otherwise.
"""
from __future__ import annotations

import os
import sys

# Set OpenBLAS and OpenMP environment variables before importing numpy / scipy / sklearn
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import RobustScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SERIALIZE_COORD_MODEL")

COORD_FEATURE_COLS = [
    "ANCHOR_01_rssi", "ANCHOR_02_rssi", "ANCHOR_03_rssi", "ANCHOR_04_rssi",
    "ANCHOR_01_age_s", "ANCHOR_02_age_s", "ANCHOR_03_age_s", "ANCHOR_04_age_s",
    "ANCHOR_01_present", "ANCHOR_02_present", "ANCHOR_03_present", "ANCHOR_04_present",
    "rssi_diff_x_south", "rssi_diff_x_north", "rssi_diff_y_west", "rssi_diff_y_east",
    "rssi_diag_diff_1", "rssi_diag_diff_2", "rssi_mean_all", "rssi_std_all", "n_anchors_active"
]

TARGET_COLS = ["target_x", "target_y"]


def main():
    dataset_path = PROJECT_ROOT / "datasets" / "multi_anchor_observations.csv"
    model_dir = PROJECT_ROOT / "models"

    if not dataset_path.exists():
        logger.error(f"Synchronized dataset not found: {dataset_path}")
        logger.error("Run training/multi_anchor_comparison.py first to build the dataset.")
        sys.exit(1)

    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded {len(df):,} synchronized windows from {df['session_id'].nunique()} sessions.")

    # Verify all feature columns exist
    missing = [c for c in COORD_FEATURE_COLS if c not in df.columns]
    if missing:
        logger.error(f"Missing feature columns: {missing}")
        sys.exit(1)

    X = df[COORD_FEATURE_COLS].values.astype(float)
    y = df[TARGET_COLS].values.astype(float)

    # Fit scaler on full dataset (production model, not CV evaluation)
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # Train the champion: ExtraTrees with n_jobs=1 to avoid OpenBLAS thread allocation issues on Windows
    model = MultiOutputRegressor(
        ExtraTreesRegressor(
            n_estimators=250,
            max_depth=12,
            random_state=42,
            n_jobs=1,
        )
    )
    logger.info("Training Extra Trees (Coord) on full dataset...")
    model.fit(X_scaled, y)

    # Evaluate in-sample (sanity check — CV metrics are in multi_anchor_comparison.json)
    y_pred = model.predict(X_scaled)
    err_2d = np.linalg.norm(y_pred - y, axis=1)
    logger.info(f"In-sample sanity check: Mean 2D = {np.mean(err_2d):.4f}m, "
                f"Median = {np.median(err_2d):.4f}m (CV: 0.885m / 0.406m)")

    # Save artifacts
    model_path = model_dir / "coordinate_regressor.joblib"
    scaler_path = model_dir / "coordinate_scaler.joblib"
    meta_path = model_dir / "coordinate_model_metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        "model_type": "MultiOutputRegressor(ExtraTreesRegressor)",
        "prediction_target": "direct_xy_coordinates",
        "feature_cols": COORD_FEATURE_COLS,
        "target_cols": TARGET_COLS,
        "n_estimators": 250,
        "max_depth": 12,
        "training_windows": len(df),
        "training_sessions": int(df["session_id"].nunique()),
        "cross_validated_metrics": {
            "mean_2d_error_m": 0.8853,
            "median_2d_error_m": 0.4059,
            "rmse_2d_error_m": 1.3690,
            "acc_sub_50cm_pct": 54.26,
            "acc_sub_1m_pct": 69.96,
            "acc_sub_1_5m_pct": 76.08,
            "validation_strategy": "5-Fold GroupKFold on session_id (Zero Session Leakage)",
            "statistical_significance": "p = 0.0019 vs Trilateration (paired t-test)",
        },
        "anchor_coordinates": {
            "ANCHOR_01": [0.0, 0.0],
            "ANCHOR_02": [5.0, 0.0],
            "ANCHOR_03": [0.0, 5.0],
            "ANCHOR_04": [5.0, 5.0],
        },
        "in_sample_metrics": {
            "mean_2d_m": round(float(np.mean(err_2d)), 4),
            "median_2d_m": round(float(np.median(err_2d)), 4),
        },
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Saved coordinate_regressor.joblib ({model_path.stat().st_size / 1024:.1f} KB)")
    logger.info(f"✅ Saved coordinate_scaler.joblib ({scaler_path.stat().st_size / 1024:.1f} KB)")
    logger.info(f"✅ Saved coordinate_model_metadata.json")
    logger.info(f"\nProduction multi-anchor coordinate model is ready for server/app.py integration.")


if __name__ == "__main__":
    main()
