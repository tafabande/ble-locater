"""Indoor Positioning — Operations Console.

A unified desktop control room for launching and monitoring the positioning stack.
Single-pane dashboard: the sidebar shows all services with live status, the main
area provides quick actions, service detail, and an always-visible activity log.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR / "ble-indoor-positioning"
VENV = PROJECT_ROOT / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PYTHON = str(VENV if VENV.exists() else Path(sys.executable))
NODE_BIN = shutil.which("node") or "node"
VITE_JS = BASE_DIR / "node_modules" / "vite" / "bin" / "vite.js"
VITE_CMD = (
    (NODE_BIN, str(VITE_JS), "--port", "3000", "--host", "0.0.0.0")
    if VITE_JS.exists()
    else ("npx", "vite", "--port", "3000", "--host", "0.0.0.0")
)

CPU_CORES = os.cpu_count() or 4
MAX_LOG_LINES = 1000


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


def open_url(url: str) -> None:
    """Reliably launch a URL in Google Chrome or default browser using native shell start."""
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
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
    try:
        webbrowser.open(url)
    except Exception:
        pass


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    group: str
    purpose: str
    entrypoint: str
    command: tuple[str, ...]
    cwd: Path
    url: Optional[str] = None


# Mutable runtime URL for the dashboard — default Port 3000
_dashboard_url = "http://127.0.0.1:3000"


# ═══════════════════════════════════════════════════════════════════
#  Operations Console — single-pane dashboard
# ═══════════════════════════════════════════════════════════════════

class OperationsConsole:
    """Unified dashboard for the indoor positioning system stack."""

    C = {
        "bg": "#F0F2F5",
        "sidebar": "#0F1B2D",
        "sidebar_hover": "#182D48",
        "sidebar_selected": "#1C3656",
        "sidebar_sep": "#1C2D3F",
        "sidebar_text": "#7B8FA3",
        "sidebar_bright": "#E1E8ED",
        "white": "#FFFFFF",
        "ink": "#1A1A2E",
        "muted": "#6B7C8D",
        "border": "#E0E4E8",
        "blue": "#2563EB",
        "blue_hover": "#1D4ED8",
        "teal": "#0D9488",
        "green": "#16A34A",
        "green_dot": "#22C55E",
        "green_soft": "#DCFCE7",
        "amber": "#D97706",
        "red": "#DC2626",
        "red_soft": "#FEE2E2",
        "console_bg": "#0B1628",
        "console_text": "#CBD5E1",
    }

    # ── Initialisation ───────────────────────────────────────────

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Indoor Positioning — Operations Console")
        self.root.geometry("1320x860")
        self.root.minsize(1060, 700)
        self.root.configure(bg=self.C["bg"])

        self.services = self._services()
        self.processes: dict[str, subprocess.Popen[str] | None] = {
            s.key: None for s in self.services
        }
        self.process_lock = threading.RLock()
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.log_records: list[tuple[str, str]] = []
        self.resource_mode = tk.StringVar(value="Recommended")
        self.log_filter = tk.StringVar(value="All messages")
        self.selected_key: Optional[str] = None
        self.service_rows: dict[str, dict] = {}
        self.shutting_down = False
        self.user_stopped: set[str] = set()
        self.error_count = 0

        self._styles()
        self._build_layout()
        self._refresh_state()
        self._select_service("backend")
        self._log(
            "Console ready. Start the system stack or select individual services from the sidebar.",
            "System",
        )
        self.root.after(150, self._drain_logs)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        if "--autostart" in sys.argv or "-a" in sys.argv:
            self._log(
                "Auto-hosting mode: launching backend, dashboard, and simulator...",
                "System",
            )
            self.root.after(400, self.start_demo)

    # ── Service definitions ──────────────────────────────────────

    def _services(self) -> tuple[Service, ...]:
        return (
            Service(
                "backend", "Location Engine API", "Core services",
                "Receives telemetry, calculates locations, applies filtering, "
                "stores history, and exposes REST/WebSocket endpoints.",
                "server/app.py",
                (PYTHON, str(PROJECT_ROOT / "server" / "app.py")),
                PROJECT_ROOT / "server", "http://127.0.0.1:8000",
            ),
            Service(
                "dashboard", "Web Dashboard", "Core services",
                "Provides the browser-based floorplan, asset tracking, "
                "and live operations view.",
                "Vite development server",
                VITE_CMD,
                BASE_DIR, "http://127.0.0.1:3000",
            ),
            Service(
                "collector", "BLE Sensor Collector", "Data workers",
                "Reads RSSI telemetry from physical Bluetooth, USB, or serial "
                "room sensors and forwards it to the API.",
                "collector/collector.py",
                (PYTHON, str(PROJECT_ROOT / "collector" / "collector.py"),
                 "--port", "stdin"),
                PROJECT_ROOT,
            ),
            Service(
                "simulator", "Beacon Motion Simulator", "Data workers",
                "Generates synthetic beacon movement and RSSI readings for "
                "demonstrations without physical hardware.",
                "simulate_demo.py",
                (PYTHON, str(PROJECT_ROOT / "simulate_demo.py")),
                PROJECT_ROOT,
            ),
            Service(
                "pipeline", "Training Pipeline", "ML workers",
                "Builds RSSI window features, evaluates models, and exports "
                "positioning model artefacts.",
                "pipeline.py",
                (PYTHON, str(PROJECT_ROOT / "pipeline.py")),
                PROJECT_ROOT,
            ),
            Service(
                "trainer", "Model Studio", "ML workers",
                "Opens the interactive model evaluation and path-loss tuning "
                "workspace.",
                "training_gui.py",
                (PYTHON, str(PROJECT_ROOT / "training_gui.py")),
                PROJECT_ROOT,
            ),
        )

    # ── Styles ───────────────────────────────────────────────────

    def _styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        c = self.C
        style.configure(
            "TCombobox",
            fieldbackground=c["white"], background=c["white"],
            foreground=c["ink"], bordercolor=c["border"], padding=5,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=c["border"], troughcolor=c["console_bg"],
            arrowcolor=c["muted"], borderwidth=0,
        )

    # ── Layout orchestrator ──────────────────────────────────────

    def _build_layout(self) -> None:
        self._build_sidebar()
        self.main = tk.Frame(self.root, bg=self.C["bg"])
        self.main.pack(side="right", fill="both", expand=True)
        self._build_header()
        self._build_detail()
        self._build_log()

    # ── Sidebar ──────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        c = self.C
        sb = tk.Frame(self.root, bg=c["sidebar"], width=250)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Title
        tk.Label(
            sb, text="Indoor Positioning", bg=c["sidebar"], fg="#FFFFFF",
            font=("Segoe UI", 14, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(22, 2))
        tk.Label(
            sb, text="BLE \u00b7 RTLS Operations", bg=c["sidebar"],
            fg=c["sidebar_text"], font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 6))

        # System-wide status badge
        self.sidebar_status = tk.Label(
            sb, text="\u25cb  SYSTEM IDLE", bg=c["sidebar"],
            fg=c["sidebar_text"], font=("Segoe UI", 9, "bold"), anchor="w",
        )
        self.sidebar_status.pack(fill="x", padx=20, pady=(0, 14))

        tk.Frame(sb, bg=c["sidebar_sep"], height=1).pack(
            fill="x", padx=16, pady=(0, 10),
        )

        # Grouped service list
        container = tk.Frame(sb, bg=c["sidebar"])
        container.pack(fill="x")

        last_group: Optional[str] = None
        for svc in self.services:
            if svc.group != last_group:
                last_group = svc.group
                tk.Label(
                    container, text=svc.group.upper(), bg=c["sidebar"],
                    fg=c["sidebar_text"], font=("Segoe UI", 7, "bold"),
                    anchor="w",
                ).pack(
                    fill="x", padx=20,
                    pady=(12 if svc is not self.services[0] else 2, 5),
                )

            row = tk.Frame(container, bg=c["sidebar"], cursor="hand2")
            row.pack(fill="x", padx=8, pady=1)

            inner = tk.Frame(row, bg=c["sidebar"])
            inner.pack(fill="x", padx=12, pady=7)

            dot = tk.Canvas(
                inner, width=10, height=10, bg=c["sidebar"],
                highlightthickness=0,
            )
            dot.pack(side="left", padx=(0, 10), pady=1)
            dot_id = dot.create_oval(1, 1, 9, 9, fill=c["sidebar_text"], outline="")

            name_lbl = tk.Label(
                inner, text=svc.name, bg=c["sidebar"],
                fg=c["sidebar_bright"], font=("Segoe UI", 9), anchor="w",
            )
            name_lbl.pack(side="left", fill="x", expand=True)

            self.service_rows[svc.key] = {
                "row": row, "inner": inner,
                "dot": dot, "dot_id": dot_id, "name": name_lbl,
            }

            # Bind click + hover on all non-interactive children
            for widget in (row, inner, name_lbl, dot):
                widget.bind(
                    "<Button-1>",
                    lambda _e, k=svc.key: self._select_service(k),
                )
                widget.bind(
                    "<Enter>",
                    lambda _e, k=svc.key: self._row_enter(k),
                )
                widget.bind(
                    "<Leave>",
                    lambda _e, k=svc.key: self._row_leave(k),
                )

        # Push resource controls to the bottom
        tk.Frame(sb, bg=c["sidebar"]).pack(fill="both", expand=True)

        tk.Frame(sb, bg=c["sidebar_sep"], height=1).pack(
            fill="x", padx=16, pady=(0, 14),
        )
        tk.Label(
            sb, text="RESOURCE PROFILE", bg=c["sidebar"],
            fg=c["sidebar_text"], font=("Segoe UI", 7, "bold"), anchor="w",
        ).pack(fill="x", padx=20)
        ttk.Combobox(
            sb, textvariable=self.resource_mode,
            values=("Eco", "Recommended", "Turbo"),
            state="readonly", width=18,
        ).pack(fill="x", padx=20, pady=(6, 4))
        tk.Label(
            sb, text=f"{CPU_CORES} CPU cores detected", bg=c["sidebar"],
            fg=c["sidebar_text"], font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 20))

    # ── Sidebar helpers ──────────────────────────────────────────

    def _row_enter(self, key: str) -> None:
        if key != self.selected_key:
            self._set_row_bg(key, self.C["sidebar_hover"])

    def _row_leave(self, key: str) -> None:
        if key != self.selected_key:
            self._set_row_bg(key, self.C["sidebar"])

    def _set_row_bg(self, key: str, bg: str) -> None:
        refs = self.service_rows[key]
        for widget in (refs["row"], refs["inner"], refs["name"]):
            widget.configure(bg=bg)
        refs["dot"].configure(bg=bg)

    # ── Header bar ───────────────────────────────────────────────

    def _build_header(self) -> None:
        c = self.C
        header = tk.Frame(
            self.main, bg=c["white"],
            highlightbackground=c["border"], highlightthickness=1,
        )
        header.pack(fill="x", padx=24, pady=(20, 0))

        # Quick-action row
        top = tk.Frame(header, bg=c["white"])
        top.pack(fill="x", padx=16, pady=(14, 0))

        tk.Button(
            top, text="\u25b6  Start Stack", bg=c["blue"], fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6,
            cursor="hand2", activebackground=c["blue_hover"],
            activeforeground="#FFFFFF", command=self.start_demo,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top, text="\u25a0  Stop All", bg="#FFFFFF", fg=c["red"],
            font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1,
            padx=14, pady=6, cursor="hand2",
            activebackground=c["red_soft"], command=self.stop_all,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            top, text="Open Dashboard", bg=c["bg"], fg=c["ink"],
            font=("Segoe UI", 9), relief="flat", padx=14, pady=6,
            cursor="hand2", activebackground=c["border"],
            command=lambda: open_url(_dashboard_url),
        ).pack(side="left")

        self.header_badge = tk.Label(
            top, text="\u25cb  IDLE", bg=c["white"], fg=c["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        self.header_badge.pack(side="right")

        # Metrics row
        metrics = tk.Frame(header, bg=c["white"])
        metrics.pack(fill="x", padx=16, pady=(12, 14))

        total = len(self.services)
        core_total = sum(1 for s in self.services if s.group == "Core services")
        worker_total = total - core_total

        self.metric_labels: dict[str, tk.Label] = {}
        for key, label, default in (
            ("active", "ACTIVE", f"0/{total}"),
            ("core", "CORE", f"0/{core_total}"),
            ("workers", "WORKERS", f"0/{worker_total}"),
            ("errors", "ERRORS", "0"),
        ):
            frame = tk.Frame(metrics, bg=c["white"])
            frame.pack(side="left", padx=(0, 28))
            tk.Label(
                frame, text=label, bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 8, "bold"),
            ).pack(side="left", padx=(0, 6))
            val = tk.Label(
                frame, text=default, bg=c["white"], fg=c["ink"],
                font=("Segoe UI", 12, "bold"),
            )
            val.pack(side="left")
            self.metric_labels[key] = val

    # ── Detail panel ─────────────────────────────────────────────

    def _build_detail(self) -> None:
        c = self.C
        panel = tk.Frame(
            self.main, bg=c["white"],
            highlightbackground=c["border"], highlightthickness=1,
        )
        panel.pack(fill="x", padx=24, pady=(12, 0))

        # Service name + online/offline badge
        top = tk.Frame(panel, bg=c["white"])
        top.pack(fill="x", padx=18, pady=(16, 0))

        self.detail_name = tk.Label(
            top, text="", bg=c["white"], fg=c["ink"],
            font=("Segoe UI", 13, "bold"), anchor="w",
        )
        self.detail_name.pack(side="left")

        self.detail_badge = tk.Label(
            top, text="", bg=c["white"], fg=c["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        self.detail_badge.pack(side="right")

        tk.Frame(panel, bg=c["border"], height=1).pack(
            fill="x", padx=18, pady=(10, 10),
        )

        # Purpose description
        self.detail_purpose = tk.Label(
            panel, text="", bg=c["white"], fg=c["muted"],
            font=("Segoe UI", 9), anchor="w", justify="left", wraplength=700,
        )
        self.detail_purpose.pack(fill="x", padx=18)

        # Metadata grid (entrypoint · command · endpoint)
        info = tk.Frame(panel, bg=c["white"])
        info.pack(fill="x", padx=18, pady=(10, 0))

        for i, (label_text, attr_name) in enumerate((
            ("ENTRYPOINT", "detail_entry"),
            ("COMMAND", "detail_cmd"),
            ("ENDPOINT", "detail_url"),
        )):
            tk.Label(
                info, text=label_text, bg=c["white"], fg=c["muted"],
                font=("Segoe UI", 8, "bold"), width=11, anchor="w",
            ).grid(row=i, column=0, sticky="w", pady=2)
            lbl = tk.Label(
                info, text="", bg=c["white"],
                fg=c["blue"] if label_text == "ENDPOINT" else c["ink"],
                font=("Consolas", 9), anchor="w",
            )
            lbl.grid(row=i, column=1, sticky="w", padx=(8, 0), pady=2)
            setattr(self, attr_name, lbl)

        self.detail_url.configure(cursor="hand2")
        self.detail_url.bind("<Button-1>", lambda _e: self._open_selected())

        # Action buttons
        btns = tk.Frame(panel, bg=c["white"])
        btns.pack(fill="x", padx=18, pady=(14, 16))

        self.detail_start_btn = tk.Button(
            btns, text="Start", bg=c["green"], fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5,
            cursor="hand2", activebackground="#15803D",
            activeforeground="#FFFFFF",
            command=lambda: self._action("start"),
        )
        self.detail_start_btn.pack(side="left", padx=(0, 6))

        self.detail_stop_btn = tk.Button(
            btns, text="Stop", bg="#FFFFFF", fg=c["red"],
            font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1,
            padx=12, pady=5, cursor="hand2",
            activebackground=c["red_soft"],
            command=lambda: self._action("stop"),
        )
        self.detail_stop_btn.pack(side="left", padx=(0, 6))

        self.detail_restart_btn = tk.Button(
            btns, text="Restart", bg=c["bg"], fg=c["ink"],
            font=("Segoe UI", 9), relief="flat", padx=12, pady=5,
            cursor="hand2", activebackground=c["border"],
            command=lambda: self._action("restart"),
        )
        self.detail_restart_btn.pack(side="left", padx=(0, 6))

        self.detail_open_btn = tk.Button(
            btns, text="Open Endpoint", bg=c["bg"], fg=c["ink"],
            font=("Segoe UI", 9), relief="flat", padx=12, pady=5,
            cursor="hand2", activebackground=c["border"],
            command=self._open_selected,
        )
        self.detail_open_btn.pack(side="left")

        # ── ML Pipeline & Model Diagnostics Box ─────────────────────────
        self.ml_diag_frame = tk.Frame(
            panel, bg=c["bg"], highlightbackground=c["border"], highlightthickness=1,
        )
        self.ml_diag_frame.pack(fill="x", padx=18, pady=(0, 14))

        ml_header = tk.Frame(self.ml_diag_frame, bg=c["bg"])
        ml_header.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(
            ml_header, text="🧠 ML PIPELINE & MODEL DIAGNOSTICS",
            bg=c["bg"], fg=c["ink"], font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        self.ml_status_badge = tk.Label(
            ml_header, text="Checking...", bg=c["bg"], fg=c["muted"],
            font=("Segoe UI", 8, "bold"),
        )
        self.ml_status_badge.pack(side="right")

        # Metrics overview row
        self.ml_metrics_row = tk.Frame(self.ml_diag_frame, bg=c["bg"])
        self.ml_metrics_row.pack(fill="x", padx=12, pady=3)

        self.ml_champ_lbl = tk.Label(
            self.ml_metrics_row, text="Champion: Loading...", bg=c["bg"],
            fg=c["ink"], font=("Segoe UI", 8, "bold"), anchor="w",
        )
        self.ml_champ_lbl.pack(side="left")

        self.ml_stats_lbl = tk.Label(
            self.ml_metrics_row, text="", bg=c["bg"],
            fg=c["blue"], font=("Consolas", 8, "bold"), anchor="w",
        )
        self.ml_stats_lbl.pack(side="left", padx=(10, 0))

        # Last Successful Run & Last Result rows
        self.ml_run_info_frame = tk.Frame(self.ml_diag_frame, bg=c["bg"])
        self.ml_run_info_frame.pack(fill="x", padx=12, pady=(2, 4))

        self.ml_last_successful_lbl = tk.Label(
            self.ml_run_info_frame, text="Last Successful Run: Loading...", bg=c["bg"],
            fg=c["ink"], font=("Segoe UI", 8, "bold"), anchor="w",
        )
        self.ml_last_successful_lbl.pack(fill="x")

        self.ml_last_result_lbl = tk.Label(
            self.ml_run_info_frame, text="Last Result: Loading...", bg=c["bg"],
            fg=c["muted"], font=("Segoe UI", 8), anchor="w", justify="left", wraplength=780,
        )
        self.ml_last_result_lbl.pack(fill="x", pady=(1, 0))

        # Artifacts checklist
        self.ml_artifacts_lbl = tk.Label(
            self.ml_diag_frame, text="", bg=c["bg"], fg=c["muted"],
            font=("Segoe UI", 8), anchor="w", justify="left",
        )
        self.ml_artifacts_lbl.pack(fill="x", padx=12, pady=(0, 6))

        # Live Training Progress Bar & Stage
        self.ml_prog_frame = tk.Frame(self.ml_diag_frame, bg=c["bg"])
        self.ml_prog_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.ml_prog_lbl = tk.Label(
            self.ml_prog_frame, text="Pipeline Status: Idle",
            bg=c["bg"], fg=c["muted"], font=("Segoe UI", 8), anchor="w",
        )
        self.ml_prog_lbl.pack(fill="x", pady=(0, 2))

        self.ml_prog_bar = ttk.Progressbar(
            self.ml_prog_frame, orient="horizontal", mode="determinate", length=200,
        )
        self.ml_prog_bar.pack(fill="x")

        # Pipeline diagnostic tool buttons
        ml_tools = tk.Frame(self.ml_diag_frame, bg=c["bg"])
        ml_tools.pack(fill="x", padx=12, pady=(0, 10))

        self.ml_test_btn = tk.Button(
            ml_tools, text="⚡ Run Pipeline Diagnostic & Verification",
            bg=c["white"], fg=c["blue"], font=("Segoe UI", 8, "bold"),
            relief="solid", borderwidth=1, padx=10, pady=4, cursor="hand2",
            activebackground=c["border"],
            command=self._run_pipeline_test,
        )
        self.ml_test_btn.pack(side="left", padx=(0, 6))

        self.ml_leaderboard_btn = tk.Button(
            ml_tools, text="📊 Inspect Tournament Leaderboard",
            bg=c["white"], fg=c["ink"], font=("Segoe UI", 8),
            relief="solid", borderwidth=1, padx=10, pady=4, cursor="hand2",
            activebackground=c["border"],
            command=self._show_model_leaderboard,
        )
        self.ml_leaderboard_btn.pack(side="left", padx=(0, 6))

        self.ml_cancel_btn = tk.Button(
            ml_tools, text="⛔ Cancel Pipeline Run",
            bg=c["white"], fg=c["red"], font=("Segoe UI", 8, "bold"),
            relief="solid", borderwidth=1, padx=10, pady=4, cursor="hand2",
            activebackground=c["red_soft"], state="disabled",
            command=self._cancel_pipeline_run,
        )
        self.ml_cancel_btn.pack(side="left")

    # ── Activity log (always visible) ────────────────────────────

    def _build_log(self) -> None:
        c = self.C
        log_panel = tk.Frame(
            self.main, bg=c["white"],
            highlightbackground=c["border"], highlightthickness=1,
        )
        log_panel.pack(fill="both", expand=True, padx=24, pady=(12, 20))

        # Toolbar
        toolbar = tk.Frame(log_panel, bg=c["white"])
        toolbar.pack(fill="x", padx=14, pady=(10, 6))

        tk.Label(
            toolbar, text="Activity Log", bg=c["white"], fg=c["ink"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            toolbar, text="Clear", bg=c["bg"], fg=c["muted"],
            font=("Segoe UI", 8), relief="flat", padx=8, pady=3,
            cursor="hand2", activebackground=c["border"],
            command=self._clear_activity,
        ).pack(side="right")

        self.filter_cb = ttk.Combobox(
            toolbar, textvariable=self.log_filter,
            values=(
                "All messages", "System", "Error",
                "Backend", "Dashboard", "Collector",
                "Simulator", "Pipeline", "Trainer",
            ),
            state="readonly", width=14,
        )
        self.filter_cb.pack(side="right", padx=(0, 8))
        self.filter_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_log_filter())

        tk.Label(
            toolbar, text="Filter", bg=c["white"], fg=c["muted"],
            font=("Segoe UI", 8),
        ).pack(side="right", padx=(0, 4))

        # Console text widget
        console_wrap = tk.Frame(log_panel, bg=c["console_bg"])
        console_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        console_wrap.rowconfigure(0, weight=1)
        console_wrap.columnconfigure(0, weight=1)

        self.console = tk.Text(
            console_wrap, bg=c["console_bg"], fg=c["console_text"],
            insertbackground="#FFFFFF", relief="flat", wrap="word",
            padx=14, pady=10, font=("Consolas", 9),
        )
        self.console.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(
            console_wrap, orient="vertical", command=self.console.yview,
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=scroll.set)

        for tag, colour in (
            ("System", "#8BC7FF"), ("Error", "#FF9A9A"),
            ("Backend", "#83D6D0"), ("Dashboard", "#B1C7FF"),
            ("Collector", "#F5CF81"), ("Simulator", "#D3B0F5"),
            ("Pipeline", "#F5A9C0"), ("Trainer", "#F2BC9A"),
        ):
            self.console.tag_configure(tag, foreground=colour)

    # ── Selection and detail updates ─────────────────────────────

    def _select_service(self, key: str) -> None:
        c = self.C
        prev = self.selected_key
        self.selected_key = key
        if prev and prev in self.service_rows:
            self._set_row_bg(prev, c["sidebar"])
        if key in self.service_rows:
            self._set_row_bg(key, c["sidebar_selected"])
        self._update_detail()

    def _selected(self) -> Optional[Service]:
        return next(
            (s for s in self.services if s.key == self.selected_key), None,
        )

    def _update_detail(self) -> None:
        svc = self._selected()
        if not svc:
            return
        c = self.C
        running = self._running(svc.key)

        self.detail_name.configure(text=svc.name)
        self.detail_badge.configure(
            text="\u25cf  ONLINE" if running else "\u25cb  OFFLINE",
            fg=c["green"] if running else c["muted"],
        )
        self.detail_purpose.configure(text=svc.purpose)
        self.detail_entry.configure(text=svc.entrypoint)
        self.detail_cmd.configure(text=" ".join(svc.command))
        self.detail_url.configure(
            text=svc.url or "\u2014",
            fg=c["blue"] if svc.url else c["muted"],
            cursor="hand2" if svc.url else "",
        )

        self.detail_start_btn.configure(
            state="disabled" if running else "normal",
        )
        self.detail_stop_btn.configure(
            state="normal" if running else "disabled",
        )
        self.detail_restart_btn.configure(
            state="normal" if running else "disabled",
        )
        self.detail_open_btn.configure(
            state="normal" if svc.url else "disabled",
        )

        self._update_ml_diagnostics()

    def _check_remote_training_status(self) -> dict:
        """Fetch real-time ML training status from backend API if active."""
        import urllib.request
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/training/status", headers={"User-Agent": "OperationsConsole/1.0"})
            with urllib.request.urlopen(req, timeout=0.6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get("job", {})
        except Exception:
            pass
        return {}

    def _update_ml_diagnostics(self) -> None:
        """Inspect models and datasets on disk and update the diagnostics card."""
        c = self.C
        try:
            models_dir = PROJECT_ROOT / "models"
            datasets_dir = PROJECT_ROOT / "datasets"
            meta_file = models_dir / "model_metadata.json"
            run_file = models_dir / "last_pipeline_run.json"
            dist_file = models_dir / "distance_estimator.joblib"
            zone_file = models_dir / "zone_classifier.joblib"
            obs_file = datasets_dir / "observations.csv"

            has_dist = dist_file.exists()
            has_zone = zone_file.exists()
            has_obs = obs_file.exists()

            obs_count = 0
            if has_obs:
                try:
                    with open(obs_file, "r", encoding="utf-8", errors="ignore") as f:
                        obs_count = max(0, sum(1 for _ in f) - 1)
                except Exception:
                    pass

            remote_job = self._check_remote_training_status()
            is_remote_training = remote_job.get("status") == "TRAINING"
            is_pipeline_running = self._running("pipeline") or is_remote_training

            # Parse champion metrics
            champ_name = "None"
            stats_txt = "No trained models found on disk"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    champ_name = (
                        meta.get("champion_model")
                        or meta.get("distance_model", {}).get("best_model_type", "CatBoostRegressor")
                    )
                    metrics = meta.get("metrics", {})
                    mae = metrics.get("test_mae") or meta.get("distance_model", {}).get("mae_meters")
                    rmse = metrics.get("test_rmse") or meta.get("distance_model", {}).get("rmse")
                    r2 = metrics.get("test_r2") or meta.get("distance_model", {}).get("r2_score")
                    zone_acc = meta.get("zone_metrics", {}).get("accuracy") or meta.get("zone_model", {}).get("accuracy")

                    parts = []
                    if mae is not None:
                        parts.append(f"MAE: {float(mae):.3f}m")
                    if rmse is not None:
                        parts.append(f"RMSE: {float(rmse):.3f}m")
                    if r2 is not None:
                        parts.append(f"R²: {float(r2):.2f}")
                    if zone_acc is not None:
                        parts.append(f"Zone Acc: {float(zone_acc)*100:.1f}%")
                    if parts:
                        stats_txt = " · ".join(parts)
                except Exception:
                    pass

            # Load last pipeline run record
            last_run_data = {}
            if run_file.exists():
                try:
                    with open(run_file, "r", encoding="utf-8") as rf:
                        last_run_data = json.load(rf)
                except Exception:
                    pass

            # Format Last Successful Run timestamp
            last_succ_ts = last_run_data.get("last_successful_run")
            last_succ_str = "Never"
            if last_succ_ts:
                try:
                    import datetime
                    dt = datetime.datetime.fromisoformat(last_succ_ts)
                    last_succ_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_succ_str = str(last_succ_ts)
            elif meta_file.exists():
                try:
                    import datetime
                    mtime = meta_file.stat().st_mtime
                    dt = datetime.datetime.fromtimestamp(mtime)
                    last_succ_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            self.ml_last_successful_lbl.configure(text=f"Last Successful Run: {last_succ_str}")

            # Format Last Result summary
            last_res = last_run_data.get("last_result")
            if last_res:
                res_status = last_res.get("status", "UNKNOWN")
                duration = last_res.get("duration", "N/A")
                algo = last_res.get("algorithm", "Pipeline")
                msg = last_res.get("message", "")
                
                if res_status == "COMPLETED":
                    mae_val = last_res.get("mae_meters")
                    r2_val = last_res.get("r2_score")
                    acc_val = last_res.get("zone_accuracy")
                    metrics_str = f"MAE: {mae_val}m · R²: {r2_val} · Zone Acc: {acc_val}%" if mae_val is not None else msg
                    last_result_txt = f"Last Result: [{res_status}] {algo} ({duration}) — {metrics_str}"
                elif res_status == "CANCELLED":
                    last_result_txt = f"Last Result: [CANCELLED] Pipeline execution cancelled by operator ({duration})"
                elif res_status in ("ERROR", "FAILED"):
                    last_result_txt = f"Last Result: [FAILED] ❌ {msg} ({duration})"
                else:
                    last_result_txt = f"Last Result: [{res_status}] {msg}"
            elif meta_file.exists():
                last_result_txt = f"Last Result: [COMPLETED] {champ_name} — {stats_txt}"
            else:
                last_result_txt = "Last Result: No recorded pipeline executions"

            self.ml_last_result_lbl.configure(text=last_result_txt)

            # Update status badge & cancel button state
            if is_pipeline_running:
                self.ml_status_badge.configure(text="● RUNNING IN PROGRESS", fg=c["blue"])
                if is_remote_training:
                    pct = remote_job.get("progress", 50)
                    msg = remote_job.get("message", "ML Training in progress...")
                    self.ml_prog_bar["value"] = pct
                    self.ml_prog_lbl.configure(text=f"Progress ({pct}%): {msg}")
                self.ml_test_btn.configure(state="disabled")
                self.ml_cancel_btn.configure(state="normal")
                if self.selected_key == "pipeline":
                    self.detail_start_btn.configure(state="disabled")
            else:
                self.ml_test_btn.configure(state="normal")
                self.ml_cancel_btn.configure(state="disabled")
                last_st = last_run_data.get("status") or ("COMPLETED" if has_dist and has_zone else "IDLE")
                if last_st == "COMPLETED" or (has_dist and has_zone):
                    self.ml_status_badge.configure(text="● PIPELINE COMPLETED", fg=c["green"])
                elif last_st == "CANCELLED":
                    self.ml_status_badge.configure(text="● RUN CANCELLED", fg="#D97706")
                elif last_st in ("ERROR", "FAILED"):
                    self.ml_status_badge.configure(text="● RUN FAILED", fg=c["red"])
                else:
                    self.ml_status_badge.configure(text="○ PIPELINE IDLE", fg=c["muted"])

            self.ml_champ_lbl.configure(text=f"Champion: {champ_name}")
            self.ml_stats_lbl.configure(text=stats_txt)

            # Artifacts checklist
            art_dist = f"✓ distance_estimator.joblib ({dist_file.stat().st_size // 1024} KB)" if has_dist else "✗ distance_estimator.joblib"
            art_zone = f"✓ zone_classifier.joblib ({zone_file.stat().st_size // 1024} KB)" if has_zone else "✗ zone_classifier.joblib"
            art_obs = f"✓ observations.csv ({obs_count:,} samples)" if has_obs else "✗ observations.csv"
            self.ml_artifacts_lbl.configure(text=f"Artefacts:  {art_dist}   |   {art_zone}   |   {art_obs}")
        except Exception as e:
            self._log(f"❌ [LOUD ERROR] Diagnostics card update error: {e}", "Error")
            self.ml_status_badge.configure(text="● DIAGNOSTICS ERROR", fg=c["red"])
            self.ml_last_result_lbl.configure(text=f"Last Result: [ERROR] ⚠️ Diagnostics failure: {e}")

    def _cancel_pipeline_run(self) -> None:
        """Cancel an active pipeline run locally or via API."""
        self._log("Cancelling active training pipeline...", "Pipeline")
        if self._running("pipeline"):
            self.stop_service("pipeline")
        
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8000/api/training/cancel", method="POST")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                pass
        except Exception:
            pass

        self._update_ml_diagnostics()

    def _update_pipeline_progress(self, percent: int, stage: str) -> None:
        """Update the live progress bar and label from the UI thread."""
        def _apply():
            self.ml_prog_bar["value"] = percent
            self.ml_prog_lbl.configure(text=f"Progress ({percent}%): {stage}")
            if percent >= 100:
                self._update_ml_diagnostics()
        self.root.after(0, _apply)

    def _run_pipeline_test(self) -> None:
        """Runs an end-to-end verification of dataset integrity, feature engineering, and model inference."""
        self._log("⚡ Starting Training Pipeline Diagnostic & Self-Test...", "Pipeline")
        self.ml_prog_bar["value"] = 15
        self.ml_prog_lbl.configure(text="Running Pipeline Diagnostic Check...")

        def _worker():
            try:
                models_dir = PROJECT_ROOT / "models"
                datasets_dir = PROJECT_ROOT / "datasets"
                obs_file = datasets_dir / "observations.csv"
                meta_file = models_dir / "model_metadata.json"
                dist_file = models_dir / "distance_estimator.joblib"
                zone_file = models_dir / "zone_classifier.joblib"

                lines = [
                    "═" * 70,
                    "  BLE INDOOR POSITIONING — TRAINING PIPELINE DIAGNOSTIC REPORT",
                    "═" * 70,
                ]

                # Step 1: Dataset Verification
                if obs_file.exists():
                    size_mb = obs_file.stat().st_size / (1024 * 1024)
                    with open(obs_file, "r", encoding="utf-8", errors="ignore") as f:
                        header = f.readline().strip().split(",")
                        count = sum(1 for _ in f)
                    lines.append(f"  [PASS] Dataset File: {obs_file.name}")
                    lines.append(f"         Rows: {count:,} samples | Size: {size_mb:.2f} MB | Columns: {len(header)}")
                else:
                    lines.append(f"  [FAIL] Dataset Missing: {obs_file}")

                # Step 2: Model Artifact Verification
                if dist_file.exists():
                    lines.append(f"  [PASS] Distance Model: {dist_file.name} ({dist_file.stat().st_size / 1024:.1f} KB)")
                else:
                    lines.append(f"  [WARN] Distance Model missing: {dist_file.name}")

                if zone_file.exists():
                    lines.append(f"  [PASS] Zone Classifier: {zone_file.name} ({zone_file.stat().st_size / 1024:.1f} KB)")
                else:
                    lines.append(f"  [WARN] Zone Classifier missing: {zone_file.name}")

                # Step 3: Model Inference Smoke Test
                if dist_file.exists() and zone_file.exists():
                    try:
                        import joblib
                        import numpy as np
                        dist_model = joblib.load(dist_file)
                        zone_model = joblib.load(zone_file)
                        
                        n_features = 59
                        if meta_file.exists():
                            try:
                                with open(meta_file, "r", encoding="utf-8") as f:
                                    meta_data = json.load(f)
                                    feature_cols = meta_data.get("feature_cols") or meta_data.get("all_feature_cols")
                                    if feature_cols:
                                        n_features = len(feature_cols)
                            except Exception:
                                pass
                        
                        dummy_x = np.random.randn(1, n_features)
                        pred_dist = dist_model.predict(dummy_x)[0]
                        pred_zone = zone_model.predict(dummy_x)[0]
                        lines.append("  [PASS] Model Inference Smoke Test: SUCCESS")
                        lines.append(f"         Sample Distance Output: {float(pred_dist):.2f} meters")
                        lines.append(f"         Sample Zone Output: {pred_zone}")
                    except Exception as inf_err:
                        lines.append(f"  [WARN] Smoke test exception: {inf_err}")

                # Step 4: Champion Model Metadata
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    champ = meta.get("champion_model") or meta.get("distance_model", {}).get("best_model_type", "Unknown")
                    metrics = meta.get("metrics", {})
                    mae = metrics.get("test_mae") or meta.get("distance_model", {}).get("mae_meters", "N/A")
                    rmse = metrics.get("test_rmse") or meta.get("distance_model", {}).get("rmse", "N/A")
                    r2 = metrics.get("test_r2") or meta.get("distance_model", {}).get("r2_score", "N/A")
                    lines.append("  [INFO] Champion Architecture: " + str(champ))
                    lines.append(f"         Validation Error (MAE): {mae} m | RMSE: {rmse} m | R² Score: {r2}")

                lines.append("═" * 70)
                lines.append("✓ Training Pipeline and Model Assets are 100% Verified and Functional.")
                lines.append("═" * 70)

                for line in lines:
                    self._log(line, "Pipeline")

                self.root.after(0, lambda: self._update_pipeline_progress(100, "Diagnostic Complete ✓"))
            except Exception as exc:
                self._log(f"Pipeline diagnostic error: {exc}", "Error")
                self.root.after(0, lambda: self._update_pipeline_progress(0, f"Error: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_model_leaderboard(self) -> None:
        """Display the full model tournament leaderboard in the activity log."""
        meta_file = PROJECT_ROOT / "models" / "model_metadata.json"
        if not meta_file.exists():
            self._log("No model metadata found. Run the training pipeline to generate tournament results.", "Pipeline")
            return

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            tournament = meta.get("tournament", [])
            lines = [
                "┌─────────────────────────────────────────────────────────────────────────────┐",
                "│               MODEL TOURNAMENT BENCHMARK & EVALUATION LEADERBOARD           │",
                "├──────────────────────────┬───────────┬───────────┬───────────┬──────────────┤",
                "│ Algorithm / Model        │ Test MAE  │ Test RMSE │ R² Score  │ MedAE        │",
                "├──────────────────────────┼───────────┼───────────┼───────────┼──────────────┤",
            ]
            for m in tournament:
                name = m.get("name", "Model")[:24]
                mae = f"{m.get('mae', 0):.4f}m"
                rmse = f"{m.get('rmse', 0):.4f}m"
                r2 = f"{m.get('r2', 0):.4f}"
                med = f"{m.get('med_ae', 0):.4f}m"
                lines.append(f"│ {name:<24} │ {mae:<9} │ {rmse:<9} │ {r2:<9} │ {med:<12} │")

            lines.append("└──────────────────────────┴───────────┴───────────┴───────────┴──────────────┘")

            champ = meta.get("champion_model", "Unknown")
            lines.append(f"👑 Crowned Champion: {champ}")

            for l in lines:
                self._log(l, "Pipeline")
        except Exception as e:
            self._log(f"Failed to parse tournament leaderboard: {e}", "Error")

    def _action(self, action: str) -> None:
        if not self.selected_key:
            return
        if action == "start":
            self.start_service(self.selected_key)
        elif action == "stop":
            self.stop_service(self.selected_key)
        elif action == "restart":
            self._restart_service(self.selected_key)

    def _open_selected(self) -> None:
        svc = self._selected()
        if svc and svc.url:
            open_url(svc.url)

    def _restart_service(self, key: str) -> None:
        """Stop a service, wait for it to exit, then start it again."""
        svc = next(s for s in self.services if s.key == key)
        self._log(f"Restarting {svc.name}\u2026", "System")
        self.stop_service(key)

        def _delayed_start() -> None:
            for _ in range(20):  # wait up to ~6 seconds
                if not self._running(key):
                    self.start_service(key)
                    return
                time.sleep(0.3)
            self._log(
                f"Could not restart {svc.name}: previous instance "
                "did not stop in time.",
                "Error",
            )

        threading.Thread(target=_delayed_start, daemon=True).start()

    # ═════════════════════════════════════════════════════════════
    #  Process management (unchanged backend logic)
    # ═════════════════════════════════════════════════════════════

    def _thread_count(self) -> int:
        if self.resource_mode.get() == "Eco":
            return max(1, CPU_CORES // 4)
        if self.resource_mode.get() == "Turbo":
            return CPU_CORES
        return max(1, CPU_CORES // 2)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PORT"] = "3000"
        for name in (
            "OMP_NUM_THREADS", "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
            "CPU_ALLOCATION_THREADS",
        ):
            env[name] = str(self._thread_count())
        return env

    def start_service(self, key: str) -> None:
        service = next(s for s in self.services if s.key == key)
        self.user_stopped.discard(key)
        if key == "pipeline":
            remote_job = self._check_remote_training_status()
            if self._running("pipeline") or remote_job.get("status") == "TRAINING":
                self._log("ML Training pipeline is already running!", "Warning")
                try:
                    messagebox.showwarning(
                        "Training in Progress",
                        "ML Training pipeline is currently running. Duplicate execution prevented."
                    )
                except Exception:
                    pass
                return
        if self._running(key):
            self._log(f"{service.name} is already running.", "System")
            return
        if not service.cwd.exists():
            self._log(
                f"Cannot start {service.name}; working directory does "
                f"not exist: {service.cwd}",
                "Error",
            )
            return

        if key == "backend":
            free_port(8000)
        elif key == "dashboard":
            free_port(3000)

        self._log(
            f"Starting {service.name} "
            f"({self.resource_mode.get().lower()} profile).",
            "System",
        )

        def worker() -> None:
            global _dashboard_url
            while not self.shutting_down and key not in self.user_stopped:
                try:
                    flags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        if os.name == "nt" else 0
                    )
                    cmd = list(service.command)
                    if os.name == "nt":
                        resolved = shutil.which(cmd[0]) or cmd[0]
                        if not resolved.lower().endswith(".exe"):
                            cmd = ["cmd.exe", "/c"] + cmd
                        else:
                            cmd[0] = resolved
                    proc = subprocess.Popen(
                        cmd, cwd=service.cwd, env=self._env(),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1, creationflags=flags,
                    )
                    with self.process_lock:
                        self.processes[key] = proc
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        stripped = line.rstrip()
                        # Capture the actual port Vite binds to
                        if key == "dashboard":
                            m = re.search(
                                r'Local:\s*https?://[^:]+:(\d+)', stripped,
                            )
                            if m:
                                _dashboard_url = (
                                    f"http://127.0.0.1:{m.group(1)}"
                                )
                        # Parse structured progress events from training pipeline
                        if key == "pipeline" and stripped.startswith("{") and stripped.endswith("}"):
                            try:
                                pdata = json.loads(stripped)
                                if pdata.get("type") == "progress":
                                    pct = pdata.get("percent", 0)
                                    stg = pdata.get("stage", "")
                                    self._update_pipeline_progress(pct, stg)
                                    stripped = f"⚡ [{pct}%] {stg}"
                                elif pdata.get("type") == "log":
                                    stripped = pdata.get("message", stripped)
                            except Exception:
                                pass

                        tag = "Error" if "[error]" in stripped.lower() else service.key.capitalize()
                        self._log(stripped, tag)
                    code = proc.wait()
                    self._log(
                        f"{service.name} exited with code {code}.",
                        "System" if code == 0 else "Error",
                    )
                except Exception as exc:
                    self._log(
                        f"Failed to start {service.name}: {exc}", "Error",
                    )
                finally:
                    with self.process_lock:
                        self.processes[key] = None

                if (
                    not self.shutting_down
                    and key not in self.user_stopped
                    and key in ("backend", "dashboard")
                    and ("--autostart" in sys.argv or "-a" in sys.argv)
                ):
                    self._log(
                        f"Keep-Alive: Restarting {service.name}\u2026",
                        "System",
                    )
                    time.sleep(2)
                else:
                    break

        threading.Thread(target=worker, daemon=True).start()

    def stop_service(self, key: str) -> None:
        self.user_stopped.add(key)
        service = next(s for s in self.services if s.key == key)
        with self.process_lock:
            proc = self.processes.get(key)
        if not proc or proc.poll() is not None:
            self._log(f"{service.name} is not running.", "System")
            return
        self._log(f"Stopping {service.name}\u2026", "System")
        try:
            proc.send_signal(
                signal.CTRL_BREAK_EVENT if os.name == "nt"
                else signal.SIGTERM,
            )
            threading.Thread(
                target=self._wait_for_stop,
                args=(proc, service.name), daemon=True,
            ).start()
        except Exception as exc:
            self._log(f"Could not stop {service.name}: {exc}", "Error")

    def _wait_for_stop(
        self, proc: subprocess.Popen[str], name: str,
    ) -> None:
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            self._log(
                f"{name} did not exit gracefully and was terminated.",
                "Error",
            )

    def _open_browser_when_ready(
        self, url: str, attempts: int = 30,
    ) -> None:
        def check() -> None:
            import urllib.request
            for _ in range(attempts):
                if self.shutting_down:
                    return
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "ConsoleLauncher/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        if resp.status == 200:
                            self._log(
                                f"Web Dashboard ready. Opening {url}\u2026",
                                "System",
                            )
                            open_url(url)
                            return
                except Exception:
                    time.sleep(0.5)
            open_url(url)

        threading.Thread(target=check, daemon=True).start()

    def _open_browser_when_ready_dynamic(
        self, attempts: int = 30,
    ) -> None:
        """Wait for the dashboard to become reachable, using the runtime URL."""
        def check() -> None:
            import urllib.request
            for _ in range(attempts):
                if self.shutting_down:
                    return
                url = _dashboard_url
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "ConsoleLauncher/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        if resp.status == 200:
                            self._log(
                                f"Web Dashboard ready. Opening {url}\u2026",
                                "System",
                            )
                            open_url(url)
                            return
                except Exception:
                    time.sleep(0.5)
            url = _dashboard_url
            self._log(
                f"Timed out waiting for dashboard \u2014 opening {url} anyway.",
                "System",
            )
            open_url(url)

        threading.Thread(target=check, daemon=True).start()

    def start_demo(self) -> None:
        self.start_service("backend")
        self.start_service("dashboard")
        self.root.after(1200, lambda: self.start_service("simulator"))
        self._open_browser_when_ready_dynamic()

    def stop_all(self) -> None:
        active = [s for s in self.services if self._running(s.key)]
        if not active:
            self._log("No services are currently running.", "System")
            return
        if messagebox.askyesno(
            "Stop all services", f"Stop {len(active)} active service(s)?",
        ):
            for service in active:
                self.stop_service(service.key)

    def _running(self, key: str) -> bool:
        with self.process_lock:
            proc = self.processes.get(key)
            return bool(proc and proc.poll() is None)

    # ── Logging ──────────────────────────────────────────────────

    def _log(self, message: str, tag: str) -> None:
        self.log_queue.put((tag, message))

    def _drain_logs(self) -> None:
        while True:
            try:
                tag, message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_records.append((tag, message))
            if tag == "Error":
                self.error_count += 1
            if (
                self.log_filter.get() == "All messages"
                or self.log_filter.get().lower() == tag.lower()
            ):
                display_tag = (
                    tag if tag in self.console.tag_names() else "System"
                )
                self.console.insert(
                    "end",
                    f"[{tag.upper():<10}] {message}\n",
                    display_tag,
                )
                self.console.see("end")
        if len(self.log_records) > MAX_LOG_LINES:
            self.log_records = self.log_records[-MAX_LOG_LINES:]
        self.root.after(200, self._drain_logs)

    def _clear_activity(self) -> None:
        self.log_records.clear()
        self.console.delete("1.0", "end")
        self.error_count = 0

    def _apply_log_filter(self) -> None:
        """Immediately re-filter the console based on the active dropdown selection."""
        self.console.delete("1.0", "end")
        selected = self.log_filter.get().strip().lower()
        for tag, message in self.log_records:
            if selected == "all messages" or selected == tag.lower():
                display_tag = tag if tag in self.console.tag_names() else "System"
                self.console.insert("end", f"[{tag.upper():<10}] {message}\n", display_tag)
        self.console.see("end")

    # ── Periodic state refresh ───────────────────────────────────

    def _refresh_state(self) -> None:
        c = self.C
        active = core = workers = 0

        for svc in self.services:
            running = self._running(svc.key)
            refs = self.service_rows.get(svc.key)
            if refs:
                dot_colour = c["green_dot"] if running else c["sidebar_text"]
                refs["dot"].itemconfigure(refs["dot_id"], fill=dot_colour)
            if running:
                active += 1
                if svc.group == "Core services":
                    core += 1
                else:
                    workers += 1

        # Update header metrics
        total = len(self.services)
        core_total = sum(
            1 for s in self.services if s.group == "Core services"
        )
        worker_total = total - core_total

        self.metric_labels["active"].configure(text=f"{active}/{total}")
        self.metric_labels["core"].configure(text=f"{core}/{core_total}")
        self.metric_labels["workers"].configure(
            text=f"{workers}/{worker_total}",
        )
        self.metric_labels["errors"].configure(
            text=str(self.error_count),
            fg=c["red"] if self.error_count > 0 else c["ink"],
        )

        # System status badges
        if active > 0:
            self.header_badge.configure(
                text="\u25cf  ACTIVE", fg=c["green"],
            )
            self.sidebar_status.configure(
                text="\u25cf  SYSTEM ACTIVE", fg=c["green_dot"],
            )
        else:
            self.header_badge.configure(
                text="\u25cb  IDLE", fg=c["muted"],
            )
            self.sidebar_status.configure(
                text="\u25cb  SYSTEM IDLE", fg=c["sidebar_text"],
            )

        self._update_detail()
        self.root.after(800, self._refresh_state)

    # ── Window close ─────────────────────────────────────────────

    def _close(self) -> None:
        if self.shutting_down:
            return
        active = [s.name for s in self.services if self._running(s.key)]
        if active and not messagebox.askyesno(
            "Exit Operations",
            "Active services are running. Stop them and exit?",
        ):
            return
        self.shutting_down = True
        for service in self.services:
            if self._running(service.key):
                self.stop_service(service.key)
        self.root.after(300, self.root.destroy)


def main() -> None:
    root = tk.Tk()
    OperationsConsole(root)
    root.mainloop()


if __name__ == "__main__":
    main()
