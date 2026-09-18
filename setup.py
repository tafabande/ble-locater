"""Standalone ESP32 Wireless Provisioner, Flasher & Settings Tool.

Configures Wi-Fi credentials, reads hardware MAC address, binds nodes
(Node A, B, C, D) permanently, and flashes settings into ESP32 ROM.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collector.setup_gui import main

if __name__ == "__main__":
    main()
