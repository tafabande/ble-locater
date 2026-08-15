import os
import sys
import glob
import json
import time
import threading
import queue
import subprocess
import webbrowser
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR
RAW_DATA_DIR = os.path.join(BASE_DIR, 'datasets', 'raw')
if not os.path.exists(RAW_DATA_DIR):
    collector_raw = os.path.join(BASE_DIR, 'collector', 'data', 'raw')
    if os.path.exists(collector_raw):
        RAW_DATA_DIR = collector_raw
    else:
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
DATASET_PATH = os.path.join(PROJECT_ROOT, 'datasets', 'observations.csv')

MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')
DIAGNOSTIC_PLOT_PATH = os.path.join(REPORTS_DIR, 'model_diagnostics.png')
METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.json')
TARGET_DISTANCES = [0.5, 1.0, 2.0, 3.0, 5.0]
sys.path.insert(0, PROJECT_ROOT)
from learning.stage_runtime_learner import StageRuntimeLearner

def build_simulated_feature_dict(rssi_val, height_m=1.0):
    n = 2.5
    d_free = 10 ** ((-40.0 - rssi_val) / (10.0 * 2.0))
    d_indoor = 10 ** ((-60.0 - rssi_val) / (10.0 * n))
    return {'packet_count': 10.0, 'scan_duration_ms': 1000.0, 'rssi_mean': float(rssi_val), 'rssi_median': float(rssi_val), 'rssi_min': float(rssi_val) - 2.0, 'rssi_max': float(rssi_val) + 2.0, 'rssi_std': 1.5, 'rssi_variance': 2.25, 'rssi_range': 4.0, 'rssi_p05': float(rssi_val) - 2.5, 'rssi_p10': float(rssi_val) - 2.0, 'rssi_p25': float(rssi_val) - 1.0, 'rssi_p75': float(rssi_val) + 1.0, 'rssi_p90': float(rssi_val) + 2.0, 'rssi_p95': float(rssi_val) + 2.5, 'rssi_iqr': 2.0, 'rssi_p90_10_range': 4.0, 'rssi_mad': 1.2, 'rssi_snr': abs(rssi_val) / 1.5, 'rssi_skewness': 0.0, 'rssi_kurtosis': 0.0, 'rssi_delta_mean': 0.0, 'rssi_delta_std': 0.5, 'rssi_delta_max': 1.0, 'observed_adv_interval': 100.0, 'adv_interval_std': 5.0, 'path_loss_free_space': d_free, 'path_loss_indoor': d_indoor, 'rssi_mean_to_std_ratio': abs(rssi_val) / 1.5, 'rssi_median_mean_diff': 0.0, 'rssi_slope': 0.0, 'rssi_trend_strength': 0.0, 'rssi_ema_diff': 0.0, 'rssi_first_half_mean': float(rssi_val), 'rssi_second_half_mean': float(rssi_val), 'rssi_half_diff': 0.0, 'rssi_autocorrelation': 0.5, 'rssi_energy': float(rssi_val) ** 2, 'rssi_mean_delta': 0.0, 'rssi_mean_slope_3w': 0.0, 'rssi_mean_slope_5w': 0.0, 'rssi_rolling_mean_3w': float(rssi_val), 'rssi_rolling_std_3w': 1.5, 'rssi_rolling_mean_5w': float(rssi_val), 'rssi_rolling_std_5w': 1.5, 'rssi_ema_cross_window': float(rssi_val), 'rssi_velocity': 0.0, 'rssi_acceleration': 0.0, 'signal_stability_index': 1.0 / (1.5 + 0.001), 'rssi_rolling_mean_10w': float(rssi_val), 'rssi_rolling_std_10w': 1.5, 'rssi_motion_direction': 0.0, 'rssi_snr_rolling_5w': abs(rssi_val) / 1.5, 'height_m': float(height_m)}

class ResultsDashboardView(ttk.Frame):

    def __init__(self, parent, colors, metadata_path=METADATA_PATH, diagnostic_plot_path=DIAGNOSTIC_PLOT_PATH, app=None):
        super().__init__(parent)
        self.colors = colors
        self.metadata_path = metadata_path
        self.diagnostic_plot_path = diagnostic_plot_path
        self.app = app
        self.metadata = None
        self.current_plot_name = 'model_diagnostics.png'
        self.plot_photos = {}
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        toolbar = ttk.Frame(self, style='Card.TFrame', padding=12)
        toolbar.pack(fill='x', pady=(0, 10))
        ttk.Label(toolbar, text='📊 Model Performance & Evaluation Dashboard', style='Header.TLabel').pack(side='left')
        btn_box = ttk.Frame(toolbar, style='Card.TFrame')
        btn_box.pack(side='right')
        ttk.Button(btn_box, text='🔄 Refresh Data', command=self.refresh, style='Success.TButton').pack(side='left', padx=4)
        ttk.Button(btn_box, text='📋 Copy Summary', command=self.copy_summary_to_clipboard).pack(side='left', padx=4)
        ttk.Button(btn_box, text='💾 Export JSON Report', command=self.export_json_report).pack(side='left', padx=4)
        ttk.Button(btn_box, text='📂 Open Reports Folder', command=self.open_reports_folder).pack(side='left', padx=4)
        self.kpi_frame = ttk.Frame(self)
        self.kpi_frame.pack(fill='x', pady=(0, 10))
        for col in range(6):
            self.kpi_frame.columnconfigure(col, weight=1, uniform='kpi')
        self.kpi_cards = {}
        cards_def = [('champion', '🏆 CHAMPION MODEL', '--', self.colors['accent'], 'Best Evaluated Pipeline'), ('mae', '🎯 TEST MAE', '--', self.colors['green'], 'Median Error: --'), ('r2', '📈 GOODNESS OF FIT (R²)', '--', self.colors['yellow'], 'MAPE: --'), ('rmse', '📏 RMSE / MAX ERR', '--', self.colors['purple'], 'Max Error: --'), ('zone', '🔮 ZONE ACCURACY', '--', self.colors['red'], 'Classifier: --'), ('windows', '📦 DATASET WINDOWS', '--', self.colors['accent'], 'Filtered Outliers: --')]
        for idx, (key, title, val, col, sub) in enumerate(cards_def):
            card = ttk.Frame(self.kpi_frame, style='Card.TFrame', padding=12)
            card.grid(row=0, column=idx, sticky='nsew', padx=3, pady=2)
            ttk.Label(card, text=title, font=('Segoe UI', 8, 'bold'), foreground=self.colors['subtext'], background=self.colors['card']).pack(anchor='w')
            val_lbl = ttk.Label(card, text=val, font=('Segoe UI', 15, 'bold'), foreground=col, background=self.colors['card'])
            val_lbl.pack(anchor='w', pady=(4, 2))
            sub_lbl = ttk.Label(card, text=sub, font=('Segoe UI', 8), foreground=self.colors['subtext'], background=self.colors['card'])
            sub_lbl.pack(anchor='w')
            self.kpi_cards[key] = (val_lbl, sub_lbl)
        self.dash_notebook = ttk.Notebook(self)
        self.dash_notebook.pack(fill='both', expand=True)
        self.sub_accuracy = ttk.Frame(self.dash_notebook, padding=12)
        self.dash_notebook.add(self.sub_accuracy, text='🎯 Accuracy & Tolerance Gauges')
        self.build_accuracy_subtab()
        self.sub_tournament = ttk.Frame(self.dash_notebook, padding=12)
        self.dash_notebook.add(self.sub_tournament, text='🏆 Super Learner Leaderboard')
        self.build_tournament_subtab()
        self.sub_features = ttk.Frame(self.dash_notebook, padding=12)
        self.dash_notebook.add(self.sub_features, text='⭐ Top Feature Importances')
        self.build_features_subtab()
        self.sub_plots = ttk.Frame(self.dash_notebook, padding=12)
        self.dash_notebook.add(self.sub_plots, text='🖼️ Diagnostic Visualizations')
        self.build_plots_subtab()
        self.sub_zone = ttk.Frame(self.dash_notebook, padding=12)
        self.dash_notebook.add(self.sub_zone, text='🔮 Zone Classification Stats')
        self.build_zone_subtab()

    def build_accuracy_subtab(self):
        split = ttk.Frame(self.sub_accuracy)
        split.pack(fill='both', expand=True)
        left_box = ttk.Frame(split, style='Card.TFrame', padding=12)
        left_box.pack(side='left', fill='both', expand=True, padx=(0, 8))
        ttk.Label(left_box, text='📐 Distance Error Tolerance Distribution', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(left_box, text='Percentage of prediction errors staying strictly within specified spatial margins:', style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
        self.tolerance_rows = {}
        t_labels = [('within_10cm', 'Within ± 10 cm (0.10 m)'), ('within_25cm', 'Within ± 25 cm (0.25 m)'), ('within_50cm', 'Within ± 50 cm (0.50 m)'), ('within_75cm', 'Within ± 75 cm (0.75 m)'), ('within_100cm', 'Within ± 1.00 m (100 cm)'), ('within_150cm', 'Within ± 1.50 m (150 cm)')]
        for key, title in t_labels:
            row = ttk.Frame(left_box, style='Card.TFrame')
            row.pack(fill='x', pady=5)
            hdr = ttk.Frame(row, style='Card.TFrame')
            hdr.pack(fill='x')
            lbl_title = ttk.Label(hdr, text=title, font=('Segoe UI', 9, 'bold'), foreground=self.colors['text'], background=self.colors['card'])
            lbl_title.pack(side='left')
            lbl_pct = ttk.Label(hdr, text='0.0%', font=('Segoe UI', 9, 'bold'), foreground=self.colors['green'], background=self.colors['card'])
            lbl_pct.pack(side='right')
            pbar = ttk.Progressbar(row, mode='determinate', maximum=100)
            pbar.pack(fill='x', pady=(3, 0))
            self.tolerance_rows[key] = (lbl_pct, pbar)
        right_box = ttk.Frame(split, style='Card.TFrame', padding=12)
        right_box.pack(side='right', fill='both', expand=True)
        ttk.Label(right_box, text='📏 Accuracy per Target Distance', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(right_box, text='Mean Absolute Error (MAE) categorized across target test distances:', style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
        self.per_dist_tree = ttk.Treeview(right_box, columns=('target', 'mae', 'status', 'rating'), show='headings', height=8)
        self.per_dist_tree.heading('target', text='Target Distance')
        self.per_dist_tree.heading('mae', text='Test MAE (m)')
        self.per_dist_tree.heading('status', text='Accuracy Rating')
        self.per_dist_tree.heading('rating', text='Performance Note')
        self.per_dist_tree.column('target', width=120, anchor='center')
        self.per_dist_tree.column('mae', width=110, anchor='center')
        self.per_dist_tree.column('status', width=140, anchor='center')
        self.per_dist_tree.column('rating', width=220, anchor='w')
        self.per_dist_tree.pack(fill='both', expand=True)

    def build_tournament_subtab(self):
        container = ttk.Frame(self.sub_tournament)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text='🏆 Super Learner Tournament Comparative Leaderboard', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        ttk.Label(container, text='All candidate regression models evaluated using Stratified Session Cross-Validation folds:', style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
        self.tourn_tree = ttk.Treeview(container, columns=('rank', 'model', 'mae', 'rmse', 'r2', 'medae', 'mape', 'cv_mae', 'score'), show='headings', height=10)
        self.tourn_tree.heading('rank', text='Rank')
        self.tourn_tree.heading('model', text='Candidate Model')
        self.tourn_tree.heading('mae', text='Test MAE (m)')
        self.tourn_tree.heading('rmse', text='RMSE (m)')
        self.tourn_tree.heading('r2', text='R² Score')
        self.tourn_tree.heading('medae', text='MedAE (m)')
        self.tourn_tree.heading('mape', text='MAPE (%)')
        self.tourn_tree.heading('cv_mae', text='CV MAE (m)')
        self.tourn_tree.heading('score', text='Score')
        self.tourn_tree.column('rank', width=60, anchor='center')
        self.tourn_tree.column('model', width=200, anchor='w')
        self.tourn_tree.column('mae', width=90, anchor='center')
        self.tourn_tree.column('rmse', width=90, anchor='center')
        self.tourn_tree.column('r2', width=80, anchor='center')
        self.tourn_tree.column('medae', width=90, anchor='center')
        self.tourn_tree.column('mape', width=80, anchor='center')
        self.tourn_tree.column('cv_mae', width=110, anchor='center')
        self.tourn_tree.column('score', width=80, anchor='center')
        self.tourn_tree.pack(fill='both', expand=True)
        self.tourn_tree.bind('<<TreeviewSelect>>', self.on_tournament_model_selected)
        self.tourn_detail_box = ttk.Frame(container, style='Card.TFrame', padding=10)
        self.tourn_detail_box.pack(fill='x', pady=(10, 0))
        ttk.Label(self.tourn_detail_box, text='ℹ️ Selected Model Metrics Summary', style='Bold.TLabel').pack(anchor='w')
        self.tourn_detail_lbl = ttk.Label(self.tourn_detail_box, text='Click any model in the table above to view detailed metrics.', style='Muted.TLabel')
        self.tourn_detail_lbl.pack(anchor='w', pady=(2, 0))

    def build_features_subtab(self):
        container = ttk.Frame(self.sub_features)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text='⭐ Top RSSI Signal & Spatial Feature Importances', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        ttk.Label(container, text='Engineered features sorted by relative importance weight in distance estimation:', style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
        canvas_frame = ttk.Frame(container, style='Card.TFrame')
        canvas_frame.pack(fill='both', expand=True)
        self.feat_canvas = tk.Canvas(canvas_frame, bg=self.colors['panel'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.feat_canvas.yview)
        self.feat_scroll_frame = ttk.Frame(self.feat_canvas, style='Panel.TFrame')
        self.feat_scroll_frame.bind('<Configure>', lambda e: self.feat_canvas.configure(scrollregion=self.feat_canvas.bbox('all')))
        self.feat_canvas.create_window((0, 0), window=self.feat_scroll_frame, anchor='nw')
        self.feat_canvas.configure(yscrollcommand=scrollbar.set)
        self.feat_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def build_plots_subtab(self):
        container = ttk.Frame(self.sub_plots)
        container.pack(fill='both', expand=True)
        plot_bar = ttk.Frame(container, style='Card.TFrame', padding=8)
        plot_bar.pack(fill='x', pady=(0, 10))
        ttk.Label(plot_bar, text='Select Plot:', style='Bold.TLabel').pack(side='left', padx=(0, 10))
        self.btn_plot_diag = ttk.Button(plot_bar, text='📈 Model Diagnostics', command=lambda: self.switch_plot('model_diagnostics.png'))
        self.btn_plot_diag.pack(side='left', padx=4)
        self.btn_plot_audit = ttk.Button(plot_bar, text='📊 Dataset Audit', command=lambda: self.switch_plot('dataset_baseline_audit.png'))
        self.btn_plot_audit.pack(side='left', padx=4)
        self.btn_plot_sim = ttk.Button(plot_bar, text='🔬 Sim2Real Study', command=lambda: self.switch_plot('sim2real_comparison.png'))
        self.btn_plot_sim.pack(side='left', padx=4)
        self.plot_box = ttk.Frame(container, style='Card.TFrame', padding=10)
        self.plot_box.pack(fill='both', expand=True)
        self.plot_display_lbl = tk.Label(self.plot_box, bg=self.colors['panel'], text='No plot loaded.', fg=self.colors['subtext'])
        self.plot_display_lbl.pack(fill='both', expand=True)

    def build_zone_subtab(self):
        container = ttk.Frame(self.sub_zone, style='Card.TFrame', padding=15)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text='🔮 Zone Classification Performance Summary', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        z_kpi = ttk.Frame(container, style='Card.TFrame')
        z_kpi.pack(fill='x', pady=(0, 15))
        self.lbl_zone_champ = ttk.Label(z_kpi, text='Champion Classifier: --', font=('Segoe UI', 11, 'bold'), foreground=self.colors['purple'], background=self.colors['card'])
        self.lbl_zone_champ.pack(side='left', padx=15)
        self.lbl_zone_acc_card = ttk.Label(z_kpi, text='Overall Accuracy: --%', font=('Segoe UI', 11, 'bold'), foreground=self.colors['green'], background=self.colors['card'])
        self.lbl_zone_acc_card.pack(side='left', padx=15)
        ttk.Label(container, text='📋 Classification Report & Detailed Zone Metrics', style='Bold.TLabel').pack(anchor='w', pady=(0, 5))
        self.zone_text = tk.Text(container, bg=self.colors['panel'], fg=self.colors['text'], font=('Consolas', 10), relief='flat', wrap='word', height=15)
        self.zone_text.pack(fill='both', expand=True)

    def refresh(self):
        if not os.path.exists(self.metadata_path):
            self.show_empty_state()
            return
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        except Exception as e:
            self.show_empty_state(f'Error loading metadata: {e}')
            return
        meta = self.metadata
        metrics = meta.get('metrics', {})
        ext = metrics.get('extended', {})
        champ_name = meta.get('champion_model', meta.get('champion_name', 'Trained ML Model'))
        test_mae = metrics.get('test_mae', 0.0)
        med_ae = metrics.get('test_median_ae', 0.0)
        test_r2 = metrics.get('test_r2', 0.0)
        mape = ext.get('mape', 0.0)
        rmse = metrics.get('test_rmse', 0.0)
        max_err = ext.get('max_error', 0.0)
        p95_err = ext.get('p95_error', 0.0)
        outliers = metrics.get('n_outliers_removed', 0)
        train_n = meta.get('train_samples', 0)
        test_n = meta.get('test_samples', 0)
        total_n = meta.get('total_samples', train_n + test_n)
        zone_meta = meta.get('zone_classification', {})
        self.kpi_cards['champion'][0].config(text=f'{champ_name}')
        self.kpi_cards['champion'][1].config(text=f"Score: {meta.get('champion_score', '--')}")
        self.kpi_cards['mae'][0].config(text=f'{test_mae:.4f} m' if isinstance(test_mae, (int, float)) else '--')
        self.kpi_cards['mae'][1].config(text=f'Median AE: {med_ae:.4f}m' if isinstance(med_ae, (int, float)) else '--')
        self.kpi_cards['r2'][0].config(text=f'{test_r2:.4f}' if isinstance(test_r2, (int, float)) else '--')
        self.kpi_cards['r2'][1].config(text=f'MAPE: {mape:.2f}%' if isinstance(mape, (int, float)) else '--')
        self.kpi_cards['rmse'][0].config(text=f'{rmse:.4f} m' if isinstance(rmse, (int, float)) else '--')
        self.kpi_cards['rmse'][1].config(text=f'Max: {max_err:.2f}m | P95: {p95_err:.2f}m' if isinstance(max_err, (int, float)) else '--')
        if zone_meta:
            z_acc = zone_meta.get('zone_accuracy', 0.0)
            z_champ = zone_meta.get('champion_classifier', 'Classifier')
            self.kpi_cards['zone'][0].config(text=f'{z_acc:.1f}%' if isinstance(z_acc, (int, float)) else f'{z_acc}%')
            self.kpi_cards['zone'][1].config(text=f'Model: {z_champ}')
        else:
            self.kpi_cards['zone'][0].config(text='N/A')
            self.kpi_cards['zone'][1].config(text='Regression Only Mode')
        self.kpi_cards['windows'][0].config(text=f'{total_n:,} windows')
        self.kpi_cards['windows'][1].config(text=f'Outliers Filtered: {outliers:,}')
        tolerances = metrics.get('tolerances', {})
        for key, (lbl_pct, pbar) in self.tolerance_rows.items():
            val = tolerances.get(key, 0.0)
            lbl_pct.config(text=f'{val:.2f}%')
            pbar['value'] = val
        for item in self.per_dist_tree.get_children():
            self.per_dist_tree.delete(item)
        per_dist_mae = ext.get('per_distance_mae', {})
        if per_dist_mae:
            for dist_str, mae_val in sorted(per_dist_mae.items(), key=lambda x: float(x[0].replace('m', '')) if x[0].replace('m', '').replace('.', '').isdigit() else 99):
                if mae_val < 0.2:
                    status = '🟢 EXCELLENT'
                    rating = 'High precision (< 20 cm error)'
                elif mae_val < 0.8:
                    status = '🟡 GOOD'
                    rating = 'Reliable indoor accuracy (< 80 cm)'
                elif mae_val < 1.5:
                    status = '🟠 FAIR'
                    rating = 'Acceptable range (< 1.5 m)'
                else:
                    status = '🔴 HIGH VARIANCE'
                    rating = 'Higher multipath noise (> 1.5 m error)'
                self.per_dist_tree.insert('', 'end', values=(dist_str, f'{mae_val:.4f} m', status, rating))
        for item in self.tourn_tree.get_children():
            self.tourn_tree.delete(item)
        tourn = meta.get('tournament', [])
        for idx, m in enumerate(tourn, 1):
            name = m.get('name', 'Model')
            rank_str = f'🏆 #{idx}' if idx == 1 else f'#{idx}'
            m_mae = f"{m.get('mae', 0.0):.4f}"
            m_rmse = f"{m.get('rmse', 0.0):.4f}"
            m_r2 = f"{m.get('r2', 0.0):.4f}"
            m_med = f"{m.get('med_ae', 0.0):.4f}"
            m_mape = f"{m.get('ext_metrics', {}).get('mape', 0.0):.1f}%"
            cv_info = m.get('cv', {})
            cv_str = f"{cv_info.get('cv_mae_mean', 0.0):.3f} ± {cv_info.get('cv_mae_std', 0.0):.2f}m" if 'cv_mae_mean' in cv_info else '--'
            score_str = f"{m.get('composite_score', 0.0):.3f}" if 'composite_score' in m else '--'
            self.tourn_tree.insert('', 'end', values=(rank_str, name, m_mae, m_rmse, m_r2, m_med, m_mape, cv_str, score_str))
        for widget in self.feat_scroll_frame.winfo_children():
            widget.destroy()
        importances = meta.get('importances', {})
        if importances:
            sorted_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:15]
            max_imp = max([val for _, val in sorted_feats]) if sorted_feats and max([val for _, val in sorted_feats]) > 0 else 1.0
            for feat_name, imp_val in sorted_feats:
                row_f = ttk.Frame(self.feat_scroll_frame, style='Card.TFrame', padding=6)
                row_f.pack(fill='x', pady=3, padx=5)
                title_f = ttk.Frame(row_f, style='Card.TFrame')
                title_f.pack(fill='x')
                ttk.Label(title_f, text=feat_name, font=('Consolas', 9, 'bold'), foreground=self.colors['accent'], background=self.colors['card']).pack(side='left')
                ttk.Label(title_f, text=f'{imp_val * 100:.2f}% ({imp_val:.4f})', font=('Segoe UI', 9, 'bold'), foreground=self.colors['green'], background=self.colors['card']).pack(side='right')
                c_bar = tk.Canvas(row_f, height=12, bg=self.colors['panel'], highlightthickness=0)
                c_bar.pack(fill='x', pady=(3, 0))
                rel_w = min(1.0, max(0.02, imp_val / max_imp))
                c_bar.bind('<Configure>', lambda e, cb=c_bar, rw=rel_w: self.draw_feature_bar(cb, rw))
        self.switch_plot(self.current_plot_name)
        if zone_meta:
            z_champ = zone_meta.get('champion_classifier', 'Classifier')
            z_acc = zone_meta.get('zone_accuracy', 0.0)
            self.lbl_zone_champ.config(text=f'Champion Classifier: {z_champ}')
            self.lbl_zone_acc_card.config(text=f'Overall Zone Accuracy: {z_acc:.2f}%')
            self.zone_text.delete('1.0', tk.END)
            rep = zone_meta.get('classification_report', '')
            if isinstance(rep, dict):
                rep = json.dumps(rep, indent=2)
            self.zone_text.insert(tk.END, f'=== ZONE CLASSIFICATION REPORT ({z_champ}) ===\n\n{rep}')
        else:
            self.lbl_zone_champ.config(text='Champion Classifier: None')
            self.lbl_zone_acc_card.config(text='Overall Zone Accuracy: N/A')
            self.zone_text.delete('1.0', tk.END)
            self.zone_text.insert(tk.END, 'Zone classification was not run in this pipeline session.\nRun pipeline with --mode classification or --mode both to generate zone stats.')

    def draw_feature_bar(self, canvas, rel_w):
        canvas.delete('all')
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        bar_w = int(w * rel_w)
        canvas.create_rectangle(0, 0, bar_w, h, fill=self.colors['accent'], outline='')

    def switch_plot(self, plot_filename):
        self.current_plot_name = plot_filename
        target_path = os.path.join(REPORTS_DIR, plot_filename)
        if not os.path.exists(target_path):
            self.plot_display_lbl.config(image='', text=f'⚠️ Plot asset not found:\n{plot_filename}\nRun training pipeline to generate graphics.')
            return
        try:
            img = Image.open(target_path)
            img = img.resize((760, 480), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.plot_photos[plot_filename] = photo
            self.plot_display_lbl.config(image=photo, text='')
        except Exception as e:
            self.plot_display_lbl.config(image='', text=f'Error rendering image {plot_filename}: {e}')

    def on_tournament_model_selected(self, event):
        sel = self.tourn_tree.selection()
        if not sel:
            return
        vals = self.tourn_tree.item(sel[0])['values']
        if vals and self.metadata and ('tournament' in self.metadata):
            m_name = vals[1]
            for m in self.metadata['tournament']:
                if m.get('name') == m_name:
                    txt = f"🤖 Candidate: {m_name}  |  Rank Score: {m.get('composite_score', 0.0):.4f}\n• Test MAE: {m.get('mae', 0.0):.4f} m  |  RMSE: {m.get('rmse', 0.0):.4f} m  |  MedAE: {m.get('med_ae', 0.0):.4f} m\n• R² Score: {m.get('r2', 0.0):.4f}  |  MAPE: {m.get('ext_metrics', {}).get('mape', 0.0):.2f}%\n• CV Folds: {m.get('cv', {}).get('cv_type', 'N/A')} -> Mean CV MAE: {m.get('cv', {}).get('cv_mae_mean', 0.0):.4f} m"
                    self.tourn_detail_lbl.config(text=txt, foreground=self.colors['accent'])
                    break

    def copy_summary_to_clipboard(self):
        if not self.metadata:
            messagebox.showinfo('Clipboard', 'No trained model metadata available to copy.')
            return
        meta = self.metadata
        metrics = meta.get('metrics', {})
        ext = metrics.get('extended', {})
        champ = meta.get('champion_model', meta.get('champion_name', 'Trained ML Model'))
        summary_text = f"⚡ BLE INDOOR POSITIONING — MODEL TRAINING RESULTS\n==================================================\n🏆 Champion Model: {champ}\n🎯 Test MAE: {metrics.get('test_mae', '--')} m\n📈 R² Score: {metrics.get('test_r2', '--')}\n📏 RMSE: {metrics.get('test_rmse', '--')} m\n🎯 Median Absolute Error: {metrics.get('test_median_ae', '--')} m\n📊 MAPE: {ext.get('mape', '--')}%\n📦 Dataset Windows: {meta.get('train_samples', 0) + meta.get('test_samples', 0):,}\nOutliers Filtered: {metrics.get('n_outliers_removed', 0):,}\n==================================================\nCumulative Error Tolerances:\n"
        for key, val in metrics.get('tolerances', {}).items():
            summary_text += f" • {key.replace('_', ' ')}: {val:.2f}%\n"
        self.clipboard_clear()
        self.clipboard_append(summary_text)
        messagebox.showinfo('Clipboard', '✅ Executive training results summary copied to clipboard!')

    def export_json_report(self):
        if not self.metadata:
            messagebox.showinfo('Export', 'No training metadata available to export.')
            return
        fpath = filedialog.asksaveasfilename(title='Save Model Results Report JSON', defaultextension='.json', filetypes=[('JSON Files', '*.json'), ('All Files', '*.*')], initialfile=f"model_results_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if fpath:
            try:
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, indent=2)
                messagebox.showinfo('Export Success', f'✅ Results report successfully exported to:\n{fpath}')
            except Exception as e:
                messagebox.showerror('Export Error', f'Failed to save report: {e}')

    def open_reports_folder(self):
        if os.path.exists(REPORTS_DIR):
            try:
                os.startfile(REPORTS_DIR)
            except Exception:
                try:
                    subprocess.Popen(['explorer', REPORTS_DIR])
                except Exception as e:
                    messagebox.showerror('Error', f'Could not open reports directory: {e}')
        else:
            messagebox.showinfo('Reports Folder', f'Reports folder does not exist yet:\n{REPORTS_DIR}')

    def show_empty_state(self, message='No trained model results found yet.\nRun the ML Pipeline on Tab 1 to generate evaluation metrics.'):
        for val_lbl, sub_lbl in self.kpi_cards.values():
            val_lbl.config(text='--')
            sub_lbl.config(text='Pipeline pending')
        for lbl_pct, pbar in self.tolerance_rows.values():
            lbl_pct.config(text='0.0%')
            pbar['value'] = 0
        for item in self.per_dist_tree.get_children():
            self.per_dist_tree.delete(item)
        for item in self.tourn_tree.get_children():
            self.tourn_tree.delete(item)
        self.plot_display_lbl.config(image='', text=message)

class ResultsDashboardWindow(tk.Toplevel):

    def __init__(self, parent, colors, metadata_path=METADATA_PATH, diagnostic_plot_path=DIAGNOSTIC_PLOT_PATH, app=None):
        super().__init__(parent)
        self.title('📊 BLE Indoor Positioning — Model Results Dashboard')
        self.geometry('1120x820')
        self.minsize(960, 680)
        self.configure(bg=colors['bg'])
        self.dashboard_view = ResultsDashboardView(self, colors=colors, metadata_path=metadata_path, diagnostic_plot_path=diagnostic_plot_path, app=app)
        self.dashboard_view.pack(fill='both', expand=True, padx=15, pady=15)

    def refresh(self):
        self.dashboard_view.refresh()

class MLTrainingStudio:

    def __init__(self, root):
        self.root = root
        self.root.title('⚡ BLE Tracker — AI Data & Model Training Studio')
        self.root.geometry('1080x850')
        self.root.minsize(960, 720)
        self.log_queue = queue.Queue()
        self.is_training = False
        self.dashboard_window = None
        self.start_time = None
        self.current_percent = 0
        self.progress_history = []
        self.smoothed_eta_sec = None
        self.stage_learner = StageRuntimeLearner()
        self.stage_start_times = {}
        self.stage_durations = {}
        self.current_stage_name = None
        self.anim_step = 0
        self.timer_job = None
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.colors = {'bg': '#1e1e2e', 'panel': '#181825', 'card': '#313244', 'accent': '#89b4fa', 'green': '#a6e3a1', 'yellow': '#f9e2af', 'red': '#f38ba8', 'purple': '#cba6f7', 'text': '#cdd6f4', 'subtext': '#a6adc8'}
        self.model = None
        self.scaler = None
        self.metadata = None
        self.zone_model = None
        self._last_audit_mtime = 0
        self.setup_styles()
        self.build_ui()
        self.root.after(100, self.process_queue_logs)
        self.root.after(50, self.initial_load)

    def initial_load(self):
        self.lbl_status.config(text='Loading ML models and dataset...', foreground=self.colors['accent'])
        self.root.update()
        self.load_trained_model()
        self.refresh_dataset_audit()
        self.lbl_status.config(text="System Ready. Click 'RUN END-TO-END ML PIPELINE' to start.", foreground=self.colors['subtext'])
        self.auto_refresh_audit()

    def load_trained_model(self):
        model_path = os.path.join(MODEL_DIR, 'distance_estimator.joblib')
        scaler_path = os.path.join(MODEL_DIR, 'scaler.joblib')
        meta_path = os.path.join(MODEL_DIR, 'model_metadata.json')
        zone_model_path = os.path.join(MODEL_DIR, 'zone_classifier.joblib')
        self.model = None
        self.scaler = None
        self.metadata = None
        self.zone_model = None
        if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path):
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                if os.path.exists(zone_model_path):
                    try:
                        self.zone_model = joblib.load(zone_model_path)
                    except Exception:
                        pass
                return True
            except Exception as e:
                print(f'Error loading trained ML model: {e}')
                return False
        return False

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.root.configure(bg=self.colors['bg'])
        style.configure('.', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['panel'], foreground=self.colors['text'], padding=[15, 8], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', self.colors['card'])], foreground=[('selected', self.colors['accent'])])
        style.configure('Card.TFrame', background=self.colors['card'], relief='flat', borderwidth=1)
        style.configure('Panel.TFrame', background=self.colors['panel'])
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), foreground=self.colors['accent'], background=self.colors['bg'])
        style.configure('SubHeader.TLabel', font=('Segoe UI', 12, 'bold'), foreground=self.colors['purple'], background=self.colors['card'])
        style.configure('Bold.TLabel', font=('Segoe UI', 10, 'bold'), foreground=self.colors['text'], background=self.colors['card'])
        style.configure('Muted.TLabel', font=('Segoe UI', 9), foreground=self.colors['subtext'], background=self.colors['card'])
        style.configure('Primary.TButton', font=('Segoe UI', 11, 'bold'), background=self.colors['accent'], foreground='#11111b', padding=[15, 10])
        style.map('Primary.TButton', background=[('active', '#b4befe')])
        style.configure('Success.TButton', font=('Segoe UI', 10, 'bold'), background=self.colors['green'], foreground='#11111b', padding=[10, 6])
        style.configure('Treeview', background=self.colors['panel'], foreground=self.colors['text'], fieldbackground=self.colors['panel'], rowheight=28)
        style.configure('Treeview.Heading', background=self.colors['card'], foreground=self.colors['accent'], font=('Segoe UI', 10, 'bold'))
        style.configure('TProgressbar', thickness=12, troughcolor=self.colors['panel'], background=self.colors['green'])

    def build_ui(self):
        header_frame = ttk.Frame(self.root, padding=(20, 15))
        header_frame.pack(fill='x')
        ttk.Label(header_frame, text='⚡ BLE ML Studio & Automated Trainer', style='Header.TLabel').pack(side='left')
        btn_dash_pop = ttk.Button(header_frame, text='📊 OPEN RESULTS DASHBOARD', style='Success.TButton', command=self.open_results_dashboard)
        btn_dash_pop.pack(side='right', padx=(10, 0))
        ttk.Label(header_frame, text='End-to-End Feature Engineering & Distance Estimation Pipeline', style='Muted.TLabel').pack(side='right')
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        self.tab_train = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_train, text='🚀 Model Trainer & Diagnostics')
        self.build_train_tab()
        self.tab_dashboard = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_dashboard, text='📊 Results Dashboard')
        self.embedded_dashboard = ResultsDashboardView(self.tab_dashboard, colors=self.colors, metadata_path=METADATA_PATH, diagnostic_plot_path=DIAGNOSTIC_PLOT_PATH, app=self)
        self.embedded_dashboard.pack(fill='both', expand=True)
        self.tab_audit = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_audit, text='📊 Dataset Audit & Advice')
        self.build_audit_tab()
        self.tab_predict = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_predict, text='🎯 Live Model Tester')
        self.build_predict_tab()

    def open_results_dashboard(self):
        if hasattr(self, 'dashboard_window') and self.dashboard_window is not None and self.dashboard_window.winfo_exists():
            self.dashboard_window.deiconify()
            self.dashboard_window.lift()
            self.dashboard_window.focus_force()
            self.dashboard_window.refresh()
        else:
            self.dashboard_window = ResultsDashboardWindow(self.root, colors=self.colors, metadata_path=METADATA_PATH, diagnostic_plot_path=DIAGNOSTIC_PLOT_PATH, app=self)

    def build_train_tab(self):
        top_bar = ttk.Frame(self.tab_train, style='Card.TFrame', padding=15)
        top_bar.pack(fill='x', pady=(0, 15))
        btn_box = ttk.Frame(top_bar, style='Card.TFrame')
        btn_box.pack(side='left', fill='x', expand=True)
        self.train_btn = ttk.Button(btn_box, text='⚡ RUN END-TO-END ML PIPELINE', style='Primary.TButton', command=self.start_pipeline_thread)
        self.train_btn.pack(side='left', padx=(0, 15))
        mode_frame = ttk.Frame(btn_box, style='Card.TFrame')
        mode_frame.pack(side='left', padx=10)
        ttk.Label(mode_frame, text='Mode:', style='Bold.TLabel').pack(side='left', padx=(0, 5))
        self.mode_var = tk.StringVar(value='both')
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=['both', 'regression', 'classification'], state='readonly', width=14)
        mode_combo.pack(side='left')
        self.tune_var = tk.BooleanVar(value=False)
        tune_chk = ttk.Checkbutton(btn_box, text='Enable Hyperparameter Tuning', variable=self.tune_var)
        tune_chk.pack(side='left', padx=10)
        self.metrics_frame = ttk.Frame(top_bar, style='Card.TFrame')
        self.metrics_frame.pack(side='right')
        self.lbl_mae = ttk.Label(self.metrics_frame, text='MAE: -- m', style='Bold.TLabel', foreground=self.colors['green'])
        self.lbl_mae.pack(side='left', padx=8)
        self.lbl_r2 = ttk.Label(self.metrics_frame, text='R²: --', style='Bold.TLabel', foreground=self.colors['accent'])
        self.lbl_r2.pack(side='left', padx=8)
        self.lbl_zone_acc = ttk.Label(self.metrics_frame, text='Zone: --%', style='Bold.TLabel', foreground=self.colors['purple'])
        self.lbl_zone_acc.pack(side='left', padx=8)
        self.lbl_samples = ttk.Label(self.metrics_frame, text='Windows: --', style='Bold.TLabel', foreground=self.colors['yellow'])
        self.lbl_samples.pack(side='left', padx=8)
        progress_box = ttk.Frame(self.tab_train, padding=(0, 5))
        progress_box.pack(fill='x', pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_box, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(0, 5))
        status_bar = ttk.Frame(progress_box)
        status_bar.pack(fill='x')
        self.lbl_status = ttk.Label(status_bar, text="System Ready. Click 'RUN END-TO-END ML PIPELINE' to start.", font=('Segoe UI', 9, 'italic'), foreground=self.colors['subtext'])
        self.lbl_status.pack(side='left')
        self.lbl_timer = ttk.Label(status_bar, text='⏱️ Elapsed: 00:00 | ETA: --:--', font=('Segoe UI', 9, 'bold'), foreground=self.colors['accent'])
        self.lbl_timer.pack(side='right')
        split_frame = ttk.Frame(self.tab_train)
        split_frame.pack(fill='both', expand=True)
        left_box = ttk.Frame(split_frame, style='Card.TFrame', padding=10)
        left_box.pack(side='left', fill='both', expand=True, padx=(0, 10))
        ttk.Label(left_box, text='📋 Pipeline Execution Log', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        self.console_text = tk.Text(left_box, bg=self.colors['panel'], fg=self.colors['text'], insertbackground=self.colors['text'], font=('Consolas', 9), relief='flat', wrap='word', height=15)
        self.console_text.pack(fill='both', expand=True)
        right_box = ttk.Frame(split_frame, style='Card.TFrame', padding=10)
        right_box.pack(side='right', fill='both', expand=True)
        ttk.Label(right_box, text='📊 Model Accuracy Diagnostics', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        self.plot_canvas = tk.Label(right_box, bg=self.colors['panel'], text='No diagnostics loaded.\nRun pipeline to generate plots.', fg=self.colors['subtext'])
        self.plot_canvas.pack(fill='both', expand=True)
        lead_box = ttk.Frame(self.tab_train, style='Card.TFrame', padding=10)
        lead_box.pack(fill='x', pady=(10, 0))
        ttk.Label(lead_box, text='🏆 Super Learner Tournament Live Leaderboard', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        self.model_tree = ttk.Treeview(lead_box, columns=('model', 'status', 'mae', 'rmse', 'r2', 'cv_mae'), show='headings', height=5)
        self.model_tree.heading('model', text='Candidate Model')
        self.model_tree.heading('status', text='Status')
        self.model_tree.heading('mae', text='Test MAE (m)')
        self.model_tree.heading('rmse', text='RMSE (m)')
        self.model_tree.heading('r2', text='R² Score')
        self.model_tree.heading('cv_mae', text='CV MAE (m)')
        self.model_tree.column('model', width=180, anchor='w')
        self.model_tree.column('status', width=110, anchor='center')
        self.model_tree.column('mae', width=100, anchor='center')
        self.model_tree.column('rmse', width=100, anchor='center')
        self.model_tree.column('r2', width=90, anchor='center')
        self.model_tree.column('cv_mae', width=100, anchor='center')
        self.model_tree.pack(fill='x', expand=True)
        self.load_metadata_summary()
        self.load_plot_image()

    def build_audit_tab(self):
        top_audit = ttk.Frame(self.tab_audit, padding=(0, 5))
        top_audit.pack(fill='x', pady=(0, 10))
        ttk.Label(top_audit, text='Dataset Health Check & Recommended Actions', style='Header.TLabel').pack(side='left')
        ttk.Button(top_audit, text='🔄 Refresh Audit', command=self.refresh_dataset_audit, style='Success.TButton').pack(side='right')
        self.advice_box = ttk.Frame(self.tab_audit, style='Card.TFrame', padding=15)
        self.advice_box.pack(fill='x', pady=(0, 15))
        ttk.Label(self.advice_box, text='💡 Recommended Actions', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 5))
        self.advice_lbl = ttk.Label(self.advice_box, text='Analyzing dataset...', style='Bold.TLabel', wraplength=900)
        self.advice_lbl.pack(anchor='w')
        audit_split = ttk.Frame(self.tab_audit)
        audit_split.pack(fill='both', expand=True)
        cov_box = ttk.Frame(audit_split, style='Card.TFrame', padding=10)
        cov_box.pack(side='left', fill='both', expand=True, padx=(0, 10))
        ttk.Label(cov_box, text='🎯 Distance Coverage Status', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        self.cov_tree = ttk.Treeview(cov_box, columns=('dist', 'samples', 'status', 'advice'), show='headings', height=8)
        self.cov_tree.heading('dist', text='Distance (m)')
        self.cov_tree.heading('samples', text='Samples (Raw / Windows)')
        self.cov_tree.heading('status', text='Status')
        self.cov_tree.heading('advice', text='Recommendation')
        self.cov_tree.column('dist', width=100, anchor='center')
        self.cov_tree.column('samples', width=160, anchor='center')
        self.cov_tree.column('status', width=120, anchor='center')
        self.cov_tree.column('advice', width=220, anchor='w')
        self.cov_tree.pack(fill='both', expand=True)
        raw_box = ttk.Frame(audit_split, style='Card.TFrame', padding=10)
        raw_box.pack(side='right', fill='both', expand=True)
        ttk.Label(raw_box, text='📁 Raw Dataset CSV Files', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        self.file_tree = ttk.Treeview(raw_box, columns=('filename', 'size', 'distance', 'records'), show='headings', height=8)
        self.file_tree.heading('filename', text='CSV File')
        self.file_tree.heading('size', text='Size')
        self.file_tree.heading('distance', text='Distance')
        self.file_tree.heading('records', text='Records')
        self.file_tree.column('filename', width=180, anchor='w')
        self.file_tree.column('size', width=80, anchor='center')
        self.file_tree.column('distance', width=80, anchor='center')
        self.file_tree.column('records', width=90, anchor='center')
        self.file_tree.pack(fill='both', expand=True)

    def build_predict_tab(self):
        card = ttk.Frame(self.tab_predict, style='Card.TFrame', padding=20)
        card.pack(fill='both', expand=True)
        ttk.Label(card, text='🎯 Interactive Distance Estimator Tester', style='SubHeader.TLabel').pack(anchor='w', pady=(0, 15))
        ttk.Label(card, text='Test how your trained ML model artifact (XGBoost/CatBoost/RF) predicts physical distance based on live RSSI inputs.', style='Muted.TLabel').pack(anchor='w', pady=(0, 20))
        input_frame = ttk.Frame(card, style='Card.TFrame')
        input_frame.pack(fill='x', pady=10)
        ttk.Label(input_frame, text='Simulated RSSI (dBm):', style='Bold.TLabel').pack(side='left', padx=(0, 15))
        self.rssi_slider = ttk.Scale(input_frame, from_=-100, to=-30, value=-70, command=self.on_rssi_slider_change)
        self.rssi_slider.pack(side='left', fill='x', expand=True, padx=15)
        self.lbl_rssi_val = ttk.Label(input_frame, text='-70 dBm', font=('Segoe UI', 12, 'bold'), foreground=self.colors['yellow'])
        self.lbl_rssi_val.pack(side='right', padx=15)
        result_box = ttk.Frame(card, style='Panel.TFrame', padding=25)
        result_box.pack(fill='x', pady=30)
        ttk.Label(result_box, text='PREDICTED DISTANCE', font=('Segoe UI', 10, 'bold'), foreground=self.colors['subtext']).pack()
        self.lbl_pred_result = ttk.Label(result_box, text='-- meters', font=('Segoe UI', 32, 'bold'), foreground=self.colors['green'])
        self.lbl_pred_result.pack(pady=10)
        self.lbl_pred_detail = ttk.Label(result_box, text='Load or train model to test predictions.', style='Muted.TLabel')
        self.lbl_pred_detail.pack()

    def refresh_dataset_audit(self):
        if not os.path.exists(RAW_DATA_DIR):
            self.advice_lbl.config(text='⚠️ Raw data directory not found. Run collector first.', foreground=self.colors['red'])
            return
        raw_files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, 'dataset_*.csv')))
        latest_mtime = 0
        for fpath in raw_files:
            latest_mtime = max(latest_mtime, os.path.getmtime(fpath))
        dataset_mtime = 0
        if os.path.exists(DATASET_PATH):
            dataset_mtime = os.path.getmtime(DATASET_PATH)
        current_mtime = max(latest_mtime, dataset_mtime)
        if hasattr(self, '_last_audit_mtime') and self._last_audit_mtime >= current_mtime:
            return
        self._last_audit_mtime = current_mtime
        import csv
        for item in self.cov_tree.get_children():
            self.cov_tree.delete(item)
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        if not raw_files:
            self.advice_lbl.config(text="⚠️ No raw CSV files found. Connect ESP32 and click 'START RECORDING' in Collector.", foreground=self.colors['yellow'])
            return
        raw_counts = {d: 0 for d in TARGET_DISTANCES}
        raw_counts['Other'] = 0
        ml_window_counts = {d: 0 for d in TARGET_DISTANCES}
        for fpath in raw_files:
            fname = os.path.basename(fpath)
            size_kb = f'{os.path.getsize(fpath) / 1024:.1f} KB'
            records = 0
            file_dist = 'Unknown'
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    records = len(rows)
                    if rows and 'distance_m' in rows[0]:
                        try:
                            raw_dist = float(rows[0]['distance_m'])
                            nearest = min(TARGET_DISTANCES, key=lambda x: abs(x - raw_dist))
                            if abs(nearest - raw_dist) < 0.05:
                                file_dist = nearest
                                raw_counts[nearest] += records
                            else:
                                file_dist = raw_dist
                                raw_counts['Other'] += records
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass
            self.file_tree.insert('', 'end', values=(fname, size_kb, f'{file_dist}m' if isinstance(file_dist, (int, float)) else file_dist, records))
        if os.path.exists(DATASET_PATH):
            try:
                obs_df = pd.read_csv(DATASET_PATH)
                if 'distance_m' in obs_df.columns:
                    for d in TARGET_DISTANCES:
                        matched = obs_df[obs_df['distance_m'].apply(lambda val: abs(val - d) < 0.05)]
                        ml_window_counts[d] = len(matched)
            except Exception:
                pass
        else:
            for d in TARGET_DISTANCES:
                ml_window_counts[d] = max(0, (raw_counts[d] - 50) // 10 + 1) if raw_counts[d] >= 50 else 0
        missing_dists = []
        low_dists = []
        for d in TARGET_DISTANCES:
            raw_c = raw_counts[d]
            win_c = ml_window_counts[d]
            if raw_c == 0 or win_c == 0:
                status = '❌ MISSING'
                advice = 'Need 60s recording at this distance'
                missing_dists.append(f'{d}m')
            elif win_c < 100:
                status = '⚠️ LOW SAMPLES'
                advice = 'Record a bit more data (~60s)'
                low_dists.append(f'{d}m')
            else:
                status = '✅ GOOD'
                advice = 'Sufficient data available'
            self.cov_tree.insert('', 'end', values=(f'{d} m', f'{raw_c:,} pkts / {win_c:,} win', status, advice))
        if missing_dists:
            msg = f"⚠️ Dataset Incomplete: Missing distance(s): {', '.join(missing_dists)}.\n👉 Action: Set Collector GUI distance to {missing_dists[0]} and click START RECORDING for 60 seconds."
            fg = self.colors['yellow']
        elif low_dists:
            msg = f"🟡 Dataset Acceptable: Low ML window count for {', '.join(low_dists)}.\n👉 Action: Record another 30–60s for low distances, or click 'RUN END-TO-END ML PIPELINE' to train now!"
            fg = self.colors['accent']
        else:
            msg = "✅ Dataset Ready: Great ML window coverage across all required distance presets!\n👉 Action: Click '⚡ RUN END-TO-END ML PIPELINE' on Tab 1 to train your final production model."
            fg = self.colors['green']
        self.advice_lbl.config(text=msg, foreground=fg)

    def update_timer_loop(self):
        if not self.is_training or self.start_time is None:
            return
        now = time.time()
        elapsed = now - self.start_time
        elapsed_sec = int(elapsed)
        m, s = divmod(elapsed_sec, 60)
        h, m = divmod(m, 60)
        if h > 0:
            elapsed_fmt = f'{h:02d}:{m:02d}:{s:02d}'
        else:
            elapsed_fmt = f'{m:02d}:{s:02d}'
        pct = self.current_percent
        if not hasattr(self, 'progress_history') or self.progress_history is None:
            self.progress_history = []
        self.progress_history.append((now, pct))
        if len(self.progress_history) > 30:
            self.progress_history.pop(0)
        if elapsed < 4.0 or pct < 4:
            eta_fmt = 'Learning runtime...'
        elif pct >= 100:
            eta_fmt = '00:00'
        else:
            oldest_t, oldest_pct = self.progress_history[0]
            time_delta = now - oldest_t
            pct_delta = pct - oldest_pct
            if time_delta >= 1.5 and pct_delta > 0:
                speed_pct_per_sec = pct_delta / time_delta
                live_rem_sec = (100.0 - pct) / speed_pct_per_sec
            else:
                live_rem_sec = elapsed / (pct / 100.0) - elapsed
            hist_eta = self.stage_learner.compute_historical_eta(pct, elapsed)
            raw_rem_sec = 0.65 * hist_eta + 0.35 * live_rem_sec
            raw_rem_sec = max(0.0, min(7200.0, raw_rem_sec))
            if getattr(self, 'smoothed_eta_sec', None) is None:
                self.smoothed_eta_sec = raw_rem_sec
            else:
                self.smoothed_eta_sec = 0.15 * raw_rem_sec + 0.85 * self.smoothed_eta_sec
            rem_sec = int(self.smoothed_eta_sec)
            rm, rs = divmod(rem_sec, 60)
            rh, rm = divmod(rm, 60)
            if rh > 0:
                eta_fmt = f'≈ {rh:02d}:{rm:02d}:{rs:02d}'
            else:
                eta_fmt = f'≈ {rm:02d}:{rs:02d}'
        spinner = self.spinner_frames[self.anim_step % len(self.spinner_frames)]
        self.anim_step += 1
        if hasattr(self, 'lbl_timer'):
            self.lbl_timer.config(text=f'{spinner} Elapsed: {elapsed_fmt} | ETA: {eta_fmt}')
        if self.is_training:
            self.timer_job = self.root.after(200, self.update_timer_loop)

    def start_pipeline_thread(self):
        if self.is_training:
            return
        self.is_training = True
        self.start_time = time.time()
        self.current_percent = 0
        self.progress_history = []
        self.smoothed_eta_sec = None
        self.stage_start_times = {}
        self.stage_durations = {}
        self.current_stage_name = None
        self.anim_step = 0
        self.train_btn.config(state='disabled')
        self.progress_bar['mode'] = 'determinate'
        self.progress_bar['value'] = 0
        self.lbl_status.config(text='Initializing ML pipeline...', foreground=self.colors['accent'])
        if hasattr(self, 'lbl_timer'):
            self.lbl_timer.config(text='⠋ Elapsed: 00:00 | ETA: Learning runtime...', foreground=self.colors['accent'])
        self.console_text.delete('1.0', tk.END)
        self.update_timer_loop()
        thread = threading.Thread(target=self.run_pipeline_worker, daemon=True)
        thread.start()

    def run_pipeline_worker(self):
        try:
            pipeline_script = os.path.join(PROJECT_ROOT, 'pipeline.py')
            python_exe = sys.executable
            cmd = [python_exe, pipeline_script, '--mode', self.mode_var.get()]
            if self.tune_var.get():
                cmd.append('--tune')
            self.log_queue.put(f"[EXEC] Running: {' '.join(cmd)}\n\n")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=PROJECT_ROOT)
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if isinstance(data, dict):
                        msg_type = data.get('type')
                        if msg_type == 'progress':
                            self.root.after(0, lambda d=data: self.update_progress(d))
                        elif msg_type == 'model_status':
                            self.root.after(0, lambda d=data: self.update_model_status(d))
                        else:
                            self.log_queue.put(line)
                    else:
                        self.log_queue.put(line)
                except (json.JSONDecodeError, TypeError):
                    self.log_queue.put(line)
            proc.wait()
            if proc.returncode == 0:
                self.log_queue.put('\n✅ PIPELINE SUCCESSFUL!\n')
                self.root.after(0, self.on_pipeline_success)
            else:
                self.log_queue.put(f'\n❌ PIPELINE ERROR (Exit Code {proc.returncode})\n')
                self.root.after(0, self.on_pipeline_error)
        except Exception as e:
            self.log_queue.put(f'\n❌ Exception: {str(e)}\n')
            self.root.after(0, self.on_pipeline_error)

    def update_model_status(self, data: dict):
        m_name = data.get('model_name', '')
        status = data.get('status', '')
        idx = data.get('index', 0)
        total = data.get('total', 0)
        pct = data.get('percent', 0)
        self.current_percent = pct
        if hasattr(self, 'model_tree'):
            existing_item = None
            for item in self.model_tree.get_children():
                if self.model_tree.item(item)['values'][0] == m_name:
                    existing_item = item
                    break
            if status == 'TRAINING':
                vals = (m_name, '⏳ TRAINING', '--', '--', '--', '--')
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert('', 'end', values=vals)
            elif status == 'SUCCESS':
                mae_str = f"{data.get('mae', 0.0):.4f}"
                rmse_str = f"{data.get('rmse', 0.0):.4f}"
                r2_str = f"{data.get('r2', 0.0):.4f}"
                cv_str = f"{data.get('cv_mae', 0.0):.4f}"
                vals = (m_name, '✅ SUCCESS', mae_str, rmse_str, r2_str, cv_str)
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert('', 'end', values=vals)
            elif status == 'FAILED':
                err = data.get('error', 'Error')
                vals = (m_name, '❌ FAILED', '--', '--', '--', err[:25])
                if existing_item:
                    self.model_tree.item(existing_item, values=vals)
                else:
                    self.model_tree.insert('', 'end', values=vals)
        self.progress_bar['mode'] = 'determinate'
        self.progress_bar['value'] = pct
        self.lbl_status.config(text=f'[{idx}/{total}] {status}: {m_name}', foreground=self.colors['accent'] if status == 'TRAINING' else self.colors['green'] if status == 'SUCCESS' else self.colors['red'])

    def update_progress(self, data: dict):
        percent = data.get('percent', 0)
        stage = data.get('stage', '')
        metrics = data.get('metrics', {})
        self.current_percent = percent
        now = time.time()
        if stage:
            if hasattr(self, 'current_stage_name') and self.current_stage_name and (self.current_stage_name != stage):
                prev = self.current_stage_name
                if prev in self.stage_start_times:
                    self.stage_durations[prev] = now - self.stage_start_times[prev]
            self.current_stage_name = stage
            if stage not in self.stage_start_times:
                self.stage_start_times[stage] = now
        self.progress_bar['mode'] = 'determinate'
        self.progress_bar['value'] = percent
        self.lbl_status.config(text=f'[{percent}%] {stage}', foreground=self.colors['accent'])
        if metrics:
            if 'mae' in metrics and metrics['mae'] > 0:
                self.lbl_mae.config(text=f"MAE: {metrics['mae']:.4f} m")
            if 'r2' in metrics and metrics['r2'] != 0:
                self.lbl_r2.config(text=f"R²: {metrics['r2']:.4f}")
            if 'zone_acc' in metrics and metrics['zone_acc'] > 0:
                self.lbl_zone_acc.config(text=f"Zone: {metrics['zone_acc']:.1f}%")
            if 'windows' in metrics and metrics['windows'] > 0:
                self.lbl_samples.config(text=f"Windows: {metrics['windows']:,}")
        self.console_text.insert(tk.END, f'[{percent}%] {stage}\n')
        self.console_text.see(tk.END)

    def auto_refresh_audit(self):
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
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        if hasattr(self, 'current_stage_name') and self.current_stage_name and (self.current_stage_name in self.stage_start_times):
            self.stage_durations[self.current_stage_name] = time.time() - self.stage_start_times[self.current_stage_name]
        if hasattr(self, 'stage_learner') and self.stage_durations:
            self.stage_learner.record_run(self.stage_durations)
        self.progress_bar['value'] = 100
        self.train_btn.config(state='normal')
        if self.start_time:
            total_sec = int(time.time() - self.start_time)
            m, s = divmod(total_sec, 60)
            h, m = divmod(m, 60)
            time_str = f'{h:02d}:{m:02d}:{s:02d}' if h > 0 else f'{m:02d}:{s:02d}'
            if hasattr(self, 'lbl_timer'):
                self.lbl_timer.config(text=f'✅ Finished in {time_str}', foreground=self.colors['green'])
        self.lbl_status.config(text='✅ Model training and evaluation complete!', foreground=self.colors['green'])
        self.load_trained_model()
        self.load_metadata_summary()
        self.load_plot_image()
        self.refresh_dataset_audit()
        if hasattr(self, 'embedded_dashboard'):
            self.embedded_dashboard.refresh()
        if hasattr(self, 'rssi_slider'):
            self.on_rssi_slider_change(self.rssi_slider.get())
        self.open_results_dashboard()

    def on_pipeline_error(self):
        self.is_training = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.progress_bar['value'] = 0
        self.train_btn.config(state='normal')
        if self.start_time:
            total_sec = int(time.time() - self.start_time)
            m, s = divmod(total_sec, 60)
            h, m = divmod(m, 60)
            time_str = f'{h:02d}:{m:02d}:{s:02d}' if h > 0 else f'{m:02d}:{s:02d}'
            if hasattr(self, 'lbl_timer'):
                self.lbl_timer.config(text=f'❌ Stopped at {time_str}', foreground=self.colors['red'])
        self.lbl_status.config(text='❌ Training failed. Check log console below.', foreground=self.colors['red'])

    def load_metadata_summary(self):
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, 'r') as f:
                    meta = json.load(f)
                metrics = meta.get('metrics', {})
                self.lbl_mae.config(text=f"MAE: {metrics.get('test_mae', '--')} m")
                self.lbl_r2.config(text=f"R²: {metrics.get('test_r2', '--')}")
                self.lbl_samples.config(text=f"Windows: {meta.get('train_samples', 0) + meta.get('test_samples', 0)}")
                zone_meta = meta.get('zone_classification', {})
                if zone_meta:
                    zone_acc = zone_meta.get('zone_accuracy', '--')
                    self.lbl_zone_acc.config(text=f'Zone: {zone_acc}%')
                else:
                    self.lbl_zone_acc.config(text=f'Zone: N/A')
                if hasattr(self, 'embedded_dashboard'):
                    self.embedded_dashboard.refresh()
            except Exception:
                pass

    def load_plot_image(self):
        if os.path.exists(DIAGNOSTIC_PLOT_PATH):
            try:
                img = Image.open(DIAGNOSTIC_PLOT_PATH)
                img = img.resize((480, 400), Image.Resampling.LANCZOS)
                self.photo_img = ImageTk.PhotoImage(img)
                self.plot_canvas.config(image=self.photo_img, text='')
            except Exception as e:
                self.plot_canvas.config(text=f'Error displaying image: {e}')

    def on_rssi_slider_change(self, val):
        rssi_val = float(val)
        self.lbl_rssi_val.config(text=f'{int(rssi_val)} dBm')
        if self.model is not None and self.scaler is not None and (self.metadata is not None):
            try:
                feature_cols = self.metadata.get('feature_cols', [])
                sim_features = build_simulated_feature_dict(rssi_val)
                X_vec = [sim_features.get(col, 0.0) for col in feature_cols]
                X = np.array([X_vec], dtype=float)
                X_scaled = self.scaler.transform(X)
                d_pred = float(self.model.predict(X_scaled)[0])
                d_pred = max(0.1, min(25.0, d_pred))
                champ_name = self.metadata.get('champion_model', 'Trained ML Model')
                mae = self.metadata.get('metrics', {}).get('test_mae', '--')
                zone_info = ''
                if self.zone_model is not None:
                    try:
                        zone_pred = self.zone_model.predict(X_scaled)[0]
                        zone_info = f' | Zone Class: {zone_pred}'
                    except Exception:
                        pass
                self.lbl_pred_result.config(text=f'{d_pred:.2f} meters')
                self.lbl_pred_detail.config(text=f'🤖 Real ML Model ({champ_name}) | Test MAE: {mae}m{zone_info}')
                return
            except Exception as e:
                pass
        import math
        n = 2.5
        d_est = 10 ** ((-60 - rssi_val) / (10 * n))
        d_est = max(0.3, min(10.0, d_est))
        self.lbl_pred_result.config(text=f'{d_est:.2f} meters')
        self.lbl_pred_detail.config(text='⚠️ Log-Distance Fallback (Train ML model to enable real pipeline predictions)')

def main():
    root = tk.Tk()
    app = MLTrainingStudio(root)
    root.mainloop()
if __name__ == '__main__':
    main()
