#!/usr/bin/env python3
"""
Simulated Demo for BLE Indoor Positioning
=========================================
Generates a virtual BLE tag moving in a figure-8 path and transmits
realistic RSSI measurements directly to the FastAPI backend.
"""

import time
import math
import random
import requests
import argparse
import sys

URL = "http://127.0.0.1:8000/api/observation"

# Based on DEFAULT_ANCHORS_CONFIG in server/app.py
ANCHORS = {
    "ANCHOR_01": (0.0, 0.0),
    "ANCHOR_02": (5.0, 0.0),
    "ANCHOR_03": (2.5, 4.33),
}
MAC = "52:06:26:03:01:DA"

def distance_to_rssi(d):
    """Path loss model: RSSI = TxPower - 10 * n * log10(d) + noise"""
    if d < 0.1:
        d = 0.1
    # Assuming TxPower=-55 dBm at 1m, Path Loss Exponent (n)=2.0
    rssi = -55.0 - 10 * 2.0 * math.log10(d)
    noise = random.normalvariate(0, 1.5)  # 1.5 dB standard deviation
    return max(-100, min(-30, int(rssi + noise)))

def main():
    parser = argparse.ArgumentParser(description="Simulate a moving BLE tag.")
    parser.add_argument("--speed", type=float, default=1.0, help="Movement speed multiplier")
    args = parser.parse_args()

    print("--- Simulated Demo Started ---")
    print("Simulating a BLE tag moving in a figure-8 path...")
    print("Press Ctrl+C to terminate.")

    # Center of the default triangle layout
    cx, cy = 2.5, 1.5
    
    t = 0.0
    
    try:
        while True:
            # Figure-8 Parametric Equations
            # x(t) = a * sin(t), y(t) = b * sin(t)*cos(t)
            angle = (t * args.speed / 10.0) * 2 * math.pi
            x = cx + 2.0 * math.sin(angle)
            y = cy + 2.0 * math.sin(angle) * math.cos(angle)
            
            timestamp = int(time.time() * 1000)
            
            success = 0
            for anchor_id, (ax, ay) in ANCHORS.items():
                dist = math.sqrt((x - ax)**2 + (y - ay)**2)
                rssi = distance_to_rssi(dist)
                
                # 5% chance to drop a packet simulating real world interference
                if random.random() > 0.05:
                    payload = {
                        "timestamp": timestamp,
                        "anchor": anchor_id,
                        "mac": MAC,
                        "rssi": rssi,
                        "name": "SIMULATED_TAG"
                    }
                    try:
                        requests.post(URL, json=payload, timeout=0.5)
                        success += 1
                    except requests.exceptions.RequestException:
                        pass # Ignore connection errors if server is down

            if success > 0:
                print(f"[SIMULATOR] Tag @ ({x:.2f}, {y:.2f}) - Sent {success}/3 anchor observations", flush=True)
            else:
                print(f"[SIMULATOR] Tag @ ({x:.2f}, {y:.2f}) - Failed to reach server", flush=True)
            
            # Send at roughly 10Hz
            time.sleep(0.1)
            t += 0.1

    except KeyboardInterrupt:
        print("\n[SIMULATOR] Terminated by user.")

if __name__ == "__main__":
    main()
