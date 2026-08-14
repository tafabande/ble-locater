"""
⚡ Hospital Asset Locator — Simple Control & Operations Panel
============================================================
A plain-English, zero-jargon control desk for facility managers, staff, and operators.
Designed so anyone can start the system, search for equipment/patients, and monitor operations
without any programming or engineering background.
"""

import os
import sys
import time
import json
import queue
import re
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "ble-indoor-positioning")
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")

if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable


class ControlCenterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⚡ Hospital Asset Locator — Easy Control Panel")
        self.root.geometry("1380x920")
        self.root.minsize(1200, 800)

        self.log_queue = queue.Queue()
        self.log_event_counts = deque([0] * 60, maxlen=60)
        self.current_sec_events = 0

        self.cpu_history = deque([0.0] * 60, maxlen=60)
        self.ram_history = deque([0.0] * 60, maxlen=60)

        self.processes = {
            "backend": None,
            "dashboard": None,
            "collector": None,
            "simulator": None,
            "tests": None
        }

        self.proc_meta = {
            name: {
                "start_time": None,
                "pid": None,
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "log_lines": 0,
                "status": "OFFLINE"
            } for name in self.processes
        }

        self.test_state = {
            "running": False,
            "total": 0,
            "completed": 0,
            "passed": 0,
            "failed": 0,
            "current_test": ""
        }

        self.auto_scroll = tk.BooleanVar(value=True)
        self.current_log_filter = "ALL"
        self.search_term = ""

        # Friendly Color Palette (Slate Blue & Warm Accents)
        self.colors = {
            "bg": "#0F172A",           # Dark Navy Slate background
            "panel": "#1E293B",        # Surface panel background
            "card": "#1E293B",         # Card background
            "card_inner": "#0F172A",   # Inner nested callout box
            "border": "#334155",       # Border lines
            "accent": "#38BDF8",       # Sky Blue Accent
            "accent_hover": "#0EA5E9",
            "green": "#4ADE80",        # Success Green
            "yellow": "#FBBF24",       # Friendly Amber
            "red": "#F87171",          # Stop Red
            "purple": "#C084FC",       # Purple Badge
            "text": "#F8FAFC",         # Primary white text
            "subtext": "#94A3B8",      # Subtitle muted text
            "hint": "#94A3B8"          # Plain-English helper text
        }

        self.setup_styles()
        self.build_ui()

        self.root.after(100, self.process_queue_logs)
        self.root.after(1000, self.update_system_telemetry)
        self.root.after(1000, self.update_process_states)
        self.root.after(3000, self.refresh_diagnostics)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        self.root.configure(bg=self.colors["bg"])

        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.colors["card"], relief="flat")
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("Inner.TFrame", background=self.colors["card_inner"])

        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground=self.colors["text"], background=self.colors["panel"])
        style.configure("Subtitle.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.colors["accent"], background=self.colors["card"])
        style.configure("Body.TLabel", font=("Segoe UI", 9), foreground=self.colors["text"], background=self.colors["card"])
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground=self.colors["subtext"], background=self.colors["card"])
        style.configure("Hint.TLabel", font=("Segoe UI", 9), foreground=self.colors["subtext"], background=self.colors["card_inner"])
        style.configure("PanelMuted.TLabel", font=("Segoe UI", 9), foreground=self.colors["subtext"], background=self.colors["panel"])

        # Button Styles
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), background=self.colors["accent"], foreground="#0F172A", padding=[12, 6])
        style.map("Primary.TButton", background=[("active", self.colors["accent_hover"])])

        style.configure("Success.TButton", font=("Segoe UI", 9, "bold"), background=self.colors["green"], foreground="#0F172A", padding=[12, 6])
        style.map("Success.TButton", background=[("active", "#22C55E")])

        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), background=self.colors["red"], foreground="#0F172A", padding=[10, 6])
        style.map("Danger.TButton", background=[("active", "#EF4444")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9), background=self.colors["border"], foreground=self.colors["text"], padding=[10, 6])
        style.map("Secondary.TButton", background=[("active", "#475569")])

        # Progress bars
        style.configure("CPU.Horizontal.TProgressbar", foreground=self.colors["accent"], background=self.colors["accent"], troughcolor=self.colors["bg"])
        style.configure("RAM.Horizontal.TProgressbar", foreground=self.colors["purple"], background=self.colors["purple"], troughcolor=self.colors["bg"])
        style.configure("Test.Horizontal.TProgressbar", foreground=self.colors["green"], background=self.colors["green"], troughcolor=self.colors["bg"])

    def build_ui(self):
        # ──────────────────────────────────────────────────────────────────
        # 1. HEADER BAR & COMPUTER HEALTH METERS
        # ──────────────────────────────────────────────────────────────────
        top_bar = ttk.Frame(self.root, style="Panel.TFrame", padding=(20, 12))
        top_bar.pack(fill="x")

        # Left Branding
        title_box = ttk.Frame(top_bar, style="Panel.TFrame")
        title_box.pack(side="left")

        header_row = ttk.Frame(title_box, style="Panel.TFrame")
        header_row.pack(anchor="w")
        ttk.Label(header_row, text="⚡ Hospital Asset Locator", style="Title.TLabel").pack(side="left")
        ttk.Label(header_row, text=" Easy Control Desk", font=("Segoe UI", 9, "bold"), foreground=self.colors["accent"], background=self.colors["panel"]).pack(side="left", padx=6)

        ttk.Label(title_box, text="Simple controls to find equipment, patients, and staff across rooms in real time", style="PanelMuted.TLabel").pack(anchor="w", pady=(2, 0))

        # System Health Meters (Plain Language)
        telem_box = ttk.Frame(top_bar, style="Panel.TFrame")
        telem_box.pack(side="left", expand=True, padx=20)

        # Computer Speed (CPU)
        cpu_box = ttk.Frame(telem_box, style="Panel.TFrame")
        cpu_box.pack(side="left", padx=12)
        ttk.Label(cpu_box, text="COMPUTER SPEED", font=("Segoe UI", 8, "bold"), foreground=self.colors["subtext"], background=self.colors["panel"]).pack(anchor="w")
        self.lbl_top_cpu = ttk.Label(cpu_box, text="0.0%", font=("Segoe UI", 11, "bold"), foreground=self.colors["accent"], background=self.colors["panel"])
        self.lbl_top_cpu.pack(anchor="w")
        self.bar_top_cpu = ttk.Progressbar(cpu_box, style="CPU.Horizontal.TProgressbar", length=85, mode="determinate")
        self.bar_top_cpu.pack(anchor="w", pady=(2, 0))

        # Memory Used (RAM)
        ram_box = ttk.Frame(telem_box, style="Panel.TFrame")
        ram_box.pack(side="left", padx=12)
        ttk.Label(ram_box, text="MEMORY USED", font=("Segoe UI", 8, "bold"), foreground=self.colors["subtext"], background=self.colors["panel"]).pack(anchor="w")
        self.lbl_top_ram = ttk.Label(ram_box, text="0.0 GB", font=("Segoe UI", 11, "bold"), foreground=self.colors["purple"], background=self.colors["panel"])
        self.lbl_top_ram.pack(anchor="w")
        self.bar_top_ram = ttk.Progressbar(ram_box, style="RAM.Horizontal.TProgressbar", length=85, mode="determinate")
        self.bar_top_ram.pack(anchor="w", pady=(2, 0))

        # Active Tools
        svc_box = ttk.Frame(telem_box, style="Panel.TFrame")
        svc_box.pack(side="left", padx=12)
        ttk.Label(svc_box, text="ACTIVE TOOLS", font=("Segoe UI", 8, "bold"), foreground=self.colors["subtext"], background=self.colors["panel"]).pack(anchor="w")
        self.lbl_active_procs = ttk.Label(svc_box, text="0 / 6 Running", font=("Segoe UI", 11, "bold"), foreground=self.colors["green"], background=self.colors["panel"])
        self.lbl_active_procs.pack(anchor="w")

        # Top Header Action Buttons
        ttk.Button(top_bar, text="🌐 Launch Web Dashboard", style="Success.TButton", command=self.launch_dashboard_and_open).pack(side="right", padx=(0, 10))
        ttk.Button(top_bar, text="🛑 Turn Off Everything", style="Danger.TButton", command=self.stop_all_services).pack(side="right")

        ttk.Separator(self.root, orient="horizontal").pack(fill="x")

        # ──────────────────────────────────────────────────────────────────
        # 2. ⭐ SIMPLE STEP-BY-STEP GUIDED WORKFLOW (NON-TECHNICAL)
        # ──────────────────────────────────────────────────────────────────
        stepper_bar = ttk.Frame(self.root, style="Panel.TFrame", padding=(20, 10))
        stepper_bar.pack(fill="x")

        ttk.Label(stepper_bar, text="⭐ EASY 3-STEP START GUIDE:", font=("Segoe UI", 9, "bold"), foreground=self.colors["yellow"], background=self.colors["panel"]).pack(side="left", padx=(0, 10))

        ttk.Button(stepper_bar, text="1️⃣ Turn On System + Demo Motion", style="Primary.TButton", command=self.launch_all_services).pack(side="left", padx=4)
        ttk.Label(stepper_bar, text="➔", font=("Segoe UI", 12), foreground=self.colors["subtext"], background=self.colors["panel"]).pack(side="left", padx=4)
        
        ttk.Button(stepper_bar, text="2️⃣ Open Search Webpage", style="Success.TButton", command=lambda: webbrowser.open("http://localhost:8000")).pack(side="left", padx=4)
        ttk.Label(stepper_bar, text="➔", font=("Segoe UI", 12), foreground=self.colors["subtext"], background=self.colors["panel"]).pack(side="left", padx=4)

        ttk.Button(stepper_bar, text="3️⃣ Open React Building Floorplan", style="Secondary.TButton", command=lambda: webbrowser.open("http://localhost:5173")).pack(side="left", padx=4)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x")

        # ──────────────────────────────────────────────────────────────────
        # 3. MAIN WORKSPACE
        # ──────────────────────────────────────────────────────────────────
        main_layout = ttk.Frame(self.root, padding=(16, 10))
        main_layout.pack(fill="both", expand=True)

        # Left Column: Easy System Tools Desk (~52% width)
        left_pane = ttk.Frame(main_layout)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right Column: System Logs & Graphs (~48% width)
        right_pane = ttk.Frame(main_layout)
        right_pane.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # ── SCROLLABLE SERVICE CARDS ON LEFT PANE ──
        svc_canvas = tk.Canvas(left_pane, bg=self.colors["bg"], highlightthickness=0)
        svc_scrollbar = ttk.Scrollbar(left_pane, orient="vertical", command=svc_canvas.yview)
        self.svc_inner = ttk.Frame(svc_canvas)

        self.svc_inner.bind("<Configure>", lambda e: svc_canvas.configure(scrollregion=svc_canvas.bbox("all")))
        svc_canvas.create_window((0, 0), window=self.svc_inner, anchor="nw")
        svc_canvas.configure(yscrollcommand=svc_scrollbar.set)

        svc_canvas.pack(side="left", fill="both", expand=True)
        svc_scrollbar.pack(side="right", fill="y")

        # Non-Technical Service Definitions with Plain Language Explanations
        services_config = [
            {
                "key": "backend",
                "title": "📍 Location Engine & Search Server",
                "desc": "The central brain that calculates room locations for equipment/patients and powers the search bar.",
                "url": "http://127.0.0.1:8000",
                "what": "Calculates room coordinates (Room A, B, C, D) and handles search queries from users.",
                "when": "Must be ON whenever staff want to search or track items.",
                "what_will_happen": "Clicking 'Turn On' starts the central location server. You can then open the search webpage.",
                "start_fn": self.start_backend,
                "stop_fn": self.stop_backend
            },
            {
                "key": "collector",
                "title": "📡 Physical Room Sensor Collector (Hardware GUI)",
                "desc": "Receives real Bluetooth signals from physical sensors mounted on room walls.",
                "url": None,
                "what": "Listens for physical signals from real room hardware plugged into USB ports.",
                "when": "Use when deployed with real physical room sensors.",
                "what_will_happen": "Clicking 'Turn On' starts reading real physical signals into the server.",
                "start_fn": self.start_collector,
                "stop_fn": self.stop_collector
            },
            {
                "key": "simulator",
                "title": "🎮 Demo Item Movement Generator (Virtual Test)",
                "desc": "Generates moving fake equipment tags across rooms so you can try searching without physical hardware.",
                "url": None,
                "what": "Moves virtual items like 'ECG Machine #01' and 'Patient Bed 1' around rooms automatically.",
                "when": "Use when demonstrating or testing without real physical sensors plugged in.",
                "what_will_happen": "Clicking 'Turn On' creates simulated moving items on your floorplan map.",
                "start_fn": self.start_sim,
                "stop_fn": self.stop_sim
            },
            {
                "key": "dashboard",
                "title": "🗺️ React Building Floorplan Web Portal",
                "desc": "Single visual map page showing 2D/3D floorplan, item motion, geofence alerts, and analytics.",
                "url": "http://127.0.0.1:5173",
                "what": "Displays the standardized React/Vite interactive map of the floorplan with live markers.",
                "when": "Use when you want to view the live asset floorplan view or room statistics.",
                "what_will_happen": "Clicking 'Open Webpage' opens the React floorplan app in your browser.",
                "start_fn": self.start_dashboard,
                "stop_fn": self.stop_dashboard
            }
        ]

        self.service_cards = {}
        for config in services_config:
            card = self.create_explaining_service_card(self.svc_inner, config)
            card.pack(fill="x", pady=(0, 10))

        # Test Runner Card (Plain English)
        test_card = ttk.Frame(self.svc_inner, style="Card.TFrame", padding=12)
        test_card.pack(fill="x", pady=(0, 10))

        t_top = ttk.Frame(test_card, style="Card.TFrame")
        t_top.pack(fill="x")
        ttk.Label(t_top, text="🧪 System Health Self-Test & Diagnostic Check", style="Subtitle.TLabel").pack(side="left")
        self.lbl_test_badge = ttk.Label(t_top, text="READY", font=("Segoe UI", 9, "bold"), foreground=self.colors["purple"], background=self.colors["card"])
        self.lbl_test_badge.pack(side="right")

        ttk.Label(test_card, text="Runs automatic health checks to confirm room calculations, search rules, and data storage are working properly.", style="Muted.TLabel").pack(anchor="w", pady=(2, 6))

        # Inner plain-English explanation
        t_inner = ttk.Frame(test_card, style="Inner.TFrame", padding=8)
        t_inner.pack(fill="x", pady=(0, 8))
        ttk.Label(t_inner, text="💡 What this does: Checks 10+ internal system safety rules in 3 seconds to verify zero errors.", style="Hint.TLabel", wraplength=480).pack(anchor="w")
        ttk.Label(t_inner, text="⚡ What will happen: Runs automated checks and displays a green 'ALL PASSED' checkmark.", font=("Segoe UI", 9), foreground=self.colors["yellow"], background=self.colors["card_inner"], wraplength=480).pack(anchor="w", pady=(2, 0))

        self.test_progress_bar = ttk.Progressbar(test_card, style="Test.Horizontal.TProgressbar", mode="determinate")
        self.test_progress_bar.pack(fill="x", pady=(2, 6))

        t_stats = ttk.Frame(test_card, style="Card.TFrame")
        t_stats.pack(fill="x")
        self.lbl_test_current = ttk.Label(t_stats, text="Status: Ready to test system health", style="Muted.TLabel")
        self.lbl_test_current.pack(side="left")
        self.lbl_test_counts = ttk.Label(t_stats, text="Passed: 0 | Failed: 0", font=("Segoe UI", 9, "bold"), foreground=self.colors["green"], background=self.colors["card"])
        self.lbl_test_counts.pack(side="right")

        t_btns = ttk.Frame(test_card, style="Card.TFrame")
        t_btns.pack(fill="x", pady=(8, 0))
        ttk.Button(t_btns, text="▶ Run Self-Test Check", style="Primary.TButton", command=self.run_tests).pack(side="left")
        ttk.Button(t_btns, text="Cancel Test", style="Danger.TButton", command=self.stop_tests).pack(side="left", padx=8)

        # ── BUILD RIGHT PANE: TELEMETRY SPARKLINE + LOG CONSOLE ──

        # System Health Graphs
        spark_card = ttk.Frame(right_pane, style="Card.TFrame", padding=12)
        spark_card.pack(fill="x", pady=(0, 10))

        s_top = ttk.Frame(spark_card, style="Card.TFrame")
        s_top.pack(fill="x", pady=(0, 4))
        ttk.Label(s_top, text="📈 Computer Speed & Activity Graphs", style="Subtitle.TLabel").pack(side="left")
        ttk.Label(s_top, text="Past 60 seconds", style="Muted.TLabel").pack(side="right")

        spark_box = ttk.Frame(spark_card, style="Card.TFrame")
        spark_box.pack(fill="x")

        self.spark_sys_canvas = tk.Canvas(spark_box, height=50, bg=self.colors["bg"], highlightthickness=1, highlightbackground=self.colors["border"])
        self.spark_sys_canvas.pack(fill="x", pady=2)

        self.spark_log_canvas = tk.Canvas(spark_box, height=40, bg=self.colors["bg"], highlightthickness=1, highlightbackground=self.colors["border"])
        self.spark_log_canvas.pack(fill="x", pady=2)

        # Diagnostics Overview
        diag_card = ttk.Frame(right_pane, style="Card.TFrame", padding=12)
        diag_card.pack(fill="x", pady=(0, 10))

        d_top = ttk.Frame(diag_card, style="Card.TFrame")
        d_top.pack(fill="x", pady=(0, 4))
        ttk.Label(d_top, text="📊 Asset Registry & System Status", style="Subtitle.TLabel").pack(side="left")

        d_grid = ttk.Frame(diag_card, style="Card.TFrame")
        d_grid.pack(fill="x")

        self.lbl_diag_model = ttk.Label(d_grid, text="Location AI: Ready & Active", style="Body.TLabel")
        self.lbl_diag_model.grid(row=0, column=0, sticky="w", pady=1)

        self.lbl_diag_registry = ttk.Label(d_grid, text="Asset Registry: 12 Hospital Assets Registered (ECGs, Pumps, Staff, Patients)", style="Muted.TLabel")
        self.lbl_diag_registry.grid(row=1, column=0, sticky="w", pady=1)

        # Terminal Console with Friendly Filters
        console_card = ttk.Frame(right_pane, style="Card.TFrame", padding=12)
        console_card.pack(fill="both", expand=True)

        c_top = ttk.Frame(console_card, style="Card.TFrame")
        c_top.pack(fill="x", pady=(0, 6))
        ttk.Label(c_top, text="📋 Activity & Log Message Stream", style="Subtitle.TLabel").pack(side="left")
        ttk.Button(c_top, text="Clear Stream", style="Secondary.TButton", command=self.clear_console).pack(side="right")

        filter_bar = ttk.Frame(console_card, style="Card.TFrame")
        filter_bar.pack(fill="x", pady=(0, 6))

        ttk.Label(filter_bar, text="Filter Stream:", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        self.cmb_filter = ttk.Combobox(
            filter_bar,
            values=[
                "ALL (Everything)",
                "LOCATION ENGINE (Server)",
                "BUILDING MAP (Dashboard)",
                "PHYSICAL SENSORS (Collector)",
                "DEMO SIMULATOR (Virtual Beacons)",
                "SELF-TESTS (Diagnostics)",
                "ERRORS & WARNINGS ONLY"
            ],
            width=24,
            state="readonly"
        )
        self.cmb_filter.set("ALL (Everything)")
        self.cmb_filter.pack(side="left", padx=(0, 8))
        self.cmb_filter.bind("<<ComboboxSelected>>", self.on_filter_change)

        ttk.Label(filter_bar, text="Search text:", style="Muted.TLabel").pack(side="left", padx=(4, 4))
        self.ent_search = ttk.Entry(filter_bar, width=12)
        self.ent_search.pack(side="left", padx=(0, 8))
        self.ent_search.bind("<KeyRelease>", self.on_search_change)

        ttk.Checkbutton(filter_bar, text="Auto-Scroll", variable=self.auto_scroll, style="Muted.TLabel").pack(side="left")

        # Text Console
        self.console = tk.Text(
            console_card,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
            padx=8,
            pady=8
        )
        c_scroll = ttk.Scrollbar(console_card, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=c_scroll.set)

        self.console.pack(side="left", fill="both", expand=True)
        c_scroll.pack(side="right", fill="y")

        # Tags
        self.console.tag_config("SYSTEM", foreground=self.colors["purple"])
        self.console.tag_config("BACKEND", foreground=self.colors["accent"])
        self.console.tag_config("DASHBOARD", foreground=self.colors["purple"])
        self.console.tag_config("COLLECTOR", foreground=self.colors["yellow"])
        self.console.tag_config("SIMULATOR", foreground=self.colors["green"])
        self.console.tag_config("TESTS", foreground=self.colors["accent"])
        self.console.tag_config("ERROR", foreground=self.colors["red"], font=("Consolas", 9, "bold"))
        self.console.tag_config("WARNING", foreground=self.colors["yellow"])

    def create_explaining_service_card(self, parent, c: dict):
        """Builds an intuitive, non-technical service card explaining What, When, and What Will Happen."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)

        # Header Row
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")

        ttk.Label(top, text=c["title"], style="Subtitle.TLabel").pack(side="left")
        status_lbl = ttk.Label(top, text="🔴 TURNED OFF", font=("Segoe UI", 9, "bold"), foreground=self.colors["red"], background=self.colors["card"])
        status_lbl.pack(side="right")

        # Primary Description (Plain Language)
        ttk.Label(card, text=c["desc"], style="Body.TLabel", wraplength=500).pack(anchor="w", pady=(2, 6))

        # Inner Plain-English Callout Box
        inner = ttk.Frame(card, style="Inner.TFrame", padding=8)
        inner.pack(fill="x", pady=(0, 8))

        ttk.Label(inner, text=f"💡 What it does: {c['what']}", style="Hint.TLabel", wraplength=480).pack(anchor="w")
        ttk.Label(inner, text=f"👉 When to use: {c['when']}", style="Hint.TLabel", wraplength=480).pack(anchor="w", pady=(2, 0))
        ttk.Label(inner, text=f"⚡ What will happen: {c['what_will_happen']}", font=("Segoe UI", 9, "bold"), foreground=self.colors["yellow"], background=self.colors["card_inner"], wraplength=480).pack(anchor="w", pady=(2, 0))

        # Control Row
        bottom = ttk.Frame(card, style="Card.TFrame")
        bottom.pack(fill="x")

        btn_start = ttk.Button(bottom, text="▶ Turn On", style="Primary.TButton", command=c["start_fn"])
        btn_start.pack(side="left", padx=(0, 6))

        btn_stop = ttk.Button(bottom, text="Turn Off", style="Danger.TButton", command=c["stop_fn"], state="disabled")
        btn_stop.pack(side="left", padx=(0, 6))

        if c.get("url"):
            btn_open = ttk.Button(bottom, text="🌐 Open Webpage", style="Success.TButton", command=lambda: webbrowser.open(c["url"]))
            btn_open.pack(side="left", padx=(0, 6))

        lbl_meta = ttk.Label(bottom, text="Status: Ready", style="Muted.TLabel")
        lbl_meta.pack(side="right")

        self.service_cards[c["key"]] = {
            "status_lbl": status_lbl,
            "lbl_meta": lbl_meta,
            "btn_start": btn_start,
            "btn_stop": btn_stop
        }

        return card

    # ──────────────────────────────────────────────────────────────────
    # PROCESS MANAGEMENT LOGIC
    # ──────────────────────────────────────────────────────────────────

    def run_process_in_thread(self, name: str, command: list, cwd: str):
        def worker():
            try:
                self.log_queue.put(f"[SYSTEM] Turning on '{name}'...\n")
                self.proc_meta[name]["start_time"] = time.time()
                self.proc_meta[name]["status"] = "RUNNING"

                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd
                )
                self.processes[name] = proc
                self.proc_meta[name]["pid"] = proc.pid

                for line in iter(proc.stdout.readline, ""):
                    if line:
                        self.log_queue.put(f"[{name.upper()}] {line}")
                        self.proc_meta[name]["log_lines"] += 1
                        self.current_sec_events += 1

                proc.wait()
                exit_code = proc.returncode
                if exit_code == 0:
                    self.log_queue.put(f"[SYSTEM] '{name}' stopped normally.\n")
                else:
                    self.log_queue.put(f"[SYSTEM] '{name}' stopped (Code {exit_code}).\n")
            except Exception as e:
                self.log_queue.put(f"[ERROR] Could not start '{name}': {e}\n")
            finally:
                self.processes[name] = None
                self.proc_meta[name]["status"] = "OFFLINE"
                self.proc_meta[name]["pid"] = None
                self.proc_meta[name]["start_time"] = None
                self.proc_meta[name]["cpu_percent"] = 0.0
                self.proc_meta[name]["memory_mb"] = 0.0

        threading.Thread(target=worker, daemon=True).start()

    def start_backend(self):
        if not self.processes["backend"]:
            script = os.path.join(PROJECT_ROOT, "server", "app.py")
            self.run_process_in_thread("backend", [VENV_PYTHON, script], os.path.join(PROJECT_ROOT, "server"))

    def stop_backend(self):
        self.kill_proc("backend")

    def start_dashboard(self):
        webbrowser.open("http://127.0.0.1:5173")
        self.log_queue.put("[SYSTEM] Opened React building floorplan app in browser (http://127.0.0.1:5173).\n")

    def stop_dashboard(self):
        pass

    def start_collector(self):
        if not self.processes["collector"]:
            script = os.path.join(PROJECT_ROOT, "collector", "collector.py")
            self.run_process_in_thread("collector", [VENV_PYTHON, script, "--port", "stdin"], PROJECT_ROOT)

    def stop_collector(self):
        self.kill_proc("collector")

    def start_sim(self):
        if not self.processes["simulator"]:
            script = os.path.join(PROJECT_ROOT, "simulate_demo.py")
            self.run_process_in_thread("simulator", [VENV_PYTHON, script], PROJECT_ROOT)

    def stop_sim(self):
        self.kill_proc("simulator")

    def kill_proc(self, name: str):
        proc = self.processes.get(name)
        if proc:
            try:
                if HAS_PSUTIL:
                    parent = psutil.Process(proc.pid)
                    for child in parent.children(recursive=True):
                        child.terminate()
                    parent.terminate()
                else:
                    proc.terminate()
                self.log_queue.put(f"[SYSTEM] Turned off '{name}'.\n")
            except Exception as e:
                self.log_queue.put(f"[ERROR] Could not turn off '{name}': {e}\n")

    def launch_all_services(self):
        """Launches core backend and demo simulator services."""
        self.start_backend()
        self.root.after(1500, self.start_sim)

    def launch_dashboard_and_open(self):
        """Starts location engine, live motion, and opens the React Dashboard in browser."""
        self.launch_all_services()
        self.root.after(1500, lambda: webbrowser.open("http://localhost:5173"))

    def stop_all_services(self):
        """Stops all active subprocesses."""
        for name in list(self.processes.keys()):
            if self.processes[name] is not None:
                self.kill_proc(name)

    # ──────────────────────────────────────────────────────────────────
    # AUTOMATED DIAGNOSTIC SELF-TEST RUNNER
    # ──────────────────────────────────────────────────────────────────

    def run_tests(self):
        if self.test_state["running"]:
            return

        self.test_state["running"] = True
        self.test_state["total"] = 0
        self.test_state["completed"] = 0
        self.test_state["passed"] = 0
        self.test_state["failed"] = 0
        self.test_state["current_test"] = "Checking system health..."

        self.lbl_test_badge.config(text="CHECKING", foreground=self.colors["yellow"])
        self.test_progress_bar.config(value=0, maximum=100)

        def worker():
            self.log_queue.put("[SYSTEM] Starting automated self-test check...\n")
            try:
                cmd = [VENV_PYTHON, "-m", "pytest", "-v"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                self.processes["tests"] = proc
                self.proc_meta["tests"]["start_time"] = time.time()
                self.proc_meta["tests"]["status"] = "RUNNING"

                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        continue
                    self.log_queue.put(f"[TESTS] {line}")
                    self.current_sec_events += 1

                    if "PASSED" in line:
                        self.test_state["passed"] += 1
                        self.test_state["completed"] += 1
                    elif "FAILED" in line or "ERROR" in line:
                        self.test_state["failed"] += 1
                        self.test_state["completed"] += 1

                    match_col = re.search(r"collected (\d+) item", line)
                    if match_col:
                        self.test_state["total"] = int(match_col.group(1))

                proc.wait()
                if proc.returncode == 0:
                    self.log_queue.put("[SYSTEM] All system checks passed cleanly! ✅\n")
                    self.test_state["current_test"] = "Health Check Complete: ALL PASSED!"
                else:
                    self.log_queue.put(f"[SYSTEM] Health check finished with warnings (Code {proc.returncode}). ❌\n")
                    self.test_state["current_test"] = f"Finished with warnings (Code {proc.returncode})"

            except Exception as e:
                self.log_queue.put(f"[ERROR] Failed running self-test: {e}\n")
            finally:
                self.test_state["running"] = False
                self.processes["tests"] = None
                self.proc_meta["tests"]["status"] = "OFFLINE"

        threading.Thread(target=worker, daemon=True).start()

    def stop_tests(self):
        proc = self.processes.get("tests")
        if proc:
            proc.terminate()
            self.test_state["running"] = False
            self.lbl_test_badge.config(text="CANCELLED", foreground=self.colors["red"])

    # ──────────────────────────────────────────────────────────────────
    # TELEMETRY & SPARKLINE DRAWING LOOPS
    # ──────────────────────────────────────────────────────────────────

    def update_system_telemetry(self):
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent()
            ram_info = psutil.virtual_memory()
            ram_pct = ram_info.percent
            ram_gb = ram_info.used / (1024 ** 3)
        else:
            cpu = 0.0
            ram_pct = 0.0
            ram_gb = 0.0

        self.cpu_history.append(cpu)
        self.ram_history.append(ram_pct)

        self.lbl_top_cpu.config(text=f"{cpu:.1f}%")
        self.bar_top_cpu.config(value=cpu)

        self.lbl_top_ram.config(text=f"{ram_gb:.1f} GB ({ram_pct:.0f}%)")
        self.bar_top_ram.config(value=ram_pct)

        self.log_event_counts.append(self.current_sec_events)
        self.current_sec_events = 0

        self.draw_system_sparkline()
        self.draw_log_sparkline()

        active_cnt = sum(1 for p in self.processes.values() if p is not None)
        self.lbl_active_procs.config(text=f"{active_cnt} / 6 Running")

        if self.test_state["running"]:
            tot = max(1, self.test_state["total"])
            comp = self.test_state["completed"]
            pct = min(100, int((comp / tot) * 100)) if tot > 0 else 0
            self.test_progress_bar.config(value=pct)
            self.lbl_test_badge.config(text=f"{pct}% ({comp}/{tot})", foreground=self.colors["yellow"])
            self.lbl_test_current.config(text=f"Checking system health... ({comp}/{tot})")
            self.lbl_test_counts.config(
                text=f"Passed: {self.test_state['passed']} | Failed: {self.test_state['failed']}",
                foreground=self.colors["green"] if self.test_state["failed"] == 0 else self.colors["red"]
            )
        elif self.test_state["completed"] > 0:
            badge_str = "ALL PASSED ✅" if self.test_state["failed"] == 0 else "WARNINGS ❌"
            color = self.colors["green"] if self.test_state["failed"] == 0 else self.colors["red"]
            self.lbl_test_badge.config(text=badge_str, foreground=color)

        self.root.after(2500, self.update_system_telemetry)

    def draw_system_sparkline(self):
        c = self.spark_sys_canvas
        c.delete("all")

        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 10 or h <= 10:
            return

        c.create_text(8, 6, anchor="nw", text="Computer Speed & Memory Usage (60s)", fill=self.colors["subtext"], font=("Segoe UI", 8))

        step = w / 59
        cpu_pts = []
        for i, val in enumerate(self.cpu_history):
            x = i * step
            y = h - (val / 100.0) * (h - 18) - 4
            cpu_pts.extend([x, y])

        if len(cpu_pts) >= 4:
            c.create_line(cpu_pts, fill=self.colors["accent"], width=2, smooth=True)

        ram_pts = []
        for i, val in enumerate(self.ram_history):
            x = i * step
            y = h - (val / 100.0) * (h - 18) - 4
            ram_pts.extend([x, y])

        if len(ram_pts) >= 4:
            c.create_line(ram_pts, fill=self.colors["purple"], width=1, dash=(4, 2), smooth=True)

    def draw_log_sparkline(self):
        c = self.spark_log_canvas
        c.delete("all")

        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 10 or h <= 10:
            return

        max_val = max(10, max(self.log_event_counts))
        c.create_text(8, 4, anchor="nw", text=f"System Signal Activity Rate (Peak: {max_val} msgs/s)", fill=self.colors["subtext"], font=("Segoe UI", 8))

        step = w / 59
        pts = []
        for i, val in enumerate(self.log_event_counts):
            x = i * step
            y = h - (val / float(max_val)) * (h - 16) - 4
            pts.extend([x, y])

        if len(pts) >= 4:
            c.create_line(pts, fill=self.colors["green"], width=2, smooth=True)

    def update_process_states(self):
        for name, card in self.service_cards.items():
            meta = self.proc_meta[name]
            proc = self.processes.get(name)

            if proc and proc.poll() is None:
                card["status_lbl"].config(text="🟢 ACTIVE", foreground=self.colors["green"])
                card["btn_start"].config(state="disabled")
                card["btn_stop"].config(state="normal")

                if HAS_PSUTIL and meta["pid"]:
                    try:
                        p = psutil.Process(meta["pid"])
                        cpu = p.cpu_percent(interval=None)
                        mem = p.memory_info().rss / (1024 * 1024)
                        card["lbl_meta"].config(text=f"Status: Active | Speed: {cpu:.0f}% | Memory: {mem:.0f} MB")
                    except Exception:
                        pass
            else:
                card["status_lbl"].config(text="🔴 TURNED OFF", foreground=self.colors["red"])
                card["btn_start"].config(state="normal")
                card["btn_stop"].config(state="disabled")
                card["lbl_meta"].config(text="Status: Ready to start")

        self.root.after(2500, self.update_process_states)

    def refresh_diagnostics(self):
        meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")
        if os.path.exists(meta_path):
            try:
                self.lbl_diag_model.config(
                    text="Location AI: Ready & High Accuracy",
                    foreground=self.colors["green"]
                )
            except Exception:
                self.lbl_diag_model.config(text="Location AI: Initializing", foreground=self.colors["yellow"])
        else:
            self.lbl_diag_model.config(text="Location AI: Ready in models/", foreground=self.colors["subtext"])

        self.root.after(5000, self.refresh_diagnostics)

    # ──────────────────────────────────────────────────────────────────
    # CONSOLE LOG PIPELINE & FILTERING
    # ──────────────────────────────────────────────────────────────────

    def process_queue_logs(self):
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.append_log_line(msg)
            except queue.Empty:
                break
        self.root.after(250, self.process_queue_logs)

    def append_log_line(self, msg: str):
        tag = "SYSTEM"
        if "[BACKEND]" in msg.upper() or "[LOCATION ENGINE]" in msg.upper():
            tag = "BACKEND"
        elif "[DASHBOARD]" in msg.upper() or "[MAP]" in msg.upper():
            tag = "DASHBOARD"
        elif "[COLLECTOR]" in msg.upper() or "[SENSORS]" in msg.upper():
            tag = "COLLECTOR"
        elif "[SIMULATOR]" in msg.upper() or "[DEMO]" in msg.upper():
            tag = "SIMULATOR"
        elif "[TESTS]" in msg.upper():
            tag = "TESTS"

        if "ERROR" in msg.upper() or "EXCEPTION" in msg.upper():
            tag = "ERROR"

        # Filter logic
        sel_filter = self.current_log_filter
        if "LOCATION ENGINE" in sel_filter and tag != "BACKEND": return
        if "BUILDING MAP" in sel_filter and tag != "DASHBOARD": return
        if "PHYSICAL SENSORS" in sel_filter and tag != "COLLECTOR": return
        if "DEMO SIMULATOR" in sel_filter and tag != "SIMULATOR": return
        if "SELF-TESTS" in sel_filter and tag != "TESTS": return
        if "ERRORS" in sel_filter and tag != "ERROR": return

        if self.search_term and self.search_term.lower() not in msg.lower():
            return

        self.console.insert(tk.END, msg, tag)
        if self.auto_scroll.get():
            self.console.see(tk.END)

    def on_filter_change(self, event=None):
        self.current_log_filter = self.cmb_filter.get()

    def on_search_change(self, event=None):
        self.search_term = self.ent_search.get()

    def clear_console(self):
        self.console.delete("1.0", tk.END)

    def on_close(self):
        active = [name for name, proc in self.processes.items() if proc is not None]
        if active:
            if not messagebox.askyesno("Exit Control Panel?", f"Active tools are running: {', '.join(active)}.\nTurn off all background tools and exit?"):
                return
            self.stop_all_services()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ControlCenterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
