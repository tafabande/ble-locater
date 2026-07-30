"""
BLE Distance Estimator — High-Performance Ensemble Trainer
============================================================

Trains a Multi-Model Ensemble (Random Forest + Extra Trees + Gradient Boosting Voting/Stacking)
on 20 engineered RSSI features for maximum indoor localization precision.
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
    VotingRegressor,
    StackingRegressor,
)
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import train_test_split, cross_val_score, RepeatedKFold, GridSearchCV
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)
from sklearn.preprocessing import StandardScaler
import joblib


# ──────────────────────────────────────────────────────────────────────
#  20 EXPANDED FEATURE COLUMNS
# ──────────────────────────────────────────────────────────────────────

FEATURE_COLUMNS = [
    "packet_count",
    "scan_duration_ms",
    "rssi_mean",
    "rssi_median",
    "rssi_min",
    "rssi_max",
    "rssi_std",
    "rssi_variance",
    "rssi_p10",
    "rssi_p25",
    "rssi_p75",
    "rssi_p90",
    "rssi_iqr",
    "rssi_mad",
    "rssi_skewness",
    "rssi_kurtosis",
    "rssi_delta_mean",
    "rssi_delta_std",
    "observed_adv_interval",
    "path_loss_est",
]

TARGET_COLUMN = "distance_m"
TEST_SIZE = 0.2
RANDOM_STATE = 42


# ──────────────────────────────────────────────────────────────────────
#  DATA LOADING & VALIDATION
# ──────────────────────────────────────────────────────────────────────

def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate the engineered dataset."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset: {dataset_path}")
    print(f"  Total Rows: {len(df)}")
    print(f"  Total Columns: {len(df.columns)}")

    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN], inplace=True)

    print(f"\n{'='*65}")
    print(f"  DATASET & FEATURE SUMMARY")
    print(f"{'='*65}")
    print(f"  Clean Samples:    {len(df)}")
    print(f"  Distance Presets: {sorted(df[TARGET_COLUMN].unique())} m")
    print(f"  Samples/Distance:")
    for dist, count in df.groupby(TARGET_COLUMN).size().items():
        print(f"    {dist:4.1f}m: {count} observation windows")
    print(f"  RSSI Range:       [{df['rssi_min'].min()}, {df['rssi_max'].max()}] dBm")
    print(f"  Features Count:   {len(FEATURE_COLUMNS)}")
    print(f"{'='*65}\n")

    return df


# ──────────────────────────────────────────────────────────────────────
#  HIGH-PERFORMANCE ENSEMBLE MODEL TRAINING
# ──────────────────────────────────────────────────────────────────────

def build_ensemble_model(model_type: str = "ensemble") -> object:
    """Instantiate high-capacity base models and ensemble wrapper."""
    rf = RandomForestRegressor(
        n_estimators=500,
        max_depth=20,
        min_samples_split=3,
        min_samples_leaf=1,
        max_features="sqrt",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    et = ExtraTreesRegressor(
        n_estimators=500,
        max_depth=20,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    gb = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        random_state=RANDOM_STATE,
    )

    if model_type == "random_forest":
        return rf
    elif model_type == "extra_trees":
        return et
    elif model_type == "gradient_boosting":
        return gb
    elif model_type == "stacking":
        return StackingRegressor(
            estimators=[("rf", rf), ("et", et), ("gb", gb)],
            final_estimator=RidgeCV(),
            n_jobs=-1,
        )
    else:  # Default: Weighted Voting Ensemble
        return VotingRegressor(
            estimators=[("rf", rf), ("et", et), ("gb", gb)],
            weights=[0.4, 0.4, 0.2],
            n_jobs=-1,
        )


def train_model(
    df: pd.DataFrame,
    model_type: str = "ensemble",
    tune_hyperparams: bool = False,
) -> dict:
    """Train and evaluate the beefy ML ensemble model."""
    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMN].values

    y_bins = pd.qcut(y, q=min(5, len(np.unique(y))), labels=False, duplicates="drop")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_bins
    )

    print(f"Train/Test split: {len(X_train)} / {len(X_test)} samples")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    model = build_ensemble_model(model_type=model_type)

    if tune_hyperparams:
        print("\n[SEARCH] Running GridSearch hyperparameter tuning...")
        param_grid = {
            "weights": [[0.5, 0.3, 0.2], [0.4, 0.4, 0.2], [0.35, 0.35, 0.3]]
        }
        if model_type == "ensemble":
            grid_search = GridSearchCV(model, param_grid, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
            grid_search.fit(X_train_scaled, y_train)
            model = grid_search.best_estimator_
            print(f"  Best Voting Weights: {grid_search.best_params_}")

    print("\n[TRAIN] Fitting High-Capacity Ensemble Model (RF 500 + ExtraTrees 500 + GB 300)...")
    model.fit(X_train_scaled, y_train)

    y_pred_train = model.predict(X_train_scaled)
    y_pred_test  = model.predict(X_test_scaled)

    # 5-Fold Cross Validation (Repeated 2x)
    rkf = RepeatedKFold(n_splits=5, n_repeats=2, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=rkf, scoring="neg_mean_absolute_error", n_jobs=-1)

    metrics = {
        "train_mae":      round(mean_absolute_error(y_train, y_pred_train), 4),
        "test_mae":       round(mean_absolute_error(y_test, y_pred_test), 4),
        "test_rmse":      round(np.sqrt(mean_squared_error(y_test, y_pred_test)), 4),
        "test_r2":        round(r2_score(y_test, y_pred_test), 4),
        "test_median_ae": round(median_absolute_error(y_test, y_pred_test), 4),
        "cv_mae_mean":    round(-cv_scores.mean(), 4),
        "cv_mae_std":     round(cv_scores.std(), 4),
    }

    # Extract feature importances if available
    importances = {}
    if hasattr(model, "feature_importances_"):
        imps = model.feature_importances_
        importances = dict(zip(FEATURE_COLUMNS, imps))
    elif hasattr(model, "estimators_"):
        # Average feature importances across base tree estimators
        base_imps = [e.feature_importances_ for e in model.estimators_ if hasattr(e, "feature_importances_")]
        if base_imps:
            mean_imps = np.mean(base_imps, axis=0)
            importances = dict(zip(FEATURE_COLUMNS, mean_imps))

    importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    print(f"\n{'='*65}")
    print(f"  HIGH-CAPACITY MODEL EVALUATION — {model_type.upper()}")
    print(f"{'='*65}")
    print(f"  Train MAE:       {metrics['train_mae']:.4f} m")
    print(f"  Test  MAE:       {metrics['test_mae']:.4f} m")
    print(f"  Test  RMSE:      {metrics['test_rmse']:.4f} m")
    print(f"  Test  R² Score:  {metrics['test_r2']:.4f}")
    print(f"  Test  Median AE: {metrics['test_median_ae']:.4f} m")
    print(f"  Repeated CV MAE: {metrics['cv_mae_mean']:.4f} ± {metrics['cv_mae_std']:.4f} m")
    print(f"\n  Top 10 Feature Importances:")
    for i, (feat, imp) in enumerate(list(importances.items())[:10]):
        bar = "#" * int(imp * 40)
        print(f"    {feat:24s} {imp:.4f}  {bar}")
    print(f"{'='*65}\n")

    return {
        "model":        model,
        "scaler":       scaler,
        "metrics":      metrics,
        "importances":  importances,
        "y_test":       y_test,
        "y_pred_test":  y_pred_test,
        "y_train":      y_train,
        "y_pred_train": y_pred_train,
        "feature_cols": FEATURE_COLUMNS,
        "model_type":   model_type,
    }


# ──────────────────────────────────────────────────────────────────────
#  DIAGNOSTIC PLOTS
# ──────────────────────────────────────────────────────────────────────

def generate_plots(result: dict, output_dir: str):
    """Generate diagnostic plot grid."""
    os.makedirs(output_dir, exist_ok=True)

    y_test      = result["y_test"]
    y_pred_test = result["y_pred_test"]
    importances = result["importances"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle("BLE High-Capacity Ensemble Model — Diagnostics", fontsize=16, fontweight="bold")

    # 1. Predicted vs Actual
    ax = axes[0, 0]
    ax.scatter(y_test, y_pred_test, alpha=0.5, edgecolors="k", linewidths=0.5, s=40, color="#89b4fa")
    lims = [min(y_test.min(), y_pred_test.min()) - 0.5, max(y_test.max(), y_pred_test.max()) + 0.5]
    ax.plot(lims, lims, "r--", linewidth=2, label="Ideal 1:1 prediction")
    ax.set_xlabel("Actual Distance (m)")
    ax.set_ylabel("Predicted Distance (m)")
    ax.set_title("Predicted vs Actual Distance")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Residuals distribution
    ax = axes[0, 1]
    residuals = y_pred_test - y_test
    ax.hist(residuals, bins=30, edgecolor="black", alpha=0.7, color="#a6e3a1")
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2)
    ax.set_xlabel("Prediction Error (m)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Residuals Distribution (MAE={result['metrics']['test_mae']:.3f}m)")
    ax.grid(True, alpha=0.3)

    # 3. Top 10 Feature importances
    ax = axes[1, 0]
    if importances:
        top_feats = list(importances.keys())[:10]
        top_vals  = list(importances.values())[:10]
        ax.barh(top_feats[::-1], top_vals[::-1], color="#cba6f7", edgecolor="black")
        ax.set_xlabel("Importance Weight")
        ax.set_title("Top 10 Feature Importances")
        ax.grid(True, alpha=0.3, axis="x")

    # 4. Error by distance
    ax = axes[1, 1]
    unique_dists = np.sort(np.unique(y_test))
    mae_per_dist = []
    for d in unique_dists:
        mask = y_test == d
        if mask.sum() > 0:
            mae_per_dist.append(mean_absolute_error(y_test[mask], y_pred_test[mask]))
        else:
            mae_per_dist.append(0)
    ax.bar(unique_dists.astype(str), mae_per_dist, color="#f9e2af", edgecolor="black")
    ax.set_xlabel("Actual Distance (m)")
    ax.set_ylabel("MAE (m)")
    ax.set_title("Mean Absolute Error per Distance")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "model_diagnostics.png")
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[PLOT] Diagnostic plots saved: {plot_path}")


# ──────────────────────────────────────────────────────────────────────
#  SAVE & LOAD ARTIFACTS
# ──────────────────────────────────────────────────────────────────────

def save_model(result: dict, output_dir: str):
    """Save model, scaler, and metadata."""
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, "distance_estimator.joblib")
    joblib.dump(result["model"], model_path)
    print(f"[SAVE] Model saved: {model_path}")

    scaler_path = os.path.join(output_dir, "scaler.joblib")
    joblib.dump(result["scaler"], scaler_path)
    print(f"[SAVE] Scaler saved: {scaler_path}")

    metadata = {
        "model_type":    result["model_type"],
        "feature_cols":  result["feature_cols"],
        "metrics":       result["metrics"],
        "importances":   {k: round(v, 6) for k, v in result["importances"].items()},
        "trained_at":    datetime.datetime.now().isoformat(),
        "train_samples": len(result["y_train"]),
        "test_samples":  len(result["y_test"]),
    }
    meta_path = os.path.join(output_dir, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[META] Metadata saved: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="BLE Ensemble Distance Estimator Trainer")
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--model-type", type=str, choices=["ensemble", "random_forest", "extra_trees", "gradient_boosting", "stacking"], default="ensemble")
    parser.add_argument("--tune", action="store_true")
    args = parser.parse_args()

    if args.output_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output_dir = os.path.join(project_root, "models")

    df = load_dataset(args.dataset)
    result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)
    save_model(result, args.output_dir)

    reports_dir = os.path.join(os.path.dirname(args.output_dir), "reports")
    generate_plots(result, reports_dir)

    print(f"\n[DONE] High-Capacity Ensemble Training Complete!")


if __name__ == "__main__":
    main()
