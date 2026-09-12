"""Indoor Positioning — Standalone System Administrator & Telemetry GUI.

A focused, modular Python application for infrastructure administration,
node health monitoring, connection statistics, error diagnostics, and system telemetry.
Delegates network monitoring to ConnectionMonitor and system checks to DiagnosticEngine.
"""
from __future__ import annotations

import datetime
import json
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import BACKEND_URL, load_anchor_config, load_anchor_metadata
from core.telemetry import SystemTelemetryManager
from admin.connection_monitor import ConnectionMonitor, ConnectionStatus
from admin.diagnostics import DiagnosticEngine, DiagnosticCheckResult


class SystemAdminApp:
    """Dedicated desktop GUI for system administration and telemetry monitoring."""

    THEME = {
        "bg": "#0B1120",          # Deep Obsidian Navy
        "panel": "#131D31",       # Navy Surface
        "card": "#1E293B",        # Slate 800
        "border": "#334155",      # Slate 700
        "text": "#F1F5F9",        # Slate 100
        "subtext": "#94A3B8",     # Slate 400
        "accent": "#38BDF8",      # Sky 400
        "green": "#10B981",       # Emerald 500
        "green_dark": "#064E3B",
        "amber": "#F59E0B",       # Amber 500
        "amber_dark": "#78350F",
        "red": "#EF4444",         # Rose 500
        "red_dark": "#7F1D1D",
        "purple": "#A855F7",      # Purple 500
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("🛠️ BLE RTLS — System Administrator & Telemetry Console")
        self.root.geometry("1240x840")
        self.root.minsize(1040, 680)
        self.root.configure(bg=self.THEME["bg"])

        # Modular backend & telemetry monitors
        anchor_cfgs = load_anchor_config()
        self.anchor_meta = load_anchor_metadata()
        self.telemetry = SystemTelemetryManager(list(anchor_cfgs.keys()))
        self.conn_monitor = ConnectionMonitor(BACKEND_URL)

        # Populate names from metadata
        for aid, meta in self.anchor_meta.items():
            self.telemetry.get_or_create_node(aid, mac=meta.get("mac", ""), name=meta.get("name", aid))

        self.backend_online = False
        self.last_ping_ms = 0.0
        self.selected_log_filter = tk.StringVar(value="ALL")

        self._configure_styles()
        self._build_ui()

        # Start periodic telemetry poller
        self.root.after(200, self._poll_system_telemetry)

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

        style.configure("TNotebook", background=t["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=t["panel"], foreground=t["subtext"], padding=(16, 8), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", t["card"])], foreground=[("selected", t["text"])])

        style.configure("TCombobox", fieldbackground=t["card"], background=t["card"], foreground=t["text"], padding=4)
        style.configure("TEntry", fieldbackground=t["card"], foreground=t["text"], padding=4)

    def _build_ui(self) -> None:
        # Top Header Bar
        header = tk.Frame(self.root, bg=self.THEME["panel"], height=58)
        header.pack(fill="x", side="top")

        title_box = tk.Frame(header, bg=self.THEME["panel"])
        title_box.pack(side="left", padx=20, pady=10)

        tk.Label(title_box, text="🛠️ SYSTEM ADMINISTRATOR & TELEMETRY", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(title_box, text="· Infrastructure Health & Network Diagnostics", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 9)).pack(side="left", padx=10)

        # Quick Health Badges
        right_box = tk.Frame(header, bg=self.THEME["panel"])
        right_box.pack(side="right", padx=20, pady=12)

        self.api_badge = tk.Label(right_box, text="API: CHECKING...", bg=self.THEME["card"], fg=self.THEME["subtext"], font=("Segoe UI", 8, "bold"), padx=10, pady=3)
        self.api_badge.pack(side="left", padx=4)

        self.health_badge = tk.Label(right_box, text="NODES: 0/12", bg=self.THEME["card"], fg=self.THEME["subtext"], font=("Segoe UI", 8, "bold"), padx=10, pady=3)
        self.health_badge.pack(side="left", padx=4)

        # Notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        # Tab 1: Node Telemetry & Hardware State
        self.tab_nodes = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_nodes, text="📡 ESP32 Nodes & Telemetry")
        self._build_nodes_tab(self.tab_nodes)

        # Tab 2: Connections & Network Monitor
        self.tab_network = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_network, text="🌐 Connections & Network")
        self._build_network_tab(self.tab_network)

        # Tab 3: Diagnostics & Event Logs
        self.tab_diag = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_diag, text="🩺 Diagnostics & Logs")
        self._build_diag_tab(self.tab_diag)

    def _build_nodes_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        # Top System KPI Row
        kpi_row = tk.Frame(p, bg=t["bg"])
        kpi_row.pack(fill="x", pady=(0, 12))
        for col in range(5):
            kpi_row.columnconfigure(col, weight=1, uniform="kpi")

        self.kpi_online = self._create_kpi(kpi_row, 0, "ONLINE NODES", "-- / 12", t["green"])
        self.kpi_packets = self._create_kpi(kpi_row, 1, "TOTAL PACKETS", "--", t["accent"])
        self.kpi_drops = self._create_kpi(kpi_row, 2, "DROPPED PACKETS", "0 (0.0%)", t["green"])
        self.kpi_cpu = self._create_kpi(kpi_row, 3, "BACKEND CPU / RAM", "--% / --MB", t["amber"])
        self.kpi_uptime = self._create_kpi(kpi_row, 4, "SYSTEM UPTIME", "0s", t["purple"])

        # Node Telemetry Table
        table_frame = tk.Frame(p, bg=t["panel"], padx=14, pady=12)
        table_frame.pack(fill="both", expand=True)

        tk.Label(table_frame, text="ESP32 RECEIVER NODES LIVE TELEMETRY MATRIX", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        cols = ("anchor", "mac", "name", "status", "rssi", "packets", "drops", "rate", "latency", "last_seen")
        self.node_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)
        self.node_tree.heading("anchor", text="Node ID")
        self.node_tree.heading("mac", text="Hardware MAC")
        self.node_tree.heading("name", text="Designation / Room")
        self.node_tree.heading("status", text="Health Status")
        self.node_tree.heading("rssi", text="Avg RSSI")
        self.node_tree.heading("packets", text="Packets")
        self.node_tree.heading("drops", text="Drops")
        self.node_tree.heading("rate", text="Rate (Hz)")
        self.node_tree.heading("latency", text="Latency")
        self.node_tree.heading("last_seen", text="Last Active")

        self.node_tree.column("anchor", width=95, anchor="center")
        self.node_tree.column("mac", width=140, anchor="center")
        self.node_tree.column("name", width=180, anchor="w")
        self.node_tree.column("status", width=95, anchor="center")
        self.node_tree.column("rssi", width=85, anchor="center")
        self.node_tree.column("packets", width=85, anchor="center")
        self.node_tree.column("drops", width=75, anchor="center")
        self.node_tree.column("rate", width=80, anchor="center")
        self.node_tree.column("latency", width=80, anchor="center")
        self.node_tree.column("last_seen", width=100, anchor="center")

        self.node_tree.pack(fill="both", expand=True, pady=(8, 0))

    def _build_network_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        split = tk.Frame(p, bg=t["bg"])
        split.pack(fill="both", expand=True)

        left = tk.Frame(split, bg=t["panel"], width=520, padx=16, pady=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="COMMUNICATION INTERFACES & PORTS", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))

        # Core Backend API card
        api_card = tk.Frame(left, bg=t["card"], padx=14, pady=12)
        api_card.pack(fill="x", pady=6)
        tk.Label(api_card, text="CORE FASTAPI REST / WEBSOCKET ENGINE", bg=t["card"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.lbl_api_info = tk.Label(api_card, text=f"Endpoint: {BACKEND_URL}\nStatus: Checking...", bg=t["card"], fg=t["subtext"], justify="left")
        self.lbl_api_info.pack(anchor="w", pady=(4, 6))

        tk.Button(api_card, text="🔄 Test Connection / Ping", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._ping_backend).pack(anchor="w")

        # Serial COM Ports card
        serial_card = tk.Frame(left, bg=t["card"], padx=14, pady=12)
        serial_card.pack(fill="x", pady=6)
        tk.Label(serial_card, text="PHYSICAL SERIAL & USB COM PORTS", bg=t["card"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.lbl_serial_info = tk.Label(serial_card, text="Scanning ports...", bg=t["card"], fg=t["subtext"], justify="left")
        self.lbl_serial_info.pack(anchor="w", pady=(4, 6))

        tk.Button(serial_card, text="🔄 Rescan Hardware Ports", bg=t["panel"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._scan_serial_ports).pack(anchor="w")

        right = tk.Frame(split, bg=t["panel"], width=520, padx=16, pady=14)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(right, text="CONNECTION INTEGRITY & STATS", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 10))

        self.net_stats_text = tk.Text(right, bg="#0B1120", fg=t["text"], font=("Consolas", 9), relief="flat", wrap="word")
        self.net_stats_text.pack(fill="both", expand=True)

    def _build_diag_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        toolbar = tk.Frame(p, bg=t["panel"], padx=14, pady=10)
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(toolbar, text="SYSTEM DIAGNOSTICS & EVENT LOG", bg=t["panel"], fg=t["text"], font=("Segoe UI", 10, "bold")).pack(side="left")

        tk.Button(toolbar, text="🩺 Run Health Self-Check", bg=t["accent"], fg="#000000", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=12, pady=4, command=self._run_health_check).pack(side="right", padx=4)
        tk.Button(toolbar, text="🗑️ Clear Logs", bg=t["card"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=10, pady=4, command=self._clear_logs).pack(side="right", padx=4)

        tk.Label(toolbar, text="Filter:", bg=t["panel"], fg=t["subtext"], font=("Segoe UI", 8)).pack(side="right", padx=(12, 4))
        for level in ("ALL", "INFO", "WARNING", "ERROR"):
            tk.Button(
                toolbar, text=level,
                bg=t["card"], fg=t["text"], font=("Segoe UI", 8),
                relief="flat", cursor="hand2", padx=6, pady=2,
                command=lambda l=level: self._set_log_filter(l),
            ).pack(side="right", padx=2)

        log_frame = tk.Frame(p, bg=t["panel"], padx=14, pady=12)
        log_frame.pack(fill="both", expand=True)

        self.diag_text = tk.Text(log_frame, bg="#090E17", fg=t["text"], font=("Consolas", 9), relief="flat", wrap="word")
        self.diag_text.pack(fill="both", expand=True)

    def _create_kpi(self, parent: tk.Frame, col: int, title: str, val: str, color: str) -> tk.Label:
        card = tk.Frame(parent, bg=self.THEME["panel"], padx=14, pady=10)
        card.grid(row=0, column=col, sticky="nsew", padx=3)

        tk.Label(card, text=title, bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        lbl = tk.Label(card, text=val, bg=self.THEME["panel"], fg=color, font=("Segoe UI", 12, "bold"))
        lbl.pack(anchor="w", pady=(3, 0))
        return lbl

    def _poll_system_telemetry(self) -> None:
        def worker():
            status: ConnectionStatus = self.conn_monitor.ping_backend()
            self.root.after(0, lambda: self._update_ui_with_status(status))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(1500, self._poll_system_telemetry)

    def _update_ui_with_status(self, status: ConnectionStatus) -> None:
        self.backend_online = status.is_online
        self.last_ping_ms = status.latency_ms

        if status.is_online:
            self.api_badge.config(text=f"API: ONLINE ({status.latency_ms}ms)", bg=self.THEME["green_dark"], fg="#FFFFFF")
            self.lbl_api_info.config(text=f"Endpoint: {BACKEND_URL}\nStatus: ONLINE · Latency: {status.latency_ms} ms · {status.message}")
        else:
            self.api_badge.config(text="API: OFFLINE", bg=self.THEME["red_dark"], fg="#FFFFFF")
            self.lbl_api_info.config(text=f"Endpoint: {BACKEND_URL}\nStatus: OFFLINE · {status.message}")

        # Update host resources and stats
        tele = self.telemetry.get_full_telemetry()
        res = tele.get("host_resources", {})
        cpu = res.get("cpu_percent", 0.0)
        ram = res.get("ram_used_mb", 0.0)
        self.kpi_cpu.config(text=f"{cpu}% / {ram:.0f}MB")

        online_n = tele.get("online_nodes", 0)
        total_n = tele.get("total_nodes", 12)
        self.kpi_online.config(text=f"{online_n} / {total_n}")
        self.health_badge.config(text=f"NODES: {online_n}/{total_n}")

        total_pkts = tele.get("total_packets", 0)
        self.kpi_packets.config(text=f"{total_pkts:,}")

        drops = tele.get("total_dropped_packets", 0)
        drop_rate = tele.get("drop_rate_pct", 0.0)
        self.kpi_drops.config(text=f"{drops} ({drop_rate}%)", fg=self.THEME["green"] if drop_rate < 1.0 else self.THEME["amber"])

        uptime = tele.get("uptime_seconds", 0)
        self.kpi_uptime.config(text=f"{int(uptime)}s")

        # Network stats
        stats = self.conn_monitor.get_connection_statistics()
        self.net_stats_text.delete("1.0", "end")
        self.net_stats_text.insert("end", (
            f"CONNECTION METRICS\n"
            f"----------------------------------------\n"
            f"Total Ping Requests : {stats['total_attempts']}\n"
            f"Failed Requests     : {stats['failed_attempts']}\n"
            f"Network Reliability : {stats['success_rate_pct']}%\n"
            f"Last Round-trip     : {status.latency_ms} ms\n"
        ))

        # Node tree
        for item in self.node_tree.get_children():
            self.node_tree.delete(item)

        for aid, node_data in tele.get("nodes", {}).items():
            st = node_data.get("status", "OFFLINE")
            st_text = "🟢 ONLINE" if st == "ONLINE" else "🟡 DEGRADED" if st == "DEGRADED" else "⚪ OFFLINE"
            last_sec = node_data.get("last_seen_seconds_ago", -1)
            last_text = f"{last_sec:.1f}s ago" if last_sec >= 0 else "Never"

            self.node_tree.insert("", "end", values=(
                aid,
                node_data.get("mac_address", "Unknown"),
                node_data.get("name", aid),
                st_text,
                f"{node_data.get('average_rssi', -100):.1f} dBm",
                f"{node_data.get('packet_count', 0):,}",
                str(node_data.get("dropped_packets", 0)),
                f"{node_data.get('packet_rate_hz', 0.0):.1f}",
                f"{node_data.get('latency_ms', 0.0):.0f} ms",
                last_text,
            ))

    def _ping_backend(self) -> None:
        self.lbl_api_info.config(text=f"Endpoint: {BACKEND_URL}\nPinging server...")
        def pinger():
            status = self.conn_monitor.ping_backend()
            if status.is_online:
                self.root.after(0, lambda: messagebox.showinfo("Ping Successful", f"Backend reached in {status.latency_ms} ms."))
            else:
                self.root.after(0, lambda: messagebox.showerror("Ping Failed", f"Could not reach backend:\n{status.message}"))

        threading.Thread(target=pinger, daemon=True).start()

    def _scan_serial_ports(self) -> None:
        ports = self.conn_monitor.scan_serial_interfaces()
        if not ports:
            self.lbl_serial_info.config(text="No hardware COM ports detected.\nConnect ESP32 receiver or use Simulated Stream.")
        else:
            lines = [f"• {p['device']}: {p['description']}" for p in ports]
            self.lbl_serial_info.config(text="\n".join(lines))

    def _run_health_check(self) -> None:
        """Run system-wide diagnostic check via DiagnosticEngine."""
        checks: list[DiagnosticCheckResult] = DiagnosticEngine.run_self_check(
            is_backend_online=self.backend_online,
            backend_latency_ms=self.last_ping_ms,
        )
        lines = []
        for c in checks:
            badge = "✔ PASS" if c.status == "PASS" else "⚠ WARN" if c.status == "WARN" else "❌ FAIL"
            lines.append(f"[{badge}] {c.component}: {c.details}")

        msg = "\n".join(lines)
        self.diag_text.insert("end", f"\n--- HEALTH SELF-CHECK ({datetime.datetime.now().strftime('%H:%M:%S')}) ---\n" + msg + "\n")
        self.diag_text.see("end")
        messagebox.showinfo("Health Check Results", msg)

    def _set_log_filter(self, level: str) -> None:
        self.selected_log_filter.set(level)

    def _clear_logs(self) -> None:
        self.diag_text.delete("1.0", "end")


def main() -> None:
    root = tk.Tk()
    app = SystemAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
