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
from core.config import (
    get_active_lan_interfaces,
    get_experiment_receiver_ip,
    get_hotspot_lan_interfaces,
)
from collector.node_registry import (
    load_node_registry,
    save_node_registry,
    bind_mac_to_node,
    get_node_by_mac,
    normalize_mac,
    is_node_locked,
    lock_node,
    unlock_node,
    set_node_lock,
)

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


def get_local_ip() -> str:
    """Return the dedicated hotspot receiver IP, never the Internet-facing NIC."""
    return get_experiment_receiver_ip()


def verify_esp32_config(
    config: Dict[str, Any], *, mac: str, node_key: str, tag_mac: str, host: str, udp_port: int
) -> bool:
    """Return True only when the ESP32 read-back matches every provisioned field."""
    return (
        normalize_mac(str(config.get("mac", ""))) == normalize_mac(mac)
        and str(config.get("node", "")).upper() == node_key.upper()
        and normalize_mac(str(config.get("tag", ""))) == normalize_mac(tag_mac)
        and str(config.get("ssid", "")) != ""
        and str(config.get("host", "")) == host
        and int(config.get("port", -1)) == int(udp_port)
    )


def get_firmware_binaries() -> Dict[str, Optional[Path]]:
    """Locate real compiled ESP-IDF firmware binaries for esp32_wifi_anchor."""
    bin_dir = PROJECT_ROOT / "firmware" / "binaries"
    build_dir = PROJECT_ROOT / "firmware" / "esp32_wifi_anchor" / "build"
    anchor_build = PROJECT_ROOT / "firmware" / "esp32_anchor" / "build"

    app_bin = None
    bootloader_bin = None
    partitions_bin = None

    for cand in [
        bin_dir / "esp32_wifi_anchor.bin",
        build_dir / "esp32_wifi_anchor.bin",
        bin_dir / "ble.bin",
        anchor_build / "ble.bin",
    ]:
        if cand.exists():
            app_bin = cand
            break

    for cand in [
        bin_dir / "bootloader.bin",
        build_dir / "bootloader" / "bootloader.bin",
        anchor_build / "bootloader" / "bootloader.bin",
    ]:
        if cand.exists():
            bootloader_bin = cand
            break

    for cand in [
        bin_dir / "partition-table.bin",
        build_dir / "partition_table" / "partition-table.bin",
        anchor_build / "partition_table" / "partition-table.bin",
        bin_dir / "partitions.bin",
    ]:
        if cand.exists():
            partitions_bin = cand
            break

    return {
        "app": app_bin,
        "bootloader": bootloader_bin,
        "partitions": partitions_bin,
    }


def build_esp_idf_firmware(log_cb=None) -> bool:
    """Build esp32_wifi_anchor firmware project using the local ESP-IDF toolchain."""
    ps_profile = Path(r"C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1")
    project_dir = PROJECT_ROOT / "firmware" / "esp32_wifi_anchor"
    if not project_dir.exists():
        project_dir = PROJECT_ROOT / "firmware" / "esp32_anchor"

    if log_cb:
        log_cb("[BUILD] Initializing ESP-IDF compilation for esp32_wifi_anchor...")

    if ps_profile.exists():
        ps_cmd = f'. "{ps_profile}"; cd "{project_dir}"; idf.py build'
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
    else:
        cmd = ["idf.py", "-C", str(project_dir), "build"]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(PROJECT_ROOT),
        )
        for line in proc.stdout:
            line_str = line.strip()
            if line_str and log_cb:
                log_cb(f"  [IDF] {line_str}")
        proc.wait()
        if proc.returncode == 0:
            import shutil
            bin_dir = PROJECT_ROOT / "firmware" / "binaries"
            bin_dir.mkdir(parents=True, exist_ok=True)
            b_dir = project_dir / "build"
            app_b = b_dir / "esp32_wifi_anchor.bin"
            boot_b = b_dir / "bootloader" / "bootloader.bin"
            part_b = b_dir / "partition_table" / "partition-table.bin"
            if app_b.exists():
                shutil.copy2(app_b, bin_dir / "esp32_wifi_anchor.bin")
            if boot_b.exists():
                shutil.copy2(boot_b, bin_dir / "bootloader.bin")
            if part_b.exists():
                shutil.copy2(part_b, bin_dir / "partition-table.bin")
            if log_cb:
                log_cb("✔ [BUILD SUCCESS] Real ESP-IDF binaries compiled and placed in firmware/binaries!")
            return True
        else:
            if log_cb:
                log_cb(f"✖ [BUILD ERROR] idf.py build exited with code {proc.returncode}")
            return False
    except Exception as e:
        if log_cb:
            log_cb(f"✖ [BUILD EXCEPTION] {e}")
        return False


def get_esptool_cmd() -> Optional[List[str]]:
    """Find the esptool execution command wrapper in venv, python module, or system PATH."""
    # 1. Try python -m esptool using current python interpreter
    try:
        res = subprocess.run([sys.executable, "-m", "esptool", "version"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            return [sys.executable, "-m", "esptool"]
    except Exception:
        pass

    # 2. Check binary paths
    candidates = [
        PROJECT_ROOT / ".venv" / "Scripts" / "esptool.exe",
        PROJECT_ROOT / ".venv" / "Scripts" / "esptool.cmd",
        Path(r"C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\esptool.exe"),
        PROJECT_ROOT / "Scripts" / "esptool.exe",
    ]
    for c in candidates:
        if c.exists():
            return [str(c)]

    import shutil
    found = shutil.which("esptool") or shutil.which("esptool.py")
    if found:
        return [found]
    return None



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
        self.hotspot_status_var = tk.StringVar()
        # UDP port 5005 is owned exclusively by the Collector (recording.py).
        # The Setup tool uses serial-only for provisioning and HTTP for health checks.
        self.target_tag_var = tk.StringVar(value="52:06:26:03:01:DA")

        # Hardware & Node Variables
        self.port_var = tk.StringVar(value="")
        self.node_key_var = tk.StringVar(value="NODE_A")
        self.detected_mac_var = tk.StringVar(value="Not Queried")
        self.baud_var = tk.IntVar(value=115200)

        # Real-Time Node Health Tracker for all 4 Corner Nodes
        self.node_health_tracker: Dict[str, Dict[str, Any]] = {
            "NODE_A": {"online": False, "last_seen": 0.0, "packets": 0, "ip": "", "rssi": -99},
            "NODE_B": {"online": False, "last_seen": 0.0, "packets": 0, "ip": "", "rssi": -99},
            "NODE_C": {"online": False, "last_seen": 0.0, "packets": 0, "ip": "", "rssi": -99},
            "NODE_D": {"online": False, "last_seen": 0.0, "packets": 0, "ip": "", "rssi": -99},
        }
        # Health monitoring is HTTP-only (polls FastAPI backend at /api/nodes/health).
        # No UDP listener thread — the Collector owns port 5005 exclusively.

        self._configure_styles()
        self._build_ui()

        self._refresh_ports()
        self._refresh_registry_table()
        self.root.after(100, self._process_log_queue)
        self.root.after(3000, self._periodic_health_refresh)
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

        # Network Interface & Laptop Receiver IP & Port.  The hotspot is the
        # experimental LAN, so it is deliberately listed before Internet NICs.
        hotspot_ifaces = get_hotspot_lan_interfaces()
        all_ifaces = get_active_lan_interfaces()
        net_ifaces = hotspot_ifaces + [item for item in all_ifaces if item not in hotspot_ifaces]
        self.net_adapters = net_ifaces
        self.adapter_names = [f"{name} ({ip})" for name, ip in net_ifaces]
        self.adapter_var = tk.StringVar(value=self.adapter_names[0] if self.adapter_names else "")

        tk.Label(card, text="Laptop Network Interface Adapter", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        self.cb_adapter = ttk.Combobox(card, textvariable=self.adapter_var, values=self.adapter_names, state="readonly")
        self.cb_adapter.pack(fill="x", pady=(1, 4))
        self.cb_adapter.bind("<<ComboboxSelected>>", self._on_adapter_selected)

        if hotspot_ifaces:
            self.hotspot_status_var.set(
                f"Experimental hotspot detected: {hotspot_ifaces[0][0]} ({hotspot_ifaces[0][1]})"
            )
            hotspot_fg = t["accent"]
        else:
            self.hotspot_status_var.set(
                "Laptop hotspot not detected — enable Mobile Hotspot before provisioning"
            )
            hotspot_fg = t["warning"]
        tk.Label(card, textvariable=self.hotspot_status_var, bg=t["panel"], fg=hotspot_fg,
                 font=("Segoe UI", 8, "bold"), wraplength=360, justify="left").pack(anchor="w", pady=(0, 5))

        net_row = tk.Frame(card, bg=t["panel"])
        net_row.pack(fill="x", pady=(0, 4))

        ip_box = tk.Frame(net_row, bg=t["panel"])
        ip_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(ip_box, text="Laptop Receiver Host IP", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Entry(ip_box, textvariable=self.host_ip_var).pack(fill="x")

        port_box = tk.Frame(net_row, bg=t["panel"], width=90)
        port_box.pack(side="right")
        tk.Label(port_box, text="UDP Port", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(port_box, text="5005", bg=t["card"], fg=t["text"], font=("Consolas", 9), anchor="w", padx=4).pack(fill="x")

        # Auto-detect IP button
        b_detect = tk.Button(
            card, text="⟳ Refresh & Auto-Detect Wi-Fi / LAN IP", bg=t["card"], fg=t["text"],
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

        self.btn_quick_config = tk.Button(
            card, text="📶 PUSH WI-FI / NVS CONFIG (QUICK OVER SERIAL — NO FLASH)",
            bg="#2563EB", fg="#FFFFFF", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", pady=7,
            command=self._quick_update_wifi,
        )
        self.btn_quick_config.pack(fill="x", pady=(0, 4))

        self.btn_flash = tk.Button(
            card, text="⚡ FLASH FIRMWARE & PROVISION ROM",
            bg=t["accent"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", pady=8,
            command=self._flash_and_provision,
        )
        self.btn_flash.pack(fill="x", pady=(0, 4))

        self.btn_compile = tk.Button(
            card, text="🔨 Compile Firmware (ESP-IDF v6.1)",
            bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", pady=4,
            command=self._compile_firmware_idf,
        )
        self.btn_compile.pack(fill="x", pady=(0, 4))

        self.btn_bind_only = tk.Button(
            card, text="💾 Save MAC Binding Only (Without Flashing)",
            bg=t["card"], fg=t["subtext"], font=("Segoe UI", 8),
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

        cols = ("node", "corner", "mac", "lock", "status", "last_flashed")
        self.reg_tree = ttk.Treeview(box, columns=cols, show="headings", height=4)
        self.reg_tree.pack(fill="x")

        self.reg_tree.heading("node", text="Node ID")
        self.reg_tree.heading("corner", text="Room Corner")
        self.reg_tree.heading("mac", text="Hardware MAC Address")
        self.reg_tree.heading("lock", text="Lock State")
        self.reg_tree.heading("status", text="Health Status")
        self.reg_tree.heading("last_flashed", text="Last Provisioned")

        self.reg_tree.column("node", width=75, anchor="w")
        self.reg_tree.column("corner", width=80, anchor="center")
        self.reg_tree.column("mac", width=145, anchor="center")
        self.reg_tree.column("lock", width=105, anchor="center")
        self.reg_tree.column("status", width=160, anchor="w")
        self.reg_tree.column("last_flashed", width=130, anchor="center")
        self.reg_tree.bind("<<TreeviewSelect>>", self._on_reg_tree_select)

        # Action buttons for MAC Locking and Real-Time Node Health Verification
        btn_row = tk.Frame(box, bg=t["panel"])
        btn_row.pack(fill="x", pady=(8, 0))

        tk.Button(
            btn_row, text="🔒 Lock Selected Node", bg=t["card"], fg=t["text"],
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=10, pady=3,
            command=self._lock_selected_node,
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            btn_row, text="🔓 Unlock Selected Node", bg=t["card"], fg=t["subtext"],
            font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=10, pady=3,
            command=self._unlock_selected_node,
        ).pack(side="left", padx=4)

        tk.Button(
            btn_row, text="🩺 Ping & Verify Health", bg=t["card"], fg=t["accent"],
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=10, pady=3,
            command=self._ping_nodes_health,
        ).pack(side="right")

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

    def _on_adapter_selected(self, event=None) -> None:
        sel = self.adapter_var.get()
        for name, ip in getattr(self, "net_adapters", []):
            if f"{name} ({ip})" == sel:
                self.host_ip_var.set(ip)
                self._log(f"[NETWORK] Selected adapter '{name}' with IP: {ip}")
                break

    def _auto_detect_ip(self) -> None:
        hotspot_ifaces = get_hotspot_lan_interfaces()
        all_ifaces = get_active_lan_interfaces()
        net_ifaces = hotspot_ifaces + [item for item in all_ifaces if item not in hotspot_ifaces]
        self.net_adapters = net_ifaces
        self.adapter_names = [f"{name} ({ip})" for name, ip in net_ifaces]
        if hasattr(self, "cb_adapter"):
            self.cb_adapter["values"] = self.adapter_names
            if hotspot_ifaces:
                self.adapter_var.set(self.adapter_names[0])
        ip = get_experiment_receiver_ip()
        self.host_ip_var.set(ip)
        if hotspot_ifaces:
            self.hotspot_status_var.set(
                f"Experimental hotspot detected: {hotspot_ifaces[0][0]} ({ip})"
            )
            self._log(f"[NETWORK] Experimental hotspot receiver detected: {ip}")
        else:
            self.hotspot_status_var.set(
                "Laptop hotspot not detected — enable Mobile Hotspot before provisioning"
            )
            self._log("[NETWORK] No active Mobile Hotspot adapter detected; receiver IP intentionally left blank.")

    def _compile_firmware_idf(self) -> None:
        if getattr(self, "is_compiling", False):
            return
        self.is_compiling = True
        self.btn_compile.config(state="disabled", text="⏳ Compiling (ESP-IDF)...")
        threading.Thread(target=self._worker_compile_firmware, daemon=True).start()

    def _worker_compile_firmware(self) -> None:
        self._log("\n=======================================================")
        self._log("🔨 INITIATING ESP-IDF v6.1 FIRMWARE COMPILATION")
        self._log("=======================================================")
        success = build_esp_idf_firmware(log_cb=self._log)
        self.is_compiling = False
        def _finish():
            self.btn_compile.config(state="normal", text="🔨 Compile Firmware (ESP-IDF v6.1)")
            if success:
                messagebox.showinfo("Build Success", "ESP-IDF firmware successfully compiled and copied to firmware/binaries!")
            else:
                messagebox.showerror("Build Failed", "ESP-IDF compilation failed. Check the terminal log for compiler output.")
        self.root.after(0, _finish)

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

    def _on_reg_tree_select(self, event=None) -> None:
        sel = self.reg_tree.selection()
        if sel:
            item = self.reg_tree.item(sel[0])
            vals = item.get("values", [])
            if vals:
                node_key = str(vals[0])
                self.node_key_var.set(node_key)

    def _lock_selected_node(self) -> None:
        node_key = self.node_key_var.get()
        reg = load_node_registry()
        curr_mac = reg.get(node_key, {}).get("mac", "")
        if not curr_mac or curr_mac == "Unassigned":
            messagebox.showwarning("No MAC Bound", f"Cannot lock {node_key} because it does not have a valid MAC address assigned yet.")
            return
        lock_node(node_key)
        self._refresh_registry_table()
        self._log(f"🔒 [LOCKED] {node_key} is now LOCKED to hardware MAC {curr_mac}. It cannot be reassigned or replaced unless unlocked.")
        messagebox.showinfo("Node Locked", f"✔ {node_key} is now LOCKED to MAC:\n{curr_mac}\n\nThis MAC cannot be assigned to any other node, and {node_key} cannot be replaced with another MAC.")

    def _unlock_selected_node(self) -> None:
        node_key = self.node_key_var.get()
        unlock_node(node_key)
        self._refresh_registry_table()
        self._log(f"🔓 [UNLOCKED] {node_key} is now UNLOCKED. MAC reassignment or hardware replacement is permitted.")
        messagebox.showinfo("Node Unlocked", f"✔ {node_key} is now UNLOCKED.\nYou can now reassign or replace its hardware MAC address.")

    def _ping_nodes_health(self) -> None:
        """Poll the FastAPI backend for live node health (HTTP only, no UDP)."""
        self._log("[HEALTH] Polling backend HTTP endpoint for live node health...")
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8000/api/nodes/health", headers={"User-Agent": "SetupApp"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for k, v in data.get("nodes", {}).items():
                    if k in self.node_health_tracker and v.get("online"):
                        nh = self.node_health_tracker[k]
                        nh["online"] = True
                        nh["last_seen"] = time.time() - (v.get("last_seen_sec", 0.0) if v.get("last_seen_sec", 0.0) >= 0 else 0.0)
                        nh["packets"] = v.get("packets", nh.get("packets", 0))
                        nh["rssi"] = v.get("last_rssi", -99)
                        nh["ip"] = v.get("ip", nh.get("ip", ""))
                self._log(f"[HEALTH] Backend responded — {sum(1 for nh in self.node_health_tracker.values() if nh.get('online'))} node(s) online.")
        except Exception as e:
            self._log(f"[HEALTH] Backend not reachable ({e}). Start the Collector or FastAPI server first.")

        self._refresh_registry_table()

    def _periodic_health_refresh(self) -> None:
        """Periodic HTTP-only health poll from the FastAPI backend."""
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8000/api/nodes/health", headers={"User-Agent": "SetupApp"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for k, v in data.get("nodes", {}).items():
                    if k in self.node_health_tracker and v.get("online"):
                        nh = self.node_health_tracker[k]
                        nh["online"] = True
                        nh["last_seen"] = time.time() - (v.get("last_seen_sec", 0.0) if v.get("last_seen_sec", 0.0) >= 0 else 0.0)
                        nh["packets"] = v.get("packets", nh.get("packets", 0))
                        nh["rssi"] = v.get("last_rssi", -99)
                        nh["ip"] = v.get("ip", nh.get("ip", ""))
        except Exception:
            pass

        self._refresh_registry_table()
        self.root.after(5000, self._periodic_health_refresh)

    # _health_listener_worker REMOVED — UDP port 5005 is owned exclusively
    # by the Collector (recording.py). Setup tool uses HTTP-only health polling.

    def _refresh_registry_table(self) -> None:
        self.reg_tree.delete(*self.reg_tree.get_children())
        registry = load_node_registry()
        now = time.time()
        for node_key in sorted(registry.keys()):
            info = registry[node_key]
            is_locked = bool(info.get("locked", False))
            lock_str = "🔒 LOCKED" if is_locked else "🔓 UNLOCKED"

            health = self.node_health_tracker.get(node_key, {})
            last_seen = health.get("last_seen", 0.0)
            is_live_online = (now - last_seen) < 7.0 if last_seen > 0 else False

            if is_live_online:
                pkts = health.get("packets", 0)
                ip_str = f" · {health.get('ip')}" if health.get("ip") else ""
                status_str = f"🟢 ONLINE ({pkts} pkts{ip_str})"
            else:
                if last_seen > 0:
                    status_str = f"⚪ OFFLINE ({int(now - last_seen)}s ago)"
                elif info.get("mac") and info.get("mac").upper() != "UNASSIGNED" and len(info.get("mac")) == 17:
                    status_str = "⚪ OFFLINE (Configured)"
                else:
                    status_str = "⚪ UNCONFIGURED"

            self.reg_tree.insert("", "end", values=(
                node_key,
                info.get("corner", ""),
                info.get("mac") or "Unassigned",
                lock_str,
                status_str,
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
        esptool_cmd = get_esptool_cmd()
        mac_found = None
        chip_info = "ESP32 Generic"

        if esptool_cmd:
            try:
                # Interrogate chip type
                cmd_chip = esptool_cmd + ["--port", port, "chip_id"]
                self._log(f"[RUN] {' '.join(cmd_chip)}")
                self._log("💡 If your board requires it: HOLD the BOOT button, then press EN/RESET. Release BOOT after 'Connecting...' appears.")
                proc_chip = subprocess.run(cmd_chip, capture_output=True, text=True, timeout=30)
                out_chip = proc_chip.stdout + proc_chip.stderr
                m_chip = re.search(r"Chip is\s+([^\r\n]+)", out_chip)
                if m_chip:
                    chip_info = m_chip.group(1).strip()
                    self._log(f"✔ Silicon Detected: {chip_info}")

                # Read hardware MAC
                cmd_mac = esptool_cmd + ["--port", port, "read-mac"]
                self._log("💡 Hold BOOT + press EN if the board requires manual download-mode entry (30s timeout).")
                proc = subprocess.run(cmd_mac, capture_output=True, text=True, timeout=30)
                out = proc.stdout + proc.stderr
                m = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", out)
                if m:
                    mac_found = m.group(1).upper()
                else:
                    m2 = re.search(r"([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})", out)
                    if m2:
                        mac_found = normalize_mac(m2.group(1))
            except Exception as e:
                self._log(f"[INFO] esptool interrogation note: {e}")

        # Fallback to serial query if application is already running
        if not mac_found and SERIAL_AVAILABLE:
            try:
                ser = serial.Serial(port, 115200, timeout=3.0)
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
            self.root.after(0, lambda m=mac_found: self.detected_mac_var.set(m))
            self._log(f"✔ [MAC SUCCESS] Silicon Hardware MAC Detected: {mac_found} ({chip_info})")

            # Check if this MAC is already bound in registry
            found = get_node_by_mac(mac_found)
            if found:
                node_key, info = found
                self.root.after(0, lambda nk=node_key: self.node_key_var.set(nk))
                self._log(f"ℹ [REGISTRY MATCH] This device is already permanently registered to: {node_key} ({info.get('display_name')})")
                self._log(f"  → Automatically selected target node radio: {node_key}")
            else:
                self._log(f"ℹ [NEW DEVICE] Ready to assign MAC {mac_found} to: {self.node_key_var.get()}")
        else:
            self.root.after(0, lambda: self.detected_mac_var.set("Failed to detect"))
            self._log("✖ [ERROR] Could not read MAC address. Hold the 'BOOT' button on the ESP32 while clicking 'Read MAC'.")

    def _save_binding_only(self) -> None:
        mac = self.detected_mac_var.get().strip()
        if not mac or mac in ("Not Queried", "Failed to detect"):
            messagebox.showwarning("Read MAC First", "Please click 'Read MAC' to interrogate the connected ESP32 first.")
            return

        node_key = self.node_key_var.get()
        reg = load_node_registry()
        norm_mac = normalize_mac(mac)

        # Enforce lock on target node
        if reg.get(node_key, {}).get("locked", False):
            curr_mac = reg[node_key].get("mac", "")
            if curr_mac and curr_mac.upper() != norm_mac:
                messagebox.showerror(
                    "Node Locked",
                    f"⛔ Node {node_key} is LOCKED with MAC:\n{curr_mac}\n\n"
                    f"You cannot replace its MAC with {norm_mac}.\n"
                    f"Unlock {node_key} first if you wish to reassign or replace this node."
                )
                self._log(f"[LOCK-ERROR] Cannot overwrite locked {node_key} (MAC: {curr_mac}) with {norm_mac}.")
                return

        # Enforce lock if MAC is assigned to another locked node
        for ok, info in reg.items():
            if ok != node_key and info.get("mac", "").upper() == norm_mac and info.get("locked", False):
                messagebox.showerror(
                    "MAC Address Locked",
                    f"⛔ MAC address {norm_mac} is permanently LOCKED to {ok} ({info.get('display_name', '')}).\n\n"
                    f"You cannot assign it to {node_key} unless {ok} is unlocked first."
                )
                self._log(f"[LOCK-ERROR] MAC {norm_mac} is locked to {ok}. Cannot assign to {node_key}.")
                return

        try:
            bind_mac_to_node(node_key, mac, status="registered")
            self._refresh_registry_table()
            self._log(f"✔ [SAVED] Permanently bound MAC {mac} to {node_key} in node_registry.json")
            messagebox.showinfo("Binding Saved", f"Successfully bound hardware MAC {mac} to {node_key} permanently.")
        except PermissionError as pe:
            messagebox.showerror("Lock Violation", str(pe))

    def _quick_update_wifi(self) -> None:
        """Push Wi-Fi credentials and NVS settings over Serial without flashing firmware binaries."""
        if self.is_flashing:
            return

        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Select Port", "Please select a valid COM port.")
            return

        ssid = self.wifi_ssid_var.get().strip()
        pwd = self.wifi_pass_var.get().strip()
        host = self.host_ip_var.get().strip()
        udp_port = 5005
        node_key = self.node_key_var.get()
        tag_mac = self.target_tag_var.get().strip()

        if not ssid:
            messagebox.showwarning("Missing SSID", "Please enter a Wi-Fi SSID.")
            return
        if not host or not get_hotspot_lan_interfaces():
            messagebox.showwarning(
                "Experimental Hotspot Required",
                "Enable the laptop Mobile Hotspot first. The ESP32 receiver address must be the hotspot adapter IP, not the Internet Wi-Fi address.",
            )
            return

        reg = load_node_registry()
        raw_det = self.detected_mac_var.get().strip()
        norm_det = normalize_mac(raw_det) if raw_det not in ("Not Queried", "Failed to detect", "") else None

        # Lock validations
        if reg.get(node_key, {}).get("locked", False):
            curr_mac = reg[node_key].get("mac", "")
            if norm_det and curr_mac and norm_det != curr_mac.upper():
                messagebox.showerror(
                    "Node Locked",
                    f"⛔ Node {node_key} is LOCKED with MAC:\n{curr_mac}\n\n"
                    f"Connected ESP32 has MAC: {norm_det}.\n\n"
                    f"Unlock {node_key} first if you want to replace its hardware."
                )
                return

        if not messagebox.askyesno(
            "Confirm Quick Wi-Fi Update",
            f"Push Wi-Fi & NVS configuration to {node_key} on {port}?\n\n"
            f"• Wi-Fi SSID: {ssid}\n"
            f"• Laptop Host: {host}:{udp_port}\n"
            f"• Target Tag:  {tag_mac}\n\n"
            f"(This quickly updates credentials in ESP32 NVS ROM over serial in ~2 seconds without re-flashing firmware.)"
        ):
            return

        self.is_flashing = True
        self.btn_quick_config.config(state="disabled", bg=self.THEME["card"])
        self.btn_flash.config(state="disabled", bg=self.THEME["card"])
        threading.Thread(
            target=self._worker_quick_nvs_provision,
            args=(port, node_key, ssid, pwd, host, udp_port, tag_mac),
            daemon=True,
        ).start()

    def _worker_quick_nvs_provision(
        self, port: str, node_key: str, ssid: str, pwd: str, host: str, udp_port: int, tag_mac: str
    ) -> None:
        self._log(f"\n=======================================================")
        self._log(f"📶 QUICK NVS CONFIGURATION FOR {node_key} ON {port}")
        self._log(f"=======================================================")

        try:
            if not SERIAL_AVAILABLE:
                raise RuntimeError("pyserial is required for ESP32 UART communication.")

            self._log(f"[STEP 1/3] Connecting to ESP32 on {port} (115200 baud)...")
            ser = None
            for attempt in range(1, 4):
                try:
                    ser = serial.Serial(port, 115200, timeout=1.5)
                    break
                except (serial.SerialException, PermissionError, OSError) as e:
                    self._log(f"  [Attempt {attempt}/3] Port busy or opening: {e}")
                    time.sleep(1.0)

            if not ser or not ser.is_open:
                raise RuntimeError(
                    f"Could not open serial port {port}.\n"
                    f"If the Collector or a serial monitor is currently reading from {port}, change the Collector's stream input or close it temporarily."
                )

            self._log("[STEP 2/3] Writing NVS parameters over UART...")
            time.sleep(0.4)
            ser.write(b"\n")
            time.sleep(0.2)
            try:
                ser.read_all()
            except Exception:
                pass

            commands = [
                f"SET_ANCHOR={node_key}\n",
                f"SET_TAG={tag_mac}\n",
                f"SET_WIFI={ssid},{pwd}\n",
                f"SET_HOST={host}\n",
                f"SET_PORT={udp_port}\n",
                "SAVE_CONFIG\n",
                "RECONNECT_WIFI\n",
            ]
            unsupported = []
            for cmd in commands:
                cmd_name = cmd.strip().split('=')[0]
                self._log(f"  → Sending: {cmd_name}")
                ser.write(cmd.encode("utf-8"))
                time.sleep(0.3)
                reply = ser.read_all().decode("utf-8", errors="ignore").strip()
                if reply:
                    for r_line in reply.splitlines():
                        if r_line.strip():
                            self._log(f"    ← Reply: {r_line.strip()}")
                            if "unknown command" in r_line.lower():
                                unsupported.append(cmd_name)

            if unsupported:
                raise RuntimeError(
                    "The ESP32 firmware on this device does not support the Wi-Fi provisioning commands "
                    f"({', '.join(unsupported)}).\n\n"
                    "This device is running the older 'ble_anchor' firmware, which only supports "
                    "SET_ANCHOR / SET_TAG / SET_MODE.\n\n"
                    "Use the 'Flash & Provision' button instead — it will flash the full "
                    "esp32_wifi_anchor firmware (with Wi-Fi, host & UDP support) before writing "
                    "the NVS configuration."
                )

            self._log("  → Verifying NVS parameters via GET_CONFIG...")
            ser.write(b"GET_CONFIG\n")
            time.sleep(0.5)
            verify_res = ser.read_all().decode("utf-8", errors="ignore").strip()

            ser.write(b"GET_MAC\n")
            time.sleep(0.3)
            mac_res = ser.read_all().decode("utf-8", errors="ignore").strip()
            ser.close()

            detected_mac = None
            m = re.search(r'"mac":\s*"([^"]+)"', mac_res)
            if m:
                detected_mac = normalize_mac(m.group(1))

            if not detected_mac:
                raw_mac = self.detected_mac_var.get().strip()
                if raw_mac not in ("Not Queried", "Failed to detect", ""):
                    detected_mac = normalize_mac(raw_mac)

            if not detected_mac:
                raise RuntimeError("Could not verify the ESP32 silicon MAC after NVS provisioning.")

            verified_config = False
            for line in verify_res.splitlines():
                clean = line.strip()
                if clean.startswith("{") and clean.endswith("}"):
                    try:
                        verified_config = verify_esp32_config(
                            json.loads(clean), mac=detected_mac, node_key=node_key,
                            tag_mac=tag_mac, host=host, udp_port=udp_port,
                        )
                        if verified_config:
                            break
                    except Exception:
                        pass
            if not verified_config:
                raise RuntimeError(
                    "ESP32 NVS read-back did not match the requested MAC, node, tag, host, and UDP port. "
                    "Registry was not updated."
                )

            bind_mac_to_node(node_key, detected_mac, status="provisioned")
            self.root.after(0, self._refresh_registry_table)

            self._log("✔ NVS configuration written & saved to ROM. ESP32 Wi-Fi reconnecting...")

            # Step 3: Check health via backend
            self._log("[STEP 3/3] Checking node heartbeat via backend HTTP API (15s)...")
            heartbeat_received = False
            start_wait = time.time()
            while (time.time() - start_wait) < 15.0:
                try:
                    import urllib.request
                    req = urllib.request.Request("http://127.0.0.1:8000/api/nodes/health", headers={"User-Agent": "SetupApp"})
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        node_data = data.get("nodes", {}).get(node_key, {})
                        if node_data.get("online"):
                            heartbeat_received = True
                            nh = self.node_health_tracker[node_key]
                            nh["online"] = True
                            nh["last_seen"] = time.time()
                            nh["ip"] = node_data.get("ip", "")
                            nh["packets"] = node_data.get("packets", 0)
                            nh["rssi"] = node_data.get("last_rssi", -99)
                            break
                except Exception:
                    pass
                time.sleep(2.0)

            if heartbeat_received:
                self._log(f"🟢 [VERIFIED ONLINE] Physical UDP heartbeat received from {node_key}!")
                if detected_mac:
                    bind_mac_to_node(node_key, detected_mac, status="online")
                self.root.after(0, self._refresh_registry_table)
                messagebox.showinfo(
                    "Quick Update Complete",
                    f"✔ Wi-Fi credentials updated successfully!\n\n"
                    f"Node {node_key} is VERIFIED ONLINE receiving UDP heartbeats.\n"
                    f"• SSID: {ssid}\n"
                    f"• Host: {host}:{udp_port}"
                )
            else:
                self._log("🟡 [PROVISIONED] Credentials written to NVS. Waiting for router connection.")
                messagebox.showinfo(
                    "Configuration Saved",
                    f"✔ Wi-Fi credentials sent to {node_key} and saved to NVS ROM!\n\n"
                    f"• SSID: {ssid}\n"
                    f"• Host: {host}:{udp_port}\n\n"
                    f"ESP32 is reconnecting to Wi-Fi. Check Collector or ping health in a few moments."
                )
        except Exception as err:
            self._log(f"✖ [ERROR DURING QUICK PROVISION] {err}")
            messagebox.showerror("Configuration Failed", f"Encountered error: {err}")
        finally:
            self.is_flashing = False
            self.root.after(0, lambda: self.btn_quick_config.config(state="normal", bg="#2563EB"))
            self.root.after(0, lambda: self.btn_flash.config(state="normal", bg=self.THEME["accent"]))

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
        udp_port = 5005  # Fixed — Collector owns UDP 5005 exclusively
        node_key = self.node_key_var.get()
        tag_mac = self.target_tag_var.get().strip()

        if not ssid:
            messagebox.showwarning("Missing SSID", "Please enter a Wi-Fi SSID.")
            return
        if not host or not get_hotspot_lan_interfaces():
            messagebox.showwarning(
                "Experimental Hotspot Required",
                "Enable the laptop Mobile Hotspot first. The ESP32 receiver address must be the hotspot adapter IP, not the Internet Wi-Fi address.",
            )
            return

        reg = load_node_registry()
        raw_det = self.detected_mac_var.get().strip()
        norm_det = normalize_mac(raw_det) if raw_det not in ("Not Queried", "Failed to detect", "") else None

        # Check if target node is locked
        if reg.get(node_key, {}).get("locked", False):
            curr_mac = reg[node_key].get("mac", "")
            if norm_det and curr_mac and norm_det != curr_mac.upper():
                messagebox.showerror(
                    "Node Locked",
                    f"⛔ Node {node_key} is LOCKED with MAC:\n{curr_mac}\n\n"
                    f"Connected ESP32 has MAC: {norm_det}.\n\n"
                    f"You cannot flash or replace {node_key} with a different device while it is locked.\n"
                    f"Unlock {node_key} first if you want to replace its hardware."
                )
                self._log(f"[LOCK-ERROR] Cannot flash {norm_det} to locked {node_key} (locked to {curr_mac}).")
                return

        if norm_det:
            for ok, info in reg.items():
                if ok != node_key and info.get("mac", "").upper() == norm_det and info.get("locked", False):
                    messagebox.showerror(
                        "MAC Locked",
                        f"⛔ Connected ESP32 ({norm_det}) is LOCKED to {ok}.\n\n"
                        f"You cannot flash it as {node_key} unless {ok} is unlocked first."
                    )
                    self._log(f"[LOCK-ERROR] Device {norm_det} is locked to {ok}. Cannot flash as {node_key}.")
                    return

        # Confirm action
        if not messagebox.askyesno(
            "Confirm Provisioning",
            f"Flash & Provision {node_key} on {port} with:\n\n"
            f"• Wi-Fi SSID: {ssid}\n"
            f"• Laptop Host: {host}:{udp_port}\n"
            f"• Target Tag:  {tag_mac}\n\n"
            f"Proceed?"
        ):
            return

        self.is_flashing = True
        self.btn_flash.config(state="disabled", bg=self.THEME["card"])
        if hasattr(self, "btn_quick_config"):
            self.btn_quick_config.config(state="disabled", bg=self.THEME["card"])
        threading.Thread(
            target=self._worker_provision,
            args=(port, node_key, ssid, pwd, host, udp_port, tag_mac),
            daemon=True,
        ).start()

    def _worker_provision(
        self, port: str, node_key: str, ssid: str, pwd: str, host: str, udp_port: int, tag_mac: str
    ) -> None:
        self._log(f"\n=======================================================")
        self._log(f"🚀 STARTING PROVISIONING WORKFLOW FOR {node_key} ON {port}")
        self._log(f"=======================================================")

        try:
            # 1. Interrogate Real Silicon MAC & Chip Type
            self._log("[STEP 1/4] Interrogating Silicon Chip Type & Hardware MAC...")
            esptool_cmd = get_esptool_cmd()
            mac = None
            chip_type = "ESP32"

            if esptool_cmd:
                try:
                    self._log("💡 If your board requires it: HOLD the BOOT button, then press EN/RESET.")
                    self._log("   Release BOOT after 'Connecting...' appears. (30s timeout)")
                    cmd_chip = esptool_cmd + ["--port", port, "chip_id"]
                    proc_chip = subprocess.run(cmd_chip, capture_output=True, text=True, timeout=30)
                    out_chip = proc_chip.stdout + proc_chip.stderr
                    m_chip = re.search(r"Chip is\s+([^\r\n]+)", out_chip)
                    if m_chip:
                        chip_type = m_chip.group(1).strip()
                        self._log(f"✔ Detected Chip: {chip_type}")

                    cmd_mac = esptool_cmd + ["--port", port, "read-mac"]
                    proc = subprocess.run(cmd_mac, capture_output=True, text=True, timeout=30)
                    m = re.search(r"MAC:\s*([0-9a-fA-F:]{17})", proc.stdout + proc.stderr)
                    if m:
                        mac = m.group(1).upper()
                except subprocess.TimeoutExpired:
                    self._log("⏰ [TIMEOUT] esptool timed out after 30s. Hold BOOT + press EN and retry.")
                except Exception as e:
                    self._log(f"[INFO] Hardware scan note: {e}")

            if not mac:
                mac = self.detected_mac_var.get()
                if mac in ("Not Queried", "Failed to detect"):
                    mac = None

            if not mac and SERIAL_AVAILABLE:
                try:
                    ser = serial.Serial(port, 115200, timeout=3.0)
                    time.sleep(0.3)
                    ser.write(b"GET_MAC\n")
                    time.sleep(0.3)
                    res = ser.read_all().decode("utf-8", errors="ignore")
                    ser.close()
                    m = re.search(r'"mac":\s*"([^"]+)"', res)
                    if m:
                        mac = normalize_mac(m.group(1))
                except Exception:
                    pass

            if not mac:
                raise RuntimeError("Could not interrogate real silicon MAC address. Hold the BOOT button on the ESP32 and try again.")

            self._log(f"✔ Silicon Hardware MAC: {mac}")

            # 2. Flash ESP-IDF Firmware Binaries (bootloader @ 0x1000, partition-table @ 0x8000, app @ 0x10000)
            self._log("[STEP 2/5] Locating and Flashing ESP-IDF Firmware Binaries...")
            bins = get_firmware_binaries()
            app_bin = bins.get("app")
            boot_bin = bins.get("bootloader")
            part_bin = bins.get("partitions")

            if not esptool_cmd:
                raise RuntimeError("esptool is required for flashing ESP32 hardware.")

            if not app_bin or not app_bin.exists():
                self._log("⚠️ Compiled app binary not found. Triggering automated ESP-IDF build...")
                built = build_esp_idf_firmware(log_cb=self._log)
                if not built:
                    raise RuntimeError("Failed to build firmware using ESP-IDF. Please check the build log.")
                bins = get_firmware_binaries()
                app_bin = bins.get("app")
                boot_bin = bins.get("bootloader")
                part_bin = bins.get("partitions")

            if not app_bin or not app_bin.exists():
                raise RuntimeError("esp32_wifi_anchor.bin not found after build.")

            flash_args = [
                "--port", port,
                "--baud", "460800",
                "write_flash",
                "-z",
                "--flash_mode", "dio",
                "--flash_freq", "40m",
                "--flash_size", "2MB",
            ]
            if boot_bin and boot_bin.exists():
                flash_args.extend(["0x1000", str(boot_bin)])
            if part_bin and part_bin.exists():
                flash_args.extend(["0x8000", str(part_bin)])
            flash_args.extend(["0x10000", str(app_bin)])

            flash_cmd = esptool_cmd + flash_args
            self._log(f"⚡ Flashing ESP-IDF firmware to {port}...")
            self._log("💡 Hold BOOT + press EN if required. Flashing can take up to 2 minutes.")
            self._log(f"[RUN] {' '.join(flash_cmd)}")
            p_flash = subprocess.run(flash_cmd, capture_output=True, text=True, timeout=120)
            if p_flash.returncode != 0:
                raise RuntimeError(f"esptool write_flash failed: {p_flash.stderr or p_flash.stdout}")
            self._log("✔ Flash write successful! Waiting for Windows COM driver release & chip reboot...")
            time.sleep(3.5)

            # 3. Verify Serial Boot & UART Communication
            self._log("[STEP 3/5] Verifying Serial Boot & Handshake...")
            if not SERIAL_AVAILABLE:
                raise RuntimeError("pyserial is required for ESP32 UART communication.")

            ser = None
            boot_ok = False
            for attempt in range(1, 6):
                try:
                    ser = serial.Serial(port, 115200, timeout=1.5)
                    time.sleep(0.4)
                    ser.write(b"\nGET_MAC\n")
                    time.sleep(0.4)
                    res = ser.read_all().decode("utf-8", errors="ignore")
                    if "mac" in res.lower() or "{" in res or "anchor" in res.lower():
                        boot_ok = True
                        self._log(f"✔ [BOOT HANDSHAKE] ESP32 firmware responded on {port} (Attempt {attempt})")
                        break
                    else:
                        # Firmware is running, received characters or prompt
                        boot_ok = True
                        self._log(f"✔ [PORT READY] Serial port {port} opened successfully on attempt {attempt}")
                        break
                except (serial.SerialException, PermissionError, OSError) as e:
                    self._log(f"  [Attempt {attempt}/5] Waiting for Windows to release {port}... ({e})")
                    if ser:
                        try:
                            ser.close()
                        except Exception:
                            pass
                    ser = None
                    time.sleep(1.5)

            if not ser or not ser.is_open:
                raise RuntimeError(
                    f"Could not open serial port {port} after 5 attempts (Access Denied / Driver Lock).\n"
                    f"Ensure no other serial monitor (Arduino IDE, VS Code, PuTTY) or process is using {port}."
                )

            # 4. Transmit NVS parameters over UART with Read-Back Verification
            self._log("[STEP 4/5] Writing Wi-Fi credentials & Node identity into NVS Flash...")

            # Drain any boot spam from buffer
            try:
                ser.read_all()
            except Exception:
                pass

            # Wait for the freshly-flashed firmware to finish booting and the UART
            # command handler to become ready. Commands sent too early are silently
            # dropped while the chip is still booting, which causes the read-back
            # verification to fail. Poll GET_MAC until the firmware responds.
            self._log("  → Waiting for firmware to finish booting (UART handshake)...")
            fw_ready = False
            for _ in range(20):
                try:
                    ser.write(b"GET_MAC\n")
                    time.sleep(0.4)
                    res = ser.read_all().decode("utf-8", errors="ignore")
                    if '"mac"' in res.lower() or "mac" in res.lower():
                        fw_ready = True
                        self._log("  ✔ Firmware ready — UART command handler responding.")
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            if not fw_ready:
                raise RuntimeError(
                    "ESP32 firmware did not respond to UART handshake after flashing. "
                    "The chip may still be booting or the firmware did not start. "
                    "Reopen the port and try again."
                )

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
                cmd_name = cmd.strip().split('=')[0]
                self._log(f"  → Sending: {cmd_name}")
                ser.write(cmd.encode("utf-8"))
                time.sleep(0.3)
                reply = ser.read_all().decode("utf-8", errors="ignore").strip()
                if reply:
                    for r_line in reply.splitlines():
                        if r_line.strip():
                            self._log(f"    ← Reply: {r_line.strip()}")

            # Strict Read-Back Verification
            self._log("  → Verifying NVS parameters via GET_CONFIG...")
            ser.write(b"GET_CONFIG\n")
            time.sleep(0.5)
            verify_res = ser.read_all().decode("utf-8", errors="ignore").strip()
            try:
                ser.close()
            except Exception:
                pass

            verified = False
            if verify_res:
                for line in verify_res.splitlines():
                    clean = line.strip()
                    if clean.startswith("{") and clean.endswith("}"):
                        try:
                            cfg_data = json.loads(clean)
                            if verify_esp32_config(
                                cfg_data, mac=mac, node_key=node_key, tag_mac=tag_mac,
                                host=host, udp_port=udp_port,
                            ):
                                verified = True
                                self._log(f"    ← NVS Verified: Node={cfg_data.get('node')}, Tag={cfg_data.get('tag')}, SSID={cfg_data.get('ssid')}")
                                break
                        except Exception:
                            pass

            if not verified:
                raise RuntimeError(
                    "ESP32 read-back did not match the requested MAC, node, tag, host, and UDP port. "
                    "Registry was not updated. Reflash and provision again."
                )

            self._log(f"✔ Read-Back Verified: {node_key} actively running with target tag {tag_mac}")

            # 5. Verify node came online via HTTP health poll (no UDP bind — Collector owns 5005)
            self._log(f"[STEP 5/5] Verifying node health via backend HTTP API...")
            self._log("📡 Polling http://127.0.0.1:8000/api/nodes/health for heartbeat (timeout: 20s)...")
            self._log("   (Ensure the Collector or FastAPI server is running to see live heartbeats.)")

            heartbeat_received = False
            start_wait = time.time()
            while (time.time() - start_wait) < 20.0:
                try:
                    import urllib.request
                    req = urllib.request.Request("http://127.0.0.1:8000/api/nodes/health", headers={"User-Agent": "SetupApp"})
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        node_data = data.get("nodes", {}).get(node_key, {})
                        if node_data.get("online"):
                            heartbeat_received = True
                            nh = self.node_health_tracker[node_key]
                            nh["online"] = True
                            nh["last_seen"] = time.time()
                            nh["ip"] = node_data.get("ip", "")
                            nh["packets"] = node_data.get("packets", 0)
                            nh["rssi"] = node_data.get("last_rssi", -99)
                            break
                except Exception:
                    pass
                time.sleep(2.0)

            if heartbeat_received:
                self._log(f"🟢 [VERIFIED ONLINE] Physical UDP heartbeat received from {node_key} ({mac})!")
                save_status = "online"
            else:
                self._log(f"🟡 [PROVISIONED] Configuration saved, but no UDP packet arrived within 15s.")
                self._log("   (Verify ESP32 is in Wi-Fi range and router permits UDP broadcast.)")
                save_status = "provisioned"

            bind_mac_to_node(node_key, mac, status=save_status)
            self.root.after(0, self._refresh_registry_table)

            self._log(f"✔ {node_key} successfully configured and permanently bound to {mac}!")
            self._log("ℹ Node is now ready. Place at room corner and power via USB charger.")
            self._log("=======================================================\n")
            status_msg = "Node is VERIFIED ONLINE via real UDP heartbeats!" if heartbeat_received else "Node is provisioned. Connect to Wi-Fi to establish heartbeats."
            messagebox.showinfo(
                "Provisioning Complete",
                f"Successfully provisioned {node_key}!\n\n"
                f"• Status: {status_msg}\n"
                f"• Hardware MAC: {mac}\n"
                f"• Wi-Fi Network: {ssid}\n"
                f"• Host Receiver: {host}:5005\n\n"
                f"You can now unplug this ESP32 and place it at its designated corner."
            )
        except Exception as err:
            self._log(f"✖ [ERROR DURING PROVISIONING] {err}")
            self._log("💡 TROUBLESHOOTING TIP: Ensure no other serial monitor or application is holding the COM port.")
            messagebox.showerror("Provisioning Failed", f"Encountered error: {err}")
        finally:
            self.is_flashing = False
            if hasattr(self, "btn_quick_config"):
                self.root.after(0, lambda: self.btn_quick_config.config(state="normal", bg="#2563EB"))
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
