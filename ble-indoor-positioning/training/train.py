"""
BLE Indoor Positioning — Ultra-Robust Super Learner Tournament & Trainer
==========================================================================

Multi-stage training pipeline with:
  - 12+ regression candidates (RF, ET, GB, HGB, SVR, XGBoost, CatBoost,
    LightGBM, KNN, MLP, AdaBoost, BayesianRidge, ElasticNet)
  - K-Fold Cross-Validation for robust model evaluation
  - RSSI outlier detection & removal
  - Automatic feature importance pruning
  - Zone classification tournament with 8+ classifiers
  - Stacking & Voting ensembles
  - 38-feature support (backward-compatible with 30-feature datasets)

Automatically selects and saves the champion model with crash-proof safeguards.
"""

import os
import sys
import json
import logging
import argparse
import datetime
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    AdaBoostRegressor,
    BaggingRegressor,
    StackingRegressor,
    VotingRegressor,
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier,
    VotingClassifier,
    GradientBoostingClassifier,
)
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.linear_model import (
    RidgeCV,
    BayesianRidge,
    ElasticNet,
)
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    StratifiedKFold,
    KFold,
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.feature_selection import SelectFromModel
import joblib

# ──────────────────────────────────────────────────────────────────────
#  OPTIONAL IMPORTS (graceful degradation — never crashes the pipeline)
# ──────────────────────────────────────────────────────────────────────

try:
    from xgboost import XGBRegressor, XGBClassifier
    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False
    print("[INFO] XGBoost not available — skipping XGBoost candidates. (pip install xgboost)")

try:
    from catboost import CatBoostRegressor, CatBoostClassifier
    HAS_CATBOOST = True
except Exception:
    HAS_CATBOOST = False
    print("[INFO] CatBoost not available — skipping CatBoost candidates. (pip install catboost)")

try:
    from lightgbm import LGBMRegressor, LGBMClassifier
    HAS_LIGHTGBM = True
except Exception:
    HAS_LIGHTGBM = False
    print("[INFO] LightGBM not available — skipping LightGBM candidates. (pip install lightgbm)")

logger = logging.getLogger("TRAINING_TOURNAMENT")

# ──────────────────────────────────────────────────────────────────────
#  50 ADVANCED FEATURE COLUMNS (backward-compatible with 30/39)
# ──────────────────────────────────────────────────────────────────────

# Original 30 features
BASE_FEATURE_COLUMNS = [
    "packet_count", "scan_duration_ms", "rssi_mean", "rssi_median", "rssi_min", "rssi_max",
    "rssi_std", "rssi_variance", "rssi_range", "rssi_p05", "rssi_p10", "rssi_p25",
    "rssi_p75", "rssi_p90", "rssi_p95", "rssi_iqr", "rssi_p90_10_range", "rssi_mad",
    "rssi_snr", "rssi_skewness", "rssi_kurtosis", "rssi_delta_mean", "rssi_delta_std",
    "rssi_delta_max", "observed_adv_interval", "adv_interval_std", "path_loss_free_space",
    "path_loss_indoor", "rssi_mean_to_std_ratio", "rssi_median_mean_diff"
]

# Intra-window temporal/behavioral features (8)
TEMPORAL_FEATURE_COLUMNS = [
    "rssi_slope", "rssi_trend_strength", "rssi_ema_diff",
    "rssi_first_half_mean", "rssi_second_half_mean", "rssi_half_diff",
    "rssi_autocorrelation", "rssi_energy"
]

# V2: Cross-window temporal features (15 new)
CROSS_WINDOW_FEATURE_COLUMNS = [
    "rssi_mean_delta", "rssi_mean_slope_3w", "rssi_mean_slope_5w",
    "rssi_rolling_mean_3w", "rssi_rolling_std_3w",
    "rssi_rolling_mean_5w", "rssi_rolling_std_5w",
    "rssi_ema_cross_window", "rssi_velocity", "rssi_acceleration",
    "signal_stability_index", "rssi_rolling_mean_10w", "rssi_rolling_std_10w",
    "rssi_motion_direction", "rssi_snr_rolling_5w"
]

# Physical metadata features (height elevation)
PHYSICAL_METADATA_COLUMNS = ["height_m"]

# Full set = 50 (30 base + 8 temporal + 11 cross-window + 1 height)
ALL_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + TEMPORAL_FEATURE_COLUMNS + CROSS_WINDOW_FEATURE_COLUMNS + PHYSICAL_METADATA_COLUMNS

TARGET_COLUMN = "distance_m"
TEST_SIZE = 0.2
RANDOM_STATE = 42
CV_FOLDS = 5  # K-Fold cross-validation folds

# Distance zone boundaries for classification mode
# Boundaries follow the actual data distribution (0.5, 1.0, 2.0, 3.0, 5.0m)
# using midpoints between consecutive collection distances as zone edges.
ZONE_BOUNDARIES = [0, 0.75, 1.5, 2.5, 4.0, float("inf")]
ZONE_LABELS = ["Very Close (<=0.75m)", "Close (0.75-1.5m)", "Mid (1.5-2.5m)", "Far (2.5-4m)", "Very Far (4m+)"]


# ──────────────────────────────────────────────────────────────────────
#  UTILITIES
# ──────────────────────────────────────────────────────────────────────

def detect_available_features(df: pd.DataFrame) -> list:
    """Auto-detect which feature columns exist in the dataset for backward compatibility."""
    available = [col for col in ALL_FEATURE_COLUMNS if col in df.columns]
    n_base = sum(1 for c in BASE_FEATURE_COLUMNS if c in available)
    n_temporal = sum(1 for c in TEMPORAL_FEATURE_COLUMNS if c in available)
    n_cross_window = sum(1 for c in CROSS_WINDOW_FEATURE_COLUMNS if c in available)
    print(f"\n[FEATURE DETECTION] Found {len(available)} features: {n_base} base + {n_temporal} temporal + {n_cross_window} cross-window")
    if n_temporal == 0:
        print("  [INFO] No temporal features detected — using legacy 30-feature mode.")
        print("  [TIP]  Re-run feature engineering to generate the 8 temporal features.")
    if n_cross_window == 0:
        print("  [INFO] No cross-window features detected — V1 mode (no motion awareness).")
        print("  [TIP]  Re-run feature engineering to generate the 11 V2 cross-window features.")
    elif n_cross_window < len(CROSS_WINDOW_FEATURE_COLUMNS):
        missing = [c for c in CROSS_WINDOW_FEATURE_COLUMNS if c not in available]
        print(f"  [WARN] Partial cross-window features. Missing: {missing}")
    else:
        print("  [OK] Full V2 feature mode active (50 features including cross-window temporal).")
    return available


def distance_to_zone(distances: np.ndarray) -> np.ndarray:
    """Map continuous distances to zone labels."""
    zones = np.empty(len(distances), dtype=object)
    for i, d in enumerate(distances):
        for j in range(len(ZONE_BOUNDARIES) - 1):
            if ZONE_BOUNDARIES[j] <= d < ZONE_BOUNDARIES[j + 1]:
                zones[i] = ZONE_LABELS[j]
                break
        else:
            zones[i] = ZONE_LABELS[-1]
    return zones


def detect_and_remove_outliers(X: np.ndarray, y: np.ndarray, contamination: float = 0.05) -> tuple:
    """
    Remove RSSI outlier windows using IQR on the target variable.
    Returns cleaned X, y and count of removed samples.
    """
    q1 = np.percentile(y, 25)
    q3 = np.percentile(y, 75)
    iqr = q3 - q1
    lower = q1 - 2.0 * iqr
    upper = q3 + 2.0 * iqr

    mask = (y >= lower) & (y <= upper)
    n_removed = np.sum(~mask)

    if n_removed > 0:
        print(f"  [OUTLIER] Removed {n_removed} outlier windows ({n_removed/len(y)*100:.1f}%) "
              f"outside [{lower:.2f}m, {upper:.2f}m]")
    else:
        print(f"  [OUTLIER] No outliers detected (IQR bounds: [{lower:.2f}m, {upper:.2f}m])")

    return X[mask], y[mask], int(n_removed)


def feature_importance_pruning(model, X_train, y_train, feature_cols, threshold=0.001):
    """
    Use a quick Random Forest to identify near-zero-importance features.
    Returns a mask of features to keep.
    """
    try:
        quick_rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1)
        quick_rf.fit(X_train, y_train)
        importances = quick_rf.feature_importances_

        keep_mask = importances >= threshold
        n_kept = np.sum(keep_mask)
        n_pruned = len(keep_mask) - n_kept

        if n_pruned > 0:
            pruned_names = [f for f, k in zip(feature_cols, keep_mask) if not k]
            print(f"  [PRUNE] Pruned {n_pruned} near-zero-importance features: {pruned_names[:8]}...")
        else:
            print(f"  [PRUNE] All {n_kept} features contribute — no pruning needed.")

        return keep_mask, importances
    except Exception as e:
        logger.warning(f"Feature pruning failed: {e}")
        return np.ones(len(feature_cols), dtype=bool), np.ones(len(feature_cols))


# ──────────────────────────────────────────────────────────────────────
#  DATA LOADING & AUDIT
# ──────────────────────────────────────────────────────────────────────

def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate engineered dataset."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    try:
        df = pd.read_csv(dataset_path)
    except Exception as e:
        raise ValueError(f"Failed to read dataset CSV: {e}")

    # Check minimum required columns (base features)
    required = set(BASE_FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    # Handle height_m column with 0.0 fallback for legacy datasets
    if "height_m" not in df.columns:
        df["height_m"] = 0.0
    else:
        df["height_m"] = df["height_m"].fillna(0.0)

    # Use all available feature columns for NaN dropping
    available_features = [c for c in ALL_FEATURE_COLUMNS if c in df.columns]
    df.dropna(subset=available_features + [TARGET_COLUMN], inplace=True)

    if df.empty:
        raise ValueError(f"Dataset at {dataset_path} contains 0 valid clean rows after dropping NaNs.")

    print(f"\n{'='*75}")
    print(f"  [DATASET TELEMETRY AUDIT & SPECTRUM]")
    print(f"{'='*75}")
    print(f"  Total Clean Windows : {len(df)}")
    print(f"  Features Available  : {len(available_features)}")
    print(f"  Distance Presets    : {sorted(df[TARGET_COLUMN].unique())} m")
    print(f"\n  Distance Breakdown:")
    for dist, count in df.groupby(TARGET_COLUMN).size().items():
        pct = (count / len(df)) * 100
        bar = "#" * int(pct / 2)
        print(f"    {dist:4.1f}m : {count:4d} windows ({pct:5.1f}%)  {bar}")

    # Zone distribution preview
    zones = distance_to_zone(df[TARGET_COLUMN].values)
    print(f"\n  Zone Distribution:")
    for label in ZONE_LABELS:
        count = np.sum(zones == label)
        pct = (count / len(df)) * 100
        bar = "#" * int(pct / 2)
        print(f"    {label:24s} : {count:4d} windows ({pct:5.1f}%)  {bar}")

    # Height / Elevation breakdown preview
    if "height_m" in df.columns:
        print(f"\n  Height / Elevation Breakdown:")
        for h_val, count in df.groupby("height_m").size().items():
            pct = (count / len(df)) * 100
            bar = "#" * int(pct / 2)
            print(f"    {h_val:4.1f}m : {count:4d} windows ({pct:5.1f}%)  {bar}")

    # V2: Motion Label breakdown
    if "motion" in df.columns:
        print(f"\n  Motion Label Breakdown:")
        for motion_val, count in df.groupby("motion").size().items():
            pct = (count / len(df)) * 100
            bar = "#" * int(pct / 2)
            print(f"    {str(motion_val):16s} : {count:4d} windows ({pct:5.1f}%)  {bar}")

    # Environmental & Dirty Data breakdown preview
    if "obstacle_type" in df.columns:
        print(f"\n  Environmental / Dirty Data Breakdown:")
        for obs_type, count in df.groupby("obstacle_type").size().items():
            pct = (count / len(df)) * 100
            bar = "#" * int(pct / 2)
            print(f"    {str(obs_type):24s} : {count:4d} windows ({pct:5.1f}%)  {bar}")

    print(f"{'='*75}\n")

    return df


# ──────────────────────────────────────────────────────────────────────
#  REGRESSION TOURNAMENT (12+ CANDIDATES + K-FOLD)
# ──────────────────────────────────────────────────────────────────────

def instantiate_candidates() -> dict:
    """Instantiate 12+ regression candidates for tournament comparison."""

    # === TREE-BASED ENSEMBLES ===
    rf = RandomForestRegressor(
        n_estimators=400, max_depth=20, min_samples_split=3,
        min_samples_leaf=2, max_features="sqrt",
        random_state=RANDOM_STATE, n_jobs=-1
    )
    et = ExtraTreesRegressor(
        n_estimators=400, max_depth=20, min_samples_split=3,
        min_samples_leaf=2, max_features="sqrt",
        random_state=RANDOM_STATE, n_jobs=-1
    )
    gb = GradientBoostingRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=5,
        subsample=0.8, min_samples_leaf=5,
        random_state=RANDOM_STATE
    )
    hgb = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_depth=6,
        min_samples_leaf=10, l2_regularization=0.1,
        random_state=RANDOM_STATE
    )

    # === BOOSTING VARIANTS ===
    ada = AdaBoostRegressor(
        estimator=DecisionTreeRegressor(max_depth=5),
        n_estimators=200, learning_rate=0.05,
        random_state=RANDOM_STATE
    )

    # === DISTANCE-BASED ===
    knn = KNeighborsRegressor(
        n_neighbors=7, weights="distance", metric="minkowski", p=2, n_jobs=-1
    )

    # === NEURAL NETWORK ===
    mlp = MLPRegressor(
        hidden_layer_sizes=(128, 64, 32), activation="relu",
        solver="adam", learning_rate="adaptive", learning_rate_init=0.001,
        max_iter=500, early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=20, random_state=RANDOM_STATE
    )

    # === LINEAR / REGULARIZED ===
    svr = SVR(C=10.0, epsilon=0.05, kernel="rbf")
    bayesian = BayesianRidge(alpha_1=1e-6, alpha_2=1e-6, lambda_1=1e-6, lambda_2=1e-6)
    elastic = ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=1000, random_state=RANDOM_STATE)

    # === BAGGING ===
    bagging = BaggingRegressor(
        estimator=DecisionTreeRegressor(max_depth=10),
        n_estimators=200, max_samples=0.8, max_features=0.8,
        random_state=RANDOM_STATE, n_jobs=-1
    )

    candidates = {
        "Random Forest (400 Trees)": rf,
        "Extra Trees (400 Trees)": et,
        "Gradient Boosting (300)": gb,
        "Hist Gradient Boosting": hgb,
        "AdaBoost Regressor": ada,
        "KNN Regressor (k=7)": knn,
        "MLP Neural Network": mlp,
        "SVR (RBF Kernel)": svr,
        "Bayesian Ridge": bayesian,
        "ElasticNet": elastic,
        "Bagging Ensemble": bagging,
    }

    # === XGBOOST ===
    if HAS_XGBOOST:
        xgb = XGBRegressor(
            n_estimators=400, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=1.0, min_child_weight=3,
            gamma=0.1, random_state=RANDOM_STATE, n_jobs=-1, verbosity=0
        )
        xgb_tuned = XGBRegressor(
            n_estimators=600, learning_rate=0.03, max_depth=8,
            subsample=0.7, colsample_bytree=0.7,
            reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
            gamma=0.2, random_state=RANDOM_STATE, n_jobs=-1, verbosity=0
        )
        candidates["XGBoost Regressor"] = xgb
        candidates["XGBoost (Deep Tuned)"] = xgb_tuned

    # === CATBOOST ===
    if HAS_CATBOOST:
        cat = CatBoostRegressor(
            iterations=400, learning_rate=0.05, depth=6,
            l2_leaf_reg=3.0, random_seed=RANDOM_STATE, verbose=0
        )
        cat_deep = CatBoostRegressor(
            iterations=600, learning_rate=0.03, depth=8,
            l2_leaf_reg=5.0, bagging_temperature=0.5,
            random_seed=RANDOM_STATE, verbose=0
        )
        candidates["CatBoost Regressor"] = cat
        candidates["CatBoost (Deep Tuned)"] = cat_deep

    # === LIGHTGBM ===
    if HAS_LIGHTGBM:
        lgbm = LGBMRegressor(
            n_estimators=400, learning_rate=0.05, max_depth=6,
            num_leaves=31, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=1.0, min_child_samples=10,
            random_state=RANDOM_STATE, n_jobs=-1, verbose=-1
        )
        lgbm_tuned = LGBMRegressor(
            n_estimators=600, learning_rate=0.03, max_depth=8,
            num_leaves=63, subsample=0.7, colsample_bytree=0.7,
            reg_alpha=0.5, reg_lambda=2.0, min_child_samples=5,
            random_state=RANDOM_STATE, n_jobs=-1, verbose=-1
        )
        candidates["LightGBM Regressor"] = lgbm
        candidates["LightGBM (Deep Tuned)"] = lgbm_tuned

    # === STACKING SUPER LEARNER ===
    stacking_estimators = [
        ("rf", RandomForestRegressor(n_estimators=200, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)),
        ("et", ExtraTreesRegressor(n_estimators=200, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)),
        ("hgb", HistGradientBoostingRegressor(max_iter=200, max_depth=5, random_state=RANDOM_STATE)),
        ("knn", KNeighborsRegressor(n_neighbors=7, weights="distance", n_jobs=-1)),
    ]
    if HAS_XGBOOST:
        stacking_estimators.append(("xgb", XGBRegressor(
            n_estimators=200, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1, verbosity=0
        )))
    if HAS_LIGHTGBM:
        stacking_estimators.append(("lgbm", LGBMRegressor(
            n_estimators=200, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1
        )))

    stacking = StackingRegressor(
        estimators=stacking_estimators,
        final_estimator=RidgeCV(),
        cv=3, n_jobs=-1
    )
    candidates["Stacking Super Learner"] = stacking

    # === VOTING ENSEMBLE ===
    voting_estimators = [
        ("rf", RandomForestRegressor(n_estimators=200, max_depth=15, random_state=RANDOM_STATE, n_jobs=-1)),
        ("hgb", HistGradientBoostingRegressor(max_iter=200, max_depth=5, random_state=RANDOM_STATE)),
        ("knn", KNeighborsRegressor(n_neighbors=7, weights="distance", n_jobs=-1)),
    ]
    if HAS_XGBOOST:
        voting_estimators.append(("xgb", XGBRegressor(
            n_estimators=200, max_depth=5, random_state=RANDOM_STATE, n_jobs=-1, verbosity=0
        )))

    voting = VotingRegressor(estimators=voting_estimators, n_jobs=-1)
    candidates["Voting Ensemble"] = voting

    return candidates


def evaluate_error_tolerances(y_true, y_pred) -> dict:
    """Compute percentage of predictions within strict distance error thresholds."""
    try:
        errors = np.abs(y_true - y_pred)
        total = max(1, len(errors))
        return {
            "within_10cm": round((np.sum(errors <= 0.10) / total) * 100, 2),
            "within_25cm": round((np.sum(errors <= 0.25) / total) * 100, 2),
            "within_50cm": round((np.sum(errors <= 0.50) / total) * 100, 2),
            "within_75cm": round((np.sum(errors <= 0.75) / total) * 100, 2),
            "within_100cm": round((np.sum(errors <= 1.00) / total) * 100, 2),
            "within_150cm": round((np.sum(errors <= 1.50) / total) * 100, 2),
        }
    except Exception:
        return {"within_10cm": 0.0, "within_25cm": 0.0, "within_50cm": 0.0,
                "within_75cm": 0.0, "within_100cm": 0.0, "within_150cm": 0.0}


def evaluate_extended_metrics(y_true, y_pred) -> dict:
    """Compute extended metrics for dissertation-quality reporting."""
    try:
        errors = np.abs(y_true - y_pred)

        # MAPE — guarded against division by zero
        nonzero_mask = np.abs(y_true) > 0.01
        if np.sum(nonzero_mask) > 0:
            mape = float(np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100)
        else:
            mape = 0.0

        # Max Error
        max_error = float(np.max(errors))

        # 95th Percentile Error
        p95_error = float(np.percentile(errors, 95))

        # Explained Variance Score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        explained_var = float(1.0 - ss_res / (ss_tot + 1e-10)) if ss_tot > 0 else 0.0

        # Per-Distance MAE
        unique_dists = sorted(np.unique(np.round(y_true, 1)))
        per_distance_mae = {}
        for dist in unique_dists:
            mask = np.abs(y_true - dist) < 0.05  # tolerance for float comparison
            if np.sum(mask) > 0:
                per_distance_mae[f"{dist:.1f}m"] = round(float(np.mean(np.abs(y_true[mask] - y_pred[mask]))), 4)

        return {
            "mape": round(mape, 2),
            "max_error": round(max_error, 4),
            "p95_error": round(p95_error, 4),
            "explained_variance": round(explained_var, 4),
            "per_distance_mae": per_distance_mae,
        }
    except Exception as e:
        logger.warning(f"Extended metrics computation failed: {e}")
        return {"mape": 0.0, "max_error": 0.0, "p95_error": 0.0,
                "explained_variance": 0.0, "per_distance_mae": {}}


def run_cross_validation(model, X_scaled, y, model_name: str, cv_folds: int = CV_FOLDS) -> dict:
    """Run K-Fold cross-validation and return robust mean/std metrics."""
    try:
        kf = KFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)

        mae_scores = -cross_val_score(model, X_scaled, y, cv=kf, scoring="neg_mean_absolute_error", n_jobs=-1)
        r2_scores = cross_val_score(model, X_scaled, y, cv=kf, scoring="r2", n_jobs=-1)

        result = {
            "cv_mae_mean": round(float(np.mean(mae_scores)), 4),
            "cv_mae_std": round(float(np.std(mae_scores)), 4),
            "cv_r2_mean": round(float(np.mean(r2_scores)), 4),
            "cv_r2_std": round(float(np.std(r2_scores)), 4),
        }
        print(f"    CV MAE: {result['cv_mae_mean']:.4f} ± {result['cv_mae_std']:.4f} | "
              f"CV R²: {result['cv_r2_mean']:.4f} ± {result['cv_r2_std']:.4f}")
        return result
    except Exception as e:
        print(f"    [WARN] Cross-validation failed for {model_name}: {e}")
        return {"cv_mae_mean": 99.0, "cv_mae_std": 0.0, "cv_r2_mean": -1.0, "cv_r2_std": 0.0}


def train_model(df: pd.DataFrame, model_type: str = "auto", tune_hyperparams: bool = False) -> dict:
    """
    Run Ultra-Robust Super Learner Tournament:
    1. Detect features (backward-compatible)
    2. Outlier removal
    3. Feature importance pruning
    4. Train 12+ candidates with K-Fold CV
    5. Select champion by composite score (MAE + CV stability)
    """
    feature_cols = detect_available_features(df)

    X_raw = df[feature_cols].values
    y_raw = df[TARGET_COLUMN].values

    # ── Stage 1: Outlier Detection ───────────────────────────────────
    print(f"\n{'='*75}")
    print(f"  [STAGE 1] OUTLIER DETECTION & DATA CLEANING")
    print(f"{'='*75}")
    X_clean, y_clean, n_outliers = detect_and_remove_outliers(X_raw, y_raw)

    # ── Stage 2: Train/Test Split with Stratification ────────────────
    try:
        n_uniques = len(np.unique(y_clean))
        if n_uniques > 1 and len(y_clean) >= 10:
            y_bins = pd.qcut(y_clean, q=min(5, n_uniques), labels=False, duplicates="drop")
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_bins
            )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE
            )
    except Exception:
        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )

    # Use RobustScaler — more resilient to remaining outliers than StandardScaler
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── Stage 3: Feature Importance Pruning ──────────────────────────
    print(f"\n{'='*75}")
    print(f"  [STAGE 2] FEATURE IMPORTANCE PRUNING")
    print(f"{'='*75}")
    keep_mask, quick_importances = feature_importance_pruning(
        None, X_train_scaled, y_train, feature_cols, threshold=0.001
    )

    # Apply pruning
    active_feature_cols = [f for f, k in zip(feature_cols, keep_mask) if k]
    X_train_pruned = X_train_scaled[:, keep_mask]
    X_test_pruned = X_test_scaled[:, keep_mask]

    print(f"  Active features: {len(active_feature_cols)}/{len(feature_cols)}")

    # ── Stage 4: Tournament ──────────────────────────────────────────
    candidates = instantiate_candidates()

    print(f"\n{'='*75}")
    print(f"  [STAGE 3] SUPER LEARNER TOURNAMENT ({len(candidates)} CANDIDATES)")
    print(f"  Training: {len(X_train_pruned)} samples | Testing: {len(X_test_pruned)} samples")
    print(f"  Active Features: {len(active_feature_cols)} | CV Folds: {CV_FOLDS}")
    print(f"{'='*75}")

    tournament_results = []
    trained_models = {}

    for name, model in candidates.items():
        print(f"\n[TOURNAMENT] > {name}")
        try:
            model.fit(X_train_pruned, y_train)
            y_pred = model.predict(X_test_pruned)

            mae = float(mean_absolute_error(y_test, y_pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
            r2 = float(r2_score(y_test, y_pred))
            med = float(median_absolute_error(y_test, y_pred))
            tols = evaluate_error_tolerances(y_test, y_pred)

            print(f"  -> MAE: {mae:.4f}m | RMSE: {rmse:.4f}m | R2: {r2:.4f} | "
                  f"<=25cm: {tols['within_25cm']}% | <=50cm: {tols['within_50cm']}%")

            # K-Fold Cross-Validation for robustness check
            cv_results = run_cross_validation(model, X_train_pruned, y_train, name)

            trained_models[name] = model
            tournament_results.append({
                "name": name,
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "med_ae": med,
                "tolerances": tols,
                "cv": cv_results,
                "y_pred": y_pred
            })
        except Exception as e:
            logger.error(f"Candidate {name} failed: {e}")
            print(f"  [FAILED]: {e}")

    if not tournament_results:
        # Emergency Fallback
        rf_fallback = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE)
        rf_fallback.fit(X_train_pruned, y_train)
        y_pred = rf_fallback.predict(X_test_pruned)
        mae = float(mean_absolute_error(y_test, y_pred))
        tols = evaluate_error_tolerances(y_test, y_pred)
        trained_models["Fallback RF"] = rf_fallback
        tournament_results.append({
            "name": "Fallback RF", "mae": mae,
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "r2": float(r2_score(y_test, y_pred)),
            "med_ae": float(median_absolute_error(y_test, y_pred)),
            "tolerances": tols, "cv": {}, "y_pred": y_pred
        })

    # ── Champion Selection: Composite Score ──────────────────────────
    # Score = weighted combination of test MAE and CV stability
    for res in tournament_results:
        cv_mae = res.get("cv", {}).get("cv_mae_mean", res["mae"])
        cv_std = res.get("cv", {}).get("cv_mae_std", 0.5)
        # Lower is better: penalize high MAE and high CV variance
        res["composite_score"] = 0.6 * res["mae"] + 0.3 * cv_mae + 0.1 * cv_std

    tournament_results.sort(key=lambda x: x["composite_score"])
    champion = tournament_results[0]
    champion_name = champion["name"]
    champion_model = trained_models[champion_name]

    # ── Leaderboard ──────────────────────────────────────────────────
    print(f"\n{'='*75}")
    print(f"  [LEADERBOARD] FULL TOURNAMENT RANKINGS")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Model':<30} {'MAE':>8} {'RMSE':>8} {'R2':>7} {'CV MAE':>10} {'<=25cm':>7}")
    print(f"  {'-'*5} {'-'*30} {'-'*8} {'-'*8} {'-'*7} {'-'*10} {'-'*7}")
    for i, res in enumerate(tournament_results):
        cv_str = f"{res.get('cv', {}).get('cv_mae_mean', '--')}"
        marker = " [WINNER]" if i == 0 else ""
        print(f"  {i+1:<5} {res['name']:<30} {res['mae']:8.4f} {res['rmse']:8.4f} "
              f"{res['r2']:7.4f} {cv_str:>10} {res['tolerances']['within_25cm']:6.1f}%{marker}")
    print(f"{'='*75}")

    print(f"\n{'='*75}")
    print(f"  [CHAMPION] WINNER: {champion_name.upper()}")
    print(f"{'='*75}")
    print(f"  Test MAE    : {champion['mae']:.4f} m")
    print(f"  Test RMSE   : {champion['rmse']:.4f} m")
    print(f"  Test R2     : {champion['r2']:.4f}")
    print(f"  Median AE   : {champion['med_ae']:.4f} m")
    print(f"  <= 10cm Acc : {champion['tolerances']['within_10cm']}%")
    print(f"  <= 25cm Acc : {champion['tolerances']['within_25cm']}%")
    print(f"  <= 50cm Acc : {champion['tolerances']['within_50cm']}%")
    print(f"  <= 75cm Acc : {champion['tolerances']['within_75cm']}%")
    print(f"  <= 100cm Acc: {champion['tolerances']['within_100cm']}%")
    print(f"  <= 150cm Acc: {champion['tolerances']['within_150cm']}%")
    if champion.get("cv"):
        print(f"  CV MAE      : {champion['cv']['cv_mae_mean']:.4f} +/- {champion['cv']['cv_mae_std']:.4f}")
        print(f"  CV R2       : {champion['cv']['cv_r2_mean']:.4f} +/- {champion['cv']['cv_r2_std']:.4f}")

    # V2: Extended metrics (dissertation-quality)
    ext_metrics = evaluate_extended_metrics(y_test, champion["y_pred"])
    print(f"\n  [V2 EXTENDED METRICS]")
    print(f"  MAPE           : {ext_metrics['mape']:.2f}%")
    print(f"  Max Error      : {ext_metrics['max_error']:.4f} m")
    print(f"  95th Pctl Error: {ext_metrics['p95_error']:.4f} m  (95% of predictions within this)")
    print(f"  Explained Var  : {ext_metrics['explained_variance']:.4f}")
    if ext_metrics.get('per_distance_mae'):
        print(f"  Per-Distance MAE:")
        for dist_key, dist_mae in ext_metrics['per_distance_mae'].items():
            print(f"    {dist_key:8s} : {dist_mae:.4f} m")

    # ── Permutation Feature Importance ───────────────────────────────
    perm_importances = {}
    try:
        print(f"\n[SENSITIVITY] Computing Permutation Feature Importances for Champion...")
        perm_res = permutation_importance(
            champion_model, X_test_pruned, y_test,
            n_repeats=10, random_state=RANDOM_STATE, n_jobs=-1
        )
        perm_importances = dict(zip(active_feature_cols, perm_res.importances_mean))
        perm_importances = dict(sorted(perm_importances.items(), key=lambda x: x[1], reverse=True))

        print(f"\n  Top 15 Feature Sensitivities:")
        for feat, imp in list(perm_importances.items())[:15]:
            bar = "#" * max(0, int(imp * 50))
            print(f"    {feat:28s} {imp:.4f}  {bar}")
        print(f"{'='*75}\n")
    except Exception as e:
        logger.warning(f"Permutation importance warning: {e}")

    metrics = {
        "train_mae": round(float(mean_absolute_error(y_train, champion_model.predict(X_train_pruned))), 4),
        "test_mae": round(champion["mae"], 4),
        "test_rmse": round(champion["rmse"], 4),
        "test_r2": round(champion["r2"], 4),
        "test_median_ae": round(champion["med_ae"], 4),
        "tolerances": champion["tolerances"],
        "extended": ext_metrics,
        "champion_name": champion_name,
        "cv_metrics": champion.get("cv", {}),
        "n_outliers_removed": n_outliers,
        "n_features_active": len(active_feature_cols),
        "n_features_total": len(feature_cols),
    }

    return {
        "model": champion_model,
        "scaler": scaler,
        "metrics": metrics,
        "importances": perm_importances,
        "y_test": y_test,
        "y_pred_test": champion["y_pred"],
        "y_train": y_train,
        "feature_cols": active_feature_cols,
        "all_feature_cols": feature_cols,
        "keep_mask": keep_mask.tolist(),
        "model_type": champion_name,
        "tournament": [{k: v for k, v in res.items() if k != "y_pred"} for res in tournament_results]
    }


# ──────────────────────────────────────────────────────────────────────
#  ZONE CLASSIFICATION TOURNAMENT (8+ CANDIDATES)
# ──────────────────────────────────────────────────────────────────────

def instantiate_classification_candidates() -> dict:
    """Instantiate 8+ classification candidates for zone tournament."""
    candidates = {
        "Random Forest Classifier": RandomForestClassifier(
            n_estimators=400, max_depth=20, min_samples_split=3,
            random_state=RANDOM_STATE, n_jobs=-1
        ),
        "Extra Trees Classifier": ExtraTreesClassifier(
            n_estimators=400, max_depth=20, min_samples_split=3,
            random_state=RANDOM_STATE, n_jobs=-1
        ),
        "Hist Gradient Boosting Clf": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, max_depth=6,
            random_state=RANDOM_STATE
        ),
        "Gradient Boosting Clf": GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=5,
            subsample=0.8, random_state=RANDOM_STATE
        ),
        "KNN Classifier (k=7)": KNeighborsClassifier(
            n_neighbors=7, weights="distance", n_jobs=-1
        ),
        "MLP Classifier": MLPClassifier(
            hidden_layer_sizes=(128, 64, 32), activation="relu",
            solver="adam", max_iter=500, early_stopping=True,
            random_state=RANDOM_STATE
        ),
        "AdaBoost Classifier": AdaBoostClassifier(
            n_estimators=200, learning_rate=0.05,
            random_state=RANDOM_STATE
        ),
        "Bagging Classifier": BaggingClassifier(
            n_estimators=200, max_samples=0.8, max_features=0.8,
            random_state=RANDOM_STATE, n_jobs=-1
        ),
    }

    if HAS_XGBOOST:
        candidates["XGBoost Classifier"] = XGBClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
            eval_metric="mlogloss"
        )

    if HAS_CATBOOST:
        candidates["CatBoost Classifier"] = CatBoostClassifier(
            iterations=400, learning_rate=0.05, depth=6,
            l2_leaf_reg=3.0, random_seed=RANDOM_STATE, verbose=0
        )

    if HAS_LIGHTGBM:
        candidates["LightGBM Classifier"] = LGBMClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=6,
            num_leaves=31, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1
        )

    return candidates


def train_zone_classifier(df: pd.DataFrame) -> dict:
    """Train zone classification tournament with K-Fold validation."""
    feature_cols = detect_available_features(df)

    X = df[feature_cols].values
    y_continuous = df[TARGET_COLUMN].values
    y_zones = distance_to_zone(y_continuous)

    # Encode zone labels to integers
    unique_zones = sorted(set(y_zones))
    zone_to_int = {z: i for i, z in enumerate(unique_zones)}
    int_to_zone = {i: z for z, i in zone_to_int.items()}
    y_encoded = np.array([zone_to_int[z] for z in y_zones])

    # Stratified split
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_encoded
        )
    except Exception:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )

    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    candidates = instantiate_classification_candidates()

    print(f"\n{'='*75}")
    print(f"  [ZONE CLASSIFICATION] TOURNAMENT ({len(candidates)} CANDIDATES)")
    print(f"  Zones: {unique_zones}")
    print(f"{'='*75}")

    best_f1 = -1
    best_name = None
    best_model = None
    best_y_pred = None
    clf_results = []

    for name, model in candidates.items():
        print(f"\n[ZONE] > {name}")
        try:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            acc = float(accuracy_score(y_test, y_pred))
            f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

            # K-Fold CV for classifiers
            try:
                skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
                cv_acc = cross_val_score(model, X_train_scaled, y_train, cv=skf, scoring="accuracy", n_jobs=-1)
                cv_acc_mean = round(float(np.mean(cv_acc)) * 100, 2)
                cv_acc_std = round(float(np.std(cv_acc)) * 100, 2)
            except Exception:
                cv_acc_mean = round(acc * 100, 2)
                cv_acc_std = 0.0

            print(f"  -> Accuracy: {acc*100:.2f}% | F1: {f1:.4f} | CV Acc: {cv_acc_mean}% +/- {cv_acc_std}%")

            clf_results.append({
                "name": name,
                "accuracy": round(acc * 100, 2),
                "f1_weighted": round(f1, 4),
                "cv_accuracy_mean": cv_acc_mean,
                "cv_accuracy_std": cv_acc_std,
            })

            # Use F1-weighted as champion criterion (better for imbalanced zones)
            if f1 > best_f1:
                best_f1 = f1
                best_name = name
                best_model = model
                best_y_pred = y_pred

        except Exception as e:
            logger.error(f"Zone classifier {name} failed: {e}")
            print(f"  [FAILED]: {e}")

    if best_model is None:
        print("  [!] All zone classifiers failed. Skipping classification.")
        return {}

    # Decode labels for reporting
    y_test_labels = [int_to_zone[i] for i in y_test]
    y_pred_labels = [int_to_zone[i] for i in best_y_pred]

    # Zone leaderboard
    clf_results.sort(key=lambda x: x["f1_weighted"], reverse=True)
    print(f"\n{'='*75}")
    print(f"  [ZONE LEADERBOARD]")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Classifier':<30} {'Acc':>7} {'F1':>7} {'CV Acc':>10}")
    print(f"  {'-'*5} {'-'*30} {'-'*7} {'-'*7} {'-'*10}")
    for i, res in enumerate(clf_results):
        marker = " [WINNER]" if res["name"] == best_name else ""
        print(f"  {i+1:<5} {res['name']:<30} {res['accuracy']:6.1f}% {res['f1_weighted']:6.4f} "
              f"{res['cv_accuracy_mean']:6.1f}%{marker}")

    print(f"\n{'='*75}")
    print(f"  [ZONE CHAMPION] WINNER: {best_name.upper()}")
    print(f"  Zone Accuracy: {accuracy_score(y_test, best_y_pred)*100:.2f}%")
    print(f"  F1 (weighted): {best_f1:.4f}")
    print(f"{'='*75}")

    # Per-zone classification report
    try:
        report = classification_report(y_test_labels, y_pred_labels, zero_division=0)
        print(f"\n  Per-Zone Classification Report:\n{report}")
    except Exception:
        report = ""

    # Confusion matrix
    try:
        cm = confusion_matrix(y_test_labels, y_pred_labels, labels=ZONE_LABELS)
    except Exception:
        cm = np.array([])

    return {
        "model": best_model,
        "scaler": scaler,
        "zone_accuracy": round(float(accuracy_score(y_test, best_y_pred)) * 100, 2),
        "f1_weighted": round(best_f1, 4),
        "champion_name": best_name,
        "feature_cols": feature_cols,
        "zone_labels": ZONE_LABELS,
        "zone_to_int": zone_to_int,
        "int_to_zone": int_to_zone,
        "y_test_labels": y_test_labels,
        "y_pred_labels": y_pred_labels,
        "confusion_matrix": cm,
        "classification_report": report,
        "tournament": clf_results,
    }


# ──────────────────────────────────────────────────────────────────────
#  DIAGNOSTIC PLOTS & REPORTING
# ──────────────────────────────────────────────────────────────────────

def generate_plots(result: dict, output_dir: str, zone_result: dict = None):
    """Generate comprehensive V2 diagnostic plot grid with extended analysis panels."""
    try:
        os.makedirs(output_dir, exist_ok=True)

        y_test = result.get("y_test")
        y_pred_test = result.get("y_pred_test")
        importances = result.get("importances", {})

        if y_test is None or y_pred_test is None:
            return

        has_zones = zone_result and zone_result.get("confusion_matrix") is not None and zone_result["confusion_matrix"].size > 0

        # V2: Always 4 rows (8 panels) for richer analysis
        fig, axes = plt.subplots(4, 2, figsize=(16, 26))

        fig.suptitle(f"BLE Champion: {result.get('model_type', 'Ensemble')} — V2 Diagnostics", fontsize=16, fontweight="bold")

        # 1. Predicted vs Actual
        ax = axes[0, 0]
        ax.scatter(y_test, y_pred_test, alpha=0.6, edgecolors="k", linewidths=0.5, s=45, color="#89b4fa")
        lims = [min(y_test.min(), y_pred_test.min()) - 0.5, max(y_test.max(), y_pred_test.max()) + 0.5]
        ax.plot(lims, lims, "r--", linewidth=2, label="Ideal 1:1")
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

        # 3. Top 15 Permutation Feature Importance
        ax = axes[1, 0]
        if importances:
            top_feats = list(importances.keys())[:15]
            top_vals = [max(0, float(v)) for v in list(importances.values())[:15]]
            ax.barh(top_feats[::-1], top_vals[::-1], color="#cba6f7", edgecolor="black")
            ax.set_xlabel("Permutation Sensitivity Score")
            ax.set_title("Top 15 Feature Importances")
            ax.grid(True, alpha=0.3, axis="x")

        # 4. Error Tolerance Spectrum (V2: extended thresholds)
        ax = axes[1, 1]
        tols = result["metrics"]["tolerances"]
        labels = ["\u226410cm", "\u226425cm", "\u226450cm", "\u226475cm", "\u22641m", "\u22641.5m"]
        vals = [
            tols.get("within_10cm", 0), tols.get("within_25cm", 0),
            tols.get("within_50cm", 0), tols.get("within_75cm", 0),
            tols.get("within_100cm", 0), tols.get("within_150cm", 0)
        ]
        bars = ax.bar(labels, vals, color="#f9e2af", edgecolor="black")
        ax.set_ylabel("Accuracy (%)")
        ax.set_ylim(0, 105)
        ax.set_title("Cumulative Error Tolerance Spectrum")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{yval:.1f}%", ha='center', va='bottom', fontweight='bold', fontsize=8)

        # 5. V2: Cumulative Error Distribution Curve
        ax = axes[2, 0]
        errors = np.abs(y_test - y_pred_test)
        sorted_errors = np.sort(errors)
        cumulative_pct = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors) * 100
        ax.plot(sorted_errors, cumulative_pct, color="#89b4fa", linewidth=2.5)
        ax.axhline(y=95, color="#f38ba8", linestyle="--", linewidth=1.5, label="95th percentile")
        ax.axhline(y=50, color="#f9e2af", linestyle="--", linewidth=1.5, label="50th percentile")
        # Mark key thresholds
        for thresh, label in [(0.25, "25cm"), (0.50, "50cm"), (1.0, "1m")]:
            pct = float(np.sum(errors <= thresh)) / len(errors) * 100
            ax.axvline(x=thresh, color="#a6adc8", linestyle=":", alpha=0.7)
            ax.text(thresh + 0.02, 5, f"{label}\n{pct:.0f}%", fontsize=7, color="#a6adc8")
        ax.set_xlabel("Absolute Error (m)")
        ax.set_ylabel("Cumulative Percentage (%)")
        ax.set_title("Cumulative Error Distribution (CDF)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, max(sorted_errors[-1] * 1.05, 2.0))

        # 6. V2: Per-Distance MAE Bar Chart
        ax = axes[2, 1]
        ext_metrics = result.get("metrics", {}).get("extended", {})
        per_dist_mae = ext_metrics.get("per_distance_mae", {})
        if per_dist_mae:
            dist_labels = list(per_dist_mae.keys())
            dist_vals = list(per_dist_mae.values())
            colors_dist = ["#89b4fa", "#a6e3a1", "#f9e2af", "#fab387", "#f38ba8", "#cba6f7", "#94e2d5"]
            bar_colors = [colors_dist[i % len(colors_dist)] for i in range(len(dist_labels))]
            bars = ax.bar(dist_labels, dist_vals, color=bar_colors, edgecolor="black")
            ax.axhline(y=result["metrics"]["test_mae"], color="red", linestyle="--", linewidth=1.5, label=f"Overall MAE ({result['metrics']['test_mae']:.3f}m)")
            ax.set_ylabel("MAE (metres)")
            ax.set_title("Per-Distance MAE Breakdown")
            ax.grid(True, alpha=0.3, axis="y")
            ax.legend(fontsize=8)
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.01, f"{yval:.3f}", ha='center', va='bottom', fontweight='bold', fontsize=8)
        else:
            ax.text(0.5, 0.5, "Per-distance MAE\nnot available", ha='center', va='center', transform=ax.transAxes, fontsize=12, color="#a6adc8")
            ax.set_title("Per-Distance MAE")

        # 7 & 8. Zone Classification panels (if available)
        if has_zones:
            # 7. Confusion Matrix
            ax = axes[3, 0]
            cm = zone_result["confusion_matrix"]
            zone_labels = zone_result["zone_labels"]
            n_zones = min(len(zone_labels), cm.shape[0])
            display_labels = zone_labels[:n_zones]

            im = ax.imshow(cm[:n_zones, :n_zones], interpolation='nearest', cmap='Blues')
            ax.set_title(f"Zone Confusion ({zone_result['champion_name']})")
            ax.set_xlabel("Predicted Zone")
            ax.set_ylabel("Actual Zone")
            ax.set_xticks(range(n_zones))
            ax.set_xticklabels(display_labels, rotation=45, ha="right", fontsize=7)
            ax.set_yticks(range(n_zones))
            ax.set_yticklabels(display_labels, fontsize=7)

            for i in range(n_zones):
                for j in range(n_zones):
                    val = cm[i, j]
                    color = "white" if val > cm.max() / 2 else "black"
                    ax.text(j, i, str(val), ha="center", va="center", color=color, fontweight="bold")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

            # 8. Zone Accuracy Bar Chart
            ax = axes[3, 1]
            y_test_labels = zone_result["y_test_labels"]
            y_pred_labels = zone_result["y_pred_labels"]
            zone_accs = []
            for label in zone_labels:
                mask = [yt == label for yt in y_test_labels]
                if sum(mask) > 0:
                    correct = sum(1 for yt, yp in zip(y_test_labels, y_pred_labels) if yt == label and yp == label)
                    zone_accs.append(correct / sum(mask) * 100)
                else:
                    zone_accs.append(0)

            colors_list = ["#89b4fa", "#a6e3a1", "#f9e2af", "#fab387", "#f38ba8"]
            bars = ax.bar(zone_labels, zone_accs, color=colors_list[:len(zone_labels)], edgecolor="black")
            ax.set_ylabel("Accuracy (%)")
            ax.set_ylim(0, 105)
            ax.set_title(f"Per-Zone Accuracy ({zone_result['zone_accuracy']}% overall)")
            ax.grid(True, alpha=0.3, axis="y")
            ax.set_xticklabels(zone_labels, rotation=20, ha="right", fontsize=7)
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{yval:.1f}%", ha='center', va='bottom', fontweight='bold', fontsize=8)
        else:
            # No zones — hide bottom row
            axes[3, 0].axis("off")
            axes[3, 1].axis("off")

        plt.tight_layout()
        plot_path = os.path.join(output_dir, "model_diagnostics.png")
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[PLOT] V2 diagnostic plots saved: {plot_path}")
    except Exception as e:
        logger.error(f"Failed to generate diagnostic plots: {e}")


def save_model(result: dict, output_dir: str, zone_result: dict = None):
    """Save model, scaler, and rich metadata."""
    try:
        os.makedirs(output_dir, exist_ok=True)

        joblib.dump(result["model"], os.path.join(output_dir, "distance_estimator.joblib"))
        joblib.dump(result["scaler"], os.path.join(output_dir, "scaler.joblib"))

        metadata = {
            "champion_model": result["model_type"],
            "feature_cols": result["feature_cols"],
            "all_feature_cols": result.get("all_feature_cols", result["feature_cols"]),
            "keep_mask": result.get("keep_mask", [True] * len(result["feature_cols"])),
            "metrics": result["metrics"],
            "importances": {k: round(float(v), 6) for k, v in result["importances"].items()},
            "tournament": result["tournament"],
            "trained_at": datetime.datetime.now().isoformat(),
            "train_samples": len(result["y_train"]),
            "test_samples": len(result["y_test"]),
            "pipeline_version": "2.0-motion-aware",
            "has_cross_window_features": any(c in result["feature_cols"] for c in CROSS_WINDOW_FEATURE_COLUMNS),
            "n_cross_window_features": sum(1 for c in result["feature_cols"] if c in CROSS_WINDOW_FEATURE_COLUMNS),
        }

        # Save zone classification results
        if zone_result and zone_result.get("model"):
            joblib.dump(zone_result["model"], os.path.join(output_dir, "zone_classifier.joblib"))
            joblib.dump(zone_result["scaler"], os.path.join(output_dir, "zone_scaler.joblib"))
            metadata["zone_classification"] = {
                "champion_classifier": zone_result["champion_name"],
                "zone_accuracy": zone_result["zone_accuracy"],
                "f1_weighted": zone_result.get("f1_weighted", 0),
                "zone_labels": zone_result["zone_labels"],
                "zone_to_int": zone_result["zone_to_int"],
                "feature_cols": zone_result["feature_cols"],
                "tournament": zone_result["tournament"],
            }
            print(f"[SAVE] Zone classifier saved: {os.path.join(output_dir, 'zone_classifier.joblib')}")

        with open(os.path.join(output_dir, "model_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"[SAVE] Champion model & scaler saved to {output_dir}")
    except Exception as e:
        logger.error(f"Failed to save model assets: {e}")


def main():
    parser = argparse.ArgumentParser(description="BLE Ultra-Robust Super Learner Tournament")
    parser.add_argument("--dataset", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--model-type", type=str, default="auto")
    parser.add_argument("--tune", action="store_true")
    parser.add_argument("--mode", type=str, choices=["regression", "classification", "both"], default="both",
                        help="Training mode: regression only, classification (zones) only, or both (default)")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.dataset is None:
        args.dataset = os.path.join(project_root, "datasets", "observations.csv")

    if args.output_dir is None:
        args.output_dir = os.path.join(project_root, "models")

    df = load_dataset(args.dataset)

    result = None
    zone_result = None

    if args.mode in ("regression", "both"):
        result = train_model(df, model_type=args.model_type, tune_hyperparams=args.tune)

    if args.mode in ("classification", "both"):
        zone_result = train_zone_classifier(df)

    if result:
        save_model(result, args.output_dir, zone_result=zone_result)
        reports_dir = os.path.join(os.path.dirname(args.output_dir), "reports")
        generate_plots(result, reports_dir, zone_result=zone_result)
    elif zone_result:
        os.makedirs(args.output_dir, exist_ok=True)
        joblib.dump(zone_result["model"], os.path.join(args.output_dir, "zone_classifier.joblib"))
        joblib.dump(zone_result["scaler"], os.path.join(args.output_dir, "zone_scaler.joblib"))
        meta = {
            "zone_classification": {
                "champion_classifier": zone_result["champion_name"],
                "zone_accuracy": zone_result["zone_accuracy"],
                "zone_labels": zone_result["zone_labels"],
                "tournament": zone_result["tournament"],
                "trained_at": datetime.datetime.now().isoformat(),
            }
        }
        with open(os.path.join(args.output_dir, "model_metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)

    print(f"\n[DONE] Ultra-Robust Super Learner Tournament Complete!")


if __name__ == "__main__":
    main()
