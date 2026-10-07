"""Standalone Model Tournament Benchmark & Performance Studio Entrypoint."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.model_benchmark_view import main

if __name__ == "__main__":
    main()
