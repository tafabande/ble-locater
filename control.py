"""Indoor Positioning — Application Launcher & Research Operations Console (Project 1).

A lightweight, dedicated launchpad for the indoor positioning research ecosystem:
  Data Collector & Room Surveyor (controller.py)
  ESP32 Wireless Provisioner & Flasher (setup.py)
  AI Model Studio & Trainer (trainer_gui.py)
  System Administrator & Telemetry (admin_gui.py)
"""
from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    BACKEND_PORT, BACKEND_URL,
    PYTHON_EXE, MODELS_DIR, DATASETS_DIR, free_port
)


def wait_for_http_ready(url: str, timeout_sec: float = 15.0, check_interval: float = 0.5) -> bool:
    """Poll an HTTP URL with retries until it returns HTTP < 500 or timeout expires."""
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ControlWatchdog"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            pass
        time.sleep(check_interval)
    return False


class ApplicationLauncher:
    """Lightweight entry point and ecosystem launcher for Project 1."""

    THEME = {
        "bg": "#121214",          # Deep Zinc background
        "panel": "#18181B",       # Zinc 900 panel
        "card": "#27272A",        # Zinc 800 card
        "card_hover": "#323238",  # Zinc 750 hover
        "border": "#3F3F46",      # Zinc 700 border
        "text": "#FAFAFA",        # Zinc 50 text
        "subtext": "#A1A1AA",     # Zinc 400 subtext
        "accent": "#E4E4E7",      # Crisp neutral Zinc 200
        "accent_hover": "#D4D4D8",
        "green": "#10B981",       # Emerald 500
        "green_dark": "#064E3B",
        "red": "#EF4444",         # Rose 500
        "amber": "#F59E0B",       # Amber 500
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Indoor Positioning — Research Operations Console")
        self.root.geometry("1060x700")
        self.root.minsize(920, 600)
        self.root.configure(bg=self.THEME["bg"])

        # Process management for background services
        self.processes: dict[str, subprocess.Popen[str] | None] = {
            "backend": None,
        }
        self.expected_services: set[str] = set()
        self._service_restart_counts: dict[str, int] = {"backend": 0}
        self.proc_lock = threading.RLock()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.shutting_down = False

        self._configure_styles()
        self._build_ui()

        # Start watchdog loop for background services
        threading.Thread(target=self._watchdog_loop, daemon=True).start()
        self.root.after(100, self._process_log_queue)
        self.root.after(300, self._check_ecosystem_readiness)

        if "--autostart" in sys.argv:
            self.root.after(500, self.start_full_stack)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self.THEME["bg"], foreground=self.THEME["text"])
        style.configure("TProgressbar", thickness=6, background=self.THEME["green"], troughcolor=self.THEME["panel"], borderwidth=0)

    def _build_ui(self) -> None:
        # Header Bar
        header = tk.Frame(self.root, bg=self.THEME["panel"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=self.THEME["panel"])
        title_box.pack(side="left", padx=24, pady=12)

        tk.Label(
            title_box, text="⚡ INDOOR POSITIONING",
            bg=self.THEME["panel"], fg=self.THEME["text"],
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        tk.Label(
            title_box, text="Research Platform · Physical ESP32 Hardware Ingestion · ML Tournament Studio",
            bg=self.THEME["panel"], fg=self.THEME["subtext"],
            font=("Segoe UI", 8)
        ).pack(anchor="w")

        btn_box = tk.Frame(header, bg=self.THEME["panel"])
        btn_box.pack(side="right", padx=24, pady=12)

        self.btn_benchmark = tk.Button(
            btn_box, text="BENCHMARK STUDIO",
            bg="#FBBF24", fg="#121214", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=12, pady=6,
            command=self.launch_benchmark,
        )
        self.btn_benchmark.pack(side="right", padx=(0, 10))

        self.btn_stack = tk.Button(
            btn_box, text="▶  START BACKEND ENGINE",
            bg=self.THEME["green"], fg="#FFFFFF", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=14, pady=6,
            command=self.toggle_full_stack,
        )
        self.btn_stack.pack(side="right")

        # Main Container
        main = tk.Frame(self.root, bg=self.THEME["bg"])
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # 2x2 Grid of Application Cards
        apps_frame = tk.Frame(main, bg=self.THEME["bg"])
        apps_frame.pack(fill="x", pady=(0, 16))
        apps_frame.columnconfigure(0, weight=1, uniform="app")
        apps_frame.columnconfigure(1, weight=1, uniform="app")

        # 1. Experiment Controller & Data Collector Card (Row 0, Col 0)
        self.card_coll = self._create_app_card(
            apps_frame, row=0, col=0,
            icon="[COLLECTOR]", title="Experiment Controller & Data Collector",
            desc="Remodeled collection console: Master Start/Pause/Stop ribbon,\n2D room layout, obstacle raycasting & wireless Wi-Fi UDP ingestion.",
            status="Python GUI", status_color=self.THEME["green"],
            action_text="Launch Controller GUI",
            action_cmd=self.launch_collector,
        )

        # 2. ESP32 Wireless Provisioner & Flasher Card (Row 0, Col 1)
        self.card_setup = self._create_app_card(
            apps_frame, row=0, col=1,
            icon="[HARDWARE]", title="ESP32 Wireless Setup & Flasher",
            desc="Provision Wi-Fi credentials, bind hardware MAC to 4 corners\n(Node A, B, C, D), flash ESP32 ROM & serial debug monitor.",
            status="Python GUI", status_color=self.THEME["accent"],
            action_text="Launch Setup & Flasher GUI",
            action_cmd=self.launch_setup,
        )

        # 3. Model Trainer Card (Row 1, Col 0)
        self.card_trainer = self._create_app_card(
            apps_frame, row=1, col=0,
            icon="[TRAINER]", title="AI Model Studio & Trainer",
            desc="Feature engineering (60 features), Super Learner ML tournament,\nMAE/RMSE evaluation metrics, and diagnostic plots.",
            status="Python GUI", status_color=self.THEME["amber"],
            action_text="Launch Trainer GUI",
            action_cmd=self.launch_trainer,
            secondary_text="Benchmark Studio",
            secondary_cmd=self.launch_benchmark,
        )

        # 4. System Administrator & Telemetry Card (Row 1, Col 1)
        self.card_admin = self._create_app_card(
            apps_frame, row=1, col=1,
            icon="[ADMIN]", title="System Administrator & Telemetry",
            desc="Hardware node health, RSSI readings, packet stats, dropped packets,\nnetwork connections, and diagnostic logs.",
            status="Python GUI", status_color=self.THEME["accent"],
            action_text="Launch Admin Console",
            action_cmd=self.launch_admin,
        )

        # Lower Split: Service Controls & Console Log
        lower = tk.Frame(main, bg=self.THEME["bg"])
        lower.pack(fill="both", expand=True)

        # Service Controls Bar
        services_bar = tk.Frame(lower, bg=self.THEME["panel"], padx=16, pady=12)
        services_bar.pack(fill="x", pady=(0, 10))

        tk.Label(services_bar, text="CORE SERVICES:", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 12))

        self.btn_backend = self._create_service_button(services_bar, "Backend API (:8000)", "backend", self._toggle_backend)

        # Readiness summary pill
        self.readiness_pill = tk.Label(services_bar, text="Ecosystem: Standby", bg=self.THEME["card"], fg=self.THEME["amber"], font=("Segoe UI", 8, "bold"), padx=10, pady=3)
        self.readiness_pill.pack(side="right")

        # Activity Log Box
        log_frame = tk.Frame(lower, bg=self.THEME["panel"], padx=14, pady=10)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="OPERATIONAL ACTIVITY LOG", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 8, "bold")).pack(anchor="w")

        self.log_text = tk.Text(log_frame, bg="#0E0E10", fg=self.THEME["text"], font=("Consolas", 9), relief="flat", wrap="word", height=6)
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))

    def _create_app_card(self, parent: tk.Frame, row: int, col: int, icon: str, title: str, desc: str, status: str, status_color: str, action_text: str, action_cmd, secondary_text: str = None, secondary_cmd = None) -> dict:
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

        # Launch Button(s)
        btn_box = tk.Frame(card, bg=self.THEME["panel"])
        btn_box.pack(fill="x")

        btn = tk.Button(
            btn_box, text=action_text,
            bg=self.THEME["card"], fg=self.THEME["text"],
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            padx=12, pady=6, command=action_cmd,
        )

        if secondary_text and secondary_cmd:
            btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
            sec_btn = tk.Button(
                btn_box, text=secondary_text,
                bg="#FBBF24", fg="#121214",
                font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                padx=10, pady=6, command=secondary_cmd,
            )
            sec_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
        else:
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
    def launch_admin(self) -> None:
        """Launch the standalone System Administrator & Telemetry GUI."""
        self._log("Launching Standalone System Administrator GUI...")
        script = BASE_DIR / "admin_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_collector(self) -> None:
        """Launch the standalone Experiment Controller & Data Collector GUI."""
        self._log("Launching Standalone Experiment Controller & Data Collector GUI...")
        script = BASE_DIR / "controller.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_setup(self) -> None:
        """Launch the standalone ESP32 Wireless Provisioner & Flasher GUI."""
        self._log("Launching Standalone ESP32 Wireless Provisioner & Flasher GUI...")
        script = BASE_DIR / "setup.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_trainer(self) -> None:
        """Launch the standalone Model Trainer GUI."""
        self._log("Launching Standalone Model Trainer GUI...")
        script = BASE_DIR / "trainer_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))

    def launch_benchmark(self) -> None:
        """Launch the standalone Model Tournament Benchmark Studio."""
        self._log("Launching Model Tournament Benchmark Studio & Evaluation Suite...")
        script = BASE_DIR / "benchmark_gui.py"
        subprocess.Popen([PYTHON_EXE, str(script)], cwd=str(BASE_DIR))


    # ── Backend Service Controls ─────────────────────────────────────────────
    def toggle_full_stack(self) -> None:
        if self._is_service_running("backend"):
            self.stop_full_stack()
        else:
            self.start_full_stack()

    def start_full_stack(self) -> None:
        self._log("Starting Backend API engine (:8000)...")
        self.expected_services.add("backend")
        self._start_service("backend")
        self.btn_stack.config(text="⏹  STOP BACKEND ENGINE", bg=self.THEME["red"])

        def _verify_readiness():
            b_ready = wait_for_http_ready(f"{BACKEND_URL}/healthz", timeout_sec=18.0) or wait_for_http_ready(f"{BACKEND_URL}/api/health", timeout_sec=5.0)
            if b_ready:
                self._log("✔ Backend API (:8000) verified healthy and accepting telemetry.")
                self.root.after(0, lambda: self.readiness_pill.config(text="Backend: Healthy", fg=self.THEME["green"]))

        threading.Thread(target=_verify_readiness, daemon=True).start()

    def stop_full_stack(self) -> None:
        self._log("Stopping backend engine...")
        self.expected_services.clear()
        self._service_restart_counts = {"backend": 0}
        self._stop_service("backend")
        self.btn_stack.config(text="▶  START BACKEND ENGINE", bg=self.THEME["green"])
        self.readiness_pill.config(text="Backend: Stopped", fg=self.THEME["subtext"])

    # ── Service Process Management ───────────────────────────────────────────
    def _is_service_running(self, key: str) -> bool:
        with self.proc_lock:
            proc = self.processes.get(key)
            return proc is not None and proc.poll() is None

    def _start_service(self, key: str, max_retries: int = 3) -> bool:
        """Start a managed service with port pre-clearing and retry on failure."""
        with self.proc_lock:
            if self._is_service_running(key):
                return True

            for attempt in range(1, max_retries + 1):
                if self.shutting_down:
                    return False

                if key == "backend":
                    free_port(BACKEND_PORT)
                    cmd = [PYTHON_EXE, str(PROJECT_ROOT / "server" / "app.py")]
                    cwd = str(PROJECT_ROOT / "server")
                else:
                    return False

                try:
                    self._log(f"Starting [{key}] (attempt {attempt}/{max_retries})...")
                    proc = subprocess.Popen(
                        cmd, cwd=cwd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1,
                    )
                    self.processes[key] = proc
                    self._log(f"Started service [{key}] (PID: {proc.pid})")
                    threading.Thread(target=self._drain_proc_output, args=(key, proc), daemon=True).start()

                    time.sleep(0.8)
                    if proc.poll() is None:
                        return True
                    else:
                        exit_code = proc.poll()
                        self._log(f"[WARN] [{key}] process exited with code {exit_code}. Retrying...")
                        if key == "backend":
                            free_port(BACKEND_PORT)
                        time.sleep(1.0)
                except Exception as e:
                    self._log(f"[ERROR] Attempt {attempt} failed to start [{key}]: {e}")
                    time.sleep(1.0)

            self._log(f"✖ [FAILURE] Could not start service [{key}] after {max_retries} attempts.")
            return False

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
                if any(kw in stripped.lower() for kw in ("ready", "error", "running", "listening", "started")):
                    self._log(f"[{key}] {stripped}")

    def _toggle_backend(self) -> None:
        if self._is_service_running("backend"):
            self.expected_services.discard("backend")
            self._stop_service("backend")
        else:
            self.expected_services.add("backend")
            self._start_service("backend")

    def _watchdog_loop(self) -> None:
        """Watch service states, auto-recover crashed services, and update button indicators."""
        while not self.shutting_down:
            time.sleep(1.5)
            if self.shutting_down:
                break

            b_run = self._is_service_running("backend")

            if not self.shutting_down:
                if "backend" in self.expected_services and not b_run:
                    retries = self._service_restart_counts.get("backend", 0)
                    if retries < 3:
                        self._service_restart_counts["backend"] = retries + 1
                        self._log(f"🚨 [WATCHDOG] Backend API crashed unexpectedly! Auto-restarting (retry {retries + 1}/3)...")
                        self._start_service("backend")
                    else:
                        self._log("✖ [WATCHDOG] Backend API crashed repeatedly. Manual check required.")
                        self.expected_services.discard("backend")

            self.root.after(0, lambda: self._update_service_indicators(b_run))

    def _update_service_indicators(self, b_run: bool) -> None:
        self.btn_backend.config(
            text=f"{'🟢' if b_run else '○'} Backend API (:8000)",
            fg=self.THEME["green"] if b_run else self.THEME["subtext"],
        )

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


# ── Headless Pipeline ────────────────────────────────────────────────────────
def run_headless_pipeline() -> int:
    """Run backend API service in headless daemon mode with watchdog."""
    print("=" * 70)
    print(" ⚡ INDOOR POSITIONING — HEADLESS BACKEND PIPELINE")
    print("=" * 70)

    stop_event = threading.Event()

    def _sig_handler(signum, frame):
        print("\n[SHUTDOWN] Intercepted interrupt signal. Halting backend...")
        stop_event.set()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    processes: dict[str, subprocess.Popen] = {}

    def _start(name: str, cmd: list[str], cwd: str, port: int):
        free_port(port)
        p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        processes[name] = p
        print(f"[{name.upper()}] Launched with PID {p.pid}")
        return p

    # Start Backend
    backend_cmd = [PYTHON_EXE, str(PROJECT_ROOT / "server" / "app.py")]
    _start("backend", backend_cmd, str(PROJECT_ROOT / "server"), BACKEND_PORT)
    print("[BACKEND] Waiting for health status...")
    if wait_for_http_ready(f"{BACKEND_URL}/healthz", timeout_sec=20.0) or wait_for_http_ready(f"{BACKEND_URL}/api/health", timeout_sec=5.0):
        print("✔ [BACKEND READY] FastAPI server is healthy at http://127.0.0.1:8000")
    else:
        print("⚠️ [BACKEND WARN] Backend health check timed out. Continuing...")

    print("\n[PIPELINE ACTIVE] Backend running. Press Ctrl+C to terminate.\n")

    restart_counts = {"backend": 0}
    while not stop_event.is_set():
        time.sleep(2.0)
        bp = processes.get("backend")
        if bp and bp.poll() is not None and not stop_event.is_set():
            rc = restart_counts["backend"]
            if rc < 5:
                restart_counts["backend"] += 1
                print(f"🚨 [WATCHDOG] Backend process died (exit {bp.poll()}). Auto-restarting ({rc+1}/5)...")
                _start("backend", backend_cmd, str(PROJECT_ROOT / "server"), BACKEND_PORT)
                wait_for_http_ready(f"{BACKEND_URL}/healthz", timeout_sec=10.0)

    for name, p in processes.items():
        if p and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    print("[SHUTDOWN] Backend stopped cleanly.")
    return 0


def run_pipeline_tests(max_retries: int = 2) -> int:
    """Run automated pytest suite with retries on failure."""
    print("=" * 70)
    print(" ⚡ INDOOR POSITIONING — AUTOMATED TEST SUITE RUNNER")
    print("=" * 70)
    test_dir = str(PROJECT_ROOT / "tests")
    cmd = [PYTHON_EXE, "-m", "pytest", test_dir, "-v"]

    for attempt in range(1, max_retries + 1):
        print(f"\n[TEST SUITE] Executing pytest (attempt {attempt}/{max_retries})...")
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if res.returncode == 0:
            print(f"\n✔ [SUCCESS] All tests passed cleanly on attempt {attempt}.")
            return 0
        else:
            print(f"\n⚠️ [TEST RETRY] Pytest exited with code {res.returncode}.")
            if attempt < max_retries:
                print("Freeing ports and retrying tests in 2 seconds...")
                free_port(BACKEND_PORT)
                free_port(5005)
                time.sleep(2.0)

    print(f"\n✖ [FAILURE] Tests failed after {max_retries} attempts.")
    return 1


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            "Indoor Positioning System — Control Centre & Pipeline Launcher\n\n"
            "Usage:\n"
            "  python control.py                    Launch interactive Control Centre GUI\n"
            "  python control.py --autostart        Launch Control Centre and immediately start backend\n"
            "  python control.py --headless         Run backend API in headless CLI mode\n"
            "  python control.py --test             Run automated test suite with retries\n"
            "  python control.py setup              Launch ESP32 Wireless Provisioner & Flasher GUI\n"
            "  python control.py collector          Launch Visual Data Collector & Environment Controller GUI\n"
            "  python control.py trainer            Launch AI Model Studio & Trainer GUI\n"
            "  python control.py benchmark          Launch Model Tournament Benchmark & Performance Studio\n"
            "  python control.py admin              Launch System Administrator & Telemetry GUI\n"
        )
        return

    # Check for direct headless mode
    if "--headless" in sys.argv or "headless" in sys.argv:
        sys.exit(run_headless_pipeline())

    # Check for direct test mode
    if "--test" in sys.argv or "test" in sys.argv:
        sys.exit(run_pipeline_tests())

    # Direct App Dispatcher
    cli_args = [a.lower() for a in sys.argv[1:]]
    if "--setup" in cli_args or "setup" in cli_args or ("--app" in sys.argv and sys.argv[sys.argv.index("--app")+1].lower() in ("setup", "flasher")):
        import setup
        setup.main()
        return
    elif "--collector" in cli_args or "collector" in cli_args or "controller" in cli_args or ("--app" in sys.argv and sys.argv[sys.argv.index("--app")+1].lower() in ("controller", "collector")):
        import controller
        controller.main()
        return
    elif "--admin" in cli_args or "admin" in cli_args or ("--app" in sys.argv and sys.argv[sys.argv.index("--app")+1].lower() == "admin"):
        import admin_gui
        admin_gui.main()
        return
    elif "--trainer" in cli_args or "trainer" in cli_args or ("--app" in sys.argv and sys.argv[sys.argv.index("--app")+1].lower() in ("trainer", "train")):
        import trainer_gui
        trainer_gui.main()
        return
    elif "--benchmark" in cli_args or "benchmark" in cli_args or ("--app" in sys.argv and sys.argv[sys.argv.index("--app")+1].lower() in ("benchmark", "tournament")):
        import benchmark_gui
        benchmark_gui.main()
        return


    root = tk.Tk()
    app = ApplicationLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
