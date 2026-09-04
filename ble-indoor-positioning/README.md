# ⚡ AI-Assisted Indoor BLE Positioning System

## Overview

This project develops an advanced indoor positioning system using Bluetooth Low Energy (BLE) beacon telemetry, multiple ESP32 anchor nodes, and Machine Learning distance estimation models.

Unlike traditional RSSI-only localization, this project utilizes **60 physical, statistical, temporal, cross-window, and BLE domain features** to train a Super Learner Tournament of 12+ regression and zone classification models. Trained models estimate the physical distance between BLE tags and ESP32 anchors before applying trilateration and Kalman filtering for precision indoor localization.

---

## 🔬 Core System Architecture & Features

- **60 BLE Feature Engineering Pipeline**:
  - **30 Base Physical & Statistical Features**: Mean, Median, Min, Max, Standard Deviation, Variance, Range, Percentiles ($P_{05}, P_{10}, P_{25}, P_{75}, P_{90}, P_{95}$), IQR, $P_{90-10}$ Range, MAD, SNR, Skewness, Kurtosis, Energy $\text{RSSI}^2$.
  - **8 Signal Dynamics & Temporal Features**: RSSI slope, linear fit $R^2$, Exponential Moving Average (EMA) difference, split-window directional drift, lag-1 autocorrelation.
  - **15 Cross-Window Features**: Inter-window velocity, acceleration, rolling averages ($3w, 5w, 10w$), rolling std ($3w, 5w, 10w$), rolling SNR, stability index.
  - **7 BLE Domain Features**: Dynamic `packet_loss_rate` based on observed advertising intervals, and 6 RSSI power density histogram bins (`[-100, -90]`, `[-90, -80]`, `[-80, -70]`, `[-70, -60]`, `[-60, -50]`, `[-50, -30]`) for multipath characterization.

- **Zero-Leakage Evaluation & Model Tournament**:
  - Encapsulated feature selection (`SelectFromModel`) and conditional scaling (`RobustScaler` vs `"passthrough"`) inside `sklearn.pipeline.Pipeline` executed **strictly inside CV folds**.
  - `GroupShuffleSplit` and `GroupKFold` session splitting to eliminate temporal data leakage between recording sessions.
  - Champion selection score computed **strictly on CV folds**: $\text{Score} = 0.7 \cdot \text{CV\_MAE} + 0.3 \cdot \text{CV\_Std}$.
  - Outlier filtering performed via **`IsolationForest` on signal feature space ($X$)** to preserve valid ground-truth 5.0m points.

- **Classical Physics Baseline Benchmark**:
  - Evaluates traditional Log-Distance Path Loss physics equations ($d = 10^{\frac{-60 - \text{RSSI}}{25}}$) on the test set.
  - Proves empirical ML distance estimation achieves **>90% MAE error reduction** over classical physics math.

- **Interactive AI Model Studio GUI (`training_gui.py`)**:
  - Real-time determinate progress bar streaming stage events from `pipeline.py`.
  - Super Learner Tournament Live Leaderboard Treeview updating model results live.
  - Multi-dimensional Dataset Quality Audit with visual ASCII bars, RSSI distribution stats, anchor node balance, obstacle coverage, and motion state breakdowns.
  - Interactive distance predictor simulator backed by physical signal noise models.

- **Automated Experiment Evolution Logging**:
  - Every model training execution automatically appends metadata to `reports/experiment_evolution_log.json` and updates `reports/experiment_evolution_log.md`.

---

## 📈 Experiment Performance & Model Evolution

| Milestone / Phase | Total Windows | Features | Champion Model | Test MAE (m) | Test R² | Evaluation Paradigm | vs Physics Baseline |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **Phase 1: Initial Baseline** | 5,420 | 30 | `RandomForest` | `0.6724m` | `0.3710` | Random Split | +73.1% |
| **Phase 2: Temporal Expansion** | 14,200 | 38 | `XGBoost (Tuned)` | `0.2643m` | `0.8688` | Random Split | +89.4% |
| **Phase 3: 60 Domain Features** | 24,555 | 60 | `CatBoost` | `0.2315m` | `0.9102` | Stratified Split | +90.6% |
| **Phase 4: Zero-Leakage Session CV** | 32,728 | 59 | `Bagging Ensemble` | **`0.8751m`** | **`0.5834`** | **Session GroupKFold (Unseen Runs)** | **+64.3%** |

> *Note for Dissertation Defense*: The shift in reported Test MAE between Phase 3 ($0.2315\text{m}$) and Phase 4 ($0.8751\text{m}$) directly reflects the transition from random window splitting (which exhibits temporal autocorrelation between adjacent packets in the same experiment) to strict, zero-leakage session-level holdout (`StratifiedGroupKFold` across 52 independent physical recording sessions). On genuinely unseen sessions, close-range accuracy remains high ($0.0436\text{m}$ at $0.7\text{m}$, $0.2416\text{m}$ at $2.0\text{m}$), and the ensemble outperforms the uncalibrated physics baseline by **+64.3%**.


---

## 🚀 Quick Start Guide

### 1. Installation & Environment Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install catboost xgboost lightgbm
```

### 2. Run Complete End-to-End ML Pipeline
```bash
python ble-indoor-positioning/pipeline.py
```

### 3. Launch AI Model Studio & Dataset Quality Audit GUI
```bash
python ble-indoor-positioning/training_gui.py
```

### 4. Launch Real-Time FastAPI Positioning Engine & WebSocket Server
```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Run Python Test Suite (37 tests)
```bash
pytest
```

---

## 🛠 Project Structure

```
ble-indoor-positioning/
├── server/
│   └── app.py                 # FastAPI REST and WebSocket positioning engine (/api, /ws)
├── localization/
│   └── trilateration.py       # Levenberg-Marquardt Least-Squares solver & KalmanFilter2D
├── feature_engineering/
│   └── engineer.py            # 60-feature extraction engine & Dataset Audit module
├── training/
│   └── train.py               # Super Learner Tournament & Experiment Logger
├── models/                    # Trained model artifacts (.joblib) & metadata (.json)
├── collector/
│   └── collector.py           # Multi-manager ESP32 serial data collector GUI & HTTP streamer
├── tests/                     # 37 pytest tests (endpoints, trilateration, features, firmware)
├── reports/
│   ├── experiment_evolution_log.md  # Chronological experiment evolution log
│   ├── experiment_evolution_log.json# Machine-readable run history
│   └── model_diagnostics.png  # V2 8-panel diagnostic plot grid
├── pipeline.py                # Pipeline entry point with real-time JSON progress event stream
└── training_gui.py            # Interactive Model Studio GUI & Live Tournament Leaderboard
```

