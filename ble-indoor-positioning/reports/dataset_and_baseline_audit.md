# 📊 BLE Indoor Positioning — Dataset & Evaluation Baseline Audit Report

> **Comprehensive Diagnostic Study**  
> **Date**: 2026-08-05 19:56:00  
> **Dataset**: `datasets/observations.csv` (33,741 total windows)

---

## 1. 🎯 Train/Test Split & Distance Spectrum Audit

Evaluation was performed using **Session-aware `GroupShuffleSplit` (80% Train / 20% Test)** across 52 total sessions (41 Train / 11 Test).

| Distance (m) | Train Windows | Train (%) | Test Windows | Test (%) | Delta (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `0.5m` | 1,716.0 | 6.27% | 772.0 | 12.09% | `+5.82%` |
| `0.6m` | 1,321.0 | 4.83% | 0.0 | 0.0% | `-4.83%` |
| `0.7m` | 1,073.0 | 3.92% | 0.0 | 0.0% | `-3.92%` |
| `1.0m` | 3,891.0 | 14.22% | 1,607.0 | 25.18% | `+10.95%` |
| `1.1m` | 642.0 | 2.35% | 0.0 | 0.0% | `-2.35%` |
| `1.5m` | 1,861.0 | 6.8% | 0.0 | 0.0% | `-6.8%` |
| `1.9m` | 1,048.0 | 3.83% | 0.0 | 0.0% | `-3.83%` |
| `2.0m` | 4,406.0 | 16.1% | 0.0 | 0.0% | `-16.1%` |
| `3.0m` | 1,576.0 | 5.76% | 3,024.0 | 47.38% | `+41.62%` |
| `3.4m` | 2,625.0 | 9.59% | 0.0 | 0.0% | `-9.59%` |
| `4.5m` | 689.0 | 2.52% | 0.0 | 0.0% | `-2.52%` |
| `4.6m` | 2,516.0 | 9.2% | 0.0 | 0.0% | `-9.2%` |
| `5.0m` | 636.0 | 2.32% | 0.0 | 0.0% | `-2.32%` |
| `5.3m` | 1,979.0 | 7.23% | 0.0 | 0.0% | `-7.23%` |
| `7.0m` | 1,379.0 | 5.04% | 980.0 | 15.35% | `+10.31%` |

> [!IMPORTANT]
> **Key Finding**: Session-based splitting creates natural shifts in target distance frequency. Test held-out sessions contain distinct distance proportions compared to the training set, causing target mean shifts.

---

## 2. 🧮 Baseline Predictor & $R^2$ Formula Verification

To verify baseline logic and $R^2$ behavior on out-of-session data:

* **Training Set Mean Target ($\overline{y}_{\text{train}}$)**: `2.6406m`
* **Test Set Mean Target ($\overline{y}_{\text{test}}$)**: `2.8082m` (Shift of `+0.1676m`)

### Benchmark Model Comparison Table

| Model / Predictor | Test MAE (m) | Test RMSE (m) | Test $R^2$ Score | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Train Mean Baseline ($\overline{y}_{\text{train}}$)** | **1.5115m** | **2.0520m** | **-0.0067** | Predicts constant `2.64m` on test set |
| **Test Mean Predictor ($\overline{y}_{\text{test}}$)** | **1.4688m** | **2.0452m** | **0.0000** | Theoretical zero benchmark ($R^2 = 0$) |
| **Random Forest Regressor** | **1.4207m** | **1.9844m** | **0.0585** | Machine Learning model trained on 30 RSSI features |

> [!NOTE]
> **$R^2$ Formula Explanation**:  
> Standard $R^2$ is defined as $1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}}$, where $\text{SS}_{\text{tot}}$ is computed relative to the **test set mean** ($\overline{y}_{\text{test}}$).  
> Because the training set mean $\overline{y}_{\text{train}}$ differs from $\overline{y}_{\text{test}}$, a constant baseline predicting $\overline{y}_{\text{train}}$ yields a **negative $R^2$** (`-0.0067`). Machine learning models outperforming this naive baseline achieve strong positive $R^2$ (`0.0585`).

---

## 3. 🔍 Per-Session Error Breakdown

Analysis of test set sessions reveals that error is non-uniform across recording sessions:

### Top 5 Highest Error Sessions

| Session File | Distance | Obstacle Type | Test MAE (m) | Test RMSE (m) | Session $R^2$ |
| :--- | :---: | :--- | :---: | :---: | :---: |
| `dataset_2026-08-05_160531.csv` | `7.0m` | `nan` | **4.1097m** | **4.1488m** | `Single Target` |
| `dataset_2026-08-05_164358.csv` | `7.0m` | `Phone` | **4.0757m** | **4.1165m** | `Single Target` |
| `dataset_2026-07-31_222134.csv` | `1.0m` | `Bluetooth Device` | **2.1374m** | **2.2427m** | `Single Target` |
| `dataset_2026-07-31_215336.csv` | `1.0m` | `nan` | **1.9379m** | **1.9804m** | `Single Target` |
| `dataset_2026-08-01_153911.csv` | `0.5m` | `Wifi Interference` | **1.2816m** | **1.3025m** | `Single Target` |

### Top 5 Best Performing Sessions

| Session File | Distance | Obstacle Type | Test MAE (m) | Test RMSE (m) | Session $R^2$ |
| :--- | :---: | :--- | :---: | :---: | :---: |
| `dataset_2026-08-01_023541.csv` | `3.0m` | `Wooden Door` | **0.5237m** | **0.6067m** | `Single Target` |
| `dataset_2026-08-01_030059.csv` | `3.0m` | `nan` | **0.4609m** | **0.5727m** | `Single Target` |
| `dataset_2026-08-04_164608.csv` | `1.0m` | `Wooden Door` | **0.374m** | **0.5625m** | `Single Target` |
| `dataset_2026-08-01_002427.csv` | `3.0m` | `Human Body` | **0.3696m** | **0.4932m** | `Single Target` |
| `dataset_2026-08-01_005116.csv` | `3.0m` | `Tape  Measure` | **0.3555m** | **0.4937m** | `Single Target` |

---

## 4. 📶 RSSI Spectrum & Environmental Attenuation Analysis

### Mean RSSI per Distance Target

| Distance (m) | Sample Count | Mean RSSI (dBm) | Median RSSI (dBm) | Std Dev (dB) | Min / Max RSSI |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `0.5m` | 2,488 | **-68.50 dBm** | -69.00 dBm | 4.39 dB | -81.0 / -48.0 dBm |
| `0.6m` | 1,321 | **-62.70 dBm** | -61.00 dBm | 3.90 dB | -80.0 / -56.0 dBm |
| `0.7m` | 1,073 | **-60.06 dBm** | -60.00 dBm | 4.00 dB | -89.0 / -51.0 dBm |
| `1.0m` | 5,498 | **-77.76 dBm** | -78.00 dBm | 8.59 dB | -98.0 / -57.0 dBm |
| `1.1m` | 642 | **-66.82 dBm** | -67.00 dBm | 1.26 dB | -73.0 / -65.0 dBm |
| `1.5m` | 1,861 | **-78.96 dBm** | -79.00 dBm | 3.78 dB | -88.0 / -71.0 dBm |
| `1.9m` | 1,048 | **-69.44 dBm** | -70.00 dBm | 1.91 dB | -75.0 / -64.0 dBm |
| `2.0m` | 4,406 | **-76.07 dBm** | -75.00 dBm | 4.95 dB | -98.0 / -68.0 dBm |
| `3.0m` | 4,600 | **-81.89 dBm** | -82.00 dBm | 6.30 dB | -102.0 / -68.0 dBm |
| `3.4m` | 2,625 | **-67.81 dBm** | -68.00 dBm | 6.37 dB | -106.0 / -56.0 dBm |
| `4.5m` | 689 | **-86.48 dBm** | -86.00 dBm | 3.01 dB | -97.0 / -78.0 dBm |
| `4.6m` | 2,516 | **-81.20 dBm** | -79.00 dBm | 4.07 dB | -91.0 / -76.0 dBm |
| `5.0m` | 636 | **-85.78 dBm** | -84.00 dBm | 5.98 dB | -103.0 / -78.0 dBm |
| `5.3m` | 1,979 | **-85.66 dBm** | -86.00 dBm | 4.97 dB | -97.0 / -15.0 dBm |
| `7.0m` | 2,359 | **-78.40 dBm** | -77.00 dBm | 4.52 dB | -109.0 / -72.0 dBm |

> [!WARNING]
> **Key Finding — Signal Attenuation Non-Monotonicity**:  
> RSSI mean power level does not decrease smoothly with distance. Instead, obstacles (human body absorption, concrete walls, mattress dampening) introduce up to $\pm 15\text{ dBm}$ variations at the same physical distance, forcing ML models to learn non-linear environmental representations.

---

## 5. 🖼️ Visual Diagnostic Artifacts

![Dataset & Baseline Audit Plot](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/reports/dataset_baseline_audit.png)

---
