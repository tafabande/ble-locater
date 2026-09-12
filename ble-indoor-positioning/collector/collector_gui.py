"""Indoor Positioning — Standalone Data Collector GUI.

A focused, modular Python application for collecting BLE dataset observations.
Delegates session tracking to session_manager, packet ingestion to recording engine,
and real-time checks to the data quality validator.
"""
from __future__ import annotations

import datetime
import os
import queue
import subprocess
import sys
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import RAW_DATA_DIR, load_anchor_config
from core.ble import list_serial_ports, calculate_log_distance
from collector.session_manager import SessionManager, SessionConfig
from collector.recording import RecordingEngine
from collector.validation import QualityVerdict


class DataCollectorApp:
    """Dedicated desktop GUI for BLE RSSI dataset collection."""

    THEME = {
        "bg": "#0F172A",          # Slate 900
        "panel": "#1E293B",       # Slate 800
        "card": "#334155",        # Slate 700
        "border": "#475569",      # Slate 600
        "text": "#F8FAFC",        # Slate 50
        "subtext": "#94A3B8",     # Slate 400
        "accent": "#0EA5E9",      # Sky 500
        "accent_hover": "#0284C7",
        "green": "#10B981",       # Emerald 500
        "green_dark": "#065F46",
        "red": "#EF4444",         # Rose 500
        "red_dark": "#991B1B",
        "amber": "#F59E0B",       # Amber 500
        "purple": "#8B5CF6",      # Violet 500
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("📡 BLE RTLS — Sensor Data Collector")
        self.root.geometry("1180x820")
        self.root.minsize(1020, 680)
        self.root.configure(bg=self.THEME["bg"])

        # Modular components
        self.session_manager = SessionManager()
        self.packet_queue: queue.Queue[dict] = queue.Queue()
        self.recording_engine = RecordingEngine(self.packet_queue)

        # UI Form Variables
        self.session_name_var = tk.StringVar(value=f"survey_{datetime.date.today().strftime('%Y%m%d')}_01")
        self.target_mac_var = tk.StringVar(value="52:06:26:03:01:DA")
        self.distance_var = tk.DoubleVar(value=1.0)
        self.anchor_var = tk.StringVar(value="ANCHOR_01")
        self.condition_var = tk.StringVar(value="Line-of-Sight (LOS)")
        self.tag_height_var = tk.DoubleVar(value=1.0)
        self.notes_var = tk.StringVar(value="Floor tripod, indoor ambient")
        self.target_samples_var = tk.IntVar(value=100)
        self.port_var = tk.StringVar(value="Simulated Stream")

        self.sample_count = 0
        self.rssi_buffer: list[int] = []

        self._configure_styles()
        self._build_ui()

        # Periodically refresh packet queue and UI
        self.root.after(80, self._process_packet_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        t = self.THEME

        style.configure("TFrame", background=t["bg"])
        style.configure("Panel.TFrame", background=t["panel"])
        style.configure("Card.TFrame", background=t["card"])
        style.configure("TLabel", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=t["panel"], foreground=t["text"], font=("Segoe UI", 12, "bold"))
        style.configure("Muted.TLabel", background=t["panel"], foreground=t["subtext"], font=("Segoe UI", 8))

        style.configure("TCombobox", fieldbackground=t["card"], background=t["card"], foreground=t["text"], padding=4)
        style.configure("TEntry", fieldbackground=t["card"], foreground=t["text"], padding=4)

    def _build_ui(self) -> None:
        # Top Header Bar
        header = tk.Frame(self.root, bg=self.THEME["panel"], height=60)
        header.pack(fill="x", side="top")

        title_box = tk.Frame(header, bg=self.THEME["panel"])
        title_box.pack(side="left", padx=20, pady=12)

        tk.Label(title_box, text="📡 BLE DATASET COLLECTOR", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(title_box, text="· Standalone Ground-Truth Survey Engine", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 9)).pack(side="left", padx=10)

        # Status badge
        self.status_badge = tk.Label(header, text="○  IDLE", bg=self.THEME["card"], fg=self.THEME["subtext"], font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.status_badge.pack(side="right", padx=20, pady=14)

        # Main horizontal split
        container = tk.Frame(self.root, bg=self.THEME["bg"])
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Left Column: Setup & Parameters
        left_col = tk.Frame(container, bg=self.THEME["panel"], width=460)
        left_col.pack(side="left", fill="y", padx=(0, 12))
        left_col.pack_propagate(False)

        self._build_setup_panel(left_col)

        # Right Column: Live Telemetry, Gauges, Quality & History
        right_col = tk.Frame(container, bg=self.THEME["bg"])
        right_col.pack(side="right", fill="both", expand=True)

        self._build_telemetry_panel(right_col)

    def _build_setup_panel(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        tk.Label(p, text="SESSION PARAMETERS", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 8))

        form = tk.Frame(p, bg=t["panel"])
        form.pack(fill="x", padx=18)

        # Session name
        tk.Label(form, text="Session Name", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 2))
        ttk.Entry(form, textvariable=self.session_name_var).pack(fill="x")

        # Target MAC
        tk.Label(form, text="Target Beacon MAC", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        ttk.Entry(form, textvariable=self.target_mac_var).pack(fill="x")

        # Ground Truth Distance (Presets + Custom)
        tk.Label(form, text="Ground-Truth Distance (meters)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        dist_box = tk.Frame(form, bg=t["panel"])
        dist_box.pack(fill="x")

        for d_val in (0.5, 1.0, 2.0, 3.0, 5.0):
            tk.Button(
                dist_box, text=f"{d_val}m",
                bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"),
                relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda val=d_val: self.distance_var.set(val),
            ).pack(side="left", padx=2)

        ttk.Entry(dist_box, textvariable=self.distance_var, width=8).pack(side="right", padx=(4, 0))

        # Anchor Selector
        tk.Label(form, text="Recording Anchor Node", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        anchors = list(load_anchor_config().keys()) + ["All Anchors"]
        ttk.Combobox(form, textvariable=self.anchor_var, values=anchors, state="readonly").pack(fill="x")

        # Environmental Conditions
        tk.Label(form, text="Environmental Condition", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        conditions = [
            "Line-of-Sight (LOS)",
            "Non-Line-of-Sight (NLOS)",
            "Obstacle Shadow (Metal/Concrete)",
            "High Multipath (Reflective)",
            "Human Body Shadowing",
        ]
        ttk.Combobox(form, textvariable=self.condition_var, values=conditions, state="readonly").pack(fill="x")

        # Tag height & Notes
        tk.Label(form, text="Tag Height (meters)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        ttk.Entry(form, textvariable=self.tag_height_var).pack(fill="x")

        tk.Label(form, text="Survey Notes / Orientation", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        ttk.Entry(form, textvariable=self.notes_var).pack(fill="x")

        # Source Port
        tk.Label(form, text="Data Ingestion Port", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        ports = ["Simulated Stream"] + [p["device"] for p in list_serial_ports()]
        ttk.Combobox(form, textvariable=self.port_var, values=ports, state="readonly").pack(fill="x")

        # Target Sample Count
        tk.Label(form, text="Target Sample Count", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 2))
        sample_opts = tk.Frame(form, bg=t["panel"])
        sample_opts.pack(fill="x")
        for count in (50, 100, 200, 500):
            tk.Button(
                sample_opts, text=str(count),
                bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"),
                relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda c=count: self.target_samples_var.set(c),
            ).pack(side="left", padx=2)

        ttk.Entry(sample_opts, textvariable=self.target_samples_var, width=8).pack(side="right")

        # Big Action Buttons
        btn_box = tk.Frame(p, bg=t["panel"])
        btn_box.pack(fill="x", padx=18, pady=(20, 12))

        self.btn_record = tk.Button(
            btn_box, text="▶  START RECORDING",
            bg=t["green"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", padx=14, pady=8,
            command=self.toggle_recording,
        )
        self.btn_record.pack(fill="x", pady=4)

        tk.Button(
            btn_box, text="📂 Open Raw Data Folder",
            bg=t["card"], fg=t["text"], font=("Segoe UI", 9),
            relief="flat", cursor="hand2", pady=4,
            command=self._open_raw_folder,
        ).pack(fill="x", pady=4)

    def _build_telemetry_panel(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        # Top KPI Cards
        kpi_row = tk.Frame(p, bg=t["bg"])
        kpi_row.pack(fill="x", pady=(0, 12))
        for i in range(4):
            kpi_row.columnconfigure(i, weight=1, uniform="kpi")

        self.kpi_rssi = self._create_kpi_card(kpi_row, 0, "CURRENT RSSI", "-- dBm", t["accent"])
        self.kpi_samples = self._create_kpi_card(kpi_row, 1, "SAMPLES RECORDED", "0 / 100", t["green"])
        self.kpi_stats = self._create_kpi_card(kpi_row, 2, "RUNNING MEAN / STD", "-- dBm (±--)", t["amber"])
        self.kpi_dist = self._create_kpi_card(kpi_row, 3, "PATH LOSS EST.", "-- m", t["purple"])

        # Progress bar
        self.progress = ttk.Progressbar(p, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 12))

        # Signal Quality Banner
        self.quality_banner = tk.Label(
            p, text="● Signal Analyzer Ready. Start recording to evaluate variance and RSSI distribution.",
            bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 9), padx=14, pady=8, anchor="w",
        )
        self.quality_banner.pack(fill="x", pady=(0, 12))

        # Real-time RSSI Level Canvas Meter
        meter_frame = tk.Frame(p, bg=t["panel"], padx=14, pady=10)
        meter_frame.pack(fill="x", pady=(0, 12))

        tk.Label(meter_frame, text="SIGNAL STRENGTH SPECTRUM", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.meter_canvas = tk.Canvas(meter_frame, bg="#0B132B", height=32, highlightthickness=0)
        self.meter_canvas.pack(fill="x", pady=(6, 2))

        # Recent Packet Stream Table
        table_frame = tk.Frame(p, bg=t["panel"], padx=14, pady=10)
        table_frame.pack(fill="both", expand=True)

        tk.Label(table_frame, text="VERBATIM INCOMING OBSERVATIONS", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        cols = ("time", "anchor", "mac", "rssi", "dist", "quality")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        self.tree.heading("time", text="Timestamp")
        self.tree.heading("anchor", text="Anchor ID")
        self.tree.heading("mac", text="Device MAC")
        self.tree.heading("rssi", text="RSSI (dBm)")
        self.tree.heading("dist", text="Ground Truth")
        self.tree.heading("quality", text="Quality Status")

        self.tree.column("time", width=110, anchor="center")
        self.tree.column("anchor", width=100, anchor="center")
        self.tree.column("mac", width=140, anchor="center")
        self.tree.column("rssi", width=90, anchor="center")
        self.tree.column("dist", width=100, anchor="center")
        self.tree.column("quality", width=150, anchor="w")

        self.tree.pack(fill="both", expand=True, pady=(6, 0))

    def _create_kpi_card(self, parent: tk.Frame, col: int, title: str, initial_val: str, color: str) -> tk.Label:
        card = tk.Frame(parent, bg=self.THEME["panel"], padx=14, pady=10)
        card.grid(row=0, column=col, sticky="nsew", padx=3)

        tk.Label(card, text=title, bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        val_lbl = tk.Label(card, text=initial_val, bg=self.THEME["panel"], fg=color, font=("Segoe UI", 13, "bold"))
        val_lbl.pack(anchor="w", pady=(3, 0))
        return val_lbl

    def toggle_recording(self) -> None:
        if not self.recording_engine.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self) -> None:
        # Validate and create session through SessionManager
        ok, msg, session = self.session_manager.create_session(
            name=self.session_name_var.get(),
            mac=self.target_mac_var.get(),
            distance_m=self.distance_var.get(),
            anchor_id=self.anchor_var.get(),
            condition=self.condition_var.get(),
            tag_height_m=self.tag_height_var.get(),
            notes=self.notes_var.get(),
            target_samples=self.target_samples_var.get(),
        )
        if not ok or not session:
            messagebox.showerror("Configuration Error", msg)
            return

        self.sample_count = 0
        self.rssi_buffer.clear()
        self.btn_record.config(text="⏹  STOP RECORDING", bg=self.THEME["red"])
        self.status_badge.config(text="●  RECORDING SESSION", bg=self.THEME["red_dark"], fg="#FFFFFF")

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.recording_engine.start_recording(session, self.port_var.get())

    def _stop_recording(self) -> None:
        count = self.recording_engine.stop_recording()
        self.btn_record.config(text="▶  START RECORDING", bg=self.THEME["green"])
        self.status_badge.config(text="○  IDLE", bg=self.THEME["card"], fg=self.THEME["subtext"])

        session = self.session_manager.active_session
        if session and session.target_file_path.exists():
            messagebox.showinfo(
                "Recording Complete",
                f"Collection saved successfully:\n{session.target_file_path.name}\n"
                f"Samples recorded: {count}",
            )

    def _process_packet_queue(self) -> None:
        target_max = self.target_samples_var.get()
        while not self.packet_queue.empty():
            pkt = self.packet_queue.get_nowait()
            rssi = int(pkt.get("rssi", -80))
            anchor = pkt.get("anchor_id", "Unknown")
            mac = pkt.get("device_mac", "Unknown")
            dist = pkt.get("distance", self.distance_var.get())
            verdict: QualityVerdict | None = pkt.get("quality_verdict")

            self.rssi_buffer.append(rssi)
            if len(self.rssi_buffer) > 100:
                self.rssi_buffer.pop(0)

            # Update KPI cards
            self.kpi_rssi.config(text=f"{rssi} dBm")
            est_dist = round(calculate_log_distance(rssi), 2)
            self.kpi_dist.config(text=f"{est_dist:.2f} m")

            mean_rssi = verdict.mean_rssi if verdict else -80.0
            std_rssi = verdict.std_rssi if verdict else 0.0
            self.kpi_stats.config(text=f"{mean_rssi} dBm (±{std_rssi})")

            self._draw_meter(rssi)

            if verdict:
                if verdict.status == "WARNING":
                    self.quality_banner.config(text=f"⚠ {verdict.message}", bg=self.THEME["red_dark"], fg="#FFFFFF")
                else:
                    self.quality_banner.config(text=f"✔ {verdict.message}", bg=self.THEME["green_dark"], fg="#FFFFFF")

            # Update sample progress if recording
            if self.recording_engine.is_recording:
                self.sample_count = pkt.get("sample_count", self.sample_count)
                self.kpi_samples.config(text=f"{self.sample_count} / {target_max}")
                pct = min(100, int((self.sample_count / max(1, target_max)) * 100))
                self.progress["value"] = pct

                t_str = time.strftime("%H:%M:%S")
                cond_text = verdict.status if verdict else "NOMINAL"
                self.tree.insert("", 0, values=(t_str, anchor, mac, f"{rssi} dBm", f"{dist}m", cond_text))
                if len(self.tree.get_children()) > 30:
                    self.tree.delete(self.tree.get_children()[-1])

                if self.sample_count >= target_max:
                    self._stop_recording()
                    break

        self.root.after(80, self._process_packet_queue)

    def _draw_meter(self, rssi: int) -> None:
        c = self.meter_canvas
        c.delete("all")
        width = c.winfo_width()
        if width <= 1:
            width = 600
        height = 32

        norm = max(0.0, min(1.0, (rssi - (-100.0)) / 70.0))
        bar_w = int(width * norm)

        color = self.THEME["green"] if rssi >= -65 else self.THEME["amber"] if rssi >= -80 else self.THEME["red"]

        c.create_rectangle(0, 0, bar_w, height, fill=color, outline="")
        c.create_text(
            bar_w - 8 if bar_w > 80 else bar_w + 40, height // 2,
            text=f"{rssi} dBm", fill="#FFFFFF", font=("Segoe UI", 9, "bold"),
        )

    def _open_raw_folder(self) -> None:
        if os.name == "nt":
            os.startfile(str(RAW_DATA_DIR))
        else:
            subprocess.Popen(["xdg-open", str(RAW_DATA_DIR)])

    def _on_close(self) -> None:
        self.recording_engine.stop_all()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = DataCollectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
