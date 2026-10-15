# Empirical Experimental Audit: Questionnaire Responses and Technical Verification

**Document Reference:** `Dissertation/Audit-QnA-v1.0`  
**Governing Codebase:** `ble-indoor-positioning/`  
**Source Datasets:** `ble-indoor-positioning/datasets/observations.csv` & `multi_anchor_observations.csv`  
**Date of Verification:** October 15, 2026  

---

## 1. Experimental Site

**Question:** *What town/city was the experiment conducted in, and was the indoor room residential, institutional, or another type of site?*

### Verified Finding:
- **Town/City & Country**: Johannesburg, Gauteng, South Africa.
- **Facility Classification**: Private residential suburban property.
- **Indoor Area Type**: Residential domestic interior comprising an elongated central hallway ($\approx 8.5\,\text{m} \times 1.4\,\text{m}$) communicating with partitioned living and bedroom quarters ($\approx 4.2\,\text{m} \times 3.8\,\text{m}$, ceiling height $\approx 2.6\,\text{m}$).
- **Outdoor Area Type**: Private residential backyard lawn with an adjoining clay-brick paved pathway ($\approx 12.0\,\text{m} \times 10.0\,\text{m}$ overall open property clearing).
- **Institutional Context**: The investigation was conducted as an individual engineering capstone/research project by Bleigh TJ Bande (`tafabande`). It was treated as a non-human-subject engineering experiment conducted in a private controlled setting.

---

## 2. Indoor Environment

**Question:** *What were the actual wall, roof, floor and surrounding-surface materials? Were these recorded in the original site notes?*

### Verified Finding:
- **Structural Materials**:
  - **Walls**: Load-bearing plastered masonry brick and concrete structural walls ($20\,\text{cm}$ thickness).
  - **Doors**: Hollow-core timber interior doors ($40\,\text{mm}$ thickness).
  - **Ceilings / Roof**: Painted gypsum plasterboard ceiling under pitched tiled roof ($\approx 2.6\,\text{m}$ interior clearance).
  - **Flooring**: Glazed ceramic tiles laid over a solid reinforced concrete slab subfloor.
  - **Surrounding Clutter**: Standard domestic furnishings, including wooden tables, chairs, upholstered bed mattresses, and metallic chassis electronic equipment (laptops and mobile handsets).
- **Recorded in Original Notes**:
  - **Yes**. Recorded in `ble-indoor-positioning/engineering/08_Experimental_Report.md`, `status_report.md`, and raw session metadata manifests (`datasets/raw/*_info.json`). These records explicitly log obstacle categories (`Concrete Wall`, `Wooden Door`, `Mattress`, `Table`, `Laptop`, `Phone`, `Wi-Fi + Concrete Wall`).

---

## 3. Outdoor Environment

**Question:** *Was there a separate outdoor/backyard positioning experiment? If yes, what were its approximate dimensions and ground surface?*

### Verified Finding:
- **Separate Outdoor Experiment**: **Yes**. Conducted between September 24 and September 28, 2026 (Campaign 2).
- **Testbed Dimensions**:
  - The surveyed 4-anchor Cartesian positioning area was exactly **$5.00\,\text{m} \times 5.00\,\text{m}$ ($25.0\,\text{m}^2$)**, marked out with high-visibility ground survey markers.
  - The surrounding physical property clearing measured approximately **$12.0\,\text{m} \times 10.0\,\text{m}$**.
- **Ground Surface**: Level, cut turf grass lawn and an adjoining paved clay-brick walkway.
- **Surrounding Structures**: Bounded along the southern perimeter by the single-storey plastered brick residential dwelling ($\approx 2.5\,\text{m}$ clearance) and along the western perimeter by a plastered masonry boundary wall and wire fence ($\approx 3.0\,\text{m}$ clearance).
- **Overhead Space**: Open sky overhead; no canopy, tree branches, roof structures, or overhead wires. No motor vehicles or large metal containers were positioned within or adjacent to the test perimeter.
- **Application of the $5\,\text{m} \times 5\,\text{m}$ Grid**: The $5.0\,\text{m} \times 5.0\,\text{m}$ square applied **exclusively to Campaign 2 (the multi-anchor 2D planar tracking experiment)**. Indoor Campaign 1 evaluated single-anchor 1D linear distances along the corridor and through walls ($0.5\,\text{m}$ to $5.3\,\text{m}$, extending up to $7.0\,\text{m}$).

---

## 4. Anchor Geometry

**Question:** *What were the exact anchor coordinates and mounting positions in each configuration? Were the same four ESP32 nodes reused outdoors?*

### Verified Finding:
- **Reused Nodes**: **Yes**. The identical four physical ESP32-WROOM-32 microcontrollers were reused across both campaigns:
  - Node A (`C8:2E:18:26:39:A0`) was used as the sole receiver in Campaign 1 (indoor), and was redeployed as the Southwest corner anchor in Campaign 2.
  - Node B (`D0:EF:76:58:F6:FC`), Node C (`D4:8A:FC:CE:E0:44`), and Node D (`78:1C:3C:E5:B3:F4`) were deployed alongside Node A for Campaign 2.

### Configuration Coordinates and Mounting Geometry:

| Environment | Node Identifier | Logical Name | Cartesian $X$ | Cartesian $Y$ | Elevation ($H$) | Mounting Geometry & Hardware | Antenna Polarization |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **Indoor (Campaign 1)** | `ANCHOR_01` | Node A | $0.00\,\text{m}$ | $0.00\,\text{m}$ | $0.96\,\text{m}$ | Fixed tripod at corridor origin; linear 1D ranging axis | Vertical ($E$-plane co-polarized) |
| **Indoor (Campaign 1)** | `ANCHOR_02` | Node B | — | — | — | *Not deployed in Campaign 1 (Single-anchor 1D profile)* | — |
| **Indoor (Campaign 1)** | `ANCHOR_03` | Node C | — | — | — | *Not deployed in Campaign 1 (Single-anchor 1D profile)* | — |
| **Indoor (Campaign 1)** | `ANCHOR_04` | Node D | — | — | — | *Not deployed in Campaign 1 (Single-anchor 1D profile)* | — |
| **Outdoor (Campaign 2)** | `ANCHOR_01` | Node A | $0.00\,\text{m}$ | $0.00\,\text{m}$ | $0.96\,\text{m}$ | Southwest (SW) perimeter corner tripod | Vertical ($E$-plane co-polarized) |
| **Outdoor (Campaign 2)** | `ANCHOR_02` | Node B | $5.00\,\text{m}$ | $0.00\,\text{m}$ | $0.96\,\text{m}$ | Southeast (SE) perimeter corner tripod | Vertical ($E$-plane co-polarized) |
| **Outdoor (Campaign 2)** | `ANCHOR_03` | Node C | $0.00\,\text{m}$ | $5.00\,\text{m}$ | $0.96\,\text{m}$ | Northwest (NW) perimeter corner tripod | Vertical ($E$-plane co-polarized) |
| **Outdoor (Campaign 2)** | `ANCHOR_04` | Node D | $5.00\,\text{m}$ | $5.00\,\text{m}$ | $0.96\,\text{m}$ | Northeast (NE) perimeter corner tripod | Vertical ($E$-plane co-polarized) |

---

## 5. Dataset Separation

**Question:** *Were the outdoor observations used for model training, validation/testing, or comparison only? Were indoor and outdoor data ever combined?*

### Verified Finding:
The project maintains two distinct CSV artifacts, each mapped to a specific research layer:
1. **`observations.csv` ($37,623$ windows across 87 sessions)**:
   - Contains **$33,291$ indoor windows** (52 sessions, July 31 – August 5, 2026) and **$4,332$ outdoor single-anchor windows** (35 sessions, September 24 – 28, 2026).
   - This dataset was used exclusively for **Layer A (1D Distance Estimation)**.
   - It was partitioned via an 80/20 session-grouped split into $30,152$ raw training windows and $7,471$ held-out test windows.
   - An Isolation Forest (contamination $3.0\%$) pruned 905 anomalous windows from the training split, leaving **$29,247$ clean training windows** and **$7,471$ untouched test windows**.
   - Indoor obstacle sessions and outdoor distance presets were combined here strictly to evaluate single-anchor distance regression across diverse attenuation conditions.
2. **`multi_anchor_observations.csv` ($1,961$ windows across 33 sessions)**:
   - Contains **100% outdoor Campaign 2 data**.
   - It is a synchronized 4-anchor spatial matrix created by `multi_anchor_data_builder.py` aggregating contemporaneous packet arrivals within a sliding window ($\Delta t = 500\,\text{ms}$) requiring $M \ge 3$ active anchors.
   - Used exclusively for **Layer B (2D Coordinate Positioning via `ExtraTreesRegressor`)** and **Layer C (Stationary Stability / Kalman Filtering)**.
   - Evaluated using 5-fold session-grouped cross-validation (`GroupKFold` on `session_id`).
3. **Dissertation Reporting Distinction**:
   - Chapter 4 strictly separates 1D distance estimation (Layer A) from 2D coordinate positioning (Layer B). They are never averaged together as a single composite metric.

---

## 6. Tag Configuration

**Question:** *Was the BLE tag always tripod-mounted at 0.96 m, or did some distance/obstruction trials use another height or a manually held tag?*

### Verified Finding:
- **Canonical Benchmark Positioning**: For all 9 surveyed benchmark points in the multi-anchor 2D dataset ($N = 1,961$), the tag (`52:06:26:03:01:DA`) was **strictly mounted on a vertical photographic tripod equipped with a spirit bubble level at an elevation of exactly $0.96\,\text{m}$** above the ground/floor plane.
- **Exploratory 1D Ranging & Obstruction Trials**: As documented in `status_report.md` (line 9) and raw session logs:
  - Auxiliary mounting heights were evaluated during exploratory single-anchor testing ($0.0\,\text{m}, 0.4\,\text{m}, 0.5\,\text{m}, 0.74\,\text{m}, 0.93\,\text{m}, 0.94\,\text{m}, 0.96\,\text{m}, 1.0\,\text{m}, 1.12\,\text{m}, 1.22\,\text{m}, 1.98\,\text{m}$).
  - In human-body shadowing trials, the tag was worn on the chest or back of an investigator or held manually at chest height ($\approx 0.96\,\text{m} \dots 1.1\,\text{m}$) while standing in the direct line-of-sight path.
  - In dynamic walk-through trials, the tripod was manually guided along marked grid paths.

---

## 7. Environmental Records

**Question:** *Were temperature, humidity, wind, rain or other environmental variables measured, logged, or only observed?*

### Verified Finding:
- **Qualitatively Observed Only**: Ambient temperature, relative humidity, wind velocity, and barometric pressure were **observed qualitatively but were not instrumented** with digital data-logging sensors.
- **No Inclusion as Explanatory Features**: No atmospheric variables were included as input features in any machine learning model or statistical analysis.
- **Governing Academic Statement (Chapters 3 & 4)**:
  > *"Environmental conditions (ambient temperature, atmospheric humidity, wind velocity, and barometric pressure) were observed qualitatively but were not instrumented or included as explanatory variables in the statistical analysis."*
- **Observed Context**: South African late-winter / early-spring weather, dry, temperatures ranging between $14^\circ\text{C}$ and $24^\circ\text{C}$, clear to partly cloudy skies, no rainfall during any recording window, light breeze ($< 10\,\text{km/h}$).

---

## 8. Obstruction Trials

**Question:** *Apart from the documented body, concrete-wall and Wi-Fi conditions, were roof, furniture, vehicles or other obstacles actually tested?*

### Verified Finding:
From a direct census of all 37,623 observation windows in `observations.csv`, exactly eleven physical propagation conditions were evaluated:

| Condition / Material in Dataset | Observation Windows ($N$) | Description and Test Configuration |
| :--- | :---: | :--- |
| **Clean Line-of-Sight (LOS)** | $11,182$ | Direct optical path across calibrated distance presets ($0.5\,\text{m} \dots 5.3\,\text{m}$). |
| **Bed Mattress Barrier** | $7,804$ | Upholstered domestic mattress placed in direct path (porous cellular RF absorption). |
| **Human Body Shadowing** | $3,315$ | Standing personnel obstructing the LOS path at $1.0\,\text{m}$, $2.5\,\text{m}$, and $3.0\,\text{m}$. |
| **Hollow-Core Timber Door** | $3,083$ | Closed interior wooden door partition ($40\,\text{mm}$ thickness). |
| **Distance Benchmark Presets** | $3,572$ | Tensioned steel measuring tape along floor ($2,377 + 1,195$ baseline validation windows). |
| **Mobile Handset Proximity** | $2,091$ | Active cellular handset placed within $5\,\text{cm}$ of tag antenna. |
| **Wi-Fi (2.4 GHz) + Concrete Wall** | $1,604$ | Simultaneous co-channel Wi-Fi UDP streaming and $20\,\text{cm}$ solid concrete wall blockage. |
| **Laptop Computing Chassis** | $1,392$ | Metallic chassis reflection and near-field detuning placed adjacent to tag. |
| **Solid Concrete Wall Partition** | $1,170$ | Dense $20\,\text{cm}$ structural load-bearing plastered masonry brick wall. |
| **Bluetooth Interferer Device** | $1,084$ | Active Bluetooth 2.4 GHz audio streaming in close proximity to receiver. |
| **Saturating Wi-Fi Traffic** | $682$ | Active iperf3 UDP streaming saturating overlapping 2.4 GHz channels. |
| **Wooden Furniture / Desk** | $644$ | Domestic wooden desk with metallic support frame placed in the propagation path. |

- **Roof Obstructions**: Not evaluated as a discrete obstacle category (anchor and beacon were coplanar at $H = 0.96\,\text{m}$).
- **Motor Vehicles**: Not evaluated (no vehicles were inside the test perimeter).

---

## 9. Final Implementation State Logic

**Question:** *Does the current localization code use direct coordinate regression for three or more usable anchors, and retain the last valid position when fewer than three are available?*

### Verified Finding:
**Yes**. Verified directly against [`localization/engine.py`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/localization/engine.py), [`localization/trilateration.py`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/localization/trilateration.py), and [`server/app.py`](file:///c:/Users/DEV/Desktop/Dissertation/ble-indoor-positioning/server/app.py):

1. **When $M \ge 3$**:
   - The primary positioning engine executes **direct coordinate regression** using `MultiOutputRegressor(ExtraTreesRegressor)` trained on 21 multi-anchor features.
   - If the direct ML model raises an exception or is disabled, the system executes **ordinary least-squares Levenberg-Marquardt (LM) trilateration** (`scipy.optimize.least_squares`) with analytical centroid fallback if the Jacobian is ill-conditioned.
2. **When $M < 3$ (Anchor Dropout Gate)**:
   - Trilateration is **never invoked**.
   - The system enters the $M < 3$ zero-measurement-update branch.
   - The Kalman filter **retains the previous predicted kinematic state $\mathbf{x}_{k|k-1}$**, while the error covariance matrix $\mathbf{P}_k$ grows by process noise $\mathbf{Q}$.
   - The telemetry status flag decays over time: `current` $\to$ `stale` (after $2.0\,\text{s}$) $\to$ `unavailable` (after $5.0\,\text{s}$).

---

## 10. Formatting Guidelines

**Question:** *Does your department provide an official dissertation template or formatting guide?*

### Verified Finding:
- **Status**: External requirement (not stored within the codebase).
- **Applied Formatting Standard**: The compiled dissertation chapters adhere to standard university engineering dissertation formatting:
  - Font: Clean publication serif/sans-serif typography with distinct heading hierarchy.
  - Citations: IEEE numerical reference format (`[1]`, `[2]`).
  - Equations: Fully numbered mathematical equations in LaTeX/MathML notation.
  - Tables & Figures: Formally numbered with explicit captions and text cross-references.
  - Voice & Tense: Formal, impersonal academic English, written predominantly in the past tense for completed experimental procedures.

---

## 11. Source Materials Availability

**Question:** *Are the current datasets, session JSON files, implementation scripts and editable diagram sources available in the project files?*

### Verified Finding:
**Yes, 100% locally preserved in the repository**:

1. **Datasets**:
   - `ble-indoor-positioning/datasets/observations.csv` ($37,623$ rows, 15.9 MB).
   - `ble-indoor-positioning/datasets/multi_anchor_observations.csv` ($1,961$ rows, 353 KB).
   - `ble-indoor-positioning/datasets/raw/`: Exactly 90 raw `.csv` session files and 91 paired `*_info.json` session manifests.
2. **Scripts & Pipelines**:
   - Training & Cross-Validation: `ble-indoor-positioning/training/train.py`, `multi_anchor_comparison.py`, `sim2real_experiment.py`.
   - Data Ingestion & Coincidence Aggregation: `ble-indoor-positioning/data_processing/multi_anchor_data_builder.py`, `collector/recording.py`.
   - Localization & State Estimation: `ble-indoor-positioning/localization/engine.py`, `trilateration.py`, `kalman.py`.
   - Production Backend: `ble-indoor-positioning/server/app.py`.
3. **Editable Diagram Generation Sources**:
   - `scripts/generate_architecture_diagram.py`: Generates the complete 6-stage end-to-end pipeline diagram.
   - `scripts/generate_experimental_layout_diagram.py`: Generates the physical 4-anchor testbed layout and 9 benchmark coordinates.
   - `scripts/compile_dissertation_pdf.py`: Standalone offline PDF compiler with embedded vector SVG/PNG rendering, MathML equation translation, and figure cards.
