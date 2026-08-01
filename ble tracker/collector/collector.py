import csv
import os
import sys
import time
import glob
import random
import threading
import queue
from datetime import datetime
import subprocess

import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports


# ============================================================
# Configuration & Constants
# ============================================================

BAUD_RATES = [115200, 9600, 57600, 230400, 460800, 921600]
DEFAULT_BAUD_RATE = 115200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")

# ESP32 Firmware Build Binary Paths
BOOTLOADER_BIN = os.path.join(BUILD_DIR, "bootloader", "bootloader.bin")
PARTITION_BIN = os.path.join(BUILD_DIR, "partition_table", "partition-table.bin")
APP_BIN = os.path.join(BUILD_DIR, "ble.bin")

os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# BLE Collector Application
# ============================================================

class BLECollector:

    def __init__(self, root):

        self.root = root
        self.root.title("BLE Tracker - Dataset Collector Studio")
        self.root.geometry("880x760")
        self.root.minsize(820, 680)

        # Serial & Threading
        self.serial_connection = None
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.current_port = None
        self.current_baud = DEFAULT_BAUD_RATE

        # Port Monitoring State
        self.known_ports_map = {}  # { 'COM6': 'COM6 - USB-SERIAL CH340' }
        self.last_esp_port = None
        self.auto_scan_enabled = True

        # Firmware Flashing State
        self.flashing = False
        self.auto_flash_var = tk.BooleanVar(value=False)

        # Collection State
        self.collecting = False
        self.paused = False
        self.start_time = None
        self.samples_count = 0

        # File Handling
        self.csv_file = None
        self.csv_writer = None
        self.dataset_path = None

        # Thread Queue
        self.data_queue = queue.Queue()

        # Apply Modern Styling
        self.setup_styles()

        # Build User Interface
        self.build_gui()

        # Print Initialization & Hardware Discovery Report
        self.run_initial_port_diagnostic()

        # Queue Processor Loop (50ms)
        self.root.after(50, self.process_queue)

        # Auto Port Scanning Loop (1.5s)
        self.root.after(1500, self.auto_scan_ports_loop)


    # ========================================================
    # Theme & Styles
    # ========================================================

    def setup_styles(self):

        self.root.configure(bg="#181825")

        self.style = ttk.Style()
        
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Color Palette Definitions
        bg_dark = "#181825"
        card_bg = "#1e1e2e"
        card_border = "#313244"
        fg_text = "#cdd6f4"
        fg_muted = "#a6adc8"
        accent_blue = "#89b4fa"
        accent_green = "#a6e3a1"
        accent_yellow = "#f9e2af"
        accent_red = "#f38ba8"

        # Global TTK Styles
        self.style.configure(".", background=bg_dark, foreground=fg_text, font=("Segoe UI", 10))

        # Frames & Header
        self.style.configure("TFrame", background=bg_dark)
        self.style.configure("Card.TFrame", background=card_bg, relief="flat")
        
        self.style.configure(
            "Card.TLabelframe",
            background=card_bg,
            bordercolor=card_border,
            darkcolor=card_border,
            lightcolor=card_border,
            relief="solid",
            borderwidth=1,
            padding=12
        )
        self.style.configure(
            "Card.TLabelframe.Label",
            background=card_bg,
            foreground=accent_blue,
            font=("Segoe UI", 11, "bold")
        )

        # Labels
        self.style.configure("TLabel", background=card_bg, foreground=fg_text)
        self.style.configure("Subtext.TLabel", background=card_bg, foreground=fg_muted, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background=bg_dark, foreground="#cba6f7", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", background=card_bg, font=("Segoe UI", 11, "bold"))

        # Badges & Stats
        self.style.configure("StatVal.TLabel", background=card_bg, foreground=accent_blue, font=("Segoe UI", 14, "bold"))
        self.style.configure("StatLbl.TLabel", background=card_bg, foreground=fg_muted, font=("Segoe UI", 9))

        # Buttons
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background=accent_green,
            foreground="#11111b",
            padding=(14, 8)
        )
        self.style.map(
            "Primary.TButton",
            background=[("disabled", "#45475a"), ("active", "#94e2d5")],
            foreground=[("disabled", "#7f849c")]
        )

        self.style.configure(
            "Warning.TButton",
            font=("Segoe UI", 10, "bold"),
            background=accent_yellow,
            foreground="#11111b",
            padding=(14, 8)
        )
        self.style.map(
            "Warning.TButton",
            background=[("disabled", "#45475a"), ("active", "#f9e2af")],
            foreground=[("disabled", "#7f849c")]
        )

        self.style.configure(
            "Danger.TButton",
            font=("Segoe UI", 10, "bold"),
            background=accent_red,
            foreground="#11111b",
            padding=(14, 8)
        )
        self.style.map(
            "Danger.TButton",
            background=[("disabled", "#45475a"), ("active", "#f38ba8")],
            foreground=[("disabled", "#7f849c")]
        )

        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#313244",
            foreground=fg_text,
            padding=(8, 4)
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#45475a")]
        )

        # Quick Pill Preset Button Style
        self.style.configure(
            "Pill.TButton",
            font=("Segoe UI", 9),
            background="#313244",
            foreground="#cdd6f4",
            padding=(6, 3)
        )
        self.style.map(
            "Pill.TButton",
            background=[("active", accent_blue)],
            foreground=[("active", "#11111b")]
        )

        # Combobox & Entry
        self.style.configure(
            "TCombobox",
            fieldbackground="#313244",
            background="#313244",
            foreground=fg_text,
            arrowcolor=fg_text
        )
        self.style.configure(
            "TEntry",
            fieldbackground="#313244",
            foreground=fg_text,
            insertcolor=fg_text
        )


    # ========================================================
    # GUI Construction
    # ========================================================

    def build_gui(self):

        # Main Layout Container
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill="both", expand=True)

        # --- Top Header ---
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 10))

        title = ttk.Label(
            header_frame,
            text="📡 BLE TRACKER — DATASET COLLECTOR STUDIO",
            style="Header.TLabel"
        )
        title.pack(side="left")

        subtitle = ttk.Label(
            header_frame,
            text="ESP32 RSSI & Metadata Acquisition System",
            style="Subtext.TLabel",
            background="#181825"
        )
        subtitle.pack(side="right", anchor="e", pady=5)


        # --- Section 1: ESP32 Connection Card ---
        conn_box = ttk.LabelFrame(main_container, text="1. ESP32 Connection Setup", style="Card.TLabelframe")
        conn_box.pack(fill="x", pady=(0, 10))

        # Port Selection Row
        ttk.Label(conn_box, text="Serial COM Port:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.port_combo = ttk.Combobox(conn_box, width=32, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        refresh_btn = ttk.Button(conn_box, text="🔄 Scan Ports Now", style="Secondary.TButton", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Auto Scan Status Indicator
        self.autoscan_lbl = ttk.Label(conn_box, text="⚡ Auto-Scan: ACTIVE (1.5s)", style="Subtext.TLabel", foreground="#a6e3a1")
        self.autoscan_lbl.grid(row=0, column=3, padx=(10, 5), pady=5)

        # Baud Rate Row
        ttk.Label(conn_box, text="Baud Rate:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.baud_combo = ttk.Combobox(conn_box, values=BAUD_RATES, width=12, state="readonly")
        self.baud_combo.set(DEFAULT_BAUD_RATE)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.device_info_lbl = ttk.Label(conn_box, text="Device: Scanning...", style="Subtext.TLabel", foreground="#89b4fa")
        self.device_info_lbl.grid(row=1, column=2, columnspan=2, sticky="w", padx=5, pady=5)

        # Firmware Auto-Loader & Flashing Row
        ttk.Label(conn_box, text="ESP32 Code Loader:").grid(row=2, column=0, sticky="w", padx=5, pady=5)

        flash_frame = ttk.Frame(conn_box)
        flash_frame.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        self.flash_btn = ttk.Button(
            flash_frame,
            text="⚡ Load / Flash ESP32 Code",
            style="Primary.TButton",
            command=self.start_flash_firmware
        )
        self.flash_btn.pack(side="left", padx=(0, 10))

        self.autoflash_chk = ttk.Checkbutton(
            flash_frame,
            text="Auto-Flash on Connect",
            variable=self.auto_flash_var,
            command=self.on_autoflash_toggle
        )
        self.autoflash_chk.pack(side="left", padx=(0, 15))

        self.firmware_status_lbl = ttk.Label(flash_frame, text="Firmware: Checking...", style="Subtext.TLabel")
        self.firmware_status_lbl.pack(side="left")

        self.check_firmware_binaries()


        # --- Section 2: Experiment Metadata Card ---
        exp_box = ttk.LabelFrame(main_container, text="2. Ground Truth Experiment Metadata", style="Card.TLabelframe")
        exp_box.pack(fill="x", pady=(0, 10))

        # Distance Input & Presets
        ttk.Label(exp_box, text="Physical Distance (meters):").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        dist_input_frame = ttk.Frame(exp_box)
        dist_input_frame.grid(row=0, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        self.distance_entry = ttk.Entry(dist_input_frame, width=10)
        self.distance_entry.pack(side="left", padx=(0, 10))
        self.distance_entry.insert(0, "1.0")

        ttk.Label(dist_input_frame, text="Presets:", style="Subtext.TLabel").pack(side="left", padx=(0, 3))

        for d_val in ["0.1", "0.5", "1.0", "2.0", "3.2", "5.0"]:
            btn = ttk.Button(
                dist_input_frame,
                text=f"{d_val}m",
                style="Pill.TButton",
                command=lambda val=d_val: self.set_preset_distance(val)
            )
            btn.pack(side="left", padx=2)

        rand_btn = ttk.Button(
            dist_input_frame,
            text="🎲 Random Dist",
            style="Secondary.TButton",
            command=self.set_random_distance
        )
        rand_btn.pack(side="left", padx=(8, 0))

        # Height Level / Elevation Row
        ttk.Label(exp_box, text="Height / Elevation (meters):").grid(row=1, column=0, sticky="w", padx=5, pady=5)

        height_frame = ttk.Frame(exp_box)
        height_frame.grid(row=1, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        self.height_entry = ttk.Entry(height_frame, width=10)
        self.height_entry.pack(side="left", padx=(0, 10))
        self.height_entry.insert(0, "1.0")

        ttk.Label(height_frame, text="Presets:", style="Subtext.TLabel").pack(side="left", padx=(0, 3))

        height_presets = [
            ("Floor (0.0m)", "0.0"),
            ("Waist (1.0m)", "1.0"),
            ("Desk (1.4m)", "1.4"),
            ("Head (1.7m)", "1.7"),
        ]
        for label, h_val in height_presets:
            btn = ttk.Button(
                height_frame,
                text=label,
                style="Pill.TButton",
                command=lambda val=h_val: self.set_preset_height(val)
            )
            btn.pack(side="left", padx=2)

        # Dirty Data Presets Row
        ttk.Label(exp_box, text="Environment / Dirty Data Mode:").grid(row=2, column=0, sticky="w", padx=5, pady=5)

        self.dirty_mode_combo = ttk.Combobox(
            exp_box,
            values=[
                "Clean / Direct Line-of-Sight (LOS)",
                "WiFi Interference (2.4GHz Heavy)",
                "Concrete Wall",
                "WiFi + Concrete Wall",
                "Human Body Absorption",
                "Dynamic Movement / Multipath",
                "Phone Orientation Switch",
                "Custom / Manual"
            ],
            state="readonly",
            width=32
        )
        self.dirty_mode_combo.set("Clean / Direct Line-of-Sight (LOS)")
        self.dirty_mode_combo.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        self.dirty_mode_combo.bind("<<ComboboxSelected>>", self.on_dirty_preset_change)

        # Obstacle Controls Row
        ttk.Label(exp_box, text="Is there an obstacle?").grid(row=3, column=0, sticky="w", padx=5, pady=5)

        self.obstacle_combo = ttk.Combobox(exp_box, values=["No", "Yes"], state="readonly", width=10)
        self.obstacle_combo.set("No")
        self.obstacle_combo.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self.obstacle_combo.bind("<<ComboboxSelected>>", self.on_obstacle_change)

        ttk.Label(exp_box, text="Obstacle Type / Material:").grid(row=3, column=2, sticky="w", padx=(20, 5), pady=5)

        obs_type_frame = ttk.Frame(exp_box)
        obs_type_frame.grid(row=3, column=3, sticky="w", padx=5, pady=5)

        self.obstacle_type_combo = ttk.Combobox(
            obs_type_frame,
            values=[
                "None", "WiFi Interference", "Concrete Wall", "WiFi + Concrete Wall",
                "Human Body", "Wooden Door", "Glass Window", "Metal Shield",
                "Multipath Movement", "Orientation Change", "Custom..."
            ],
            width=22
        )
        self.obstacle_type_combo.set("None")
        self.obstacle_type_combo.pack(side="left")
        self.obstacle_type_combo.config(state="disabled")

        ttk.Label(
            exp_box,
            text="💡 Tip: Collecting arbitrary distances, heights, and 'Dirty Data' (WiFi interference, walls) ensures maximum ML robustness.",
            style="Subtext.TLabel"
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=5, pady=(5, 0))


        # --- Section 3: Live Dashboard & Controls ---
        ctrl_box = ttk.LabelFrame(main_container, text="3. Collection Controls & Live Metrics", style="Card.TLabelframe")
        ctrl_box.pack(fill="x", pady=(0, 10))

        # Sub-frame split: Left Buttons, Right Badges
        ctrl_layout = ttk.Frame(ctrl_box)
        ctrl_layout.pack(fill="x")

        # Action Buttons Column
        btn_frame = ttk.Frame(ctrl_layout)
        btn_frame.pack(side="left", anchor="w")

        self.start_button = ttk.Button(btn_frame, text="▶ START RECORDING", style="Primary.TButton", command=self.start_collection)
        self.start_button.pack(side="left", padx=(0, 8))

        self.pause_button = ttk.Button(btn_frame, text="⏸ PAUSE", style="Warning.TButton", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(btn_frame, text="⏹ STOP & SAVE", style="Danger.TButton", command=self.stop_collection, state="disabled")
        self.stop_button.pack(side="left", padx=(0, 8))

        # Live Metrics Badges Right
        metrics_frame = ttk.Frame(ctrl_layout)
        metrics_frame.pack(side="right", anchor="e")

        # Samples Card
        s_box = ttk.Frame(metrics_frame, padding=(10, 2))
        s_box.pack(side="left", padx=10)
        self.samples_lbl = ttk.Label(s_box, text="0", style="StatVal.TLabel")
        self.samples_lbl.pack()
        ttk.Label(s_box, text="SAMPLES", style="StatLbl.TLabel").pack()

        # Rate Card
        r_box = ttk.Frame(metrics_frame, padding=(10, 2))
        r_box.pack(side="left", padx=10)
        self.rate_lbl = ttk.Label(r_box, text="0.0 Hz", style="StatVal.TLabel")
        self.rate_lbl.pack()
        ttk.Label(r_box, text="SAMPLE RATE", style="StatLbl.TLabel").pack()

        # Status Badge Line
        status_bar = ttk.Frame(ctrl_box)
        status_bar.pack(fill="x", pady=(10, 0))

        self.status_dot = ttk.Label(status_bar, text="● SCANNING PORTS...", foreground="#f9e2af", style="Status.TLabel")
        self.status_dot.pack(side="left")

        self.file_info_lbl = ttk.Label(status_bar, text="Target Dir: collector/data/raw/", style="Subtext.TLabel")
        self.file_info_lbl.pack(side="left", padx=(20, 0))

        open_folder_btn = ttk.Button(status_bar, text="📁 Open Dataset Folder", style="Secondary.TButton", command=self.open_data_folder)
        open_folder_btn.pack(side="right")


        # --- Section 4: Live BLE Terminal ---
        console_box = ttk.LabelFrame(main_container, text="4. Real-Time BLE Stream Console", style="Card.TLabelframe")
        console_box.pack(fill="both", expand=True)

        # Toolbar above console
        c_toolbar = ttk.Frame(console_box)
        c_toolbar.pack(fill="x", pady=(0, 5))

        ttk.Label(c_toolbar, text="Stream Log:", style="Subtext.TLabel").pack(side="left")

        diag_btn = ttk.Button(c_toolbar, text="🔍 Re-run Port Diagnostic", style="Secondary.TButton", command=self.run_initial_port_diagnostic)
        diag_btn.pack(side="right", padx=(5, 0))

        clear_btn = ttk.Button(c_toolbar, text="🗑 Clear Console", style="Secondary.TButton", command=self.clear_console)
        clear_btn.pack(side="right")

        # Scrollable Console Text Area
        console_inner = ttk.Frame(console_box)
        console_inner.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(console_inner)
        scrollbar.pack(side="right", fill="y")

        self.console = tk.Text(
            console_inner,
            height=10,
            bg="#11111b",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            selectbackground="#45475a",
            font=("Consolas", 9),
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set
        )
        self.console.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.console.yview)

        # Configure Text Tags for Log Highlighting
        self.console.tag_config("INFO", foreground="#89b4fa")
        self.console.tag_config("DATA", foreground="#a6e3a1")
        self.console.tag_config("WARN", foreground="#f9e2af")
        self.console.tag_config("ERROR", foreground="#f38ba8")
        self.console.tag_config("SYS", foreground="#cba6f7")

        # --- Section 5: Dataset Health Audit & Deficit Monitor ---
        audit_box = ttk.LabelFrame(main_container, text="5. Dataset Coverage Audit & Missing Sample Deficit Monitor", style="Card.TLabelframe")
        audit_box.pack(fill="x", pady=(10, 0))

        audit_top = ttk.Frame(audit_box)
        audit_top.pack(fill="x", pady=(0, 5))

        self.audit_summary_lbl = ttk.Label(
            audit_top,
            text="Scanning raw dataset files for sample coverage...",
            style="Subtext.TLabel",
            foreground="#f9e2af"
        )
        self.audit_summary_lbl.pack(side="left")

        ttk.Button(
            audit_top,
            text="🔄 Refresh Deficit Audit",
            style="Secondary.TButton",
            command=self.refresh_dataset_audit
        ).pack(side="right")

        self.audit_tree = ttk.Treeview(
            audit_box,
            columns=("dist", "current_win", "target_win", "missing_win", "est_min", "status"),
            show="headings",
            height=5
        )
        self.audit_tree.heading("dist", text="Distance (m)")
        self.audit_tree.heading("current_win", text="Current Windows")
        self.audit_tree.heading("target_win", text="Target Windows")
        self.audit_tree.heading("missing_win", text="Missing Windows")
        self.audit_tree.heading("est_min", text="Est. Mins Needed")
        self.audit_tree.heading("status", text="Coverage Status")

        self.audit_tree.column("dist", width=90, anchor="center")
        self.audit_tree.column("current_win", width=120, anchor="center")
        self.audit_tree.column("target_win", width=110, anchor="center")
        self.audit_tree.column("missing_win", width=120, anchor="center")
        self.audit_tree.column("est_min", width=120, anchor="center")
        self.audit_tree.column("status", width=140, anchor="center")

        self.audit_tree.pack(fill="x", expand=True)


    # ========================================================
    # Startup Port Discovery & Diagnostic Report
    # ========================================================

    def run_initial_port_diagnostic(self):

        self.log("SYS", "=" * 70)
        self.log("SYS", " HARDWARE DISCOVERY & SERIAL PORT DIAGNOSTIC REPORT")
        self.log("SYS", "=" * 70)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log("SYS", f" Timestamp : {now_str}")
        self.log("SYS", f" Output Dir: {DATA_DIR}")
        self.log("SYS", " Searching for connected USB / Serial devices...")

        ports = list(serial.tools.list_ports.comports())
        self.known_ports_map = {}
        esp_port_info = None

        if not ports:
            self.log("WARN", " [✖] No active serial COM ports detected on this system.")
            self.log("WARN", "     Please connect your ESP32 via USB data cable.")
            self.log("SYS", " Status: Auto-port scanner ACTIVE (scanning every 1.5s).")
            self.port_combo["values"] = []
            self.port_combo.set("No COM ports found")
            self.device_info_lbl.config(text="Device: None detected", foreground="#f38ba8")
            self.status_dot.config(text="● NO ESP32 DETECTED — Waiting for USB connection...", foreground="#f38ba8")
        else:
            port_list_display = []
            for p in ports:
                device_str = p.device
                desc = p.description
                hwid = p.hwid or "N/A"
                mfg = getattr(p, 'manufacturer', None) or "Unknown Manufacturer"
                
                full_display = f"{device_str} - {desc}"
                port_list_display.append(full_display)
                self.known_ports_map[device_str] = full_display

                # Check for ESP32 UART bridge chips
                desc_lower = desc.lower()
                is_esp = any(k in desc_lower for k in ["ch340", "cp210", "ftdi", "uart", "esp32", "usb-serial"])

                self.log("INFO", f" [✔] Port Detected: {device_str}")
                self.log("INFO", f"     • Description : {desc}")
                self.log("INFO", f"     • Manufacturer: {mfg}")
                self.log("INFO", f"     • Hardware ID : {hwid}")
                
                if is_esp:
                    self.log("SYS", f"     • Detection   : ★ Recognized ESP32 USB-UART Serial Bridge!")
                    if not esp_port_info:
                        esp_port_info = (device_str, full_display, desc)

            self.port_combo["values"] = port_list_display

            if esp_port_info:
                dev_code, dev_disp, dev_desc = esp_port_info
                self.port_combo.set(dev_disp)
                self.last_esp_port = dev_code
                self.device_info_lbl.config(text=f"Detected: {dev_desc}", foreground="#a6e3a1")
                self.status_dot.config(text=f"● ESP32 READY on {dev_code}", foreground="#a6e3a1")
                self.log("SYS", f" Result: Auto-selected target port {dev_code}")
            else:
                self.port_combo.current(0)
                selected_dev = port_list_display[0].split(" - ")[0]
                self.device_info_lbl.config(text=f"Selected: {port_list_display[0]}", foreground="#89b4fa")
                self.status_dot.config(text=f"● READY on {selected_dev}", foreground="#a6e3a1")
                self.log("INFO", f" Result: Selected default port {selected_dev}")

        self.log("SYS", "=" * 70)


    # ========================================================
    # Auto Port Scanner Loop (Hot-plug & Disconnect Monitoring)
    # ========================================================

    def auto_scan_ports_loop(self):
        if self.auto_scan_enabled:
            try:
                current_ports = list(serial.tools.list_ports.comports())
                current_map = {p.device: f"{p.device} - {p.description}" for p in current_ports}

                # 1. Detect Newly Added Ports (Hot-Plug)
                added_ports = set(current_map.keys()) - set(self.known_ports_map.keys())
                if added_ports:
                    for new_p in added_ports:
                        desc = current_map[new_p]
                        self.log("SYS", f"⚡ HOT-PLUG EVENT: New device connected on {new_p} ({desc})")
                        
                        desc_lower = desc.lower()
                        if any(k in desc_lower for k in ["ch340", "cp210", "ftdi", "uart", "esp32", "usb-serial"]):
                            self.log("SYS", f"★ Auto-detected ESP32 on {new_p}! Updating port selection.")
                            self.last_esp_port = new_p
                            if not self.collecting and not self.flashing:
                                self.port_combo.set(desc)
                                self.device_info_lbl.config(text=f"Detected: {desc.split(' - ')[1]}", foreground="#a6e3a1")
                                self.status_dot.config(text=f"● ESP32 READY on {new_p}", foreground="#a6e3a1")

                                if self.auto_flash_var.get():
                                    self.log("SYS", f"⚡ Auto-Flash trigger for newly connected ESP32 on {new_p}...")
                                    self.root.after(500, lambda p=new_p: self.start_flash_firmware(p))

                # 2. Detect Removed Ports (Disconnect)
                removed_ports = set(self.known_ports_map.keys()) - set(current_map.keys())
                if removed_ports:
                    for rem_p in removed_ports:
                        self.log("WARN", f"⚠️ DISCONNECT EVENT: Serial device removed from {rem_p}")
                        
                        # Active port removed while collecting?
                        if self.collecting and self.current_port == rem_p:
                            self.log("ERROR", f"CRITICAL: Active ESP32 serial port {rem_p} was physically disconnected!")
                            self.data_queue.put(("PORT_DISCONNECTED", rem_p))

                # Update state map & combo values if ports changed
                if added_ports or removed_ports:
                    self.known_ports_map = current_map
                    port_values = list(current_map.values())
                    self.port_combo["values"] = port_values

                    if not port_values and not self.collecting:
                        self.port_combo.set("No COM ports found")
                        self.device_info_lbl.config(text="Device: None detected", foreground="#f38ba8")
                        self.status_dot.config(text="● NO ESP32 DETECTED — Connect via USB", foreground="#f38ba8")

            except Exception as e:
                pass

        # Reschedule scanner loop (1.5s)
        self.root.after(1500, self.auto_scan_ports_loop)


    # ========================================================
    # Manual Port Scan Trigger
    # ========================================================

    def refresh_ports(self):
        self.log("INFO", "Manual port scan requested...")
        self.run_initial_port_diagnostic()
        self.check_firmware_binaries()


    # ========================================================
    # Firmware Binary Verification & Flashing Engine
    # ========================================================

    def get_firmware_status(self):
        missing = []
        if not os.path.exists(BOOTLOADER_BIN):
            missing.append("bootloader.bin")
        if not os.path.exists(PARTITION_BIN):
            missing.append("partition-table.bin")
        if not os.path.exists(APP_BIN):
            missing.append("ble.bin")
        return len(missing) == 0, missing

    def check_firmware_binaries(self):
        ready, missing = self.get_firmware_status()
        if ready:
            self.firmware_status_lbl.config(text="Firmware: READY (ble.bin)", foreground="#a6e3a1")
        else:
            self.firmware_status_lbl.config(text=f"Firmware: Missing ({', '.join(missing)})", foreground="#f38ba8")

    def on_autoflash_toggle(self):
        if self.auto_flash_var.get():
            self.log("SYS", "⚡ Auto-Flash on Connect feature ENABLED")
        else:
            self.log("SYS", "Auto-Flash on Connect feature DISABLED")

    def start_flash_firmware(self, target_port=None):
        if self.flashing:
            messagebox.showinfo("Flashing in Progress", "Firmware flashing is already running.")
            return

        if self.collecting:
            if not messagebox.askyesno("Stop Collection", "Active data collection must be stopped to flash firmware. Proceed?"):
                return
            self.stop_collection()

        selected_port_str = target_port or self.port_combo.get()
        if not selected_port_str or "No COM ports" in selected_port_str:
            messagebox.showerror("Connection Error", "Please connect and select a valid ESP32 COM port first.")
            return

        port = selected_port_str.split(" - ")[0]

        ready, missing = self.get_firmware_status()
        if not ready:
            err_msg = f"Cannot load firmware! Required build binaries missing in:\n{BUILD_DIR}\n\nMissing files: {', '.join(missing)}\n\nPlease build the ESP32 code using 'idf.py build' first."
            self.log("ERROR", err_msg)
            messagebox.showerror("Firmware Missing", err_msg)
            return

        # Safely release serial connection before flashing
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception:
                pass
            self.serial_connection = None

        self.flashing = True
        self.flash_btn.config(state="disabled", text="⚡ FLASHING ESP32...")
        self.lock_inputs(True)
        self.status_dot.config(text=f"⚡ FLASHING FIRMWARE to {port}...", foreground="#f9e2af")

        threading.Thread(target=self.flash_worker, args=(port,), daemon=True).start()

    def flash_worker(self, port):
        self.data_queue.put(("FLASH_LOG", "=" * 70))
        self.data_queue.put(("FLASH_LOG", "⚡ ESP32 FIRMWARE AUTO-LOADER & FLASHER"))
        self.data_queue.put(("FLASH_LOG", "=" * 70))
        self.data_queue.put(("FLASH_LOG", f" Target Port : {port}"))
        self.data_queue.put(("FLASH_LOG", f" Bootloader  : {BOOTLOADER_BIN} (0x1000)"))
        self.data_queue.put(("FLASH_LOG", f" Partition   : {PARTITION_BIN} (0x8000)"))
        self.data_queue.put(("FLASH_LOG", f" App Binary  : {APP_BIN} (0x10000)"))
        self.data_queue.put(("FLASH_LOG", " Invoking esptool flashing utility..."))

        # Use 115200 baud rate and flash-size detect for 100% hardware compatibility & noise immunity
        cmd = [
            sys.executable, "-m", "esptool",
            "--chip", "esp32",
            "--port", port,
            "--baud", "115200",
            "--before", "default-reset",
            "--after", "hard-reset",
            "write-flash",
            "--flash-mode", "dio",
            "--flash-freq", "40m",
            "--flash-size", "detect",
            "0x1000", BOOTLOADER_BIN,
            "0x8000", PARTITION_BIN,
            "0x10000", APP_BIN
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in iter(process.stdout.readline, ''):
                if line:
                    clean_line = line.rstrip()
                    self.data_queue.put(("FLASH_LOG", f" [esptool] {clean_line}"))

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.data_queue.put(("FLASH_LOG", "★ FIRMWARE FLASHED SUCCESSFULLY! ESP32 reset triggered."))
                self.data_queue.put(("FLASH_COMPLETE", True, port, "Firmware code was successfully loaded onto ESP32!"))
            else:
                self.data_queue.put(("FLASH_LOG", f"[✖] Flashing failed with exit code: {return_code}"))
                self.data_queue.put(("FLASH_LOG", "💡 Troubleshooting Tips:"))
                self.data_queue.put(("FLASH_LOG", "   1. Press & hold the BOOT (IO0) button on your ESP32 board for 2 seconds while flashing starts."))
                self.data_queue.put(("FLASH_LOG", "   2. Ensure your USB cable supports high-speed data transfer."))
                self.data_queue.put(("FLASH_LOG", "   3. Disconnect external sensors or peripherals attached to ESP32 GPIO pins."))
                self.data_queue.put(("FLASH_COMPLETE", False, port, f"Flashing failed (Exit code: {return_code}).\n\nTry holding the BOOT button on your ESP32 board while clicking Flash."))

        except Exception as e:
            self.data_queue.put(("FLASH_LOG", f"[✖] Flashing error: {str(e)}"))
            self.data_queue.put(("FLASH_COMPLETE", False, port, f"Flashing exception: {str(e)}"))


    # ========================================================
    # Helper Handlers & Presets
    # ========================================================

    def refresh_dataset_audit(self):
        """Asynchronously scans raw dataset CSV files on a background thread so the GUI never lags."""
        if hasattr(self, "audit_summary_lbl"):
            self.audit_summary_lbl.config(text="⚡ Auditing dataset coverage...", foreground="#89b4fa")

        def audit_worker():
            target_presets = [0.5, 1.0, 2.0, 3.0, 5.0]
            target_windows = 2500
            dist_records = {d: 0 for d in target_presets}

            raw_files = sorted(glob.glob(os.path.join(DATA_DIR, "dataset_*.csv")))

            for fpath in raw_files:
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        line_count = 0
                        first_data_row = None
                        for i, line in enumerate(f):
                            line_count += 1
                            if i == 1 and line.strip():
                                first_data_row = line.strip().split(",")

                        if line_count > 1 and first_data_row and len(first_data_row) >= 6:
                            try:
                                file_dist = float(first_data_row[5])
                                approx_windows = (line_count - 1) // 10
                                if file_dist in dist_records:
                                    dist_records[file_dist] += approx_windows
                            except ValueError:
                                pass
                except Exception:
                    pass

            self.data_queue.put(("AUDIT_RESULT", dist_records, target_windows))

        threading.Thread(target=audit_worker, daemon=True).start()

    def update_audit_ui(self, dist_records, target_windows):
        """Updates Section 5 Treeview and summary label on the main GUI thread."""
        if hasattr(self, "audit_tree"):
            for item in self.audit_tree.get_children():
                self.audit_tree.delete(item)

        target_presets = [0.5, 1.0, 2.0, 3.0, 5.0]
        total_missing = 0
        critical_missing = []

        for d in target_presets:
            current = dist_records.get(d, 0)
            missing = max(0, target_windows - current)
            total_missing += missing
            est_mins = round((missing * 1.0) / 60.0, 1)

            if current == 0:
                status = "🔴 CRITICAL MISSING"
                critical_missing.append(f"{d}m")
            elif current < 1000:
                status = "🟡 LOW SAMPLES"
                critical_missing.append(f"{d}m")
            else:
                status = "✅ GOOD"

            if hasattr(self, "audit_tree"):
                self.audit_tree.insert(
                    "", "end",
                    values=(f"{d} m", f"{current:,} win", f"{target_windows:,} win", f"{missing:,} win", f"~{est_mins} mins", status)
                )

        if hasattr(self, "audit_summary_lbl"):
            if critical_missing:
                msg = f"⚠️ Dataset Deficit: Priority sample collection needed for distance(s): {', '.join(critical_missing)}. Total missing: {total_missing:,} windows."
                self.audit_summary_lbl.config(text=msg, foreground="#f38ba8")
            else:
                msg = "✅ Excellent Coverage: Target dataset size reached across all distance presets!"
                self.audit_summary_lbl.config(text=msg, foreground="#a6e3a1")

    def set_preset_distance(self, value_str):
        if not self.collecting:
            self.distance_entry.delete(0, tk.END)
            self.distance_entry.insert(0, value_str)

    def set_random_distance(self):
        if not self.collecting:
            # Pick a random arbitrary distance between 0.1m and 5.0m (1 decimal place)
            d_rand = round(random.uniform(0.1, 5.0), 1)
            self.distance_entry.delete(0, tk.END)
            self.distance_entry.insert(0, str(d_rand))

    def set_preset_height(self, value_str):
        if not self.collecting:
            self.height_entry.delete(0, tk.END)
            self.height_entry.insert(0, value_str)

    def on_dirty_preset_change(self, event=None):
        mode = self.dirty_mode_combo.get()
        mapping = {
            "Clean / Direct Line-of-Sight (LOS)": ("No", "None"),
            "WiFi Interference (2.4GHz Heavy)": ("Yes", "WiFi Interference"),
            "Concrete Wall": ("Yes", "Concrete Wall"),
            "WiFi + Concrete Wall": ("Yes", "WiFi + Concrete Wall"),
            "Human Body Absorption": ("Yes", "Human Body"),
            "Dynamic Movement / Multipath": ("Yes", "Multipath Movement"),
            "Phone Orientation Switch": ("Yes", "Orientation Change"),
        }
        if mode in mapping:
            obs, obs_type = mapping[mode]
            self.obstacle_combo.set(obs)
            self.obstacle_type_combo.config(state="normal" if obs == "Yes" else "disabled")
            self.obstacle_type_combo.set(obs_type)
        elif mode == "Custom / Manual":
            self.obstacle_combo.set("Yes")
            self.obstacle_type_combo.config(state="normal")
            self.obstacle_type_combo.set("Custom...")

    def on_obstacle_change(self, event=None):
        if self.obstacle_combo.get() == "Yes":
            self.obstacle_type_combo.config(state="normal")
            if self.obstacle_type_combo.get() == "None":
                self.obstacle_type_combo.set("Human Body")
        else:
            self.obstacle_type_combo.set("None")
            self.obstacle_type_combo.config(state="disabled")

    def open_data_folder(self):
        try:
            if os.name == 'nt':
                os.startfile(DATA_DIR)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', DATA_DIR])
            else:
                subprocess.Popen(['xdg-open', DATA_DIR])
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not open directory:\n{e}")

    def clear_console(self):
        self.console.config(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.config(state="disabled")


    # ========================================================
    # Start Collection Flow
    # ========================================================

    def start_collection(self):

        # 1. Validate Distance & Height
        distance_text = self.distance_entry.get().strip()
        if not distance_text:
            messagebox.showerror("Missing Input", "Please specify a distance in meters.")
            return

        try:
            distance = float(distance_text)
            if distance < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Distance must be a positive numeric value (e.g. 1.5).")
            return

        height_text = self.height_entry.get().strip()
        try:
            height_m = float(height_text) if height_text else 1.0
            if height_m < 0:
                raise ValueError
        except ValueError:
            height_m = 1.0

        # 2. Validate Port
        selected_port_str = self.port_combo.get()
        if not selected_port_str or "No COM ports" in selected_port_str:
            messagebox.showerror("Connection Error", "Please connect a valid ESP32 COM port.")
            return

        port = selected_port_str.split(" - ")[0]
        self.current_port = port

        # 3. Validate Baud Rate
        try:
            baud_rate = int(self.baud_combo.get())
        except ValueError:
            baud_rate = DEFAULT_BAUD_RATE
        self.current_baud = baud_rate

        # 4. Metadata Settings
        obstacle = self.obstacle_combo.get()
        obstacle_type = self.obstacle_type_combo.get().strip()
        if obstacle == "No":
            obstacle_type = "None"
        elif not obstacle_type:
            obstacle_type = "Unspecified"

        # 5. Initialize CSV Dataset File
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"dataset_{timestamp_str}.csv"
        self.dataset_path = os.path.join(DATA_DIR, filename)

        try:
            self.csv_file = open(self.dataset_path, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)

            # Standard Dataset Header (including height_m)
            self.csv_writer.writerow([
                "timestamp",
                "anchor",
                "mac",
                "rssi",
                "name",
                "distance_m",
                "obstacle",
                "obstacle_type",
                "height_m"
            ])
            self.csv_file.flush()

            # Open Serial Connection
            self.serial_connection = serial.Serial(port, baud_rate, timeout=1)

            # State Updates
            self.collecting = True
            self.paused = False
            self.stop_event.clear()
            self.samples_count = 0
            self.start_time = time.time()

            # UI Lock / Controls Update
            self.lock_inputs(True)
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal", text="⏸ PAUSE")
            self.stop_button.config(state="normal")

            self.status_dot.config(text=f"● COLLECTING | {port}", foreground="#a6e3a1")
            self.file_info_lbl.config(text=f"File: {filename}")
            self.samples_lbl.config(text="0")
            self.rate_lbl.config(text="0.0 Hz")

            self.log("SYS", f"Started session logging to: {filename}")
            self.log("SYS", f"Params → Port: {port} @ {baud_rate} baud | Dist: {distance}m | Height: {height_m}m | Obstacle: {obstacle} ({obstacle_type})")

            # Start Reader Worker Thread
            self.reader_thread = threading.Thread(
                target=self.serial_reader,
                args=(distance, obstacle, obstacle_type, height_m),
                daemon=True
            )
            self.reader_thread.start()

        except Exception as e:
            messagebox.showerror("Serial Error", f"Failed to connect to {port}:\n{str(e)}")
            self.cleanup()


    # ========================================================
    # Worker Thread: Serial Reader
    # ========================================================

    def serial_reader(self, distance, obstacle, obstacle_type, height_m=1.0):
        while not self.stop_event.is_set():
            try:
                if not self.serial_connection or not self.serial_connection.is_open:
                    break

                raw_line = self.serial_connection.readline()
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # Skip header if ESP32 reboots
                if line.startswith("timestamp,"):
                    continue

                # Parse expected CSV format: timestamp,anchor,mac,rssi,name
                parts = line.split(",")
                if len(parts) < 5:
                    continue

                timestamp = parts[0].strip()
                anchor = parts[1].strip()
                mac = parts[2].strip()
                rssi = parts[3].strip()
                name = ",".join(parts[4:]).strip()

                # Validate timestamp is numeric, MAC format, and RSSI is integer
                if not timestamp.isdigit():
                    continue
                if ":" not in mac or len(mac) < 11:
                    continue
                try:
                    int(rssi)
                except ValueError:
                    continue

                # Optional target MAC filter (default tag: 52:06:26:03:01:DA)
                target_mac = getattr(self, "target_mac_filter", "52:06:26:03:01:DA")
                if target_mac and mac.upper() != target_mac.upper():
                    continue

                # Create populated dataset record (with height_m)
                row = [
                    timestamp,
                    anchor,
                    mac,
                    rssi,
                    name,
                    distance,
                    obstacle,
                    obstacle_type,
                    height_m
                ]

                self.data_queue.put(row)

            except serial.SerialException as se:
                self.data_queue.put(("PORT_DISCONNECTED", str(se)))
                break
            except Exception as e:
                self.data_queue.put(("ERROR", str(e)))
                break


    # ========================================================
    # Queue Consumer (GUI Thread Loop)
    # ========================================================

    def process_queue(self):
        try:
            while True:
                item = self.data_queue.get_nowait()

                # Event: Audit Result Ready
                if isinstance(item, tuple) and item[0] == "AUDIT_RESULT":
                    dist_records, target_windows = item[1], item[2]
                    self.update_audit_ui(dist_records, target_windows)
                    continue

                # Event: Flashing Process Log
                if isinstance(item, tuple) and item[0] == "FLASH_LOG":
                    self.log("SYS", item[1])
                    continue

                # Event: Flashing Complete
                if isinstance(item, tuple) and item[0] == "FLASH_COMPLETE":
                    success, port, msg = item[1], item[2], item[3]
                    self.flashing = False
                    self.flash_btn.config(state="normal", text="⚡ Load / Flash ESP32 Code")
                    self.lock_inputs(False)
                    if success:
                        self.status_dot.config(text=f"● ESP32 FLASHED & READY on {port}", foreground="#a6e3a1")
                        messagebox.showinfo("Firmware Loaded", f"Success!\n\n{msg}\n\nESP32 is now loaded with the RSSI collection firmware.")
                    else:
                        self.status_dot.config(text=f"🔴 FLASH FAILED on {port}", foreground="#f38ba8")
                        messagebox.showerror("Flash Error", f"Failed to load firmware:\n\n{msg}")
                    continue

                # Event: Serial Port Disconnected Event
                if isinstance(item, tuple) and item[0] == "PORT_DISCONNECTED":
                    self.log("ERROR", f"CRITICAL: Serial Port disconnect error ({item[1]})")
                    self.status_dot.config(text=f"🔴 DISCONNECTED ({self.current_port}) — Re-plug ESP32 USB", foreground="#f38ba8")
                    self.paused = True
                    self.pause_button.config(text="▶ RESUME (When Re-connected)")
                    messagebox.showwarning("Device Disconnected", f"ESP32 on {self.current_port} was unplugged or lost power!\n\nCollection is PAUSED. Re-plug USB and click RESUME or STOP.")
                    continue

                # Event: General Error
                if isinstance(item, tuple) and item[0] == "ERROR":
                    self.log("ERROR", f"Serial Exception: {item[1]}")
                    continue

                if self.paused:
                    continue

                row = item

                # Write to CSV
                if self.csv_writer and self.csv_file:
                    self.csv_writer.writerow(row)
                    self.csv_file.flush()

                # Stream to real-time positioning server if active (FastAPI on http://localhost:8000)
                try:
                    def stream_packet(r):
                        try:
                            import requests
                            packet_json = {
                                "timestamp": int(r[0]),
                                "anchor": r[1],
                                "mac": r[2],
                                "rssi": int(r[3]),
                                "name": r[4]
                            }
                            requests.post("http://localhost:8000/api/observation", json=packet_json, timeout=0.15)
                        except Exception:
                            pass
                    threading.Thread(target=stream_packet, args=(row,), daemon=True).start()
                except Exception:
                    pass

                self.samples_count += 1

                # Update Stats Labels
                self.samples_lbl.config(text=str(self.samples_count))
                
                elapsed = time.time() - self.start_time if self.start_time else 1.0
                rate = self.samples_count / max(elapsed, 0.1)
                self.rate_lbl.config(text=f"{rate:.1f} Hz")

                # Console Stream Log
                rssi_val = row[3]
                anchor_id = row[1]
                mac_addr = row[2]
                self.log("DATA", f"[{anchor_id}] {mac_addr} | RSSI: {rssi_val} dBm | Dist: {row[5]}m")

        except queue.Empty:
            pass

        self.root.after(50, self.process_queue)


    # ========================================================
    # Pause / Resume Toggle
    # ========================================================

    def toggle_pause(self):
        if not self.collecting:
            return

        self.paused = not self.paused

        if self.paused:
            self.pause_button.config(text="▶ RESUME")
            self.status_dot.config(text="● PAUSED", foreground="#f9e2af")
            self.log("WARN", "Data collection paused. Incoming samples will be discarded.")
        else:
            self.pause_button.config(text="⏸ PAUSE")
            self.status_dot.config(text=f"● COLLECTING | {self.current_port}", foreground="#a6e3a1")
            self.log("SYS", "Data collection resumed.")


    # ========================================================
    # Stop Collection
    # ========================================================

    def stop_collection(self):
        if not self.collecting:
            return

        self.stop_event.set()

        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception:
                pass
            self.serial_connection = None

        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None

        self.collecting = False
        self.paused = False

        # UI State Reset
        self.lock_inputs(False)
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled", text="⏸ PAUSE")
        self.stop_button.config(state="disabled")

        self.status_dot.config(text="● STOPPED & SAVED", foreground="#89b4fa")
        self.log("SYS", f"Session completed. Total saved samples: {self.samples_count}")
        self.log("SYS", f"Output File: {self.dataset_path}")

        messagebox.showinfo(
            "Collection Complete",
            f"Successfully recorded {self.samples_count} BLE samples!\n\nSaved to:\n{self.dataset_path}"
        )


    # ========================================================
    # State Lock & Cleanup
    # ========================================================

    def lock_inputs(self, lock=True):
        state = "disabled" if lock else "readonly"
        entry_state = "disabled" if lock else "normal"
        
        self.port_combo.config(state=state)
        self.baud_combo.config(state=state)
        self.distance_entry.config(state=entry_state)
        self.obstacle_combo.config(state=state)
        if self.obstacle_combo.get() == "Yes" and not lock:
            self.obstacle_type_combo.config(state="normal")
        else:
            self.obstacle_type_combo.config(state="disabled" if lock else ("normal" if self.obstacle_combo.get() == "Yes" else "disabled"))

    def cleanup(self):
        self.stop_event.set()
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception:
                pass
            self.serial_connection = None

        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None

        self.collecting = False
        self.root.destroy()


    # ========================================================
    # Console Logger
    # ========================================================

    def log(self, tag, message):
        self.console.config(state="normal")

        # Keep console size manageable (max 1000 lines)
        line_count = int(self.console.index('end-1c').split('.')[0])
        if line_count > 1000:
            self.console.delete("1.0", "200.0")

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"

        self.console.insert(tk.END, formatted, tag)
        self.console.see(tk.END)
        self.console.config(state="disabled")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = BLECollector(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()
