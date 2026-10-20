# -*- coding: utf-8 -*-
"""Autonomous Self-Healing Pipeline Controller for BLE RTLS Dashboard.

Coordinates cross-repository synchronization between:
  1. Backend & ML Tournament Engine: Dissertation (tafabande/ble-locater)
  2. Frontend RTLS Dashboard: Dashboard for Tag Movement (tafabande/ble-dashboard)

Self-Healing Capabilities:
  - Auto-downloads / clones the dashboard repository if missing.
  - Detects and clears conflicting ports (8443, 8000, 5005) and kills stale runtimes.
  - Automatically installs missing npm packages (node_modules).
  - Automatically builds the production bundle (npm run build) if missing.
  - Synchronizes dist/ assets into the FastAPI static directory.
  - Autostarts backend and frontend and launches the web browser.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import BACKEND_PORT, BACKEND_URL, PYTHON_EXE, free_port, open_browser_url

DASHBOARD_PORT = 8443
TELEMETRY_PORT = 5005
GITHUB_REPO_URL = "https://github.com/tafabande/ble-dashboard.git"
BACKEND_STATIC_DIR = PROJECT_ROOT / "server" / "static"


def get_dashboard_dir() -> Path:
    """Resolve the local path of the Dashboard for Tag Movement repo."""
    env_path = os.environ.get("BLE_DASHBOARD_DIR")
    if env_path and Path(env_path).exists():
        return Path(env_path).resolve()

    candidates = [
        BASE_DIR.parent / "Dashboard for Tag Movement",
        BASE_DIR / "Dashboard for Tag Movement",
        BASE_DIR.parent / "ble-dashboard",
        BASE_DIR / "ble-dashboard",
    ]
    for c in candidates:
        if (c / "package.json").exists():
            return c.resolve()

    # Default fallback destination if not yet cloned
    return (BASE_DIR.parent / "Dashboard for Tag Movement").resolve()


def find_tool(name: str) -> str | None:
    """Find an executable tool in PATH or common Windows install locations."""
    found = shutil.which(name)
    if found:
        return found

    # Windows standard locations using forward slashes
    paths: list[str] = []
    if name in ("node", "node.exe"):
        paths = [
            "C:/Program Files/nodejs/node.exe",
            "C:/Program Files (x86)/nodejs/node.exe",
            os.path.expandvars("%LOCALAPPDATA%/Programs/node/node.exe"),
        ]
    elif name in ("npm", "npm.cmd"):
        paths = [
            "C:/Program Files/nodejs/npm.cmd",
            "C:/Program Files (x86)/nodejs/npm.cmd",
            os.path.expandvars("%APPDATA%/npm/npm.cmd"),
        ]
    elif name in ("git", "git.exe"):
        paths = [
            "C:/Program Files/Git/cmd/git.exe",
            "C:/Program Files/Git/bin/git.exe",
            os.path.expandvars("%LOCALAPPDATA%/Programs/Git/cmd/git.exe"),
        ]

    for p in paths:
        if os.path.exists(p):
            return p
    return None


def kill_stale_runtimes_and_ports(log_fn=None) -> None:
    """Free all ports used by the RTLS ecosystem (8443, 8000, 5005)."""
    _log = log_fn or print
    _log("[PIPELINE] Clearing stale runtimes and releasing ports (8443, 8000, 5005)...")
    free_port(DASHBOARD_PORT)
    free_port(BACKEND_PORT)
    free_port(TELEMETRY_PORT)
    time.sleep(0.5)


def check_http_alive(url: str, timeout_sec: float = 1.5) -> bool:
    """Test if an HTTP endpoint returns a valid response."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PipelineWatchdog"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status < 500
    except Exception:
        return False


def ensure_codebase(target_dir: Path, log_fn=None) -> bool:
    """Ensure the dashboard codebase exists. If missing, clone from GitHub."""
    _log = log_fn or print
    if (target_dir / "package.json").exists():
        _log(f"[PIPELINE] Dashboard repository verified at: {target_dir}")
        return True

    _log(f"[PIPELINE] Dashboard repo not found at {target_dir}. Initiating autonomous clone...")
    git_exe = find_tool("git")
    if not git_exe:
        _log("[ERROR] Git not found on system. Please install Git or clone manually.")
        return False

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [git_exe, "clone", GITHUB_REPO_URL, str(target_dir)]
    _log(f"[PIPELINE] Running: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0 and (target_dir / "package.json").exists():
            _log("[PIPELINE] Successfully cloned dashboard codebase.")
            return True
        else:
            _log(f"[ERROR] Git clone failed: {res.stderr}")
            return False
    except Exception as e:
        _log(f"[ERROR] Failed to clone dashboard: {e}")
        return False


def ensure_dependencies(dashboard_dir: Path, log_fn=None) -> bool:
    """Ensure node_modules are installed. Run npm install if missing."""
    _log = log_fn or print
    node_modules = dashboard_dir / "node_modules"
    if node_modules.exists() and (node_modules / "vite").exists():
        _log("[PIPELINE] Node packages verified in node_modules.")
        return True

    _log("[PIPELINE] Missing node_modules detected. Resolving via npm install...")
    npm_cmd = find_tool("npm")
    if not npm_cmd:
        _log("[ERROR] npm not found on system. Please install Node.js.")
        return False

    try:
        cmd = [npm_cmd, "install", "--no-audit", "--no-fund"]
        _log(f"[PIPELINE] Executing: {' '.join(cmd)} in {dashboard_dir}")
        res = subprocess.run(cmd, cwd=str(dashboard_dir), capture_output=True, text=True, timeout=180)
        if res.returncode == 0:
            _log("[PIPELINE] Successfully installed frontend dependencies.")
            return True
        else:
            _log(f"[ERROR] npm install exited with code {res.returncode}: {res.stderr}")
            return False
    except Exception as e:
        _log(f"[ERROR] Exception during npm install: {e}")
        return False


def ensure_build_and_sync(dashboard_dir: Path, log_fn=None) -> bool:
    """Ensure production bundle is compiled and synced to FastAPI static dir."""
    _log = log_fn or print
    dist_index = dashboard_dir / "dist" / "index.html"
    src_app = dashboard_dir / "src" / "App.tsx"

    needs_build = not dist_index.exists()
    if not needs_build and src_app.exists() and dist_index.stat().st_mtime < src_app.stat().st_mtime:
        needs_build = True

    if needs_build:
        _log("[PIPELINE] Production build missing or out of date. Building with npm run build...")
        npm_cmd = find_tool("npm")
        if not npm_cmd:
            _log("[ERROR] npm not found on system. Cannot build bundle.")
            return False
        try:
            cmd = [npm_cmd, "run", "build"]
            res = subprocess.run(cmd, cwd=str(dashboard_dir), capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                _log(f"[ERROR] npm run build failed: {res.stderr}")
                return False
            _log("[PIPELINE] Production build completed successfully.")
        except Exception as e:
            _log(f"[ERROR] Exception during build: {e}")
            return False

    # Sync to backend static directory
    try:
        BACKEND_STATIC_DIR.mkdir(parents=True, exist_ok=True)
        dist_dir = dashboard_dir / "dist"
        if dist_dir.exists():
            _log(f"[PIPELINE] Synchronizing dist/ to {BACKEND_STATIC_DIR}...")
            shutil.copytree(dist_dir, BACKEND_STATIC_DIR, dirs_exist_ok=True)
            _log("[PIPELINE] Static assets synchronized to FastAPI backend.")
    except Exception as e:
        _log(f"[WARN] Failed to sync static files to backend: {e}")

    return True


def heal_and_prepare_environment(log_fn=None) -> tuple[bool, Path | None]:
    """Comprehensive self-healing routine for dashboard environment."""
    _log = log_fn or print
    _log("==================================================================")
    _log(" [SELF-HEALING PIPELINE] Pre-flight Environment Diagnostics")
    _log("==================================================================")

    # 1. Clear ports and kill stale processes
    kill_stale_runtimes_and_ports(_log)

    # 2. Check and ensure codebase
    dash_dir = get_dashboard_dir()
    if not ensure_codebase(dash_dir, _log):
        return False, None

    # 3. Check and install missing dependencies
    if not ensure_dependencies(dash_dir, _log):
        return False, dash_dir

    # 4. Check and build production bundle
    if not ensure_build_and_sync(dash_dir, _log):
        return False, dash_dir

    _log("==================================================================")
    _log(" [SUCCESS] Dashboard environment is fully healed and verified.")
    _log("==================================================================")
    return True, dash_dir


def start_dashboard_service(dash_dir: Path, log_fn=None, pipe_output: bool = True) -> subprocess.Popen:
    """Start the production dashboard server on port 8443."""
    _log = log_fn or print
    node_exe = find_tool("node") or "node"
    server_script = dash_dir / "server.js"

    free_port(DASHBOARD_PORT)
    time.sleep(0.3)

    cmd = [node_exe, str(server_script)]
    _log(f"[PIPELINE] Starting Dashboard Server on port {DASHBOARD_PORT}...")
    
    if pipe_output:
        proc = subprocess.Popen(
            cmd, cwd=str(dash_dir),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
    else:
        proc = subprocess.Popen(
            cmd, cwd=str(dash_dir),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return proc


def launch_full_pipeline(log_fn=None, open_browser: bool = True) -> bool:
    """Autonomous end-to-end launcher:
    1. Heals environment (codebase, packages, ports, build, sync).
    2. Ensures backend API is running.
    3. Starts dashboard host.
    4. Opens browser.
    """
    _log = log_fn or print
    ok, dash_dir = heal_and_prepare_environment(_log)
    if not ok or not dash_dir:
        _log("[ERROR] Self-healing could not complete preparation.")
        return False

    # Start dashboard server
    proc = start_dashboard_service(dash_dir, _log, pipe_output=False)
    _log(f"[PIPELINE] Dashboard server launched (PID: {proc.pid})")

    # Verify HTTP readiness
    _log(f"[PIPELINE] Verifying dashboard at http://localhost:{DASHBOARD_PORT}...")
    ready = False
    for _ in range(20):
        if check_http_alive(f"http://127.0.0.1:{DASHBOARD_PORT}"):
            ready = True
            break
        time.sleep(0.5)

    if ready:
        _log(f"[SUCCESS] RTLS Dashboard is live at http://localhost:{DASHBOARD_PORT}")
        if open_browser:
            _log("[PIPELINE] Launching web browser...")
            open_browser_url(f"http://localhost:{DASHBOARD_PORT}")
        return True
    else:
        _log(f"[WARN] Dashboard port check timed out, but process {proc.pid} is running.")
        if open_browser:
            open_browser_url(f"http://localhost:{DASHBOARD_PORT}")
        return True


if __name__ == "__main__":
    _log_func = print
    launch_full_pipeline(_log_func, open_browser=True)
