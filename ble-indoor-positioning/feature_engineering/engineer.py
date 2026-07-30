"""
Feature Engineering: Raw BLE Packets → 1-Second Observation Windows
===================================================================

Takes raw per-packet CSV files from the collector and aggregates them
into 1-second observation windows with statistical RSSI features.

Input CSV columns:
    timestamp, anchor, mac, rssi, name, distance_m, obstacle, obstacle_type

Output CSV columns:
    window_start, anchor_id, packet_count, scan_duration_ms,
    rssi_mean, rssi_min, rssi_max, rssi_std, rssi_variance,
    rssi_delta_mean, observed_adv_interval,
    distance_m, obstacle, obstacle_type
"""

import os
import glob
import argparse
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

# 1-second window size in milliseconds (matching dataset.md spec)
WINDOW_SIZE_MS = 1000

# Minimum packets in a window to keep (too few → unreliable stats)
MIN_PACKETS_PER_WINDOW = 3


# ──────────────────────────────────────────────────────────────────────
#  CORE FEATURE EXTRACTION
# ──────────────────────────────────────────────────────────────────────

def compute_window_features(group: pd.DataFrame) -> dict:
    """
    Compute statistical features for a single observation window.

    Parameters
    ----------
    group : pd.DataFrame
        A group of raw packets within one 1-second window.

    Returns
    -------
    dict
        Computed features for this window.
    """
    rssi_values = group["rssi"].values.astype(float)
    timestamps  = group["timestamp"].values.astype(float)

    packet_count     = len(rssi_values)
    scan_duration_ms = float(timestamps[-1] - timestamps[0]) if packet_count > 1 else 0.0

    rssi_mean     = float(np.mean(rssi_values))
    rssi_min      = float(np.min(rssi_values))
    rssi_max      = float(np.max(rssi_values))
    rssi_std      = float(np.std(rssi_values, ddof=1)) if packet_count > 1 else 0.0
    rssi_variance = float(np.var(rssi_values, ddof=1)) if packet_count > 1 else 0.0

    # Mean absolute RSSI delta between consecutive packets
    if packet_count > 1:
        deltas = np.abs(np.diff(rssi_values))
        rssi_delta_mean = float(np.mean(deltas))
    else:
        rssi_delta_mean = 0.0

    # Observed advertisement interval (mean time between packets in ms)
    if packet_count > 1:
        time_deltas = np.diff(timestamps)
        observed_adv_interval = float(np.mean(time_deltas))
    else:
        observed_adv_interval = 0.0

    return {
        "packet_count":          packet_count,
        "scan_duration_ms":      scan_duration_ms,
        "rssi_mean":             round(rssi_mean, 4),
        "rssi_min":              rssi_min,
        "rssi_max":              rssi_max,
        "rssi_std":              round(rssi_std, 4),
        "rssi_variance":         round(rssi_variance, 4),
        "rssi_delta_mean":       round(rssi_delta_mean, 4),
        "observed_adv_interval": round(observed_adv_interval, 4),
    }


# ──────────────────────────────────────────────────────────────────────
#  PIPELINE: RAW CSV → OBSERVATION WINDOWS
# ──────────────────────────────────────────────────────────────────────

def process_raw_csv(filepath: str, target_mac: str = None) -> pd.DataFrame:
    """
    Load a raw CSV and transform it into observation-window features.

    Parameters
    ----------
    filepath : str
        Path to the raw collector CSV file.
    target_mac : str, optional
        If provided, only keep packets from this MAC address.
        Supports case-insensitive matching.

    Returns
    -------
    pd.DataFrame
        One row per 1-second observation window.
    """
    df = pd.read_csv(filepath)

    # Basic validation
    required_cols = {"timestamp", "anchor", "mac", "rssi", "distance_m"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing columns in {filepath}: {missing}")

    # Ensure numeric types
    df["timestamp"]  = pd.to_numeric(df["timestamp"], errors="coerce")
    df["rssi"]       = pd.to_numeric(df["rssi"], errors="coerce")
    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df.dropna(subset=["timestamp", "rssi", "distance_m"], inplace=True)

    # Filter by target MAC if specified
    if target_mac:
        df = df[df["mac"].str.upper() == target_mac.upper()].copy()
        if df.empty:
            print(f"  [!] No packets for MAC {target_mac} in {os.path.basename(filepath)}")
            return pd.DataFrame()

    # Sort by timestamp
    df.sort_values("timestamp", inplace=True)

    # Assign each packet to a 1-second window
    t_min = df["timestamp"].min()
    df["window_id"] = ((df["timestamp"] - t_min) // WINDOW_SIZE_MS).astype(int)

    # Group by anchor + window and compute features
    rows = []
    for (anchor, window_id), group in df.groupby(["anchor", "window_id"]):
        if len(group) < MIN_PACKETS_PER_WINDOW:
            continue

        features = compute_window_features(group)

        # Metadata from the first packet in this window
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

    # Reorder columns to match dataset.md spec
    col_order = [
        "window_start", "anchor_id", "packet_count", "scan_duration_ms",
        "rssi_mean", "rssi_min", "rssi_max", "rssi_std", "rssi_variance",
        "rssi_delta_mean", "observed_adv_interval",
        "distance_m", "obstacle", "obstacle_type"
    ]
    result = result[[c for c in col_order if c in result.columns]]
    return result


def process_all_raw_csvs(raw_dir: str, output_path: str, target_mac: str = None) -> pd.DataFrame:
    """
    Process all raw CSV files in a directory and merge into one dataset.

    Parameters
    ----------
    raw_dir : str
        Directory containing raw collector CSV files.
    output_path : str
        Where to save the engineered dataset.
    target_mac : str, optional
        If provided, filter for this specific BLE device.

    Returns
    -------
    pd.DataFrame
        The merged, engineered dataset.
    """
    csv_files = sorted(glob.glob(os.path.join(raw_dir, "dataset_*.csv")))

    if not csv_files:
        raise FileNotFoundError(f"No raw CSV files found in {raw_dir}")

    print(f"Found {len(csv_files)} raw CSV file(s) in {raw_dir}")
    if target_mac:
        print(f"Filtering for target MAC: {target_mac}")

    all_windows = []
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        df = process_raw_csv(fpath, target_mac=target_mac)
        if df.empty:
            print(f"  [SKIP] {fname} -> 0 windows (skipped)")
        else:
            print(f"  [OK] {fname} -> {len(df)} observation windows")
            all_windows.append(df)

    if not all_windows:
        raise ValueError("No observation windows were generated from any CSV file.")

    merged = pd.concat(all_windows, ignore_index=True)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"\n[DONE] Engineered dataset saved: {output_path}")
    print(f"   Total observation windows: {len(merged)}")
    print(f"   Distance coverage: {sorted(merged['distance_m'].unique())} m")
    print(f"   Features: {list(merged.columns)}")

    return merged


# ──────────────────────────────────────────────────────────────────────
#  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BLE Feature Engineering: raw packets → observation windows"
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        required=True,
        help="Path to the directory containing raw collector CSV files"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for the engineered dataset CSV (default: datasets/observations.csv)"
    )
    parser.add_argument(
        "--target-mac",
        type=str,
        default=None,
        help="Only include packets from this BLE MAC address (e.g. 52:06:26:03:01:DA)"
    )
    args = parser.parse_args()

    # Default output path
    if args.output is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output = os.path.join(project_root, "datasets", "observations.csv")

    process_all_raw_csvs(args.raw_dir, args.output, target_mac=args.target_mac)


if __name__ == "__main__":
    main()
