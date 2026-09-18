"""Indoor Positioning — Remodeled Data Acquisition & Visual Environment Controller.

Features:
  • Big Start / Pause / Stop master recording ribbon
  • 2D interactive room layout (spacing, grid, 4 corner anchors, obstacles, movable tag)
  • Wireless Wi-Fi UDP telemetry receiver (eliminates cables to laptop during experiments)
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collector.collector_gui import main

if __name__ == "__main__":
    main()
