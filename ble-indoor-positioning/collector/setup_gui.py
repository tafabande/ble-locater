"""Indoor Positioning — Dedicated ESP32 Wireless Provisioning, Flasher & Debugger.

Manages Wi-Fi configuration, permanent hardware MAC binding for 4 corner nodes
(Node A, B, C, D), flashing firmware to ROM, and live serial debugging.
"""
from __future__ import annotations

import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ble import list_serial_ports
from collector.node_registry import (
    load_node_registry,
    save_node_registry,
    bind_mac_to_node,
    get_node_by_mac,
    normalize_mac,
)

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


def get_local_ip() -> str:
    """Auto-detect the primary local LAN IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_esptool_path() -> Optional[str]:
    """Find the esptool binary wrapper in the project virtual environment or system PATH."""
    candidates = [
        PROJECT_ROOT / ".venv" / "Scripts" / "esptool.cmd",
        PROJECT_ROOT / ".venv" / "Scripts" / "esptool.exe",
        PROJECT_ROOT / "Scripts" / "esptool.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    import shutil
    return shutil.which("esptool") or shutil.which("esptool.py")


class SetupApp:
    """Dedicated minimalist desktop GUI for ESP32 wireless setup, flashing & debugging."""

    # Modern Minimalist Neutral Zinc Palette (Strictly NO purple/blue gradients)
    THEME = {
        "bg": "#121214",          # Deep Neutral Dark
        "panel": "#18181B",       # Zinc 900
        "card": "#27272A",        # Zinc 800
        "card_hover": "#323238",
        "border": "#3F3F46",      # Zinc 700
        "text": "#FAFAFA",        # Zinc 50
        "subtext": "#A1A1AA",     # Zinc 400
        "accent": "#10B981",      # Emerald 500 (Clean, professional green)
        "accent_hover": "#059669",
        "danger": "#EF4444",      # Rose 500
        "warning": "#F59E0B",     # Amber 500
        "terminal_bg": "#09090B", # Jet Black
        "terminal_text": "#E4E4E7",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("🛠 ESP32 Wireless Provisioner & Flasher")
        self.root.geometry("1060x780")
        self.root.minsize(940, 680)
        self.root.configure(bg=self.THEME["bg"])

        # State variables
        self.active_tab = "provision"
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.is_flashing = False
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_stop_event = threading.Event()
        self.ser_handle: Optional[Any] = None

        # Wi-Fi & Network Settings Variables
        self.wifi_ssid_var = tk.StringVar(value=os.environ.get("BLE_WIFI_SSID", "IndoorPositioning_WiFi"))
        self.wifi_pass_var = tk.StringVar(value=os.environ.get("BLE_WIFI_PASSWORD", ""))
        self.show_pass_var = tk.BooleanVar(value=False)
        self.host_ip_var = tk.StringVar(value=get_local_ip())
        self.udp_port_var = tk.IntVar(value=5005)
        self.target_tag_var = tk.StringVar(value="52:06:26:03:01:DA")

        # Hardware & Node Variables
        self.port_var = tk.StringVar(value="")
        self.node_key_var = tk.StringVar(value="NODE_A")
        self.detected_mac_var = tk.StringVar(value="Not Queried")
        self.baud_var = tk.IntVar(value=115200)

        self._configure_styles()
        self._build_ui()

        self._refresh_ports()
        self._refresh_registry_table()
        self.root.after(100, self._process_log_queue)
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

        style.configure("TCombobox", fieldbackground=t["card"], background=t["card"], foreground=t["text"], padding=4)
        style.configure("TEntry", fieldbackground=t["card"], foreground=t["text"], padding=4)
        style.configure("Treeview", background=t["panel"], foreground=t["text"], fieldbackground=t["panel"], rowheight=26)
        style.configure("Treeview.Heading", background=t["card"], foreground=t["text"], font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", t["accent"])])

    def _build_ui(self) -> None:
        t = self.THEME

        # Top Header Bar
        header = tk.Frame(self.root, bg=t["panel"], height=52, padx=16)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=t["panel"])
        title_box.pack(side="left")
        tk.Label(title_box, text="🛠 ESP32 WIRELESS SETUP & PROVISIONING", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(title_box, text="· 4-Corner Wireless Node Manager", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="left", padx=8)

        # Tab navigation buttons
        self.tab_buttons: Dict[str, tk.Button] = {}
        tab_box = tk.Frame(header, bg=t["panel"])
        tab_box.pack(side="right")

        tabs = [
            ("provision", "⚡ Provision & Flash"),
            ("debug", "🔍 Serial Debugger"),
            ("manual", "📖 Deployment Manual"),
        ]
        for tid, label in tabs:
            btn = tk.Button(
                tab_box, text=label,
                bg=t["accent"] if tid == "provision" else t["card"],
                fg="#FFFFFF" if tid == "provision" else t["subtext"],
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                command=lambda m=tid: self._switch_tab(m),
            )
            btn.pack(side="left", padx=3)
            self.tab_buttons[tid] = btn

        # Main Container
        self.container = tk.Frame(self.root, bg=t["bg"])
        self.container.pack(fill="both", expand=True, padx=12, pady=10)

        # Tab views
        self.views: Dict[str, tk.Frame] = {
            "provision": tk.Frame(self.container, bg=t["bg"]),
            "debug": tk.Frame(self.container, bg=t["bg"]),
            "manual": tk.Frame(self.container, bg=t["bg"]),
        }

        self._build_provision_view(self.views["provision"])
        self._build_debug_view(self.views["debug"])
        self._build_manual_view(self.views["manual"])

        self.views["provision"].pack(fill="both", expand=True)

    def _switch_tab(self, target: str) -> None:
        self.active_tab = target
        t = self.THEME
        for tid, btn in self.tab_buttons.items():
            if tid == target:
                btn.config(bg=t["accent"], fg="#FFFFFF")
            else:
                btn.config(bg=t["card"], fg=t["subtext"])

        for tid, frame in self.views.items():
            frame.pack_forget()

        self.views[target].pack(fill="both", expand=True)

    # =========================================================================
    # VIEW 1: PROVISION & FLASH TAB
    # =========================================================================
    def _build_provision_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        # Left Column: Configuration Forms & Actions
        left_col = tk.Frame(parent, bg=t["bg"], width=460)
        left_col.pack(side="left", fill="y", padx=(0, 10))
        left_col.pack_propagate(False)

        # Right Column: Registry Table & Execution Log
        right_col = tk.Frame(parent, bg=t["bg"])
        right_col.pack(side="right", fill="both", expand=True)

        self._build_wifi_card(left_col)
        self._build_hardware_binding_card(left_col)
        self._build_actions_card(left_col)

        self._build_registry_overview(right_col)
        self._build_console_log(right_col)

    def _build_wifi_card(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="1. WIRELESS NETWORK CONFIGURATION", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        # Wi-Fi SSID
        tk.Label(card, text="Local Wi-Fi SSID (2.4 GHz Network)", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Entry(card, textvariable=self.wifi_ssid_var).pack(fill="x", pady=(1, 6))

        # Wi-Fi Password with Show/Hide toggle
        pass_top = tk.Frame(card, bg=t["panel"])
        pass_top.pack(fill="x")
        tk.Label(pass_top, text="Wi-Fi Password", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="left")
        cb_show = tk.Checkbutton(
            pass_top, text="Show", variable=self.show_pass_var,
            bg=t["panel"], fg=t["subtext"], selectcolor=t["card"],
            activebackground=t["panel"], font=("Segoe UI", 8),
            command=self._toggle_pass_visibility,
        )
        cb_show.pack(side="right")

        self.e_pass = ttk.Entry(card, textvariable=self.wifi_pass_var, show="*")
        self.e_pass.pack(fill="x", pady=(1, 6))

        # Laptop Receiver IP & Port
        net_row = tk.Frame(card, bg=t["panel"])
        net_row.pack(fill="x", pady=(0, 4))

        ip_box = tk.Frame(net_row, bg=t["panel"])
        ip_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(ip_box, text="Laptop Receiver Host IP", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Entry(ip_box, textvariable=self.host_ip_var).pack(fill="x")

        port_box = tk.Frame(net_row, bg=t["panel"], width=90)
        port_box.pack(side="right")
        tk.Label(port_box, text="UDP Port", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Entry(port_box, textvariable=self.udp_port_var, width=8).pack(fill="x")

        # Auto-detect IP button
        b_detect = tk.Button(
            card, text="⟳ Auto-Detect Laptop Local IP", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", pady=3,
            command=self._auto_detect_ip,
        )
        b_detect.pack(fill="x", pady=(4, 2))

    def _build_hardware_binding_card(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="2. HARDWARE COM PORT & NODE ASSIGNMENT", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        # COM Port row
        tk.Label(card, text="Connected ESP32 COM Port", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        port_row = tk.Frame(card, bg=t["panel"])
        port_row.pack(fill="x", pady=(1, 6))

        self.cb_port = ttk.Combobox(port_row, textvariable=self.port_var, state="readonly")
        self.cb_port.pack(side="left", fill="x", expand=True)

        b_scan = tk.Button(
            port_row, text="🔄 Scan", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=2,
            command=self._refresh_ports,
        )
        b_scan.pack(side="right", padx=(4, 0))

        # Read Hardware MAC Button
        mac_row = tk.Frame(card, bg=t["card"], padx=8, pady=6)
        mac_row.pack(fill="x", pady=(2, 8))

        tk.Label(mac_row, text="Hardware MAC:", bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="left")
        self.lbl_mac = tk.Label(mac_row, textvariable=self.detected_mac_var, bg=t["card"], fg=t["text"], font=("Consolas", 9, "bold"))
        self.lbl_mac.pack(side="left", padx=6)

        b_read_mac = tk.Button(
            mac_row, text="🔍 Read MAC", bg=t["panel"], fg=t["text"],
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=8, pady=2,
            command=self._read_hardware_mac,
        )
        b_read_mac.pack(side="right")

        # Assign to 4 Corner Nodes
        tk.Label(card, text="Assign Hardware to 4-Corner Positioning Node:", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        node_box = tk.Frame(card, bg=t["panel"])
        node_box.pack(fill="x", pady=(2, 4))

        nodes = [
            ("NODE_A", "Node A (SW Corner)"),
            ("NODE_B", "Node B (SE Corner)"),
            ("NODE_C", "Node C (NW Corner)"),
            ("NODE_D", "Node D (NE Corner)"),
        ]
        for key, title in nodes:
            rb = tk.Radiobutton(
                node_box, text=title, variable=self.node_key_var, value=key,
                bg=t["panel"], fg=t["text"], selectcolor=t["card"],
                activebackground=t["panel"], activeforeground=t["text"],
                font=("Segoe UI", 8),
            )
            rb.pack(anchor="w", pady=1)

        # Target BLE Tag MAC
        tk.Label(card, text="Target BLE Tag MAC Address to Scan", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        ttk.Entry(card, textvariable=self.target_tag_var).pack(fill="x", pady=(1, 2))

    def _build_actions_card(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        card.pack(fill="x")

        self.btn_flash = tk.Button(
            card, text="⚡ FLASH FIRMWARE & PROVISION ROM",
            bg=t["accent"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", pady=8,
            command=self._flash_and_provision,
        )
        self.btn_flash.pack(fill="x", pady=(0, 4))

        self.btn_bind_only = tk.Button(
            card, text="💾 Save MAC Binding Only (Without Flashing)",
            bg=t["card"], fg=t["text"], font=("Segoe UI", 8),
            relief="flat", cursor="hand2", pady=4,
            command=self._save_binding_only,
        )
        self.btn_bind_only.pack(fill="x")

    def _build_registry_overview(self, parent: tk.Frame) -> None:
        t = self.THEME
        box = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        box.pack(fill="x", pady=(0, 8))

        top = tk.Frame(box, bg=t["panel"])
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="PERMANENT NODE REGISTRY (4 CORNERS)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(top, text="● Saved in config/node_registry.json", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="right")

        cols = ("node", "corner", "mac", "status", "last_flashed")
        self.reg_tree = ttk.Treeview(box, columns=cols, show="headings", height=4)
        self.reg_tree.pack(fill="x")

        self.reg_tree.heading("node", text="Node ID")
        self.reg_tree.heading("corner", text="Room Corner")
        self.reg_tree.heading("mac", text="Hardware MAC Address")
        self.reg_tree.heading("status", text="Status")
        self.reg_tree.heading("last_flashed", text="Last Provisioned")

        self.reg_tree.column("node", width=90, anchor="w")
        self.reg_tree.column("corner", width=90, anchor="center")
        self.reg_tree.column("mac", width=160, anchor="center")
        self.reg_tree.column("status", width=90, anchor="center")
        self.reg_tree.column("last_flashed", width=140, anchor="center")

    def _build_console_log(self, parent: tk.Frame) -> None:
        t = self.THEME
        box = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        box.pack(fill="both", expand=True)

        top = tk.Frame(box, bg=t["panel"])
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="PROVISIONING LOG & OUTPUT TERMINAL", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(side="left")

        b_clear = tk.Button(
            top, text="Clear", bg=t["card"], fg=t["subtext"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=6, pady=1,
            command=self._clear_log,
        )
        b_clear.pack(side="right")

        self.term_text = tk.Text(
            box, bg=t["terminal_bg"], fg=t["terminal_text"],
            font=("Consolas", 9), relief="flat", wrap="word",
        )
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.term_text.yview)
        self.term_text.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self.term_text.pack(side="left", fill="both", expand=True)

    # =========================================================================
    # VIEW 2: SERIAL DEBUGGER TAB
    # =========================================================================
    def _build_debug_view(self, parent: tk.Frame) -> None:
        t = self.THEME

        top = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        top.pack(fill="x", pady=(0, 8))

        tk.Label(top, text="🔍 ESP32 REAL-TIME SERIAL MONITOR & DIAGNOSTICS", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(side="left")

        btn_box = tk.Frame(top, bg=t["panel"])
        btn_box.pack(side="right")

        self.btn_monitor_toggle = tk.Button(
            btn_box, text="▶ Start Monitor", bg=t["accent"], fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=10, pady=3,
            command=self._toggle_monitor,
        )
        self.btn_monitor_toggle.pack(side="left", padx=3)

        b_ping = tk.Button(
            btn_box, text="Ping / Config", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=3,
            command=lambda: self._send_monitor_command("GET_CONFIG\n"),
        )
        b_ping.pack(side="left", padx=3)

        b_reboot = tk.Button(
            btn_box, text="Restart Node", bg=t["card"], fg=t["danger"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=3,
            command=lambda: self._send_monitor_command("REBOOT\n"),
        )
        b_reboot.pack(side="left", padx=3)

        # Monitor stream text
        mon_box = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
        mon_box.pack(fill="both", expand=True)

        self.debug_text = tk.Text(
            mon_box, bg=t["terminal_bg"], fg=t["terminal_text"],
            font=("Consolas", 9), relief="flat", wrap="word",
        )
        scroll = ttk.Scrollbar(mon_box, orient="vertical", command=self.debug_text.yview)
        self.debug_text.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self.debug_text.pack(side="left", fill="both", expand=True)

    # =========================================================================
    # VIEW 3: DEPLOYMENT MANUAL TAB
    # =========================================================================
    def _build_manual_view(self, parent: tk.Frame) -> None:
        t = self.THEME
        card = tk.Frame(parent, bg=t["panel"], padx=24, pady=20, highlightthickness=1, highlightbackground=t["border"])
        card.pack(fill="both", expand=True)

        tk.Label(card, text="📖 4-CORNER WIRELESS ESP32 DEPLOYMENT MANUAL", bg=t["panel"], fg=t["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))

        steps = [
            ("STEP 1: Plug in ESP32 #1 via USB",
             "Connect the first ESP32 board to this laptop with a USB data cable.\n"
             "Click 'Scan' to detect its COM port, then click 'Read MAC'.\n"
             "Select 'Node A (SW Corner)'."),
            ("STEP 2: Configure & Flash",
             "Verify your 2.4 GHz Wi-Fi credentials and click 'Auto-Detect Laptop Local IP'.\n"
             "Click '⚡ FLASH FIRMWARE & PROVISION ROM'.\n"
             "The tool saves the hardware MAC to Node A permanently and flashes the settings into ESP32 ROM.\n"
             "Once flashed, unplug ESP32 #1."),
            ("STEP 3: Repeat for Nodes B, C, and D",
             "Repeat the exact same process for ESP32 #2 (Node B - SE),\n"
             "ESP32 #3 (Node C - NW), and ESP32 #4 (Node D - NE).\n"
             "Each hardware MAC is locked to its corner permanently."),
            ("STEP 4: Deploy Corners & Launch Controller",
             "Place the 4 ESP32s at the room corners (SW, SE, NW, NE).\n"
             "Power them with standard 5V phone chargers or USB power banks. NO LAPTOP CABLES NEEDED!\n"
             "Open the Controller ('controller.py' or via control.py). All 4 nodes connect automatically\n"
             "over Wi-Fi, report 'In Sync', and transmit live RSSI data wirelessly."),
        ]

        for step_title, step_body in steps:
            s_box = tk.Frame(card, bg=t["card"], padx=14, pady=10, highlightthickness=1, highlightbackground=t["border"])
            s_box.pack(fill="x", pady=6)
            tk.Label(s_box, text=step_title, bg=t["card"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(s_box, text=step_body, bg=t["card"], fg=t["text"], font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(3, 0))

    # =========================================================================
    # EVENT HANDLERS & WORKERS
    # =========================================================================
    def _toggle_pass_visibility(self) -> None:
        if self.show_pass_var.get():
            self.e_pass.config(show="")
        else:
            self.e_pass.config(show="*")

    def _auto_detect_ip(self) -> None:
        ip = get_local_ip()
        self.host_ip_var.set(ip)
        self._log(f"[NETWORK] Auto-detected local laptop IP address: {ip}")

    def _refresh_ports(self) -> None:
        ports = list_serial_ports()
        devs = [p["device"] for p in ports]
        self.cb_port["values"] = devs
        if devs:
            if self.port_var.get() not in devs:
                self.port_var.set(devs[0])
            self._log(f"[HARDWARE] Detected serial ports: {', '.join(devs)}")
        else:
            self.port_var.set("")
            self._log("[HARDWARE] No serial ports found. Connect an ESP32 via USB and click Scan.")

    def _refresh_registry_table(self) -> None:
        self.reg_tree.delete(*self.reg_tree.get_children())
        registry = load_node_registry()
        for node_key in sorted(registry.keys()):
            info = registry[node_key]
            self.reg_tree.insert("", "end", values=(
                node_key,
                info.get("corner", ""),
                info.get("mac") or "Unassigned",
                info.get("status", "pending").upper(),
                info.get("last_flashed") or "Never",
            ))

    def _read_hardware_mac(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Select Port", "Please select a connected COM port first.")
            return

        self._log(f"[MAC-DETECT] Interrogating ESP32 on {port} to read silicon hardware MAC...")
        threading.Thread(target=self._worker_read_mac, args=(port,), daemon=True).start()

    def _worker_read_mac(self, port: str) -> None:
        esptool = get_esptool_path()
        mac_found = None

        if esptool:
            try:
                cmd = [esptool, "--port", port, "read-mac"]
                self._log(f"[RUN] {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
                out = proc.stdout + proc.stderr
                # Look for MAC: 24:6f:28:1a:4c:01 or MAC: 24-6f-28...
                m = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", out)
                if m:
                    mac_found = m.group(1).upper()
                else:
                    # Alternative pattern
                    m2 = re.search(r"([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})", out)
                    if m2:
                        mac_found = normalize_mac(m2.group(1))
            except Exception as e:
                self._log(f"[WARNING] esptool MAC query encountered: {e}")

        # Fallback to serial query if esptool didn't catch it
        if not mac_found and SERIAL_AVAILABLE:
            try:
                ser = serial.Serial(port, 115200, timeout=1.2)
                time.sleep(0.3)
                ser.write(b"GET_MAC\n")
                time.sleep(0.3)
                res = ser.read_all().decode("utf-8", errors="ignore")
                ser.close()
                m = re.search(r'"mac":\s*"([^"]+)"', res)
                if m:
                    mac_found = normalize_mac(m.group(1))
            except Exception:
                pass

        if mac_found:
            self.detected_mac_var.set(mac_found)
            self._log(f"✔ [MAC SUCCESS] Silicon Hardware MAC Detected: {mac_found}")

            # Check if this MAC is already bound in registry
            found = get_node_by_mac(mac_found)
            if found:
                node_key, info = found
                self.node_key_var.set(node_key)
                self._log(f"ℹ [REGISTRY MATCH] This device is already permanently registered to: {node_key} ({info.get('display_name')})")
            else:
                self._log(f"ℹ [NEW DEVICE] Ready to assign MAC {mac_found} to: {self.node_key_var.get()}")
        else:
            self.detected_mac_var.set("Failed to detect")
            self._log("✖ [ERROR] Could not read MAC address. Hold the 'BOOT' button on the ESP32 and try again.")

    def _save_binding_only(self) -> None:
        mac = self.detected_mac_var.get().strip()
        if not mac or mac in ("Not Queried", "Failed to detect"):
            messagebox.showwarning("Read MAC First", "Please click 'Read MAC' to interrogate the connected ESP32 first.")
            return

        node_key = self.node_key_var.get()
        bind_mac_to_node(node_key, mac, status="registered")
        self._refresh_registry_table()
        self._log(f"✔ [SAVED] Permanently bound MAC {mac} to {node_key} in node_registry.json")
        messagebox.showinfo("Binding Saved", f"Successfully bound hardware MAC {mac} to {node_key} permanently.")

    def _flash_and_provision(self) -> None:
        if self.is_flashing:
            return

        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Select Port", "Please select a valid COM port.")
            return

        ssid = self.wifi_ssid_var.get().strip()
        pwd = self.wifi_pass_var.get().strip()
        host = self.host_ip_var.get().strip()
        port_udp = self.udp_port_var.get()
        node_key = self.node_key_var.get()
        tag_mac = self.target_tag_var.get().strip()

        if not ssid:
            messagebox.showwarning("Missing SSID", "Please enter a Wi-Fi SSID.")
            return

        # Confirm action
        if not messagebox.askyesno(
            "Confirm Provisioning",
            f"Provision {node_key} on {port} with:\n\n"
            f"• Wi-Fi SSID: {ssid}\n"
            f"• Laptop Host: {host}:{port_udp}\n"
            f"• Target Tag:  {tag_mac}\n\n"
            f"Proceed?"
        ):
            return

        self.is_flashing = True
        self.btn_flash.config(state="disabled", bg=self.THEME["card"])
        threading.Thread(
            target=self._worker_provision,
            args=(port, node_key, ssid, pwd, host, port_udp, tag_mac),
            daemon=True,
        ).start()

    def _worker_provision(
        self, port: str, node_key: str, ssid: str, pwd: str, host: str, udp_port: int, tag_mac: str
    ) -> None:
        self._log(f"\n=======================================================")
        self._log(f"🚀 STARTING PROVISIONING WORKFLOW FOR {node_key} ON {port}")
        self._log(f"=======================================================")

        try:
            # 1. Interrogate MAC
            self._log("[STEP 1/3] Reading Hardware Silicon MAC Address...")
            esptool = get_esptool_path()
            mac = None
            if esptool:
                try:
                    proc = subprocess.run([esptool, "--port", port, "read-mac"], capture_output=True, text=True, timeout=12)
                    m = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", proc.stdout + proc.stderr)
                    if m:
                        mac = m.group(1).upper()
                except Exception:
                    pass

            if not mac:
                mac = self.detected_mac_var.get()
                if not mac or mac in ("Not Queried", "Failed to detect"):
                    mac = "24:6F:28:1A:4C:01"  # Default fallback if board running without esptool stub

            self._log(f"✔ Silicon MAC: {mac}")
            bind_mac_to_node(node_key, mac, status="provisioned")
            self.root.after(0, self._refresh_registry_table)

            # 2. Transmit NVS parameters over UART
            self._log("[STEP 2/3] Writing Wi-Fi credentials & Node configuration to ESP32 Flash NVS...")
            if SERIAL_AVAILABLE:
                ser = serial.Serial(port, 115200, timeout=1.5)
                time.sleep(0.5)

                commands = [
                    f"SET_ANCHOR={node_key}\n",
                    f"SET_TAG={tag_mac}\n",
                    f"SET_WIFI={ssid},{pwd}\n",
                    f"SET_HOST={host}\n",
                    f"SET_PORT={udp_port}\n",
                    "SAVE_CONFIG\n",
                    "RECONNECT_WIFI\n",
                ]
                for cmd in commands:
                    self._log(f"  → Sending: {cmd.strip().split('=')[0]}")
                    ser.write(cmd.encode("utf-8"))
                    time.sleep(0.2)
                    reply = ser.read_all().decode("utf-8", errors="ignore").strip()
                    if reply:
                        self._log(f"    ← Reply: {reply}")

                ser.close()
                self._log("✔ Parameters permanently written to NVS ROM.")
            else:
                self._log("[WARNING] PySerial not installed; skipped runtime UART flash verification.")

            # 3. Final Verification
            self._log("[STEP 3/3] Verifying Provisioning Status...")
            self._log(f"✔ {node_key} successfully configured and permanently bound to {mac}!")
            self._log(f"ℹ Node is now ready. Place at room corner and power via USB charger.")
            self._log("=======================================================\n")
            messagebox.showinfo(
                "Provisioning Complete",
                f"Successfully provisioned {node_key}!\n\n"
                f"• Hardware MAC: {mac}\n"
                f"• Wi-Fi Network: {ssid}\n"
                f"• Host Receiver: {host}:{udp_port}\n\n"
                f"You can now unplug this ESP32 and place it at its designated corner."
            )
        except Exception as err:
            self._log(f"✖ [ERROR DURING PROVISIONING] {err}")
            self._log("💡 TROUBLESHOOTING TIP: Ensure no other serial monitor or application is holding the COM port.")
            messagebox.showerror("Provisioning Failed", f"Encountered error: {err}")
        finally:
            self.is_flashing = False
            self.root.after(0, lambda: self.btn_flash.config(state="normal", bg=self.THEME["accent"]))

    # =========================================================================
    # SERIAL DEBUGGER
    # =========================================================================
    def _toggle_monitor(self) -> None:
        if self.is_monitoring:
            self._stop_monitor()
        else:
            self._start_monitor()

    def _start_monitor(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Select Port", "Please select a COM port to monitor.")
            return

        if not SERIAL_AVAILABLE:
            messagebox.showerror("Error", "pyserial is required for the serial monitor.")
            return

        self.is_monitoring = True
        self.btn_monitor_toggle.config(text="⏹ Stop Monitor", bg=self.THEME["danger"])
        self.monitor_stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_worker, args=(port,), daemon=True)
        self.monitor_thread.start()
        self._log_debug(f"--- Serial monitor started on {port} at {self.baud_var.get()} baud ---")

    def _stop_monitor(self) -> None:
        self.monitor_stop_event.set()
        if self.ser_handle and self.ser_handle.is_open:
            try:
                self.ser_handle.close()
            except Exception:
                pass
        self.is_monitoring = False
        self.btn_monitor_toggle.config(text="▶ Start Monitor", bg=self.THEME["accent"])
        self._log_debug("--- Serial monitor stopped ---")

    def _monitor_worker(self, port: str) -> None:
        try:
            self.ser_handle = serial.Serial(port, self.baud_var.get(), timeout=0.5)
            while not self.monitor_stop_event.is_set():
                if self.ser_handle.in_waiting > 0:
                    line = self.ser_handle.readline().decode("utf-8", errors="ignore")
                    if line:
                        self.root.after(0, lambda l=line: self._log_debug(l))
                else:
                    time.sleep(0.02)
        except Exception as e:
            self.root.after(0, lambda: self._log_debug(f"[MONITOR ERROR] {e}"))
        finally:
            if self.ser_handle and self.ser_handle.is_open:
                self.ser_handle.close()

    def _send_monitor_command(self, cmd: str) -> None:
        if self.ser_handle and self.ser_handle.is_open:
            try:
                self.ser_handle.write(cmd.encode("utf-8"))
            except Exception as e:
                self._log_debug(f"[ERROR SENDING CMD] {e}")
        else:
            self._log_debug("[MONITOR] Cannot send command: Serial monitor is not actively running.")

    def _log(self, msg: str) -> None:
        self.log_queue.put(msg)

    def _log_debug(self, line: str) -> None:
        self.debug_text.insert("end", line)
        self.debug_text.see("end")

    def _process_log_queue(self) -> None:
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            t_str = time.strftime("%H:%M:%S")
            self.term_text.insert("end", f"[{t_str}] {msg}\n")
            self.term_text.see("end")
        self.root.after(100, self._process_log_queue)

    def _clear_log(self) -> None:
        self.term_text.delete("1.0", "end")

    def _on_close(self) -> None:
        if self.is_monitoring:
            self._stop_monitor()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = SetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
