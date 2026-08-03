import csv
import glob
import json
import logging
import os
import queue
import random
import subprocess
import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import serial
import serial.tools.list_ports

# Logging Setup
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("BLECollector")


# ============================================================
# Configuration & Constants
# ============================================================

BAUD_RATES = [115200, 9600, 57600, 230400, 460800, 921600]
DEFAULT_BAUD_RATE = 115200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")

# ESP32 Firmware Build Binary Paths
BOOTLOADER_BIN = os.path.join(BUILD_DIR, "bootloader", "bootloader.bin")
PARTITION_BIN = os.path.join(BUILD_DIR, "partition_table", "partition-table.bin")
APP_BIN = os.path.join(BUILD_DIR, "ble.bin")

os.makedirs(DATA_DIR, exist_ok=True)


def get_system_font_families():
    """Detects available system fonts and returns robust primary and monospace font family candidates."""
    try:
        from tkinter import font
        available = set(font.families())
    except Exception:
        available = set()

    sans_candidates = ["Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial", "Liberation Sans", "Ubuntu", "DejaVu Sans", "sans-serif"]
    primary_font = next((f for f in sans_candidates if f in available), "Segoe UI" if sys.platform == "win32" else "Arial")

    mono_candidates = ["Consolas", "Cascadia Code", "SF Mono", "Courier New", "Liberation Mono", "DejaVu Sans Mono", "monospace"]
    mono_font = next((f for f in mono_candidates if f in available), "Consolas" if sys.platform == "win32" else "Courier New")

    return primary_font, mono_font


# ============================================================
# Manager 1: Configuration Manager (config.json)
# ============================================================

class ConfigManager:
    """Manages application settings stored in config.json."""

    DEFAULT_CONFIG = {
        "baud_rate": DEFAULT_BAUD_RATE,
        "auto_scan_interval_ms": 1500,
        "stream_endpoint_url": "http://localhost:8000/api/observation",
        "stream_enabled": True,
        "buffer_flush_size": 50,
        "window_size": 50,
        "stride": 10,
        "target_mac_filter": "52:06:26:03:01:DA",
        "target_windows_goal": 2500,
    }

    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = self.DEFAULT_CONFIG.copy()
                    merged.update(cfg)
                    return merged
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()


# ============================================================
# Manager 2: Persistent Worker Thread Network Streamer
# ============================================================

class NetworkStreamer:
    """Persistent single-thread HTTP streamer for non-blocking packet forwarding."""

    def __init__(self, endpoint_url, enabled=True):
        self.endpoint_url = endpoint_url
        self.enabled = enabled
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None

    def start(self):
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

    def stop(self):
        self.stop_event.set()

    def push(self, row):
        if self.enabled and not self.stop_event.is_set():
            self.queue.put(row)

    def _worker_loop(self):
        import requests
        session = requests.Session()
        while not self.stop_event.is_set():
            try:
                row = self.queue.get(timeout=0.5)
                packet_json = {
                    "timestamp": int(row[0]),
                    "anchor": row[1],
                    "mac": row[2],
                    "rssi": int(row[3]),
                    "name": row[4]
                }
                try:
                    session.post(self.endpoint_url, json=packet_json, timeout=0.15)
                except Exception as req_err:
                    pass
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"NetworkStreamer worker exception: {e}")


# ============================================================
# Manager 3: Dataset Writer & Metadata Manager (dataset_info.json)
# ============================================================

class DatasetWriter:
    """Handles buffered CSV dataset recording and sidecar dataset_info.json metadata generation."""

    def __init__(self, data_dir, buffer_flush_size=50):
        self.data_dir = data_dir
        self.buffer_flush_size = buffer_flush_size
        self.csv_file = None
        self.csv_writer = None
        self.dataset_path = None
        self.metadata_path = None
        self.unflushed_count = 0
        self.session_start_time = None
        self.metadata_info = {}

    def start_session(self, distance, obstacle, obstacle_type, height_m=1.0, motion="stationary", dirty_mode="", target_mac=""):
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"dataset_{timestamp_str}.csv"
        info_filename = f"dataset_{timestamp_str}_info.json"

        self.dataset_path = os.path.join(self.data_dir, filename)
        self.metadata_path = os.path.join(self.data_dir, info_filename)
        self.session_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.unflushed_count = 0

        self.metadata_info = {
            "session_filename": filename,
            "start_timestamp": self.session_start_time,
            "end_timestamp": None,
            "distance_m": distance,
            "height_m": height_m,
            "motion": motion,
            "obstacle": obstacle,
            "obstacle_type": obstacle_type,
            "dirty_environment_mode": dirty_mode,
            "target_mac": target_mac,
            "total_samples": 0
        }

        self.csv_file = open(self.dataset_path, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "timestamp", "anchor", "mac", "rssi", "name",
            "distance_m", "obstacle", "obstacle_type", "height_m", "motion"
        ])
        return filename

    def write_row(self, row):
        if self.csv_writer and self.csv_file:
            self.csv_writer.writerow(row)
            self.unflushed_count += 1
            self.metadata_info["total_samples"] += 1

            if self.unflushed_count >= self.buffer_flush_size:
                self.flush()

    def flush(self):
        if self.csv_file and not self.csv_file.closed:
            try:
                self.csv_file.flush()
                self.unflushed_count = 0
            except Exception as e:
                logger.error(f"Error flushing CSV file: {e}")

    def stop_session(self):
        self.flush()
        if self.csv_file and not self.csv_file.closed:
            try:
                self.csv_file.close()
            except Exception as e:
                logger.error(f"Error closing CSV file: {e}")
            self.csv_file = None

        self.metadata_info["end_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.metadata_path:
            try:
                with open(self.metadata_path, "w", encoding="utf-8") as f:
                    json.dump(self.metadata_info, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving dataset_info.json: {e}")

        return self.dataset_path, self.metadata_info["total_samples"]


class DatasetAuditor:
    """Performs true multi-dimensional sliding-window dataset coverage & quality analysis across raw CSV files."""

    def __init__(self, data_dir, target_presets=None, target_windows=2500, window_size=50, stride=10):
        self.data_dir = data_dir
        self.target_presets = target_presets or [0.5, 1.0, 2.0, 3.0, 5.0]
        self.height_presets = [0.0, 1.0, 1.4, 1.7]
        self.target_windows = target_windows
        self.window_size = window_size
        self.stride = stride

    def run_audit(self):
        dist_samples = {d: 0 for d in self.target_presets}
        height_samples = {h: 0 for h in self.height_presets}
        motion_samples = {"stationary": 0, "approaching": 0, "moving_away": 0}
        obs_samples = {"Clean (LOS)": 0, "Obstacle / Dirty Data": 0}
        anchor_samples = {}

        total_samples = 0
        file_durations = []

        raw_files = sorted(glob.glob(os.path.join(self.data_dir, "dataset_*.csv")))

        for fpath in raw_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header or len(header) < 4:
                        continue

                    file_ts = []
                    for row in reader:
                        if len(row) < 4:
                            continue

                        # Parse timestamp for empirical Hz calculation
                        try:
                            ts = int(row[0])
                            file_ts.append(ts)
                        except (ValueError, TypeError):
                            pass

                        # Anchor Node ID
                        anchor = row[1].strip() if len(row) > 1 else "Unknown"
                        anchor_samples[anchor] = anchor_samples.get(anchor, 0) + 1

                        # Distance (col index 5)
                        if len(row) > 5:
                            try:
                                raw_d = float(row[5].strip().lower().replace("m", "").replace(",", "."))
                                for target in self.target_presets:
                                    if abs(raw_d - target) < 0.1:
                                        dist_samples[target] += 1
                                        break
                            except (ValueError, TypeError):
                                pass

                        # Obstacle / Environment (col index 6)
                        if len(row) > 6:
                            obs_val = row[6].strip().lower()
                            has_obs_type = len(row) > 7 and row[7].strip().lower() not in ["none", ""]
                            if obs_val in ["yes", "1", "true"] or has_obs_type:
                                obs_samples["Obstacle / Dirty Data"] += 1
                            else:
                                obs_samples["Clean (LOS)"] += 1

                        # Height (col index 8)
                        if len(row) > 8:
                            try:
                                raw_h = float(row[8].strip().lower().replace("m", "").replace(",", "."))
                                for h_target in self.height_presets:
                                    if abs(raw_h - h_target) < 0.15:
                                        height_samples[h_target] += 1
                                        break
                            except (ValueError, TypeError):
                                pass

                        # Motion (col index 9)
                        if len(row) > 9:
                            m_val = row[9].strip().lower()
                            if m_val in motion_samples:
                                motion_samples[m_val] += 1

                        total_samples += 1

                    if len(file_ts) >= 2:
                        dur_sec = (max(file_ts) - min(file_ts)) / 1000.0
                        if dur_sec > 0:
                            file_durations.append((len(file_ts), dur_sec))

            except Exception as e:
                logger.warning(f"DatasetAuditor error scanning {fpath}: {e}")

        # Empirical Sample Rate (Hz)
        if file_durations:
            tot_p = sum(p for p, d in file_durations)
            tot_d = sum(d for p, d in file_durations)
            sample_rate_hz = tot_p / max(tot_d, 0.1) if tot_d > 0 else 20.0
        else:
            sample_rate_hz = 20.0

        def calc_windows(samples_cnt):
            return max(0, (samples_cnt - self.window_size) // self.stride + 1) if samples_cnt >= self.window_size else 0

        dist_windows = {d: calc_windows(dist_samples[d]) for d in self.target_presets}
        height_windows = {h: calc_windows(height_samples[h]) for h in self.height_presets}
        motion_windows = {m: calc_windows(motion_samples[m]) for m in motion_samples}
        obs_windows = {k: calc_windows(obs_samples[k]) for k in obs_samples}
        anchor_windows = {a: calc_windows(anchor_samples[a]) for a in anchor_samples}

        return {
            "distance": {"records": dist_windows, "target": self.target_windows},
            "height": {"records": height_windows, "target": 1000},
            "motion": {"records": motion_windows, "target": 1000},
            "obstacle": {"records": obs_windows, "target": 1500},
            "anchor": {"records": anchor_windows, "target": self.target_windows},
            "sample_rate_hz": round(sample_rate_hz, 1),
            "total_samples": total_samples,
            "total_windows": calc_windows(total_samples)
        }


# ============================================================
# Manager 5: Serial Connection & Hardware Port Manager
# ============================================================

class SerialManager:
    """Handles serial COM port diagnostics, hot-plug detection, and serial connection lifecycle."""

    def __init__(self):
        self.serial_conn = None
        self.known_ports_map = {}
        self.last_esp_port = None
        self.scan_error_count = 0

    def scan_ports(self):
        start_t = time.time()
        try:
            current_ports = list(serial.tools.list_ports.comports())
            elapsed = time.time() - start_t
            self.scan_error_count = 0
            current_map = {p.device: f"{p.device} - {p.description}" for p in current_ports}
            return current_map, elapsed, None
        except Exception as e:
            self.scan_error_count += 1
            logger.warning(f"Serial port scan exception (attempt {self.scan_error_count}): {e}")
            return self.known_ports_map, 0.0, e

    def connect(self, port, baud_rate):
        if self.serial_conn and self.serial_conn.is_open:
            self.close()
        self.serial_conn = serial.Serial(port, baud_rate, timeout=1)
        return self.serial_conn

    def close(self):
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception as e:
                logger.warning(f"Error closing serial connection: {e}")
            self.serial_conn = None


# ============================================================
# BLE Collector Application (Tkinter GUI Controller)
# ============================================================

class BLECollector:

    def __init__(self, root):
        self.root = root
        self.root.title("BLE Tracker - Dataset Collector Studio")
        self.root.geometry("880x760")
        self.root.minsize(820, 680)

        # Instantiate Manager Classes
        self.config_mgr = ConfigManager(CONFIG_PATH)
        self.serial_mgr = SerialManager()
        self.writer_mgr = DatasetWriter(
            DATA_DIR,
            buffer_flush_size=self.config_mgr.get("buffer_flush_size", 50)
        )
        self.auditor_mgr = DatasetAuditor(
            DATA_DIR,
            target_windows=self.config_mgr.get("target_windows_goal", 2500),
            window_size=self.config_mgr.get("window_size", 50),
            stride=self.config_mgr.get("stride", 10)
        )
        self.streamer_mgr = NetworkStreamer(
            endpoint_url=self.config_mgr.get("stream_endpoint_url", "http://localhost:8000/api/observation"),
            enabled=self.config_mgr.get("stream_enabled", True)
        )
        self.streamer_mgr.start()

        # Serial & Threading State
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.current_port = None
        self.current_baud = self.config_mgr.get("baud_rate", DEFAULT_BAUD_RATE)

        # Port Monitoring State
        self.auto_scan_enabled = True

        # Firmware Flashing State
        self.flashing = False
        self.auto_flash_var = tk.BooleanVar(value=False)

        # Collection State
        self.collecting = False
        self.paused = False
        self.start_time = None
        self.samples_count = 0

        # Thread Queue
        self.data_queue = queue.Queue()

        # Apply Modern Styling
        self.setup_styles()

        # Build User Interface
        self.build_gui()

        # Initial Diagnostic Report
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

        # Detect System Font Fallbacks
        font_primary, font_mono = get_system_font_families()
        self.font_primary = font_primary
        self.font_mono = font_mono

        bg_dark = "#181825"
        card_bg = "#1e1e2e"
        card_border = "#313244"
        fg_text = "#cdd6f4"
        fg_muted = "#a6adc8"
        accent_blue = "#89b4fa"
        accent_green = "#a6e3a1"
        accent_yellow = "#f9e2af"
        accent_red = "#f38ba8"

        self.style.configure(".", background=bg_dark, foreground=fg_text, font=(font_primary, 10))
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
            font=(font_primary, 11, "bold")
        )

        self.style.configure("TLabel", background=card_bg, foreground=fg_text)
        self.style.configure("Subtext.TLabel", background=card_bg, foreground=fg_muted, font=(font_primary, 9))
        self.style.configure("Header.TLabel", background=bg_dark, foreground="#cba6f7", font=(font_primary, 18, "bold"))
        self.style.configure("Status.TLabel", background=card_bg, font=(font_primary, 11, "bold"))

        self.style.configure("StatVal.TLabel", background=card_bg, foreground=accent_blue, font=(font_primary, 14, "bold"))
        self.style.configure("StatLbl.TLabel", background=card_bg, foreground=fg_muted, font=(font_primary, 9))

        self.style.configure(
            "Primary.TButton",
            font=(font_primary, 10, "bold"),
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
            font=(font_primary, 10, "bold"),
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
            font=(font_primary, 10, "bold"),
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
            font=(font_primary, 9),
            background="#313244",
            foreground=fg_text,
            padding=(8, 4)
        )
        self.style.map("Secondary.TButton", background=[("active", "#45475a")])

        self.style.configure(
            "Pill.TButton",
            font=(font_primary, 9),
            background="#313244",
            foreground="#cdd6f4",
            padding=(6, 3)
        )
        self.style.map(
            "Pill.TButton",
            background=[("active", accent_blue)],
            foreground=[("active", "#11111b")]
        )

        self.style.configure("TEntry", fieldbackground="#313244", foreground=fg_text, insertcolor=fg_text)

        self.style.configure(
            "Treeview",
            background="#1e1e2e",
            foreground="#cdd6f4",
            fieldbackground="#1e1e2e",
            rowheight=26,
            font=(font_primary, 9)
        )
        self.style.configure(
            "Treeview.Heading",
            background="#313244",
            foreground="#89b4fa",
            font=(font_primary, 10, "bold")
        )
        self.style.map("Treeview", background=[("selected", "#45475a")], foreground=[("selected", "#cdd6f4")])


    # ========================================================
    # GUI Construction
    # ========================================================

    def build_gui(self):
        canvas = tk.Canvas(self.root, bg="#181825", highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)

        main_container = ttk.Frame(canvas, padding=15)
        main_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas_frame = canvas.create_window((0, 0), window=main_container, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_frame, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=v_scrollbar.set)

        v_scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Top Header ---
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 10))

        title = ttk.Label(header_frame, text="📡 BLE TRACKER — DATASET COLLECTOR STUDIO", style="Header.TLabel")
        title.pack(side="left")

        subtitle = ttk.Label(
            header_frame,
            text="ESP32 RSSI & Metadata Acquisition System (Modular V3)",
            style="Subtext.TLabel",
            background="#181825"
        )
        subtitle.pack(side="right", anchor="e", pady=5)

        # --- Section 1: ESP32 Connection Card ---
        conn_box = ttk.LabelFrame(main_container, text="1. ESP32 Connection Setup", style="Card.TLabelframe")
        conn_box.pack(fill="x", pady=(0, 10))

        ttk.Label(conn_box, text="Serial COM Port:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.port_combo = ttk.Combobox(conn_box, width=32, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        refresh_btn = ttk.Button(conn_box, text="🔄 Scan Ports Now", style="Secondary.TButton", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        self.autoscan_lbl = ttk.Label(conn_box, text="⚡ Auto-Scan: ACTIVE (1.5s)", style="Subtext.TLabel", foreground="#a6e3a1")
        self.autoscan_lbl.grid(row=0, column=3, padx=(10, 5), pady=5)

        ttk.Label(conn_box, text="Baud Rate:").grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.baud_combo = ttk.Combobox(conn_box, values=BAUD_RATES, width=12, state="readonly")
        self.baud_combo.set(self.current_baud)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.device_info_lbl = ttk.Label(conn_box, text="Device: Scanning...", style="Subtext.TLabel", foreground="#89b4fa")
        self.device_info_lbl.grid(row=1, column=2, columnspan=2, sticky="w", padx=5, pady=5)

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
            text="\U0001f3b2 Random Dist",
            style="Secondary.TButton",
            command=self.set_random_distance
        )
        rand_btn.pack(side="left", padx=(8, 0))

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

        ttk.Label(exp_box, text="Motion Mode:").grid(row=2, column=0, sticky="w", padx=5, pady=5)

        motion_frame = ttk.Frame(exp_box)
        motion_frame.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        self.motion_combo = ttk.Combobox(
            motion_frame,
            values=["stationary", "approaching", "moving_away"],
            state="readonly",
            width=18
        )
        self.motion_combo.set("stationary")
        self.motion_combo.pack(side="left", padx=(0, 10))

        ttk.Label(
            motion_frame,
            text="\U0001f6b6 Stationary = still | Approaching = walking toward beacon | Moving Away = walking from beacon",
            style="Subtext.TLabel"
        ).pack(side="left")

        ttk.Label(exp_box, text="Environment / Dirty Data Mode:").grid(row=3, column=0, sticky="w", padx=5, pady=5)

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
        self.dirty_mode_combo.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        self.dirty_mode_combo.bind("<<ComboboxSelected>>", self.on_dirty_preset_change)

        ttk.Label(exp_box, text="Is there an obstacle?").grid(row=4, column=0, sticky="w", padx=5, pady=5)

        self.obstacle_combo = ttk.Combobox(exp_box, values=["No", "Yes"], state="readonly", width=10)
        self.obstacle_combo.set("No")
        self.obstacle_combo.grid(row=4, column=1, sticky="w", padx=5, pady=5)
        self.obstacle_combo.bind("<<ComboboxSelected>>", self.on_obstacle_change)

        ttk.Label(exp_box, text="Obstacle Type / Material:").grid(row=4, column=2, sticky="w", padx=(20, 5), pady=5)

        obs_type_frame = ttk.Frame(exp_box)
        obs_type_frame.grid(row=4, column=3, sticky="w", padx=5, pady=5)

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
            text="\U0001f4a1 Tip: Collecting arbitrary distances, heights, and 'Dirty Data' ensures maximum ML model robustness.",
            style="Subtext.TLabel"
        ).grid(row=5, column=0, columnspan=4, sticky="w", padx=5, pady=(5, 0))

        # --- Section 3: Live Dashboard & Controls ---
        ctrl_box = ttk.LabelFrame(main_container, text="3. Collection Controls & Live Metrics", style="Card.TLabelframe")
        ctrl_box.pack(fill="x", pady=(0, 10))

        ctrl_layout = ttk.Frame(ctrl_box)
        ctrl_layout.pack(fill="x")

        btn_frame = ttk.Frame(ctrl_layout)
        btn_frame.pack(side="left", anchor="w")

        self.start_button = ttk.Button(btn_frame, text="▶ START RECORDING", style="Primary.TButton", command=self.start_collection)
        self.start_button.pack(side="left", padx=(0, 8))

        self.pause_button = ttk.Button(btn_frame, text="⏸ PAUSE", style="Warning.TButton", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(btn_frame, text="⏹ STOP & SAVE", style="Danger.TButton", command=self.stop_collection, state="disabled")
        self.stop_button.pack(side="left", padx=(0, 8))

        metrics_frame = ttk.Frame(ctrl_layout)
        metrics_frame.pack(side="right", anchor="e")

        s_box = ttk.Frame(metrics_frame, padding=(10, 2))
        s_box.pack(side="left", padx=10)
        self.samples_lbl = ttk.Label(s_box, text="0", style="StatVal.TLabel")
        self.samples_lbl.pack()
        ttk.Label(s_box, text="SAMPLES", style="StatLbl.TLabel").pack()

        r_box = ttk.Frame(metrics_frame, padding=(10, 2))
        r_box.pack(side="left", padx=10)
        self.rate_lbl = ttk.Label(r_box, text="0.0 Hz", style="StatVal.TLabel")
        self.rate_lbl.pack()
        ttk.Label(r_box, text="SAMPLE RATE", style="StatLbl.TLabel").pack()

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

        c_toolbar = ttk.Frame(console_box)
        c_toolbar.pack(fill="x", pady=(0, 5))

        ttk.Label(c_toolbar, text="Stream Log:", style="Subtext.TLabel").pack(side="left")

        diag_btn = ttk.Button(c_toolbar, text="🔍 Re-run Port Diagnostic", style="Secondary.TButton", command=self.run_initial_port_diagnostic)
        diag_btn.pack(side="right", padx=(5, 0))

        clear_btn = ttk.Button(c_toolbar, text="🗑 Clear Console", style="Secondary.TButton", command=self.clear_console)
        clear_btn.pack(side="right")

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
            font=(getattr(self, "font_mono", "Consolas"), 9),
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set
        )
        self.console.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.console.yview)

        self.console.tag_config("INFO", foreground="#89b4fa")
        self.console.tag_config("DATA", foreground="#a6e3a1")
        self.console.tag_config("WARN", foreground="#f9e2af")
        self.console.tag_config("ERROR", foreground="#f38ba8")
        self.console.tag_config("SYS", foreground="#cba6f7")

        # --- Section 5: True Multi-Dimensional Dataset Quality & Coverage Audit ---
        audit_box = ttk.LabelFrame(main_container, text="5. Multi-Dimensional Dataset Quality & Coverage Audit", style="Card.TLabelframe")
        audit_box.pack(fill="x", pady=(10, 0))

        audit_top = ttk.Frame(audit_box)
        audit_top.pack(fill="x", pady=(0, 5))

        self.audit_summary_lbl = ttk.Label(
            audit_top,
            text="Scanning raw dataset files across 5 experimental dimensions...",
            style="Subtext.TLabel",
            foreground="#f9e2af"
        )
        self.audit_summary_lbl.pack(side="left")

        audit_ctrls = ttk.Frame(audit_top)
        audit_ctrls.pack(side="right")

        ttk.Label(audit_ctrls, text="Dimension Filter:", style="Subtext.TLabel").pack(side="left", padx=(0, 5))

        self.audit_dim_combo = ttk.Combobox(
            audit_ctrls,
            values=["Distance (m)", "Height / Elevation (m)", "Motion Mode", "Environment / Obstacle", "Anchor Nodes"],
            state="readonly",
            width=22
        )
        self.audit_dim_combo.set("Distance (m)")
        self.audit_dim_combo.pack(side="left", padx=(0, 10))
        self.audit_dim_combo.bind("<<ComboboxSelected>>", self.on_audit_dim_change)

        ttk.Button(
            audit_ctrls,
            text="🔄 Refresh Deficit Audit",
            style="Secondary.TButton",
            command=self.refresh_dataset_audit
        ).pack(side="left")

        tree_frame = ttk.Frame(audit_box)
        tree_frame.pack(fill="x", expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll.pack(side="right", fill="y")

        self.audit_tree = ttk.Treeview(
            tree_frame,
            columns=("category", "current_win", "target_win", "missing_win", "est_min", "status"),
            show="headings",
            height=5,
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.audit_tree.yview)

        self.audit_tree.heading("category", text="Category / Preset")
        self.audit_tree.heading("current_win", text="Current Windows")
        self.audit_tree.heading("target_win", text="Target Goal")
        self.audit_tree.heading("missing_win", text="Missing Deficit")
        self.audit_tree.heading("est_min", text="Est. Mins (Empirical)")
        self.audit_tree.heading("status", text="Coverage Status")

        self.audit_tree.column("category", width=140, anchor="center")
        self.audit_tree.column("current_win", width=120, anchor="center")
        self.audit_tree.column("target_win", width=110, anchor="center")
        self.audit_tree.column("missing_win", width=120, anchor="center")
        self.audit_tree.column("est_min", width=140, anchor="center")
        self.audit_tree.column("status", width=180, anchor="center")

        self.audit_tree.pack(side="left", fill="both", expand=True)


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

        current_map, elapsed, err = self.serial_mgr.scan_ports()
        esp_port_info = None

        if err or not current_map:
            self.log("WARN", " [✖] No active serial COM ports detected on this system.")
            self.log("WARN", "     Please connect your ESP32 via USB data cable.")
            self.log("SYS", " Status: Auto-port scanner ACTIVE (scanning every 1.5s).")
            self.port_combo["values"] = []
            self.port_combo.set("No COM ports found")
            self.device_info_lbl.config(text="Device: None detected", foreground="#f38ba8")
            self.status_dot.config(text="● NO ESP32 DETECTED — Waiting for USB connection...", foreground="#f38ba8")
        else:
            port_list_display = list(current_map.values())
            for dev_str, full_disp in current_map.items():
                desc_lower = full_disp.lower()
                is_esp = any(k in desc_lower for k in ["ch340", "cp210", "ftdi", "uart", "esp32", "usb-serial"])

                self.log("INFO", f" [✔] Port Detected: {dev_str}")
                self.log("INFO", f"     • Description : {full_disp}")

                if is_esp:
                    self.log("SYS", "     • Detection   : ★ Recognized ESP32 USB-UART Serial Bridge!")
                    if not esp_port_info:
                        esp_port_info = (dev_str, full_disp)

            self.port_combo["values"] = port_list_display

            if esp_port_info:
                dev_code, dev_disp = esp_port_info
                self.port_combo.set(dev_disp)
                self.serial_mgr.last_esp_port = dev_code
                self.device_info_lbl.config(text=f"Detected: {dev_disp.split(' - ')[1]}", foreground="#a6e3a1")
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
        next_interval = 1500

        if self.auto_scan_enabled:
            current_map, elapsed, err = self.serial_mgr.scan_ports()

            if err:
                next_interval = min(5000, 1500 * (2 ** min(self.serial_mgr.scan_error_count, 3)))
                logger.warning(f"Port scanner glitch (retry in {next_interval}ms): {err}")
            else:
                if elapsed > 0.2:
                    next_interval = 2500

                added_ports = set(current_map.keys()) - set(self.serial_mgr.known_ports_map.keys())
                if added_ports:
                    for new_p in added_ports:
                        desc = current_map[new_p]
                        self.log("SYS", f"⚡ HOT-PLUG EVENT: New device connected on {new_p} ({desc})")

                        desc_lower = desc.lower()
                        if any(k in desc_lower for k in ["ch340", "cp210", "ftdi", "uart", "esp32", "usb-serial"]):
                            self.log("SYS", f"★ Auto-detected ESP32 on {new_p}! Updating port selection.")
                            self.serial_mgr.last_esp_port = new_p
                            if not self.collecting and not self.flashing:
                                self.port_combo.set(desc)
                                self.device_info_lbl.config(text=f"Detected: {desc.split(' - ')[1]}", foreground="#a6e3a1")
                                self.status_dot.config(text=f"● ESP32 READY on {new_p}", foreground="#a6e3a1")

                                if self.auto_flash_var.get():
                                    self.log("SYS", f"⚡ Auto-Flash trigger for newly connected ESP32 on {new_p}...")
                                    self.root.after(500, lambda p=new_p: self.start_flash_firmware(p))

                removed_ports = set(self.serial_mgr.known_ports_map.keys()) - set(current_map.keys())
                if removed_ports:
                    for rem_p in removed_ports:
                        self.log("WARN", f"⚠️ DISCONNECT EVENT: Serial device removed from {rem_p}")

                        if self.collecting and self.current_port == rem_p:
                            self.log("ERROR", f"CRITICAL: Active ESP32 serial port {rem_p} was physically disconnected!")
                            self.data_queue.put(("PORT_DISCONNECTED", rem_p))

                if added_ports or removed_ports:
                    self.serial_mgr.known_ports_map = current_map
                    port_values = list(current_map.values())
                    self.port_combo["values"] = port_values

                    if not port_values and not self.collecting:
                        self.port_combo.set("No COM ports found")
                        self.device_info_lbl.config(text="Device: None detected", foreground="#f38ba8")
                        self.status_dot.config(text="● NO ESP32 DETECTED — Connect via USB", foreground="#f38ba8")

        self.root.after(next_interval, self.auto_scan_ports_loop)


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

        self.serial_mgr.close()

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

    # ========================================================
    # Helper Handlers & Presets
    # ========================================================

    def refresh_dataset_audit(self):
        """Asynchronously performs true multi-dimensional sliding window dataset coverage analysis."""
        if hasattr(self, "audit_summary_lbl"):
            self.audit_summary_lbl.config(text="⚡ Auditing dataset quality & coverage across 5 dimensions...", foreground="#89b4fa")

        def audit_worker():
            audit_data = self.auditor_mgr.run_audit()
            self.data_queue.put(("AUDIT_RESULT", audit_data))

        threading.Thread(target=audit_worker, daemon=True).start()

    def on_audit_dim_change(self, event=None):
        if hasattr(self, "last_audit_data") and self.last_audit_data:
            self.render_audit_dim_data(self.last_audit_data)

    def update_audit_ui(self, audit_data):
        self.last_audit_data = audit_data
        self.render_audit_dim_data(audit_data)

    def render_audit_dim_data(self, audit_data):
        """Renders Section 5 Treeview and summary label according to selected dimension filter."""
        if hasattr(self, "audit_tree"):
            for item in self.audit_tree.get_children():
                self.audit_tree.delete(item)

        dim_choice = self.audit_dim_combo.get() if hasattr(self, "audit_dim_combo") else "Distance (m)"
        dim_map = {
            "Distance (m)": "distance",
            "Height / Elevation (m)": "height",
            "Motion Mode": "motion",
            "Environment / Obstacle": "obstacle",
            "Anchor Nodes": "anchor"
        }
        dim_key = dim_map.get(dim_choice, "distance")

        dim_info = audit_data.get(dim_key, {})
        records = dim_info.get("records", {})
        target_goal = dim_info.get("target", 2500)
        sample_rate_hz = audit_data.get("sample_rate_hz", 20.0)
        stride = self.config_mgr.get("stride", 10)

        total_missing = 0
        critical_missing = []

        for category, current in records.items():
            cat_label = f"{category} m" if dim_key in ["distance", "height"] else str(category)
            missing = max(0, target_goal - current)
            total_missing += missing

            # Dynamic empirical time estimate based on measured packet rate (Hz)
            est_mins = round((missing * stride) / (max(sample_rate_hz, 0.1) * 60.0), 1)

            # Percentage-based Coverage Tiers
            pct = round((current / max(target_goal, 1)) * 100, 1)

            if pct == 0:
                status = "🔴 CRITICAL (0%)"
                critical_missing.append(cat_label)
            elif pct < 50:
                status = f"🟠 LOW ({pct}%)"
                critical_missing.append(cat_label)
            elif pct < 90:
                status = f"🟡 MODERATE ({pct}%)"
            elif pct < 100:
                status = f"🟢 NEARLY COMPLETE ({pct}%)"
            else:
                status = f"✅ COMPLETE ({pct}%)"

            if hasattr(self, "audit_tree"):
                self.audit_tree.insert(
                    "", "end",
                    values=(cat_label, f"{current:,} win", f"{target_goal:,} win", f"{missing:,} win", f"~{est_mins} mins", status)
                )

        if hasattr(self, "audit_summary_lbl"):
            tot_win = audit_data.get("total_windows", 0)
            tot_samp = audit_data.get("total_samples", 0)
            if critical_missing:
                msg = f"⚠️ Dataset Deficit [{dim_choice}]: Deficit in {', '.join(critical_missing)}. Total: {tot_win:,} windows ({tot_samp:,} packets @ {sample_rate_hz} Hz)."
                self.audit_summary_lbl.config(text=msg, foreground="#f38ba8")
            else:
                msg = f"✅ High Quality Coverage [{dim_choice}]: Total dataset: {tot_win:,} windows ({tot_samp:,} packets @ {sample_rate_hz} Hz)."
                self.audit_summary_lbl.config(text=msg, foreground="#a6e3a1")

    def set_preset_distance(self, value_str):
        if not self.collecting:
            self.distance_entry.delete(0, tk.END)
            self.distance_entry.insert(0, value_str)

    def set_random_distance(self):
        if not self.collecting:
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

        selected_port_str = self.port_combo.get()
        if not selected_port_str or "No COM ports" in selected_port_str:
            messagebox.showerror("Connection Error", "Please connect a valid ESP32 COM port.")
            return

        port = selected_port_str.split(" - ")[0]
        self.current_port = port

        try:
            baud_rate = int(self.baud_combo.get())
        except ValueError:
            baud_rate = DEFAULT_BAUD_RATE
        self.current_baud = baud_rate

        obstacle = self.obstacle_combo.get()
        obstacle_type = self.obstacle_type_combo.get().strip()
        if obstacle == "No":
            obstacle_type = "None"
        elif not obstacle_type:
            obstacle_type = "Unspecified"

        motion = self.motion_combo.get() if hasattr(self, 'motion_combo') else "stationary"
        dirty_mode = self.dirty_mode_combo.get() if hasattr(self, 'dirty_mode_combo') else ""
        target_mac = self.config_mgr.get("target_mac_filter", "52:06:26:03:01:DA")

        try:
            # Start Writer Session (creates dataset_info.json sidecar metadata)
            filename = self.writer_mgr.start_session(
                distance=distance,
                obstacle=obstacle,
                obstacle_type=obstacle_type,
                height_m=height_m,
                motion=motion,
                dirty_mode=dirty_mode,
                target_mac=target_mac
            )

            # Connect Serial via Manager
            serial_conn = self.serial_mgr.connect(port, baud_rate)

            # State Updates
            self.collecting = True
            self.paused = False
            self.stop_event.clear()
            self.samples_count = 0
            self.start_time = time.time()

            # UI Controls Update
            self.lock_inputs(True)
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal", text="⏸ PAUSE")
            self.stop_button.config(state="normal")

            self.status_dot.config(text=f"● COLLECTING | {port}", foreground="#a6e3a1")
            self.file_info_lbl.config(text=f"File: {filename}")
            self.samples_lbl.config(text="0")
            self.rate_lbl.config(text="0.0 Hz")

            self.log("SYS", f"Started session logging to: {filename}")
            self.log("SYS", f"Params \u2192 Port: {port} @ {baud_rate} baud | Dist: {distance}m | Height: {height_m}m | Motion: {motion} | Obstacle: {obstacle} ({obstacle_type})")

            # Start Reader Thread
            self.reader_thread = threading.Thread(
                target=self.serial_reader,
                args=(distance, obstacle, obstacle_type, height_m, motion),
                daemon=True
            )
            self.reader_thread.start()

        except Exception as e:
            messagebox.showerror("Serial Error", f"Failed to connect to {port}:\n{str(e)}")
            self.cleanup()


    # ========================================================
    # Worker Thread: Serial Reader
    # ========================================================

    def serial_reader(self, distance, obstacle, obstacle_type, height_m=1.0, motion="stationary"):
        while not self.stop_event.is_set():
            try:
                conn = self.serial_mgr.serial_conn
                if not conn or not conn.is_open:
                    break

                raw_line = conn.readline()
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line.startswith("timestamp,"):
                    continue

                parts = line.split(",")
                if len(parts) < 5:
                    continue

                timestamp = parts[0].strip()
                anchor = parts[1].strip()
                mac = parts[2].strip()
                rssi = parts[3].strip()
                name = ",".join(parts[4:]).strip()

                if not timestamp.isdigit():
                    continue
                if ":" not in mac or len(mac) < 11:
                    continue
                try:
                    int(rssi)
                except ValueError:
                    continue

                target_mac = self.config_mgr.get("target_mac_filter", "52:06:26:03:01:DA")
                if target_mac and mac.upper() != target_mac.upper():
                    continue

                row = [
                    timestamp, anchor, mac, rssi, name,
                    distance, obstacle, obstacle_type, height_m, motion
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

                if isinstance(item, tuple) and item[0] == "AUDIT_RESULT":
                    audit_data = item[1]
                    self.update_audit_ui(audit_data)
                    continue

                if isinstance(item, tuple) and item[0] == "FLASH_LOG":
                    self.log("SYS", item[1])
                    continue

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

                if isinstance(item, tuple) and item[0] == "PORT_DISCONNECTED":
                    self.log("ERROR", f"CRITICAL: Serial Port disconnect error ({item[1]})")
                    self.status_dot.config(text=f"🔴 DISCONNECTED ({self.current_port}) — Re-plug ESP32 USB", foreground="#f38ba8")
                    self.paused = True
                    self.pause_button.config(text="▶ RESUME (When Re-connected)")
                    messagebox.showwarning("Device Disconnected", f"ESP32 on {self.current_port} was unplugged or lost power!\n\nCollection is PAUSED. Re-plug USB and click RESUME or STOP.")
                    continue

                if isinstance(item, tuple) and item[0] == "ERROR":
                    self.log("ERROR", f"Serial Exception: {item[1]}")
                    continue

                if self.paused:
                    continue

                row = item

                # Buffered CSV Write (no flush per row!)
                self.writer_mgr.write_row(row)

                # Push to Persistent Network Streamer Thread
                self.streamer_mgr.push(row)

                self.samples_count += 1

                # Update Live Metrics Labels
                self.samples_lbl.config(text=str(self.samples_count))

                elapsed = time.time() - self.start_time if self.start_time else 1.0
                rate = self.samples_count / max(elapsed, 0.1)
                self.rate_lbl.config(text=f"{rate:.1f} Hz")

                # Console Stream Log
                rssi_val = row[3]
                anchor_id = row[1]
                mac_addr = row[2]
                motion_val = row[9] if len(row) > 9 else "stationary"
                self.log("DATA", f"[{anchor_id}] {mac_addr} | RSSI: {rssi_val} dBm | Dist: {row[5]}m | Motion: {motion_val}")

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
            self.writer_mgr.flush()
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
        self.serial_mgr.close()

        # Flush & close CSV writer, save dataset_info.json sidecar metadata
        dataset_path, total_samples = self.writer_mgr.stop_session()

        self.collecting = False
        self.paused = False

        # UI State Reset
        self.lock_inputs(False)
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled", text="⏸ PAUSE")
        self.stop_button.config(state="disabled")

        self.status_dot.config(text="● STOPPED & SAVED", foreground="#89b4fa")
        self.log("SYS", f"Session completed. Total saved samples: {total_samples}")
        self.log("SYS", f"Output File: {dataset_path}")
        self.log("SYS", f"Metadata File: {self.writer_mgr.metadata_path}")

        messagebox.showinfo(
            "Collection Complete",
            f"Successfully recorded {total_samples} BLE samples!\n\nSaved to:\n{dataset_path}\n\nMetadata written to dataset_info.json"
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
        if hasattr(self, 'motion_combo'):
            self.motion_combo.config(state=state)
        if self.obstacle_combo.get() == "Yes" and not lock:
            self.obstacle_type_combo.config(state="normal")
        else:
            self.obstacle_type_combo.config(state="disabled" if lock else ("normal" if self.obstacle_combo.get() == "Yes" else "disabled"))

    def cleanup(self):
        self.stop_event.set()
        self.serial_mgr.close()
        self.writer_mgr.stop_session()
        self.streamer_mgr.stop()
        self.collecting = False
        self.root.destroy()


    # ========================================================
    # Console Logger
    # ========================================================

    def log(self, tag, message):
        self.console.config(state="normal")

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
