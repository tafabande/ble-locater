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


# ── LAN & Wi-Fi Network Interface Detection (No Internet / 8.8.8.8 Trick) ─────
def get_active_lan_interfaces() -> list[tuple[str, str]]:
    """Enumerate real active local LAN / Wi-Fi network interfaces with IPv4 addresses.

    Operates 100% offline without connecting to external internet IP (8.8.8.8).
    Excludes loopback (127.0.0.1), link-local (169.254.x.x), and virtual/hyper-v adapters.
    Prioritizes real physical Wi-Fi adapters first, then Ethernet.
    Returns list of (interface_name, ipv4_address).
    """
    results: list[tuple[str, str]] = []
    seen_ips: set[str] = set()

    # 1. Try psutil if available in environment
    try:
        import psutil
        import socket
        for name, snics in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(name)
            if stats and not stats.isup:
                continue
            lower_name = name.lower()
            if any(v in lower_name for v in ("vethernet", "virtualbox", "vmware", "hyper-v", "wsl", "loopback", "bluetooth")):
                continue
            for snic in snics:
                if snic.family == socket.AF_INET:
                    ip = snic.address
                    if not ip.startswith(("127.", "169.254.")) and ip not in seen_ips:
                        results.append((name, ip))
                        seen_ips.add(ip)
    except Exception:
        pass

    # 2. Fallback to native OS command if psutil is unavailable or returned empty
    if not results and sys.platform == "win32":
        try:
            import re
            out = subprocess.check_output("ipconfig", text=True, stderr=subprocess.DEVNULL)
            current_adapter = "LAN"
            for line in out.splitlines():
                m_adapter = re.match(r"^[A-Za-z0-9].*adapter (.*):", line)
                if m_adapter:
                    current_adapter = m_adapter.group(1).strip()
                m_ip = re.search(r"IPv4 Address[ .]*: ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", line)
                if m_ip:
                    ip = m_ip.group(1).strip()
                    lower_name = current_adapter.lower()
                    if not any(v in lower_name for v in ("vethernet", "virtualbox", "vmware", "hyper-v", "wsl", "loopback", "bluetooth")):
                        if not ip.startswith(("127.", "169.254.")) and ip not in seen_ips:
                            results.append((current_adapter, ip))
                            seen_ips.add(ip)
        except Exception:
            pass

    # Rank Wi-Fi adapters first, then Ethernet, then other LAN
    def _rank(item: tuple[str, str]) -> int:
        n_lower = item[0].lower()
        if any(w in n_lower for w in ("wi-fi", "wifi", "wlan", "wireless", "802.11")):
            return 0
        if any(e in n_lower for e in ("ethernet", "eth", "local area")):
            return 1
        return 2

    results.sort(key=_rank)
    return results


def get_primary_lan_ip() -> str:
    """Return the primary active local LAN or Wi-Fi IPv4 address of this machine."""
    interfaces = get_active_lan_interfaces()
    if interfaces:
        return interfaces[0][1]
    return "127.0.0.1"


def get_hotspot_lan_interfaces() -> list[tuple[str, str]]:
    """Return active Windows Mobile Hotspot / Wi-Fi Direct LAN interfaces.

    The RTLS experiment uses the laptop as the access point. Its receiver
    address must come from the hotspot-facing interface, not an unrelated
    Internet-facing Wi-Fi or Ethernet connection.
    """
    candidates: list[tuple[str, str]] = []
    for name, ip in get_active_lan_interfaces():
        name_lower = name.lower()
        is_hotspot_name = (
            "local area connection*" in name_lower
            or "wi-fi direct" in name_lower
            or "wifi direct" in name_lower
            or "mobile hotspot" in name_lower
            or "hotspot" in name_lower
        )
        is_private_lan = ip.startswith((
            "10.", "192.168.", "172.16.", "172.17.", "172.18.",
            "172.19.", "172.2", "172.30.", "172.31.",
        ))
        if is_hotspot_name and is_private_lan:
            candidates.append((name, ip))
    return candidates


def get_experiment_receiver_ip() -> str:
    """Return the dedicated hotspot receiver IPv4 address, or empty if absent."""
    hotspots = get_hotspot_lan_interfaces()
    return hotspots[0][1] if hotspots else ""



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
    """Free a TCP or UDP port if an orphaned process is holding it on Windows."""
    if os.name != "nt":
        return
    try:
        result = subprocess.run(
            ["netstat", "-aon"],
            capture_output=True, text=True, timeout=5,
        )
        current_pid = os.getpid()
        for line in result.stdout.splitlines():
            clean = line.strip()
            if f":{port}" in clean and ("LISTENING" in clean or clean.startswith("UDP")):
                parts = clean.split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) > 0 and int(pid) != current_pid:
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
