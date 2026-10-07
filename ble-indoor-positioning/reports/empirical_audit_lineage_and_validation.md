# Empirical Audit, Dataset Lineage & Scientific Validation

**Authoritative Methodological Reference for Dissertation Defense & Examination**  
*Document Designation: AUDIT-DOC-BLE-2026-V3*  
*Timestamp: October 2026 (Audit Pipeline Verified)*

---

## 1. Traceability of the 2D Multilateration Result (0.7279 m MAE)

### Where does `0.7279 m` come from?
The empirical dataset in [`observations.csv`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/datasets/observations.csv) was collected in radial ranging sessions relative to known ground-truth distances ($d \in [0.5, 7.0]$ meters), rather than simultaneous 4-anchor synchronized packet receptions. 

Consequently, Stage 2 (2D Multilateration) is evaluated via a **semi-empirical Monte Carlo simulation**:
1. **Layout & Geometry**: A standard $6.0\text{ m} \times 6.0\text{ m}$ perimeter is defined with four corner anchors:
   - Anchor 1: $(0.0, 0.0)\text{ m}$
   - Anchor 2: $(6.0, 0.0)\text{ m}$
   - Anchor 3: $(6.0, 6.0)\text{ m}$
   - Anchor 4: $(0.0, 6.0)\text{ m}$
2. **True Location Sampling**: $K = 300$ mobile tag test positions $(x_k, y_k)$ are uniformly sampled within the interior boundary: $(x, y) \sim U(0.5, 5.5)^2$ (reproducible with fixed seed `seed = 42`).
3. **True Radial Ranging**: For each anchor $i \in \{1, 2, 3, 4\}$, true geometric Euclidean distance is computed:
   $$d_{i, k} = \sqrt{(x_k - x_i)^2 + (y_k - y_i)^2}$$
4. **Empirical Residual Perturbation**: Ranging error residuals $\epsilon \sim \mathcal{D}_{\text{test}}$ are sampled directly from the **chronologically embargoed holdout test set (Protocol 2, $N = 5,378$)**:
   $$\hat{d}_{i, k} = \max\left(0.1, d_{i, k} + (p_{\text{xgb}, m} - y_{\text{true}, m})\right)$$
5. **Non-Linear Least Squares Ingestion**: The perturbed ranges $(\hat{d}_1, \dots, \hat{d}_4)$ are ingested into the project's actual production solver ([`TrilaterationEngine`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/localization/trilateration.py)) using Levenberg-Marquardt optimization.
6. **Empirical Results ($K = 300$, Seed = 42)**:
   - **2D Position MAE**: **0.7279 m**
   - **2D Position RMSE**: **0.9802 m**
   - **2D Median Error**: **0.5389 m**
   - **Sub-meter Accuracy ($\le 1.0\text{ m}$)**: **74.0%**
   - **Sub-half-meter Accuracy ($\le 0.5\text{ m}$)**: **47.0%**
   - **Solver Convergence**: 100% (zero divergence across all evaluations).
   - **Dilution of Precision (GDOP)**: **1.02** (the well-conditioned rectangular constellation confirms error is driven by radio ranging variance, not geometric ill-conditioning).

### Monte Carlo Sample-Size Sensitivity Check ($K = 300, 1,000, 5,000$)
To verify that the 0.7279 m figure is not a small-sample Monte Carlo artifact, sample size sensitivity was evaluated using the exact same procedure:

| Sample Size ($K$) | 2D MAE | 2D RMSE | 2D MedAE | $\le 1.0$ m | $\le 0.5$ m | Mean GDOP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$K = 300$ (Primary)** | **0.7279 m** | 0.9802 m | 0.5389 m | 74.0% | 47.0% | 1.02 |
| **$K = 1,000$** | **0.6984 m** | 0.9345 m | 0.5233 m | 75.6% | 48.7% | 1.02 |
| **$K = 5,000$** | **0.7184 m** | 0.9605 m | 0.5265 m | 74.5% | 48.3% | 1.02 |

**Conclusion**: The sensitivity analysis indicates that the estimated 2D positioning error is reasonably stable with respect to Monte Carlo sample size over the evaluated range (varying by under $0.95\text{ cm}$ between $K=300$ and $K=5,000$).

> [!IMPORTANT]
> **Academic Phrasing for the Dissertation**:  
> *"The proposed ML-assisted localization pipeline achieves an estimated 2D positioning MAE of 0.7279 m (median: 0.5389 m, 74.0% $\le 1.0$ m) when empirical ranging residuals from the zero-leakage embargoed test holdout are propagated through the production Levenberg-Marquardt multilateration engine. This result establishes computational error-propagation fidelity under realistic ranging error distributions, rather than physical multi-anchor simultaneous tag localization."*

---

## 2. Definitive Dataset Lineage & Sample Accounting

### The Purge Buffer Rule: $\text{purge} = \max(15, \lfloor 0.05N \rfloor)$
The longest engineered rolling feature reaches back **10 consecutive windows** (`rssi_rolling_mean_10w`, `rssi_rolling_std_10w`). To mathematically guarantee zero test-to-train feature leakage across sliding window boundaries:
$$\text{purge} = \max(15, \lfloor 0.05N \rfloor) \ge 15 > 10$$
This guarantees that the first test window's 10-window lookback falls strictly within the discarded purge zone, eliminating causal reach into training telemetry.

| Stage / Split | Window Count | Sessions | Methodological Description |
| :--- | :---: | :---: | :--- |
| **Total Ingested Raw Telemetry** | **37,623** | **87** | Full dataset collected across 8 calendar dates (July 31 – Sept 28, 2026). |
| **Clean Complete Windows** | **37,623** | **87** | Zero missing values across 59 engineered feature columns. |
| **Protocol 1 (Random Split 80/20)** | 30,098 train / 7,525 test | 87 | Unstratified random partition. Subject to ~89.5% sliding window packet overlap. |
| **Protocol 2 (Chronologically Blocked & Embargoed)** | **30,125 train (80.1%)**<br>**2,120 purged ($\ge 15$ w)**<br>**5,378 test (14.3%)** | **87** | Strict chronological blocking per session. Guaranteed $\ge 15$-window purge buffer. Zero temporal leakage. |
| **Protocol 3 (Distance-Stratified Disjoint Session Holdout)** | **29,693 train (79.2%)**<br>**7,503 test (20.8%)** | **67 train**<br>**24 test** | Exactly 25% of sessions held out per ground-truth distance tier. Zero session overlap. |

---

## 3. Protocol 3: Disjoint Session Split vs. Calendar Date Split

### Code Implementation Verification:
In [`dissertation_audit.py`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/training/dissertation_audit.py), Protocol 3 groups observations by `TARGET_COLUMN` (`distance_m`) and reserves the final 25% of sessions within each distance tier for the test set:
- **Training partition**: 67 sessions, 29,693 observation windows
- **Test partition**: 24 sessions, 7,503 observation windows
- **Session overlap**: Exactly 0.0%

### Why Distance-Stratification is Required Over a Pure Calendar Split:
The physical dataset spans two collection epochs:
1. **Summer (July 31 – August 5, 2026)**: 52 sessions. Surveyed distances: 0.5, 0.6, 0.7, 1.0, 1.1, 1.5, 1.9, 2.0, 3.0, 3.4, 4.5, 4.6, 5.0, 5.3, 7.0 m.
2. **Autumn (September 24 – September 28, 2026)**: 35 sessions. Surveyed distances: 0.0, 1.5, 2.2, 2.5, 2.8, 3.2, 3.4, 3.6, 4.1, 4.3, 4.5, 5.0, 5.6, 5.7, 7.1 m.

If an unstratified pure calendar split is performed (Summer train $N = 33,291$ vs. Autumn test $N = 4,332$), the test partition contains distances (2.2m, 2.5m, 2.8m, etc.) never observed during training. This conflates temporal drift with spatial interpolation to uncalibrated distance points, yielding:
$$\text{MAE}_{\text{calendar}} = 1.2567\text{ m} \quad (+145.6\%)$$

By contrast, the **Distance-Stratified Disjoint Session Holdout** (Protocol 3) ensures both train and test partitions evaluate identical distance regimes, isolating pure session-level and temporal drift across completely independent recording sessions:
$$\text{MAE}_{\text{Protocol 3}} = 1.3864\text{ m} \quad (+170.9\%)$$

> [!NOTE]
> **Scientific Interpretation**:
> The performance degradation ($0.5116\text{ m} \rightarrow 1.3864\text{ m}$) documents uncalibrated temporal and session-dependent distribution shift across collection dates. The dissertation attributes this rigorously to aggregate physical drift (transceiver repositioning, antenna orientations, battery supply voltage, unmeasured multipath variations), explicitly avoiding speculative attribution to unmeasured variables such as ambient humidity or temperature.

---

## 4. Systematic Feature Group Ablation Taxonomy

The 59 engineered features are categorized into three physical and signal-processing domains:

1. **Base Static Moments ($N = 30$)**: Instantaneous window statistics (`rssi_mean`, `rssi_std`, percentiles, SNR, skewness, kurtosis, path loss models).
2. **Temporal & Cross-Window Dynamics ($N = 23$)**:
   - Intra-window temporal dynamics ($N = 8$): `rssi_slope`, `rssi_trend_strength`, `rssi_ema_diff`, `rssi_autocorrelation`, `rssi_energy`, etc.
   - Cross-window rolling filters ($N = 15$): multi-scale rolling means and stds (3, 5, 10 windows), EMA cross-window, velocity, acceleration.
3. **Environmental Interactions & 3D Geometry ($N = 6$)**: `height_m`, `obstacle_factor`, `rssi_x_height`, interaction terms.

### Empirical Ablation Results (Evaluated on Protocol 2 Embargoed Test Holdout $N = 5,378$):

| Feature Configuration | Feature Count | Ranging MAE | Error Delta vs. Full | Physical Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Full Engineered Feature Set** | **59** | **0.5116 m** | **0.0% (Baseline)** | Multi-scale temporal smoothing + statistical moments + environmental terms |
| **Temporal & Cross-Window Only** | **23** | **0.8106 m** | **+58.4%** | Suppresses short-term multipath flutter; lacks static magnitude anchoring |
| **Static Base Features Only (No Rolling)** | **30** | **1.2880 m** | **+151.8%** | Instantaneous distribution moments without temporal memory collapse under fading |
| **Raw Instantaneous RSSI Only** | **1** | **1.2879 m** | **+151.7%** | Classical path-loss mapping corrupted by stochastic Rayleigh phase noise |

**Key Takeaway**: Incorporating temporal cross-window dynamics improves ranging accuracy from $\sim 1.29\text{ m}$ to $0.5116\text{ m}$ (a 60.3% error reduction), proving that machine learning succeeds by learning temporal structure rather than simple static RSSI-to-distance mapping.

---

## 5. Statistical Hypothesis Testing: Statistical vs. Practical Significance

### Statistical Metrics:
- **Models**: XGBoost (Deep Tuned) vs. LightGBM (Deep Tuned)
- **Test Set**: Protocol 2 Embargoed Holdout ($N = 5,378$ paired test residuals)
- **Hypothesis Test**: Two-tailed paired $t$-test on absolute residuals $|y_i - \hat{y}_i|$
- **XGBoost MAE**: **0.5116 m**
- **LightGBM MAE**: **0.5851 m**
- **Test Statistic**: $t = -18.370$
- **p-value**: $p = 3.81 \times 10^{-73}$ ($p \ll 0.001$, highly statistically significant)
- **95% Confidence Interval of Difference**: $[-0.0814\text{ m}, -0.0657\text{ m}]$

### Critical Scientific Assessment:
- **Statistical Significance**: Extreme ($p < 10^{-72}$) due to large sample power ($N = 5,378$).
- **Practical Significance**: Modest. The true absolute difference is:
  $$\Delta \text{MAE} = 0.5851\text{ m} - 0.5116\text{ m} = 0.0735\text{ m} \quad (\approx 7.4\text{ cm})$$
  $$\text{Cohen's } d \approx 0.23 \quad (\text{small effect size})$$
- In room-scale tracking where 2D multilateration error is $\sim 73\text{ cm}$, a $7.4\text{ cm}$ ranging advantage represents an incremental algorithmic refinement rather than a transformative breakthrough.

---

## 6. Authoritative Dissertation Evidence Hierarchy (Results Chapter Skeleton)

| Scientific Claim | Underlying Dataset | Experimental Protocol | Direct or Simulated? | Authoritative Metric | Status in Dissertation |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Single-Link Ranging Accuracy** | Physical ESP32 BLE Telemetry | Protocol 2 (Chronologically Blocked, $\ge 15\text{w}$ purge) | **Direct** | $\text{MAE} = \mathbf{0.5116\text{ m}}$<br>($\text{RMSE} = 0.9894\text{ m}$, $R^2 = 0.7030$, $\le 1\text{m} = 84.9\%$) | 🟢 **Proven Empirically** |
| **Temporal Feature Attribution** | Physical ESP32 BLE Telemetry | Protocol 2 Ablation | **Direct** | Full: $0.5116\text{ m}$ vs.<br>Static: $1.2880\text{ m}$ (+151.8%) | 🟢 **Proven Empirically** |
| **Cross-Session Temporal Generalization** | Physical ESP32 BLE Telemetry | Protocol 3 (Distance-Stratified Disjoint Sessions) | **Direct** | $\text{MAE} = \mathbf{1.3864\text{ m}}$<br>(+170.9% error inflation) | 🟢 **Proven Empirically** (Domain Shift Finding) |
| **2D Multilateration Error Propagation** | Physical Ranging Residuals ($N=5,378$) + 4-Anchor Geometry | Protocol 2 Residual Ingestion into Production Solver | **Semi-Empirical (Monte Carlo)** | 2D $\text{MAE} = \mathbf{0.7279\text{ m}}$<br>(MedAE: $0.5389\text{ m}$, $\le 1\text{m} = 74.0\%$) | 🟡 **Validated Computationally** (Fidelity to runtime engine) |
| **Solver Geometry Stability (GDOP)** | 4-Corner Anchor Constellation ($6\text{m} \times 6\text{m}$) | Levenberg-Marquardt Matrix Inversion | **Analytic / Computational** | $\text{GDOP} = \mathbf{1.02}$<br>(100% convergence) | 🟡 **Validated Analytically** |
| **Simultaneous 4-Anchor Physical 2D Positioning** | None (Single-link sessions in `observations.csv`) | N/A | **N/A** | N/A | 🔴 **Not Demonstrated** (Explicit Dissertation Limitation) |
| **Continuous Tag Trajectory Tracking** | None (Static ground-truth distance points) | N/A | **N/A** | N/A | 🔴 **Not Demonstrated** (Explicit Future Work) |
