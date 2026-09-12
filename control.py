"""Indoor Positioning — Application Launcher & Control Centre.

A lightweight, dedicated launchpad for the indoor positioning ecosystem:
  📍 Live Tracking Dashboard (Web / Browser)
  🛠️ System Administrator & Telemetry (Standalone Python GUI)
  📡 Data Collector (Standalone Python GUI)
  🧠 Model Trainer (Standalone Python GUI)
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    BACKEND_PORT, DASHBOARD_PORT, BACKEND_URL, DASHBOARD_URL,
    PYTHON_EXE, NODE_BIN, MODELS_DIR, DATASETS_DIR, free_port, open_browser_url
)

VITE_JS = BASE_DIR / "node_modules" / "vite" / "bin" / "vite.js"
VITE_CMD = (
    (NODE_BIN, str(VITE_JS), "--port", str(DASHBOARD_PORT), "--host", "0.0.0.0")
    if VITE_JS.exists()
    else ("npx", "vite", "--port", str(DASHBOARD_PORT), "--host", "0.0.0.0")
)


class ApplicationLauncher:
    """Lightweight entry point and ecosystem launcher."""

    THEME = {
        "bg": "#0F172A",          # Slate 900
        "panel": "#1E293B",       # Slate 800
        "card": "#334155",        # Slate 700
        "card_hover": "#3B4D66",
        "border": "#475569",      # Slate 600
        "text": "#F8FAFC",        # Slate 50
        "subtext": "#94A3B8",     # Slate 400
        "accent": "#38BDF8",      # Sky 400
        "accent_hover": "#0284C7",
        "green": "#10B981",       # Emerald 500
        "green_dark": "#064E3B",
        "red": "#EF4444",         # Rose 500
        "amber": "#F59E0B",       # Amber 500
        "purple": "#A855F7",      # Purple 500
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Indoor Positioning — Application Launcher")
        self.root.geometry("1100x740")
        self.root.minsize(960, 620)
        self.root.configure(bg=self.THEME["bg"])

        # Process management for background services
        self.processes: dict[str, subprocess.Popen[str] | None] = {
            "backend": None,
            "dashboard": None,
            "simulator": None,
        }
        self.proc_lock = threading.RLock()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.shutting_down = False

        self._configure_styles()
        self._build_ui()

        # Start watchdog loop for background services
        threading.Thread(target=self._watchdog_loop, daemon=True).start()
        self.root.after(100, self._process_log_queue)
        self.root.after(300, self._check_ecosystem_readiness)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Handle CLI autostart flag
        if "--autostart" in sys.argv or "-a" in sys.argv:
            self._log("[LAUNCHER] Autostart mode enabled — launching full tracking stack...")
            self.root.after(500, self.start_full_stack)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        t = self.THEME

        style.configure("TFrame", background=t["bg"])
        style.configure("Panel.TFrame", background=t["panel"])
        style.configure("Card.TFrame", background=t["card"])
        style.configure("TLabel", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9))

    def _build_ui(self) -> None:
        # Top Header
        header = tk.Frame(self.root, bg=self.THEME["panel"], height=64)
        header.pack(fill="x", side="top")

        title_box = tk.Frame(header, bg=self.THEME["panel"])
        title_box.pack(side="left", padx=24, pady=12)

        tk.Label(title_box, text="⚡ INDOOR POSITIONING", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(title_box, text="· Application Control Centre", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 10)).pack(side="left", padx=10)

        # Quick stack action buttons
        btn_box = tk.Frame(header, bg=self.THEME["panel"])
        btn_box.pack(side="right", padx=24, pady=12)

        self.btn_stack = tk.Button(
            btn_box, text="▶  START FULL STACK",
            bg=self.THEME["green"], fg="#FFFFFF", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=14, pady=6,
            command=self.toggle_full_stack,
        )
        self.btn_stack.pack(side="right")

        # Main Container
        main = tk.Frame(self.root, bg=self.THEME["bg"])
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # Grid of Application Cards (2x2)
        apps_frame = tk.Frame(main, bg=self.THEME["bg"])
        apps_frame.pack(fill="x", pady=(0, 16))
        apps_frame.columnconfigure(0, weight=1, uniform="app")
        apps_frame.columnconfigure(1, weight=1, uniform="app")

        # 1. Live Tracking Dashboard Card
        self.card_dash = self._create_app_card(
            apps_frame, row=0, col=0,
            icon="📍", title="Live Tracking Dashboard",
            desc="Focused 2D/3D indoor floor plan, live asset tracking, and tag telemetry.\nPrimary production user interface.",
            status="Web (Port 3000)", status_color=self.THEME["accent"],
            action_text="Launch Dashboard in Browser ↗",
            action_cmd=self.launch_dashboard,
        )

        # 2. System Administrator & Telemetry Card
        self.card_admin = self._create_app_card(
            apps_frame, row=0, col=1,
            icon="🛠️", title="System Administrator & Telemetry",
            desc="Hardware node health, RSSI readings, packet stats, dropped packets,\nnetwork connections, and diagnostic logs.",
            status="Python GUI", status_color=self.THEME["purple"],
            action_text="Launch Admin Console",
            action_cmd=self.launch_admin,
        )

        # 3. Data Collector Card
        self.card_coll = self._create_app_card(
            apps_frame, row=1, col=0,
            icon="📡", title="Sensor Data Collector",
            desc="Dataset survey collection, environmental condition tagging,\nground-truth distance records, and raw CSV persistence.",
            status="Python GUI", status_color=self.THEME["green"],
            action_text="Launch Collector GUI",
            action_cmd=self.launch_collector,
        )

        # 4. Model Trainer Card
        self.card_trainer = self._create_app_card(
            apps_frame, row=1, col=1,
            icon="🧠", title="AI Model Studio & Trainer",
            desc="Feature engineering (60 features), Super Learner ML tournament,\nMAE/RMSE evaluation metrics, and diagnostic plots.",
            status="Python GUI", status_color=self.THEME["amber"],
            action_text="Launch Trainer GUI",
            action_cmd=self.launch_trainer,
        )

        # Lower Split: Service Controls & Console Log
        lower = tk.Frame(main, bg=self.THEME["bg"])
        lower.pack(fill="both", expand=True)

        # Service Controls Bar
        services_bar = tk.Frame(lower, bg=self.THEME["panel"], padx=16, pady=12)
        services_bar.pack(fill="x", pady=(0, 10))

        tk.Label(services_bar, text="CORE SERVICES:", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 12))

        self.btn_backend = self._create_service_button(services_bar, "Backend API (:8000)", "backend", self._toggle_backend)
        self.btn_dashboard_srv = self._create_service_button(services_bar, "Vite Web Server (:3000)", "dashboard", self._toggle_dashboard)
        self.btn_simulator = self._create_service_button(services_bar, "Motion Simulator", "simulator", self._toggle_simulator)

        # Readiness summary pill
        self.readiness_pill = tk.Label(services_bar, text="Ecosystem: Nominal", bg=self.THEME["card"], fg=self.THEME["green"], font=("Segoe UI", 8, "bold"), padx=10, pady=3)
        self.readiness_pill.pack(side="right")

        # Activity Log Box
        log_frame = tk.Frame(lower, bg=self.THEME["panel"], padx=14, pady=10)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="OPERATIONAL ACTIVITY LOG", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 8, "bold")).pack(anchor="w")

        self.log_text = tk.Text(log_frame, bg="#090E17", fg=self.THEME["text"], font=("Consolas", 9), relief="flat", wrap="word", height=6)
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))

    def _create_app_card(self, parent: tk.Frame, row: int, col: int, icon: str, title: str, desc: str, status: str, status_color: str, action_text: str, action_cmd) -> dict:
        card = tk.Frame(parent, bg=self.THEME["panel"], padx=18, pady=16)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        # Top line: Icon + Title + Status Pill
        top = tk.Frame(card, bg=self.THEME["panel"])
        top.pack(fill="x")

        tk.Label(top, text=f"{icon}  {title}", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 11, "bold")).pack(side="left")
        status_lbl = tk.Label(top, text=status, bg=self.THEME["card"], fg=status_color, font=("Segoe UI", 8, "bold"), padx=8, pady=2)
        status_lbl.pack(side="right")

        # Description
        tk.Label(card, text=desc, bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(8, 12))

        # Launch Button
        btn = tk.Button(
            card, text=action_text,
            bg=self.THEME["card"], fg=self.THEME["text"],
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            padx=12, pady=6, command=action_cmd,
        )
        btn.pack(fill="x")

        return {"card": card, "status": status_lbl, "btn": btn}

    def _create_service_button(self, parent: tk.Frame, label: str, key: str, cmd) -> tk.Button:
        btn = tk.Button(
            parent, text=f"○ {label}",
            bg=self.THEME["card"], fg=self.THEME["subtext"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2",
            padx=10, pady=3, command=cmd,
        )
        btn.pack(side="left", padx=4)
        return btn

    def _log(self, msg: str) -> None:
        t_str = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{t_str}] {msg}\n")

    def _process_log_queue(self) -> None:
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self.log_text.insert("end", line)
            self.log_text.see("end")
        self.root.after(100, self._process_log_queue)

    def _check_ecosystem_readiness(self) -> None:
        """Verify model presence, dataset availability, and service statuses."""
        m_path = MODELS_DIR / "distance_estimator.joblib"
        d_path = DATASETS_DIR / "observations.csv"

        if m_path.exists():
            try:
                meta_path = MODELS_DIR / "model_metadata.json"
                mae_str = ""
                if meta_path.exists():
                    with open(meta_path, "r") as f:
                        mae = json.load(f).get("metrics", {}).get("test_mae", 0.0)
                        mae_str = f" (MAE: {mae:.2f}m)"
                self.card_trainer["status"].config(text=f"Trained{mae_str}", fg=self.THEME["green"])
            except Exception:
                pass
        else:
            self.card_trainer["status"].config(text="Needs Training", fg=self.THEME["amber"])

        if d_path.exists():
            self.card_coll["status"].config(text="Dataset Ready", fg=self.THEME["green"])

        self.root.after(3000, self._check_ecosystem_readiness)

    # ── Application Launchers ────────────────────────────────────────────────
    def launch_dashboard(self) -> None:
        """Ensure backend and Vite server are running, then launch browser."""
        self._log("Opening Live Tracking Dashboard in browser...")
        if not self._is_service_running("backend"):
            self._start_service("backend")
        if not self._is_service_running("dashboard"):
            self._start_service("dashboard")

        # Launch browser after slight delay to allow Vite initialization
        self.root.after(600, lambda: open_browser_url(DASHBOARD_URL))

    def launch_admin(self) -> None:
        """Launch the standalone System Administrator & Telemetry GUI."""
        self._log("Launching Standalone System Administrator GUI...")
        script = BASE_DIR / "admin_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_collector(self) -> None:
        """Launch the standalone Data Collector GUI."""
        self._log("Launching Standalone Data Collector GUI...")
        script = BASE_DIR / "collector_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_trainer(self) -> None:
        """Launch the standalone Model Trainer GUI."""
        self._log("Launching Standalone Model Trainer GUI...")
        script = BASE_DIR / "trainer_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    # ── Full Stack Controls ──────────────────────────────────────────────────
    def toggle_full_stack(self) -> None:
        if any(self._is_service_running(k) for k in ("backend", "dashboard")):
            self.stop_full_stack()
        else:
            self.start_full_stack()

    def start_full_stack(self) -> None:
        self._log("Starting full tracking stack (Backend, Web Server, Motion Simulator)...")
        self._start_service("backend")
        self._start_service("dashboard")
        self._start_service("simulator")
        self.btn_stack.config(text="⏹  STOP FULL STACK", bg=self.THEME["red"])

    def stop_full_stack(self) -> None:
        self._log("Stopping all background services...")
        self._stop_service("simulator")
        self._stop_service("dashboard")
        self._stop_service("backend")
        self.btn_stack.config(text="▶  START FULL STACK", bg=self.THEME["green"])

    # ── Service Process Management ───────────────────────────────────────────
    def _is_service_running(self, key: str) -> bool:
        with self.proc_lock:
            proc = self.processes.get(key)
            return proc is not None and proc.poll() is None

    def _start_service(self, key: str) -> None:
        with self.proc_lock:
            if self._is_service_running(key):
                return

            if key == "backend":
                free_port(BACKEND_PORT)
                cmd = [PYTHON_EXE, str(PROJECT_ROOT / "server" / "app.py")]
                cwd = str(PROJECT_ROOT / "server")
            elif key == "dashboard":
                free_port(DASHBOARD_PORT)
                cmd = list(VITE_CMD)
                cwd = str(BASE_DIR)
            elif key == "simulator":
                cmd = [PYTHON_EXE, str(PROJECT_ROOT / "simulate_demo.py")]
                cwd = str(PROJECT_ROOT)
            else:
                return

            try:
                proc = subprocess.Popen(
                    cmd, cwd=cwd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                self.processes[key] = proc
                self._log(f"Started service [{key}] (PID: {proc.pid})")
                threading.Thread(target=self._drain_proc_output, args=(key, proc), daemon=True).start()
            except Exception as e:
                self._log(f"[ERROR] Failed to start {key}: {e}")

    def _stop_service(self, key: str) -> None:
        with self.proc_lock:
            proc = self.processes.get(key)
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                self.processes[key] = None
                self._log(f"Stopped service [{key}]")

    def _drain_proc_output(self, key: str, proc: subprocess.Popen) -> None:
        if not proc.stdout:
            return
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            stripped = line.strip()
            if stripped:
                # Log select messages
                if any(kw in stripped.lower() for kw in ("ready", "error", "running", "listening", "started")):
                    self._log(f"[{key}] {stripped}")

    def _toggle_backend(self) -> None:
        if self._is_service_running("backend"):
            self._stop_service("backend")
        else:
            self._start_service("backend")

    def _toggle_dashboard(self) -> None:
        if self._is_service_running("dashboard"):
            self._stop_service("dashboard")
        else:
            self._start_service("dashboard")

    def _toggle_simulator(self) -> None:
        if self._is_service_running("simulator"):
            self._stop_service("simulator")
        else:
            self._start_service("simulator")

    def _watchdog_loop(self) -> None:
        """Watch service states and update button indicators."""
        while not self.shutting_down:
            time.sleep(1.0)
            if self.shutting_down:
                break

            b_run = self._is_service_running("backend")
            d_run = self._is_service_running("dashboard")
            s_run = self._is_service_running("simulator")

            self.root.after(0, lambda: self._update_service_indicators(b_run, d_run, s_run))

    def _update_service_indicators(self, b_run: bool, d_run: bool, s_run: bool) -> None:
        self.btn_backend.config(
            text=f"{'🟢' if b_run else '○'} Backend API (:8000)",
            fg=self.THEME["green"] if b_run else self.THEME["subtext"],
        )
        self.btn_dashboard_srv.config(
            text=f"{'🟢' if d_run else '○'} Vite Web Server (:3000)",
            fg=self.THEME["green"] if d_run else self.THEME["subtext"],
        )
        self.btn_simulator.config(
            text=f"{'🟢' if s_run else '○'} Motion Simulator",
            fg=self.THEME["green"] if s_run else self.THEME["subtext"],
        )

        # Update card status pill for Live Dashboard
        if d_run and b_run:
            self.card_dash["status"].config(text="Running (:3000)", fg=self.THEME["green"])
        else:
            self.card_dash["status"].config(text="Web (Port 3000)", fg=self.THEME["accent"])

    def _on_close(self) -> None:
        self.shutting_down = True
        with self.proc_lock:
            for k, p in list(self.processes.items()):
                if p and p.poll() is None:
                    try:
                        p.terminate()
                    except Exception:
                        pass
        self.root.destroy()


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            "Indoor Positioning System — Control Centre Launcher\n\n"
            "Usage:\n"
            "  python control.py                    Launch interactive Control Centre GUI\n"
            "  python control.py --autostart        Launch Control Centre and immediately start services\n"
            "  python control.py --app admin        Launch System Administrator / Telemetry GUI\n"
            "  python control.py --app collector    Launch Data Collector GUI\n"
            "  python control.py --app trainer      Launch Model Trainer GUI\n"
            "  python control.py --app tracking     Launch Live Tracking Web Dashboard\n"
        )
        return

    # CLI App Dispatcher
    if "--app" in sys.argv:
        idx = sys.argv.index("--app")
        if idx + 1 < len(sys.argv):
            target_app = sys.argv[idx + 1].lower()
            if target_app == "admin":
                import admin_gui
                admin_gui.main()
                return
            elif target_app in ("collector", "collect"):
                import collector_gui
                collector_gui.main()
                return
            elif target_app in ("trainer", "train"):
                import trainer_gui
                trainer_gui.main()
                return
            elif target_app in ("tracking", "dashboard"):
                open_browser_url(DASHBOARD_URL)
                return

    root = tk.Tk()
    app = ApplicationLauncher(root)
    if "--autostart" in sys.argv:
        root.after(500, app._toggle_backend)
        root.after(1000, app._toggle_dashboard)
    root.mainloop()


if __name__ == "__main__":
    main()

