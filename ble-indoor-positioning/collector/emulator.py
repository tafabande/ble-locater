import argparse
import json
import math
import random
import sys
import time

def generate_rssi(mean: float, noise: float) -> int:
    val = round(random.normalvariate(mean, noise))
    return max(-100, min(-30, val))

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
    parser = argparse.ArgumentParser(description='ESP32 BLE Anchor Node - Hardware Emulator')
    parser.add_argument('--mode', '-m', type=str, choices=['NORMAL', 'RAW', 'DUAL'], default='NORMAL', help='Operation mode of the emulated ESP32 (default: NORMAL)')
    parser.add_argument('--mac', type=str, default='52:06:26:03:01:DA', help='MAC address of the simulated tag')
    parser.add_argument('--anchor', '-a', type=str, default='A1', help='ID of the simulated anchor')
    parser.add_argument('--interval', '-i', type=float, default=100.0, help='Simulated advertising interval of the tag in milliseconds (default: 100.0)')
    parser.add_argument('--duration', '-d', type=float, default=None, help='Run for N seconds, then exit. If not set, runs indefinitely.')
    parser.add_argument('--noise', type=float, default=2.0, help='Standard deviation of RSSI noise (default: 2.0)')
    parser.add_argument('--mean', type=float, default=-60.0, help='Mean RSSI value (default: -60.0)')
    args = parser.parse_args()
    print(f'--- ESP32 Emulated Console (Anchor: {args.anchor}, Mode: {args.mode}) ---', file=sys.stderr)
    print(f'Simulating tag {args.mac} with mean RSSI={args.mean}dBm, interval={args.interval}ms', file=sys.stderr)
    print('Press Ctrl+C to terminate.', file=sys.stderr)
    start_time = time.time()
    boot_time_ms = int(time.time() * 1000)
    packet_buffer = []
    last_advertisement_time = time.time()
    last_window_time = time.time()
    window_counter = 0
    current_mean_rssi = args.mean
    try:
        while True:
            now = time.time()
            if args.duration and now - start_time >= args.duration:
                print('[Emulator] Duration limit reached. Exiting.', file=sys.stderr)
                break
            current_mean_rssi += random.uniform(-0.1, 0.1)
            current_mean_rssi = max(-90.0, min(-40.0, current_mean_rssi))
            jitter = random.uniform(-5.0, 5.0)
            if (now - last_advertisement_time) * 1000 >= args.interval + jitter:
                last_advertisement_time = now
                if random.random() > 0.05:
                    rssi = generate_rssi(current_mean_rssi, args.noise)
                    pkt_time_ms = int(now * 1000) - boot_time_ms
                    pkt = {'timestamp': pkt_time_ms, 'rssi': rssi}
                    packet_buffer.append(pkt)
                    if args.mode in ['RAW', 'DUAL']:
                        raw_out = {'type': 'raw', 'timestamp': pkt_time_ms, 'mac': args.mac, 'rssi': rssi}
                        print(json.dumps(raw_out))
                        sys.stdout.flush()
            if now - last_window_time >= 1.0:
                window_start_ms = int(last_window_time * 1000) - boot_time_ms
                if args.mode in ['NORMAL', 'DUAL'] and packet_buffer:
                    window_counter += 1
                    obs = calculate_stats(packet_buffer, args.anchor, args.mac, window_start_ms)
                    if obs:
                        print(json.dumps(obs))
                        print(f'\nWindow {window_counter}', file=sys.stderr)
                        print(f"Packets {obs['packet_count']}", file=sys.stderr)
                        print(f"Mean {obs['rssi_mean']:.2f}", file=sys.stderr)
                        print(f"Variance {obs['rssi_variance']:.2f}", file=sys.stderr)
                        print('Output Success\n', file=sys.stderr)
                        sys.stdout.flush()
                packet_buffer.clear()
                last_window_time = now
            time.sleep(0.005)
    except KeyboardInterrupt:
        print('\n[Emulator] Terminated by user.', file=sys.stderr)
if __name__ == '__main__':
    main()
