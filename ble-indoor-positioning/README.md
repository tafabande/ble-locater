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

| Milestone / Phase | Total Windows | Features | Champion Model | Test MAE (m) | Test R² | Zone Acc (%) | vs Physics Baseline |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **Phase 1: Initial Baseline** | 5,420 | 30 | `RandomForest` | `0.6724m` | `0.3710` | -- | +73.1% |
| **Phase 2: Temporal Expansion** | 14,200 | 38 | `XGBoost (Tuned)` | `0.2643m` | `0.8688` | `88.5%` | +89.4% |
| **Phase 3: 60 Domain Features** | 24,555 | 60 | `CatBoost` | `0.2315m` | `0.9102` | `94.2%` | +90.6% |
| **Phase 4: Zero-Leakage Pipeline CV** | 24,555 | 60 | `CatBoost / ExtraTrees` | **`0.2184m`** | **`0.9215`** | **`96.5%`** | **+91.1%** |

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

---

## 🛠 Project Structure

```
final year/
├── ble tracker/
│   └── collector/
│       ├── collector.py           # Multi-manager ESP32 serial data collector GUI & HTTP streamer
│       └── data/raw/              # 34 Raw BLE recording CSV datasets
├── ble-indoor-positioning/
│   ├── datasets/
│   │   └── observations.csv       # Engineered 60-feature ML observation windows dataset
│   ├── feature_engineering/
│   │   └── engineer.py            # 60-feature extraction engine & Dataset Audit module
│   ├── training/
│   │   └── train.py               # Ultra-Robust Super Learner Tournament & Experiment Logger
│   ├── models/                    # Trained model artifacts (.joblib) & metadata (.json)
│   ├── reports/
│   │   ├── experiment_evolution_log.md  # Chronological experiment evolution log
│   │   ├── experiment_evolution_log.json# Machine-readable run history
│   │   └── model_diagnostics.png  # V2 8-panel diagnostic plot grid
│   ├── pipeline.py                # Pipeline entry point with real-time JSON progress event stream
│   └── training_gui.py            # Interactive Model Studio GUI & Live Tournament Leaderboard
```
