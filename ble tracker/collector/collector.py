import csv
import os
import sys
import time
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

os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# BLE Collector Application
# ============================================================

class BLECollector:

    def __init__(self, root):

        self.root = root
        self.root.title("BLE Tracker - Dataset Collector Studio")
        self.root.geometry("820x700")
        self.root.minsize(780, 640)

        # Serial & Threading
        self.serial_connection = None
        self.reader_thread = None
        self.stop_event = threading.Event()

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

        # Queue Processor Loop
        self.root.after(50, self.process_queue)

        # Initial Port Enumeration
        self.refresh_ports()


    # ========================================================
    # Theme & Styles
    # ========================================================

    def setup_styles(self):

        self.root.configure(bg="#181825")

        self.style = ttk.Style()
        
        # Use clam theme as foundation for custom color control
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

        refresh_btn = ttk.Button(conn_box, text="🔄 Refresh Ports", style="Secondary.TButton", command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Baud Rate Row
        ttk.Label(conn_box, text="Baud Rate:").grid(row=0, column=3, sticky="w", padx=(20, 5), pady=5)
        
        self.baud_combo = ttk.Combobox(conn_box, values=BAUD_RATES, width=12, state="readonly")
        self.baud_combo.set(DEFAULT_BAUD_RATE)
        self.baud_combo.grid(row=0, column=4, padx=5, pady=5, sticky="w")


        # --- Section 2: Experiment Metadata Card ---
        exp_box = ttk.LabelFrame(main_container, text="2. Ground Truth Experiment Metadata", style="Card.TLabelframe")
        exp_box.pack(fill="x", pady=(0, 10))

        # Distance Input & Presets
        ttk.Label(exp_box, text="Physical Distance (meters):").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        dist_input_frame = ttk.Frame(exp_box)
        dist_input_frame.grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        self.distance_entry = ttk.Entry(dist_input_frame, width=12)
        self.distance_entry.pack(side="left", padx=(0, 10))
        self.distance_entry.insert(0, "1.0")

        ttk.Label(dist_input_frame, text="Quick Presets:", style="Subtext.TLabel").pack(side="left", padx=(0, 5))

        for d_val in ["0.5", "1.0", "2.0", "3.0", "5.0"]:
            btn = ttk.Button(
                dist_input_frame,
                text=f"{d_val}m",
                style="Pill.TButton",
                command=lambda val=d_val: self.set_preset_distance(val)
            )
            btn.pack(side="left", padx=2)

        # Obstacle Controls
        ttk.Label(exp_box, text="Is there an obstacle?").grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.obstacle_combo = ttk.Combobox(exp_box, values=["No", "Yes"], state="readonly", width=10)
        self.obstacle_combo.set("No")
        self.obstacle_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.obstacle_combo.bind("<<ComboboxSelected>>", self.on_obstacle_change)

        ttk.Label(exp_box, text="Obstacle Type / Material:").grid(row=1, column=2, sticky="w", padx=(20, 5), pady=5)

        obs_type_frame = ttk.Frame(exp_box)
        obs_type_frame.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        self.obstacle_type_combo = ttk.Combobox(
            obs_type_frame,
            values=["None", "Human Body", "Wooden Door", "Concrete Wall", "Glass Window", "Metal Shield", "Custom..."],
            width=18
        )
        self.obstacle_type_combo.set("None")
        self.obstacle_type_combo.pack(side="left")
        self.obstacle_type_combo.config(state="disabled")

        ttk.Label(
            exp_box,
            text="💡 Tip: Accurate distance and obstacle inputs ensure high-quality dataset training.",
            style="Subtext.TLabel"
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(5, 0))


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

        self.status_dot = ttk.Label(status_bar, text="● READY", foreground="#a6e3a1", style="Status.TLabel")
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


    # ========================================================
    # Helper Handlers & Presets
    # ========================================================

    def set_preset_distance(self, value_str):
        if not self.collecting:
            self.distance_entry.delete(0, tk.END)
            self.distance_entry.insert(0, value_str)

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
    # COM Port Enumeration
    # ========================================================

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = []
        esp_index = -1

        for idx, port in enumerate(ports):
            desc = f"{port.device} - {port.description}"
            port_list.append(desc)
            # Auto-detect ESP32 serial bridge chips
            p_desc_lower = port.description.lower()
            if any(k in p_desc_lower for k in ["ch340", "cp210", "ftdi", "uart", "esp32", "usb-serial"]):
                esp_index = idx

        self.port_combo["values"] = port_list

        if port_list:
            if esp_index >= 0:
                self.port_combo.current(esp_index)
            else:
                self.port_combo.current(0)
            self.log("INFO", f"Detected {len(port_list)} available COM port(s).")
        else:
            self.port_combo.set("No COM ports found")
            self.log("WARN", "No COM ports detected. Connect ESP32 via USB and click Refresh.")


    # ========================================================
    # Start Collection Flow
    # ========================================================

    def start_collection(self):

        # 1. Validate Distance
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

        # 2. Validate Port
        selected_port_str = self.port_combo.get()
        if not selected_port_str or "No COM ports" in selected_port_str:
            messagebox.showerror("Connection Error", "Please select a valid ESP32 COM port.")
            return

        port = selected_port_str.split(" - ")[0]

        # 3. Validate Baud Rate
        try:
            baud_rate = int(self.baud_combo.get())
        except ValueError:
            baud_rate = DEFAULT_BAUD_RATE

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

            # Standard Dataset Header
            self.csv_writer.writerow([
                "timestamp",
                "anchor",
                "mac",
                "rssi",
                "name",
                "distance_m",
                "obstacle",
                "obstacle_type"
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
            self.log("SYS", f"Params → Distance: {distance}m | Obstacle: {obstacle} ({obstacle_type}) | Baud: {baud_rate}")

            # Start Reader Worker Thread
            self.reader_thread = threading.Thread(
                target=self.serial_reader,
                args=(distance, obstacle, obstacle_type),
                daemon=True
            )
            self.reader_thread.start()

        except Exception as e:
            messagebox.showerror("Serial Error", f"Failed to connect to {port}:\n{str(e)}")
            self.cleanup()


    # ========================================================
    # Worker Thread: Serial Reader
    # ========================================================

    def serial_reader(self, distance, obstacle, obstacle_type):
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

                timestamp = parts[0]
                anchor = parts[1]
                mac = parts[2]
                rssi = parts[3]
                name = ",".join(parts[4:])

                # Create populated dataset record
                row = [
                    timestamp,
                    anchor,
                    mac,
                    rssi,
                    name,
                    distance,
                    obstacle,
                    obstacle_type
                ]

                self.data_queue.put(row)

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

                if isinstance(item, tuple) and item[0] == "ERROR":
                    self.log("ERROR", f"Serial Thread Exception: {item[1]}")
                    continue

                if self.paused:
                    continue

                row = item

                # Write to CSV
                if self.csv_writer and self.csv_file:
                    self.csv_writer.writerow(row)
                    self.csv_file.flush()

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
            self.status_dot.config(text=f"● COLLECTING | {self.port_combo.get().split(' - ')[0]}", foreground="#a6e3a1")
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
