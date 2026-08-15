"""Indoor Positioning — Professional Operations Console.

A focused desktop control room for launching and monitoring the positioning stack.
The interface intentionally avoids decorative icons and excessive colour: hierarchy,
spacing, typography, and explicit action labels do the work.
"""
from __future__ import annotations

import os
import queue
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
CPU_CORES = os.cpu_count() or 4
MAX_LOG_LINES = 3000


def open_url(url: str) -> None:
    """Reliably launch a URL in the user's default browser using native shell start."""
    if os.name == "nt":
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", url], shell=True)
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


class OperationsConsole:
    C = {
        "window": "#F4F6F8",
        "nav": "#102A43",
        "nav_muted": "#9FB3C8",
        "nav_active": "#1F4E79",
        "white": "#FFFFFF",
        "ink": "#102A43",
        "muted": "#627D98",
        "line": "#D9E2EC",
        "soft": "#EAF0F5",
        "blue": "#1769AA",
        "blue_hover": "#0F5A94",
        "teal": "#178C8C",
        "green": "#218739",
        "amber": "#B7791F",
        "red": "#C53030",
        "console": "#0B1F33",
        "console_text": "#C8D6E5",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Indoor Positioning — Operations Console")
        self.root.geometry("1280x820")
        self.root.minsize(1040, 680)
        self.root.configure(bg=self.C["window"])

        self.services = self._services()
        self.processes: dict[str, subprocess.Popen[str] | None] = {s.key: None for s in self.services}
        self.process_lock = threading.RLock()
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.log_records: list[tuple[str, str]] = []
        self.resource_mode = tk.StringVar(value="Recommended")
        self.log_filter = tk.StringVar(value="All messages")
        self.selected_key: Optional[str] = None
        self.card_refs: dict[str, dict[str, tk.Widget]] = {}
        self.shutting_down = False

        self._styles()
        self._build_shell()
        self._build_overview()
        self._build_service_view()
        self._build_activity_view()
        self._refresh_state()
        self._select_service("backend")
        self._log("Console ready. Hosting Location Engine API, Web Dashboard parameters, and simulator.", "System")
        self.root.after(150, self._drain_logs)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        autostart = "--autostart" in sys.argv or "-a" in sys.argv
        if autostart:
            self._log("Auto-hosting mode triggered: launching backend API, web dashboard, and data stream...", "System")
            self.root.after(400, self.start_demo)


    def _services(self) -> tuple[Service, ...]:
        return (
            Service("backend", "Location Engine API", "Core services", "Receives telemetry, calculates locations, applies filtering, stores history, and exposes REST/WebSocket endpoints.", "server/app.py", (PYTHON, str(PROJECT_ROOT / "server" / "app.py")), PROJECT_ROOT / "server", "http://127.0.0.1:8000"),
            Service("dashboard", "Web Dashboard", "Core services", "Provides the browser-based floorplan, asset tracking, and live operations view.", "Vite development server", ("npx", "vite", "--port", "5173"), BASE_DIR, "http://127.0.0.1:5173"),
            Service("collector", "BLE Sensor Collector", "Data workers", "Reads RSSI telemetry from physical Bluetooth, USB, or serial room sensors and forwards it to the API.", "collector/collector.py", (PYTHON, str(PROJECT_ROOT / "collector" / "collector.py"), "--port", "stdin"), PROJECT_ROOT),
            Service("simulator", "Beacon Motion Simulator", "Data workers", "Generates synthetic beacon movement and RSSI readings for demonstrations without physical hardware.", "simulate_demo.py", (PYTHON, str(PROJECT_ROOT / "simulate_demo.py")), PROJECT_ROOT),
            Service("pipeline", "Training Pipeline", "ML workers", "Builds RSSI window features, evaluates models, and exports positioning model artefacts.", "pipeline.py", (PYTHON, str(PROJECT_ROOT / "pipeline.py")), PROJECT_ROOT),
            Service("trainer", "Model Studio", "ML workers", "Opens the interactive model evaluation and path-loss tuning workspace.", "training_gui.py", (PYTHON, str(PROJECT_ROOT / "training_gui.py")), PROJECT_ROOT),
        )

    def _styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        c = self.C
        style.configure("TFrame", background=c["window"])
        style.configure("Nav.TFrame", background=c["nav"])
        style.configure("Panel.TFrame", background=c["white"])
        style.configure("Top.TFrame", background=c["window"])
        style.configure("Title.TLabel", background=c["window"], foreground=c["ink"], font=("Segoe UI", 20, "bold"))
        style.configure("NavTitle.TLabel", background=c["nav"], foreground=c["white"], font=("Segoe UI", 13, "bold"))
        style.configure("NavText.TLabel", background=c["nav"], foreground=c["nav_muted"], font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=c["window"], foreground=c["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("PanelTitle.TLabel", background=c["white"], foreground=c["ink"], font=("Segoe UI", 12, "bold"))
        style.configure("PanelText.TLabel", background=c["white"], foreground=c["muted"], font=("Segoe UI", 9))
        style.configure("Card.TFrame", background=c["white"])
        style.configure("CardTitle.TLabel", background=c["white"], foreground=c["ink"], font=("Segoe UI", 10, "bold"))
        style.configure("CardText.TLabel", background=c["white"], foreground=c["muted"], font=("Segoe UI", 9))
        style.configure("MetricValue.TLabel", background=c["white"], foreground=c["ink"], font=("Segoe UI", 19, "bold"))
        style.configure("MetricLabel.TLabel", background=c["white"], foreground=c["muted"], font=("Segoe UI", 8, "bold"))
        style.configure("TButton", font=("Segoe UI", 9), padding=(11, 7))
        style.configure("Primary.TButton", background=c["blue"], foreground=c["white"], borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Primary.TButton", background=[("active", c["blue_hover"]), ("disabled", c["line"])])
        style.configure("Secondary.TButton", background=c["soft"], foreground=c["ink"], borderwidth=0)
        style.map("Secondary.TButton", background=[("active", c["line"])])
        style.configure("Danger.TButton", background=c["white"], foreground=c["red"], borderwidth=1, relief="solid")
        style.map("Danger.TButton", background=[("active", "#FDECEC")])
        style.configure("TCombobox", fieldbackground=c["white"], background=c["white"], foreground=c["ink"], bordercolor=c["line"], padding=5)
        style.configure("Treeview", background=c["white"], fieldbackground=c["white"], foreground=c["ink"], rowheight=39, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=c["soft"], foreground=c["muted"], relief="flat", font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", "#DCECF8")], foreground=[("selected", c["ink"])])
        style.configure("Horizontal.TProgressbar", troughcolor=c["soft"], background=c["teal"], borderwidth=0, thickness=5)
        style.configure("Vertical.TScrollbar", background=c["soft"], troughcolor=c["white"], arrowcolor=c["muted"], borderwidth=0)

    def _build_shell(self) -> None:
        self.nav = ttk.Frame(self.root, style="Nav.TFrame", width=220, padding=(22, 24))
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        ttk.Label(self.nav, text="Indoor Positioning", style="NavTitle.TLabel").pack(anchor="w")
        ttk.Label(self.nav, text="Real-time BLE tag movement\nacross anchor mesh   BLE · RTLS", style="NavText.TLabel", wraplength=170).pack(anchor="w", pady=(4, 28))
        ttk.Label(self.nav, text="OPERATIONS", background=self.C["nav"], foreground=self.C["nav_muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 8))
        self.nav_buttons: dict[str, tk.Button] = {}
        for key, label in (("overview", "Overview"), ("services", "Services"), ("activity", "Activity")):
            button = tk.Button(self.nav, text=label, anchor="w", relief="flat", borderwidth=0, padx=12, pady=9, background=self.C["nav"], foreground=self.C["nav_muted"], activebackground=self.C["nav_active"], activeforeground=self.C["white"], font=("Segoe UI", 9), command=lambda k=key: self._show_view(k))
            button.pack(fill="x", pady=2)
            self.nav_buttons[key] = button
        ttk.Separator(self.nav).pack(fill="x", pady=24)
        ttk.Label(self.nav, text="RESOURCE PROFILE", background=self.C["nav"], foreground=self.C["nav_muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(self.nav, textvariable=self.resource_mode, values=("Eco", "Recommended", "Turbo"), state="readonly", width=16).pack(fill="x", pady=(8, 4))
        ttk.Label(self.nav, text=f"Detected capacity: {CPU_CORES} CPU cores", style="NavText.TLabel", wraplength=170).pack(anchor="w")
        ttk.Label(self.nav, text="Use Recommended for normal operation. Turbo uses all available cores.", style="NavText.TLabel", wraplength=170).pack(anchor="w", pady=(8, 0))
        self.content = ttk.Frame(self.root, padding=(30, 26, 30, 26))
        self.content.pack(side="right", fill="both", expand=True)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(1, weight=1)
        header = ttk.Frame(self.content, style="Top.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.columnconfigure(0, weight=1)
        self.page_title = ttk.Label(header, text="Overview", style="Title.TLabel")
        self.page_title.grid(row=0, column=0, sticky="w")
        self.system_state = ttk.Label(header, text="SYSTEM IDLE", background=self.C["window"], foreground=self.C["muted"], font=("Segoe UI", 9, "bold"))
        self.system_state.grid(row=0, column=1, sticky="e")

    def _panel(self, parent: tk.Widget, padding=18) -> ttk.Frame:
        return ttk.Frame(parent, style="Panel.TFrame", padding=padding)

    def _build_overview(self) -> None:
        self.overview = ttk.Frame(self.content)
        self.overview.columnconfigure(0, weight=3)
        self.overview.columnconfigure(1, weight=2)
        self.overview.rowconfigure(2, weight=1)
        self.overview.grid(row=1, column=0, sticky="nsew")
        intro = self._panel(self.overview, 22)
        intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        intro.columnconfigure(0, weight=1)
        ttk.Label(intro, text="Control room", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(intro, text="Start the complete positioning system stack or manage individual processes from Services.", style="PanelText.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 16))
        ttk.Button(intro, text="Start System Stack", style="Primary.TButton", command=self.start_demo).grid(row=2, column=0, sticky="w")
        ttk.Button(intro, text="Stop all services", style="Danger.TButton", command=self.stop_all).grid(row=2, column=0, sticky="w", padx=(145, 0))
        ttk.Button(intro, text="Open Web Dashboard", style="Secondary.TButton", command=lambda: open_url("http://127.0.0.1:5173")).grid(row=2, column=0, sticky="w", padx=(275, 0))
        metrics = ttk.Frame(self.overview)
        metrics.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        for i in range(3): metrics.columnconfigure(i, weight=1)
        self.metric_vars = {k: tk.StringVar(value="0") for k in ("active", "core", "workers")}
        for i, (key, label) in enumerate((("active", "ACTIVE PROCESSES"), ("core", "CORE SERVICES"), ("workers", "WORKER PROCESSES"))):
            p = self._panel(metrics, 16)
            p.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            ttk.Label(p, text=label, style="MetricLabel.TLabel").pack(anchor="w")
            ttk.Label(p, textvariable=self.metric_vars[key], style="MetricValue.TLabel").pack(anchor="w", pady=(6, 0))
        quick = self._panel(self.overview, 18)
        quick.grid(row=2, column=0, sticky="nsew", padx=(0, 7))
        quick.rowconfigure(1, weight=1)
        quick.columnconfigure(0, weight=1)
        ttk.Label(quick, text="Service summary", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.summary_tree = ttk.Treeview(quick, columns=("service", "group", "status"), show="headings", selectmode="browse")
        for col, text, width in (("service", "SERVICE", 190), ("group", "GROUP", 120), ("status", "STATUS", 90)):
            self.summary_tree.heading(col, text=text)
            self.summary_tree.column(col, width=width, anchor="w")
        self.summary_tree.grid(row=1, column=0, sticky="nsew")
        self.summary_tree.bind("<Double-1>", lambda _: self._show_view("services"))
        help_panel = self._panel(self.overview, 18)
        help_panel.grid(row=2, column=1, sticky="nsew", padx=(7, 0))
        ttk.Label(help_panel, text="Operating guidance", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(help_panel, text="Recommended workflow", background=self.C["white"], foreground=self.C["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(18, 4))
        ttk.Label(help_panel, text="1. Select a resource profile.\n2. Start the system stack.\n3. Open the dashboard when services are online.\n4. Use Activity to investigate output or failures.", style="PanelText.TLabel", justify="left", wraplength=260).pack(anchor="w")
        ttk.Label(help_panel, text="The console does not hide failures: every process exit and startup error is recorded in Activity.", style="PanelText.TLabel", justify="left", wraplength=260).pack(anchor="w", pady=(18, 0))

    def _build_service_view(self) -> None:
        self.services_view = ttk.Frame(self.content)
        self.services_view.columnconfigure(0, weight=3)
        self.services_view.columnconfigure(1, weight=2)
        self.services_view.rowconfigure(1, weight=1)
        ttk.Label(self.services_view, text="Choose a service to view its purpose, command, and controls.", foreground=self.C["muted"], background=self.C["window"], font=("Segoe UI", 9)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        table_panel = self._panel(self.services_view, 14)
        table_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        table_panel.rowconfigure(0, weight=1)
        table_panel.columnconfigure(0, weight=1)
        self.service_tree = ttk.Treeview(table_panel, columns=("service", "group", "entry", "status"), show="headings", selectmode="browse")
        for col, text, width in (("service", "SERVICE", 185), ("group", "GROUP", 105), ("entry", "ENTRYPOINT", 170), ("status", "STATUS", 90)):
            self.service_tree.heading(col, text=text)
            self.service_tree.column(col, width=width, anchor="w")
        self.service_tree.grid(row=0, column=0, sticky="nsew")
        self.service_tree.bind("<<TreeviewSelect>>", self._tree_selected)
        scroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.service_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.service_tree.configure(yscrollcommand=scroll.set)
        self.detail_panel = self._panel(self.services_view, 22)
        self.detail_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        self.detail_panel.columnconfigure(0, weight=1)
        self.detail_name = ttk.Label(self.detail_panel, text="", style="PanelTitle.TLabel")
        self.detail_name.grid(row=0, column=0, sticky="w")
        self.detail_status = ttk.Label(self.detail_panel, text="", background=self.C["white"], foreground=self.C["muted"], font=("Segoe UI", 9, "bold"))
        self.detail_status.grid(row=1, column=0, sticky="w", pady=(5, 17))
        self.detail_text = ttk.Label(self.detail_panel, text="", style="PanelText.TLabel", wraplength=300, justify="left")
        self.detail_text.grid(row=2, column=0, sticky="w")
        ttk.Separator(self.detail_panel).grid(row=3, column=0, sticky="ew", pady=20)
        ttk.Label(self.detail_panel, text="COMMAND", style="MetricLabel.TLabel").grid(row=4, column=0, sticky="w")
        self.detail_command = ttk.Label(self.detail_panel, text="", style="PanelText.TLabel", wraplength=300, justify="left")
        self.detail_command.grid(row=5, column=0, sticky="w", pady=(5, 0))
        self.detail_start = ttk.Button(self.detail_panel, text="Start service", style="Primary.TButton", command=lambda: self._action_selected("start"))
        self.detail_start.grid(row=6, column=0, sticky="w", pady=(24, 0))
        self.detail_stop = ttk.Button(self.detail_panel, text="Stop service", style="Danger.TButton", command=lambda: self._action_selected("stop"), state="disabled")
        self.detail_stop.grid(row=7, column=0, sticky="w", pady=(8, 0))
        self.detail_open = ttk.Button(self.detail_panel, text="Open endpoint", style="Secondary.TButton", command=self._open_selected)
        self.detail_open.grid(row=8, column=0, sticky="w", pady=(8, 0))

    def _build_activity_view(self) -> None:
        self.activity_view = ttk.Frame(self.content)
        self.activity_view.rowconfigure(1, weight=1)
        self.activity_view.columnconfigure(0, weight=1)
        toolbar = self._panel(self.activity_view, 12)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(toolbar, text="Filter messages", style="PanelText.TLabel").pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.log_filter, values=("All messages", "System", "Error", "Backend", "Dashboard", "Collector", "Simulator", "Pipeline", "Trainer"), state="readonly", width=15).pack(side="left", padx=(10, 0))
        ttk.Button(toolbar, text="Clear activity", style="Secondary.TButton", command=self._clear_activity).pack(side="right")
        panel = self._panel(self.activity_view, 12)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        self.console = tk.Text(panel, background=self.C["console"], foreground=self.C["console_text"], insertbackground=self.C["white"], relief="flat", wrap="word", padx=14, pady=14, font=("Consolas", 9))
        self.console.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(panel, orient="vertical", command=self.console.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=scroll.set)
        for tag, colour in (("System", "#8BC7FF"), ("Error", "#FF9A9A"), ("Backend", "#83D6D0"), ("Dashboard", "#B1C7FF"), ("Collector", "#F5CF81"), ("Simulator", "#D3B0F5"), ("Pipeline", "#F5A9C0"), ("Trainer", "#F2BC9A")):
            self.console.tag_configure(tag, foreground=colour)

    def _show_view(self, key: str) -> None:
        for view in (self.overview, self.services_view, self.activity_view):
            view.grid_remove()
        view, title = {"overview": (self.overview, "Overview"), "services": (self.services_view, "Services"), "activity": (self.activity_view, "Activity")} [key]
        view.grid(row=1, column=0, sticky="nsew")
        self.page_title.configure(text=title)
        for name, button in self.nav_buttons.items():
            button.configure(background=self.C["nav_active"] if name == key else self.C["nav"])

    def _select_service(self, key: str) -> None:
        self.selected_key = key
        if hasattr(self, "service_tree") and self.service_tree.exists(key):
            self.service_tree.selection_set(key)
            self.service_tree.focus(key)
        self._update_detail()

    def _tree_selected(self, _event=None) -> None:
        selected = self.service_tree.selection()
        if selected:
            self.selected_key = selected[0]
            self._update_detail()

    def _selected(self) -> Optional[Service]:
        return next((s for s in self.services if s.key == self.selected_key), None)

    def _update_detail(self) -> None:
        service = self._selected()
        if not service: return
        self.detail_name.configure(text=service.name)
        self.detail_text.configure(text=service.purpose)
        self.detail_command.configure(text=" ".join(service.command))
        running = self._running(service.key)
        self.detail_status.configure(text="ONLINE" if running else "OFFLINE", foreground=self.C["green"] if running else self.C["muted"])
        self.detail_start.configure(state="disabled" if running else "normal")
        self.detail_stop.configure(state="normal" if running else "disabled")
        self.detail_open.configure(state="normal" if service.url else "disabled")

    def _action_selected(self, action: str) -> None:
        if self.selected_key:
            (self.start_service if action == "start" else self.stop_service)(self.selected_key)

    def _open_selected(self) -> None:
        service = self._selected()
        if service and service.url:
            open_url(service.url)

    def _thread_count(self) -> int:
        if self.resource_mode.get() == "Eco": return max(1, CPU_CORES // 4)
        if self.resource_mode.get() == "Turbo": return CPU_CORES
        return max(1, CPU_CORES // 2)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PORT"] = "5173"
        for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "CPU_ALLOCATION_THREADS"):
            env[name] = str(self._thread_count())
        return env

    def start_service(self, key: str) -> None:
        service = next(s for s in self.services if s.key == key)
        if self._running(key):
            self._log(f"{service.name} is already running.", "System")
            return
        if not service.cwd.exists():
            self._log(f"Cannot start {service.name}; working directory does not exist: {service.cwd}", "Error")
            return
        self._log(f"Starting {service.name} using the {self.resource_mode.get().lower()} profile.", "System")

        def worker() -> None:
            while not self.shutting_down:
                try:
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                    cmd = list(service.command)
                    if os.name == "nt":
                        resolved = shutil.which(cmd[0]) or cmd[0]
                        if not resolved.lower().endswith(".exe"):
                            cmd = ["cmd.exe", "/c"] + cmd
                        else:
                            cmd[0] = resolved
                    proc = subprocess.Popen(cmd, cwd=service.cwd, env=self._env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=flags)
                    with self.process_lock: self.processes[key] = proc
                    assert proc.stdout is not None
                    for line in proc.stdout: self._log(line.rstrip(), service.name.split()[0])
                    code = proc.wait()
                    self._log(f"{service.name} exited with code {code}.", "System" if code == 0 else "Error")
                except Exception as exc:
                    self._log(f"Failed to start {service.name}: {exc}", "Error")
                finally:
                    with self.process_lock: self.processes[key] = None

                if not self.shutting_down and key in ("backend", "dashboard") and ("--autostart" in sys.argv or "-a" in sys.argv):
                    self._log(f"Keep-Alive: Automatically restarting {service.name} hosting...", "System")
                    time.sleep(2)
                else:
                    break

        threading.Thread(target=worker, daemon=True).start()


    def stop_service(self, key: str) -> None:
        service = next(s for s in self.services if s.key == key)
        with self.process_lock: proc = self.processes.get(key)
        if not proc or proc.poll() is not None:
            self._log(f"{service.name} is not running.", "System")
            return
        self._log(f"Stopping {service.name}…", "System")
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM)
            threading.Thread(target=self._wait_for_stop, args=(proc, service.name), daemon=True).start()
        except Exception as exc:
            self._log(f"Could not stop {service.name}: {exc}", "Error")

    def _wait_for_stop(self, proc: subprocess.Popen[str], name: str) -> None:
        try: proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill(); self._log(f"{name} did not exit gracefully and was terminated.", "Error")

    def _open_browser_when_ready(self, url: str, attempts: int = 30) -> None:
        def check():
            import urllib.request
            for _ in range(attempts):
                if self.shutting_down:
                    return
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "ConsoleLauncher/1.0"})
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        if resp.status == 200:
                            self._log(f"Web Dashboard ready. Opening {url}...", "System")
                            open_url(url)
                            return
                except Exception:
                    time.sleep(0.5)
            open_url(url)
        threading.Thread(target=check, daemon=True).start()

    def start_demo(self) -> None:
        self.start_service("backend")
        self.start_service("dashboard")
        self.root.after(1200, lambda: self.start_service("simulator"))
        self._open_browser_when_ready("http://127.0.0.1:5173")



    def stop_all(self) -> None:
        active = [s for s in self.services if self._running(s.key)]
        if not active:
            self._log("No services are currently running.", "System"); return
        if messagebox.askyesno("Stop all services", f"Stop {len(active)} active service(s)?"):
            for service in active: self.stop_service(service.key)

    def _running(self, key: str) -> bool:
        with self.process_lock:
            proc = self.processes.get(key)
            return bool(proc and proc.poll() is None)

    def _log(self, message: str, tag: str) -> None:
        self.log_queue.put((tag, message))

    def _drain_logs(self) -> None:
        while True:
            try: tag, message = self.log_queue.get_nowait()
            except queue.Empty: break
            self.log_records.append((tag, message))
            if self.log_filter.get() == "All messages" or self.log_filter.get().lower() == tag.lower():
                self.console.insert("end", f"[{tag.upper():<10}] {message}\n", tag if tag in self.console.tag_names() else "System")
                self.console.see("end")
        if len(self.log_records) > MAX_LOG_LINES: self.log_records = self.log_records[-MAX_LOG_LINES:]
        self.root.after(200, self._drain_logs)

    def _clear_activity(self) -> None:
        self.log_records.clear(); self.console.delete("1.0", "end")

    def _refresh_state(self) -> None:
        active = core = workers = 0
        if hasattr(self, "service_tree"):
            for service in self.services:
                running = self._running(service.key)
                status = "Online" if running else "Offline"
                values = (service.name, service.group, service.entrypoint, status)
                if self.service_tree.exists(service.key): self.service_tree.item(service.key, values=values)
                else: self.service_tree.insert("", "end", iid=service.key, values=values)
                if running:
                    active += 1
                    if service.group == "Core services": core += 1
                    else: workers += 1
            if hasattr(self, "summary_tree"):
                for item in self.summary_tree.get_children(): self.summary_tree.delete(item)
                for service in self.services: self.summary_tree.insert("", "end", values=(service.name, service.group, "Online" if self._running(service.key) else "Offline"))
        self.metric_vars["active"].set(str(active)); self.metric_vars["core"].set(str(core)); self.metric_vars["workers"].set(str(workers))
        self.system_state.configure(text="SYSTEM ACTIVE" if active else "SYSTEM IDLE", foreground=self.C["green"] if active else self.C["muted"])
        self._update_detail()
        self.root.after(800, self._refresh_state)

    def _close(self) -> None:
        if self.shutting_down: return
        active = [s.name for s in self.services if self._running(s.key)]
        if active and not messagebox.askyesno("Exit Operations", "Active services are running. Stop them and exit?"): return
        self.shutting_down = True
        for service in self.services:
            if self._running(service.key): self.stop_service(service.key)
        self.root.after(300, self.root.destroy)


def main() -> None:
    root = tk.Tk()
    app = OperationsConsole(root)
    app._show_view("overview")
    root.mainloop()


if __name__ == "__main__":
    main()
