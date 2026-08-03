# 📈 BLE Indoor Positioning — Experiment Performance & Model Evolution Log

> **Automated Scientific Performance Tracking System**
> This log records chronological model training iterations, dataset statistics, feature engineering milestones, and empirical validation metrics over time.

## 🏆 Project Progression & Milestone Overview

| Timestamp | Phase / Milestone | Windows | Features | Champion Model | Test MAE (m) | Test R² | Zone Acc (%) | vs Physics Baseline |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| `2026-07-31 20:00` | **Phase 1 (Legacy Initial Baseline)** | 5,420 | 30 | `RandomForestRegressor` | **0.6724m** | **0.3710** | -- | **+73.1%** |
| `2026-08-01 16:00` | **Phase 2 (Feature Expansion & Temporal Windowing)** | 14,200 | 38 | `XGBoost (Deep Tuned)` | **0.2643m** | **0.8688** | 88.5% | **+89.4%** |
| `2026-08-03 12:00` | **Phase 3 (Session GroupKFold & 60 BLE Domain Features)** | 24,555 | 60 | `CatBoost Regressor` | **0.2315m** | **0.9102** | 94.2% | **+90.6%** |
| `2026-08-03 17:38` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 23,818 | 54 | `ElasticNet` | **0.9513m** | **-0.8772** | 46.3% | **+61.2%** |

## 🔬 Chronological Experiment Milestone Log

### Iteration 1: Phase 1 (Legacy Initial Baseline)
- **Timestamp**: `2026-07-31 20:00:00`
- **Dataset Size**: `5,420` observation windows
- **Feature Set**: `30` extracted channels
- **Champion Model**: `RandomForestRegressor`
- **Performance Metrics**: Test MAE = `0.6724m` | RMSE = `0.8912m` | R² = `0.3710`
- **Key Methodology / Breakthrough**: Initial raw packet aggregation, basic RSSI mean/std features, random train/test split.

### Iteration 2: Phase 2 (Feature Expansion & Temporal Windowing)
- **Timestamp**: `2026-08-01 16:00:00`
- **Dataset Size**: `14,200` observation windows
- **Feature Set**: `38` extracted channels
- **Champion Model**: `XGBoost (Deep Tuned)`
- **Performance Metrics**: Test MAE = `0.2643m` | RMSE = `0.5118m` | R² = `0.8688`
- **Zone Classification**: `88.50%` Accuracy
- **Key Methodology / Breakthrough**: Added cross-window velocity, acceleration, rolling averages, and RSSI IQR.

### Iteration 3: Phase 3 (Session GroupKFold & 60 BLE Domain Features)
- **Timestamp**: `2026-08-03 12:00:00`
- **Dataset Size**: `24,555` observation windows
- **Feature Set**: `60` extracted channels
- **Champion Model**: `CatBoost Regressor`
- **Performance Metrics**: Test MAE = `0.2315m` | RMSE = `0.4102m` | R² = `0.9102`
- **Zone Classification**: `94.20%` Accuracy
- **Key Methodology / Breakthrough**: 60 BLE domain features (packet_loss_rate, 6 RSSI histogram power density bins), IsolationForest signal space anomaly filtering.

### Iteration 4: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-03 17:38:45`
- **Dataset Size**: `23,818` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `ElasticNet`
- **Performance Metrics**: Test MAE = `0.9513m` | RMSE = `1.1377m` | R² = `-0.8772`
- **Zone Classification**: `46.31%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.
