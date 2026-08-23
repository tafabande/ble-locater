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
| `2026-08-03 21:30` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 23,818 | 54 | `MLP Neural Network` | **0.5635m** | **0.0256** | 46.3% | **+77.0%** |
| `2026-08-04 15:52` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 23,818 | 54 | `Stacking Super Learner` | **0.2638m** | **0.8665** | 92.8% | **+89.2%** |
| `2026-08-04 16:05` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 23,818 | 55 | `Stacking Super Learner` | **0.2603m** | **0.8684** | 92.8% | **+89.4%** |
| `2026-08-04 16:11` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 27,582 | 55 | `Bagging Ensemble` | **0.6031m** | **-0.5566** | 38.0% | **+75.4%** |
| `2026-08-04 16:58` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 27,581 | 54 | `KNN Regressor (k=7)` | **1.4089m** | **-0.3980** | -- | **+42.5%** |
| `2026-08-04 17:28` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 28,179 | 54 | `Bagging Ensemble` | **0.9799m** | **0.2485** | -- | **+60.0%** |
| `2026-08-04 22:37` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 28,422 | 54 | `KNN Regressor (k=7)` | **1.2829m** | **-0.1156** | 93.5% | **+47.6%** |
| `2026-08-05 14:36` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 30,440 | 54 | `ElasticNet` | **1.3120m** | **-0.0204** | 93.6% | **+46.4%** |
| `2026-08-05 19:34` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 32,728 | 54 | `Bayesian Ridge` | **1.5290m** | **0.0765** | 91.0% | **+37.6%** |
| `2026-08-05 21:01` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 32,728 | 59 | `Bagging Ensemble` | **0.8751m** | **0.5834** | 93.8% | **+64.3%** |
| `2026-08-17 00:50` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 32,728 | 59 | `Bagging Ensemble` | **0.8751m** | **0.5834** | 93.9% | **+64.3%** |
| `2026-08-19 16:22` | **Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)** | 32,728 | 59 | `Bagging Ensemble` | **0.8751m** | **0.5834** | 93.9% | **+64.3%** |

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

### Iteration 5: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-03 21:30:38`
- **Dataset Size**: `23,818` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `MLP Neural Network`
- **Performance Metrics**: Test MAE = `0.5635m` | RMSE = `0.8145m` | R² = `0.0256`
- **Zone Classification**: `46.31%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 6: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 15:52:14`
- **Dataset Size**: `23,818` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `Stacking Super Learner`
- **Performance Metrics**: Test MAE = `0.2638m` | RMSE = `0.5072m` | R² = `0.8665`
- **Zone Classification**: `92.85%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 7: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 16:05:21`
- **Dataset Size**: `23,818` observation windows
- **Feature Set**: `55` extracted channels
- **Champion Model**: `Stacking Super Learner`
- **Performance Metrics**: Test MAE = `0.2603m` | RMSE = `0.5032m` | R² = `0.8684`
- **Zone Classification**: `92.85%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 8: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 16:11:44`
- **Dataset Size**: `27,582` observation windows
- **Feature Set**: `55` extracted channels
- **Champion Model**: `Bagging Ensemble`
- **Performance Metrics**: Test MAE = `0.6031m` | RMSE = `0.8521m` | R² = `-0.5566`
- **Zone Classification**: `38.05%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 9: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 16:58:41`
- **Dataset Size**: `27,581` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `KNN Regressor (k=7)`
- **Performance Metrics**: Test MAE = `1.4089m` | RMSE = `1.7539m` | R² = `-0.3980`
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 10: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 17:28:23`
- **Dataset Size**: `28,179` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `Bagging Ensemble`
- **Performance Metrics**: Test MAE = `0.9799m` | RMSE = `1.1782m` | R² = `0.2485`
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 11: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-04 22:37:48`
- **Dataset Size**: `28,422` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `KNN Regressor (k=7)`
- **Performance Metrics**: Test MAE = `1.2829m` | RMSE = `1.6874m` | R² = `-0.1156`
- **Zone Classification**: `93.52%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 12: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-05 14:36:28`
- **Dataset Size**: `30,440` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `ElasticNet`
- **Performance Metrics**: Test MAE = `1.3120m` | RMSE = `1.5783m` | R² = `-0.0204`
- **Zone Classification**: `93.56%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 13: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-05 19:34:42`
- **Dataset Size**: `32,728` observation windows
- **Feature Set**: `54` extracted channels
- **Champion Model**: `Bayesian Ridge`
- **Performance Metrics**: Test MAE = `1.5290m` | RMSE = `1.8374m` | R² = `0.0765`
- **Zone Classification**: `91.01%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 14: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-05 21:01:23`
- **Dataset Size**: `32,728` observation windows
- **Feature Set**: `59` extracted channels
- **Champion Model**: `Bagging Ensemble`
- **Performance Metrics**: Test MAE = `0.8751m` | RMSE = `1.1756m` | R² = `0.5834`
- **Zone Classification**: `93.85%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 15: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-17 00:50:16`
- **Dataset Size**: `32,728` observation windows
- **Feature Set**: `59` extracted channels
- **Champion Model**: `Bagging Ensemble`
- **Performance Metrics**: Test MAE = `0.8751m` | RMSE = `1.1756m` | R² = `0.5834`
- **Zone Classification**: `93.93%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.

### Iteration 16: Phase 4 (Zero-Leakage Pipeline CV & Physics Baseline Benchmark)
- **Timestamp**: `2026-08-19 16:22:47`
- **Dataset Size**: `32,728` observation windows
- **Feature Set**: `59` extracted channels
- **Champion Model**: `Bagging Ensemble`
- **Performance Metrics**: Test MAE = `0.8751m` | RMSE = `1.1756m` | R² = `0.5834`
- **Zone Classification**: `93.93%` Accuracy
- **Key Methodology / Breakthrough**: In-Fold Pipeline feature selection & scaling, session GroupKFold CV, zero-leakage composite score selection.
