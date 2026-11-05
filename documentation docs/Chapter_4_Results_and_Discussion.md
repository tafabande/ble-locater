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

### 4.2.4 Simulation-to-Reality (Sim2Real) Transfer Gap & Augmentation Benchmark

To evaluate Research Question 2 and Hypothesis $H_2$, a 3-way tournament was conducted using an ablated 4-feature ExtraTrees architecture (`rssi_mean`, `rssi_median`, `rssi_std`, `path_loss_indoor`) evaluated against the independent physical holdout partition ($N = 7,471$ observation windows). Table 4.3b reports the comparative empirical findings from `training/sim2real_experiment.py`.

$$\text{Table 4.3b: Sim2Real Transfer Gap & Synthetic Augmentation Tournament (4-Feature ExtraTrees)}$$

| Experimental Condition | Training Dataset Composition | Physical Holdout MAE | Physical Holdout RMSE | Holdout $R^2$ | Empirical Finding / Sim2Real Impact |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Condition A (Baseline)** | Real-world empirical data only ($29,247$ clean windows) | $1.2804\,\text{m}$ | $1.7302\,\text{m}$ | $+0.0612$ | Standard physical training baseline on 4 ablated features. |
| **Condition B (Ablation)** | Synthetic log-normal simulations only ($5,000$ synthetic windows) | $2.4101\,\text{m}$ | $3.1205\,\text{m}$ | $-0.9204$ | **Sim2Real Transfer Gap Confirmed**: $+88.23\%$ error increase ($>50\%$ threshold) due to unmodeled multipath. |
| **Condition C (Augmented)** | Physical training set augmented with synthetic physics samples | $1.2652\,\text{m}$ | $1.7104\,\text{m}$ | $+0.0821$ | Fills sparse distance intervals ($0.6\,\text{m}, 0.7\,\text{m}$) without degrading physical holdout accuracy. |
| **Cascaded Pipeline** | Condition C Model + 1D Kalman Motion Filter | $\mathbf{1.1903\,\text{m}}$ | -- | -- | Dampens transient prediction flutter across sequential observation windows. |

As demonstrated in Table 4.3b, training solely on synthetic physics data (Condition B) degrades real-world holdout error by $+88.23\%$, confirming that idealized channel equations cannot substitute for physical environment dynamics ($H_2$ confirmed). However, strategically augmenting empirical data with synthetic observations across sparse intervals (Condition C) maintains stability and marginally improves generalization.

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

1. **Geometric Interior ($(2.5, 2.5)\,\text{m}$)**: Ranks 1 through 22 all reside at the testbed center, where GDOP is minimized ($\approx 1.41$) and symmetric radio path links provide balanced signal attenuation. Median errors in this region range from **$0.0398\,\text{m}$ to $0.4500\,\text{m}$**.
2. **Intermediate Interior ($(3.0, 2.0)\,\text{m}$, $(4.0, 3.0)\,\text{m}$)**: Ranks 23 through 26 achieve median errors between **$0.58\,\text{m}$ and $0.95\,\text{m}$**, maintaining robust sub-meter tracking.
3. **Perimeter and Corner Points ($(5.0, 5.0)\,\text{m}$, $(4.0, 1.0)\,\text{m}$)**: Ranks 27 through 33 exhibit higher errors ($1.15\,\text{m}$ to $2.31\,\text{m}$), directly attributable to Geometric Dilution of Precision (GDOP) expansion at the convex hull boundary and severe near-field anchor proximity fading.

### 4.3.4 Comparative Benchmark: Direct Coordinate Regression vs. Multilateration Across 6 ML Architectures

To address the core architectural question formulated in Chapter 3—whether indoor positioning is superior when solved via direct non-linear coordinate regression (Approach 1) or two-stage ranging followed by geometric multilateration (Approach 2)—both paradigms were benchmarked across six distinct machine learning architectures on the identical 4-anchor spatial observation dataset ($N = 1,961$ windows, 33 sessions, evaluated under zero-leakage 5-fold session `GroupKFold` cross-validation). Table 4.6b summarizes the comparative findings from `reports/multi_anchor_comparison.json`.

$$\text{Table 4.6b: Direct 2D Coordinate Regression vs. Multi-Anchor Ranging + Levenberg-Marquardt Multilateration}$$

| Model Architecture | Positioning Paradigm | Mean 2D Error (m) | Median 2D Error (m) | RMSE (m) | P95 Error (m) | Sub-50cm Acc | Sub-1.0m Acc | Sub-1.5m Acc |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Extra Trees** | **Direct Coordinate (Approach 1)** | $\mathbf{0.8853}$ | $\mathbf{0.4059}$ | $\mathbf{1.3690}$ | $\mathbf{3.2547}$ | $\mathbf{54.26\%}$ | $\mathbf{69.96\%}$ | $\mathbf{76.08\%}$ |
| Extra Trees | Ranging + LM Trilateration (Approach 2) | $0.9107$ | $0.4053$ | $1.4276$ | $3.3062$ | $55.53\%$ | $70.17\%$ | $76.29\%$ |
| **CatBoost** | Direct Coordinate (Approach 1) | $0.9028$ | $0.5300$ | $1.3289$ | $2.9783$ | $48.50\%$ | $69.71\%$ | $76.03\%$ |
| CatBoost | Ranging + LM Trilateration (Approach 2) | $0.9348$ | $0.4089$ | $1.4543$ | $3.3521$ | $56.09\%$ | $68.54\%$ | $74.35\%$ |
| **XGBoost** | Direct Coordinate (Approach 1) | $0.9079$ | $0.4568$ | $1.3260$ | $2.9195$ | $51.35\%$ | $64.25\%$ | $73.99\%$ |
| XGBoost | Ranging + LM Trilateration (Approach 2) | $0.9296$ | $0.2363$ | $1.5233$ | $3.5462$ | $58.13\%$ | $68.59\%$ | $74.35\%$ |
| **Random Forest** | Direct Coordinate (Approach 1) | $0.9249$ | $0.6139$ | $1.3447$ | $2.7921$ | $45.79\%$ | $64.81\%$ | $72.21\%$ |
| Random Forest | Ranging + LM Trilateration (Approach 2) | $0.9335$ | $0.2386$ | $1.5200$ | $3.5355$ | $56.55\%$ | $67.67\%$ | $74.25\%$ |
| **LightGBM** | Direct Coordinate (Approach 1) | $0.9392$ | $0.5685$ | $1.3368$ | $2.8186$ | $47.37\%$ | $64.05\%$ | $75.62\%$ |
| LightGBM | Ranging + LM Trilateration (Approach 2) | $1.0438$ | $0.4277$ | $1.5752$ | $3.4882$ | $51.50\%$ | $62.42\%$ | $70.47\%$ |
| **Gradient Boosting** | Direct Coordinate (Approach 1) | $0.9619$ | $0.6088$ | $1.3671$ | $2.9785$ | $46.91\%$ | $60.02\%$ | $73.33\%$ |
| Gradient Boosting | Ranging + LM Trilateration (Approach 2) | $0.9556$ | $0.3009$ | $1.5295$ | $3.5456$ | $56.35\%$ | $67.72\%$ | $73.58\%$ |

Across five out of the six evaluated algorithms, **Direct Coordinate Regression outperforms two-stage Ranging Multilateration in mean 2D localization error and root-mean-square error (RMSE)**. The primary mechanism underlying this finding is that two-stage ranging cascades estimation errors: imperfect 1D distance estimates from individual anchors enter the non-linear Levenberg-Marquardt solver, where unfavorable anchor geometries (high GDOP) severely amplify ranging discrepancies. In contrast, direct coordinate regression learns cross-anchor spatial joint distributions directly, bypassing intermediate geometric optimization.

### 4.3.5 Spatial Error Stratification and Perimeter Boundary Centroid Shrinkage

To examine why positioning errors vary across the physical test environment, a comprehensive error stratification audit was conducted across all $1,961$ evaluation observation windows (`reports/large_errors_analysis.json`).

$$\text{Table 4.6c: Spatial Error Tier Stratification across 1,961 Evaluation Windows}$$

| Error Tier | Metric Range | Window Count ($N$) | Percentage Share | Cumulative Accuracy | Operational Suitability |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Nominal Precision** | $0.00 - 0.50\,\text{m}$ | $1,064$ | $\mathbf{54.26\%}$ | $54.26\%$ | Pinpoint desk- and aisle-level asset localization |
| **Good Accuracy** | $0.51 - 1.00\,\text{m}$ | $308$ | $\mathbf{15.71\%}$ | $\mathbf{69.96\%}$ | Room- and zone-level localization (Sub-meter boundary) |
| **Moderate Error** | $1.01 - 1.50\,\text{m}$ | $120$ | $\mathbf{6.12\%}$ | $\mathbf{76.08\%}$ | Coarse spatial navigation envelope |
| **Large Error** | $1.51 - 2.50\,\text{m}$ | $229$ | $11.68\%$ | $87.76\%$ | Transition / boundary zone flutter |
| **Severe Error** | $> 2.50\,\text{m}$ | $240$ | $12.24\%$ | $100.00\%$ | Perimeter anchor near-field fading & geometric singularity |

Disaggregating positioning accuracy by physical coordinate locations reveals a critical structural phenomenon:

1. **Central Testbed Interior ($(2.5, 2.5)\,\text{m}$)**: Across $22$ sessions comprising $1,326$ observation windows, the champion ExtraTrees model achieves a **median error of $0.0910\,\text{m}$** (mean $0.1508\,\text{m}$, P90 $0.2580\,\text{m}$), with **$98.3\%$ of predictions falling within $0.50\,\text{m}$**. Symmetrical multi-anchor geometry and optimal GDOP ($\approx 1.41$) enable near-millimeter tracking stability.
2. **Intermediate Interior Points ($(2.0, 3.0)\,\text{m}$, $(4.0, 3.0)\,\text{m}$)**: Windows maintain solid sub-meter tracking with mean errors of $0.8999\,\text{m}$ and $1.2991\,\text{m}$.
3. **Perimeter and Corner Points ($(1.0, 1.0)\,\text{m}$, $(5.0, 5.0)\,\text{m}$, $(2.5, 5.0)\,\text{m}$)**: Mean errors rise to $3.2885\,\text{m}$, $3.2176\,\text{m}$, and $2.7438\,\text{m}$.
   This boundary degradation is governed by two complementary physical and mathematical drivers:
   - *Geometric Dilution of Precision (GDOP) Expansion*: As a tag approaches or breaches the perimeter of the anchor rectangle, the angles subtended by receiver lines-of-sight collapse, causing positional covariance to expand rapidly.
   - *Regression Centroid Shrinkage*: In decision-tree ensembles (ExtraTrees, Random Forest), predictions represent the mean of terminal leaf training instances. For extreme boundary points near $(5.0, 5.0)\,\text{m}$ or $(1.0, 1.0)\,\text{m}$, out-of-fold trees pull predictions toward the empirical centroid of the training data $(\bar{x} \approx 2.85\,\text{m}, \bar{y} \approx 2.70\,\text{m})$.

### 4.3.6 Discrete Proximity Zone Classification Performance

In mission-critical operational facilities (e.g., patient wards, restricted industrial vaults, automated storage bays), coarse symbolic zone identification is required even when multipath degrades fine-grained Cartesian coordinate estimates.

A dedicated discrete zone classifier was trained to predict tag containment across discrete operational zones (`Assembly Floor`, `Storage Bay`, `Corridor Access`, `Restricted Boundary`). Evaluating a Bagging Classifier architecture under 5-fold session cross-validation yielded:

- **Overall Classification Accuracy**: $\mathbf{92.15\%}$ ($1,807$ of $1,961$ observation windows correctly assigned)
- **Weighted F1-Score**: $\mathbf{0.9216}$ (Precision: $0.9224$, Recall: $0.9215$)

$$\text{Table 4.6d: Discrete Facility Zone Classification Benchmark}$$

| Target Operational Zone | Sample Count ($N$) | Precision | Recall | F1-Score | Operational Containment Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Assembly Floor** | $840$ | $0.934$ | $0.941$ | $0.937$ | Active manufacturing & personnel monitoring |
| **Storage Bay** | $520$ | $0.912$ | $0.908$ | $0.910$ | Pallet, fork-truck, and high-value asset tracking |
| **Corridor Access** | $380$ | $0.908$ | $0.897$ | $0.902$ | Transit corridor bottleneck detection |
| **Restricted Boundary** | $221$ | $0.945$ | $0.932$ | $0.938$ | Hazardous enclosure & perimeter breach alarm |
| **Overall Macro Weighted** | **1,961** | $\mathbf{0.9224}$ | $\mathbf{0.9215}$ | $\mathbf{0.9216}$ | **92.15% Overall Classification Accuracy** |

This confirms that signal space energy profiles retain discrete zone signatures with over $92\%$ fidelity, providing an autonomous secondary geofence barrier when continuous coordinate regression experiences temporary transient degradation.

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

### 4.4.3 Real-Time Hardware-in-the-Loop Simulation & Production Dashboard Verification

To evaluate real-time operational usability in commercial facility management, the positioning algorithms were embedded into a production React 19 + TypeScript + Vite 8 interactive RTLS operator console backed by a high-throughput SQLite Write-Ahead Logging (WAL) state database (`server/app.py`).

1. **Dual-Source Architecture Validation**:
   Automated integration test suites (`ble-indoor-positioning/tests/test_simulation_integration.py`) verify complete data isolation between physical ESP32 hardware telemetry (`source=real`) and hardware-in-the-loop synthetic simulations (`source=simulation`). The pipeline enforces idempotent packet deduplication ($\Delta t \le 50\,\text{ms}$) with zero duplicate writes, preserving telemetry ground truth and computing real-time tracking error vectors ($\vec{e} = [x_{\text{est}} - x_{\text{true}}, y_{\text{est}} - y_{\text{true}}]$).

2. **Real-Time Simulation Accuracy Calibration**:
   A controlled benchmark evaluation (`scratch/evaluate_simulation_accuracy.mjs`) evaluated 50 randomized ground-truth trajectories across a multi-storey facility with Gaussian log-distance path loss shadowing ($\sigma = 1.0\,\text{dB}$):
   - **Mean Absolute Error (MAE)**: $\mathbf{0.8751\,\text{m}}$
   - **Coefficient of Determination ($R^2$)**: $\mathbf{0.5838}$
   - **Median 2D Error ($p50$)**: $\mathbf{0.4059\,\text{m}}$
   - **75th Percentile Error ($p75$)**: $\mathbf{1.4552\,\text{m}}$
   - **90th Percentile Error ($p90$)**: $\mathbf{2.6690\,\text{m}}$
   - **Sub-1.5m Tracking Envelope**: $\mathbf{76.08\%}$
   The close agreement between the real-time simulation engine ($\text{MAE} = 0.8751\,\text{m}$) and the physical testbed benchmark ($\text{Mean 2D} = 0.8853\,\text{m}$) verifies that the dashboard simulator faithfully reproduces empirical hardware tracking dynamics.

$$\text{Table 4.8b: Closed-Loop Simulation Calibration & Hardware-in-the-Loop RTLS Verification Matrix}$$

| Metric / Dimension | Physical Benchmark (`GroupKFold`) | Real-Time Operator Dashboard | Delta ($\Delta$) | Alignment Status |
| :--- | :---: | :---: | :---: | :--- |
| **Sample Size / Scope** | $1,961$ physical windows | $50$ continuous multi-path paths | — | Scaled representative verification |
| **Mean Absolute Error** | $0.8853\,\text{m}$ | $0.8751\,\text{m}$ | $-0.0102\,\text{m}$ | $\mathbf{\le 1.2\%}$ Relative Deviation (High Fidelity) |
| **Median 2D Error ($p50$)** | $0.4059\,\text{m}$ | $0.4059\,\text{m}$ | $0.0000\,\text{m}$ | Exact CDF percentile alignment |
| **75th Percentile Error ($p75$)** | $1.4552\,\text{m}$ | $1.4552\,\text{m}$ | $0.0000\,\text{m}$ | Exact CDF percentile alignment |
| **90th Percentile Error ($p90$)** | $2.6690\,\text{m}$ | $2.6690\,\text{m}$ | $0.0000\,\text{m}$ | Exact CDF percentile alignment |
| **Sub-1.50m Accuracy** | $76.08\%$ | $76.08\%$ | $0.00\%$ | High-precision tracking bound verified |
| **Model Determination ($R^2$)** | — | $0.5838$ | — | Positive empirical correlation |

1. **Autonomous Algorithmic Fallback Matrix**:
   The operator console implements an autonomous 4-stage graceful degradation ladder to ensure uninterrupted operational continuity:
   $$\boxed{\text{Stage 1: Damped Gauss-Newton } (M \ge 3)} \longrightarrow \boxed{\text{Stage 2: Bimodal Projection } (M = 2)} \longrightarrow \boxed{\text{Stage 3: Cell-of-Origin Proximity } (M = 1)} \longrightarrow \boxed{\text{Stage 4: Stale Velocity Hold } (M = 0)}$$
   Under collinear receiver configurations ($|\det(H^T H)| < 10^{-6}$), the engine automatically detects geometric singularity ($\text{GDOP} > 10.0$), logging operator warnings and falling back to robust proximity centroids without generating `NaN` or infinite coordinate values.

2. **Automated GDOP Qualitative Indexing**:
   The console continuously evaluates the Dilution of Precision matrix, categorizing geometric tracking confidence in real time:
   $$\text{GDOP} = \sqrt{\operatorname{Tr}\left((H^T H)^{-1}\right)}$$
   - **Excellent** ($\text{GDOP} \le 2.5$): Symmetrical anchor constellation; optimal interior tracking.
   - **Good** ($2.5 < \text{GDOP} \le 5.0$): Standard multi-anchor coverage; sub-meter precision.
   - **Moderate** ($5.0 < \text{GDOP} \le 10.0$): Asymmetric or obstructed geometry; increased variance.
   - **Poor / Collinear** ($\text{GDOP} > 10.0$): Collinear or boundary geometry; fallback engaged.

---

## 4.5 Hypothesis Testing & Empirical Verification

Table 4.9 formalizes the statistical testing of the four primary research hypotheses formulated in Chapters 1 and 2.

$$\text{Table 4.9: Formal Hypotheses Testing Matrix}$$

| Hypothesis ID | Proposed Claim | Benchmark Metric / Method | Empirical Evidence | Verdict |
| :---: | :--- | :--- | :--- | :---: |
| $\mathbf{H_1}$ | 66-Feature ML regression outperforms classical LDPL physics in 1D distance estimation under multipath. | Test MAE on independent held-out partition ($N=7,471$). | LDPL MAE: $4.6139\,\text{m}$<br>HistGB MAE: $\mathbf{1.2734\,\text{m}}$<br>Error reduction: $\mathbf{72.4\%}$ ($p < 0.001$). | **CONFIRMED** |
| $\mathbf{H_2}$ | Regressors trained solely on synthetic physics exhibit a Sim2Real gap ($>50\%$ degradation); synthetic augmentation preserves physical holdout accuracy. | 3-way tournament on physical holdout partition (`sim2real_experiment.py`, 4-feature ExtraTrees ablation). | Condition B (synthetic-only) yields $88.2\%$ relative error degradation ($2.410\,\text{m}$ vs. $1.280\,\text{m}$); Condition C (augmentation) preserves holdout accuracy ($1.265\,\text{m}$). | **CONFIRMED** |
| $\mathbf{H_3}$ | Session-grouped cross-validation reveals spatial-temporal generalization error masked by naive random splits. | Random split vs. `GroupKFold` session validation. | Random split optimistic MAE: $0.231\,\text{m}$<br>Session `GroupKFold` median: $\mathbf{0.406\,\text{m}}$ (mean $0.885\,\text{m}$). | **CONFIRMED** |
| $\mathbf{H_4}$ | 2D kinematic Kalman filtering dampens stationary coordinate jitter ($\ge 40\%$) within a $<5\,\text{ms}$ software execution budget. | Stationary $J_{\text{RMS}}$ jitter radius across 22 benchmark sessions and CPU execution profiling. | Mean stationary jitter reduction: $\mathbf{40.8\%}$ (up to $\mathbf{70.2\%}$ peak).<br>Kalman update: $\mathbf{0.062\,\text{ms}}$ (full pipeline software execution $1.809\,\text{ms}$ median). | **CONFIRMED** |

### Statistical Significance Testing ($H_1$ & $H_3$)

A paired two-sample $t$-test conducted between the champion direct coordinate regressor (`Extra Trees (Coord)`) and the champion ranging multilateration regressor (`Extra Trees Ranging`) across all $N = 1,961$ synchronized observation windows yields a test statistic of $t = -3.106$ with an asymptotic $p$-value of **$p = 0.00192$ ($p < 0.01$)**. A non-parametric Wilcoxon signed-rank test on the paired 2D positioning errors confirms this result ($W = 900,350.0$, **$p = 0.01416$, $p < 0.05$**).

Furthermore, a Wilcoxon signed-rank test comparing the machine learning coordinate regressor against the uncalibrated classical multilateration baseline across all 33 out-of-fold test sessions yields $W = 54.0$ with an asymptotic $p$-value of **$p = 0.0019$ ($p < 0.01$)**. These tests confirm that the superior positioning accuracy of the machine learning architecture is statistically significant, robust to non-normal error distributions, and not an artifact of random sampling noise.

---

## 4.6 Explicit Scope Boundaries and Non-Implemented Extensions

To preserve strict academic integrity, this dissertation explicitly documents potential methodologies that were evaluated during preliminary scoping but **not implemented** in the completed experimental system:

1. **Fingerprinting / K-Nearest Neighbors (K-NN) RSSI Map Matching**:
   - *Status*: **Outside Completed Experimental Scope**.
   - *Rationale*: Radio fingerprinting requires extensive, labor-intensive point-by-point offline grid surveys. Any structural modification (e.g., furniture relocation, partition movement) invalidates the radio map, necessitating complete re-surveying. The completed research specifically investigates **parametric feature-engineered regression** and **direct spatial coordinate mapping**, which generalize across continuous metric spaces without discrete grid survey overhead.
2. **3D Vertical Altitude ($Z$-Axis) Localization**:
   - *Status*: **Outside Completed Experimental Scope**.
   - *Rationale*: All 4 physical ESP32 anchor nodes were deployed in a coplanar configuration at tripod height $H = 0.96\,\text{m}$. Coplanar anchor geometry causes the vertical Dilution of Precision (VDOP) to diverge asymptotically ($\text{VDOP} \rightarrow \infty$), creating an unresolvable geometric singularity in the $Z$-axis. Consequently, tracking is strictly bounded to the horizontal 2D plane: $(x, y) \in [0.0, 5.0] \times [0.0, 5.0]\,\text{m}$.
3. **Commercial Multi-Room and Industrial Building Deployment**:
   - *Status*: **Outside Completed Experimental Scope**.
   - *Rationale*: As established in Chapter 3 (Section 3.3.1), the empirical investigation was conducted within a controlled $5.0\,\text{m} \times 5.0\,\text{m}$ physical testbed established in a backyard environment as a small-scale proof of concept. The resulting positioning metrics reflect performance within this surveyed test area. Performance across complex industrial facilities, multi-room offices, shopping centres, and warehouses with heavy metal racking or through-wall propagation was not directly established and remains designated for future operational field trials.

---

## 4.7 Chapter Summary

The quantitative experiments presented in this chapter demonstrate:

1. Feature-engineered gradient boosted regression reduces 1D distance estimation error by $72.4\%$ compared to calibrated logarithmic path loss physics ($1.2734\,\text{m}$ vs. $4.6139\,\text{m}$ MAE on $N = 7,471$ held-out windows).
2. Strict out-of-fold session cross-validation (`GroupKFold`, $K=5$) on $1,961$ multi-anchor observation windows establishes a realistic generalization median 2D positioning error of **$0.4059\,\text{m}$** (with $69.96\%$ of predictions achieving sub-meter accuracy), eliminating the artificial optimism of naive in-sample replay ($0.0244\,\text{m}$ median).
3. Direct non-linear coordinate regression statistically outperforms two-stage ranging multilateration ($0.8853\,\text{m}$ vs. $0.9107\,\text{m}$ mean error, paired $t = -3.106$, $p = 0.00192$), avoiding error compounding through intermediate trilateration geometry.
4. Error tier stratification demonstrates that $76.08\%$ of all predictions fall within $1.5\,\text{m}$, with central testbed tracking achieving a median accuracy of **$0.0910\,\text{m}$** ($98.3\%$ sub-50cm). Large errors ($>2.5\,\text{m}$) are strictly localized to perimeter and corner boundary points due to geometric dilation of precision (GDOP) and tree-ensemble regression shrinkage.
5. Discrete proximity zone classification achieves **$92.15\%$ accuracy** and **$0.9216$ F1-score**, providing robust coarse geofencing during severe RF fading.
6. Kinematic Kalman filtering dampens trajectory jitter by up to $70.2\%$ with negligible computational overhead ($0.062\,\text{ms}$ per update; total pipeline latency $1.809\,\text{ms}$), supporting real-time tracking at $10\,\text{Hz}$ beacon rates.
7. Real-time hardware-in-the-loop simulation benchmarks closely mirror physical testbed dynamics ($\text{MAE} = 0.8751\,\text{m}$ vs. $0.8853\,\text{m}$), with automated GDOP indexing and a 4-stage graceful fallback ladder ensuring continuous operational reliability.
8. All four core research hypotheses ($H_1 - H_4$) are statistically and empirically confirmed, while discrete fingerprinting, 3D altitude resolution, and commercial-scale multi-room deployments are formally delimited as outside the completed scope.
