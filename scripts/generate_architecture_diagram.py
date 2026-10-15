"""Generate high-resolution (300 DPI PNG + vector SVG) academic architecture diagram
for the BLE Indoor Positioning dissertation.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_diagram(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    svg_path = os.path.join(output_dir, "architecture_pipeline_diagram.svg")
    png_path = os.path.join(output_dir, "architecture_pipeline_diagram.png")

    fig = plt.figure(figsize=(16, 11), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # Color Palette - Professional Academic / Engineering
    c_bg = "#F8FAFC"       # Slate 50
    c_border = "#0F172A"   # Slate 900
    c_layer1 = "#EFF6FF"   # Blue 50
    c_layer1_b = "#2563EB" # Blue 600
    c_layer2 = "#ECFDF5"   # Emerald 50
    c_layer2_b = "#059669" # Emerald 600
    c_layer3 = "#FAF5FF"   # Purple 50
    c_layer3_b = "#7C3AED" # Purple 600
    c_layer4 = "#FFFBEB"   # Amber 50
    c_layer4_b = "#D97706" # Amber 600
    c_layer5 = "#F1F5F9"   # Slate 100
    c_layer5_b = "#475569" # Slate 600

    c_box = "#FFFFFF"
    c_box_edge = "#334155"

    # Figure Background
    fig.patch.set_facecolor("#FFFFFF")

    # Title Banner
    ax.text(8.0, 10.55, "AI-Assisted BLE Indoor Positioning Platform", 
            fontsize=18, fontweight="bold", ha="center", va="center", color="#0F172A")
    ax.text(8.0, 10.22, "Physical Hardware Acquisition, Machine Learning Ranging, 2D Trajectory Kalman Filtering & Telemetry Architecture", 
            fontsize=10.5, style="italic", ha="center", va="center", color="#475569")

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 1: EDGE HARDWARE & WIRELESS ACQUISITION LAYER
    # ─────────────────────────────────────────────────────────────────────────
    l1_box = patches.FancyBboxPatch((0.5, 7.8), 15.0, 2.1, boxstyle="round,pad=0.15", 
                                   facecolor=c_layer1, edgecolor=c_layer1_b, linewidth=1.8)
    ax.add_patch(l1_box)
    ax.text(0.8, 9.65, "LAYER 1: PHYSICAL EDGE HARDWARE & WIRELESS ACQUISITION (ESP-IDF / NimBLE)", 
            fontsize=10, fontweight="bold", color=c_layer1_b, va="center")

    # Node boxes (A, B, C, D) + Target Tag
    tag_box = patches.FancyBboxPatch((0.8, 8.1), 2.7, 1.3, boxstyle="round,pad=0.1", 
                                     facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(tag_box)
    ax.text(2.15, 9.15, "Target BLE 5.0 Beacon Tag", fontsize=9, fontweight="bold", ha="center", color="#0F172A")
    ax.text(2.15, 8.85, "MAC: 52:06:26:03:01:DA", fontsize=7.5, family="monospace", ha="center", color="#1E293B")
    ax.text(2.15, 8.55, "Tx Power: 0 dBm (Ref: -77.8 dBm)", fontsize=7.5, ha="center", color="#475569")
    ax.text(2.15, 8.28, "Adv Interval: 100ms (10 Hz, Ch 37-39)", fontsize=7.2, ha="center", color="#475569")

    # Anchors Box
    anchors_box = patches.FancyBboxPatch((4.0, 8.1), 7.4, 1.3, boxstyle="round,pad=0.1", 
                                         facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(anchors_box)
    ax.text(7.7, 9.15, "4x Autonomous ESP32-WROOM-32 Anchor Nodes (Dual-Role Stack)", 
            fontsize=9, fontweight="bold", ha="center", color="#0F172A")
    ax.text(7.7, 8.85, "Node A (SW: 0,0m) • Node B (SE: 5,0m) • Node C (NW: 0,5m) • Node D (NE: 5,5m) | H = 0.96m", 
            fontsize=7.5, ha="center", color="#1E293B")
    ax.text(7.7, 8.55, "Passive Scanning: 50ms interval, 30ms window (60% Duty Cycle) • Duplicate Filter: Disabled (0)", 
            fontsize=7.5, ha="center", color="#475569")
    ax.text(7.7, 8.28, "Edge MAC Whitelist: Drops foreign frames • Dual Transport: Wi-Fi UDP :5005 & UART 115200", 
            fontsize=7.2, ha="center", color="#475569")

    # Ingestion Receiver Box
    ingest_box = patches.FancyBboxPatch((11.9, 8.1), 3.3, 1.3, boxstyle="round,pad=0.1", 
                                        facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(ingest_box)
    ax.text(13.55, 9.15, "UDP Ingestion Worker", fontsize=9, fontweight="bold", ha="center", color="#0F172A")
    ax.text(13.55, 8.85, "Zero-Config Dynamic Auto-Discovery", fontsize=7.5, ha="center", color="#1E293B")
    ax.text(13.55, 8.55, "Verbatim Socket Log (.raw.log)", fontsize=7.5, ha="center", color="#475569")
    ax.text(13.55, 8.28, "Canonical Dataset Persistence (.csv)", fontsize=7.2, ha="center", color="#475569")

    # Arrows Layer 1
    ax.annotate("", xy=(4.0, 8.75), xytext=(3.5, 8.75), 
                arrowprops=dict(arrowstyle="->", color=c_layer1_b, lw=2.0))
    ax.annotate("", xy=(11.9, 8.75), xytext=(11.4, 8.75), 
                arrowprops=dict(arrowstyle="->", color=c_layer1_b, lw=2.0))

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2: FEATURE ENGINEERING & IN-FOLD DATA PREPARATION
    # ─────────────────────────────────────────────────────────────────────────
    l2_box = patches.FancyBboxPatch((0.5, 5.5), 15.0, 1.95, boxstyle="round,pad=0.15", 
                                   facecolor=c_layer2, edgecolor=c_layer2_b, linewidth=1.8)
    ax.add_patch(l2_box)
    ax.text(0.8, 7.22, "LAYER 2: DATA PREPROCESSING & FEATURE ENGINEERING PIPELINE", 
            fontsize=10, fontweight="bold", color=c_layer2_b, va="center")

    w_box = patches.FancyBboxPatch((0.8, 5.75), 3.2, 1.25, boxstyle="round,pad=0.1", 
                                   facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(w_box)
    ax.text(2.4, 6.75, "1000ms Rolling Time Windows", fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(2.4, 6.45, "Window Size: 1000ms | Stride: 1000ms", fontsize=7.3, ha="center", color="#1E293B")
    ax.text(2.4, 6.18, "Strict Chronological Monotonic Sorting", fontsize=7.2, ha="center", color="#475569")
    ax.text(2.4, 5.92, "IsolationForest Outlier Filter (3% Contam)", fontsize=7.0, ha="center", color="#059669")

    f66_box = patches.FancyBboxPatch((4.5, 5.75), 4.9, 1.25, boxstyle="round,pad=0.1", 
                                     facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(f66_box)
    ax.text(6.95, 6.75, "66-Feature 1D Distance Pipeline", fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(6.95, 6.45, "18 Moments (Mean, Std, Skew, Kurtosis, Percentiles)", fontsize=7.2, ha="center", color="#1E293B")
    ax.text(6.95, 6.18, "7 Dynamic Deltas • 6 RF Energy Histograms (-100..-30dBm)", fontsize=7.0, ha="center", color="#475569")
    ax.text(6.95, 5.92, "15 Cross-Window (Vel, Accel) • 16 Environmental Factors", fontsize=7.0, ha="center", color="#475569")

    f21_box = patches.FancyBboxPatch((9.9, 5.75), 5.3, 1.25, boxstyle="round,pad=0.1", 
                                     facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(f21_box)
    ax.text(12.55, 6.75, "21-Feature Multi-Anchor 2D Coordinate Matrix", fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(12.55, 6.45, "4x Anchor RSSI (A1-A4) • 4x Packet Age (age_s) • 4x Presence Flags", fontsize=7.2, ha="center", color="#1E293B")
    ax.text(12.55, 6.18, "6x Spatial Differential Channels (North-South, East-West, Diagonals)", fontsize=7.0, ha="center", color="#475569")
    ax.text(12.55, 5.92, "Mean / Std All RSSI • Active Anchor Count (n_anchors_active)", fontsize=7.0, ha="center", color="#475569")

    # Arrows L1 -> L2
    ax.annotate("", xy=(8.0, 7.8), xytext=(8.0, 7.45), 
                arrowprops=dict(arrowstyle="<-", color=c_border, lw=1.8))
    ax.annotate("", xy=(4.5, 6.37), xytext=(4.0, 6.37), 
                arrowprops=dict(arrowstyle="->", color=c_layer2_b, lw=1.8))
    ax.annotate("", xy=(9.9, 6.37), xytext=(9.4, 6.37), 
                arrowprops=dict(arrowstyle="->", color=c_layer2_b, lw=1.8))

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 3: INFERENCE & LOCALIZATION SOLVER LAYER
    # ─────────────────────────────────────────────────────────────────────────
    l3_box = patches.FancyBboxPatch((0.5, 3.2), 15.0, 1.95, boxstyle="round,pad=0.15", 
                                   facecolor=c_layer3, edgecolor=c_layer3_b, linewidth=1.8)
    ax.add_patch(l3_box)
    ax.text(0.8, 4.92, "LAYER 3: HYBRID LOCALIZATION ENGINE (DIRECT REGRESSION + MULTILATERATION FALLBACK)", 
            fontsize=10, fontweight="bold", color=c_layer3_b, va="center")

    ml_coord_box = patches.FancyBboxPatch((0.8, 3.45), 6.5, 1.25, boxstyle="round,pad=0.1", 
                                          facecolor=c_box, edgecolor=c_layer3_b, linewidth=1.6)
    ax.add_patch(ml_coord_box)
    ax.text(4.05, 4.45, "PRIMARY: MultiOutput ExtraTrees 2D Regressor", fontsize=8.5, fontweight="bold", ha="center", color=c_layer3_b)
    ax.text(4.05, 4.15, "Model: coordinate_regressor.joblib (n_est=250, depth=12) • Scaler: RobustScaler", fontsize=7.2, ha="center", color="#0F172A")
    ax.text(4.05, 3.88, "Zero-Leakage 5-Fold GroupKFold on session_id (Overlap = 0)", fontsize=7.2, ha="center", color="#475569")
    ax.text(4.05, 3.60, "Out-of-Fold Error: Median 0.406m • Mean 0.885m • 69.96% Sub-1.0m", fontsize=7.2, fontweight="bold", ha="center", color="#7C3AED")

    fallback_box = patches.FancyBboxPatch((8.0, 3.45), 7.2, 1.25, boxstyle="round,pad=0.1", 
                                          facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(fallback_box)
    ax.text(11.6, 4.45, "FALLBACK: Distance Estimation + Levenberg-Marquardt Trilateration", fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(11.6, 4.15, "Model: HistGradientBoosting Regressor (Test MAE: 1.273m vs Physics 4.608m, +72.4%)", fontsize=7.2, ha="center", color="#1E293B")
    ax.text(11.6, 3.88, "Solver: Scipy Least-Squares with Soft L1 / Cauchy Robust Loss (loss='soft_l1')", fontsize=7.2, ha="center", color="#475569")
    ax.text(11.6, 3.60, "GDOP Evaluation (1.2-1.8) • Automatic Degraded Mode (4 -> 3 -> 2 -> 1 Anchors)", fontsize=7.2, ha="center", color="#475569")

    # Connect L2 to L3
    ax.annotate("", xy=(4.05, 3.45), xytext=(4.05, 5.5), 
                arrowprops=dict(arrowstyle="<-", color=c_border, lw=1.8))
    ax.annotate("", xy=(11.6, 3.45), xytext=(11.6, 5.5), 
                arrowprops=dict(arrowstyle="<-", color=c_border, lw=1.8))

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 4: 2D ADAPTIVE KALMAN SMOOTHING & HYSTERESIS
    # ─────────────────────────────────────────────────────────────────────────
    l4_box = patches.FancyBboxPatch((0.5, 1.55), 15.0, 1.35, boxstyle="round,pad=0.15", 
                                   facecolor=c_layer4, edgecolor=c_layer4_b, linewidth=1.8)
    ax.add_patch(l4_box)
    ax.text(0.8, 2.7, "LAYER 4: 2D ADAPTIVE KALMAN FILTER & SPATIAL HYSTERESIS ENGINE", 
            fontsize=10, fontweight="bold", color=c_layer4_b, va="center")

    kf_box = patches.FancyBboxPatch((0.8, 1.7), 8.5, 0.85, boxstyle="round,pad=0.1", 
                                    facecolor=c_box, edgecolor=c_layer4_b, linewidth=1.4)
    ax.add_patch(kf_box)
    ax.text(5.05, 2.32, "2D Constant Velocity Kalman Filter: x_k = [x, y, v_x, v_y]^T", 
            fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(5.05, 2.05, "Dynamic dt: Monotonic clock tracking [0.01s, 5.0s] • Process Noise Q = diag(0.05) • Meas Noise R = diag(0.80)", 
            fontsize=7.2, ha="center", color="#1E293B")
    ax.text(5.05, 1.82, "Results: 70.2% Multilateration Jitter Reduced (0.382m -> 0.114m) • 40.8% ML Jitter Reduced • Execution: 0.06 ms", 
            fontsize=7.2, fontweight="bold", ha="center", color="#B45309")

    hyst_box = patches.FancyBboxPatch((9.7, 1.7), 5.5, 0.85, boxstyle="round,pad=0.1", 
                                      facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(hyst_box)
    ax.text(12.45, 2.32, "Spatial Room Hysteresis & Geofencing", fontsize=8.5, fontweight="bold", ha="center", color="#0F172A")
    ax.text(12.45, 2.05, "Margin: +/- 0.3m Deadband on Room Boundary (x=5.0m, y=5.0m)", fontsize=7.2, ha="center", color="#1E293B")
    ax.text(12.45, 1.82, "Eliminates boundary flicker • Geofence alert state machine", fontsize=7.2, ha="center", color="#475569")

    # Connect L3 to L4
    ax.annotate("", xy=(8.0, 1.55), xytext=(8.0, 3.2), 
                arrowprops=dict(arrowstyle="<-", color=c_border, lw=1.8))

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 5: PERSISTENCE, WEBSOCKET TELEMETRY & DASHBOARD
    # ─────────────────────────────────────────────────────────────────────────
    l5_box = patches.FancyBboxPatch((0.5, 0.1), 15.0, 1.15, boxstyle="round,pad=0.15", 
                                   facecolor=c_layer5, edgecolor=c_layer5_b, linewidth=1.8)
    ax.add_patch(l5_box)
    ax.text(0.8, 1.05, "LAYER 5: ENTERPRISE PERSISTENCE, TELEMETRY & OPERATIONS DASHBOARD", 
            fontsize=10, fontweight="bold", color=c_layer5_b, va="center")

    db_box = patches.FancyBboxPatch((0.8, 0.22), 4.4, 0.72, boxstyle="round,pad=0.08", 
                                    facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(db_box)
    ax.text(3.0, 0.72, "SQLite WAL Persistence (ACID)", fontsize=8.2, fontweight="bold", ha="center", color="#0F172A")
    ax.text(3.0, 0.50, "PRAGMA journal_mode=WAL • synchronous=NORMAL", fontsize=6.8, ha="center", color="#1E293B")
    ax.text(3.0, 0.32, "Tables: positions, assets, geofence_alerts", fontsize=6.8, ha="center", color="#475569")

    ws_box = patches.FancyBboxPatch((5.6, 0.22), 4.4, 0.72, boxstyle="round,pad=0.08", 
                                    facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(ws_box)
    ax.text(7.8, 0.72, "FastAPI WebSocket Telemetry (/ws)", fontsize=8.2, fontweight="bold", ha="center", color="#0F172A")
    ax.text(7.8, 0.50, "Debounced broadcast rate: <= 10 Hz (asyncio.sleep 0.1s)", fontsize=6.8, ha="center", color="#1E293B")
    ax.text(7.8, 0.32, "Push JSON: (x, y, uncertainty, gdop, room, alert)", fontsize=6.8, ha="center", color="#475569")

    ui_box = patches.FancyBboxPatch((10.4, 0.22), 4.8, 0.72, boxstyle="round,pad=0.08", 
                                    facecolor=c_box, edgecolor=c_box_edge, linewidth=1.2)
    ax.add_patch(ui_box)
    ax.text(12.8, 0.72, "React 19 + Tailwind v4 Dashboard (:3000)", fontsize=8.2, fontweight="bold", ha="center", color="#0F172A")
    ax.text(12.8, 0.50, "Real-time SVG Canvas • Cartesian-to-SVG Inversion", fontsize=6.8, ha="center", color="#1E293B")
    ax.text(12.8, 0.32, "Ring Buffers: slice(0,60) events • Desktop Control Console", fontsize=6.8, ha="center", color="#475569")

    # Connect L4 to L5
    ax.annotate("", xy=(8.0, 0.1), xytext=(8.0, 1.55), 
                arrowprops=dict(arrowstyle="<-", color=c_border, lw=1.8))

    plt.tight_layout()
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated SVG: {svg_path}")
    print(f"Generated PNG (300 DPI): {png_path}")

if __name__ == "__main__":
    generate_diagram("ble-indoor-positioning/reports")
