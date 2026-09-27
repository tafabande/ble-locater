import argparse
import json
import math
import random
import sys
import time

def calculate_stats(packets: list[dict], anchor_id: str, mac: str, window_start_time_ms: int) -> dict:
    count = len(packets)
    if count == 0:
        return {}
    rssis = [p['rssi'] for p in packets]
    rssi_mean = sum(rssis) / count
    rssi_variance = sum(((r - rssi_mean) ** 2 for r in rssis)) / count
    rssi_std = math.sqrt(rssi_variance)
    rssi_min = min(rssis)
    rssi_max = max(rssis)
    rssi_range = rssi_max - rssi_min
    sorted_rssis = sorted(rssis)
    if count % 2 == 1:
        rssi_median = sorted_rssis[count // 2]
    else:
        rssi_median = (sorted_rssis[count // 2 - 1] + sorted_rssis[count // 2]) / 2.0
    rssi_mode = max(set(sorted_rssis), key=sorted_rssis.count)

    def get_percentile(p):
        idx = p * (count - 1)
        low = int(math.floor(idx))
        high = int(math.ceil(idx))
        if low == high:
            return sorted_rssis[low]
        return sorted_rssis[low] + (idx - low) * (sorted_rssis[high] - sorted_rssis[low])
    percentile_25 = get_percentile(0.25)
    percentile_75 = get_percentile(0.75)
    if rssi_std > 0.0001:
        normalized_diffs = [(r - rssi_mean) / rssi_std for r in rssis]
        skewness = sum((d ** 3 for d in normalized_diffs)) / count
        kurtosis = sum((d ** 4 for d in normalized_diffs)) / count
    else:
        skewness = 0.0
        kurtosis = 0.0
    rssi_delta_mean = 0.0
    advertising_interval_ms = 0.0
    max_consecutive_gap_ms = 1000
    lost_packets = 0
    if count > 1:
        rssi_delta_mean = sum((abs(rssis[i] - rssis[i - 1]) for i in range(1, count))) / (count - 1)
        time_span = packets[-1]['timestamp'] - packets[0]['timestamp']
        advertising_interval_ms = time_span / (count - 1)
        gaps = []
        for i in range(1, count):
            gap = packets[i]['timestamp'] - packets[i - 1]['timestamp']
            gaps.append(gap)
            expected_gaps = round(gap / 100.0)
            if expected_gaps > 1:
                lost_packets += expected_gaps - 1
        max_consecutive_gap_ms = max(gaps)
    packet_loss_estimate = lost_packets / (count + lost_packets) if count + lost_packets > 0 else 0.0
    return {'type': 'observation', 'anchor_id': anchor_id, 'timestamp': window_start_time_ms, 'device_mac': mac, 'packet_count': count, 'scan_duration_ms': 1000, 'rssi_mean': round(rssi_mean, 2), 'rssi_std': round(rssi_std, 2), 'rssi_variance': round(rssi_variance, 2), 'rssi_min': rssi_min, 'rssi_max': rssi_max, 'rssi_range': rssi_range, 'rssi_delta_mean': round(rssi_delta_mean, 2), 'advertising_interval_ms': round(advertising_interval_ms, 2), 'rssi_median': round(rssi_median, 2), 'rssi_mode': rssi_mode, 'skewness': round(skewness, 4), 'kurtosis': round(kurtosis, 4), 'percentile_25': round(percentile_25, 2), 'percentile_75': round(percentile_75, 2), 'packet_loss_estimate': round(packet_loss_estimate, 4), 'max_consecutive_gap_ms': max_consecutive_gap_ms}

def main() -> None:
    print("[HARDWARE DIRECTIVE] ESP32 Anchor hardware simulation has been completely removed.", file=sys.stderr)
    print("Physical ESP32 devices must be flashed with firmware in 'firmware/esp32_wifi_anchor/'", file=sys.stderr)
    print("and stream real radio measurements over UDP port 5005 or Serial UART.", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    main()
