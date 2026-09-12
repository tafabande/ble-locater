"""Indoor Positioning — Centralized Configuration & Environment Settings.

Removes hardcoded ports, file paths, coordinates, and environment assumptions.
Supports environment variable overrides and JSON configuration loading.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# ── Directory Paths ──────────────────────────────────────────────────────────
CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CORE_DIR.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

DATASETS_DIR = Path(os.environ.get("BLE_DATASETS_DIR", PROJECT_ROOT / "datasets"))
RAW_DATA_DIR = Path(os.environ.get("BLE_RAW_DATA_DIR", DATASETS_DIR / "raw"))
MODELS_DIR = Path(os.environ.get("BLE_MODELS_DIR", PROJECT_ROOT / "models"))
REPORTS_DIR = Path(os.environ.get("BLE_REPORTS_DIR", PROJECT_ROOT / "reports"))

# Ensure directories exist
for directory in (DATASETS_DIR, RAW_DATA_DIR, MODELS_DIR, REPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


# ── Network & Host Configuration ─────────────────────────────────────────────
BACKEND_HOST = os.environ.get("BLE_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BLE_BACKEND_PORT", "8000"))
DASHBOARD_HOST = os.environ.get("BLE_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.environ.get("BLE_DASHBOARD_PORT", "3000"))

BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
WS_URL = f"ws://{BACKEND_HOST}:{BACKEND_PORT}/ws"
DASHBOARD_URL = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"


# ── Python Environment Detection ─────────────────────────────────────────────
def get_python_executable() -> str:
    """Find the project virtual environment Python or fallback to current sys.executable."""
    venv_candidates = [
        PROJECT_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
        WORKSPACE_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
        PROJECT_ROOT / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
    ]
    for candidate in venv_candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


PYTHON_EXE = get_python_executable()
NODE_BIN = shutil.which("node") or "node"


# ── Default Anchor Coordinates & Metadata ────────────────────────────────────
DEFAULT_ANCHORS_CONFIG: Dict[str, Tuple[float, float]] = {
    "ANCHOR_01": (0.2, 5.2),
    "ANCHOR_02": (4.8, 5.2),
    "ANCHOR_03": (2.5, 9.8),
    "ANCHOR_04": (5.2, 5.2),
    "ANCHOR_05": (9.8, 5.2),
    "ANCHOR_06": (7.5, 9.8),
    "ANCHOR_07": (0.2, 0.2),
    "ANCHOR_08": (4.8, 0.2),
    "ANCHOR_09": (2.5, 4.8),
    "ANCHOR_10": (5.2, 0.2),
    "ANCHOR_11": (9.8, 0.2),
    "ANCHOR_12": (7.5, 4.8),
}

DEFAULT_ANCHORS_METADATA: Dict[str, Dict[str, Any]] = {
    "ANCHOR_01": {"mac": "24:6F:28:1A:4C:01", "name": "ESP32 Node 1 (SW Room A)"},
    "ANCHOR_02": {"mac": "24:6F:28:1A:4C:02", "name": "ESP32 Node 2 (SE Room A)"},
    "ANCHOR_03": {"mac": "24:6F:28:1A:4C:03", "name": "ESP32 Node 3 (NW Room A)"},
    "ANCHOR_04": {"mac": "24:6F:28:1A:4C:04", "name": "ESP32 Node 4 (SW Room B)"},
    "ANCHOR_05": {"mac": "24:6F:28:1A:4C:05", "name": "ESP32 Node 5 (SE Room B)"},
    "ANCHOR_06": {"mac": "24:6F:28:1A:4C:06", "name": "ESP32 Node 6 (NW Room B)"},
    "ANCHOR_07": {"mac": "24:6F:28:1A:4C:07", "name": "ESP32 Node 7 (SW Room C)"},
    "ANCHOR_08": {"mac": "24:6F:28:1A:4C:08", "name": "ESP32 Node 8 (SE Room C)"},
    "ANCHOR_09": {"mac": "24:6F:28:1A:4C:09", "name": "ESP32 Node 9 (NW Room C)"},
    "ANCHOR_10": {"mac": "24:6F:28:1A:4C:10", "name": "ESP32 Node 10 (SW Room D)"},
    "ANCHOR_11": {"mac": "24:6F:28:1A:4C:11", "name": "ESP32 Node 11 (SE Room D)"},
    "ANCHOR_12": {"mac": "24:6F:28:1A:4C:12", "name": "ESP32 Node 12 (NW Room D)"},
}


def load_anchor_config() -> Dict[str, Tuple[float, float]]:
    """Load anchor positions from file or environment, falling back to default."""
    env_config = os.environ.get("BLE_ANCHORS_CONFIG")
    if env_config:
        try:
            parsed = json.loads(env_config)
            return {k: (float(v[0]), float(v[1])) for k, v in parsed.items()}
        except Exception:
            pass

    config_file = PROJECT_ROOT / "config" / "anchors.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                parsed = json.load(f)
                return {k: (float(v[0]), float(v[1])) for k, v in parsed.items()}
        except Exception:
            pass

    return DEFAULT_ANCHORS_CONFIG.copy()


def load_anchor_metadata() -> Dict[str, Dict[str, Any]]:
    """Load anchor metadata from file or environment, falling back to default."""
    config_file = PROJECT_ROOT / "config" / "anchors_metadata.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_ANCHORS_METADATA.copy()


# ── System Utilities ─────────────────────────────────────────────────────────
def free_port(port: int) -> None:
    """Free a TCP port if an orphaned process is holding it on Windows."""
    if os.name != "nt":
        return
    try:
        result = subprocess.run(
            ["netstat", "-aon"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) > 0:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    except Exception:
        pass


def open_browser_url(url: str) -> None:
    """Reliably launch a URL in the user's default browser or Google Chrome."""
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for cp in chrome_paths:
            if os.path.exists(cp):
                try:
                    subprocess.Popen([cp, url])
                    return
                except Exception:
                    pass
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", url])
            return
        except Exception:
            pass

    import webbrowser
    webbrowser.open(url)
