import os
import glob
import logging
import argparse
import numpy as np
import pandas as pd
from scipy import stats
logger = logging.getLogger('FEATURE_ENGINEERING')
WINDOW_SIZE_MS = 1000
MIN_PACKETS_PER_WINDOW = 1

def _safe_float(val: float, default: float=0.0, min_val: float=-100000.0, max_val: float=100000.0) -> float:
    try:
        f_val = float(val)
        if not np.isfinite(f_val):
            return float(default)
        return float(max(min_val, min(max_val, f_val)))
    except Exception:
        return float(default)

def compute_window_features(group: pd.DataFrame) -> dict:
    if group is None or group.empty or 'rssi' not in group:
        return {'packet_count': 0, 'scan_duration_ms': 0.0, 'rssi_mean': -70.0, 'rssi_median': -70.0, 'rssi_min': -70.0, 'rssi_max': -70.0, 'rssi_std': 0.0, 'rssi_variance': 0.0, 'rssi_range': 0.0, 'rssi_p05': -70.0, 'rssi_p10': -70.0, 'rssi_p25': -70.0, 'rssi_p75': -70.0, 'rssi_p90': -70.0, 'rssi_p95': -70.0, 'rssi_iqr': 0.0, 'rssi_p90_10_range': 0.0, 'rssi_mad': 0.0, 'rssi_snr': 0.0, 'rssi_skewness': 0.0, 'rssi_kurtosis': 0.0, 'rssi_delta_mean': 0.0, 'rssi_delta_std': 0.0, 'rssi_delta_max': 0.0, 'observed_adv_interval': 0.0, 'adv_interval_std': 0.0, 'path_loss_free_space': 3.16, 'path_loss_indoor': 2.15, 'rssi_mean_to_std_ratio': -70.0, 'rssi_median_mean_diff': 0.0, 'rssi_slope': 0.0, 'rssi_trend_strength': 0.0, 'rssi_ema_diff': 0.0, 'rssi_first_half_mean': -70.0, 'rssi_second_half_mean': -70.0, 'rssi_half_diff': 0.0, 'rssi_autocorrelation': 0.0, 'rssi_energy': 4900.0}
    try:
        valid_df = group[['rssi', 'timestamp']].dropna()
        rssi_raw = pd.to_numeric(valid_df['rssi'], errors='coerce').fillna(-70.0).values.astype(float)
        ts_raw = pd.to_numeric(valid_df['timestamp'], errors='coerce').fillna(0.0).values.astype(float)
    except Exception:
        rssi_raw = np.array([-70.0])
        ts_raw = np.array([0.0])
    if len(rssi_raw) == 0:
        rssi_raw = np.array([-70.0])
    if len(ts_raw) == 0:
        ts_raw = np.array([0.0])
    rssi_values = np.nan_to_num(rssi_raw, nan=-70.0, posinf=0.0, neginf=-120.0)
    timestamps = np.nan_to_num(ts_raw, nan=0.0, posinf=1000000000000.0, neginf=0.0)
    packet_count = len(rssi_values)
    scan_duration_ms = float(timestamps[-1] - timestamps[0]) if packet_count > 1 else 0.0
    scan_duration_ms = max(0.0, scan_duration_ms)
    rssi_mean = float(np.mean(rssi_values))
    rssi_median = float(np.median(rssi_values))
    rssi_min = float(np.min(rssi_values))
    rssi_max = float(np.max(rssi_values))
    rssi_std = float(np.std(rssi_values, ddof=1)) if packet_count > 1 else 0.0
    rssi_var = float(np.var(rssi_values, ddof=1)) if packet_count > 1 else 0.0
    rssi_p05 = float(np.percentile(rssi_values, 5))
    rssi_p10 = float(np.percentile(rssi_values, 10))
    rssi_p25 = float(np.percentile(rssi_values, 25))
    rssi_p75 = float(np.percentile(rssi_values, 75))
    rssi_p90 = float(np.percentile(rssi_values, 90))
    rssi_p95 = float(np.percentile(rssi_values, 95))
    rssi_range = rssi_max - rssi_min
    rssi_iqr = rssi_p75 - rssi_p25
    rssi_p90_10_range = rssi_p90 - rssi_p10
    rssi_mad = float(np.median(np.abs(rssi_values - rssi_median)))
    rssi_snr = abs(rssi_mean) / (rssi_std + 1e-05)
    if packet_count > 2 and rssi_std > 1e-05:
        try:
            rssi_skew = float(stats.skew(rssi_values))
            rssi_kurt = float(stats.kurtosis(rssi_values))
        except Exception:
            rssi_skew = 0.0
            rssi_kurt = 0.0
    else:
        rssi_skew = 0.0
        rssi_kurt = 0.0
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
    n_free_space = 2.0
    n_indoor_obs = 3.0
    tx_power_1m = -77.8
    exp_fs = (tx_power_1m - rssi_mean) / (10.0 * n_free_space)
    exp_in = (tx_power_1m - rssi_mean) / (10.0 * n_indoor_obs)
    path_loss_free_space = 10.0 ** max(-2.0, min(3.0, exp_fs))
    path_loss_indoor = 10.0 ** max(-2.0, min(3.0, exp_in))
    path_loss_free_space = min(25.0, max(0.1, path_loss_free_space))
    path_loss_indoor = min(25.0, max(0.1, path_loss_indoor))
    rssi_mean_to_std_ratio = rssi_mean / (rssi_std + 1.0)
    rssi_median_mean_diff = rssi_median - rssi_mean
    if packet_count > 2 and len(timestamps) == len(rssi_values):
        try:
            t_norm = timestamps - timestamps[0]
            t_range = t_norm[-1] - t_norm[0]
            if t_range > 0:
                t_scaled = t_norm / t_range
                coeffs = np.polyfit(t_scaled, rssi_values, 1)
                rssi_slope = float(coeffs[0])
                rssi_fit = np.polyval(coeffs, t_scaled)
                ss_res = np.sum((rssi_values - rssi_fit) ** 2)
                ss_tot = np.sum((rssi_values - rssi_mean) ** 2)
                rssi_trend_strength = float(1.0 - ss_res / (ss_tot + 1e-10))
            else:
                rssi_slope = 0.0
                rssi_trend_strength = 0.0
        except Exception:
            rssi_slope = 0.0
            rssi_trend_strength = 0.0
    else:
        rssi_slope = 0.0
        rssi_trend_strength = 0.0
    if packet_count > 1:
        try:
            alpha = 2.0 / (packet_count + 1)
            ema = rssi_values[0]
            for val in rssi_values[1:]:
                ema = alpha * val + (1 - alpha) * ema
            rssi_ema_diff = float(ema - rssi_mean)
        except Exception:
            rssi_ema_diff = 0.0
    else:
        rssi_ema_diff = 0.0
    mid_idx = packet_count // 2
    if mid_idx > 0:
        rssi_first_half_mean = float(np.mean(rssi_values[:mid_idx]))
        rssi_second_half_mean = float(np.mean(rssi_values[mid_idx:]))
        rssi_half_diff = rssi_second_half_mean - rssi_first_half_mean
    else:
        rssi_first_half_mean = rssi_mean
        rssi_second_half_mean = rssi_mean
        rssi_half_diff = 0.0
    if packet_count > 2 and rssi_std > 1e-05:
        try:
            rssi_centered = rssi_values - rssi_mean
            with np.errstate(divide='ignore', invalid='ignore'):
                autocorr = np.corrcoef(rssi_centered[:-1], rssi_centered[1:])[0, 1]
            rssi_autocorrelation = float(autocorr) if np.isfinite(autocorr) else 0.0
        except Exception:
            rssi_autocorrelation = 0.0
    else:
        rssi_autocorrelation = 0.0
    try:
        rssi_energy = float(np.sum(rssi_values ** 2)) / max(1, packet_count)
    except Exception:
        rssi_energy = rssi_mean ** 2
    packet_rate = float(packet_count) / (float(scan_duration_ms) / 1000.0) if scan_duration_ms > 0 else 0.0
    rssi_bin_neg100_90 = float(np.mean((rssi_values >= -100) & (rssi_values < -90)))
    rssi_bin_neg90_80 = float(np.mean((rssi_values >= -90) & (rssi_values < -80)))
    rssi_bin_neg80_70 = float(np.mean((rssi_values >= -80) & (rssi_values < -70)))
    rssi_bin_neg70_60 = float(np.mean((rssi_values >= -70) & (rssi_values < -60)))
    rssi_bin_neg60_50 = float(np.mean((rssi_values >= -60) & (rssi_values < -50)))
    rssi_bin_neg50_30 = float(np.mean(rssi_values >= -50))
    features_raw = {'packet_count': packet_count, 'packet_rate': packet_rate, 'scan_duration_ms': scan_duration_ms, 'rssi_mean': rssi_mean, 'rssi_median': rssi_median, 'rssi_min': rssi_min, 'rssi_max': rssi_max, 'rssi_std': rssi_std, 'rssi_variance': rssi_var, 'rssi_range': rssi_range, 'rssi_p05': rssi_p05, 'rssi_p10': rssi_p10, 'rssi_p25': rssi_p25, 'rssi_p75': rssi_p75, 'rssi_p90': rssi_p90, 'rssi_p95': rssi_p95, 'rssi_iqr': rssi_iqr, 'rssi_p90_10_range': rssi_p90_10_range, 'rssi_mad': rssi_mad, 'rssi_snr': rssi_snr, 'rssi_skewness': rssi_skew, 'rssi_kurtosis': rssi_kurt, 'rssi_delta_mean': rssi_delta_mean, 'rssi_delta_std': rssi_delta_std, 'rssi_delta_max': rssi_delta_max, 'observed_adv_interval': observed_adv_interval, 'adv_interval_std': adv_interval_std, 'path_loss_free_space': path_loss_free_space, 'path_loss_indoor': path_loss_indoor, 'rssi_mean_to_std_ratio': rssi_mean_to_std_ratio, 'rssi_median_mean_diff': rssi_median_mean_diff, 'rssi_slope': rssi_slope, 'rssi_trend_strength': rssi_trend_strength, 'rssi_ema_diff': rssi_ema_diff, 'rssi_first_half_mean': rssi_first_half_mean, 'rssi_second_half_mean': rssi_second_half_mean, 'rssi_half_diff': rssi_half_diff, 'rssi_autocorrelation': rssi_autocorrelation, 'rssi_energy': rssi_energy, 'rssi_bin_neg100_90': rssi_bin_neg100_90, 'rssi_bin_neg90_80': rssi_bin_neg90_80, 'rssi_bin_neg80_70': rssi_bin_neg80_70, 'rssi_bin_neg70_60': rssi_bin_neg70_60, 'rssi_bin_neg60_50': rssi_bin_neg60_50, 'rssi_bin_neg50_30': rssi_bin_neg50_30}
    features_clean = {}
    for k, v in features_raw.items():
        if k == 'packet_count':
            features_clean[k] = int(v)
        else:
            features_clean[k] = round(_safe_float(v), 4)
    return features_clean

def compute_cross_window_features(window_df: pd.DataFrame) -> pd.DataFrame:
    if window_df is None or window_df.empty or 'rssi_mean' not in window_df.columns:
        return window_df
    df = window_df.copy()
    n = len(df)
    rssi_means = df['rssi_mean'].values.astype(float)
    window_starts = df['window_start'].values.astype(float) if 'window_start' in df.columns else np.arange(n) * 1000.0
    rssi_mean_delta = np.zeros(n)
    rssi_mean_delta[1:] = np.diff(rssi_means)
    df['rssi_mean_delta'] = np.round(rssi_mean_delta, 4)
    for window_size, col_name in [(3, 'rssi_mean_slope_3w'), (5, 'rssi_mean_slope_5w')]:
        slopes = np.zeros(n)
        for i in range(n):
            start_idx = max(0, i - window_size + 1)
            segment = rssi_means[start_idx:i + 1]
            if len(segment) >= 2:
                try:
                    x = np.arange(len(segment), dtype=float)
                    coeffs = np.polyfit(x, segment, 1)
                    slopes[i] = coeffs[0]
                except Exception:
                    slopes[i] = 0.0
            else:
                slopes[i] = 0.0
        df[col_name] = np.round(slopes, 4)
    df['rssi_rolling_mean_3w'] = df['rssi_mean'].rolling(window=3, min_periods=1).mean().round(4)
    df['rssi_rolling_std_3w'] = df['rssi_mean'].rolling(window=3, min_periods=1).std().fillna(0.0).round(4)
    df['rssi_rolling_mean_5w'] = df['rssi_mean'].rolling(window=5, min_periods=1).mean().round(4)
    df['rssi_rolling_std_5w'] = df['rssi_mean'].rolling(window=5, min_periods=1).std().fillna(0.0).round(4)
    alpha = 0.3
    ema_vals = np.zeros(n)
    ema_vals[0] = rssi_means[0]
    for i in range(1, n):
        ema_vals[i] = alpha * rssi_means[i] + (1 - alpha) * ema_vals[i - 1]
    df['rssi_ema_cross_window'] = np.round(ema_vals, 4)
    velocities = np.zeros(n)
    for i in range(1, n):
        dt = (window_starts[i] - window_starts[i - 1]) / 1000.0
        if dt > 0:
            velocities[i] = rssi_mean_delta[i] / dt
        else:
            velocities[i] = 0.0
    df['rssi_velocity'] = np.round(velocities, 4)
    accelerations = np.zeros(n)
    accelerations[1:] = np.diff(velocities)
    df['rssi_acceleration'] = np.round(accelerations, 4)
    stability = np.zeros(n)
    for i in range(n):
        start_idx = max(0, i - 4)
        deltas_window = np.abs(rssi_mean_delta[start_idx:i + 1])
        if len(deltas_window) > 0:
            stability[i] = float(np.sum(deltas_window < 2.0)) / len(deltas_window)
        else:
            stability[i] = 1.0
    df['signal_stability_index'] = np.round(stability, 4)
    df['rssi_rolling_mean_10w'] = df['rssi_mean'].rolling(window=10, min_periods=1).mean().round(4)
    df['rssi_rolling_std_10w'] = df['rssi_mean'].rolling(window=10, min_periods=1).std().fillna(0.0).round(4)
    slopes_5w = df['rssi_mean_slope_5w'].values
    motion_dir = np.zeros(n)
    for i in range(n):
        if slopes_5w[i] > 0.3:
            motion_dir[i] = 1.0
        elif slopes_5w[i] < -0.3:
            motion_dir[i] = -1.0
        else:
            motion_dir[i] = 0.0
    df['rssi_motion_direction'] = motion_dir
    if 'rssi_snr' in df.columns:
        df['rssi_snr_rolling_5w'] = df['rssi_snr'].rolling(window=5, min_periods=1).mean().round(4)
    else:
        df['rssi_snr_rolling_5w'] = 0.0
    cross_window_cols = ['rssi_mean_delta', 'rssi_mean_slope_3w', 'rssi_mean_slope_5w', 'rssi_rolling_mean_3w', 'rssi_rolling_std_3w', 'rssi_rolling_mean_5w', 'rssi_rolling_std_5w', 'rssi_ema_cross_window', 'rssi_velocity', 'rssi_acceleration', 'signal_stability_index', 'rssi_rolling_mean_10w', 'rssi_rolling_std_10w', 'rssi_motion_direction', 'rssi_snr_rolling_5w']
    for col in cross_window_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
            df[col] = df[col].replace([np.inf, -np.inf], 0.0)
    return df
CANONICAL_PRESETS = np.array([0.5, 0.6, 0.7, 1.0, 1.1, 1.5, 1.9, 2.0, 3.0, 3.4, 4.3, 4.5, 4.6, 5.0, 5.3])

def normalize_distance_preset(val: float) -> float:
    try:
        f_val = float(val)
        if not np.isfinite(f_val):
            return 0.0
        idx = np.argmin(np.abs(CANONICAL_PRESETS - f_val))
        if abs(CANONICAL_PRESETS[idx] - f_val) <= 0.15:
            return float(CANONICAL_PRESETS[idx])
        return float(round(f_val, 1))
    except Exception:
        return 0.0

def compute_environmental_interactions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'obstacle_factor' not in df.columns:
        obstacle_factors = []
        for idx, row in df.iterrows():
            obs = str(row.get('obstacle', 'No')).strip().capitalize()
            obs_type = str(row.get('obstacle_type', 'None')).strip().title()
            if obs in ('No', 'False', '0') or obs_type in ('None', 'Nan', '', 'N/A'):
                factor = 1.0
            elif obs_type in ('Cardboard', 'Tape', 'Wood', 'Glass'):
                factor = 1.3
            elif obs_type in ('Human', 'Body', 'Furniture', 'Partition'):
                factor = 1.7
            elif obs_type in ('Metal', 'Wall', 'Concrete', 'Steel'):
                factor = 2.2
            else:
                factor = 1.5
            obstacle_factors.append(factor)
        df['obstacle_factor'] = np.round(obstacle_factors, 2)
    if 'rssi_mean' in df.columns and 'height_m' in df.columns and ('rssi_x_height' not in df.columns):
        df['rssi_x_height'] = np.round(df['rssi_mean'] * df['height_m'].fillna(0.0), 4)
    if 'path_loss_indoor' in df.columns and 'obstacle_factor' in df.columns and ('pathloss_div_obstacle_factor' not in df.columns):
        obs_safe = df['obstacle_factor'].replace(0.0, 1.0)
        df['pathloss_div_obstacle_factor'] = np.round(df['path_loss_indoor'] / obs_safe, 4)
    if 'path_loss_free_space' in df.columns and 'obstacle_factor' in df.columns and ('pathloss_free_div_obstacle_factor' not in df.columns):
        obs_safe = df['obstacle_factor'].replace(0.0, 1.0)
        df['pathloss_free_div_obstacle_factor'] = np.round(df['path_loss_free_space'] / obs_safe, 4)
    if 'rssi_mean' in df.columns and 'height_m' in df.columns and ('rssi_div_height' not in df.columns):
        df['rssi_div_height'] = np.round(df['rssi_mean'] / (df['height_m'].fillna(0.0) + 1.0), 4)
    return df

def normalize_and_clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'distance_m' in df.columns:
        df['distance_m'] = pd.to_numeric(df['distance_m'], errors='coerce').apply(normalize_distance_preset)
        df['distance_bucket'] = df['distance_m']
    if 'anchor_id' in df.columns:
        df['anchor_id'] = df['anchor_id'].astype(str).str.strip().str.upper()
    if 'obstacle' in df.columns:
        df['obstacle'] = df['obstacle'].astype(str).str.strip().str.capitalize()
    if 'obstacle_type' in df.columns:
        df['obstacle_type'] = df['obstacle_type'].astype(str).str.strip().str.title()
        df['obstacle_type'] = df['obstacle_type'].replace({'Nan': 'None', 'None': 'None', '': 'None', 'N/A': 'None'})
    if 'motion' in df.columns:
        df['motion'] = df['motion'].astype(str).str.strip().str.lower()
        df['motion'] = df['motion'].replace({'nan': 'stationary', '': 'stationary'})
    df = compute_environmental_interactions(df)
    dedup_cols = [c for c in ['window_start', 'anchor_id'] if c in df.columns]
    if len(dedup_cols) == 2:
        before_count = len(df)
        df.drop_duplicates(subset=dedup_cols, keep='first', inplace=True)
        after_count = len(df)
        if before_count > after_count:
            logger.info(f'Deduplication: removed {before_count - after_count} duplicate window records.')
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        df[col] = df[col].fillna(0.0)
        df[col] = df[col].replace([np.inf, -np.inf], 0.0)
    return df

def process_raw_csv(filepath: str, target_mac: str=None, drop_duplicates: bool=False) -> pd.DataFrame:
    if not os.path.exists(filepath):
        logger.warning(f'File not found: {filepath}')
        return pd.DataFrame()
    if os.path.getsize(filepath) == 0:
        logger.info(f'Skipping empty CSV file (0 bytes): {os.path.basename(filepath)}')
        return pd.DataFrame()
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        logger.error(f'Failed to parse CSV file {filepath}: {e}')
        return pd.DataFrame()
    required_cols = {'timestamp', 'anchor', 'mac', 'rssi', 'distance_m'}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        logger.warning(f'Missing required columns in {filepath}: {missing}')
        return pd.DataFrame()
    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    df['rssi'] = pd.to_numeric(df['rssi'], errors='coerce')
    df['distance_m'] = pd.to_numeric(df['distance_m'], errors='coerce')
    df.dropna(subset=['timestamp', 'rssi', 'distance_m'], inplace=True)
    if df.empty:
        return pd.DataFrame()
    if drop_duplicates and 'duplicate_candidate' in df.columns:
        df = df[~df['duplicate_candidate'].astype(str).str.lower().isin(['true', '1'])]
    if target_mac:
        df = df[df['mac'].astype(str).str.strip().str.upper() == target_mac.strip().upper()].copy()
        if df.empty:
            print(f'  [!] No packets for MAC {target_mac} in {os.path.basename(filepath)}')
            return pd.DataFrame()
    df.sort_values('timestamp', inplace=True)
    t_min = df['timestamp'].min()
    df['window_id'] = ((df['timestamp'] - t_min) // WINDOW_SIZE_MS).astype(int)
    has_motion = 'motion' in df.columns
    rows = []
    for (anchor, window_id), group in df.groupby(['anchor', 'window_id']):
        if len(group) < MIN_PACKETS_PER_WINDOW:
            continue
        features = compute_window_features(group)
        first = group.iloc[0]
        features['window_start'] = int(t_min + window_id * WINDOW_SIZE_MS)
        features['anchor_id'] = str(anchor).strip().upper()
        features['distance_m'] = normalize_distance_preset(first['distance_m'])
        features['height_m'] = round(float(first.get('height_m', 0.0)), 2)
        features['obstacle'] = str(first.get('obstacle', 'No')).strip().capitalize()
        features['obstacle_type'] = str(first.get('obstacle_type', 'None')).strip().title()
        if has_motion:
            motion_val = str(first.get('motion', 'stationary')).strip().lower()
            features['motion'] = motion_val if motion_val in ('stationary', 'approaching', 'moving_away') else 'stationary'
        else:
            features['motion'] = 'stationary'
        rows.append(features)
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    result['session_id'] = os.path.basename(filepath)
    if len(result) > 1:
        result.sort_values(['session_id', 'anchor_id', 'window_start'], inplace=True)
        cross_window_dfs = []
        for (session_id, anchor_id), group in result.groupby(['session_id', 'anchor_id']):
            group_with_cross = compute_cross_window_features(group)
            cross_window_dfs.append(group_with_cross)
        result = pd.concat(cross_window_dfs, ignore_index=True)
    else:
        result = compute_cross_window_features(result)
    result = compute_environmental_interactions(result)
    meta_cols = ['window_start', 'anchor_id', 'session_id', 'distance_m', 'distance_bucket', 'height_m', 'obstacle', 'obstacle_type', 'motion']
    feat_cols = [c for c in result.columns if c not in meta_cols]
    col_order = ['window_start', 'anchor_id', 'session_id'] + feat_cols + ['distance_m', 'distance_bucket', 'height_m', 'obstacle', 'obstacle_type', 'motion']
    col_order = [c for c in col_order if c in result.columns]
    return result[col_order]

def print_dataset_audit_report(merged: pd.DataFrame):
    meta_cols = ['window_start', 'anchor_id', 'session_id', 'distance_m', 'distance_bucket', 'height_m', 'obstacle', 'obstacle_type', 'motion']
    feat_cols = [c for c in merged.columns if c not in meta_cols]
    total_windows = len(merged)
    print('\n' + '=' * 75)
    print('  [DATASET QUALITY AUDIT & MODEL READINESS REPORT]')
    print('=' * 75)
    print(f'  Total Observation Windows : {total_windows:,}')
    print(f'  Extracted Feature Count   : {len(feat_cols)}')
    print(f"  Unique Recording Sessions : {(merged['session_id'].nunique() if 'session_id' in merged.columns else 1)}")
    print(f"  Unique Anchor Nodes       : {(sorted(merged['anchor_id'].unique().tolist()) if 'anchor_id' in merged.columns else 'N/A')}")
    print('\n  [1. Distance Presets Coverage & Class Balance]')
    target_presets = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    dist_col = 'distance_bucket' if 'distance_bucket' in merged.columns else 'distance_m'
    actual_counts = merged[dist_col].value_counts()
    max_cnt = max(actual_counts.max(), 1)
    min_cnt = actual_counts.min()
    for d in sorted(merged[dist_col].unique()):
        cnt = actual_counts.get(d, 0)
        bar_len = int(cnt / max_cnt * 25)
        bar = '#' * bar_len
        pct = cnt / total_windows * 100
        dist_df = merged[merged[dist_col] == d]
        rssi_m = dist_df['rssi_mean'].mean() if 'rssi_mean' in dist_df.columns else 0.0
        rssi_s = dist_df['rssi_mean'].std() if 'rssi_mean' in dist_df.columns else 0.0
        status = '[GOOD]' if cnt >= 1000 else '[LOW SAMPLES]'
        print(f'     {d:>4.1f}m | {bar:<25} | {cnt:>5,} windows ({pct:>5.1f}%) | RSSI: {rssi_m:>6.1f}±{rssi_s:<4.1f} {status}')
    missing_presets = [p for p in target_presets if p not in merged['distance_m'].unique()]
    if missing_presets:
        print(f'     [!] WARNING: Missing target distance presets: {missing_presets}')
    imbalance_ratio = max_cnt / max(min_cnt, 1)
    if imbalance_ratio > 3.0:
        print(f'     [!] WARNING: Class Imbalance Detected! Ratio: {imbalance_ratio:.1f}x (Max: {max_cnt}, Min: {min_cnt})')
    if 'anchor_id' in merged.columns:
        print('\n  [2. Anchor Node Distribution & Balance]')
        anc_counts = merged['anchor_id'].value_counts()
        for anc, cnt in anc_counts.items():
            pct = cnt / total_windows * 100
            print(f"     - Anchor '{anc:<15}' : {cnt:>6,} windows ({pct:>5.1f}%)")
    if 'obstacle' in merged.columns:
        print('\n  [3. Obstacle & Environmental Coverage]')
        obs_counts = merged['obstacle'].value_counts()
        for obs, cnt in obs_counts.items():
            pct = cnt / total_windows * 100
            print(f"     - Obstacle '{obs:<15}' : {cnt:>6,} windows ({pct:>5.1f}%)")
    if 'motion' in merged.columns:
        print('\n  [4. Motion Mode Distribution]')
        m_counts = merged['motion'].value_counts()
        for m, cnt in m_counts.items():
            pct = cnt / total_windows * 100
            print(f"     - Motion '{m:<15}' : {cnt:>6,} windows ({pct:>5.1f}%)")
    print('\n  [5. Model Readiness Verdict]')
    if total_windows >= 5000 and imbalance_ratio <= 4.0:
        print('     [VERDICT] EXCELLENT: Dataset is fully balanced, diverse, and ready for ML model training!')
    elif total_windows >= 2000:
        print('     [VERDICT] MODERATE: Dataset is sufficient for training, but additional samples for underrepresented presets will improve MAE.')
    else:
        print('     [VERDICT] CRITICAL: Dataset is small. Collect additional BLE recording sessions before training.')
    print('=' * 75 + '\n')

def process_all_raw_csvs(raw_dir: str, output_path: str, target_mac: str=None, drop_duplicates: bool=False, progress_callback=None) -> pd.DataFrame:
    if not os.path.exists(raw_dir):
        raise FileNotFoundError(f'Raw CSV directory not found: {raw_dir}')
    csv_files = sorted(glob.glob(os.path.join(raw_dir, 'dataset_*.csv')))
    if not csv_files:
        raise FileNotFoundError(f"No raw CSV files matching 'dataset_*.csv' found in {raw_dir}")
    print(f'[AUDIT] Scanning {len(csv_files)} raw CSV file(s) in {raw_dir}')
    if target_mac:
        print(f'[FILTER] Target MAC lock: {target_mac}')
    all_windows = []
    total = len(csv_files)
    for index, fpath in enumerate(csv_files):
        fname = os.path.basename(fpath)
        if progress_callback:
            pct = 5 + int(index / total * 30)
            progress_callback(f'Processing CSV {index + 1}/{total}: {fname}', pct)
        try:
            df = process_raw_csv(fpath, target_mac=target_mac, drop_duplicates=drop_duplicates)
            if df.empty:
                print(f'  [SKIP] {fname} -> 0 windows (skipped)')
            else:
                df['session_id'] = fname
                meta_cols_list = ['window_start', 'anchor_id', 'session_id', 'distance_m', 'height_m', 'obstacle', 'obstacle_type', 'motion']
                n_features = len([c for c in df.columns if c not in meta_cols_list])
                print(f'  [OK] {fname} -> {len(df)} observation windows ({n_features} features)')
                all_windows.append(df)
        except Exception as e:
            print(f'  [ERROR] Failed processing {fname}: {e}')
    if not all_windows:
        raise ValueError('No valid observation windows were generated from any CSV file.')
    merged = pd.concat(all_windows, ignore_index=True)
    merged = normalize_and_clean_dataframe(merged)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged.to_csv(output_path, index=False)
    print_dataset_audit_report(merged)
    return merged

def main():
    parser = argparse.ArgumentParser(description='BLE Feature Engineering Pipeline (V2 — up to 50 features)')
    parser.add_argument('--raw-dir', type=str, required=True)
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--target-mac', type=str, default=None)
    args = parser.parse_args()
    if args.output is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.output = os.path.join(project_root, 'datasets', 'observations.csv')
    process_all_raw_csvs(args.raw_dir, args.output, target_mac=args.target_mac)
if __name__ == '__main__':
    main()
