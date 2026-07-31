"""
BLE Indoor Positioning — Ultra-Verbose Super Learner Tournament & Trainer
==========================================================================

Trains a Multi-Model Super Learner Tournament benchmarking 6 distinct algorithms
(Random Forest, Extra Trees, Gradient Boosting, HistGradient Boosting, Support Vector Regression,
and Stacking Super Learner) across 30 engineered features. Automatically selects and saves the champion model.
"""

import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    StackingRegressor,
)
from sklearn.svm import SVR
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import train_test_split, cross_val_score, RepeatedKFold
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
import joblib


# ──────────────────────────────────────────────────────────────────────
#  30 ADVANCED FEATURE COLUMNS
# ──────────────────────────────────────────────────────────────────────

FEATURE_COLUMNS = [
    "packet_count", "scan_duration_ms", "rssi_mean", "rssi_median", "rssi_min", "rssi_max",
    "rssi_std", "rssi_variance", "rssi_range", "rssi_p05", "rssi_p10", "rssi_p25",
    "rssi_p75", "rssi_p90", "rssi_p95", "rssi_iqr", "rssi_p90_10_range", "rssi_mad",
    "rssi_snr", "rssi_skewness", "rssi_kurtosis", "rssi_delta_mean", "rssi_delta_std",
    "rssi_delta_max", "observed_adv_interval", "adv_interval_std", "path_loss_free_space",
    "path_loss_indoor", "rssi_mean_to_std_ratio", "rssi_median_mean_diff"
]

TARGET_COLUMN = "distance_m"
TEST_SIZE = 0.2
RANDOM_STATE = 42


# ──────────────────────────────────────────────────────────────────────
#  DATA LOADING & AUDIT
# ──────────────────────────────────────────────────────────────────────

def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate engineered dataset."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    df = pd.read_csv(dataset_path)

    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN], inplace=True)

    print(f"\n{'='*75}")
    print(f"  [DATASET TELEMETRY AUDIT & SPECTRUM]")
    print(f"{'='*75}")
    print(f"  Total Clean Windows : {len(df)}")
    print(f"  Features Extracted  : {len(FEATURE_COLUMNS)}")
    print(f"  Distance Presets    : {sorted(df[TARGET_COLUMN].unique())} m")
    print(f"\n  Distance Breakdown:")
    for dist, count in df.groupby(TARGET_COLUMN).size().items():
        pct = (count / len(df)) * 100
        bar = "#" * int(pct / 2)
        print(f"    {dist:4.1f}m : {count:4d} windows ({pct:5.1f}%)  {bar}")
    print(f"{'='*75}\n")

    return df


# ──────────────────────────────────────────────────────────────────────
#  SUPER LEARNER TOURNAMENT
# ──────────────────────────────────────────────────────────────────────

def instantiate_candidates() -> dict:
    """Instantiate candidate models for tournament comparison."""
    rf = RandomForestRegressor(n_estimators=500, max_depth=20, min_samples_split=2, random_state=RANDOM_STATE, n_jobs=-1)
    et = ExtraTreesRegressor(n_estimators=500, max_depth=20, min_samples_split=2, random_state=RANDOM_STATE, n_jobs=-1)
    gb = GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=5, subsample=0.8, random_state=RANDOM_STATE)
    hgb = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=6, random_state=RANDOM_STATE)
    svr = SVR(C=10.0, epsilon=0.05, kernel="rbf")

    stacking = StackingRegressor(
        estimators=[("rf", rf), ("et", et), ("gb", gb), ("hgb", hgb), ("svr", svr)],
        final_estimator=RidgeCV(),
        n_jobs=-1
    )

    return {
        "Stacking Super Learner": stacking,
        "Random Forest (500 Trees)": rf,
        "Extra Trees (500 Trees)": et,
        "Gradient Boosting": gb,
        "Hist Gradient Boosting": hgb,
        "Support Vector Regressor (RBF)": svr,
    }


def evaluate_error_tolerances(y_true, y_pred) -> dict:
    """Compute percentage of predictions within strict distance error thresholds."""
    errors = np.abs(y_true - y_pred)
    total = len(errors)
    return {
        "within_10cm": round((np.sum(errors <= 0.10) / total) * 100, 2),
        "within_25cm": round((np.sum(errors <= 0.25) / total) * 100, 2),
        "within_50cm": round((np.sum(errors <= 0.50) / total) * 100, 2),
        "within_100cm": round((np.sum(errors <= 1.00) / total) * 100, 2),
    }


def train_model(df: pd.DataFrame, model_type: str = "auto", tune_hyperparams: bool = False) -> dict:
    """Run Super Learner Tournament across candidates and select champion."""
    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMN].values

    y_bins = pd.qcut(y, q=min(5, len(np.unique(y))), labels=False, duplicates="drop")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_bins
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    candidates = instantiate_candidates()

    print(f"{'='*75}")
    print(f"  [TOURNAMENT] MULTI-MODEL SUPER LEARNER ({len(candidates)} CANDIDATES)")
    print(f"{'='*75}")

    tournament_results = []
    trained_models = {}

    for name, model in candidates.items():
        print(f"\n[TOURNAMENT] Training Candidate: {name}...")
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)
        med  = median_absolute_error(y_test, y_pred)

        tols = evaluate_error_tolerances(y_test, y_pred)

        print(f"  -> Test MAE: {mae:.4f}m | RMSE: {rmse:.4f}m | R2: {r2:.4f} | <=25cm Acc: {tols['within_25cm']}%")

        trained_models[name] = model
        tournament_results.append({
            "name": name,
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "med_ae": med,
            "tolerances": tols,
            "y_pred": y_pred
        })

    # Sort candidates by Test MAE (ascending)
    tournament_results.sort(key=lambda x: x["mae"])
    champion = tournament_results[0]
    champion_name = champion["name"]
    champion_model = trained_models[champion_name]

    print(f"\n{'='*75}")
    print(f"  [CHAMPION] WINNER: {champion_name.upper()}")
    print(f"{'='*75}")
    print(f"  Champion Test MAE   : {champion['mae']:.4f} m")
    print(f"  Champion Test RMSE  : {champion['rmse']:.4f} m")
    print(f"  Champion Test R²    : {champion['r2']:.4f}")
    print(f"  Error <= 10cm Acc    : {champion['tolerances']['within_10cm']}%")
    print(f"  Error <= 25cm Acc    : {champion['tolerances']['within_25cm']}%")
    print(f"  Error <= 50cm Acc    : {champion['tolerances']['within_50cm']}%")

    # Permutation Feature Importance Analysis for Champion
    print(f"\n[SENSITIVITY] Computing Permutation Feature Importances for Champion...")
    perm_res = permutation_importance(champion_model, X_test_scaled, y_test, n_repeats=10, random_state=RANDOM_STATE, n_jobs=-1)
    perm_importances = dict(zip(FEATURE_COLUMNS, perm_res.importances_mean))
    perm_importances = dict(sorted(perm_importances.items(), key=lambda x: x[1], reverse=True))

    print(f"\n  Top 10 Feature Sensitivities:")
    for feat, imp in list(perm_importances.items())[:10]:
        bar = "#" * max(0, int(imp * 50))
        print(f"    {feat:24s} {imp:.4f}  {bar}")
    print(f"{'='*75}\n")

    metrics = {
        "train_mae":      round(mean_absolute_error(y_train, champion_model.predict(X_train_scaled)), 4),
        "test_mae":       round(champion["mae"], 4),
        "test_rmse":      round(champion["rmse"], 4),
        "test_r2":        round(champion["r2"], 4),
        "test_median_ae": round(champion["med_ae"], 4),
        "tolerances":     champion["tolerances"],
        "champion_name":  champion_name,
    }

    return {
        "model":         champion_model,
        "scaler":        scaler,
        "metrics":       metrics,
        "importances":   perm_importances,
        "y_test":        y_test,
        "y_pred_test":   champion["y_pred"],
        "y_train":       y_train,
        "feature_cols":  FEATURE_COLUMNS,
        "model_type":    champion_name,
        "tournament":    [{k: v for k, v in res.items() if k != "y_pred"} for res in tournament_results]
    }


# ──────────────────────────────────────────────────────────────────────
#  DIAGNOSTIC PLOTS & REPORTING
# ──────────────────────────────────────────────────────────────────────

def generate_plots(result: dict, output_dir: str):
    """Generate comprehensive 4-panel diagnostic plot grid."""
    os.makedirs(output_dir, exist_ok=True)

    y_test      = result["y_test"]
    y_pred_test = result["y_pred_test"]
    importances = result["importances"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(f"BLE Champion Model: {result['model_type']} — Diagnostics", fontsize=16, fontweight="bold")

    # 1. Predicted vs Actual
    ax = axes[0, 0]
    ax.scatter(y_test, y_pred_test, alpha=0.6, edgecolors="k", linewidths=0.5, s=45, color="#89b4fa")
    lims = [min(y_test.min(), y_pred_test.min()) - 0.5, max(y_test.max(), y_pred_test.max()) + 0.5]
    ax.plot(lims, lims, "r--", linewidth=2, label="Ideal 1:1 prediction")
    ax.set_xlabel("Actual Distance (m)")
    ax.set_ylabel("Predicted Distance (m)")
    ax.set_title("Predicted vs Actual Distance")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Residual Error Distribution
    ax = axes[0, 1]
    residuals = y_pred_test - y_test
    ax.hist(residuals, bins=30, edgecolor="black", alpha=0.75, color="#a6e3a1")
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2)
    ax.set_xlabel("Prediction Error (m)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Residual Error (MAE={result['metrics']['test_mae']:.3f}m)")
    ax.grid(True, alpha=0.3)

    # 3. Top 10 Permutation Feature Importance
    ax = axes[1, 0]
    if importances:
        top_feats = list(importances.keys())[:10]
        top_vals  = [max(0, v) for v in list(importances.values())[:10]]
        ax.barh(top_feats[::-1], top_vals[::-1], color="#cba6f7", edgecolor="black")
        ax.set_xlabel("Permutation Sensitivity Score")
        ax.set_title("Top 10 Feature Importances")
        ax.grid(True, alpha=0.3, axis="x")

    # 4. Error Tolerance Spectrum Bar Chart
    ax = axes[1, 1]
    tols = result["metrics"]["tolerances"]
    labels = ["<=10cm", "<=25cm", "<=50cm", "<=100cm"]
    vals   = [tols["within_10cm"], tols["within_25cm"], tols["within_50cm"], tols["within_100cm"]]
    bars = ax.bar(labels, vals, color="#f9e2af", edgecolor="black")
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Prediction Error Tolerance Spectrum")
    ax.grid(True, alpha=0.3, axis="y")
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{yval:.1f}%", ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "model_diagnostics.png")
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Diagnostic plots saved: {plot_path}")


def save_model(result: dict, output_dir: str):
    """Save model, scaler, and rich metadata."""
    os.makedirs(output_dir, exist_ok=True)

    joblib.dump(result["model"], os.path.join(output_dir, "distance_estimator.joblib"))
    joblib.dump(result["scaler"], os.path.join(output_dir, "scaler.joblib"))

    metadata = {
        "champion_model": result["model_type"],
        "feature_cols":   result["feature_cols"],
        "metrics":        result["metrics"],
        "importances":    {k: round(float(v), 6) for k, v in result["importances"].items()},
        "tournament":     result["tournament"],
        "trained_at":     datetime.datetime.now().isoformat(),
        "train_samples":  len(result["y_train"]),
        "test_samples":   len(result["y_test"]),
    }
    with open(os.path.join(output_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[SAVE] Champion model & scaler saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="BLE Super Learner Tournament")
    parser.add_argument("--dataset", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--model-type", type=str, default="auto")
    parser.add_argument("--tune", action="store_true")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.dataset is None:
        args.dataset = os.path.join(project_root, "datasets", "observations.csv")

    if args.output_dir is None:
        args.output_dir = os.path.join(project_root, "models")

    df = load_dataset(args.dataset)
    result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)
    save_model(result, args.output_dir)

    reports_dir = os.path.join(os.path.dirname(args.output_dir), "reports")
    generate_plots(result, reports_dir)

    print(f"\n[DONE] Ultra-Verbose Super Learner Tournament Complete!")


if __name__ == "__main__":
    main()
