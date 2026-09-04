import os
import time
import math
import random
import requests
import argparse
import sys

API_BASE = os.environ.get('API_URL', 'http://127.0.0.1:8000').rstrip('/')
URL_SINGLE = f'{API_BASE}/api/observation'
URL_BATCH = f'{API_BASE}/api/observation/batch'

# 12 Anchors across 4 Rooms (Room A: Executive Suite, Room B: Meeting Room, Room C: Operations Hub, Room D: Main Entrance)
ANCHORS = {
    'ANCHOR_01': (0.2, 5.2), 'ANCHOR_02': (4.8, 5.2), 'ANCHOR_03': (2.5, 9.8),  # Room A
    'ANCHOR_04': (5.2, 5.2), 'ANCHOR_05': (9.8, 5.2), 'ANCHOR_06': (7.5, 9.8),  # Room B
    'ANCHOR_07': (0.2, 0.2), 'ANCHOR_08': (4.8, 0.2), 'ANCHOR_09': (2.5, 4.8),  # Room C
    'ANCHOR_10': (5.2, 0.2), 'ANCHOR_11': (9.8, 0.2), 'ANCHOR_12': (7.5, 4.8)   # Room D
}

TAGS = [
    {'mac': '52:06:26:03:01:DA', 'name': 'SIMULATED_TAG', 'cx': 5.0, 'cy': 5.0, 'rx': 4.0, 'ry': 4.0, 'speed': 1.0},
    {'mac': 'EC:G1:00:00:00:01', 'name': 'Laser Scanner #01', 'cx': 2.5, 'cy': 7.5, 'rx': 1.8, 'ry': 1.8, 'speed': 0.8},
    {'mac': 'WC:HR:00:00:00:04', 'name': 'Utility Trolley #03', 'cx': 5.0, 'cy': 2.5, 'rx': 3.5, 'ry': 1.5, 'speed': 1.2},
    {'mac': 'ST:AF:00:00:00:09', 'name': 'Sarah Chen (Exec)', 'cx': 5.0, 'cy': 7.5, 'rx': 3.8, 'ry': 1.5, 'speed': 1.0},
    {'mac': 'PA:TN:00:00:00:11', 'name': 'Personnel Tag — Desk 1A', 'cx': 2.5, 'cy': 7.5, 'rx': 0.5, 'ry': 0.5, 'speed': 0.3},
    {'mac': 'CA:RT:00:00:00:08', 'name': 'Equipment Storage Cart', 'cx': 7.5, 'cy': 7.5, 'rx': 1.5, 'ry': 1.5, 'speed': 0.7},
]

def distance_to_rssi(d):
    if d < 0.1:
        d = 0.1
    rssi = -55.0 - 10 * 2.7 * math.log10(d)
    noise = random.normalvariate(0, 1.2)
    return max(-100, min(-30, int(rssi + noise)))

def main():
    parser = argparse.ArgumentParser(description='Simulate moving BLE asset tags.')
    parser.add_argument('--speed', type=float, default=1.0, help='Movement speed multiplier')
    args = parser.parse_args()

    print('--- Indoor BLE Tag Simulation Started ---')
    print('Simulating 6 live asset tags across Room A, B, C, D...')
    print('Press Ctrl+C to terminate.')

    t = 0.0
    try:
        while True:
            timestamp = int(time.time() * 1000)
            packets = []

            for tag_cfg in TAGS:
                mac = tag_cfg['mac']
                name = tag_cfg['name']
                speed = tag_cfg['speed'] * args.speed
                cx, cy = tag_cfg['cx'], tag_cfg['cy']
                rx, ry = tag_cfg['rx'], tag_cfg['ry']

                angle = t * speed * 0.1 * 2 * math.pi
                x = max(0.2, min(9.8, cx + rx * math.sin(angle)))
                y = max(0.2, min(9.8, cy + ry * math.sin(angle) * math.cos(angle)))

                for anchor_id, (ax, ay) in ANCHORS.items():
                    dist = math.sqrt((x - ax) ** 2 + (y - ay) ** 2)
                    if dist <= 8.5 and random.random() > 0.05:
                        rssi = distance_to_rssi(dist)
                        packets.append({
                            'timestamp': timestamp,
                            'anchor': anchor_id,
                            'mac': mac,
                            'rssi': rssi,
                            'name': name,
                            'true_x': round(x, 3),
                            'true_y': round(y, 3)
                        })

            if packets:
                try:
                    res = requests.post(URL_BATCH, json=packets, timeout=2.5)
                    if res.status_code != 200:
                        print(f'[SIMULATOR] Batch HTTP {res.status_code}', flush=True)
                except requests.exceptions.RequestException:
                    now_ts = time.time()
                    if not hasattr(main, '_last_wait_log') or (now_ts - main._last_wait_log > 5.0):
                        print(f'[SIMULATOR] Waiting for backend server at {API_BASE} ...', flush=True)
                        main._last_wait_log = now_ts

            time.sleep(0.2)
            t += 0.2
    except KeyboardInterrupt:
        print('\n[SIMULATOR] Terminated by user.')

if __name__ == '__main__':
    main()
