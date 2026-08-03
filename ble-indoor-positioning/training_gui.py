
import os
import sys
import glob
import json
import time
import threading
import queue
import subprocess
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR
RAW_DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "ble tracker", "collector", "data", "raw"))
DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "observations.csv")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
DIAGNOSTIC_PLOT_PATH = os.path.join(REPORTS_DIR, "model_diagnostics.png")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# Target distances expected for full coverage
TARGET_DISTANCES = [0.5, 1.0, 2.0, 3.0, 5.0]

# Add module paths
sys.path.insert(0, PROJECT_ROOT)


def build_simulated_feature_dict(rssi_val, height_m=1.0):
    """Builds a full dictionary of simulated signal features derived from a given RSSI value."""
    n = 2.5
    d_free = 10 ** ((-40.0 - rssi_val) / (10.0 * 2.0))
    d_indoor = 10 ** ((-60.0 - rssi_val) / (10.0 * n))

    return {
        "packet_count": 10.0,
        "scan_duration_ms": 1000.0,
        "rssi_mean": float(rssi_val),
        "rssi_median": float(rssi_val),
        "rssi_min": float(rssi_val) - 2.0,
        "rssi_max": float(rssi_val) + 2.0,
        "rssi_std": 1.5,
        "rssi_variance": 2.25,
        "rssi_range": 4.0,
        "rssi_p05": float(rssi_val) - 2.5,
        "rssi_p10": float(rssi_val) - 2.0,
        "rssi_p25": float(rssi_val) - 1.0,
        "rssi_p75": float(rssi_val) + 1.0,
        "rssi_p90": float(rssi_val) + 2.0,
        "rssi_p95": float(rssi_val) + 2.5,
        "rssi_iqr": 2.0,
        "rssi_p90_10_range": 4.0,
        "rssi_mad": 1.2,
        "rssi_snr": abs(rssi_val) / 1.5,
        "rssi_skewness": 0.0,
        "rssi_kurtosis": 0.0,
        "rssi_delta_mean": 0.0,
        "rssi_delta_std": 0.5,
        "rssi_delta_max": 1.0,
        "observed_adv_interval": 100.0,
        "adv_interval_std": 5.0,
        "path_loss_free_space": d_free,
        "path_loss_indoor": d_indoor,
        "rssi_mean_to_std_ratio": abs(rssi_val) / 1.5,
        "rssi_median_mean_diff": 0.0,
        "rssi_slope": 0.0,
        "rssi_trend_strength": 0.0,
        "rssi_ema_diff": 0.0,
        "rssi_first_half_mean": float(rssi_val),
        "rssi_second_half_mean": float(rssi_val),
        "rssi_half_diff": 0.0,
        "rssi_autocorrelation": 0.5,
        "rssi_energy": float(rssi_val) ** 2,
        "rssi_mean_delta": 0.0,
        "rssi_mean_slope_3w": 0.0,
        "rssi_mean_slope_5w": 0.0,
        "rssi_rolling_mean_3w": float(rssi_val),
        "rssi_rolling_std_3w": 1.5,
        "rssi_rolling_mean_5w": float(rssi_val),
        "rssi_rolling_std_5w": 1.5,
        "rssi_ema_cross_window": float(rssi_val),
        "rssi_velocity": 0.0,
        "rssi_acceleration": 0.0,
        "signal_stability_index": 1.0 / (1.5 + 1e-3),
        "rssi_rolling_mean_10w": float(rssi_val),
        "rssi_rolling_std_10w": 1.5,
        "rssi_motion_direction": 0.0,
        "rssi_snr_rolling_5w": abs(rssi_val) / 1.5,
        "height_m": float(height_m),
    }


class MLTrainingStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ BLE Tracker — AI Data & Model Training Studio")
        self.root.geometry("1020x820")
        self.root.minsize(920, 720)

        # Threading queue
        self.log_queue = queue.Queue()
        self.is_training = False

        # Apply Modern Dark Theme Colors
        self.colors = {
            "bg": "#1e1e2e",
            "panel": "#181825",
            "card": "#313244",
            "accent": "#89b4fa",
            "green": "#a6e3a1",
            "yellow": "#f9e2af",
            "red": "#f38ba8",
            "purple": "#cba6f7",
            "text": "#cdd6f4",
            "subtext": "#a6adc8",
        }

        # Model Asset State
        self.model = None
        self.scaler = None
        self.metadata = None
        self.zone_model = None

        self.setup_styles()
        self.build_ui()

        # Load trained ML model artifacts
        self.load_trained_model()

        # Start periodic log & status refresh loops
        self.root.after(100, self.process_queue_logs)
        self.auto_refresh_audit()

    def load_trained_model(self):
        """Loads trained ML regression model, scaler, and metadata for live interactive predictions."""
        model_path = os.path.join(MODEL_DIR, "distance_estimator.joblib")
        scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
        meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
        zone_model_path = os.path.join(MODEL_DIR, "zone_classifier.joblib")

        self.model = None
        self.scaler = None
        self.metadata = None
        self.zone_model = None

        if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path):
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

                if os.path.exists(zone_model_path):
                    try:
                        self.zone_model = joblib.load(zone_model_path)
                    except Exception:
                        pass
                return True
            except Exception as e:
                print(f"Error loading trained ML model: {e}")
                return False
        return False

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        self.root.configure(bg=self.colors["bg"])

        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["panel"], foreground=self.colors["text"], padding=[15, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.colors["card"])], foreground=[("selected", self.colors["accent"])])

        style.configure("Card.TFrame", background=self.colors["card"], relief="flat", borderwidth=1)
        style.configure("Panel.TFrame", background=self.colors["panel"])

        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.colors["accent"], background=self.colors["bg"])
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.colors["purple"], background=self.colors["card"])
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.colors["text"], background=self.colors["card"])
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground=self.colors["subtext"], background=self.colors["card"])

        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), background=self.colors["accent"], foreground="#11111b", padding=[15, 10])
        style.map("Primary.TButton", background=[("active", "#b4befe")])

        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["green"], foreground="#11111b", padding=[10, 6])

        style.configure("Treeview", background=self.colors["panel"], foreground=self.colors["text"], fieldbackground=self.colors["panel"], rowheight=28)
        style.configure("Treeview.Heading", background=self.colors["card"], foreground=self.colors["accent"], font=("Segoe UI", 10, "bold"))

        style.configure("TProgressbar", thickness=12, troughcolor=self.colors["panel"], background=self.colors["green"])

    def build_ui(self):
        # Header Banner
        header_frame = ttk.Frame(self.root, padding=(20, 15))
        header_frame.pack(fill="x")

        ttk.Label(header_frame, text="⚡ BLE ML Studio & Automated Trainer", style="Header.TLabel").pack(side="left")
        ttk.Label(header_frame, text="End-to-End Feature Engineering & Distance Estimation Pipeline", style="Muted.TLabel").pack(side="right")

        # Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Tab 1: Training & Diagnostics
        self.tab_train = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_train, text="🚀 Model Trainer & Diagnostics")
        self.build_train_tab()

        # Tab 2: Dataset Quality & Audit
        self.tab_audit = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_audit, text="📊 Dataset Audit & Advice")
        self.build_audit_tab()

        # Tab 3: Interactive Predictor
        self.tab_predict = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_predict, text="🎯 Live Model Tester")
        self.build_predict_tab()

    # ──────────────────────────────────────────────────────────────────
    # TAB 1: MODEL TRAINER & DIAGNOSTICS
    # ──────────────────────────────────────────────────────────────────

    def build_train_tab(self):
        # Top Controls & Action Bar
        top_bar = ttk.Frame(self.tab_train, style="Card.TFrame", padding=15)
        top_bar.pack(fill="x", pady=(0, 15))

        btn_box = ttk.Frame(top_bar, style="Card.TFrame")
        btn_box.pack(side="left", fill="x", expand=True)

        self.train_btn = ttk.Button(
            btn_box,
            text="⚡ RUN END-TO-END ML PIPELINE",
            style="Primary.TButton",
            command=self.start_pipeline_thread
        )
        self.train_btn.pack(side="left", padx=(0, 15))

        # Training Mode Dropdown
        mode_frame = ttk.Frame(btn_box, style="Card.TFrame")
        mode_frame.pack(side="left", padx=10)
        ttk.Label(mode_frame, text="Mode:", style="Bold.TLabel").pack(side="left", padx=(0, 5))
        self.mode_var = tk.StringVar(value="both")
        mode_combo = ttk.Combobox(
            mode_frame, textvariable=self.mode_var,
            values=["both", "regression", "classification"],
            state="readonly", width=14
        )
        mode_combo.pack(side="left")

        self.tune_var = tk.BooleanVar(value=False)
        tune_chk = ttk.Checkbutton(
            btn_box,
            text="Enable Hyperparameter Tuning",
            variable=self.tune_var
        )
        tune_chk.pack(side="left", padx=10)

        # Status Summary Metrics
        self.metrics_frame = ttk.Frame(top_bar, style="Card.TFrame")
        self.metrics_frame.pack(side="right")

        self.lbl_mae = ttk.Label(self.metrics_frame, text="MAE: -- m", style="Bold.TLabel", foreground=self.colors["green"])
        self.lbl_mae.pack(side="left", padx=8)

        self.lbl_r2 = ttk.Label(self.metrics_frame, text="R²: --", style="Bold.TLabel", foreground=self.colors["accent"])
        self.lbl_r2.pack(side="left", padx=8)

        self.lbl_zone_acc = ttk.Label(self.metrics_frame, text="Zone: --%", style="Bold.TLabel", foreground=self.colors["purple"])
        self.lbl_zone_acc.pack(side="left", padx=8)

        self.lbl_samples = ttk.Label(self.metrics_frame, text="Windows: --", style="Bold.TLabel", foreground=self.colors["yellow"])
        self.lbl_samples.pack(side="left", padx=8)

        # Progress Bar & Status Text
        progress_box = ttk.Frame(self.tab_train, padding=(0, 5))
        progress_box.pack(fill="x", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_box, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 5))

        self.lbl_status = ttk.Label(progress_box, text="System Ready. Click 'RUN END-TO-END ML PIPELINE' to start.", font=("Segoe UI", 9, "italic"), foreground=self.colors["subtext"])
        self.lbl_status.pack(side="left")

        # Main Split Frame (Log Console | Diagnostics Plot Image)
        split_frame = ttk.Frame(self.tab_train)
        split_frame.pack(fill="both", expand=True)

        # Left: Console Log Output
        left_box = ttk.Frame(split_frame, style="Card.TFrame", padding=10)
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(left_box, text="📋 Pipeline Execution Log", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        self.console_text = tk.Text(
            left_box,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
            height=15
        )
        self.console_text.pack(fill="both", expand=True)

        # Right: Plot Preview Frame
        right_box = ttk.Frame(split_frame, style="Card.TFrame", padding=10)
        right_box.pack(side="right", fill="both", expand=True)

        ttk.Label(right_box, text="📊 Model Accuracy Diagnostics", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        self.plot_canvas = tk.Label(right_box, bg=self.colors["panel"], text="No diagnostics loaded.\nRun pipeline to generate plots.", fg=self.colors["subtext"])
        self.plot_canvas.pack(fill="both", expand=True)

        # Live Model Tournament Leaderboard Panel
        lead_box = ttk.Frame(self.tab_train, style="Card.TFrame", padding=10)
        lead_box.pack(fill="x", pady=(10, 0))

        ttk.Label(lead_box, text="🏆 Super Learner Tournament Live Leaderboard", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        self.model_tree = ttk.Treeview(lead_box, columns=("model", "status", "mae", "rmse", "r2", "cv_mae"), show="headings", height=5)
        self.model_tree.heading("model", text="Candidate Model")
        self.model_tree.heading("status", text="Status")
        self.model_tree.heading("mae", text="Test MAE (m)")
        self.model_tree.heading("rmse", text="RMSE (m)")
        self.model_tree.heading("r2", text="R² Score")
        self.model_tree.heading("cv_mae", text="CV MAE (m)")

        self.model_tree.column("model", width=180, anchor="w")
        self.model_tree.column("status", width=110, anchor="center")
        self.model_tree.column("mae", width=100, anchor="center")
        self.model_tree.column("rmse", width=100, anchor="center")
        self.model_tree.column("r2", width=90, anchor="center")
        self.model_tree.column("cv_mae", width=100, anchor="center")

        self.model_tree.pack(fill="x", expand=True)

        # Load existing plots & metadata if available
        self.load_metadata_summary()
        self.load_plot_image()

    # ──────────────────────────────────────────────────────────────────
    # TAB 2: DATASET AUDIT & ADVICE
    # ──────────────────────────────────────────────────────────────────

    def build_audit_tab(self):
        # Audit Action Header
        top_audit = ttk.Frame(self.tab_audit, padding=(0, 5))
        top_audit.pack(fill="x", pady=(0, 10))

        ttk.Label(top_audit, text="Dataset Health Check & Recommended Actions", style="Header.TLabel").pack(side="left")
        ttk.Button(top_audit, text="🔄 Refresh Audit", command=self.refresh_dataset_audit, style="Success.TButton").pack(side="right")

        # Action Recommendations Panel (Alert Box)
        self.advice_box = ttk.Frame(self.tab_audit, style="Card.TFrame", padding=15)
        self.advice_box.pack(fill="x", pady=(0, 15))

        ttk.Label(self.advice_box, text="💡 Recommended Actions", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 5))

        self.advice_lbl = ttk.Label(self.advice_box, text="Analyzing dataset...", style="Bold.TLabel", wraplength=900)
        self.advice_lbl.pack(anchor="w")

        # Split Details (Coverage Table | Raw Files List)
        audit_split = ttk.Frame(self.tab_audit)
        audit_split.pack(fill="both", expand=True)

        # Left: Distance Coverage Table
        cov_box = ttk.Frame(audit_split, style="Card.TFrame", padding=10)
        cov_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(cov_box, text="🎯 Distance Coverage Status", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))

        self.cov_tree = ttk.Treeview(cov_box, columns=("dist", "samples", "status", "advice"), show="headings", height=8)
        self.cov_tree.heading("dist", text="Distance (m)")
        self.cov_tree.heading("samples", text="Samples (Raw / Windows)")
        self.cov_tree.heading("status", text="Status")
        self.cov_tree.heading("advice", text="Recommendation")

        self.cov_tree.column("dist", width=100, anchor="center")
        self.cov_tree.column("samples", width=160, anchor="center")
        self.cov_tree.column("status", width=120, anchor="center")
        self.cov_tree.column("advice", width=220, anchor="w")

        self.cov_tree.pack(fill="both", expand=True)

        # Right: Raw CSV Files Tree
        raw_box = ttk.Frame(audit_split, style="Card.TFrame", padding=10)
        raw_box.pack(side="right", fill="both", expand=True)

        ttk.Label(raw_box, text="📁 Raw Dataset CSV Files", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))

        self.file_tree = ttk.Treeview(raw_box, columns=("filename", "size", "distance", "records"), show="headings", height=8)
        self.file_tree.heading("filename", text="CSV File")
        self.file_tree.heading("size", text="Size")
        self.file_tree.heading("distance", text="Distance")
        self.file_tree.heading("records", text="Records")

        self.file_tree.column("filename", width=180, anchor="w")
        self.file_tree.column("size", width=80, anchor="center")
        self.file_tree.column("distance", width=80, anchor="center")
        self.file_tree.column("records", width=90, anchor="center")

        self.file_tree.pack(fill="both", expand=True)

    # ──────────────────────────────────────────────────────────────────
    # TAB 3: LIVE PREDICTOR SIMULATOR
    # ──────────────────────────────────────────────────────────────────

    def build_predict_tab(self):
        card = ttk.Frame(self.tab_predict, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="🎯 Interactive Distance Estimator Tester", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))
        ttk.Label(card, text="Test how your trained ML model artifact (XGBoost/CatBoost/RF) predicts physical distance based on live RSSI inputs.", style="Muted.TLabel").pack(anchor="w", pady=(0, 20))

        # Slider Input
        input_frame = ttk.Frame(card, style="Card.TFrame")
        input_frame.pack(fill="x", pady=10)

        ttk.Label(input_frame, text="Simulated RSSI (dBm):", style="Bold.TLabel").pack(side="left", padx=(0, 15))

        self.rssi_slider = ttk.Scale(input_frame, from_=-100, to=-30, value=-70, command=self.on_rssi_slider_change)
        self.rssi_slider.pack(side="left", fill="x", expand=True, padx=15)

        self.lbl_rssi_val = ttk.Label(input_frame, text="-70 dBm", font=("Segoe UI", 12, "bold"), foreground=self.colors["yellow"])
        self.lbl_rssi_val.pack(side="right", padx=15)

        # Result Display Box
        result_box = ttk.Frame(card, style="Panel.TFrame", padding=25)
        result_box.pack(fill="x", pady=30)

        ttk.Label(result_box, text="PREDICTED DISTANCE", font=("Segoe UI", 10, "bold"), foreground=self.colors["subtext"]).pack()

        self.lbl_pred_result = ttk.Label(result_box, text="-- meters", font=("Segoe UI", 32, "bold"), foreground=self.colors["green"])
        self.lbl_pred_result.pack(pady=10)

        self.lbl_pred_detail = ttk.Label(result_box, text="Load or train model to test predictions.", style="Muted.TLabel")
        self.lbl_pred_detail.pack()

    # ──────────────────────────────────────────────────────────────────
    # DATA AUDIT & LOGIC FUNCTIONS
    # ──────────────────────────────────────────────────────────────────

    def refresh_dataset_audit(self):
        """Scans raw dataset CSVs and engineered ML observation windows to update audit views."""
        import csv

        for item in self.cov_tree.get_children():
            self.cov_tree.delete(item)
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        if not os.path.exists(RAW_DATA_DIR):
            self.advice_lbl.config(text="⚠️ Raw data directory not found. Run collector first.", foreground=self.colors["red"])
            return

        raw_files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, "dataset_*.csv")))

        if not raw_files:
            self.advice_lbl.config(text="⚠️ No raw CSV files found. Connect ESP32 and click 'START RECORDING' in Collector.", foreground=self.colors["yellow"])
            return

        raw_counts = {d: 0 for d in TARGET_DISTANCES}
        raw_counts["Other"] = 0
        ml_window_counts = {d: 0 for d in TARGET_DISTANCES}

        for fpath in raw_files:
            fname = os.path.basename(fpath)
            size_kb = f"{os.path.getsize(fpath) / 1024:.1f} KB"
            records = 0
            file_dist = "Unknown"

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    records = len(rows)
                    if rows and "distance_m" in rows[0]:
                        try:
                            raw_dist = float(rows[0]["distance_m"])
                            nearest = min(TARGET_DISTANCES, key=lambda x: abs(x - raw_dist))
                            if abs(nearest - raw_dist) < 0.05:
                                file_dist = nearest
                                raw_counts[nearest] += records
                            else:
                                file_dist = raw_dist
                                raw_counts["Other"] += records
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass

            self.file_tree.insert("", "end", values=(fname, size_kb, f"{file_dist}m" if isinstance(file_dist, (int, float)) else file_dist, records))

        # Check engineered observations dataset if available
        if os.path.exists(DATASET_PATH):
            try:
                obs_df = pd.read_csv(DATASET_PATH)
                if "distance_m" in obs_df.columns:
                    for d in TARGET_DISTANCES:
                        matched = obs_df[obs_df["distance_m"].apply(lambda val: abs(val - d) < 0.05)]
                        ml_window_counts[d] = len(matched)
            except Exception:
                pass
        else:
            # Fallback estimation based on raw packet counts
            for d in TARGET_DISTANCES:
                ml_window_counts[d] = max(0, (raw_counts[d] - 50) // 10 + 1) if raw_counts[d] >= 50 else 0

        # Update Coverage Table & Advice
        missing_dists = []
        low_dists = []

        for d in TARGET_DISTANCES:
            raw_c = raw_counts[d]
            win_c = ml_window_counts[d]

            if raw_c == 0 or win_c == 0:
                status = "❌ MISSING"
                advice = "Need 60s recording at this distance"
                missing_dists.append(f"{d}m")
            elif win_c < 100:
                status = "⚠️ LOW SAMPLES"
                advice = "Record a bit more data (~60s)"
                low_dists.append(f"{d}m")
            else:
                status = "✅ GOOD"
                advice = "Sufficient data available"

            self.cov_tree.insert("", "end", values=(f"{d} m", f"{raw_c:,} pkts / {win_c:,} win", status, advice))

        # Dynamic Recommendations Text
        if missing_dists:
            msg = f"⚠️ Dataset Incomplete: Missing distance(s): {', '.join(missing_dists)}.\n👉 Action: Set Collector GUI distance to {missing_dists[0]} and click START RECORDING for 60 seconds."
            fg = self.colors["yellow"]
        elif low_dists:
            msg = f"🟡 Dataset Acceptable: Low ML window count for {', '.join(low_dists)}.\n👉 Action: Record another 30–60s for low distances, or click 'RUN END-TO-END ML PIPELINE' to train now!"
            fg = self.colors["accent"]
        else:
            msg = "✅ Dataset Ready: Great ML window coverage across all required distance presets!\n👉 Action: Click '⚡ RUN END-TO-END ML PIPELINE' on Tab 1 to train your final production model."
            fg = self.colors["green"]

        self.advice_lbl.config(text=msg, foreground=fg)

    # ──────────────────────────────────────────────────────────────────
    # PIPELINE THREAD & EXECUTION
    # ──────────────────────────────────────────────────────────────────

    def start_pipeline_thread(self):
        if self.is_training:
            return

        self.is_training = True
        self.train_btn.config(state="disabled")
        self.progress_bar["mode"] = "determinate"
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="Initializing ML pipeline...", foreground=self.colors["accent"])
        self.console_text.delete("1.0", tk.END)

        thread = threading.Thread(target=self.run_pipeline_worker, daemon=True)
        thread.start()

    def run_pipeline_worker(self):
        try:
            pipeline_script = os.path.join(PROJECT_ROOT, "pipeline.py")
            python_exe = sys.executable

            cmd = [python_exe, pipeline_script, "--mode", self.mode_var.get()]
            if self.tune_var.get():
                cmd.append("--tune")

            self.log_queue.put(f"[EXEC] Running: {' '.join(cmd)}\n\n")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=PROJECT_ROOT
            )

            for line in iter(proc.stdout.readline, ""):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if isinstance(data, dict):
                        msg_type = data.get("type")
                        if msg_type == "progress":
                            self.root.after(0, lambda d=data: self.update_progress(d))
                        elif msg_type == "model_status":
                            self.root.after(0, lambda d=data: self.update_model_status(d))
                        else:
                            self.log_queue.put(line)
                    else:
                        self.log_queue.put(line)
                except (json.JSONDecodeError, TypeError):
                    self.log_queue.put(line)

            proc.wait()

            if proc.returncode == 0:
                self.log_queue.put("\n✅ PIPELINE SUCCESSFUL!\n")
                self.root.after(0, self.on_pipeline_success)
            else:
                self.log_queue.put(f"\n❌ PIPELINE ERROR (Exit Code {proc.returncode})\n")
                self.root.after(0, self.on_pipeline_error)

        except Exception as e:
            self.log_queue.put(f"\n❌ Exception: {str(e)}\n")
            self.root.after(0, self.on_pipeline_error)

    def update_model_status(self, data: dict):
        """Live updates the tournament leaderboard table as candidate models train and evaluate."""
        m_name = data.get("model_name", "")
        status = data.get("status", "")
        idx = data.get("index", 0)
        total = data.get("total", 0)
        pct = data.get("percent", 0)

        if hasattr(self, "model_tree"):
            # Check if row exists in treeview
            existing_item = None
            for item in self.model_tree.get_children():
                if self.model_tree.item(item)["values"][0] == m_name:
                    existing_item = item
                    break

            if status == "TRAINING":
                vals = (m_name, "⏳ TRAINING", "--", "--", "--", "--")
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert("", "end", values=vals)
            elif status == "SUCCESS":
                mae_str = f"{data.get('mae', 0.0):.4f}"
                rmse_str = f"{data.get('rmse', 0.0):.4f}"
                r2_str = f"{data.get('r2', 0.0):.4f}"
                cv_str = f"{data.get('cv_mae', 0.0):.4f}"
                vals = (m_name, "✅ SUCCESS", mae_str, rmse_str, r2_str, cv_str)
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert("", "end", values=vals)
            elif status == "FAILED":
                err = data.get("error", "Error")
                vals = (m_name, "❌ FAILED", "--", "--", "--", err[:25])
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert("", "end", values=vals)

        self.progress_bar["mode"] = "determinate"
        self.progress_bar["value"] = pct
        self.lbl_status.config(
            text=f"[{idx}/{total}] {status}: {m_name}",
            foreground=self.colors["accent"] if status == "TRAINING" else (self.colors["green"] if status == "SUCCESS" else self.colors["red"])
        )

    def update_progress(self, data: dict):
        """Updates the determinate progress bar, status text, and metric cards in real-time."""
        percent = data.get("percent", 0)
        stage = data.get("stage", "")
        metrics = data.get("metrics", {})

        self.progress_bar["mode"] = "determinate"
        self.progress_bar["value"] = percent

        self.lbl_status.config(
            text=f"[{percent}%] {stage}",
            foreground=self.colors["accent"]
        )

        if metrics:
            if "mae" in metrics and metrics["mae"] > 0:
                self.lbl_mae.config(text=f"MAE: {metrics['mae']:.4f} m")
            if "r2" in metrics and metrics["r2"] != 0:
                self.lbl_r2.config(text=f"R²: {metrics['r2']:.4f}")
            if "zone_acc" in metrics and metrics["zone_acc"] > 0:
                self.lbl_zone_acc.config(text=f"Zone: {metrics['zone_acc']:.1f}%")
            if "windows" in metrics and metrics["windows"] > 0:
                self.lbl_samples.config(text=f"Windows: {metrics['windows']:,}")

        self.console_text.insert(tk.END, f"[{percent}%] {stage}\n")
        self.console_text.see(tk.END)

    def auto_refresh_audit(self):
        """Periodically refreshes the dataset audit view every 5 seconds."""
        if not self.is_training:
            self.refresh_dataset_audit()
        self.root.after(5000, self.auto_refresh_audit)

    def process_queue_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.console_text.insert(tk.END, msg)
            self.console_text.see(tk.END)
        self.root.after(100, self.process_queue_logs)

    def on_pipeline_success(self):
        self.is_training = False
        self.progress_bar["value"] = 100
        self.train_btn.config(state="normal")
        self.lbl_status.config(text="✅ Model training and evaluation complete!", foreground=self.colors["green"])

        self.load_trained_model()
        self.load_metadata_summary()
        self.load_plot_image()
        self.refresh_dataset_audit()

        if hasattr(self, "rssi_slider"):
            self.on_rssi_slider_change(self.rssi_slider.get())

    def on_pipeline_error(self):
        self.is_training = False
        self.progress_bar["value"] = 0
        self.train_btn.config(state="normal")
        self.lbl_status.config(text="❌ Training failed. Check log console below.", foreground=self.colors["red"])

    # ──────────────────────────────────────────────────────────────────
    # METADATA & IMAGE DISPLAY
    # ──────────────────────────────────────────────────────────────────

    def load_metadata_summary(self):
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "r") as f:
                    meta = json.load(f)
                metrics = meta.get("metrics", {})
                self.lbl_mae.config(text=f"MAE: {metrics.get('test_mae', '--')} m")
                self.lbl_r2.config(text=f"R²: {metrics.get('test_r2', '--')}")
                self.lbl_samples.config(text=f"Windows: {meta.get('train_samples', 0) + meta.get('test_samples', 0)}")

                # Zone classification metrics
                zone_meta = meta.get("zone_classification", {})
                if zone_meta:
                    zone_acc = zone_meta.get("zone_accuracy", "--")
                    zone_champ = zone_meta.get("champion_classifier", "")
                    self.lbl_zone_acc.config(text=f"Zone: {zone_acc}%")
                else:
                    self.lbl_zone_acc.config(text=f"Zone: N/A")
            except Exception:
                pass

    def load_plot_image(self):
        if os.path.exists(DIAGNOSTIC_PLOT_PATH):
            try:
                img = Image.open(DIAGNOSTIC_PLOT_PATH)
                img = img.resize((480, 400), Image.Resampling.LANCZOS)
                self.photo_img = ImageTk.PhotoImage(img)
                self.plot_canvas.config(image=self.photo_img, text="")
            except Exception as e:
                self.plot_canvas.config(text=f"Error displaying image: {e}")

    def on_rssi_slider_change(self, val):
        rssi_val = float(val)
        self.lbl_rssi_val.config(text=f"{int(rssi_val)} dBm")

        # 1. Use real trained ML model & scaler pipeline if loaded
        if self.model is not None and self.scaler is not None and self.metadata is not None:
            try:
                feature_cols = self.metadata.get("feature_cols", [])
                sim_features = build_simulated_feature_dict(rssi_val)

                X_vec = [sim_features.get(col, 0.0) for col in feature_cols]
                X = np.array([X_vec], dtype=float)

                X_scaled = self.scaler.transform(X)
                d_pred = float(self.model.predict(X_scaled)[0])
                d_pred = max(0.1, min(25.0, d_pred))

                champ_name = self.metadata.get("champion_model", "Trained ML Model")
                mae = self.metadata.get("metrics", {}).get("test_mae", "--")

                zone_info = ""
                if self.zone_model is not None:
                    try:
                        zone_pred = self.zone_model.predict(X_scaled)[0]
                        zone_info = f" | Zone Class: {zone_pred}"
                    except Exception:
                        pass

                self.lbl_pred_result.config(text=f"{d_pred:.2f} meters")
                self.lbl_pred_detail.config(
                    text=f"🤖 Real ML Model ({champ_name}) | Test MAE: {mae}m{zone_info}"
                )
                return
            except Exception as e:
                pass

        # 2. Fallback to physical log-distance path loss prior if model is not loaded yet
        import math
        n = 2.5
        d_est = 10 ** ((-60 - rssi_val) / (10 * n))
        d_est = max(0.3, min(10.0, d_est))
        self.lbl_pred_result.config(text=f"{d_est:.2f} meters")
        self.lbl_pred_detail.config(
            text="⚠️ Log-Distance Fallback (Train ML model to enable real pipeline predictions)"
        )


def main():
    root = tk.Tk()
    app = MLTrainingStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
