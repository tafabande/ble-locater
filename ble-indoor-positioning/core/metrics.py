"""Indoor Positioning — Shared Evaluation Metrics.

Centralized regression and 2D spatial positioning metrics.
Preserves exact mathematical formulations across model training,
tournament benchmarking, and dissertation evaluation.
"""
from __future__ import annotations

import logging
from typing import Dict, Any
import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error
)

logger = logging.getLogger("BLE_METRICS")


def evaluate_error_tolerances(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate percentage of predictions within standard metric tolerance thresholds."""
    try:
        y_t = np.asarray(y_true, dtype=float)
        y_p = np.asarray(y_pred, dtype=float)
        errors = np.abs(y_t - y_p)
        total = max(1, len(errors))
        return {
            "within_10cm": round(float(np.sum(errors <= 0.1) / total * 100), 2),
            "within_25cm": round(float(np.sum(errors <= 0.25) / total * 100), 2),
            "within_50cm": round(float(np.sum(errors <= 0.5) / total * 100), 2),
            "within_75cm": round(float(np.sum(errors <= 0.75) / total * 100), 2),
            "within_100cm": round(float(np.sum(errors <= 1.0) / total * 100), 2),
            "within_150cm": round(float(np.sum(errors <= 1.5) / total * 100), 2)
        }
    except Exception as e:
        logger.warning(f"Error tolerances calculation failed: {e}")
        return {
            "within_10cm": 0.0,
            "within_25cm": 0.0,
            "within_50cm": 0.0,
            "within_75cm": 0.0,
            "within_100cm": 0.0,
            "within_150cm": 0.0
        }


def evaluate_extended_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Calculate extended evaluation metrics: MAPE, max error, 95th percentile, explained variance, and per-distance MAE."""
    try:
        y_t = np.asarray(y_true, dtype=float)
        y_p = np.asarray(y_pred, dtype=float)
        errors = np.abs(y_t - y_p)

        nonzero_mask = np.abs(y_t) > 0.01
        if np.sum(nonzero_mask) > 0:
            mape = float(np.mean(np.abs((y_t[nonzero_mask] - y_p[nonzero_mask]) / y_t[nonzero_mask])) * 100)
        else:
            mape = 0.0

        max_error = float(np.max(errors)) if len(errors) > 0 else 0.0
        p95_error = float(np.percentile(errors, 95)) if len(errors) > 0 else 0.0
        ss_res = np.sum((y_t - y_p) ** 2)
        ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
        explained_var = float(1.0 - ss_res / (ss_tot + 1e-10)) if ss_tot > 0 else 0.0

        unique_dists = sorted(np.unique(np.round(y_t, 1)))
        per_distance_mae = {}
        for dist in unique_dists:
            mask = np.abs(y_t - dist) < 0.05
            if np.sum(mask) > 0:
                per_distance_mae[f"{dist:.1f}m"] = round(float(np.mean(np.abs(y_t[mask] - y_p[mask]))), 4)

        return {
            "mape": round(mape, 2),
            "max_error": round(max_error, 4),
            "p95_error": round(p95_error, 4),
            "explained_variance": round(explained_var, 4),
            "per_distance_mae": per_distance_mae
        }
    except Exception as e:
        logger.warning(f"Extended metrics computation failed: {e}")
        return {
            "mape": 0.0,
            "max_error": 0.0,
            "p95_error": 0.0,
            "explained_variance": 0.0,
            "per_distance_mae": {}
        }


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Compute complete 1D distance regression benchmark metrics."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    r2 = float(r2_score(y_t, y_p))
    med_ae = float(median_absolute_error(y_t, y_p))
    tolerances = evaluate_error_tolerances(y_t, y_p)
    ext_metrics = evaluate_extended_metrics(y_t, y_p)

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "med_ae": round(med_ae, 4),
        "tolerances": tolerances,
        "ext_metrics": ext_metrics
    }


def compute_2d_position_metrics(y_true_coords: np.ndarray, y_pred_coords: np.ndarray) -> Dict[str, float]:
    """Compute spatial 2D Euclidean localization error metrics."""
    y_t = np.asarray(y_true_coords, dtype=float)
    y_p = np.asarray(y_pred_coords, dtype=float)

    err_2d = np.linalg.norm(y_p - y_t, axis=1)
    mae_x = float(mean_absolute_error(y_t[:, 0], y_p[:, 0]))
    mae_y = float(mean_absolute_error(y_t[:, 1], y_p[:, 1]))
    r2_x = float(r2_score(y_t[:, 0], y_p[:, 0]))
    r2_y = float(r2_score(y_t[:, 1], y_p[:, 1]))

    mean_2d = float(np.mean(err_2d))
    median_2d = float(np.median(err_2d))
    rmse_2d = float(np.sqrt(np.mean(err_2d ** 2)))
    p95_2d = float(np.percentile(err_2d, 95))
    sub_50cm = float(np.mean(err_2d <= 0.5) * 100)
    sub_1m = float(np.mean(err_2d <= 1.0) * 100)
    sub_1_5m = float(np.mean(err_2d <= 1.5) * 100)

    return {
        "mean_2d_error_m": round(mean_2d, 4),
        "median_2d_error_m": round(median_2d, 4),
        "rmse_2d_error_m": round(rmse_2d, 4),
        "p95_2d_error_m": round(p95_2d, 4),
        "mae_x_m": round(mae_x, 4),
        "mae_y_m": round(mae_y, 4),
        "r2_x": round(r2_x, 4),
        "r2_y": round(r2_y, 4),
        "acc_sub_50cm_pct": round(sub_50cm, 2),
        "acc_sub_1m_pct": round(sub_1m, 2),
        "acc_sub_1_5m_pct": round(sub_1_5m, 2)
    }
