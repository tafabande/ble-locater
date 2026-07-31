"""
Feature Engineering: Raw BLE Packets → 1-Second Observation Windows
===================================================================

Extracts 30 state-of-the-art physical, statistical, and interaction features
per 1-second observation window for maximum localization precision.
Now updated with crash-proof safeguards against NaN/Inf values.
"""

import os
import glob
import logging
import argparse
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("FEATURE_ENGINEERING")

# ──────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

WINDOW_SIZE_MS = 1000
MIN_PACKETS_PER_WINDOW = 1


def _safe_float(val: float, default: float = 0.0, min_val: float = -1e5, max_val: float = 1e5) -> float:
    """Sanitizes floats to prevent NaN or Inf from corrupting ML feature vectors."""
    try:
        f_val = float(val)
        if not np.isfinite(f_val):
            return float(default)
        return float(max(min_val, min(max_val, f_val)))
    except Exception:
        return float(default)


# ──────────────────────────────────────────────────────────────────────
#  CORE FEATURE EXTRACTION (30 FEATURES)
# ──────────────────────────────────────────────────────────────────────

def compute_window_features(group: pd.DataFrame) -> dict:
    """
    Compute 30 advanced physical, statistical, and interaction features safely.
    """
    if group is None or group.empty or "rssi" not in group:
        # Fallback dictionary of zeros
        return {
            "packet_count": 0, "scan_duration_ms": 0.0, "rssi_mean": -70.0, "rssi_median": -70.0,
            "rssi_min": -70.0, "rssi_max": -70.0, "rssi_std": 0.0, "rssi_variance": 0.0,
            "rssi_range": 0.0, "rssi_p05": -70.0, "rssi_p10": -70.0, "rssi_p25": -70.0,
            "rssi_p75": -70.0, "rssi_p90": -70.0, "rssi_p95": -70.0, "rssi_iqr": 0.0,
            "rssi_p90_10_range": 0.0, "rssi_mad": 0.0, "rssi_snr": 0.0, "rssi_skewness": 0.0,
            "rssi_kurtosis": 0.0, "rssi_delta_mean": 0.0, "rssi_delta_std": 0.0, "rssi_delta_max": 0.0,
            "observed_adv_interval": 0.0, "adv_interval_std": 0.0, "path_loss_free_space": 3.16,
            "path_loss_indoor": 2.15, "rssi_mean_to_std_ratio": -70.0, "rssi_median_mean_diff": 0.0
        }

    try:
        rssi_raw = pd.to_numeric(group["rssi"], errors="coerce").dropna().values.astype(float)
        ts_raw = pd.to_numeric(group["timestamp"], errors="coerce").dropna().values.astype(float)
    except Exception:
        rssi_raw = np.array([-70.0])
        ts_raw = np.array([0.0])

    if len(rssi_raw) == 0:
        rssi_raw = np.array([-70.0])
    if len(ts_raw) == 0:
        ts_raw = np.array([0.0])

    rssi_values = np.nan_to_num(rssi_raw, nan=-70.0, posinf=0.0, neginf=-120.0)
    timestamps = np.nan_to_num(ts_raw, nan=0.0, posinf=1e12, neginf=0.0)

    packet_count = len(rssi_values)
    scan_duration_ms = float(timestamps[-1] - timestamps[0]) if packet_count > 1 else 0.0
    scan_duration_ms = max(0.0, scan_duration_ms)

    # 1. Primary Statistical Moments
    rssi_mean = float(np.mean(rssi_values))
    rssi_median = float(np.median(rssi_values))
    rssi_min = float(np.min(rssi_values))
    rssi_max = float(np.max(rssi_values))
    rssi_std = float(np.std(rssi_values, ddof=1)) if packet_count > 1 else 0.0
    rssi_var = float(np.var(rssi_values, ddof=1)) if packet_count > 1 else 0.0

    # 2. Percentile Spectrum & Quantiles
    rssi_p05 = float(np.percentile(rssi_values, 5))
    rssi_p10 = float(np.percentile(rssi_values, 10))
    rssi_p25 = float(np.percentile(rssi_values, 25))
    rssi_p75 = float(np.percentile(rssi_values, 75))
    rssi_p90 = float(np.percentile(rssi_values, 90))
    rssi_p95 = float(np.percentile(rssi_values, 95))

    # 3. Dispersion & Spread Measures
    rssi_range = rssi_max - rssi_min
    rssi_iqr = rssi_p75 - rssi_p25
    rssi_p90_10_range = rssi_p90 - rssi_p10
    rssi_mad = float(np.median(np.abs(rssi_values - rssi_median)))
    rssi_snr = abs(rssi_mean) / (rssi_std + 1e-5)

    # 4. Shape & Higher Order Moments
    if packet_count > 2 and rssi_std > 1e-5:
        try:
            rssi_skew = float(stats.skew(rssi_values))
            rssi_kurt = float(stats.kurtosis(rssi_values))
        except Exception:
            rssi_skew = 0.0
            rssi_kurt = 0.0
    else:
        rssi_skew = 0.0
        rssi_kurt = 0.0

    # 5. Dynamics & Temporal Deltas
    if packet_count > 1:
        deltas = np.abs(np.diff(rssi_values))
        rssi_delta_mean = float(np.mean(deltas)) if len(deltas) > 0 else 0.0
        rssi_delta_std = float(np.std(deltas, ddof=1)) if len(deltas) > 1 else 0.0
        rssi_delta_max = float(np.max(deltas)) if len(deltas) > 0 else 0.0

        time_deltas = np.diff(timestamps)
        time_deltas = time_deltas[time_deltas >= 0]
        observed_adv_interval = float(np.mean(time_deltas)) if len(time_deltas) > 0 else 0.0
        adv_interval_std = float(np.std(time_deltas, ddof=1)) if len(time_deltas) > 1 else 0.0
    else:
        rssi_delta_mean = 0.0
        rssi_delta_std = 0.0
        rssi_delta_max = 0.0
        observed_adv_interval = 0.0
        adv_interval_std = 0.0

    # 6. Physical Path Loss Priors & Feature Interactions
    n_free_space = 2.0
    n_indoor_obs = 3.0

    exp_fs = (-60.0 - rssi_mean) / (10.0 * n_free_space)
    exp_in = (-60.0 - rssi_mean) / (10.0 * n_indoor_obs)

    path_loss_free_space = 10.0 ** max(-2.0, min(3.0, exp_fs))
    path_loss_indoor = 10.0 ** max(-2.0, min(3.0, exp_in))

    path_loss_free_space = min(25.0, max(0.1, path_loss_free_space))
    path_loss_indoor = min(25.0, max(0.1, path_loss_indoor))

    rssi_mean_to_std_ratio = rssi_mean / (rssi_std + 1.0)
    rssi_median_mean_diff = rssi_median - rssi_mean

    features_raw = {
        "packet_count": packet_count,
        "scan_duration_ms": scan_duration_ms,
        "rssi_mean": rssi_mean,
        "rssi_median": rssi_median,
        "rssi_min": rssi_min,
        "rssi_max": rssi_max,
        "rssi_std": rssi_std,
        "rssi_variance": rssi_var,
        "rssi_range": rssi_range,
        "rssi_p05": rssi_p05,
        "rssi_p10": rssi_p10,
        "rssi_p25": rssi_p25,
        "rssi_p75": rssi_p75,
        "rssi_p90": rssi_p90,
        "rssi_p95": rssi_p95,
        "rssi_iqr": rssi_iqr,
        "rssi_p90_10_range": rssi_p90_10_range,
        "rssi_mad": rssi_mad,
        "rssi_snr": rssi_snr,
        "rssi_skewness": rssi_skew,
        "rssi_kurtosis": rssi_kurt,
        "rssi_delta_mean": rssi_delta_mean,
        "rssi_delta_std": rssi_delta_std,
        "rssi_delta_max": rssi_delta_max,
        "observed_adv_interval": observed_adv_interval,
        "adv_interval_std": adv_interval_std,
        "path_loss_free_space": path_loss_free_space,
        "path_loss_indoor": path_loss_indoor,
        "rssi_mean_to_std_ratio": rssi_mean_to_std_ratio,
        "rssi_median_mean_diff": rssi_median_mean_diff,
    }

    # Final sanitization pass
    features_clean = {}
    for k, v in features_raw.items():
        if k == "packet_count":
            features_clean[k] = int(v)
        else:
            features_clean[k] = round(_safe_float(v), 4)

    return features_clean


# ──────────────────────────────────────────────────────────────────────
#  PIPELINE PROCESSING
# ──────────────────────────────────────────────────────────────────────

def process_raw_csv(filepath: str, target_mac: str = None) -> pd.DataFrame:
    """Load a raw CSV and transform it into 30 observation-window features."""
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        logger.error(f"Failed to parse CSV file {filepath}: {e}")
        return pd.DataFrame()

    required_cols = {"timestamp", "anchor", "mac", "rssi", "distance_m"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        logger.warning(f"Missing required columns in {filepath}: {missing}")
        return pd.DataFrame()

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["rssi"] = pd.to_numeric(df["rssi"], errors="coerce")
    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df.dropna(subset=["timestamp", "rssi", "distance_m"], inplace=True)

    if df.empty:
        return pd.DataFrame()

    if target_mac:
        df = df[df["mac"].astype(str).str.upper() == target_mac.upper()].copy()
        if df.empty:
            print(f"  [!] No packets for MAC {target_mac} in {os.path.basename(filepath)}")
            return pd.DataFrame()

    df.sort_values("timestamp", inplace=True)

    t_min = df["timestamp"].min()
    df["window_id"] = ((df["timestamp"] - t_min) // WINDOW_SIZE_MS).astype(int)

    rows = []
    for (anchor, window_id), group in df.groupby(["anchor", "window_id"]):
        if len(group) < MIN_PACKETS_PER_WINDOW:
            continue

        features = compute_window_features(group)
        first = group.iloc[0]
        features["window_start"] = int(t_min + window_id * WINDOW_SIZE_MS)
        features["anchor_id"] = str(anchor)
        features["distance_m"] = float(first["distance_m"])
        features["obstacle"] = str(first.get("obstacle", "No"))
        features["obstacle_type"] = str(first.get("obstacle_type", "None"))

        rows.append(features)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    meta_cols = ["window_start", "anchor_id", "distance_m", "obstacle", "obstacle_type"]
    feat_cols = [c for c in result.columns if c not in meta_cols]
    col_order = ["window_start", "anchor_id"] + feat_cols + ["distance_m", "obstacle", "obstacle_type"]

    return result[col_order]


def process_all_raw_csvs(raw_dir: str, output_path: str, target_mac: str = None) -> pd.DataFrame:
    """Process all raw CSV files in a directory and merge into one dataset."""
    if not os.path.exists(raw_dir):
        raise FileNotFoundError(f"Raw CSV directory not found: {raw_dir}")

    csv_files = sorted(glob.glob(os.path.join(raw_dir, "dataset_*.csv")))

    if not csv_files:
        raise FileNotFoundError(f"No raw CSV files matching 'dataset_*.csv' found in {raw_dir}")

    print(f"[AUDIT] Scanning {len(csv_files)} raw CSV file(s) in {raw_dir}")
    if target_mac:
        print(f"[FILTER] Target MAC lock: {target_mac}")

    all_windows = []
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        try:
            df = process_raw_csv(fpath, target_mac=target_mac)
            if df.empty:
                print(f"  [SKIP] {fname} -> 0 windows (skipped)")
            else:
                print(f"  [OK] {fname} -> {len(df)} observation windows (30 features)")
                all_windows.append(df)
        except Exception as e:
            print(f"  [ERROR] Failed processing {fname}: {e}")

    if not all_windows:
        raise ValueError("No valid observation windows were generated from any CSV file.")

    merged = pd.concat(all_windows, ignore_index=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"\n[DONE] Engineered dataset saved: {output_path}")
    print(f"   Total Observation Windows: {len(merged)}")
    print(f"   Distance Presets: {sorted(merged['distance_m'].unique())} m")
    print(f"   Extracted Features Count: {len(merged.columns) - 5}")

    return merged


def main():
    parser = argparse.ArgumentParser(description="BLE 30-Feature Engineering Pipeline")
    parser.add_argument("--raw-dir", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--target-mac", type=str, default=None)
    args = parser.parse_args()

    if args.output is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output = os.path.join(project_root, "datasets", "observations.csv")

    process_all_raw_csvs(args.raw_dir, args.output, target_mac=args.target_mac)


if __name__ == "__main__":
    main()
