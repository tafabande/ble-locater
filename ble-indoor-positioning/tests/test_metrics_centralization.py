import numpy as np
import pytest

from core.metrics import (
    evaluate_error_tolerances,
    evaluate_extended_metrics,
    compute_regression_metrics,
    compute_2d_position_metrics
)
from training.train import (
    evaluate_error_tolerances as train_eval_tolerances,
    evaluate_extended_metrics as train_eval_extended
)


def test_error_tolerances_exact_thresholds():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    # Errors: 0.05 (<=10cm), 0.20 (<=25cm), 0.40 (<=50cm), 0.70 (<=75cm)
    y_pred = np.array([1.05, 2.20, 3.40, 4.70])

    tols = evaluate_error_tolerances(y_true, y_pred)
    assert tols["within_10cm"] == 25.0
    assert tols["within_25cm"] == 50.0
    assert tols["within_50cm"] == 75.0
    assert tols["within_75cm"] == 100.0
    assert tols["within_100cm"] == 100.0
    assert tols["within_150cm"] == 100.0


def test_extended_metrics_computation():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.1, 2.0, 2.8, 4.2])

    ext = evaluate_extended_metrics(y_true, y_pred)
    assert "mape" in ext
    assert "max_error" in ext
    assert "p95_error" in ext
    assert "explained_variance" in ext
    assert "per_distance_mae" in ext
    assert round(ext["max_error"], 2) == 0.20


def test_compute_regression_metrics_bundle():
    y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    res = compute_regression_metrics(y_true, y_pred)
    assert res["mae"] == 0.0
    assert res["rmse"] == 0.0
    assert res["r2"] == 1.0
    assert res["med_ae"] == 0.0
    assert res["tolerances"]["within_10cm"] == 100.0


def test_compute_2d_position_metrics():
    true_xy = np.array([[1.0, 2.0], [3.0, 4.0]])
    pred_xy = np.array([[1.3, 2.4], [3.0, 4.0]])  # First error = sqrt(0.3^2 + 0.4^2) = 0.5, second = 0.0

    res = compute_2d_position_metrics(true_xy, pred_xy)
    assert round(res["mean_2d_error_m"], 2) == 0.25
    assert round(res["median_2d_error_m"], 2) == 0.25
    assert res["acc_sub_50cm_pct"] == 100.0
    assert round(res["mae_x_m"], 3) == 0.150
    assert round(res["mae_y_m"], 3) == 0.200


def test_backward_compatibility_reexport_in_train():
    y_true = np.array([1.0, 2.0])
    y_pred = np.array([1.1, 1.9])

    core_tols = evaluate_error_tolerances(y_true, y_pred)
    train_tols = train_eval_tolerances(y_true, y_pred)
    assert core_tols == train_tols

    core_ext = evaluate_extended_metrics(y_true, y_pred)
    train_ext = train_eval_extended(y_true, y_pred)
    assert core_ext == train_ext
