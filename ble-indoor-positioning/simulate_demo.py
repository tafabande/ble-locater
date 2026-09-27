"""Indoor BLE Tag Simulation — DECOMMISSIONED.

Physical Hardware Directive:
Simulation has been permanently removed from the system.
Real-time tracking is streamed exclusively from physical ESP32 anchor nodes
detecting real BLE beacon tags over local Wi-Fi UDP port 5005.
"""
import sys

def main():
    print("=" * 70, file=sys.stderr)
    print("❌ SIMULATION DECOMMISSIONED", file=sys.stderr)
    print("Synthetic motion and RSSI simulation has been permanently removed.", file=sys.stderr)
    print("All live tracking requires physical ESP32 anchor hardware transmitting", file=sys.stderr)
    print("real BLE advertising measurements over Wi-Fi UDP port 5005.", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    main()
