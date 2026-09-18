"""Indoor Positioning — Standalone Model Trainer GUI.

A focused, modular Python application for dataset inspection, feature engineering,
model training, hyperparameter tuning, and comprehensive evaluation.
Delegates dataset inspection to DatasetInspector and deliberate promotion to ModelExporter.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
import tkinter as tk
from PIL import Image, ImageTk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import DATASETS_DIR, MODELS_DIR, REPORTS_DIR, PYTHON_EXE
from core.inference import load_distance_model
from training.dataset_inspector import DatasetInspector
from training.model_exporter import ModelExporter


class ModelTrainerApp:
    """Dedicated desktop GUI for ML dataset preparation, training, and evaluation."""

    THEME = {
        "bg": "#121214",          # Deep Zinc
        "panel": "#18181B",       # Zinc 900
        "card": "#27272A",        # Zinc 800
        "card_hover": "#323238",  # Zinc 750
        "border": "#3F3F46",      # Zinc 700
        "text": "#FAFAFA",        # Zinc 50
        "subtext": "#A1A1AA",     # Zinc 400
        "accent": "#E4E4E7",      # Crisp neutral Zinc 200
        "accent_hover": "#D4D4D8",
        "green": "#10B981",       # Emerald 500
        "yellow": "#F59E0B",      # Amber 500
        "red": "#EF4444",         # Rose 500
        "terminal_bg": "#0E0E10", # Deep terminal Zinc
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("🧠 BLE RTLS — Model Studio & Trainer")
        self.root.geometry("1220x860")
        self.root.minsize(1040, 720)
        self.root.configure(bg=self.THEME["bg"])

        # State variables
        self.dataset_path_var = tk.StringVar(value=str(DATASETS_DIR / "observations.csv"))
        self.eval_mode_var = tk.StringVar(value="balanced_session")
        self.training_mode_var = tk.StringVar(value="both")
        self.tune_var = tk.BooleanVar(value=False)
        self.drop_duplicates_var = tk.BooleanVar(value=True)

        self.is_training = False
        self.pipeline_proc: Optional[subprocess.Popen] = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.metadata: Optional[dict] = None
        self.plot_photos: dict = {}

        self._configure_styles()
        self._build_ui()

        self.root.after(100, self._process_log_queue)
        self.root.after(200, self.refresh_dashboard)

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
        # Top Header
        header = tk.Frame(self.root, bg=self.THEME["panel"], height=56)
        header.pack(fill="x", side="top")

        title_box = tk.Frame(header, bg=self.THEME["panel"])
        title_box.pack(side="left", padx=20, pady=10)

        tk.Label(title_box, text="🧠 AI MODEL STUDIO & TRAINER", bg=self.THEME["panel"], fg=self.THEME["text"], font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(title_box, text="· Super Learner & Zone Classifier Tournament", bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 9)).pack(side="left", padx=10)

        self.status_pill = tk.Label(header, text="○ READY", bg=self.THEME["card"], fg=self.THEME["green"], font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.status_pill.pack(side="right", padx=20, pady=12)

        # Notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        # Tab 1: Dataset & Training Controls
        self.tab_train = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_train, text="⚡ Dataset & Training Pipeline")
        self._build_training_tab(self.tab_train)

        # Tab 2: Evaluation & Leaderboard
        self.tab_eval = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_eval, text="📊 Evaluation & Leaderboard")
        self._build_eval_tab(self.tab_eval)

        # Tab 3: Diagnostic Visualizations
        self.tab_plots = tk.Frame(self.notebook, bg=self.THEME["bg"])
        self.notebook.add(self.tab_plots, text="🖼️ Diagnostic Visualizations")
        self._build_plots_tab(self.tab_plots)

    def _build_training_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        split = tk.Frame(p, bg=t["bg"])
        split.pack(fill="both", expand=True)

        # Left Column: Configuration & Actions
        left = tk.Frame(split, bg=t["panel"], width=460)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="DATASET & FEATURE PIPELINE", bg=t["panel"], fg=t["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

        form = tk.Frame(left, bg=t["panel"])
        form.pack(fill="x", padx=16)

        # Dataset Path
        tk.Label(form, text="Observations Dataset (CSV)", bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(4, 2))
        path_box = tk.Frame(form, bg=t["panel"])
        path_box.pack(fill="x")
        ttk.Entry(path_box, textvariable=self.dataset_path_var).pack(side="left", fill="x", expand=True)
        tk.Button(path_box, text="Browse", bg=t["card"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._browse_dataset).pack(side="right", padx=(4, 0))

        # Split Strategy
        tk.Label(form, text="Evaluation Split Mode", bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(8, 2))
        ttk.Combobox(form, textvariable=self.eval_mode_var, values=["balanced_session", "strict_session", "random"], state="readonly").pack(fill="x")

        # Training Scope
        tk.Label(form, text="Training Scope", bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(8, 2))
        ttk.Combobox(form, textvariable=self.training_mode_var, values=["both", "regression", "classification"], state="readonly").pack(fill="x")

        # Options
        tk.Label(form, text="Optimization Options", bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(10, 2))
        tk.Checkbutton(form, text="Run Hyperparameter Tuning (Grid/Bayesian)", variable=self.tune_var, bg=t["panel"], fg=t["text"], selectcolor=t["card"], activebackground=t["panel"], activeforeground=t["text"]).pack(anchor="w")
        tk.Checkbutton(form, text="Drop Duplicate Sensor Packets", variable=self.drop_duplicates_var, bg=t["panel"], fg=t["text"], selectcolor=t["card"], activebackground=t["panel"], activeforeground=t["text"]).pack(anchor="w")

        # Big Train Button
        self.btn_run_train = tk.Button(
            left, text="🚀  RUN END-TO-END ML PIPELINE",
            bg=t["green"], fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", padx=16, pady=10,
            command=self.run_pipeline,
        )
        self.btn_run_train.pack(fill="x", padx=16, pady=(20, 10))

        # Dataset Audit Card
        audit_frame = tk.Frame(left, bg=t["card"], padx=12, pady=10)
        audit_frame.pack(fill="x", padx=16, pady=(10, 16))

        tk.Label(audit_frame, text="DATASET HEALTH AUDIT", bg=t["card"], fg=t["yellow"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.audit_lbl = tk.Label(audit_frame, text="Scanning observations...", bg=t["card"], fg=t["subtext"], font=("Consolas", 8), justify="left")
        self.audit_lbl.pack(anchor="w", pady=(4, 0))

        # Right Column: Console Log & Live Progress
        right = tk.Frame(split, bg=t["panel"], padx=16, pady=14)
        right.pack(side="right", fill="both", expand=True)

        tk.Label(right, text="TRAINING PIPELINE CONSOLE", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.progress_bar = ttk.Progressbar(right, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(8, 10))

        self.log_text = tk.Text(right, bg=t["terminal_bg"], fg=t["text"], font=("Consolas", 9), relief="flat", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _build_eval_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        # Toolbar
        toolbar = tk.Frame(p, bg=t["panel"], padx=14, pady=10)
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(toolbar, text="MODEL PERFORMANCE & TOURNAMENT METRICS", bg=t["panel"], fg=t["text"], font=("Segoe UI", 10, "bold")).pack(side="left")

        # Explicit Model Promotion / Export Action Button
        tk.Button(toolbar, text="💾 Export to Production", bg=t["accent"], fg="#121214", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=10, pady=4, command=self._export_to_production).pack(side="right", padx=4)
        tk.Button(toolbar, text="🔄 Refresh Metrics", bg=t["card"], fg=t["text"], font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=10, pady=4, command=self.refresh_dashboard).pack(side="right", padx=4)
        tk.Button(toolbar, text="📋 Copy Summary", bg=t["card"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=10, pady=4, command=self._copy_summary).pack(side="right", padx=4)

        # KPI Row
        kpi_row = tk.Frame(p, bg=t["bg"])
        kpi_row.pack(fill="x", pady=(0, 10))
        for col in range(5):
            kpi_row.columnconfigure(col, weight=1, uniform="kpi")

        self.kpi_champ = self._create_kpi_box(kpi_row, 0, "CHAMPION MODEL", "--", t["accent"])
        self.kpi_mae = self._create_kpi_box(kpi_row, 1, "TEST MAE", "-- m", t["green"])
        self.kpi_r2 = self._create_kpi_box(kpi_row, 2, "GOODNESS OF FIT (R²)", "--", t["yellow"])
        self.kpi_rmse = self._create_kpi_box(kpi_row, 3, "RMSE / MAX ERR", "-- m", t["subtext"])
        self.kpi_zone = self._create_kpi_box(kpi_row, 4, "ZONE ACCURACY", "-- %", t["green"])

        # Split lower half: Leaderboard & Per-distance breakdown
        lower = tk.Frame(p, bg=t["bg"])
        lower.pack(fill="both", expand=True)

        # Tournament Leaderboard
        lead_frame = tk.Frame(lower, bg=t["panel"], padx=12, pady=10)
        lead_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(lead_frame, text="🏆 SUPER LEARNER TOURNAMENT LEADERBOARD", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        cols = ("rank", "name", "mae", "rmse", "r2", "score")
        self.tourn_tree = ttk.Treeview(lead_frame, columns=cols, show="headings", height=10)
        self.tourn_tree.heading("rank", text="Rank")
        self.tourn_tree.heading("name", text="Algorithm")
        self.tourn_tree.heading("mae", text="Test MAE")
        self.tourn_tree.heading("rmse", text="RMSE")
        self.tourn_tree.heading("r2", text="R² Score")
        self.tourn_tree.heading("score", text="Composite Score")

        self.tourn_tree.column("rank", width=60, anchor="center")
        self.tourn_tree.column("name", width=180, anchor="w")
        self.tourn_tree.column("mae", width=80, anchor="center")
        self.tourn_tree.column("rmse", width=80, anchor="center")
        self.tourn_tree.column("r2", width=80, anchor="center")
        self.tourn_tree.column("score", width=100, anchor="center")

        self.tourn_tree.pack(fill="both", expand=True, pady=(6, 0))

        # Per Distance Breakdown
        dist_frame = tk.Frame(lower, bg=t["panel"], padx=12, pady=10)
        dist_frame.pack(side="right", fill="both", expand=True, padx=(6, 0))

        tk.Label(dist_frame, text="🎯 PER-DISTANCE ACCURACY BREAKDOWN", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w")

        dist_cols = ("dist", "mae", "rating")
        self.dist_tree = ttk.Treeview(dist_frame, columns=dist_cols, show="headings", height=10)
        self.dist_tree.heading("dist", text="True Distance")
        self.dist_tree.heading("mae", text="Mean Absolute Error")
        self.dist_tree.heading("rating", text="Rating")

        self.dist_tree.column("dist", width=90, anchor="center")
        self.dist_tree.column("mae", width=130, anchor="center")
        self.dist_tree.column("rating", width=160, anchor="w")

        self.dist_tree.pack(fill="both", expand=True, pady=(6, 0))

    def _build_plots_tab(self, parent: tk.Frame) -> None:
        p = parent
        t = self.THEME

        toolbar = tk.Frame(p, bg=t["panel"], padx=14, pady=8)
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(toolbar, text="DIAGNOSTIC PLOTS VIEWER", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(toolbar, text="📂 Open Reports Folder", bg=t["card"], fg=t["text"], font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._open_reports_folder).pack(side="right")

        self.plot_label = tk.Label(p, bg=t["panel"], text="Diagnostic plot loading...", fg=t["subtext"])
        self.plot_label.pack(fill="both", expand=True)

    def _create_kpi_box(self, parent: tk.Frame, col: int, title: str, init_val: str, color: str) -> tk.Label:
        box = tk.Frame(parent, bg=self.THEME["panel"], padx=12, pady=10)
        box.grid(row=0, column=col, sticky="nsew", padx=2)

        tk.Label(box, text=title, bg=self.THEME["panel"], fg=self.THEME["subtext"], font=("Segoe UI", 7, "bold")).pack(anchor="w")
        lbl = tk.Label(box, text=init_val, bg=self.THEME["panel"], fg=color, font=("Segoe UI", 12, "bold"))
        lbl.pack(anchor="w", pady=(3, 0))
        return lbl

    def _browse_dataset(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Dataset CSV",
            initialdir=str(DATASETS_DIR),
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if path:
            self.dataset_path_var.set(path)
            self._audit_dataset()

    def _audit_dataset(self) -> None:
        path = Path(self.dataset_path_var.get())
        is_valid, msg, stats = DatasetInspector.inspect(path)
        if is_valid:
            txt = (
                f"✔ Dataset Valid\n"
                f"Observations: {stats.get('rows', 0):,} rows\n"
                f"Features: {stats.get('columns', 0)} cols\n"
                f"Distances: {stats.get('distances', [])}"
            )
            self.audit_lbl.config(text=txt, fg=self.THEME["green"])
        else:
            self.audit_lbl.config(text=f"⚠ {msg}", fg=self.THEME["yellow"])

    def run_pipeline(self) -> None:
        if self.is_training:
            messagebox.showwarning("Training in Progress", "The ML training pipeline is already running.")
            return

        cmd = [
            PYTHON_EXE,
            str(PROJECT_ROOT / "pipeline.py"),
            "--eval-mode", self.eval_mode_var.get(),
            "--mode", self.training_mode_var.get(),
        ]
        if self.tune_var.get():
            cmd.append("--tune")
        if self.drop_duplicates_var.get():
            cmd.append("--drop-duplicates")

        self.is_training = True
        self.btn_run_train.config(text="⏳ TRAINING IN PROGRESS...", state="disabled", bg=self.THEME["card"])
        self.status_pill.config(text="● TRAINING", fg=self.THEME["yellow"])
        self.progress_bar["value"] = 10
        self.log_text.delete("1.0", "end")

        def run_proc():
            try:
                proc = subprocess.Popen(
                    cmd, cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                self.pipeline_proc = proc
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    self.log_queue.put(line)
                proc.wait()
                self.log_queue.put("__DONE__")
            except Exception as e:
                self.log_queue.put(f"[ERROR] Pipeline launch failed: {e}\n")
                self.log_queue.put("__DONE__")

        threading.Thread(target=run_proc, daemon=True).start()

    def _process_log_queue(self) -> None:
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            if line == "__DONE__":
                self.is_training = False
                self.btn_run_train.config(text="🚀  RUN END-TO-END ML PIPELINE", state="normal", bg=self.THEME["accent"])
                self.status_pill.config(text="✔ COMPLETED", fg=self.THEME["green"])
                self.progress_bar["value"] = 100
                self.refresh_dashboard()
                continue

            if line.strip().startswith("{") and line.strip().endswith("}"):
                try:
                    data = json.loads(line)
                    if data.get("type") == "progress":
                        pct = data.get("percent", 0)
                        self.progress_bar["value"] = pct
                        stage = data.get("stage", "")
                        self.log_text.insert("end", f"[{pct}%] {stage}\n")
                        self.log_text.see("end")
                        continue
                except Exception:
                    pass

            self.log_text.insert("end", line)
            self.log_text.see("end")

        self.root.after(100, self._process_log_queue)

    def refresh_dashboard(self) -> None:
        self._audit_dataset()
        meta_path = MODELS_DIR / "model_metadata.json"
        if not meta_path.exists():
            return

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        except Exception:
            return

        meta = self.metadata or {}
        metrics = meta.get("metrics", {})
        champ = meta.get("champion_model", "Trained ML Model")
        test_mae = metrics.get("test_mae", 0.0)
        test_r2 = metrics.get("test_r2", 0.0)
        test_rmse = metrics.get("test_rmse", 0.0)
        zone_meta = meta.get("zone_classification", {})

        self.kpi_champ.config(text=f"{champ}")
        self.kpi_mae.config(text=f"{test_mae:.4f} m" if isinstance(test_mae, (int, float)) else "--")
        self.kpi_r2.config(text=f"{test_r2:.4f}" if isinstance(test_r2, (int, float)) else "--")
        self.kpi_rmse.config(text=f"{test_rmse:.4f} m" if isinstance(test_rmse, (int, float)) else "--")

        z_acc = zone_meta.get("zone_accuracy", 0.0)
        self.kpi_zone.config(text=f"{z_acc:.1f}%" if isinstance(z_acc, (int, float)) else "--")

        for item in self.tourn_tree.get_children():
            self.tourn_tree.delete(item)
        tourn = meta.get("tournament", [])
        for idx, m in enumerate(tourn, 1):
            rank = f"🏆 #{idx}" if idx == 1 else f"#{idx}"
            self.tourn_tree.insert("", "end", values=(
                rank,
                m.get("name", "Model"),
                f"{m.get('mae', 0.0):.4f}",
                f"{m.get('rmse', 0.0):.4f}",
                f"{m.get('r2', 0.0):.4f}",
                f"{m.get('composite_score', 0.0):.3f}" if "composite_score" in m else "--",
            ))

        for item in self.dist_tree.get_children():
            self.dist_tree.delete(item)
        ext = metrics.get("extended", {})
        per_dist = ext.get("per_distance_mae", {})
        for dist_str, mae_val in sorted(per_dist.items()):
            rating = "🟢 Precision (<0.3m)" if mae_val < 0.3 else "🟡 Good (<0.8m)" if mae_val < 0.8 else "🟠 Fair (<1.5m)"
            self.dist_tree.insert("", "end", values=(dist_str, f"{mae_val:.4f} m", rating))

        plot_path = REPORTS_DIR / "model_diagnostics.png"
        if plot_path.exists():
            try:
                img = Image.open(plot_path)
                img.thumbnail((860, 520), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.plot_photos["diag"] = photo
                self.plot_label.config(image=photo, text="")
            except Exception as e:
                self.plot_label.config(text=f"Failed to load diagnostic plot: {e}")

    def _export_to_production(self) -> None:
        """Explicitly promote evaluated candidate model to production with version tag."""
        if not self.metadata:
            messagebox.showwarning("No Model Found", "No evaluated candidate model is loaded to export.")
            return

        version = simpledialog.askstring("Model Versioning", "Enter a version tag for this production release:", initialvalue=f"v_{datetime.now().strftime('%Y%m%d')}")
        if not version:
            return

        model, scaler, _ = load_distance_model(MODELS_DIR)
        if not model or not scaler:
            messagebox.showerror("Export Failed", "Could not load candidate model artifacts from disk.")
            return

        ok, msg, _ = ModelExporter.export_champion_model(
            candidate_model=model,
            candidate_scaler=scaler,
            metadata=self.metadata,
            version_tag=version,
        )
        if ok:
            messagebox.showinfo("Export Successful", msg)
        else:
            messagebox.showerror("Export Error", msg)

    def _copy_summary(self) -> None:
        if not self.metadata:
            return
        meta = self.metadata
        metrics = meta.get("metrics", {})
        summary = (
            f"BLE Indoor Positioning — Model Results Summary\n"
            f"Champion Model: {meta.get('champion_model')}\n"
            f"Test MAE: {metrics.get('test_mae', 0.0):.4f} m\n"
            f"RMSE: {metrics.get('test_rmse', 0.0):.4f} m\n"
            f"R2 Score: {metrics.get('test_r2', 0.0):.4f}\n"
            f"Trained At: {meta.get('trained_at', datetime.now().isoformat())}\n"
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(summary)
        messagebox.showinfo("Copied", "Model evaluation summary copied to clipboard.")

    def _open_reports_folder(self) -> None:
        if os.name == "nt":
            os.startfile(str(REPORTS_DIR))
        else:
            subprocess.Popen(["xdg-open", str(REPORTS_DIR)])


def main() -> None:
    root = tk.Tk()
    app = ModelTrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
