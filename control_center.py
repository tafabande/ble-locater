"""
⚡ BLE Tracker & Indoor Positioning Studio — Centralized Control Center
======================================================================
A premium, dark-themed control desk placed in the project root folder.
Allows the user to easily launch, stop, and monitor all aspects of the project:
  - FastAPI real-time localization server
  - Streamlit live tracking dashboard
  - ML dataset GUI & training studio
  - Python ESP32 serial collector
  - Automated diagnostic test suite
"""

import os
import sys
import time
import json
import queue
import glob
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "ble-indoor-positioning")
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")

# Fallback to sys.executable if virtualenv python isn't found
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

class ControlCenterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ BLE Tracker Studio — Control Center")
        self.root.geometry("1100x820")
        self.root.minsize(1000, 720)

        # Threading Log Queue
        self.log_queue = queue.Queue()

        # Active Subprocesses
        self.processes = {
            "backend": None,
            "dashboard": None,
            "collector": None,
            "training_gui": None
        }

        # Colors (Warm Dark / Catppuccin-inspired Dark Theme)
        self.colors = {
            "bg": "#1e1e2e",
            "panel": "#181825",
            "card": "#313244",
            "accent": "#89b4fa",
            "green": "#a6e3a1",
            "yellow": "#f9e2af",
            "red": "#f38ba8",
            "purple": "#cba6f7",
            "text": "#cdd6f4",
            "subtext": "#a6adc8",
        }

        self.setup_styles()
        self.build_ui()

        # Start periodic GUI refresh loops
        self.root.after(100, self.process_queue_logs)
        self.root.after(1000, self.update_process_states)
        self.root.after(1000, self.refresh_diagnostics)

        # Cleanup subprocesses on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        self.root.configure(bg=self.colors["bg"])

        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["panel"], foreground=self.colors["text"], padding=[15, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.colors["card"])], foreground=[("selected", self.colors["accent"])])

        style.configure("Card.TFrame", background=self.colors["card"], relief="flat", borderwidth=1)
        style.configure("Panel.TFrame", background=self.colors["panel"])

        # Headings & Text
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.colors["accent"], background=self.colors["bg"])
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.colors["purple"], background=self.colors["card"])
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.colors["text"], background=self.colors["card"])
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground=self.colors["subtext"], background=self.colors["card"])

        # Buttons
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["accent"], foreground="#11111b", padding=[12, 6])
        style.map("Primary.TButton", background=[("active", "#b4befe")])

        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["red"], foreground="#11111b", padding=[12, 6])
        style.map("Danger.TButton", background=[("active", "#f5c2e7")])

        style.configure("Success.TButton", font=("Segoe UI", 9, "bold"), background=self.colors["green"], foreground="#11111b", padding=[8, 4])
        style.map("Success.TButton", background=[("active", "#a6e3a1")])

    def build_ui(self):
        # 1. Header Banner
        header = ttk.Frame(self.root, padding=(20, 15))
        header.pack(fill="x")
        ttk.Label(header, text="⚡ BLE Tracker & Indoor Positioning Studio", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="Central Control Desk", font=("Segoe UI", 11, "italic"), foreground=self.colors["purple"]).pack(side="right")

        # 2. Main Grid Layout
        main_frame = ttk.Frame(self.root, padding=(15, 0, 15, 15))
        main_frame.pack(fill="both", expand=True)

        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 15))

        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side="right", fill="both", expand=True)

        # ──────────────────────────────────────────────────────────────────
        # LEFT PANE: SERVICE MANAGEMENT PANELS
        # ──────────────────────────────────────────────────────────────────

        # A. Backend localization Server
        backend_card = ttk.Frame(left_pane, style="Card.TFrame", padding=15)
        backend_card.pack(fill="x", pady=(0, 15))
        
        ttk.Label(backend_card, text="🔌 Real-Time Inference Backend Server", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(backend_card, text="FastAPI server that receives Bluetooth packets and performs trilateration.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        btn_row = ttk.Frame(backend_card, style="Card.TFrame")
        btn_row.pack(fill="x")
        
        self.btn_start_backend = ttk.Button(btn_row, text="Start Backend", style="Primary.TButton", command=self.start_backend)
        self.btn_start_backend.pack(side="left", padx=(0, 10))
        
        self.btn_stop_backend = ttk.Button(btn_row, text="Stop Backend", style="Danger.TButton", command=self.stop_backend, state="disabled")
        self.btn_stop_backend.pack(side="left")

        self.lbl_backend_status = ttk.Label(btn_row, text="OFFLINE", font=("Segoe UI", 10, "bold"), foreground=self.colors["red"], background=self.colors["card"])
        self.lbl_backend_status.pack(side="right", padx=10)

        # B. Streamlit Live Tracking Dashboard
        dashboard_card = ttk.Frame(left_pane, style="Card.TFrame", padding=15)
        dashboard_card.pack(fill="x", pady=(0, 15))

        ttk.Label(dashboard_card, text="🗺️ Real-Time Streamlit Tracking Dashboard", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(dashboard_card, text="Displays the smoothed Kalman filtered path & coordinate map in browser.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        dash_btn_row = ttk.Frame(dashboard_card, style="Card.TFrame")
        dash_btn_row.pack(fill="x")

        self.btn_start_dash = ttk.Button(dash_btn_row, text="Launch Dashboard", style="Primary.TButton", command=self.start_dashboard)
        self.btn_start_dash.pack(side="left", padx=(0, 10))

        self.btn_stop_dash = ttk.Button(dash_btn_row, text="Stop Dashboard", style="Danger.TButton", command=self.stop_dashboard, state="disabled")
        self.btn_stop_dash.pack(side="left")

        self.lbl_dash_status = ttk.Label(dash_btn_row, text="OFFLINE", font=("Segoe UI", 10, "bold"), foreground=self.colors["red"], background=self.colors["card"])
        self.lbl_dash_status.pack(side="right", padx=10)

        # C. ML Training Studio (GUI)
        trainer_card = ttk.Frame(left_pane, style="Card.TFrame", padding=15)
        trainer_card.pack(fill="x", pady=(0, 15))

        ttk.Label(trainer_card, text="🚀 ML Dataset & Automated Training Studio", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(trainer_card, text="Visual UI for raw data audit, model training, and diagnostic evaluation.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        self.btn_launch_trainer = ttk.Button(trainer_card, text="Launch Training Studio GUI", style="Primary.TButton", command=self.launch_training_gui)
        self.btn_launch_trainer.pack(anchor="w")

        # D. ESP32 Python Serial Ingestion Collector
        collector_card = ttk.Frame(left_pane, style="Card.TFrame", padding=15)
        collector_card.pack(fill="x")

        ttk.Label(collector_card, text="📡 ESP32 Serial Data Telemetry Collector", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(collector_card, text="Read live signals from ESP32 anchor COM ports and write to datasets.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        coll_btn_row = ttk.Frame(collector_card, style="Card.TFrame")
        coll_btn_row.pack(fill="x")

        self.btn_start_collector = ttk.Button(coll_btn_row, text="Start Collector", style="Primary.TButton", command=self.start_collector)
        self.btn_start_collector.pack(side="left", padx=(0, 10))

        self.btn_stop_collector = ttk.Button(coll_btn_row, text="Stop Collector", style="Danger.TButton", command=self.stop_collector, state="disabled")
        self.btn_stop_collector.pack(side="left")

        self.lbl_coll_status = ttk.Label(coll_btn_row, text="OFFLINE", font=("Segoe UI", 10, "bold"), foreground=self.colors["red"], background=self.colors["card"])
        self.lbl_coll_status.pack(side="right", padx=10)

        # ──────────────────────────────────────────────────────────────────
        # RIGHT PANE: REAL-TIME CONSOLE LOGS & WORKSPACE DIAGNOSTICS
        # ──────────────────────────────────────────────────────────────────

        # A. Diagnostic Panel
        diag_card = ttk.Frame(right_pane, style="Card.TFrame", padding=15)
        diag_card.pack(fill="x", pady=(0, 15))

        ttk.Label(diag_card, text="📊 Workspace Integrity Diagnostics", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))

        diag_grid = ttk.Frame(diag_card, style="Card.TFrame")
        diag_grid.pack(fill="x")

        self.lbl_diag_model = ttk.Label(diag_grid, text="Champion Model: Checking...", style="Bold.TLabel")
        self.lbl_diag_model.grid(row=0, column=0, sticky="w", pady=2)
        
        self.lbl_diag_dataset = ttk.Label(diag_grid, text="Observations Dataset: Checking...", style="Bold.TLabel")
        self.lbl_diag_dataset.grid(row=1, column=0, sticky="w", pady=2)

        self.lbl_diag_tests = ttk.Label(diag_grid, text="Automated Tests Status: Checking...", style="Bold.TLabel")
        self.lbl_diag_tests.grid(row=2, column=0, sticky="w", pady=2)

        test_btn_row = ttk.Frame(diag_card, style="Card.TFrame")
        test_btn_row.pack(fill="x", pady=(10, 0))
        
        ttk.Button(test_btn_row, text="Run Diagnostic Test Suite", style="Success.TButton", command=self.run_tests).pack(side="left")
        ttk.Button(test_btn_row, text="Clean Log Console", style="Success.TButton", command=self.clear_console).pack(side="right")

        # B. Log Terminal Console Screen
        log_card = ttk.Frame(right_pane, style="Card.TFrame", padding=15)
        log_card.pack(fill="both", expand=True)

        ttk.Label(log_card, text="📋 Central Logs Terminal Console", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        self.console = tk.Text(
            log_card,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=("Consolas", 9),
            relief="flat",
            wrap="word"
        )
        self.console.pack(fill="both", expand=True)

    # ──────────────────────────────────────────────────────────────────
    # SERVICE LAUNCHERS & STOPPERS
    # ──────────────────────────────────────────────────────────────────

    def run_process_in_thread(self, name: str, command: list, cwd: str):
        """Helper to run command in background and redirect output to logs console."""
        def worker():
            try:
                self.log_queue.put(f"[SYSTEM] Starting process '{name}'...\n")
                
                # Start process with stdout/stderr piped
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd
                )
                self.processes[name] = proc

                # Stream lines into log console
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        self.log_queue.put(f"[{name.upper()}] {line}")

                proc.wait()
                self.log_queue.put(f"[SYSTEM] Process '{name}' finished with exit code {proc.returncode}.\n")
            except Exception as e:
                self.log_queue.put(f"[SYSTEM ERROR] Failed running '{name}': {e}\n")
            finally:
                self.processes[name] = None
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def start_backend(self):
        if self.processes["backend"] is not None:
            return
        
        server_script = os.path.join(PROJECT_ROOT, "server", "app.py")
        cmd = [VENV_PYTHON, server_script]
        self.run_process_in_thread("backend", cmd, os.path.join(PROJECT_ROOT, "server"))

    def stop_backend(self):
        proc = self.processes["backend"]
        if proc:
            proc.terminate()
            self.log_queue.put("[SYSTEM] Sent terminate command to Backend.\n")

    def start_dashboard(self):
        if self.processes["dashboard"] is not None:
            return

        # Run streamlit from virtualenv script folder
        dash_script = os.path.join(PROJECT_ROOT, "dashboard", "app.py")
        streamlit_exe = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "streamlit.exe")
        
        if os.path.exists(streamlit_exe):
            cmd = [streamlit_exe, "run", dash_script]
        else:
            cmd = [VENV_PYTHON, "-m", "streamlit", "run", dash_script]
            
        self.run_process_in_thread("dashboard", cmd, PROJECT_ROOT)

    def stop_dashboard(self):
        proc = self.processes["dashboard"]
        if proc:
            proc.terminate()
            self.log_queue.put("[SYSTEM] Sent terminate command to Streamlit Dashboard.\n")

    def launch_training_gui(self):
        if self.processes["training_gui"] is not None:
            return
        
        script = os.path.join(PROJECT_ROOT, "training_gui.py")
        cmd = [VENV_PYTHON, script]
        self.run_process_in_thread("training_gui", cmd, PROJECT_ROOT)

    def start_collector(self):
        if self.processes["collector"] is not None:
            return

        script = os.path.join(PROJECT_ROOT, "collector", "collector.py")
        # Run in standard input emulation mode
        cmd = [VENV_PYTHON, script, "--port", "stdin"]
        self.run_process_in_thread("collector", cmd, PROJECT_ROOT)

    def stop_collector(self):
        proc = self.processes["collector"]
        if proc:
            proc.terminate()
            self.log_queue.put("[SYSTEM] Sent terminate command to Serial Collector.\n")

    def run_tests(self):
        """Runs the pytest suite in a background thread and streams results to the console."""
        def worker():
            self.log_queue.put("[SYSTEM] Initiating diagnostic test suite (pytest)...\n")
            try:
                proc = subprocess.Popen(
                    [VENV_PYTHON, "-m", "pytest"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        self.log_queue.put(f"[TESTS] {line}")
                proc.wait()
                if proc.returncode == 0:
                    self.log_queue.put("[SYSTEM] Tests finished successfully! ✅\n")
                else:
                    self.log_queue.put(f"[SYSTEM] Tests completed with failures (Exit code {proc.returncode}). ❌\n")
            except Exception as e:
                self.log_queue.put(f"[SYSTEM ERROR] Failed running tests: {e}\n")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    # ──────────────────────────────────────────────────────────────────
    # BACKGROUND GUI MONITORING & DIAGNOSTICS LOOPS
    # ──────────────────────────────────────────────────────────────────

    def process_queue_logs(self):
        """Reads log queue messages and appends them to log viewer console."""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.console.insert(tk.END, msg)
                self.console.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.process_queue_logs)

    def update_process_states(self):
        """Checks subprocesses health and updates status labels."""
        # 1. Backend Status
        if self.processes["backend"] is not None:
            self.lbl_backend_status.config(text="RUNNING", foreground=self.colors["green"])
            self.btn_start_backend.config(state="disabled")
            self.btn_stop_backend.config(state="normal")
        else:
            self.lbl_backend_status.config(text="OFFLINE", foreground=self.colors["red"])
            self.btn_start_backend.config(state="normal")
            self.btn_stop_backend.config(state="disabled")

        # 2. Streamlit Dashboard Status
        if self.processes["dashboard"] is not None:
            self.lbl_dash_status.config(text="RUNNING", foreground=self.colors["green"])
            self.btn_start_dash.config(state="disabled")
            self.btn_stop_dash.config(state="normal")
        else:
            self.lbl_dash_status.config(text="OFFLINE", foreground=self.colors["red"])
            self.btn_start_dash.config(state="normal")
            self.btn_stop_dash.config(state="disabled")

        # 3. Collector Status
        if self.processes["collector"] is not None:
            self.lbl_coll_status.config(text="RUNNING", foreground=self.colors["green"])
            self.btn_start_collector.config(state="disabled")
            self.btn_stop_collector.config(state="normal")
        else:
            self.lbl_coll_status.config(text="OFFLINE", foreground=self.colors["red"])
            self.btn_start_collector.config(state="normal")
            self.btn_stop_collector.config(state="disabled")

        self.root.after(500, self.update_process_states)

    def refresh_diagnostics(self):
        """Scans project folder for models and datasets to verify setup integrity."""
        # 1. Verify Model Meta
        meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                self.lbl_diag_model.config(
                    text=f"Champion Model: {meta.get('champion_model', 'Ensemble')} (MAE: {meta.get('metrics', {}).get('test_mae', '--')}m)",
                    foreground=self.colors["green"]
                )
            except Exception:
                self.lbl_diag_model.config(text="Champion Model: Corrupt Metadata", foreground=self.colors["yellow"])
        else:
            self.lbl_diag_model.config(text="Champion Model: Missing (Run training studio!)", foreground=self.colors["red"])

        # 2. Verify dataset
        dataset_path = os.path.join(PROJECT_ROOT, "datasets", "observations.csv")
        if os.path.exists(dataset_path):
            try:
                lines_count = sum(1 for _ in open(dataset_path)) - 1
                self.lbl_diag_dataset.config(
                    text=f"Observations Dataset: Found ({lines_count} windows)",
                    foreground=self.colors["green"]
                )
            except Exception:
                self.lbl_diag_dataset.config(text="Observations Dataset: Unreadable", foreground=self.colors["yellow"])
        else:
            self.lbl_diag_dataset.config(text="Observations Dataset: Missing", foreground=self.colors["red"])

        # 3. Verify tests status
        self.lbl_diag_tests.config(text="Test Suite: Ready (Click run test suite)", foreground=self.colors["purple"])

        self.root.after(3000, self.refresh_diagnostics)

    def clear_console(self):
        self.console.delete("1.0", tk.END)

    def on_close(self):
        """Terminates all running subprocesses before exiting application."""
        active = [name for name, proc in self.processes.items() if proc is not None]
        if active:
            if not messagebox.askyesno("Exit Control Center?", f"Active services are running: {', '.join(active)}.\nTerminate services and exit?"):
                return
            
            for name, proc in self.processes.items():
                if proc:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ControlCenterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
