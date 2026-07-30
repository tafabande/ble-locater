"""
BLE Distance Estimator — Training Pipeline
============================================

Trains a Random Forest Regressor to predict physical distance (meters)
from BLE RSSI observation-window features.

Input:  Engineered dataset CSV (from feature_engineering/engineer.py)
Output: Trained model (.joblib) + evaluation report + diagnostic plots
"""

import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for saving plots
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)
from sklearn.preprocessing import StandardScaler
import joblib


# ──────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

# Features used for training (must match engineer.py output)
FEATURE_COLUMNS = [
    "packet_count",
    "scan_duration_ms",
    "rssi_mean",
    "rssi_min",
    "rssi_max",
    "rssi_std",
    "rssi_variance",
    "rssi_delta_mean",
    "observed_adv_interval",
]

TARGET_COLUMN = "distance_m"

# Default model hyperparameters
RF_DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 15,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}

# Test split ratio
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
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")

    # Validate required columns
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Drop rows with NaN in feature/target columns
    before = len(df)
    df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN], inplace=True)
    dropped = before - len(df)
    if dropped > 0:
        print(f"  Dropped {dropped} rows with NaN values")

    # Dataset summary
    print(f"\n{'='*60}")
    print(f"  DATASET SUMMARY")
    print(f"{'='*60}")
    print(f"  Total samples:    {len(df)}")
    print(f"  Distances:        {sorted(df[TARGET_COLUMN].unique())} m")
    print(f"  Samples/distance:")
    for dist, count in df.groupby(TARGET_COLUMN).size().items():
        print(f"    {dist}m: {count} windows")
    print(f"  RSSI range:       [{df['rssi_min'].min()}, {df['rssi_max'].max()}] dBm")
    print(f"  Mean RSSI range:  [{df['rssi_mean'].min():.1f}, {df['rssi_mean'].max():.1f}] dBm")
    print(f"{'='*60}\n")

    return df


# ──────────────────────────────────────────────────────────────────────
#  MODEL TRAINING
# ──────────────────────────────────────────────────────────────────────

def train_model(
    df: pd.DataFrame,
    model_type: str = "random_forest",
    tune_hyperparams: bool = False,
) -> dict:
    """
    Train and evaluate a distance estimation model.

    Parameters
    ----------
    df : pd.DataFrame
        Engineered dataset with features and target.
    model_type : str
        "random_forest" or "gradient_boosting".
    tune_hyperparams : bool
        If True, run GridSearchCV for hyperparameter tuning.

    Returns
    -------
    dict
        Contains trained model, scaler, metrics, and feature importances.
    """
    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMN].values

    # Train/test split (stratified by distance for balanced evaluation)
    # Use binned distance for stratification
    y_bins = pd.qcut(y, q=min(5, len(np.unique(y))), labels=False, duplicates="drop")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_bins
    )

    print(f"Train/Test split: {len(X_train)} / {len(X_test)} samples")

    # Feature scaling (kept for potential future models like SVR/NN)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # Select model
    if model_type == "gradient_boosting":
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
        )
        # GB doesn't need scaled features, but we use them for consistency
    else:
        model = RandomForestRegressor(**RF_DEFAULT_PARAMS)

    # Optional hyperparameter tuning
    if tune_hyperparams and model_type == "random_forest":
        print("\n[SEARCH] Running hyperparameter search (this may take a minute)...")
        param_grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [10, 15, 20, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
        }
        grid_search = GridSearchCV(
            model, param_grid, cv=5, scoring="neg_mean_absolute_error",
            n_jobs=-1, verbose=0
        )
        grid_search.fit(X_train_scaled, y_train)
        model = grid_search.best_estimator_
        print(f"  Best params: {grid_search.best_params_}")
        print(f"  Best CV MAE: {-grid_search.best_score_:.4f}m")
    else:
        model.fit(X_train_scaled, y_train)

    # Predictions
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test  = model.predict(X_test_scaled)

    # Cross-validation score
    cv_scores = cross_val_score(
        model, X_train_scaled, y_train, cv=5, scoring="neg_mean_absolute_error"
    )

    # Metrics
    metrics = {
        "train_mae":      round(mean_absolute_error(y_train, y_pred_train), 4),
        "test_mae":       round(mean_absolute_error(y_test, y_pred_test), 4),
        "test_rmse":      round(np.sqrt(mean_squared_error(y_test, y_pred_test)), 4),
        "test_r2":        round(r2_score(y_test, y_pred_test), 4),
        "test_median_ae": round(median_absolute_error(y_test, y_pred_test), 4),
        "cv_mae_mean":    round(-cv_scores.mean(), 4),
        "cv_mae_std":     round(cv_scores.std(), 4),
    }

    # Feature importances
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
    importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    # Print results
    print(f"\n{'='*60}")
    print(f"  MODEL EVALUATION — {model_type.upper()}")
    print(f"{'='*60}")
    print(f"  Train MAE:       {metrics['train_mae']:.4f} m")
    # Unicode block char replaced with ASCII hash for Windows compat
    print(f"  Test  MAE:       {metrics['test_mae']:.4f} m")
    print(f"  Test  RMSE:      {metrics['test_rmse']:.4f} m")
    print(f"  Test  R²:        {metrics['test_r2']:.4f}")
    print(f"  Test  Median AE: {metrics['test_median_ae']:.4f} m")
    print(f"  5-Fold CV MAE:   {metrics['cv_mae_mean']:.4f} ± {metrics['cv_mae_std']:.4f} m")
    print(f"\n  Feature Importances:")
    for feat, imp in importances.items():
        bar = "#" * int(imp * 50)
        print(f"    {feat:28s} {imp:.4f}  {bar}")
    print(f"{'='*60}\n")

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
    """Generate and save diagnostic plots for the trained model."""
    os.makedirs(output_dir, exist_ok=True)

    y_test      = result["y_test"]
    y_pred_test = result["y_pred_test"]
    importances = result["importances"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle("BLE Distance Estimator — Model Diagnostics", fontsize=16, fontweight="bold")

    # 1. Predicted vs Actual
    ax = axes[0, 0]
    ax.scatter(y_test, y_pred_test, alpha=0.5, edgecolors="k", linewidths=0.5, s=40)
    lims = [min(y_test.min(), y_pred_test.min()) - 0.5, max(y_test.max(), y_pred_test.max()) + 0.5]
    ax.plot(lims, lims, "r--", linewidth=2, label="Perfect prediction")
    ax.set_xlabel("Actual Distance (m)")
    ax.set_ylabel("Predicted Distance (m)")
    ax.set_title("Predicted vs Actual Distance")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Residuals distribution
    ax = axes[0, 1]
    residuals = y_pred_test - y_test
    ax.hist(residuals, bins=30, edgecolor="black", alpha=0.7, color="#4CAF50")
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2)
    ax.set_xlabel("Prediction Error (m)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Residuals Distribution (MAE={result['metrics']['test_mae']:.3f}m)")
    ax.grid(True, alpha=0.3)

    # 3. Feature importances bar chart
    ax = axes[1, 0]
    feat_names = list(importances.keys())
    feat_vals  = list(importances.values())
    bars = ax.barh(feat_names[::-1], feat_vals[::-1], color="#2196F3", edgecolor="black")
    ax.set_xlabel("Importance")
    ax.set_title("Feature Importances")
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
    ax.bar(unique_dists.astype(str), mae_per_dist, color="#FF9800", edgecolor="black")
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
#  SAVE MODEL + METADATA
# ──────────────────────────────────────────────────────────────────────

def save_model(result: dict, output_dir: str):
    """Save the trained model, scaler, and metadata."""
    os.makedirs(output_dir, exist_ok=True)

    # Save model
    model_path = os.path.join(output_dir, "distance_estimator.joblib")
    joblib.dump(result["model"], model_path)
    print(f"[SAVE] Model saved: {model_path}")

    # Save scaler
    scaler_path = os.path.join(output_dir, "scaler.joblib")
    joblib.dump(result["scaler"], scaler_path)
    print(f"[SAVE] Scaler saved: {scaler_path}")

    # Save metadata
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


# ──────────────────────────────────────────────────────────────────────
#  INFERENCE HELPER (for real-time server)
# ──────────────────────────────────────────────────────────────────────

def load_trained_model(model_dir: str) -> dict:
    """
    Load a trained model and scaler for inference.

    Parameters
    ----------
    model_dir : str
        Directory containing distance_estimator.joblib, scaler.joblib,
        and model_metadata.json.

    Returns
    -------
    dict
        Contains 'model', 'scaler', and 'metadata'.
    """
    model  = joblib.load(os.path.join(model_dir, "distance_estimator.joblib"))
    scaler = joblib.load(os.path.join(model_dir, "scaler.joblib"))

    with open(os.path.join(model_dir, "model_metadata.json")) as f:
        metadata = json.load(f)

    return {"model": model, "scaler": scaler, "metadata": metadata}


def predict_distance(model_bundle: dict, features: dict) -> float:
    """
    Predict distance from a single observation window.

    Parameters
    ----------
    model_bundle : dict
        Output of load_trained_model().
    features : dict
        Feature dict with keys matching FEATURE_COLUMNS.

    Returns
    -------
    float
        Predicted distance in meters.
    """
    feature_cols = model_bundle["metadata"]["feature_cols"]
    X = np.array([[features[col] for col in feature_cols]])
    X_scaled = model_bundle["scaler"].transform(X)
    return float(model_bundle["model"].predict(X_scaled)[0])


# ──────────────────────────────────────────────────────────────────────
#  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BLE Distance Estimator — Train ML model from observation windows"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to the engineered observations CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save model artifacts (default: models/)"
    )
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["random_forest", "gradient_boosting"],
        default="random_forest",
        help="Model type to train"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run hyperparameter tuning (slower but may improve accuracy)"
    )
    args = parser.parse_args()

    # Default output directory
    if args.output_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output_dir = os.path.join(project_root, "models")

    # Load and validate
    df = load_dataset(args.dataset)

    # Check minimum data requirements
    n_distances = df[TARGET_COLUMN].nunique()
    if n_distances < 2:
        print(f"\n[WARNING] Only {n_distances} unique distance(s) in dataset.")
        print("   The model needs data at MULTIPLE distances to learn RSSI→distance mapping.")
        print("   Collect data at 2+ distances (e.g., 0.5m, 1.0m, 2.0m) and re-run.")
        print("   Training will proceed but the model will be trivial.\n")

    # Train
    result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)

    # Save
    save_model(result, args.output_dir)

    # Plots
    reports_dir = os.path.join(os.path.dirname(args.output_dir), "reports")
    generate_plots(result, reports_dir)

    print(f"\n[DONE] Training complete!")
    print(f"   Model: {os.path.join(args.output_dir, 'distance_estimator.joblib')}")
    print(f"   Plots: {os.path.join(reports_dir, 'model_diagnostics.png')}")


if __name__ == "__main__":
    main()
