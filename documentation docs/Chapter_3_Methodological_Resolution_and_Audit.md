# Methodological Clarification, System Audit, and Editorial Rectification Report

**Document Reference:** `Dissertation/Methodology-Audit-v2.1`  
**Governing Artifacts:**  
- `Chapter_3_Research_Methodology.md` (and compiled PDF/HTML)  
- `Chapter_4_Results_and_Discussion.md` (and compiled PDF/HTML)  
- `ble-indoor-positioning/server/app.py`  
- `ble-indoor-positioning/localization/trilateration.py`  
- `ble-indoor-positioning/collector/recording.py`  
- `ble-indoor-positioning/datasets/` & `reports/`  

---

## 1. Executive Summary and Audit Purpose

Following an exhaustive peer review of the comprehensive methodology presented in **Chapter 3: Research Methodology & Empirical System Design**, this report formalizes the definitive technical resolutions, architectural clarifications, and editorial rectifications required to freeze Chapter 3.

The governing research principle of this dissertation is **empirical fidelity**: the written dissertation must describe exactly what the deployed firmware, backend algorithms, and laboratory testbed execute, avoiding post-hoc rationalizations or theoretical descriptions that deviate from source-code realities.

This audit:
1. Resolves all **eight outstanding technical questions** directly against the codebase, hardware firmware, and empirical records.
2. Formulates the **five technical corrections** (A through E).
3. Provides an itemized modification schedule for updating `Chapter_3_Research_Methodology.md` to ensure seamless alignment across Chapters 1, 2, 3, and 4.

---

## 2. Definitive Clarifications on the Eight Inquiries

### 2.1 Question 1: LDPL Path-Loss Exponent Reconciliation ($n = 2.12$ vs. $n = 2.50$)

#### The Identified Discrepancy
- Section 3.1.2 ($H_1$): References an LDPL baseline parameterized with $n = 2.50$.
- Section 3.4.1 (Table 3.4): Details empirical testbed calibration yielding $P_{\text{tx}} = -76.45\,\text{dBm}$ and $n = 2.12$.
- Section 3.5.2: Cites $n = 2.50$ as the path-loss exponent for the experimental environment.

#### Codebase and Empirical Verification
In wireless propagation literature (Rappaport, 2002), $n = 2.50$ represents a standard uncalibrated textbook heuristic for obstructed or partitioned indoor office environments. Conversely, $n = 2.12$ is the **empirically fitted least-squares propagation exponent** obtained by performing log-linear regression on clean Line-of-Sight (LOS) calibration measurements within the physical $5.0\,\text{m} \times 5.0\,\text{m}$ testbed across 15 discrete distance presets ($d \in [0.5, 5.3]\,\text{m}$), with measured 1-meter reference power $A = -76.45\,\text{dBm}$ (`datasets/observations.csv`, Table 3.4).

In the Layer 1 distance regression benchmarks (Chapter 4, Table 4.1), the deterministic baseline evaluated against the champion machine learning model (`HistGradientBoostingRegressor`) uses the empirically fitted parameters ($A = -76.45\,\text{dBm}, n = 2.12$). This achieves an MAE of $4.6139\,\text{m}$ on the independent held-out partition ($N = 7,471$), which the machine learning model improves upon by $72.4\%$ ($1.2734\,\text{m}$ MAE).

#### Final Resolution
Both values must remain in the text, but their methodological roles must be unambiguously distinguished:
1. **$n = 2.50$** is documented as the **nominal textbook heuristic** for generic indoor radio environments before empirical site calibration.
2. **$n = 2.12$** ($A = -76.45\,\text{dBm}$) is the **empirically calibrated baseline exponent** measured in the physical testbed under clean Line-of-Sight conditions.
3. In all comparative benchmarking against machine learning (Table 3.1, Section 3.1.2, and Section 3.5.2), the baseline is explicitly designated as the **calibrated Log-Distance Path-Loss baseline ($A = -76.45\,\text{dBm}, n = 2.12$)**, representing the most rigorous possible physical comparator.

---

### 2.2 Question 2: Final Positioning Architecture (Zero Fingerprinting)

#### The Architectural Alignment
The earlier proposal contemplated offline radio fingerprinting (K-NN RSSI signal-strength maps) and dynamic algorithm switching. The implemented and frozen production system deliberately diverged from this approach.

#### Codebase Verification (`server/app.py` lines 587–610)
```python
# Primary: Multi-Anchor Coordinate Regression Champion
if shared.get('coord_model') is not None and shared.get('coord_scaler') is not None:
    try:
        X_feat = extract_multi_anchor_features(tag, now_ms)
        if X_feat is not None and np.all(np.isfinite(X_feat)):
            X_s = shared['coord_scaler'].transform(X_feat)
            raw_coord = shared['coord_model'].predict(X_s)[0]
            pos = (
                float(max(0.0, min(5.0, raw_coord[0]))),
                float(max(0.0, min(5.0, raw_coord[1])))
            )
    except Exception as e:
        logger.warning(f'Direct coordinate model inference fallback to trilateration: {e}')

# Fallback: Ranging-based Levenberg-Marquardt Trilateration
if pos is None:
    sorted_anchors = sorted(active_distances.items(), key=lambda item: item[1])
    top_k_distances = dict(sorted_anchors[:4])
    pos, uncertainty, gdop = shared['trilateration_engine'].estimate_position(top_k_distances)

smoothed_x, smoothed_y = tag.kalman_filter.filter(pos[0], pos[1])
```

#### Final Architecture Statement
The finalized, operational positioning architecture is:
$$\boxed{\textbf{MultiOutput ExtraTrees 2D Coordinate Regression} \longrightarrow \textbf{LM Multilateration Fallback} \longrightarrow \textbf{2D Constant Velocity Kalman Filter}}$$

- **Primary Pathway**: Direct 2D regression via `MultiOutputRegressor(ExtraTreesRegressor(n_estimators=250))` mapping a 21-dimensional multi-anchor spatial feature vector directly to Cartesian coordinates $(x, y) \in [0.0, 5.0]\,\text{m}$.
- **Fallback Pathway**: 1D distance regression (`HistGradientBoostingRegressor`) followed by non-linear Levenberg-Marquardt multilateration (`TrilaterationEngine`), invoked if the direct regressor model file is uninitialized or encounters an inference exception.
- **Kinematic State Estimation**: Discrete-time 2D Constant Velocity Kalman Filter ($q = 0.05\,\text{m}^2/\text{s}^2, r = 0.80\,\text{m}^2$) applied to raw coordinates $(z_x, z_y)$ for jitter dampening.
- **Fingerprinting Exclusion**: **100% excluded from runtime**. As formally documented in Section 3.6.4 and Section 4.6, radio fingerprinting was rejected because dense radio-map grid surveys are labor-intensive, sensitive to dynamic layout changes, and fail to generalize across unvisited continuous coordinates. Chapters 1 and 2 will be synchronized to present this parametric architecture as the primary design.

---

### 2.3 Question 3: Fallback Logic for Fewer than Three Anchors ($M < 3$)

#### The Technical Contradiction
Previous drafts contained conflicting statements regarding behavior when active anchors $M < 3$: one section indicated multilateration execution; another noted mathematical underdetermination; another indicated coordinate retention.

#### Codebase Verification (`server/app.py` lines 578–581 & lines 219–235)
In the live backend processing loop (`server/app.py`):
```python
tag.estimated_distances = active_distances
if len(active_distances) < 3:
    tag.status = tag.get_position_status()
    return
```

And in `TagState.get_position_status()`:
```python
def get_position_status(self, now: Optional[float] = None) -> str:
    if self.last_position is None or self.last_position_time is None:
        return 'unavailable'
    current_time = now if now is not None else time.time()
    age = current_time - self.last_position_time
    if age <= 4.0:
        return 'current'
    elif age <= 30.0:
        return 'stale'
    return 'unavailable'
```

#### Unified System Specification
The actual runtime system enforces a strict geometric gate at $M = 3$. Table 2.1 formalizes the exact runtime behavior across all anchor availability conditions:

$$\text{Table 2.1: Unified Degraded Anchor Availability State Matrix}$$

| Active Anchors ($M$) | Geometric Determinacy | Computational Action | Emitted Coordinate $(x, y)$ | Freshness State Lifecycle | Dashboard Visual Semantics |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **$M = 4$** | Fully Overdetermined (Optimal GDOP) | Full 21-feature ExtraTrees regression (LM fallback if exception) | Newly estimated Cartesian coordinates $(\hat{x}, \hat{y})$ | `current` ($\text{age} \le 4.0\,\text{s}$) | Solid green marker, nominal $0.41\,\text{m}$ confidence circle |
| **$M = 3$** | Exactly Determined / Minimal Overdetermined | 21-feature regression with 1 imputed anchor ($-100\,\text{dBm}$) | Newly estimated Cartesian coordinates $(\hat{x}, \hat{y})$ | `current` ($\text{age} \le 4.0\,\text{s}$) | Solid green marker, elevated GDOP boundary |
| **$M = 2$** | Underdetermined (Dual-intersection ambiguity) | **Zero coordinate computation**. Localization pipeline terminates immediately (`return`). | **Last known valid coordinate retained** in state memory. | Transitions to `stale` ($4.0\,\text{s} < \text{age} \le 30.0\,\text{s}$) | Amber/yellow marker, expanding dashed uncertainty ring |
| **$M = 1$** | Completely Degenerate (Radial circle only) | **Zero coordinate computation**. Localization pipeline terminates immediately (`return`). | **Last known valid coordinate retained** in state memory. | Transitions to `stale` ($4.0\,\text{s} < \text{age} \le 30.0\,\text{s}$) | Amber/yellow marker, decaying status indicator |
| **$M = 0$** | Complete Radio Blackout (No packets) | **Zero coordinate computation**. Ingestion buffer empty. | Coordinates retained until timeout, then retracted. | Transitions to `unavailable` ($\text{age} > 30.0\,\text{s}$) | **Withdrawn from tracking canvas**; moved to offline roster |

*Reconciliation Note*: While `localization/trilateration.py` contains standalone defensive fallbacks for unit tests (returning the anchor coordinate for $M=1$ or room center for $M=0$ with GDOP 99.9), the production localization pipeline in `server/app.py` intercepts the flow at line 579: **no coordinates are ever computed or fabricated for $M < 3$**.

---

### 2.4 Question 4: Nonlinear Least-Squares Solver Implementation (SciPy `method='lm'` Ordinary Least Squares)

#### The Discrepancy
Section 3.6.2 and Section 3.7.4 stated that the multilateration fallback executes Levenberg-Marquardt with Soft $L_1$ loss. However, mathematical optimization theory and SciPy API specifications indicate that the Levenberg-Marquardt algorithm (`method='lm'`) strictly minimizes classical sum-of-squares ($L_2$ norm) and does not support robust M-estimators.

#### Codebase Verification (`localization/trilateration.py` lines 52–64)
```python
def residuals(pos):
    diffs = active_coords - pos
    calculated_dists = np.linalg.norm(diffs, axis=1)
    return calculated_dists - active_dists

try:
    res = least_squares(residuals, x0, method='lm')
    if res.success and np.all(np.isfinite(res.x)):
        estimated_pos = res.x
    else:
        logger.warning('Least-squares optimization did not converge cleanly. Using centroid fallback.')
except Exception as e:
    logger.error(f'Trilateration optimization error: {e}. Falling back to centroid.')
    estimated_pos = x0
```

#### Final Resolution
The production implementation strictly executes:
$$\min_{\mathbf{p} \in \mathbb{R}^2} \frac{1}{2} \sum_{j=1}^{M} r_j(\mathbf{p})^2, \quad \text{via } \texttt{scipy.optimize.least\_squares(residuals, x0, method='lm')}$$
1. The solver operates under **classical ordinary least squares ($L_2$ Euclidean norm)**.
2. SciPy does not permit `loss='soft_l1'` with `method='lm'` (robust loss functions in SciPy require `method='trf'` or `method='dogbox'`).
3. Outlier divergence and non-convergence are handled programmatically via **numerical exception trapping that falls back to the analytical geometric centroid** ($\mathbf{p}_0 = \frac{1}{M}\sum \mathbf{a}_j$).
4. All occurrences of "with Soft L1 loss" in Chapter 3 are corrected to: *"classical ordinary least squares Levenberg-Marquardt optimization with automated centroid exception fallback"*.

---

### 2.5 Question 5: Dynamic Tracking Data Scope and Empirical Ground Truth

#### The Scope Boundary
The research methodology formulates $H_4$ around kinematic filtering and tracking lag. However, the physical multi-anchor dataset (`datasets/` CSV files, 33 sessions across 10 surveyed coordinates) consists of **stationary benchmark recordings**, with 22 sessions concentrated at the central benchmark coordinate $(2.5, 2.5)\,\text{m}$.

#### Empirical Ground-Truth Protocol
1. **Physical Testbed Measurements**: Ground truth was established using precision laser-distancer measurements relative to surveyed room corners on a verified metric grid ($[0.0, 5.0]\,\text{m}$).
2. **Tag Physical Relocation**: Between discrete collection sessions, the physical BLE tag was manually relocated among the surveyed benchmark coordinates.
3. **Absence of Continuous Optical Motion Capture**: The laboratory environment did not feature an external millimeter-grade motion capture camera rig (e.g., Vicon or OptiTrack) required to measure continuous ground-truth kinematics of a freely moving human walking at variable speeds.
4. **Legitimate Scope of Claims**:
   - The Kalman filter evaluation legitimately confirms **stationary multipath jitter dampening** ($40.8\%$ noise suppression on direct ML coordinates, $70.2\%$ on multilateration coordinates).
   - It legitimately evaluates **step-response settling time and phase delay** across inter-session coordinate transitions.
   - It legitimately proves **sub-millisecond computational execution time** ($0.062\,\text{ms}$) under high-throughput streaming.
   - **Academic Boundary Enforced**: Chapter 3 explicitly restricts $H_4$ claims to **stationary jitter suppression, transition settling dynamics, and real-time execution latency**. It explicitly disclaims continuous kinematic trajectory tracking accuracy against moving ground truth, designating dynamic trajectory tracking with optical ground-truth verification as a future work extension.

---

### 2.6 Question 6: Latency Budget Decomposition (Execution vs. Window Accumulation)

#### The Latency Conflict
The text states both a 1,000 ms observation window and a sub-100 ms end-to-end latency budget (with profiled execution latency of $1.809\,\text{ms}$).

#### Detailed Timing and Ingestion Decomposition
To eliminate ambiguity, system timing is formally decomposed into three distinct operational boundaries:

$$\text{Table 2.2: Systematic Breakdown of Latency Boundaries and Timing Horizons}$$

| Latency Horizon | Temporal Parameter | Operational Mechanism | Physical Meaning and Evaluation Criterion |
| :--- | :---: | :--- | :--- |
| **Window Accumulation Horizon** | $1000\,\text{ms}$ | Rolling FIFO buffer maintained in memory per anchor (`WINDOW_SIZE_MS = 1000`) | Statistical observation window required to capture sufficient packet density ($2 - 10$ packets) for extracting higher-order moments and histograms. Does *not* introduce a 1-second batch pipeline stall. |
| **Algorithmic Execution Latency** | **$1.809\,\text{ms}$** (mean)<br>$3.830\,\text{ms}$ (P99) | Ingestion $\to$ Feature extraction $\to$ ExtraTrees inference $\to$ Kalman filter update | Computational CPU time required to process a newly formed feature vector and update the state filter. Confirmed well within the $5.0\,\text{ms}$ real-time algorithmic budget. |
| **Live End-to-End Pipeline Latency** | **$< 100.0\,\text{ms}$** | Radio frame emission $\to$ ESP32 UART/Wi-Fi $\to$ UDP socket $\to$ Pipeline $\to$ WebSocket push | Total elapsed latency from physical radio packet arrival at an edge anchor to visual canvas rendering on the React dashboard. Evaluated dynamically upon packet arrival using sliding historical buffers. |

*Operational Clarification*: The live server does not wait idle for 1,000 ms between updates. It maintains a continuously updated sliding window. Whenever new telemetry packets arrive, the engine evaluates feature statistics over the preceding window and immediately emits a new state estimate. Thus, the operational pipeline latency is governed by CPU execution ($1.809\,\text{ms}$) and network transport ($5 - 15\,\text{ms}$), easily fulfilling the $< 100.0\,\text{ms}$ real-time budget for $10\,\text{Hz}$ beaconing.

---

### 2.7 Question 7: Human Participation, Experimental Roles, and Ethics Exemption

#### Experimental Context
Physical obstacle attenuation trials (Section 3.4.1, Table 4.3) measured radio shadowing induced by human bodies (chest/back placement, torso shadowing, standing personnel).

#### Institutional Ethics and Privacy Statement
1. **Role of Participants**: All human-body radio attenuation trials were conducted exclusively by the **primary researchers** acting as physical radio-frequency obstacles and equipment operators in a controlled laboratory environment.
2. **No External Volunteers**: No external human subjects, members of the public, patients, or vulnerable individuals were recruited or tested.
3. **No Personal or Identifying Data**: Zero personal, physiological, biometric, medical, or identifying data were collected, stored, or processed. The recorded dataset consists strictly of physical radio observables: beacon MAC address, ESP32 anchor ID, RSSI ($\text{dBm}$), and hardware millisecond timestamps.
4. **Institutional Review Exemption**: Under institutional research ethics policies (consistent with IEEE and standard university guidelines for physical sciences and engineering), non-invasive physical measurements where investigators manipulate laboratory radio hardware and act as inert radio obstructions without collecting personal data are exempt from formal institutional review board (IRB) or human-subject ethics clearance.
5. **Inclusion in Chapter 3**: A dedicated "3.1.4 Research Ethics, Participant Protocols, and Data Protection Statement" is added to Chapter 3 codifying these facts.

---

### 2.8 Question 8: Hardware MAC Addresses and Data Protection

#### Context
The text documents physical MAC addresses:
- `24:6F:28:1A:4C:01` through `24:6F:28:1A:4C:04` (ESP32 Anchors 1–4)
- `52:06:26:03:01:DA` (Laboratory BLE 5.0 beacon tag)
- `D0:EF:76:58:F6:FC` (Laboratory ESP32 test module)

#### Recommendation and Resolution
1. **Nature of Addresses**: These addresses represent IEEE 802.15.1 and 802.11 factory-assigned hardware Medium Access Control identifiers burned into the silicon of dedicated ESP32 development boards and commercial laboratory beacon tags owned by the researchers.
2. **Zero Privacy Risk**: They do not belong to mobile phones, laptops, consumer wearables, or personnel. They contain zero personal data and cannot be linked to any individual.
3. **Academic Decision**: To preserve complete experimental reproducibility, silicon hardware auditability, and verbatim log verification (allowing external examiners to match published packet captures against verbatim logs), the hardware identifiers **remain visible in the dissertation text**.
4. **Explanatory Clarification**: An explicit footnote/statement is attached to Section 3.3.1 stating:
   > *"All MAC addresses reported in this dissertation correspond exclusively to dedicated laboratory microcontroller development boards and standalone reference beacon hardware; none correspond to personal consumer devices, mobile phones, or identifiable individuals."*

---

## 3. Resolution of the Five Technical Corrections

### 3.1 Correction A: Isolation Forest Contamination Factor Wording
- **Identified Defect**: In Section 3.4.3, the text read: *"with a 3.0 contamination factor (contamination=0.03)"*.
- **Rectification**: Revised to standard mathematical notation:
  > *"with a $3.0\%$ contamination factor (`contamination = 0.03`, `random_state = 42`)"*.

### 3.2 Correction B: Hypothesis Acceptance Threshold Percentage Symbols
- **Identified Defect**: Several hypothesis thresholds in Section 3.1.2 were written as bare numbers ($30.0$, $50.0$, $40.0$) without explicit percentage notation.
- **Rectification**: Explicitly formatted with `%` across all occurrences:
  - $H_1$ Relative MAE reduction: $\Delta\text{MAE}_{\text{rel}} \ge \mathbf{30.0\%}$ ($p < 0.01$).
  - $H_2$ Sim2Real transfer gap: $\text{Gap}_{\text{Sim2Real}} > \mathbf{50.0\%}$ relative error inflation.
  - $H_4$ Stationary jitter reduction: $J_r \ge \mathbf{40.0\%}$.

### 3.3 Correction C: Section 3.9 Nomenclature (Conclusion vs. Chapter Summary)
- **Identified Defect**: University dissertation formatting guidelines require every chapter to terminate with a formal Conclusion section. The heading was titled `3.9 Chapter Summary`.
- **Rectification**: Renamed heading to:
  > `## 3.9 Conclusion`
  The synthesis content is maintained while framing it as a definitive conclusion to Chapter 3 that leads into the empirical results of Chapter 4.

### 3.4 Correction D: Strict Segregation of Methodology Protocols and Chapter 4 Results
- **Identified Defect**: A small number of specific empirical findings (e.g., $0.4059\,\text{m}$ median error, $40.8\%$ and $70.2\%$ jitter suppression, $1.809\,\text{ms}$ pipeline latency, $131$ passed unit tests) appeared in Chapter 3 without clear attribution.
- **Rectification**:
  1. All empirical positioning metrics in Chapter 3 are explicitly labeled as **forward references to Chapter 4 findings** or **operationalized design verification targets**.
  2. Software unit test metrics ($131$ passed, $1$ skipped) are explicitly confined to the software implementation verification taxonomy (Layer II of Table 3.11), clearly distinguished from physical radio localization findings (Layer III).
  3. Chapter 3 focuses rigorously on **how the system was engineered and evaluated**, while Chapter 4 focuses on **what the empirical results revealed**.

### 3.5 Correction E: Precision in Data Classification (Empirical, Synthetic, and Test Data)
- **Identified Defect**: Section 3.1.1 stated that *"all experimental data were gathered within a surveyed physical indoor testbed"*, which conflicted with the synthetic Sim2Real experiment generator and software test fixtures.
- **Rectification**: Revised Section 3.1.1 to read:
  > *"All physical empirical radio data were gathered within a surveyed physical indoor testbed, supplemented by controlled synthetic radio propagation simulations for Sim2Real transfer gap quantification (Section 3.5.4) and automated software fixtures for application integration testing (Section 3.8.3)."*

---

## 4. Itemized Modification Schedule for `Chapter_3_Research_Methodology.md`

The following table provides the precise location and line-by-line edit instructions applied to `Chapter_3_Research_Methodology.md`:

$$\text{Table 4.1: Comprehensive Textual Rectification Schedule}$$

| Section | Line(s) | Current Problematic Text | Corrected Replacement Text |
| :--- | :---: | :--- | :--- |
| **3.1.1** | 8 | `All experimental data were gathered within a surveyed physical indoor testbed...` | `All physical empirical radio data were gathered within a surveyed physical indoor testbed, supplemented by controlled synthetic radio propagation simulations for Sim2Real transfer gap analysis (Section 3.5.4) and automated software fixtures for system integration testing (Section 3.8.3).` |
| **3.1.2** | 16 | `($A = -76.45\,\text{dBm}, n = 2.50$) [3]` | `($A = -76.45\,\text{dBm}, n = 2.12$ calibrated; nominal uncalibrated comparator $n = 2.50$) [3]` |
| **3.1.2** | 19–20 | `relative reduction in MAE of at least 30.0 (ΔMAE_rel ≥ 30.0)...` | `relative reduction in MAE of at least 30.0% ($\Delta\text{MAE}_{\text{rel}} \ge 30.0\%$, $p < 0.01$)...` |
| **3.1.2** | 30–31 | `was > 50.0 higher (relative degradation)...` | `was $> 50.0\%$ higher (relative degradation)...` |
| **3.1.2** | 48 | `stationary jitter reduction J_r ≥ 40.0 across...` | `stationary jitter reduction $J_r \ge 40.0\%$ across...` |
| **3.1.4** | *New* | *(Section did not exist)* | Added **3.1.4 Research Ethics, Participant Protocols, and Data Protection Statement** clarifying researcher-only participation, exemption, and lab hardware MAC nature. |
| **3.4.1** | 232 | `($P_{\text{tx}} = -76.45\,\text{dBm}, n = 2.12$)` | Reinforced: Clarified that $n = 2.12$ is the empirical least-squares fit across Line-of-Sight presets, whereas nominal indoor literature assumes $n = 2.50$. |
| **3.4.3** | 279 | `with a 3.0 contamination factor (contamination=0.03)` | `with a $3.0\%$ contamination factor (`contamination = 0.03`, `random_state = 42`)` |
| **3.5.2** | 408 | `($n = 2.50$ for the experimental environment)` | `($n = 2.12$ for the empirically calibrated testbed baseline; $n = 2.50$ for nominal uncalibrated indoor heuristics)` |
| **3.6.2** | 526–530 | `...with Soft L1 loss... In the production engine... Soft L1 loss...` | Replaced with explicit technical clarification: SciPy `method='lm'` strictly implements ordinary least squares ($L_2$ norm). Centroid fallback and exception handling protect against divergence. |
| **3.6.2** | 538–544 | Multilateration fallback descriptions suggesting coordinates are emitted for $M < 3$. | Synchronized with `server/app.py` line 579: $M < 3$ halts coordinate generation, retaining prior state with decaying freshness (`stale`/`unavailable`). Standalone mathematical fallback in `TrilaterationEngine` distinguished from production runtime gate. |
| **3.6.3** | 569–572 | Broad dynamic tracking language | Refined: Restricted to stationary jitter suppression, transition settling time, and computational latency budget. Disclaimed mobile continuous optical tracking. |
| **3.7.4** | 737 | `...If active anchors M < 3...` | Explicitly codified the exact state decay lifecycle (`current` $\le 4\text{s}$, `stale` $4-30\text{s}$, `unavailable` $>30\text{s}$). |
| **3.7.4** | 739 | `...implementing Levenberg-Marquardt least-squares optimization with Soft L1 loss [7]` | `...implementing Levenberg-Marquardt ordinary least-squares optimization [7] with analytical active-anchor centroid exception fallback.` |
| **3.8.1** | 895–898 | Latency budget description | Formalized the distinct separation between the $1000\,\text{ms}$ rolling observation window and the $1.809\,\text{ms}$ CPU execution latency / $< 100\,\text{ms}$ end-to-end transport latency. |
| **3.9** | 929 | `## 3.9 Chapter Summary` | `## 3.9 Conclusion` |

---

## 5. Verification and Alignment Across Chapters

1. **Chapter 1 Alignment**:
   - The primary research aim is confirmed as direct machine-learning coordinate regression with kinematic Kalman filtering.
   - Radio fingerprinting is explicitly delimited as excluded.
2. **Chapter 2 Alignment**:
   - Literature review sections covering trilateration and fingerprinting are framed as theoretical foundations and comparative context, establishing why parametric ML regression was selected over site-calibrated fingerprinting.
3. **Chapter 4 Alignment**:
   - Every metric forward-referenced in Chapter 3 ($72.4\%$ distance error reduction, $0.4059\,\text{m}$ median 2D error, $40.8\%$ / $70.2\%$ jitter reduction, $1.809\,\text{ms}$ pipeline latency) matches Chapter 4 tables exactly.
4. **Automated Test Alignment**:
   - The 131 passed and 1 skipped tests under `pytest` are documented strictly as software logic verification (Layer II) rather than physical radio localization proof (Layer III).

---

*Report compiled and certified for dissertation submission.*
