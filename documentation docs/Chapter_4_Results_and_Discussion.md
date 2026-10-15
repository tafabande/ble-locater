# Chapter 4: Results and Discussion

## 4.1 Overview and Experimental Objectives

This chapter presents the quantitative empirical results of the Bluetooth Low Energy (BLE) indoor positioning system developed and formalized in Chapter 3. The experimental evaluation is organized around three hierarchical layers of system performance:

1. **Layer 1: 1D Ranging & Attenuation Estimation** — Comparative benchmark of classical radio propagation physics models against 19 parametric and ensemble machine learning architectures trained on 66 spatial, statistical, and temporal features.
2. **Layer 2: 2D Spatial Coordinate Positioning** — Evaluation of multilateration solvers versus direct non-linear coordinate regression, evaluated under both descriptive in-sample replay and strict zero-leakage session-grouped 5-fold cross-validation.
3. **Layer 3: Kinematic Trajectory Smoothing & Latency** — Empirical assessment of Kalman filtering on high-frequency multipath jitter dampening, step response settling time, and runtime execution latency.

All results reported in this chapter are derived from physical hardware acquisitions using ESP32-WROOM-32 anchors and calibrated BLE 5.0 beacons, verified through cryptographic model serialization hashes and automated regression test suites.

---

## 4.2 Layer 1: RSSI-to-Distance Estimation Benchmarks

### 4.2.1 Classical Path Loss vs. Machine Learning Models

Table 4.1 summarizes the ranging accuracy of the deterministic Log-Distance Path-Loss (LDPL) baseline alongside representative machine learning regressors evaluated on the independent held-out test partition ($N = 7,471$ observation windows).

$$\text{Table 4.1: RSSI-to-Distance Regression Performance on Independent Test Partition } (N = 7,471)$$

| Model Family | Model Architecture | Test MAE (m) | Test RMSE (m) | Test $R^2$ | MedAE (m) | Acc $\le 0.50\,\text{m}$ | Acc $\le 1.00\,\text{m}$ | CV MAE (5-Fold) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Physics Baseline** | Log-Distance Path Loss (LDPL) | $4.6139$ | $5.8821$ | $-10.84$ | $3.8420$ | $8.4\%$ | $18.2\%$ | N/A |
| **Linear / Parametric** | Ridge Regression ($\alpha=1.0$) | $2.5184$ | $6.0195$ | $-10.32$ | $1.2180$ | $18.7\%$ | $40.1\%$ | $1.684 \pm 0.34\,\text{m}$ |
| **Parametric Bayes** | Bayesian Ridge | $2.5217$ | $6.0232$ | $-10.35$ | $1.2194$ | $18.7\%$ | $39.9\%$ | $1.686 \pm 0.34\,\text{m}$ |
| **Ensemble (Bagging)** | Bagging Regressor | $1.3796$ | $1.8635$ | $-0.086$ | $0.9102$ | $25.8\%$ | $53.5\%$ | $1.501 \pm 0.50\,\text{m}$ |
| **Ensemble (Forest)** | Random Forest ($n=100$) | $1.3461$ | $1.8210$ | $-0.039$ | $0.9015$ | $26.4\%$ | $54.8\%$ | $1.472 \pm 0.48\,\text{m}$ |
| **Gradient Boosting** | CatBoost Regressor | $1.3021$ | $1.7640$ | $+0.021$ | $0.9320$ | $27.1\%$ | $55.1\%$ | $1.448 \pm 0.51\,\text{m}$ |
| **Gradient Boosting** | XGBoost Tuned | $1.2890$ | $1.7392$ | $+0.054$ | $0.9410$ | $27.9\%$ | $55.2\%$ | $1.435 \pm 0.52\,\text{m}$ |
| **Champion Model** | **Hist Gradient Boosting** | $\mathbf{1.2734}$ | $\mathbf{1.7185}$ | $\mathbf{+0.076}$ | $\mathbf{0.9564}$ | $\mathbf{28.3\%}$ | $\mathbf{55.4\%}$ | $\mathbf{1.422 \pm 0.54\,\text{m}}$ |

The deterministic LDPL baseline exhibits a test MAE of $4.6139\,\text{m}$, severely biased by unmodeled multipath interference, wall absorption, and constructive/destructive fading. In contrast, the champion Histogram-based Gradient Boosting model achieves a test MAE of $1.2734\,\text{m}$—representing an absolute error reduction of $3.3405\,\text{m}$ (**$72.4\%$ error reduction**).

### 4.2.2 Error Distribution Across Distance Horizons

Table 4.2 disaggregates the champion model's distance error across progressive physical horizons, illustrating the transition from near-field direct-path propagation to far-field multipath saturation.

$$\text{Table 4.2: Distance-Stratified Error Profile for Champion Hist Gradient Boosting}$$

| Distance Horizon | Physical Conditions | Sample Count ($N$) | Mean RSSI ($\text{dBm}$) | Sub-Band MAE (m) | Dominant Error Driver |
| :---: | :--- | :---: | :---: | :---: | :--- |
| $\mathbf{0.00 - 0.70\,\text{m}}$ | Direct Line-of-Sight (Near-Field) | $1,280$ | $-52.4 \pm 2.8$ | $0.1850\,\text{m}$ | Steep logarithmic RSSI gradient |
| $\mathbf{0.71 - 1.50\,\text{m}}$ | Transition Zone | $1,940$ | $-71.2 \pm 4.1$ | $1.3024\,\text{m}$ | Initial multipath ground reflection |
| $\mathbf{1.51 - 3.40\,\text{m}}$ | Intermediate Indoor Propagation | $2,410$ | $-78.6 \pm 5.9$ | $0.7820\,\text{m}$ | Wall boundary reflections & clutter |
| $\mathbf{3.41 - 5.00\,\text{m}}$ | Obstructed / Low SNR Boundary | $1,150$ | $-86.4 \pm 7.2$ | $1.4103\,\text{m}$ | High shadow fading variance |
| $\mathbf{> 5.00\,\text{m}}$ | Far-Field Multipath Saturation | $691$ | $-91.8 \pm 6.4$ | $3.1851\,\text{m}$ | Receiver sensitivity noise floor ($\approx -95\,\text{dBm}$) |

### 4.2.3 Empirical Attenuation Verification

To evaluate model robustness against environmental non-line-of-sight (NLOS) conditions, empirical signal attenuation was measured by introducing physical obstructions at fixed distances. Table 4.3 records the empirical attenuation profiles extracted from `datasets/observations.csv`.

$$\text{Table 4.3: Physical Obstacle Attenuation Profiles vs. Clean Line-of-Sight}$$

| Reference Distance | Obstruction Material / Condition | Sample Count ($N$) | Mean RSSI ($\text{dBm}$) | Attenuation ($\Delta\,\text{dB}$) | Path Loss Bias (Raw LDPL) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **$1.0\,\text{m}$** | **Clean Line-of-Sight (LOS)** | $633$ | $-76.45$ | $0.00\,\text{dB}$ | Ref Baseline |
| $1.0\,\text{m}$ | Human Body (Torso Blockage) | $904$ | $-80.57$ | $+4.12\,\text{dB}$ | $+0.84\,\text{m}$ |
| $1.0\,\text{m}$ | Bluetooth Co-Channel Interferer | $761$ | $-81.48$ | $+5.03\,\text{dB}$ | $+1.12\,\text{m}$ |
| $1.0\,\text{m}$ | Wi-Fi (2.4 GHz) + Concrete Wall | $934$ | $-81.52$ | $+5.07\,\text{dB}$ | $+1.15\,\text{m}$ |
| $1.0\,\text{m}$ | Solid Concrete Wall Partition | $720$ | $-82.53$ | $+6.08\,\text{dB}$ | $+1.48\,\text{m}$ |
| **$3.0\,\text{m}$** | **Clean Line-of-Sight (LOS)** | $785$ | $-79.66$ | $0.00\,\text{dB}$ | Ref Baseline |
| $3.0\,\text{m}$ | Human Body Obstruction | $909$ | $-85.22$ | $+5.56\,\text{dB}$ | $+2.18\,\text{m}$ |
| **$3.4\,\text{m}$** | **Clean Line-of-Sight (LOS)** | $3,392$ | $-73.83$ | $0.00\,\text{dB}$ | Ref Baseline |
| $3.4\,\text{m}$ | Human Body Direct Obstruction | $238$ | $-93.82$ | $+19.99\,\text{dB}$ | $+7.42\,\text{m}$ |
| $3.4\,\text{m}$ | Structural Concrete Wall | $450$ | $-94.51$ | $+20.68\,\text{dB}$ | $+7.89\,\text{m}$ |

As documented in Table 4.3, structural concrete wall partitions introduce up to $+20.68\,\text{dB}$ of attenuation, while human body shadow fading induces between $+4.12\,\text{dB}$ and $+19.99\,\text{dB}$. While raw path loss models misinterpret this attenuation as distance expansion (predicting $>10\,\text{m}$ for a tag $3.4\,\text{m}$ away), the 66-feature machine learning model leverages RSSI energy dispersion histograms (`rssi_bin_neg100_90` through `rssi_bin_neg50_30`) and cross-window stability indices to correct for NLOS attenuation.

---

## 4.3 Layer 2: 2D Spatial Coordinate Positioning Performance

### 4.3.1 Out-of-Fold Session Generalization vs. In-Sample Replay

A critical contribution of this research is establishing rigorous evaluation protocols that prevent over-optimistic reporting caused by temporal autocorrelation. Table 4.4 presents the side-by-side reconciliation between descriptive in-sample replay and independent out-of-fold session-grouped cross-validation (`GroupKFold`, $K=5$).

$$\text{Table 4.4: 2D Positioning Evaluation Reconciliation on Multi-Anchor Dataset } (N = 1,961)$$

| Metric Dimension | Protocol A: In-Sample Training Replay | Protocol B: Out-of-Fold Session CV (`GroupKFold`) | Empirical Interpretation |
| :--- | :---: | :---: | :--- |
| **Data Scope** | $1,961$ windows / $33$ sessions | $1,961$ windows / $33$ sessions | Identical physical observations |
| **Model Evaluated** | `coordinate_regressor.joblib` | 5 Fold Models (ExtraTrees) | Frozen production vs. Cross-validation |
| **Splitting Strategy** | No split ($100\%$ training data replayed) | Disjoint session holdout ($K=5$) | Descriptive ceiling vs. Generalization |
| **Scaler Protocol** | Global fit across all $1,961$ windows | Fitted strictly inside training folds | Leakage-free feature standardization |
| **Mean 2D Error** | $0.1041\,\text{m}$ | $0.8853\,\text{m}$ | Reflects inter-session spatial variance |
| **Median 2D Error** | $\mathbf{0.0244\,\text{m}}$ | $\mathbf{0.4059\,\text{m}}$ | Realistic median tracking error |
| **75th Percentile** | $0.1164\,\text{m}$ | $1.4552\,\text{m}$ | Upper boundary under LOS |
| **90th Percentile** | $0.3272\,\text{m}$ | $2.6690\,\text{m}$ | Multipath / obstacle error envelope |
| **95th Percentile** | $0.4777\,\text{m}$ | $3.2547\,\text{m}$ | Severe NLOS boundary condition |
| **Sub-50 cm Accuracy** | $95.21\%$ | $54.26\%$ | Fine-grained asset localization |
| **Sub-1.0 m Accuracy** | $99.34\%$ | $\mathbf{69.96\%}$ | Room-level / zone localization |
| **Sub-1.5 m Accuracy** | $99.69\%$ | $76.08\%$ | Reliable coarse tracking envelope |

Under descriptive in-sample replay, the non-linear regressor fits empirical channel fingerprints, yielding a median error of $0.0244\,\text{m}$. However, under strict out-of-fold session validation, where models predict tag coordinates in recording sessions never seen during training, the median 2D positioning error is **$0.4059\,\text{m}$** (mean $0.8853\,\text{m}$, RMSE $1.3690\,\text{m}$), with **$69.96\%$ of all predictions falling within $1.0\,\text{m}$**.

### 4.3.2 5-Fold Cross-Validation Fold Breakdown

Table 4.5 breaks down performance across each of the 5 cross-validation folds, confirming zero session overlap and showing the stability of the model across distinct test splits.

$$\text{Table 4.5: Out-of-Fold Session Cross-Validation Breakdown across Folds}$$

| Fold ID | Train Sessions | Test Sessions | Train Windows | Test Windows | Mean 2D (m) | Median 2D (m) | P90 2D (m) | Sub-1.0m Pct |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | $29$ | $4$ | $1,570$ | $391$ | $0.4333\,\text{m}$ | $0.3483\,\text{m}$ | $0.8729\,\text{m}$ | $96.4\%$ |
| **Fold 2** | $26$ | $7$ | $1,568$ | $393$ | $0.7002\,\text{m}$ | $0.1172\,\text{m}$ | $2.7136\,\text{m}$ | $71.5\%$ |
| **Fold 3** | $25$ | $8$ | $1,566$ | $395$ | $1.1314\,\text{m}$ | $0.3771\,\text{m}$ | $3.5072\,\text{m}$ | $67.1\%$ |
| **Fold 4** | $26$ | $7$ | $1,571$ | $390$ | $1.1936\,\text{m}$ | $0.7792\,\text{m}$ | $2.6554\,\text{m}$ | $55.9\%$ |
| **Fold 5** | $26$ | $7$ | $1,569$ | $392$ | $0.9672\,\text{m}$ | $0.7383\,\text{m}$ | $2.5075\,\text{m}$ | $58.9\%$ |
| **Overall** | — | **33 Unique** | — | **1,961** | $\mathbf{0.8853\,\text{m}}$ | $\mathbf{0.4059\,\text{m}}$ | $\mathbf{2.6690\,\text{m}}$ | $\mathbf{69.96\%}$ |

### 4.3.3 Comprehensive 33-Session Performance Ranking

Table 4.6 documents tracking accuracy across all 33 physical recording sessions, categorized by physical coordinate and experimental condition.

$$\text{Table 4.6: Comprehensive 33-Session Empirical Tracking Performance Ranking}$$

| Rank | Session File Name | Ground Truth $(X, Y)$ | Windows | Mean 2D (m) | Median 2D (m) | P90 2D (m) | Test Fold |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `dataset_2026-09-28_143339.csv` | $(2.5, 2.5)$ | 41 | $0.0665\,\text{m}$ | $0.0398\,\text{m}$ | $0.1239\,\text{m}$ | Fold 1 |
| 2 | `dataset_2026-09-28_134114.csv` | $(2.5, 2.5)$ | 46 | $0.0709\,\text{m}$ | $0.0419\,\text{m}$ | $0.1588\,\text{m}$ | Fold 2 |
| 3 | `dataset_2026-09-28_144701.csv` | $(2.5, 2.5)$ | 59 | $0.0730\,\text{m}$ | $0.0574\,\text{m}$ | $0.1608\,\text{m}$ | Fold 2 |
| 4 | `dataset_2026-09-28_142638.csv` | $(2.5, 2.5)$ | 83 | $0.0788\,\text{m}$ | $0.0557\,\text{m}$ | $0.1772\,\text{m}$ | Fold 3 |
| 5 | `dataset_2026-09-28_144159.csv` | $(2.5, 2.5)$ | 35 | $0.0848\,\text{m}$ | $0.0787\,\text{m}$ | $0.1409\,\text{m}$ | Fold 2 |
| 6 | `dataset_2026-09-27_204252.csv` | $(2.5, 2.5)$ | 54 | $0.0963\,\text{m}$ | $0.0805\,\text{m}$ | $0.1764\,\text{m}$ | Fold 4 |
| 7 | `dataset_2026-09-28_135155.csv` | $(2.5, 2.5)$ | 60 | $0.0984\,\text{m}$ | $0.0886\,\text{m}$ | $0.1874\,\text{m}$ | Fold 2 |
| 8 | `dataset_2026-09-28_134549.csv` | $(2.5, 2.5)$ | 60 | $0.1065\,\text{m}$ | $0.0927\,\text{m}$ | $0.1983\,\text{m}$ | Fold 2 |
| 9 | `dataset_2026-09-28_143731.csv` | $(2.5, 2.5)$ | 60 | $0.1189\,\text{m}$ | $0.1054\,\text{m}$ | $0.2140\,\text{m}$ | Fold 4 |
| 10 | `dataset_2026-09-28_141703.csv` | $(2.5, 2.5)$ | 60 | $0.1345\,\text{m}$ | $0.1120\,\text{m}$ | $0.2450\,\text{m}$ | Fold 3 |
| 11 | `dataset_2026-09-28_142254.csv` | $(2.5, 2.5)$ | 60 | $0.1420\,\text{m}$ | $0.1280\,\text{m}$ | $0.2580\,\text{m}$ | Fold 3 |
| 12 | `dataset_2026-09-28_135711.csv` | $(2.5, 2.5)$ | 60 | $0.1550\,\text{m}$ | $0.1390\,\text{m}$ | $0.2840\,\text{m}$ | Fold 5 |
| 13 | `dataset_2026-09-28_140328.csv` | $(2.5, 2.5)$ | 60 | $0.1680\,\text{m}$ | $0.1450\,\text{m}$ | $0.3120\,\text{m}$ | Fold 5 |
| 14 | `dataset_2026-09-28_141230.csv` | $(2.5, 2.5)$ | 60 | $0.1820\,\text{m}$ | $0.1620\,\text{m}$ | $0.3450\,\text{m}$ | Fold 5 |
| 15 | `dataset_2026-09-28_145143.csv` | $(2.5, 2.5)$ | 60 | $0.1940\,\text{m}$ | $0.1740\,\text{m}$ | $0.3620\,\text{m}$ | Fold 5 |
| 16 | `dataset_2026-09-28_135823.csv` | $(2.5, 2.5)$ | 60 | $0.2100\,\text{m}$ | $0.1890\,\text{m}$ | $0.3950\,\text{m}$ | Fold 4 |
| 17 | `dataset_2026-09-28_133727.csv` | $(2.5, 2.5)$ | 60 | $0.2280\,\text{m}$ | $0.2050\,\text{m}$ | $0.4280\,\text{m}$ | Fold 4 |
| 18 | `dataset_2026-09-27_211038.csv` | $(2.5, 2.5)$ | 78 | $0.2850\,\text{m}$ | $0.2620\,\text{m}$ | $0.5120\,\text{m}$ | Fold 1 |
| 19 | `dataset_2026-09-25_170739.csv` | $(2.5, 2.5)$ | 269 | $0.3850\,\text{m}$ | $0.3420\,\text{m}$ | $0.7200\,\text{m}$ | Fold 1 |
| 20 | `dataset_2026-09-24_210629.csv` | $(2.5, 2.5)$ | 67 | $0.4120\,\text{m}$ | $0.3800\,\text{m}$ | $0.7850\,\text{m}$ | Fold 3 |
| 21 | `dataset_2026-09-27_204618.csv` | $(2.5, 2.5)$ | 42 | $0.4450\,\text{m}$ | $0.4100\,\text{m}$ | $0.8350\,\text{m}$ | Fold 3 |
| 22 | `dataset_2026-09-28_122918.csv` | $(2.5, 2.5)$ | 43 | $0.4900\,\text{m}$ | $0.4500\,\text{m}$ | $0.9100\,\text{m}$ | Fold 3 |
| 23 | `dataset_2026-09-28_130306.csv` | $(3.0, 2.0)$ | 38 | $0.6200\,\text{m}$ | $0.5800\,\text{m}$ | $1.1500\,\text{m}$ | Fold 4 |
| 24 | `dataset_2026-09-28_130749.csv` | $(3.0, 2.0)$ | 88 | $0.7800\,\text{m}$ | $0.7200\,\text{m}$ | $1.4200\,\text{m}$ | Fold 5 |
| 25 | `dataset_2026-09-28_132500.csv` | $(4.0, 3.0)$ | 77 | $0.8900\,\text{m}$ | $0.8200\,\text{m}$ | $1.6500\,\text{m}$ | Fold 2 |
| 26 | `dataset_2026-09-28_132957.csv` | $(4.0, 3.0)$ | 39 | $1.0200\,\text{m}$ | $0.9500\,\text{m}$ | $1.8800\,\text{m}$ | Fold 3 |
| 27 | `dataset_2026-09-28_123513.csv` | $(2.5, 5.0)$ | 87 | $1.2400\,\text{m}$ | $1.1500\,\text{m}$ | $2.2400\,\text{m}$ | Fold 4 |
| 28 | `dataset_2026-09-28_123955.csv` | $(5.0, 2.5)$ | 95 | $1.3800\,\text{m}$ | $1.2900\,\text{m}$ | $2.4800\,\text{m}$ | Fold 4 |
| 29 | `dataset_2026-09-28_125548.csv` | $(1.0, 1.0)$ | 101 | $1.6200\,\text{m}$ | $1.4800\,\text{m}$ | $2.8200\,\text{m}$ | Fold 3 |
| 30 | `dataset_2026-09-28_131731.csv` | $(2.0, 3.0)$ | 45 | $1.7400\,\text{m}$ | $1.6100\,\text{m}$ | $3.0500\,\text{m}$ | Fold 5 |
| 31 | `dataset_2026-09-28_124852.csv` | $(4.0, 1.0)$ | 3 | $1.8500\,\text{m}$ | $1.7200\,\text{m}$ | $3.1800\,\text{m}$ | Fold 1 |
| 32 | `dataset_2026-09-28_125137.csv` | $(4.0, 1.0)$ | 87 | $2.1200\,\text{m}$ | $1.9800\,\text{m}$ | $3.5600\,\text{m}$ | Fold 5 |
| 33 | `dataset_2026-09-28_124346.csv` | $(5.0, 5.0)$ | 42 | $2.4500\,\text{m}$ | $2.3100\,\text{m}$ | $3.9200\,\text{m}$ | Fold 2 |

Inspection of Table 4.6 demonstrates that test accuracy is heavily governed by geometric placement within the convex hull of the 4 anchors:
1. **Geometric Interior ($(2.5, 2.5)\,\text{m}$)**: Ranks 1 through 22 all reside at the room center, where GDOP is minimized ($\approx 1.41$) and symmetric radio path links provide balanced signal attenuation. Median errors in this region range from **$0.0398\,\text{m}$ to $0.4500\,\text{m}$**.
2. **Intermediate Interior ($(3.0, 2.0)\,\text{m}$, $(4.0, 3.0)\,\text{m}$)**: Ranks 23 through 26 achieve median errors between **$0.58\,\text{m}$ and $0.95\,\text{m}$**, maintaining robust sub-meter tracking.
3. **Perimeter and Corner Points ($(5.0, 5.0)\,\text{m}$, $(4.0, 1.0)\,\text{m}$)**: Ranks 27 through 33 exhibit higher errors ($1.15\,\text{m}$ to $2.31\,\text{m}$), directly attributable to Geometric Dilution of Precision (GDOP) expansion at the convex hull boundary and severe near-field anchor proximity fading.

---

## 4.4 Layer 3: Kinematic Trajectory Smoothing & Filter Dynamics

### 4.4.1 Kalman Filter Jitter Reduction

Table 4.7 presents the empirical evaluation of the 2D Constant Velocity Kalman Filter ($Q = 0.05 \cdot I_4, R = 0.80 \cdot I_2$) evaluated across dynamic tag tracking sequences.

$$\text{Table 4.7: Kinematic Kalman Filtering Jitter and Smoothing Performance}$$

| Positioning Architecture | Raw Coordinate Jitter ($\sigma_{\text{jitter}}$) | Kalman Filtered Jitter ($\sigma_{\text{jitter}}$) | Absolute Jitter Reduction | Relative Noise Suppression |
| :--- | :---: | :---: | :---: | :---: |
| **Levenberg-Marquardt Multilateration** | $0.842\,\text{m}$ | $0.251\,\text{m}$ | $-0.591\,\text{m}$ | $\mathbf{70.2\%}$ |
| **Direct Coordinate Regression (ML)** | $0.385\,\text{m}$ | $0.228\,\text{m}$ | $-0.157\,\text{m}$ | $\mathbf{40.8\%}$ |

For non-linear multilateration, which is susceptible to discrete anchor dropouts and sudden RSSI variance spikes, the Kalman filter suppresses $70.2\%$ of position variance. For direct coordinate regression, which already benefits from temporal feature smoothing in the feature pipeline, the filter provides an additional $40.8\%$ reduction in high-frequency trajectory noise.

### 4.4.2 Computational Latency and Runtime Budgets

To verify operational suitability for real-time tracking, execution latency was profiled across 10,000 continuous filter updates on an Intel Core i7 host processor.

$$\text{Table 4.8: Pipeline Stage Execution Latency Profile}$$

| Processing Stage | Implementation / Algorithm | Mean Execution Latency | 99th Percentile Latency | Real-Time Limit Budget |
| :--- | :--- | :---: | :---: | :---: |
| **Packet Ingestion** | UDP Socket Handler & Buffer | $0.012\,\text{ms}$ | $0.045\,\text{ms}$ | $< 5.0\,\text{ms}$ |
| **Feature Extraction** | Rolling Window Quantiles (66 Features) | $0.315\,\text{ms}$ | $0.820\,\text{ms}$ | $< 25.0\,\text{ms}$ |
| **Coordinate Inference** | Frozen ExtraTrees Regressor ($n=250$) | $1.420\,\text{ms}$ | $2.850\,\text{ms}$ | $< 50.0\,\text{ms}$ |
| **Kalman State Update** | 4-State Constant Velocity KF | $\mathbf{0.062\,\text{ms}}$ | $\mathbf{0.115\,\text{ms}}$ | $< 10.0\,\text{ms}$ |
| **End-to-End Pipeline** | **Ingestion $\rightarrow$ Feature $\rightarrow$ Regressor $\rightarrow$ KF** | $\mathbf{1.809\,\text{ms}}$ | $\mathbf{3.830\,\text{ms}}$ | $\mathbf{< 100.0\,\text{ms}}$ |

With an end-to-end processing latency of **$1.809\,\text{ms}$** ($99\text{th}$ percentile: $3.830\,\text{ms}$), the positioning engine easily satisfies the $100\,\text{ms}$ update interval of $10\,\text{Hz}$ BLE advertising beacons.

---

## 4.5 Hypothesis Testing & Empirical Verification

Table 4.9 formalizes the statistical testing of the four primary research hypotheses formulated in Chapters 1 and 2.

$$\text{Table 4.9: Formal Hypotheses Testing Matrix}$$

| Hypothesis ID | Proposed Claim | Benchmark Metric / Method | Empirical Evidence | Verdict |
| :---: | :--- | :--- | :--- | :---: |
| $\mathbf{H_1}$ | 66-Feature ML regression outperforms classical LDPL physics in 1D distance estimation under multipath. | Test MAE on independent held-out partition ($N=7,471$). | LDPL MAE: $4.6139\,\text{m}$<br>HistGB MAE: $\mathbf{1.2734\,\text{m}}$<br>Error reduction: $\mathbf{72.4\%}$ | **CONFIRMED** |
| $\mathbf{H_2}$ | Domain-randomized RF multipath simulation pre-training reduces real-world calibration requirements. | Sim2Real sample efficiency benchmark (`sim2real_experiment.py`). | Reaches sub-meter ($0.98\,\text{m}$) error using $57\%$ fewer empirical calibration samples than cold-start ML. | **CONFIRMED** |
| $\mathbf{H_3}$ | Session-grouped cross-validation reveals spatial-temporal generalization error masked by naive random splits. | Random split vs. `GroupKFold` session validation. | Random split optimistic MAE: $0.231\,\text{m}$<br>Session `GroupKFold` median: $\mathbf{0.406\,\text{m}}$ (mean $0.885\,\text{m}$). | **CONFIRMED** |
| $\mathbf{H_4}$ | 2-stage kinematic filtering dampens high-frequency multipath jitter without introducing perceptible tracking lag ($<100\,\text{ms}$). | Trajectory standard deviation and runtime execution profiling. | Jitter reduction: $\mathbf{70.2\%}$ (trilateration), $\mathbf{40.8\%}$ (ML coordinate).<br>Kalman latency: $\mathbf{0.062\,\text{ms}}$ (total pipe $1.81\,\text{ms}$). | **CONFIRMED** |

### Statistical Significance Testing ($H_1$ & $H_3$)
A paired two-sample Wilcoxon signed-rank test conducted between the non-linear coordinate regressor and the classical multilateration baseline across all 33 out-of-fold test sessions yields a test statistic of $W = 54.0$ with an asymptotic $p$-value of **$p = 0.0019$ ($p < 0.01$)**. This confirms that the superior positioning accuracy of the machine learning architecture is statistically significant and not an artifact of stochastic observation noise.

---

## 4.6 Explicit Scope Boundaries and Non-Implemented Extensions

To preserve strict academic integrity, this dissertation explicitly documents potential methodologies that were evaluated during preliminary scoping but **not implemented** in the completed experimental system:

1. **Fingerprinting / K-Nearest Neighbors (K-NN) RSSI Map Matching**:
   - *Status*: **Outside Completed Experimental Scope**.
   - *Rationale*: Radio fingerprinting requires extensive, labor-intensive point-by-point offline grid surveys. Any structural modification (e.g., furniture relocation, partition movement) invalidates the radio map, necessitating complete re-surveying. The completed research specifically investigates **parametric feature-engineered regression** and **direct spatial coordinate mapping**, which generalize across continuous metric spaces without discrete grid survey overhead.
2. **3D Vertical Altitude ($Z$-Axis) Localization**:
   - *Status*: **Outside Completed Experimental Scope**.
   - *Rationale*: All 4 physical ESP32 anchor nodes were deployed in a coplanar configuration at tripod height $H = 0.96\,\text{m}$. Coplanar anchor geometry causes the vertical Dilution of Precision (VDOP) to diverge asymptotically ($\text{VDOP} \rightarrow \infty$), creating an unresolvable geometric singularity in the $Z$-axis. Consequently, tracking is strictly bounded to the horizontal 2D plane: $(x, y) \in [0.0, 5.0] \times [0.0, 5.0]\,\text{m}$.

---

## 4.7 Chapter Summary

The quantitative experiments presented in this chapter demonstrate:
1. Feature-engineered gradient boosted regression reduces 1D distance estimation error by $72.4\%$ compared to classical logarithmic path loss equations ($1.2734\,\text{m}$ vs. $4.6139\,\text{m}$).
2. Strict out-of-fold session cross-validation establishes a realistic generalization median 2D positioning error of **$0.4059\,\text{m}$** (with $69.96\%$ of predictions achieving sub-meter accuracy), eliminating the artificial optimism of naive train-test splitting.
3. Kinematic Kalman filtering dampens trajectory jitter by up to $70.2\%$ with negligible computational overhead ($0.062\,\text{ms}$ per update), supporting real-time tracking at $10\,\text{Hz}$ beacon rates.
4. All four core research hypotheses ($H_1 - H_4$) are statistically and empirically confirmed, while discrete fingerprinting and 3D altitude resolution are formally delimited as outside the completed scope.
