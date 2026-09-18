"""Indoor Positioning — Dedicated Visual Experiment Builder & Data Collector.

A research-grade Python GUI for constructing a 2D experimental environment layout
(dimensions, grid, 4 anchor nodes, movable target, geometric obstacles with LOS/NLOS raycasting)
and collecting clean, correctly labelled, reproducible BLE RSSI observation datasets.
"""
from __future__ import annotations

import datetime
import json
import os
import queue
import subprocess
import sys
import time
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RAW_DATA_DIR, load_anchor_config
from core.ble import list_serial_ports, calculate_log_distance
from collector.geometry import snap_to_grid, euclidean_distance
from collector.environment import (
    EnvironmentLayout,
    ExperimentArea,
    AnchorNode,
    TargetNode,
    BarrierObject,
    BARRIER_TYPES,
    BARRIER_SHAPES,
)
from collector.canvas_editor import CanvasEditor
from collector.session_manager import SessionManager, SessionConfig, TARGET_DISTANCES
from collector.recording import RecordingEngine
from collector.validation import QualityVerdict


class DataCollectorApp:
    """Dedicated desktop GUI for BLE experimental layout building and dataset acquisition."""

    THEME = {
        "bg": "#121214",          # Deep Neutral Dark
        "panel": "#18181B",       # Zinc 900
        "card": "#27272A",        # Zinc 800
        "card_hover": "#323238",
        "border": "#3F3F46",      # Zinc 700
        "text": "#FAFAFA",        # Zinc 50
        "subtext": "#A1A1AA",     # Zinc 400
        "accent": "#10B981",      # Emerald 500
        "accent_hover": "#059669",
        "green": "#10B981",       # Emerald 500
        "green_dark": "#064E3B",
        "red": "#EF4444",         # Rose 500
        "red_dark": "#7F1D1D",
        "amber": "#F59E0B",       # Amber 500
        "amber_dark": "#78350F",
        "terminal_bg": "#09090B",
    }

    ANCHOR_COLORS = {
        "ANCHOR_01": "#10B981",  # Node A (SW) - Emerald
        "ANCHOR_02": "#F59E0B",  # Node B (SE) - Amber
        "ANCHOR_03": "#F43F5E",  # Node C (NW) - Rose
        "ANCHOR_04": "#14B8A6",  # Node D (NE) - Teal
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("📡 BLE RTLS — Visual Experiment Builder & Data Collector")
        self.root.geometry("1300x860")
        self.root.minsize(1100, 740)
        self.root.configure(bg=self.THEME["bg"])

        # Core engines
        self.session_manager = SessionManager()
        self.packet_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.recording_engine = RecordingEngine(self.packet_queue)

        # Form & Acquisition Variables
        today_tag = datetime.date.today().strftime("%Y%m%d")
        self.session_name_var = tk.StringVar(value=f"survey_{today_tag}_01")
        self.target_mac_var = tk.StringVar(value="52:06:26:03:01:DA")
        self.distance_var = tk.DoubleVar(value=1.0)
        self.anchor_var = tk.StringVar(value="ALL_ANCHORS")
        self.condition_var = tk.StringVar(value="Line-of-Sight (LOS)")
        self.obstacle_var = tk.StringVar(value="No")
        self.obstacle_type_var = tk.StringVar(value="None")
        self.motion_var = tk.StringVar(value="stationary")
        self.tag_height_var = tk.DoubleVar(value=0.96)
        self.notes_var = tk.StringVar(value="Visual layout 2D calibrated grid")
        self.target_samples_var = tk.IntVar(value=300)
        self.port_var = tk.StringVar(value="Wireless Wi-Fi (UDP :5005)")
        self.baud_var = tk.IntVar(value=115200)

        # Area & Visual Builder Variables
        self.area_width_var = tk.DoubleVar(value=5.0)
        self.area_height_var = tk.DoubleVar(value=5.0)
        self.grid_spacing_var = tk.DoubleVar(value=1.0)

        # Object Inspector Variables
        self.obj_name_var = tk.StringVar(value="")
        self.obj_x_var = tk.DoubleVar(value=0.0)
        self.obj_y_var = tk.DoubleVar(value=0.0)
        self.obj_w_var = tk.DoubleVar(value=1.0)
        self.obj_d_var = tk.DoubleVar(value=0.2)
        self.obj_rot_var = tk.DoubleVar(value=0.0)
        self.obj_type_var = tk.StringVar(value="Concrete wall")
        self.obj_shape_var = tk.StringVar(value="Rectangle")
        self.obj_blocks_los_var = tk.BooleanVar(value=True)

        # Canvas View Options
        self.snap_var = tk.BooleanVar(value=True)
        self.show_paths_var = tk.BooleanVar(value=True)
        self.show_dist_var = tk.BooleanVar(value=True)
        self.show_los_var = tk.BooleanVar(value=True)

        # Settings
        self.variance_threshold_var = tk.DoubleVar(value=5.5)
        self.stabilize_duration_var = tk.IntVar(value=5)

        # UI & State tracking
        self.active_tab = "collect"
        self.rssi_history: List[Tuple[float, str, int]] = []
        self.anchor_telemetry_ui: Dict[str, Dict[str, tk.Label]] = {}
        self.los_matrix_ui: Dict[str, Dict[str, tk.Label]] = {}
        self.form_widgets: List[tk.Widget] = []
        self.tool_buttons: Dict[str, tk.Button] = {}
        self.stabilize_countdown = 0

        self._configure_styles()
        self._build_shell()

        # Force immediate window layout realization and initial canvas render
        self.root.update_idletasks()
        if hasattr(self, "canvas_editor") and hasattr(self.canvas_editor, "canvas"):
            cw = self.canvas_editor.canvas.winfo_width()
            ch = self.canvas_editor.canvas.winfo_height()
            if cw > 10 and ch > 10:
                self.canvas_editor.coords.set_canvas_size(cw, ch)
            self.canvas_editor.redraw()

        # Bind Global Keyboard Shortcuts
        self.root.bind("<Delete>", lambda e: self._delete_selected_canvas_object())
        self.root.bind("<BackSpace>", lambda e: self._delete_selected_canvas_object())
        self.root.bind("<Escape>", lambda e: self._set_canvas_tool("select"))

        # Initial layout computation
        self._on_canvas_layout_changed()

        # Check for unfinalized sessions on launch (crash recovery)
        self.root.after(300, self._check_crash_recovery)

        # Periodic poller for packet queue and UI
        self.root.after(60, self._process_packet_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        t = self.THEME

        style.configure("TFrame", background=t["bg"])
        style.configure("Panel.TFrame", background=t["panel"])
        style.configure("Card.TFrame", background=t["card"])
        style.configure("TLabel", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=t["panel"], foreground=t["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Muted.TLabel", background=t["panel"], foreground=t["subtext"], font=("Segoe UI", 8))

        style.configure("TCombobox", fieldbackground=t["card"], background=t["card"], foreground=t["text"], padding=3)
        style.configure("TEntry", fieldbackground=t["card"], foreground=t["text"], padding=3)
        style.configure("Treeview", background=t["panel"], foreground=t["text"], fieldbackground=t["panel"], rowheight=22)
        style.configure("Treeview.Heading", background=t["card"], foreground=t["text"], font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", t["accent"])])

    def _build_shell(self) -> None:
        t = self.THEME

        # Top Navigation Bar
        nav_bar = tk.Frame(self.root, bg=t["panel"], height=54)
        nav_bar.pack(fill="x", side="top")
        nav_bar.pack_propagate(False)

        # Title
        title_box = tk.Frame(nav_bar, bg=t["panel"])
        title_box.pack(side="left", padx=16)
        tk.Label(title_box, text="📡 BLE DATA COLLECTOR", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(title_box, text="· Visual Experiment Environment Builder", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="left", padx=8)

        # Navigation Buttons
        self.nav_btns: Dict[str, tk.Button] = {}
        btn_box = tk.Frame(nav_bar, bg=t["panel"])
        btn_box.pack(side="left", padx=20)

        tabs = [
            ("collect", "🗺 Experiment & Collect"),
            ("sessions", "📁 Sessions Browser"),
            ("coverage", "📊 Dataset Coverage"),
            ("settings", "⚙️ Settings"),
        ]
        for tab_id, label in tabs:
            b = tk.Button(
                btn_box, text=label,
                bg=t["accent"] if tab_id == "collect" else t["card"],
                fg="#FFFFFF" if tab_id == "collect" else t["subtext"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                command=lambda tid=tab_id: self._switch_tab(tid),
            )
            b.pack(side="left", padx=3)
            self.nav_btns[tab_id] = b

        # Status Pill on Right
        self.status_pill = tk.Label(
            nav_bar, text="○  IDLE",
            bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8, "bold"), padx=12, pady=4,
        )
        self.status_pill.pack(side="right", padx=16)

        # Main View Container
        self.views_container = tk.Frame(self.root, bg=t["bg"])
        self.views_container.pack(fill="both", expand=True, padx=10, pady=10)

        # View Frames
        self.views: Dict[str, tk.Frame] = {
            "collect": tk.Frame(self.views_container, bg=t["bg"]),
            "sessions": tk.Frame(self.views_container, bg=t["bg"]),
            "coverage": tk.Frame(self.views_container, bg=t["bg"]),
            "settings": tk.Frame(self.views_container, bg=t["bg"]),
        }

        self._build_collect_view(self.views["collect"])
        self._build_sessions_view(self.views["sessions"])
        self._build_coverage_view(self.views["coverage"])
        self._build_settings_view(self.views["settings"])

        self.views["collect"].pack(fill="both", expand=True)

    def _switch_tab(self, target_tab: str) -> None:
        self.active_tab = target_tab
        t = self.THEME
        for tid, btn in self.nav_btns.items():
            if tid == target_tab:
                btn.config(bg=t["accent"], fg="#FFFFFF")
            else:
                btn.config(bg=t["card"], fg=t["subtext"])

        for tid, frame in self.views.items():
            frame.pack_forget()

        self.views[target_tab].pack(fill="both", expand=True)

        if target_tab == "sessions":
            self._refresh_sessions_table()
        elif target_tab == "coverage":
            self._refresh_coverage_view()

    # =========================================================================
    # VIEW 1: ACTIVE COLLECT & VISUAL ENVIRONMENT BUILDER
    # =========================================================================
    def _build_collect_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        # ── 1. Top Master Control Ribbon (Large Controls, Metrics & Wireless Sync) ──
        top_bar = tk.Frame(parent, bg=t["panel"], padx=14, pady=8, highlightthickness=1, highlightbackground=t["border"])
        top_bar.pack(side="top", fill="x", pady=(0, 8))

        # Left Action Buttons Group
        act_group = tk.Frame(top_bar, bg=t["panel"])
        act_group.pack(side="left")

        self.btn_record = tk.Button(
            act_group, text="▶  START RECORDING",
            bg=t["accent"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", padx=14, pady=6,
            command=self._toggle_recording,
        )
        self.btn_record.pack(side="left", padx=(0, 4))

        self.btn_pause = tk.Button(
            act_group, text="⏸ PAUSE",
            bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", padx=10, pady=6, state="disabled",
            command=self._toggle_pause,
        )
        self.btn_pause.pack(side="left", padx=2)

        self.btn_stop = tk.Button(
            act_group, text="⏹ STOP & SAVE",
            bg=t["card"], fg=t["red"], font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", padx=10, pady=6, state="disabled",
            command=self._stop_recording,
        )
        self.btn_stop.pack(side="left", padx=2)

        # Center Metrics Group
        mid_group = tk.Frame(top_bar, bg=t["panel"])
        mid_group.pack(side="left", padx=20)

        sess_box = tk.Frame(mid_group, bg=t["panel"])
        sess_box.pack(side="left", padx=(0, 10))
        tk.Label(sess_box, text="Session ID:", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        ttk.Entry(sess_box, textvariable=self.session_name_var, width=16).pack()

        target_box = tk.Frame(mid_group, bg=t["panel"])
        target_box.pack(side="left", padx=6)
        tk.Label(target_box, text="Target Samples:", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        cb_tgt = ttk.Combobox(target_box, textvariable=self.target_samples_var, values=[100, 300, 500, 1000], width=7, state="readonly")
        cb_tgt.pack()

        stat_box = tk.Frame(mid_group, bg=t["panel"])
        stat_box.pack(side="left", padx=10)
        self.lbl_master_samples = tk.Label(stat_box, text="0 / 300 samples", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold"))
        self.lbl_master_samples.pack(anchor="w")
        self.lbl_master_timer = tk.Label(stat_box, text="Elapsed: 00:00", bg=t["panel"], fg=t["subtext"], font=("Consolas", 8))
        self.lbl_master_timer.pack(anchor="w")

        # Right Stream Source & Wireless Nodes Sync Indicator
        right_group = tk.Frame(top_bar, bg=t["panel"])
        right_group.pack(side="right")

        src_box = tk.Frame(right_group, bg=t["panel"])
        src_box.pack(side="left", padx=(0, 10))
        tk.Label(src_box, text="Data Stream Source:", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.cb_port = ttk.Combobox(
            src_box, textvariable=self.port_var,
            values=["Wireless Wi-Fi (UDP :5005)", "Simulated Stream"],
            state="readonly", width=24,
        )
        self.cb_port.pack()

        self.lbl_master_sync = tk.Label(
            right_group, text="● 4/4 Nodes In Sync",
            bg=t["green_dark"], fg=t["green"], font=("Segoe UI", 8, "bold"), padx=10, pady=5,
        )
        self.lbl_master_sync.pack(side="left", padx=6)

        b_setup = tk.Button(
            right_group, text="⚙ ESP32 Setup", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=4,
            command=self._launch_setup_tool,
        )
        b_setup.pack(side="left")

        # ── 2. Underneath: Map Layout & Canvas Workspace ──────────────────────
        workspace_frame = tk.Frame(parent, bg=t["bg"])
        workspace_frame.pack(fill="both", expand=True)

        left_col = tk.Frame(workspace_frame, bg=t["panel"], width=370, highlightthickness=1, highlightbackground=t["border"])
        left_col.pack(side="left", fill="y", padx=(0, 8))
        left_col.pack_propagate(False)

        right_col = tk.Frame(workspace_frame, bg=t["bg"])
        right_col.pack(side="right", fill="both", expand=True)

        self._build_sidebar_controls(left_col)
        self._build_workspace_and_canvas(right_col)

    def _build_sidebar_controls(self, parent: tk.Frame) -> None:
        t = self.THEME

        scroll_canvas = tk.Canvas(parent, bg=t["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        scroll_content = tk.Frame(scroll_canvas, bg=t["panel"])

        scroll_content.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_window = scroll_canvas.create_window((0, 0), window=scroll_content, anchor="nw", width=348)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_content.bind("<Enter>", lambda _: scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        scroll_content.bind("<Leave>", lambda _: scroll_canvas.unbind_all("<MouseWheel>"))

        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        self.form_widgets = []

        # 1. TEST AREA CONFIGURATION
        self._build_area_section(scroll_content)

        # 2. OBJECT PROPERTIES / INSPECTOR
        self._build_inspector_section(scroll_content)

        # 3. GEOMETRIC PROPAGATION & LOS MATRIX
        self._build_propagation_section(scroll_content)

        # 4. EXPERIMENTAL READINESS & STABILIZATION
        self._build_condition_section(scroll_content)

    def _build_area_section(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=10, pady=6)
        card.pack(fill="x")

        tk.Label(card, text="TEST AREA CONFIGURATION", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

        row1 = tk.Frame(card, bg=t["panel"])
        row1.pack(fill="x", pady=2)

        # Width
        col_w = tk.Frame(row1, bg=t["panel"])
        col_w.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Label(col_w, text="Width (m)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
        e_w = ttk.Entry(col_w, textvariable=self.area_width_var, width=7)
        e_w.pack(fill="x")
        self.form_widgets.append(e_w)

        # Height
        col_h = tk.Frame(row1, bg=t["panel"])
        col_h.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(col_h, text="Height (m)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
        e_h = ttk.Entry(col_h, textvariable=self.area_height_var, width=7)
        e_h.pack(fill="x")
        self.form_widgets.append(e_h)

        # Grid
        col_g = tk.Frame(row1, bg=t["panel"])
        col_g.pack(side="left", fill="x", expand=True, padx=(4, 0))
        tk.Label(col_g, text="Grid (m)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
        e_g = ttk.Entry(col_g, textvariable=self.grid_spacing_var, width=7)
        e_g.pack(fill="x")
        self.form_widgets.append(e_g)

        # Presets row
        preset_row = tk.Frame(card, bg=t["panel"])
        preset_row.pack(fill="x", pady=(5, 2))
        presets = [("3×3m", 3.0, 3.0), ("5×5m", 5.0, 5.0), ("5×10m", 5.0, 10.0), ("10×10m", 10.0, 10.0)]
        for label, pw, ph in presets:
            btn = tk.Button(
                preset_row, text=label, bg=t["card"], fg=t["text"],
                font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=3, pady=2,
                command=lambda w=pw, h=ph: self._set_area_preset(w, h),
            )
            btn.pack(side="left", padx=1, expand=True, fill="x")
            self.form_widgets.append(btn)

        # Apply Area button
        btn_apply = tk.Button(
            card, text="📐 Apply Area Dimensions", bg=t["card"], fg=t["accent"],
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", pady=3,
            command=self._apply_area_dimensions,
        )
        btn_apply.pack(fill="x", pady=(4, 4))
        self.form_widgets.append(btn_apply)

    def _build_inspector_section(self, parent: tk.Frame) -> None:
        t = self.THEME
        self.inspector_card = tk.Frame(parent, bg=t["card"], padx=10, pady=8)
        self.inspector_card.pack(fill="x", padx=2, pady=4)

        self.inspector_header = tk.Label(
            self.inspector_card, text="OBJECT PROPERTIES",
            bg=t["card"], fg=t["accent"], font=("Segoe UI", 9, "bold")
        )
        self.inspector_header.pack(anchor="w")

        self.inspector_body = tk.Frame(self.inspector_card, bg=t["card"])
        self.inspector_body.pack(fill="x", pady=(4, 0))

        # Initial placeholder prompt
        self.inspector_prompt = tk.Label(
            self.inspector_body,
            text="Click an object on the canvas or use the\ntoolbar above to place nodes, target, or barriers.",
            bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8), justify="left"
        )
        self.inspector_prompt.pack(anchor="w", pady=4)

    def _build_propagation_section(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=10, pady=6)
        card.pack(fill="x")

        tk.Label(card, text="GEOMETRIC PROPAGATION & LOS MATRIX", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

        self.los_matrix_ui = {}
        for anc_id in ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]:
            row = tk.Frame(card, bg=t["card"], padx=6, pady=3)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=anc_id, bg=t["card"], fg=self.ANCHOR_COLORS[anc_id], font=("Segoe UI", 8, "bold"), width=9, anchor="w").pack(side="left")

            dist_lbl = tk.Label(row, text="-- m", bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"), width=8, anchor="center")
            dist_lbl.pack(side="left")

            los_pill = tk.Label(row, text="● LOS", bg=t["green_dark"], fg=t["green"], font=("Segoe UI", 7, "bold"), padx=5, pady=1)
            los_pill.pack(side="right")

            self.los_matrix_ui[anc_id] = {
                "dist": dist_lbl,
                "los": los_pill,
            }

    def _build_condition_section(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=10, pady=6)
        card.pack(fill="x")

        tk.Label(card, text="EXPERIMENT CONDITION & READINESS", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

        # Condition: LOS vs NLOS
        tk.Label(card, text="Propagation Environment", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        cb_cond = ttk.Combobox(card, textvariable=self.condition_var, values=["Line-of-Sight (LOS)", "Non-Line-of-Sight (NLOS)"], state="readonly")
        cb_cond.pack(fill="x", pady=(1, 4))
        self.form_widgets.append(cb_cond)

        # Tag height
        tk.Label(card, text="Tag Elevation Height (m)", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        e_h = ttk.Entry(card, textvariable=self.tag_height_var)
        e_h.pack(fill="x", pady=(1, 6))
        self.form_widgets.append(e_h)

        # Pre-flight checklist card
        chk_card = tk.Frame(card, bg=t["card"], padx=8, pady=6)
        chk_card.pack(fill="x", pady=(2, 6))
        tk.Label(chk_card, text="PRE-FLIGHT READINESS", bg=t["card"], fg=t["accent"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.chk_lbls = {}
        checklist_items = [
            ("area", "Test area defined"),
            ("anchors", "4 corner nodes placed"),
            ("target", "Target placed inside area"),
            ("storage", "Storage directory writable"),
        ]
        for key, desc in checklist_items:
            lbl = tk.Label(chk_card, text=f"✔ {desc}", bg=t["card"], fg=t["green"], font=("Segoe UI", 7))
            lbl.pack(anchor="w", pady=1)
            self.chk_lbls[key] = lbl

        # Stabilize button
        self.btn_stabilize = tk.Button(
            card, text="⏳ STABILIZE SIGNAL (5s)",
            bg=t["card"], fg=t["text"], font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", pady=5,
            command=self._start_stabilization,
        )
        self.btn_stabilize.pack(fill="x", pady=2)

    def _launch_setup_tool(self) -> None:
        """Launch the standalone ESP32 Wireless Provisioner & Flasher GUI."""
        from core.config import PYTHON_EXE, WORKSPACE_ROOT
        setup_script = WORKSPACE_ROOT / "setup.py"
        if not setup_script.exists():
            setup_script = PROJECT_ROOT / "collector" / "setup_gui.py"
        subprocess.Popen([PYTHON_EXE, str(setup_script)], cwd=str(WORKSPACE_ROOT))

    def _build_workspace_and_canvas(self, parent: tk.Frame) -> None:
        t = self.THEME

        # 1. Canvas Toolbar on top
        tb = tk.Frame(parent, bg=t["panel"], height=38, padx=8, pady=3)
        tb.pack(side="top", fill="x", pady=(0, 4))
        tb.pack_propagate(False)

        self.tool_buttons = {}
        tools = [
            ("select", "↖ Select"),
            ("add_node", "🔵 + Node"),
            ("add_target", "🎯 + Target"),
            ("add_barrier", "🧱 + Barrier"),
        ]
        for tid, tlabel in tools:
            btn = tk.Button(
                tb, text=tlabel,
                bg=t["accent"] if tid == "select" else t["card"],
                fg="#FFFFFF" if tid == "select" else t["text"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=9, pady=2,
                command=lambda m=tid: self._set_canvas_tool(m),
            )
            btn.pack(side="left", padx=2)
            self.tool_buttons[tid] = btn

        btn_del = tk.Button(
            tb, text="🗑 Delete", bg=t["card"], fg=t["red"],
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=8, pady=2,
            command=self._delete_selected_canvas_object,
        )
        btn_del.pack(side="left", padx=(6, 12))

        # View Toggles
        cb_snap = tk.Checkbutton(
            tb, text="Snap to Grid", variable=self.snap_var,
            bg=t["panel"], fg=t["text"], selectcolor=t["card"],
            activebackground=t["panel"], activeforeground=t["text"],
            font=("Segoe UI", 8), command=self._on_view_toggle,
        )
        cb_snap.pack(side="left", padx=3)

        cb_paths = tk.Checkbutton(
            tb, text="Show Paths", variable=self.show_paths_var,
            bg=t["panel"], fg=t["text"], selectcolor=t["card"],
            activebackground=t["panel"], activeforeground=t["text"],
            font=("Segoe UI", 8), command=self._on_view_toggle,
        )
        cb_paths.pack(side="left", padx=3)

        cb_dist = tk.Checkbutton(
            tb, text="Show Distances", variable=self.show_dist_var,
            bg=t["panel"], fg=t["text"], selectcolor=t["card"],
            activebackground=t["panel"], activeforeground=t["text"],
            font=("Segoe UI", 8), command=self._on_view_toggle,
        )
        cb_dist.pack(side="left", padx=3)

        cb_los = tk.Checkbutton(
            tb, text="Show LOS Status", variable=self.show_los_var,
            bg=t["panel"], fg=t["text"], selectcolor=t["card"],
            activebackground=t["panel"], activeforeground=t["text"],
            font=("Segoe UI", 8), command=self._on_view_toggle,
        )
        cb_los.pack(side="left", padx=3)

        btn_reset = tk.Button(
            tb, text="🔄 Reset Layout", bg=t["card"], fg=t["subtext"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=2,
            command=self._reset_default_layout,
        )
        btn_reset.pack(side="right", padx=4)

        # 2. Bottom Telemetry Strip & Incoming Observation Feed (docked to bottom first)
        self._build_bottom_telemetry_and_feed(parent)

        # 3. The 2D Interactive Canvas Editor Container (expands to fill all remaining workspace)
        canvas_container = tk.Frame(parent, bg="#070F1E", highlightthickness=2, highlightbackground="#0284C7")
        canvas_container.pack(side="top", fill="both", expand=True, pady=(0, 4))

        self.canvas_editor = CanvasEditor(
            canvas_container,
            on_selection_changed=self._on_canvas_selection_changed,
            on_layout_changed=self._on_canvas_layout_changed,
        )

    def _build_bottom_telemetry_and_feed(self, parent: tk.Frame) -> None:
        t = self.THEME
        bottom_frame = tk.Frame(parent, bg=t["bg"])
        bottom_frame.pack(side="bottom", fill="x")

        # 4-Anchor Telemetry Cards Row
        anc_row = tk.Frame(bottom_frame, bg=t["bg"])
        anc_row.pack(fill="x", pady=(0, 4))
        for i in range(4):
            anc_row.columnconfigure(i, weight=1, uniform="anc")

        anchors = ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]
        for idx, anc_id in enumerate(anchors):
            card = tk.Frame(anc_row, bg=t["panel"], padx=8, pady=6)
            card.grid(row=0, column=idx, sticky="nsew", padx=2)

            top = tk.Frame(card, bg=t["panel"])
            top.pack(fill="x")
            tk.Label(top, text=anc_id, bg=t["panel"], fg=self.ANCHOR_COLORS[anc_id], font=("Segoe UI", 8, "bold")).pack(side="left")
            status_lbl = tk.Label(top, text="● READY", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7, "bold"))
            status_lbl.pack(side="right")

            rssi_val_lbl = tk.Label(card, text="-- dBm", bg=t["panel"], fg=t["text"], font=("Segoe UI", 12, "bold"))
            rssi_val_lbl.pack(anchor="w", pady=(1, 0))

            stats_lbl = tk.Label(card, text="μ: -- | σ: -- | 0 pkts", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7))
            stats_lbl.pack(anchor="w")

            rate_lbl = tk.Label(card, text="Rate: 0.00 Hz", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 7))
            rate_lbl.pack(anchor="w")

            self.anchor_telemetry_ui[anc_id] = {
                "status": status_lbl,
                "rssi": rssi_val_lbl,
                "stats": stats_lbl,
                "rate": rate_lbl,
            }

        # Quality Banner & Progress
        bar_card = tk.Frame(bottom_frame, bg=t["panel"], padx=10, pady=4)
        bar_card.pack(fill="x", pady=(0, 4))

        self.quality_banner = tk.Label(
            bar_card, text="● Signal Analyzer Ready. Ingesting stream to evaluate signal variance and anchor liveliness.",
            bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8), anchor="w",
        )
        self.quality_banner.pack(fill="x", pady=(0, 2))

        self.prog_text_lbl = tk.Label(
            bar_card, text="Valid Samples: 0 / 300 (0%) | Raw: 0 | Rate: 0.00 Hz | Elapsed: 00:00",
            bg=t["panel"], fg=t["text"], font=("Segoe UI", 8, "bold"), anchor="w",
        )
        self.prog_text_lbl.pack(fill="x", pady=(0, 2))

        self.progress_bar = ttk.Progressbar(bar_card, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x")

        # Verbatim Incoming Raw Observations Feed Table
        feed_card = tk.Frame(bottom_frame, bg=t["panel"], padx=8, pady=4)
        feed_card.pack(fill="x")

        cols = ("time", "anchor", "mac", "rssi", "dist", "obstacle", "flag")
        self.feed_tree = ttk.Treeview(feed_card, columns=cols, show="headings", height=3)
        self.feed_tree.heading("time", text="Timestamp")
        self.feed_tree.heading("anchor", text="Anchor ID")
        self.feed_tree.heading("mac", text="Target Device MAC")
        self.feed_tree.heading("rssi", text="RSSI")
        self.feed_tree.heading("dist", text="Ground Truth")
        self.feed_tree.heading("obstacle", text="Obstacle")
        self.feed_tree.heading("flag", text="Quality Status")

        self.feed_tree.column("time", width=85, anchor="center")
        self.feed_tree.column("anchor", width=90, anchor="center")
        self.feed_tree.column("mac", width=140, anchor="center")
        self.feed_tree.column("rssi", width=70, anchor="center")
        self.feed_tree.column("dist", width=85, anchor="center")
        self.feed_tree.column("obstacle", width=90, anchor="center")
        self.feed_tree.column("flag", width=120, anchor="w")

        self.feed_tree.pack(fill="x")

    # =========================================================================
    # VIEW 2: SESSIONS BROWSER & SAMPLE PREVIEW
    # =========================================================================
    def _build_sessions_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        top_bar = tk.Frame(parent, bg=t["panel"], padx=14, pady=10)
        top_bar.pack(fill="x", pady=(0, 10))

        tk.Label(top_bar, text="📁 RECORDED DATASET SESSIONS", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(side="left")

        tk.Button(
            top_bar, text="📂 Open Raw Folder", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._open_raw_folder,
        ).pack(side="right", padx=4)

        tk.Button(
            top_bar, text="🔄 Refresh", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._refresh_sessions_table,
        ).pack(side="right", padx=4)

        tk.Button(
            top_bar, text="🗺 Load Visual Layout to Editor", bg=t["accent"], fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._load_session_layout_to_editor,
        ).pack(side="right", padx=4)

        tk.Button(
            top_bar, text="🔍 Preview Raw Samples", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._preview_selected_session,
        ).pack(side="right", padx=4)

        table_frame = tk.Frame(parent, bg=t["panel"], padx=14, pady=10)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("filename", "modified", "distance", "condition", "obstacle", "samples", "size")
        self.sessions_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        self.sessions_tree.heading("filename", text="Dataset Filename")
        self.sessions_tree.heading("modified", text="Date / Modified")
        self.sessions_tree.heading("distance", text="Distance")
        self.sessions_tree.heading("condition", text="Condition")
        self.sessions_tree.heading("obstacle", text="Obstacle")
        self.sessions_tree.heading("samples", text="Samples")
        self.sessions_tree.heading("size", text="File Size")

        self.sessions_tree.column("filename", width=220, anchor="w")
        self.sessions_tree.column("modified", width=140, anchor="center")
        self.sessions_tree.column("distance", width=80, anchor="center")
        self.sessions_tree.column("condition", width=180, anchor="w")
        self.sessions_tree.column("obstacle", width=100, anchor="center")
        self.sessions_tree.column("samples", width=80, anchor="center")
        self.sessions_tree.column("size", width=80, anchor="center")

        self.sessions_tree.pack(fill="both", expand=True)
        self.sessions_tree.bind("<Double-1>", lambda e: self._preview_selected_session())

        # Raw Samples Preview Card
        self.preview_card = tk.Frame(parent, bg=t["panel"], padx=14, pady=10)
        self.preview_card.pack(fill="both", expand=True)

        self.preview_title = tk.Label(self.preview_card, text="RAW SAMPLE PREVIEW (SELECT A SESSION ABOVE)", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold"))
        self.preview_title.pack(anchor="w", pady=(0, 4))

        self.preview_tree = ttk.Treeview(self.preview_card, show="headings", height=6)
        self.preview_tree.pack(fill="both", expand=True)

    def _refresh_sessions_table(self) -> None:
        for row in self.sessions_tree.get_children():
            self.sessions_tree.delete(row)

        sessions = self.session_manager.get_past_sessions()
        for s in sessions:
            self.sessions_tree.insert(
                "", "end", values=(
                    s["filename"],
                    s["modified"],
                    s["distance"],
                    s["condition"],
                    s["obstacle_type"],
                    f"{s['samples']:,}",
                    f"{s['size_kb']} KB",
                ),
            )

    def _preview_selected_session(self) -> None:
        sel = self.sessions_tree.selection()
        if not sel:
            messagebox.showinfo("Select Session", "Please select a dataset session from the table to preview.")
            return

        item = self.sessions_tree.item(sel[0])
        filename = item["values"][0]
        csv_path = RAW_DATA_DIR / filename
        if not csv_path.exists():
            return

        headers, rows = self.session_manager.read_session_preview(csv_path, max_rows=50)
        self.preview_title.config(text=f"RAW SAMPLE PREVIEW — {filename} (FIRST {len(rows)} ROWS)")

        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_tree["columns"] = headers
        for h in headers:
            self.preview_tree.heading(h, text=h)
            self.preview_tree.column(h, width=110, anchor="center")

        for r in rows:
            self.preview_tree.insert("", "end", values=r)

    def _load_session_layout_to_editor(self) -> None:
        sel = self.sessions_tree.selection()
        if not sel:
            messagebox.showinfo("Select Session", "Please select a dataset session to load its visual layout.")
            return

        item = self.sessions_tree.item(sel[0])
        filename = item["values"][0]
        csv_path = RAW_DATA_DIR / filename

        layout_dict = self.session_manager.get_session_layout(csv_path)
        if not layout_dict:
            messagebox.showwarning(
                "No Visual Layout",
                f"Session '{filename}' does not have an attached 2D experimental environment layout snapshot."
            )
            return

        try:
            layout = EnvironmentLayout.from_dict(layout_dict)
            self.canvas_editor.set_layout(layout)
            self.area_width_var.set(layout.area.width_m)
            self.area_height_var.set(layout.area.height_m)
            self.grid_spacing_var.set(layout.area.grid_spacing_m)
            self._switch_tab("collect")
            self._on_canvas_layout_changed()
            messagebox.showinfo(
                "Layout Reconstructed",
                f"Successfully loaded 2D experimental layout for session '{filename}'!\n\n"
                f"• Dimensions: {layout.area.width_m}m × {layout.area.height_m}m (grid {layout.area.grid_spacing_m}m)\n"
                f"• Anchors: {len(layout.anchors)} | Barriers: {len(layout.barriers)}\n"
                f"• Target Ground Truth: ({layout.target.x_m}m, {layout.target.y_m}m)"
            )
        except Exception as e:
            messagebox.showerror("Failed to Load Layout", f"Error reconstructing layout: {e}")

    # =========================================================================
    # VIEW 3: DATASET COVERAGE AUDIT
    # =========================================================================
    def _build_coverage_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        top = tk.Frame(parent, bg=t["panel"], padx=14, pady=10)
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="📊 DATASET COVERAGE & CLASS BALANCE", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Button(
            top, text="🔄 Recalculate Coverage", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
            command=self._refresh_coverage_view,
        ).pack(side="right")

        content = tk.Frame(parent, bg=t["bg"])
        content.pack(fill="both", expand=True)

        left_box = tk.Frame(content, bg=t["panel"], padx=16, pady=12)
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(left_box, text="GROUND-TRUTH DISTANCE DISTRIBUTION", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        self.coverage_canvas = tk.Canvas(left_box, bg="#0B132B", height=240, highlightthickness=0)
        self.coverage_canvas.pack(fill="x", pady=(0, 10))

        self.imbalance_box = tk.Frame(left_box, bg=t["card"], padx=12, pady=8)
        self.imbalance_box.pack(fill="x")
        self.imbalance_lbl = tk.Label(self.imbalance_box, text="● Analyzing dataset coverage...", bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8), justify="left")
        self.imbalance_lbl.pack(anchor="w")

        right_box = tk.Frame(content, bg=t["panel"], padx=16, pady=12)
        right_box.pack(side="right", fill="both", expand=True, padx=(6, 0))

        tk.Label(right_box, text="4-ANCHOR OBSERVATION BALANCE", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.anc_tree = ttk.Treeview(right_box, columns=("anchor", "samples", "share"), show="headings", height=5)
        self.anc_tree.heading("anchor", text="Anchor ID")
        self.anc_tree.heading("samples", text="Total Observations")
        self.anc_tree.heading("share", text="Share (%)")
        self.anc_tree.pack(fill="x", pady=(0, 10))

        tk.Label(right_box, text="ENVIRONMENTAL DIVERSITY", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.cond_tree = ttk.Treeview(right_box, columns=("cond", "count"), show="headings", height=5)
        self.cond_tree.heading("cond", text="Condition / Obstacle")
        self.cond_tree.heading("count", text="Samples")
        self.cond_tree.pack(fill="both", expand=True)

    def _refresh_coverage_view(self) -> None:
        cov = self.session_manager.get_dataset_coverage()
        total = cov["total_samples"]

        c = self.coverage_canvas
        c.delete("all")
        w = c.winfo_width()
        if w <= 10:
            w = 500

        d_counts = cov["distance_counts"]
        max_c = max(max(d_counts.values()) if d_counts else 1, 1)

        y = 20
        row_h = 32
        for dist_key in [0.5, 1.0, 2.0, 3.0, 5.0, "Other"]:
            cnt = d_counts.get(dist_key, 0)
            tag = f"{dist_key}m" if isinstance(dist_key, (int, float)) else dist_key
            bar_w = int((w - 140) * (cnt / max_c))

            c.create_text(40, y + 10, text=tag, fill="#F8FAFC", font=("Segoe UI", 9, "bold"), anchor="w")
            color = self.THEME["accent"] if cnt > 0 else "#475569"
            c.create_rectangle(90, y + 2, 90 + bar_w, y + 20, fill=color, outline="")
            c.create_text(100 + bar_w, y + 11, text=f"{cnt:,} pkts", fill="#94A3B8", font=("Segoe UI", 8), anchor="w")
            y += row_h

        warns = cov["imbalance_warnings"]
        if warns:
            txt = "⚠ DATASET IMBALANCE DETECTED:\n" + "\n".join(f"• {w}" for w in warns)
            self.imbalance_lbl.config(text=txt, fg=self.THEME["amber"])
        else:
            self.imbalance_lbl.config(text="✔ Dataset coverage is balanced across all canonical distance presets and 4 anchors.", fg=self.THEME["green"])

        self.anc_tree.delete(*self.anc_tree.get_children())
        anc_counts = cov["anchor_counts"]
        for anc_id in sorted(anc_counts.keys()):
            cnt = anc_counts[anc_id]
            pct = f"{(cnt / total * 100):.1f}%" if total > 0 else "0%"
            self.anc_tree.insert("", "end", values=(anc_id, f"{cnt:,}", pct))

        self.cond_tree.delete(*self.cond_tree.get_children())
        for cond_name, cnt in cov["condition_counts"].items():
            self.cond_tree.insert("", "end", values=(cond_name, f"{cnt:,}"))

    # =========================================================================
    # VIEW 4: SETTINGS
    # =========================================================================
    def _build_settings_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        box = tk.Frame(parent, bg=t["panel"], padx=20, pady=16)
        box.pack(fill="x", pady=(0, 10))

        tk.Label(box, text="⚙️ DATA ACQUISITION SETTINGS", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        tk.Label(box, text="Raw Dataset Storage Directory", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        e_dir = ttk.Entry(box)
        e_dir.insert(0, str(RAW_DATA_DIR))
        e_dir.config(state="readonly")
        e_dir.pack(fill="x", pady=(0, 8))

        tk.Label(box, text="Quality Alert Variance Threshold (dBm standard deviation)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        ttk.Entry(box, textvariable=self.variance_threshold_var, width=10).pack(anchor="w", pady=(0, 8))

        tk.Label(box, text="Pre-Recording Signal Stabilization Duration (seconds)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        ttk.Entry(box, textvariable=self.stabilize_duration_var, width=10).pack(anchor="w", pady=(0, 8))

        tk.Label(box, text="Serial Hardware Baud Rate", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        ttk.Combobox(box, textvariable=self.baud_var, values=[9600, 115200, 230400, 921600], state="readonly").pack(anchor="w", pady=(0, 8))

    # =========================================================================
    # CANVAS & VISUAL BUILDER HANDLERS
    # =========================================================================
    def _set_area_preset(self, width: float, height: float) -> None:
        self.area_width_var.set(width)
        self.area_height_var.set(height)
        self._apply_area_dimensions()

    def _apply_area_dimensions(self) -> None:
        try:
            w = max(1.0, float(self.area_width_var.get()))
            h = max(1.0, float(self.area_height_var.get()))
            g = max(0.2, float(self.grid_spacing_var.get()))
        except ValueError:
            messagebox.showwarning("Invalid Dimensions", "Please enter valid numeric dimensions in meters.")
            return

        self.canvas_editor.layout.area.width_m = w
        self.canvas_editor.layout.area.height_m = h
        self.canvas_editor.layout.area.grid_spacing_m = g
        self.canvas_editor.coords.set_dimensions(w, h)
        self.canvas_editor.render()
        self._on_canvas_layout_changed()

    def _set_canvas_tool(self, tool_mode: str) -> None:
        t = self.THEME
        self.canvas_editor.set_tool_mode(tool_mode)
        for tid, btn in self.tool_buttons.items():
            if tid == tool_mode:
                btn.config(bg=t["accent"], fg="#FFFFFF")
            else:
                btn.config(bg=t["card"], fg=t["text"])

    def _delete_selected_canvas_object(self) -> None:
        if self.canvas_editor.is_locked:
            return
        self.canvas_editor.delete_selected()

    def _reset_default_layout(self) -> None:
        if self.canvas_editor.is_locked:
            return
        if messagebox.askyesno("Reset Layout", "Reset experimental environment layout to default 5×5m area and 4 corner anchors?"):
            self.canvas_editor.set_layout(EnvironmentLayout.create_default())
            self.area_width_var.set(5.0)
            self.area_height_var.set(5.0)
            self.grid_spacing_var.set(1.0)
            self._on_canvas_layout_changed()

    def _on_view_toggle(self) -> None:
        self.canvas_editor.snap_to_grid = self.snap_var.get()
        self.canvas_editor.show_paths = self.show_paths_var.get()
        self.canvas_editor.show_distances = self.show_dist_var.get()
        self.canvas_editor.show_los = self.show_los_var.get()
        self.canvas_editor.render()

    def _on_canvas_selection_changed(self, *args: Any) -> None:
        obj = args[1] if len(args) == 2 else (args[0] if args else None)
        # Revert tool buttons highlight if canvas reverted to select
        if self.canvas_editor.tool_mode == "select":
            t = self.THEME
            for tid, btn in self.tool_buttons.items():
                if tid == "select":
                    btn.config(bg=t["accent"], fg="#FFFFFF")
                else:
                    btn.config(bg=t["card"], fg=t["text"])

        # Update Inspector Widgets
        self._update_inspector_for_selection(obj)

    def _update_inspector_for_selection(self, obj: Any) -> None:
        for child in self.inspector_body.winfo_children():
            child.destroy()

        t = self.THEME
        if obj is None:
            self.inspector_header.config(text="OBJECT PROPERTIES")
            tk.Label(
                self.inspector_body,
                text="Click an object on the canvas or use the\ntoolbar above to place nodes, target, or barriers.",
                bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8), justify="left",
            ).pack(anchor="w", pady=4)
            return

        if isinstance(obj, AnchorNode):
            self.inspector_header.config(text=f"ANCHOR: {obj.anchor_id}")
            self.obj_name_var.set(obj.label)
            self.obj_x_var.set(round(obj.x_m, 2))
            self.obj_y_var.set(round(obj.y_m, 2))

            tk.Label(self.inspector_body, text="Node Label", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
            e_lbl = ttk.Entry(self.inspector_body, textvariable=self.obj_name_var)
            e_lbl.pack(fill="x", pady=(0, 3))
            self.form_widgets.append(e_lbl)

            coord_row = tk.Frame(self.inspector_body, bg=t["card"])
            coord_row.pack(fill="x", pady=2)
            tk.Label(coord_row, text="X (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_x = ttk.Entry(coord_row, textvariable=self.obj_x_var, width=6)
            e_x.pack(side="left", padx=(2, 6))
            self.form_widgets.append(e_x)

            tk.Label(coord_row, text="Y (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_y = ttk.Entry(coord_row, textvariable=self.obj_y_var, width=6)
            e_y.pack(side="left", padx=2)
            self.form_widgets.append(e_y)

            b_apply = tk.Button(
                self.inspector_body, text="Update Node", bg=t["panel"], fg=t["accent"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", pady=3,
                command=lambda: self._apply_node_properties(obj),
            )
            b_apply.pack(fill="x", pady=(4, 2))
            self.form_widgets.append(b_apply)

        elif isinstance(obj, TargetNode):
            self.inspector_header.config(text=f"TARGET: {obj.target_id}")
            self.obj_name_var.set(obj.mac)
            self.obj_x_var.set(round(obj.x_m, 2))
            self.obj_y_var.set(round(obj.y_m, 2))

            tk.Label(self.inspector_body, text="Device MAC", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
            e_mac = ttk.Entry(self.inspector_body, textvariable=self.obj_name_var)
            e_mac.pack(fill="x", pady=(0, 3))
            self.form_widgets.append(e_mac)

            coord_row = tk.Frame(self.inspector_body, bg=t["card"])
            coord_row.pack(fill="x", pady=2)
            tk.Label(coord_row, text="X (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_x = ttk.Entry(coord_row, textvariable=self.obj_x_var, width=6)
            e_x.pack(side="left", padx=(2, 6))
            self.form_widgets.append(e_x)

            tk.Label(coord_row, text="Y (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_y = ttk.Entry(coord_row, textvariable=self.obj_y_var, width=6)
            e_y.pack(side="left", padx=2)
            self.form_widgets.append(e_y)

            b_apply = tk.Button(
                self.inspector_body, text="Update Target", bg=t["panel"], fg=t["accent"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", pady=3,
                command=lambda: self._apply_target_properties(obj),
            )
            b_apply.pack(fill="x", pady=(4, 2))
            self.form_widgets.append(b_apply)

        elif isinstance(obj, BarrierObject):
            self.inspector_header.config(text=f"BARRIER: {obj.name}")
            self.obj_name_var.set(obj.name)
            self.obj_type_var.set(obj.obstacle_type)
            self.obj_shape_var.set(obj.shape)
            self.obj_x_var.set(round(obj.x_m, 2))
            self.obj_y_var.set(round(obj.y_m, 2))
            self.obj_w_var.set(round(obj.width_m, 2))
            self.obj_d_var.set(round(obj.depth_m, 2))
            self.obj_rot_var.set(round(obj.rotation_deg, 1))
            self.obj_blocks_los_var.set(obj.blocks_los)

            tk.Label(self.inspector_body, text="Barrier Name", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
            e_name = ttk.Entry(self.inspector_body, textvariable=self.obj_name_var)
            e_name.pack(fill="x", pady=(0, 2))
            self.form_widgets.append(e_name)

            tk.Label(self.inspector_body, text="Material / Type", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
            cb_type = ttk.Combobox(self.inspector_body, textvariable=self.obj_type_var, values=BARRIER_TYPES, state="readonly")
            cb_type.pack(fill="x", pady=(0, 2))
            self.form_widgets.append(cb_type)

            tk.Label(self.inspector_body, text="Geometry Shape", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(anchor="w")
            cb_shape = ttk.Combobox(self.inspector_body, textvariable=self.obj_shape_var, values=BARRIER_SHAPES, state="readonly")
            cb_shape.pack(fill="x", pady=(0, 2))
            self.form_widgets.append(cb_shape)

            coord_row = tk.Frame(self.inspector_body, bg=t["card"])
            coord_row.pack(fill="x", pady=2)
            tk.Label(coord_row, text="X (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_x = ttk.Entry(coord_row, textvariable=self.obj_x_var, width=5)
            e_x.pack(side="left", padx=(1, 4))
            self.form_widgets.append(e_x)

            tk.Label(coord_row, text="Y (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_y = ttk.Entry(coord_row, textvariable=self.obj_y_var, width=5)
            e_y.pack(side="left", padx=1)
            self.form_widgets.append(e_y)

            dim_row = tk.Frame(self.inspector_body, bg=t["card"])
            dim_row.pack(fill="x", pady=2)
            tk.Label(dim_row, text="W/L (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_w = ttk.Entry(dim_row, textvariable=self.obj_w_var, width=5)
            e_w.pack(side="left", padx=(1, 4))
            self.form_widgets.append(e_w)

            tk.Label(dim_row, text="D/T (m):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_d = ttk.Entry(dim_row, textvariable=self.obj_d_var, width=5)
            e_d.pack(side="left", padx=(1, 4))
            self.form_widgets.append(e_d)

            tk.Label(dim_row, text="Rot (°):", bg=t["card"], fg=t["text"], font=("Segoe UI", 8)).pack(side="left")
            e_r = ttk.Entry(dim_row, textvariable=self.obj_rot_var, width=5)
            e_r.pack(side="left", padx=1)
            self.form_widgets.append(e_r)

            cb_los = tk.Checkbutton(
                self.inspector_body, text="Blocks Line-of-Sight (LOS)",
                variable=self.obj_blocks_los_var, bg=t["card"], fg=t["text"],
                selectcolor=t["panel"], activebackground=t["card"], activeforeground=t["text"],
                font=("Segoe UI", 8)
            )
            cb_los.pack(anchor="w", pady=2)
            self.form_widgets.append(cb_los)

            btn_box = tk.Frame(self.inspector_body, bg=t["card"])
            btn_box.pack(fill="x", pady=(4, 2))

            b_apply = tk.Button(
                btn_box, text="Apply Geometry", bg=t["panel"], fg=t["accent"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=3,
                command=lambda: self._apply_barrier_properties(obj),
            )
            b_apply.pack(side="left", expand=True, fill="x", padx=(0, 2))
            self.form_widgets.append(b_apply)

            b_del = tk.Button(
                btn_box, text="🗑 Delete", bg=t["panel"], fg=t["red"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=3,
                command=self._delete_selected_canvas_object,
            )
            b_del.pack(side="right", expand=True, fill="x", padx=(2, 0))
            self.form_widgets.append(b_del)

    def _apply_node_properties(self, obj: AnchorNode) -> None:
        obj.label = self.obj_name_var.get()
        try:
            obj.x_m = float(self.obj_x_var.get())
            obj.y_m = float(self.obj_y_var.get())
        except ValueError:
            pass
        self.canvas_editor.render()
        self._on_canvas_layout_changed()

    def _apply_target_properties(self, obj: TargetNode) -> None:
        obj.mac = self.obj_name_var.get()
        try:
            obj.x_m = float(self.obj_x_var.get())
            obj.y_m = float(self.obj_y_var.get())
        except ValueError:
            pass
        self.target_mac_var.set(obj.mac)
        self.canvas_editor.render()
        self._on_canvas_layout_changed()

    def _apply_barrier_properties(self, obj: BarrierObject) -> None:
        obj.name = self.obj_name_var.get()
        obj.obstacle_type = self.obj_type_var.get()
        obj.shape = self.obj_shape_var.get()
        try:
            obj.x_m = float(self.obj_x_var.get())
            obj.y_m = float(self.obj_y_var.get())
            obj.width_m = float(self.obj_w_var.get())
            obj.depth_m = float(self.obj_d_var.get())
            obj.rotation_deg = float(self.obj_rot_var.get())
        except ValueError:
            pass
        obj.blocks_los = self.obj_blocks_los_var.get()
        self.canvas_editor.render()
        self._on_canvas_layout_changed()

    def _on_canvas_layout_changed(self) -> None:
        distances = self.canvas_editor.layout.get_anchor_distances()
        los_status = self.canvas_editor.layout.get_anchor_los_status()

        t = self.THEME
        for anc_id in ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]:
            if anc_id in self.los_matrix_ui:
                dist_val = distances.get(anc_id)
                if dist_val is not None:
                    self.los_matrix_ui[anc_id]["dist"].config(text=f"{dist_val:.2f} m")
                else:
                    self.los_matrix_ui[anc_id]["dist"].config(text="-- m")

                is_los, blocker = los_status.get(anc_id, (True, None))
                if is_los:
                    self.los_matrix_ui[anc_id]["los"].config(text="● LOS", bg=t["green_dark"], fg=t["green"])
                else:
                    b_txt = f"⚠ NLOS ({blocker})" if blocker else "⚠ NLOS"
                    self.los_matrix_ui[anc_id]["los"].config(text=b_txt, bg=t["amber_dark"], fg=t["amber"])

        # Update primary distance variable to reflect distance to selected anchor or average
        anchors = self.canvas_editor.layout.anchors
        target = self.canvas_editor.layout.target
        if anchors and target:
            active_anc = self.anchor_var.get()
            if active_anc in distances:
                self.distance_var.set(round(distances[active_anc], 2))
            elif distances:
                avg_dist = sum(distances.values()) / len(distances)
                self.distance_var.set(round(avg_dist, 2))

        self._update_preflight_checklist()

    def _update_preflight_checklist(self) -> None:
        t = self.THEME
        layout = self.canvas_editor.layout

        area_ok = layout.area.width_m > 0 and layout.area.height_m > 0
        if "area" in self.chk_lbls:
            self.chk_lbls["area"].config(
                text=f"{'✔' if area_ok else '✘'} Area: {layout.area.width_m:.1f}×{layout.area.height_m:.1f}m",
                fg=t["green"] if area_ok else t["red"]
            )

        anc_count = len(layout.anchors)
        anc_ok = anc_count == 4
        if "anchors" in self.chk_lbls:
            self.chk_lbls["anchors"].config(
                text=f"{'✔' if anc_ok else '⚠'} Anchors: {anc_count}/4 configured",
                fg=t["green"] if anc_ok else t["amber"]
            )

        target = layout.target
        target_ok = False
        if target:
            target_ok = (0 <= target.x_m <= layout.area.width_m) and (0 <= target.y_m <= layout.area.height_m)
        if "target" in self.chk_lbls:
            self.chk_lbls["target"].config(
                text=f"{'✔' if target_ok else '✘'} Target at ({target.x_m:.1f}m, {target.y_m:.1f}m)" if target else "✘ No target placed",
                fg=t["green"] if target_ok else t["red"]
            )

    # =========================================================================
    # ACQUISITION LIFECYCLE & THREADING
    # =========================================================================
    def _refresh_serial_ports(self) -> None:
        ports = ["Simulated Stream"] + [p["device"] for p in list_serial_ports()]
        self.cb_port["values"] = ports
        if self.port_var.get() not in ports:
            self.port_var.set("Simulated Stream")

    def _freeze_form_parameters(self, freeze: bool) -> None:
        """Lock experimental geometry and parameters during active collection."""
        state = "disabled" if freeze else "normal"
        readonly_state = "disabled" if freeze else "readonly"
        for w in self.form_widgets:
            if isinstance(w, ttk.Combobox):
                try:
                    w.config(state=readonly_state)
                except Exception:
                    pass
            else:
                try:
                    w.config(state=state)
                except Exception:
                    pass

        for btn in self.tool_buttons.values():
            btn.config(state=state)

        # Lock the 2D visual experiment canvas
        self.canvas_editor.set_locked(freeze)

    def _validate_experiment_readiness(self) -> Tuple[bool, str]:
        """Verify that all geometric, hardware, and directory prerequisites are satisfied before recording."""
        layout = self.canvas_editor.layout

        if layout.area.width_m <= 0 or layout.area.height_m <= 0:
            return False, "Test area dimensions must be positive real numbers in metres."

        if layout.area.grid_spacing_m <= 0 or layout.area.grid_spacing_m > min(layout.area.width_m, layout.area.height_m):
            return False, "Grid spacing must be greater than 0 and less than test area dimensions."

        expected_anchors = ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]
        placed_anchors = [a.id for a in layout.anchors.values() if a.is_placed]
        missing_anchors = [anc for anc in expected_anchors if anc not in placed_anchors]
        if missing_anchors:
            return False, f"⚠ Cannot start recording:\n\n{missing_anchors[0]} is missing.\n\nPlace all four receiver nodes before recording."

        if not layout.target:
            return False, "⚠ Cannot start recording:\n\nNo target beacon tag placed.\nPlace a target on the grid before recording."

        mac = layout.target.mac or self.target_mac_var.get()
        if not mac or len(mac.split(":")) != 6:
            return False, f"⚠ Cannot start recording:\n\nInvalid target MAC address: '{mac}'.\nConfigure a valid 6-octet colon-delimited MAC address."

        if not (0 <= layout.target.x_m <= layout.area.width_m and 0 <= layout.target.y_m <= layout.area.height_m):
            return False, f"⚠ Cannot start recording:\n\nTarget is placed outside test area boundaries: ({layout.target.x_m:.2f}m, {layout.target.y_m:.2f}m).\nMove the target inside the {layout.area.width_m}×{layout.area.height_m}m area."

        for b in layout.barriers:
            if b.width_m <= 0 or b.depth_m <= 0:
                return False, f"⚠ Cannot start recording:\n\nBarrier '{b.name}' has invalid dimensions: {b.width_m}m × {b.depth_m}m.\nDimensions must be positive."
            if not (0 <= b.x_m <= layout.area.width_m and 0 <= b.y_m <= layout.area.height_m):
                return False, f"⚠ Cannot start recording:\n\nBarrier '{b.name}' is positioned outside the test area at ({b.x_m:.2f}m, {b.y_m:.2f}m)."

        if not os.access(str(RAW_DATA_DIR), os.W_OK):
            return False, f"⚠ Raw dataset storage directory '{RAW_DATA_DIR}' is not writable."

        return True, "Ready"

    def _start_stabilization(self) -> None:
        is_ready, ready_err = self._validate_experiment_readiness()
        if not is_ready:
            messagebox.showwarning("Pre-Recording Validation", ready_err)
            return

        env_dict = self.canvas_editor.layout.to_dict()
        ok, msg, session = self.session_manager.create_session(
            name=self.session_name_var.get(),
            mac=self.canvas_editor.layout.target.mac if self.canvas_editor.layout.target else self.target_mac_var.get(),
            distance_m=self.distance_var.get(),
            anchor_id=self.anchor_var.get(),
            condition=self.condition_var.get(),
            tag_height_m=self.tag_height_var.get(),
            notes=self.notes_var.get(),
            target_samples=self.target_samples_var.get(),
            obstacle=self.obstacle_var.get(),
            obstacle_type=self.obstacle_type_var.get(),
            motion=self.motion_var.get(),
            data_source=self.port_var.get(),
            environment_layout=env_dict,
        )
        if not ok or not session:
            messagebox.showerror("Configuration Validation Failed", msg)
            return

        self._freeze_form_parameters(True)
        self.stabilize_countdown = self.stabilize_duration_var.get()
        self.status_pill.config(text=f"⏳ STABILIZING ({self.stabilize_countdown}s)", bg=self.THEME["amber_dark"], fg="#FFFFFF")
        self.recording_engine.start_stabilization(session, port=self.port_var.get())
        self._countdown_stabilization()

    def _countdown_stabilization(self) -> None:
        if self.recording_engine.is_stabilizing:
            self.stabilize_countdown -= 1
            if self.stabilize_countdown > 0:
                self.status_pill.config(text=f"⏳ STABILIZING ({self.stabilize_countdown}s)")
                self.root.after(1000, self._countdown_stabilization)
            else:
                self._start_recording()

    def _toggle_recording(self) -> None:
        if not self.recording_engine.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self) -> None:
        is_ready, ready_err = self._validate_experiment_readiness()
        if not is_ready:
            messagebox.showwarning("Pre-Recording Validation", ready_err)
            return

        env_dict = self.canvas_editor.layout.to_dict()
        ok, msg, session = self.session_manager.create_session(
            name=self.session_name_var.get(),
            mac=self.canvas_editor.layout.target.mac if self.canvas_editor.layout.target else self.target_mac_var.get(),
            distance_m=self.distance_var.get(),
            anchor_id=self.anchor_var.get(),
            condition=self.condition_var.get(),
            tag_height_m=self.tag_height_var.get(),
            notes=self.notes_var.get(),
            target_samples=self.target_samples_var.get(),
            obstacle=self.obstacle_var.get(),
            obstacle_type=self.obstacle_type_var.get(),
            motion=self.motion_var.get(),
            data_source=self.port_var.get(),
            environment_layout=env_dict,
        )
        if not ok or not session:
            messagebox.showerror("Configuration Validation Failed", msg)
            return

        self._freeze_form_parameters(True)
        self.btn_record.config(state="disabled", bg=self.THEME["card"])
        self.btn_pause.config(state="normal", text="⏸  PAUSE")
        self.btn_stop.config(state="normal", bg=self.THEME["red"], fg="#FFFFFF")
        self.status_pill.config(text="●  RECORDING SESSION", bg=self.THEME["red_dark"], fg="#FFFFFF")

        self.feed_tree.delete(*self.feed_tree.get_children())
        self.rssi_history.clear()

        self.recording_engine.start_recording(session, port=self.port_var.get())

    def _toggle_pause(self) -> None:
        if self.recording_engine.is_recording:
            if not self.recording_engine.is_paused:
                self.recording_engine.pause_recording()
                self.btn_pause.config(text="▶ RESUME", bg=self.THEME["accent"])
                self.status_pill.config(text="⏸ PAUSED", bg=self.THEME["amber_dark"], fg="#FFFFFF")
            else:
                self.recording_engine.resume_recording()
                self.btn_pause.config(text="⏸ PAUSE", bg=self.THEME["card"])
                self.status_pill.config(text="● RECORDING SESSION", bg=self.THEME["red_dark"], fg="#FFFFFF")

    def _stop_recording(self) -> None:
        summary = self.recording_engine.stop_recording()
        self._freeze_form_parameters(False)

        self.btn_record.config(state="normal", text="▶  START RECORDING", bg=self.THEME["green"], fg="#FFFFFF")
        self.btn_pause.config(state="disabled", text="⏸  PAUSE", bg=self.THEME["card"])
        self.btn_stop.config(state="disabled", bg=self.THEME["card"], fg=self.THEME["red"])
        self.status_pill.config(text="○  IDLE", bg=self.THEME["card"], fg=self.THEME["subtext"])
        if hasattr(self, "lbl_master_timer"):
            self.lbl_master_timer.config(text="Elapsed: 00:00")

        session = self.session_manager.active_session
        if session and session.target_file_path.exists():
            self._show_session_summary_modal(session, summary)

    def _show_session_summary_modal(self, session: SessionConfig, summary: Dict[str, Any]) -> None:
        msg = (
            f"✅ COLLECTION SESSION COMPLETE & SAVED\n\n"
            f"Dataset File: {session.filename}\n"
            f"Ground-Truth Distance: {session.distance_m}m\n"
            f"Condition: {session.condition} ({session.obstacle_type})\n"
            f"Duration: {summary.get('duration_sec', 0)}s\n"
            f"Valid Samples Recorded: {summary.get('total_samples', 0):,} / {session.target_samples}\n"
            f"Average Arrival Rate: {summary.get('average_rate_hz', 0)} Hz\n"
            f"Running Mean RSSI: {summary.get('mean_rssi', 0)} dBm (σ={summary.get('std_rssi', 0)} dBm)\n\n"
            f"Anchor Observation Distribution:\n"
        )
        for anc_id, cnt in summary.get("anchor_counts", {}).items():
            msg += f"  • {anc_id}: {cnt:,} samples\n"

        msg += f"\nQuality Status: {summary.get('quality_status', 'NOMINAL')}\n{summary.get('quality_message', '')}"
        messagebox.showinfo("Session Summary & Finalization", msg)

    # =========================================================================
    # REAL-TIME QUEUE DISPATCHER & UI POLLING
    # =========================================================================
    def _process_packet_queue(self) -> None:
        target_max = self.target_samples_var.get()
        while not self.packet_queue.empty():
            pkt = self.packet_queue.get_nowait()
            rssi = int(pkt.get("rssi", -80))
            anc_id = pkt.get("anchor_id", "ANCHOR_01")
            mac = pkt.get("device_mac", "Unknown")
            dist = pkt.get("distance_m", self.distance_var.get())
            obs_type = pkt.get("obstacle_type", "None")
            verdict: QualityVerdict | None = pkt.get("quality_verdict")

            # Update master wireless sync indicator
            sync_st = pkt.get("sync_status")
            if sync_st and hasattr(self, "lbl_master_sync"):
                on_cnt = sync_st.get("online_count", 0)
                tot = sync_st.get("total_count", 4)
                if sync_st.get("in_sync"):
                    self.lbl_master_sync.config(text=f"● {on_cnt}/{tot} Nodes In Sync", bg=self.THEME["green_dark"], fg=self.THEME["green"])
                else:
                    self.lbl_master_sync.config(text=f"● {on_cnt}/{tot} Nodes Online", bg=self.THEME["amber_dark"], fg=self.THEME["amber"])

            now = time.time()
            self.rssi_history.append((now, anc_id, rssi))
            if len(self.rssi_history) > 100:
                self.rssi_history.pop(0)

            # Update specific anchor telemetry card
            if anc_id in self.anchor_telemetry_ui:
                card = self.anchor_telemetry_ui[anc_id]
                card["rssi"].config(text=f"{rssi} dBm")
                mean_r = verdict.mean_rssi if verdict else rssi
                std_r = verdict.std_rssi if verdict else 0.0
                card["stats"].config(text=f"μ: {mean_r:.1f} | σ: {std_r:.1f} | {pkt.get('anchor_counts', {}).get(anc_id, 0)} pkts")
                card["status"].config(text="● ONLINE", fg=self.THEME["green"])

            # Check for anchor timeouts
            offline_anchors = self.recording_engine.validator.check_anchor_timeouts(now)
            for off_anc in offline_anchors:
                if off_anc in self.anchor_telemetry_ui:
                    self.anchor_telemetry_ui[off_anc]["status"].config(text="■ OFFLINE", fg=self.THEME["red"])

            # Update quality banner
            if verdict:
                if verdict.status == "WARNING":
                    self.quality_banner.config(text=f"⚠ {verdict.message}", bg=self.THEME["amber_dark"], fg="#FFFFFF")
                elif verdict.status == "CRITICAL":
                    self.quality_banner.config(text=f"🚨 {verdict.message}", bg=self.THEME["red_dark"], fg="#FFFFFF")
                else:
                    self.quality_banner.config(text=f"✔ {verdict.message}", bg=self.THEME["green_dark"], fg="#FFFFFF")

            # Update recording progress
            if self.recording_engine.is_recording:
                valid_cnt = pkt.get("valid_samples", 0)
                raw_cnt = pkt.get("raw_packets", 0)
                elapsed_sec = int((now - self.recording_engine.start_record_time) - self.recording_engine.total_paused_time)
                elapsed_str = f"{elapsed_sec // 60:02d}:{elapsed_sec % 60:02d}"
                rate = round(valid_cnt / max(1, elapsed_sec), 2)
                pct = min(100, int((valid_cnt / max(1, target_max)) * 100))

                if hasattr(self, "lbl_master_timer"):
                    self.lbl_master_timer.config(text=f"Elapsed: {elapsed_str}")
                if hasattr(self, "lbl_master_samples"):
                    self.lbl_master_samples.config(text=f"{valid_cnt:,} / {target_max:,} samples")

                self.progress_bar["value"] = pct
                self.prog_text_lbl.config(
                    text=f"Valid Samples: {valid_cnt:,} / {target_max:,} ({pct}%) | Raw: {raw_cnt:,} | Rate: {rate} Hz | Elapsed: {elapsed_str}",
                )

                # Feed table
                t_str = datetime.datetime.now().strftime("%H:%M:%S")
                flag_text = verdict.quality_flag if verdict else "VALID"
                self.feed_tree.insert("", 0, values=(t_str, anc_id, mac, f"{rssi} dBm", f"{dist:.2f}m" if isinstance(dist, (int, float)) else dist, obs_type, flag_text))
                if len(self.feed_tree.get_children()) > 25:
                    self.feed_tree.delete(self.feed_tree.get_children()[-1])

                if valid_cnt >= target_max:
                    self._stop_recording()
                    break

        if not getattr(self, "_is_closing", False):
            try:
                self.root.after(60, self._process_packet_queue)
            except Exception:
                pass

    def _open_raw_folder(self) -> None:
        if os.name == "nt":
            os.startfile(str(RAW_DATA_DIR))
        else:
            subprocess.Popen(["xdg-open", str(RAW_DATA_DIR)])

    def _check_crash_recovery(self) -> None:
        unfinished = self.session_manager.detect_unfinished_sessions()
        if unfinished:
            msg = (
                f"⚠ UNFINISHED COLLECTION SESSIONS DETECTED:\n\n"
                f"Found {len(unfinished)} dataset(s) without companion finalization metadata:\n"
            )
            for u in unfinished[:3]:
                msg += f"  • {u['filename']} ({u['samples']} samples, {u['modified']})\n"

            msg += "\nWould you like to auto-finalize and generate metadata for these files now?"
            if messagebox.askyesno("Crash / Interruption Recovery", msg):
                for u in unfinished:
                    try:
                        stem = Path(u["path"]).stem
                        info_path = Path(u["path"]).with_name(f"{stem}_info.json")
                        with open(info_path, "w", encoding="utf-8") as f:
                            json.dump({
                                "session_filename": u["filename"],
                                "session_name": stem,
                                "total_samples": u["samples"],
                                "recovered": True,
                                "schema_version": "2.0",
                            }, f, indent=2)
                    except Exception:
                        pass
                messagebox.showinfo("Recovery Complete", "Unfinished sessions have been recovered and finalized.")

    def _on_close(self) -> None:
        self._is_closing = True
        if self.recording_engine.is_recording:
            if not messagebox.askyesno("Active Recording", "Recording is currently in progress. Stop and save before exiting?"):
                self._is_closing = False
                return
            self.recording_engine.stop_recording()

        self.recording_engine.stop_all()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = DataCollectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
