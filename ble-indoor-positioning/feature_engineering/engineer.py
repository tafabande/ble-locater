"""
Feature Engineering: Raw BLE Packets → 1-Second Observation Windows
===================================================================

Extracts 30 state-of-the-art physical, statistical, and interaction features
per 1-second observation window for maximum localization precision.
"""

import os
import glob
import argparse
import numpy as np
import pandas as pd
from scipy import stats


# ──────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

WINDOW_SIZE_MS = 1000
MIN_PACKETS_PER_WINDOW = 1


# ──────────────────────────────────────────────────────────────────────
#  CORE FEATURE EXTRACTION (30 FEATURES)
# ──────────────────────────────────────────────────────────────────────

def compute_window_features(group: pd.DataFrame) -> dict:
    """
    Compute 30 advanced physical, statistical, and interaction features.
    """
    rssi_values = group["rssi"].values.astype(float)
    timestamps  = group["timestamp"].values.astype(float)

    packet_count     = len(rssi_values)
    scan_duration_ms = float(timestamps[-1] - timestamps[0]) if packet_count > 1 else 0.0

    # 1. Primary Statistical Moments
    rssi_mean   = float(np.mean(rssi_values))
    rssi_median = float(np.median(rssi_values))
    rssi_min    = float(np.min(rssi_values))
    rssi_max    = float(np.max(rssi_values))
    rssi_std    = float(np.std(rssi_values, ddof=1)) if packet_count > 1 else 0.0
    rssi_var    = float(np.var(rssi_values, ddof=1)) if packet_count > 1 else 0.0

    # 2. Percentile Spectrum & Quantiles
    rssi_p05 = float(np.percentile(rssi_values, 5))
    rssi_p10 = float(np.percentile(rssi_values, 10))
    rssi_p25 = float(np.percentile(rssi_values, 25))
    rssi_p75 = float(np.percentile(rssi_values, 75))
    rssi_p90 = float(np.percentile(rssi_values, 90))
    rssi_p95 = float(np.percentile(rssi_values, 95))

    # 3. Dispersion & Spread Measures
    rssi_range = rssi_max - rssi_min
    rssi_iqr   = rssi_p75 - rssi_p25
    rssi_p90_10_range = rssi_p90 - rssi_p10
    rssi_mad   = float(np.median(np.abs(rssi_values - rssi_median)))
    rssi_snr   = abs(rssi_mean) / (rssi_std + 1e-5)  # Signal-to-Noise ratio proxy

    # 4. Shape & Higher Order Moments
    if packet_count > 2 and rssi_std > 0:
        rssi_skew = float(stats.skew(rssi_values))
        rssi_kurt = float(stats.kurtosis(rssi_values))
    else:
        rssi_skew = 0.0
        rssi_kurt = 0.0

    # 5. Dynamics & Temporal Deltas
    if packet_count > 1:
        deltas = np.abs(np.diff(rssi_values))
        rssi_delta_mean = float(np.mean(deltas))
        rssi_delta_std  = float(np.std(deltas, ddof=1)) if len(deltas) > 1 else 0.0
        rssi_delta_max  = float(np.max(deltas))

        time_deltas = np.diff(timestamps)
        observed_adv_interval = float(np.mean(time_deltas))
        adv_interval_std      = float(np.std(time_deltas, ddof=1)) if len(time_deltas) > 1 else 0.0
    else:
        rssi_delta_mean = 0.0
        rssi_delta_std  = 0.0
        rssi_delta_max  = 0.0
        observed_adv_interval = 0.0
        adv_interval_std      = 0.0

    # 6. Physical Path Loss Priors & Feature Interactions
    n_free_space = 2.0
    n_indoor_obs = 3.0
    path_loss_free_space = 10.0 ** ((-60.0 - rssi_mean) / (10.0 * n_free_space))
    path_loss_indoor     = 10.0 ** ((-60.0 - rssi_mean) / (10.0 * n_indoor_obs))

    path_loss_free_space = min(25.0, max(0.1, path_loss_free_space))
    path_loss_indoor     = min(25.0, max(0.1, path_loss_indoor))

    # Nonlinear interaction terms
    rssi_mean_to_std_ratio = rssi_mean / (rssi_std + 1.0)
    rssi_median_mean_diff = rssi_median - rssi_mean

    return {
        "packet_count":          packet_count,
        "scan_duration_ms":      scan_duration_ms,
        "rssi_mean":             round(rssi_mean, 4),
        "rssi_median":           round(rssi_median, 4),
        "rssi_min":              rssi_min,
        "rssi_max":              rssi_max,
        "rssi_std":              round(rssi_std, 4),
        "rssi_variance":         round(rssi_var, 4),
        "rssi_range":            round(rssi_range, 4),
        "rssi_p05":              round(rssi_p05, 4),
        "rssi_p10":              round(rssi_p10, 4),
        "rssi_p25":              round(rssi_p25, 4),
        "rssi_p75":              round(rssi_p75, 4),
        "rssi_p90":              round(rssi_p90, 4),
        "rssi_p95":              round(rssi_p95, 4),
        "rssi_iqr":              round(rssi_iqr, 4),
        "rssi_p90_10_range":     round(rssi_p90_10_range, 4),
        "rssi_mad":              round(rssi_mad, 4),
        "rssi_snr":              round(rssi_snr, 4),
        "rssi_skewness":         round(rssi_skew, 4),
        "rssi_kurtosis":         round(rssi_kurt, 4),
        "rssi_delta_mean":       round(rssi_delta_mean, 4),
        "rssi_delta_std":        round(rssi_delta_std, 4),
        "rssi_delta_max":        round(rssi_delta_max, 4),
        "observed_adv_interval": round(observed_adv_interval, 4),
        "adv_interval_std":      round(adv_interval_std, 4),
        "path_loss_free_space":  round(path_loss_free_space, 4),
        "path_loss_indoor":      round(path_loss_indoor, 4),
        "rssi_mean_to_std_ratio":round(rssi_mean_to_std_ratio, 4),
        "rssi_median_mean_diff": round(rssi_median_mean_diff, 4),
    }


# ──────────────────────────────────────────────────────────────────────
#  PIPELINE PROCESSING
# ──────────────────────────────────────────────────────────────────────

def process_raw_csv(filepath: str, target_mac: str = None) -> pd.DataFrame:
    """Load a raw CSV and transform it into 30 observation-window features."""
    df = pd.read_csv(filepath)

    required_cols = {"timestamp", "anchor", "mac", "rssi", "distance_m"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing columns in {filepath}: {missing}")

    df["timestamp"]  = pd.to_numeric(df["timestamp"], errors="coerce")
    df["rssi"]       = pd.to_numeric(df["rssi"], errors="coerce")
    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df.dropna(subset=["timestamp", "rssi", "distance_m"], inplace=True)

    if target_mac:
        df = df[df["mac"].str.upper() == target_mac.upper()].copy()
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
        features["window_start"]  = int(t_min + window_id * WINDOW_SIZE_MS)
        features["anchor_id"]     = anchor
        features["distance_m"]    = float(first["distance_m"])
        features["obstacle"]      = first.get("obstacle", "No")
        features["obstacle_type"] = first.get("obstacle_type", "None")

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
    csv_files = sorted(glob.glob(os.path.join(raw_dir, "dataset_*.csv")))

    if not csv_files:
        raise FileNotFoundError(f"No raw CSV files found in {raw_dir}")

    print(f"[AUDIT] Scanning {len(csv_files)} raw CSV file(s) in {raw_dir}")
    if target_mac:
        print(f"[FILTER] Target MAC lock: {target_mac}")

    all_windows = []
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        df = process_raw_csv(fpath, target_mac=target_mac)
        if df.empty:
            print(f"  [SKIP] {fname} -> 0 windows (skipped)")
        else:
            print(f"  [OK] {fname} -> {len(df)} observation windows (30 features)")
            all_windows.append(df)

    if not all_windows:
        raise ValueError("No observation windows were generated from any CSV file.")

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
