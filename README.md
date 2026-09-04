# 📡 Real-Time Indoor BLE Positioning & Spatial Telemetry System

A production-grade, zero-dependency indoor positioning platform combining **AI-driven distance estimation**, **mathematical multilateration**, and a **standalone React 19 + Tailwind v4 Operations Dashboard**.

---

## 🏗️ Architecture Overview

The platform integrates hardware BLE packet collection, high-frequency feature engineering, Machine Learning distance estimation, multilateration solving, and a real-time visual operations dashboard:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PHYSICAL FACILITY                               │
│                                                                             │
│     [ESP32 Anchor A]            [ESP32 Anchor B]         [ESP32 Anchor C]   │
│           │                           │                         │           │
│           └───────────────────┬───────┴─────────────────────────┘           │
│                               ▼                                             │
│                       BLE Advertising Packets                               │
│                     (RSSI, Frequency, Channel)                              │
│                               │                                             │
│                               ▼                                             │
│                   [BLE Beacon Tag (Asset/User)]                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FASTAPI & WEBSOCKET POSITIONING ENGINE                      │
│                                                                             │
│  1. 60-Feature Engineering Pipeline                                         │
│     ├── Physical & Statistical: Mean, Median, Min, Max, IQR, Skew, Kurtosis │
│     ├── Temporal & Dynamic: Slope, Autocorrelation, EMA drift               │
│     ├── BLE Multipath Domain: Power density histograms, Packet loss         │
│     └── Cross-Window: Velocity, Acceleration, Rolling SNR                   │
│                                                                             │
│  2. Super Learner Tournament (CatBoost / ExtraTrees / XGBoost)              │
│     └── Converts 60 BLE features -> Physical Distances (MAE: 0.218m)        │
│                                                                             │
│  3. Multilateration & Filtering Engine                                      │
│     ├── Levenberg-Marquardt Least-Squares Trilateration Solver              │
│     ├── 2D Adaptive Kalman Filter (Noise & Inertial Smoothing)             │
│     └── Online Recursive Distance Calibration                               │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ WebSocket / REST Telemetry
┌─────────────────────────────────────────────────────────────────────────────┐
│               REACT 19 + VITE 8 + TAILWIND v4 DASHBOARD                     │
│                                                                             │
│  ├── Live Monitor View: Real-time 2D/3D tracking, trails & geofencing       │
│  ├── Schematic Studio: CAD floor designer with metric coordinate mapping    │
│  ├── Topology Manager: 4-corner, 3-node triangulation, or 1-node proximity  │
│  ├── System Readiness Engine: Geometric dilution of precision (GDOP) check  │
│  └── Operations Console: Unified daemon lifecycle manager (control.py)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Architectural Pillars

### 1. Zero-Default Clean Slate Initialization
- **Clean State**: `/api/schematic` returns empty collections (`anchors: []`, `rooms: []`, `walls: []`) when unconfigured.
- **No Ghost Entities**: The dashboard does not render mock tags, wandering entities, or simulated packets before layout creation.
- **Setup Required Screen**: If unconfigured, the live dashboard renders a prominent setup hero card directing the operator to the Room Designer.

### 2. Strict Room-Anchor Invariant ($N_{\text{anchors}} = N_{\text{nodeCount}}$)
Anchor generation is strictly an **explicit event transition** (never a reactive side-effect of rendering):
$$\forall r \in \text{Rooms}, \quad |\{a \in \text{Anchors} \mid a.\text{roomId} = r.\text{id}\}| = r.\text{nodeCount}$$
$$\forall a \in \text{Anchors}, \quad \exists r \in \text{Rooms} \text{ such that } r.\text{id} = a.\text{roomId}$$
- **4-node mode**: Exactly 4 anchors automatically pinned to `TL`, `TR`, `BL`, `BR` corners.
- **3-node mode**: Exactly 3 anchors (Apex + 2 Base nodes) customized by the operator via design angle ($30^\circ \dots 120^\circ$).
- **1-node mode**: Exactly 1 anchor positioned for cell proximity tracking.
- **Room Deletion**: Atomically deletes all room anchors; zero orphaned anchors remain.

### 3. Comprehensive Facility Readiness Validation
Instead of checking raw anchor counts, the platform evaluates the mathematical solvability of the layout:
```typescript
export interface FacilityReadiness {
  hasRooms: boolean
  hasAnchors: boolean
  layoutValid: boolean
  positioningReady: boolean
  status: 'no_rooms' | 'no_anchors' | 'invalid_geometry' | 'ready'
  issues: string[]
  roomCount: number
  anchorCount: number
}
```
- `no_rooms`: Directs operator to create room boundaries.
- `no_anchors`: Prompts operator to plant receiver anchors.
- `invalid_geometry`: Flags degenerate conditions (e.g. collinear nodes, pairwise separation $<0.5\text{m}$, or $<3$ nodes).
- `ready`: Activates live multilateration and real-time telemetry.

### 4. Deterministic Coordinate Pipeline & Benchmark Verification
Coordinates follow an explicit, reversible mathematical mapping:
$$x_{\text{meters}} = \frac{x_{\%}}{100} \cdot W_{\text{meters}}, \quad y_{\text{meters}} = \left(1 - \frac{y_{\%}}{100}\right) \cdot H_{\text{meters}}$$

Verified against the **Analytical Ground-Truth Benchmark**:
- Room: $10\text{m} \times 10\text{m}$, Bottom-Left origin $(0, 0)\text{m}$
- Anchors: $A(0, 0)\text{m}$, $B(10, 0)\text{m}$, $C(0, 10)\text{m}$
- Tag: $T(3.0, 4.0)\text{m}$
- Analytical distances: $d_A = 5.0\text{m}$, $d_B = \sqrt{65}\text{m} \approx 8.062\text{m}$, $d_C = \sqrt{45}\text{m} \approx 6.708\text{m}$
- **Solved Position**: $(3.000, 4.000)\text{m}$ (Sub-millimeter accuracy verified on both frontend and backend).
- **Inverted Canvas**: $\{ x: 30.0\%, y: 60.0\% \}$ (Exact visual alignment).

---

## ⚡ Quick Start Guide

### Prerequisites
- **Node.js**: 18+ (Dashboard runtime)
- **Python**: 3.10+ (Positioning engine & ML pipeline)

### Option A: One-Click Launch (Desktop Operations Console)
Run the desktop launch script to start the backend engine and dashboard:
```cmd
launch.bat
```
Or launch the terminal console:
```cmd
control.bat
```

### Option B: Manual Service Startup

#### 1. Backend Positioning Engine
```bash
cd ble-indoor-positioning
# Activate virtual environment
.venv\Scripts\activate
# Start FastAPI / WebSocket server on port 8000
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Operations Dashboard
```bash
# In workspace root
npm install
npm run dev
# Dashboard launches at http://127.0.0.1:3000
```

---

## 🧪 Test Suites & Scientific Verification Protocol

The platform includes a dedicated dissertation-grade flight check protocol documented in detail in [DISSERTATION_VALIDATION_PROTOCOL.md](file:///c:/Users/User/Desktop/Dissertation/DISSERTATION_VALIDATION_PROTOCOL.md), covering the complete 20-item validation matrix.

### Frontend Verification (Vitest)
Executes 39 tests covering coordinate conversions, 6-point physical grid mapping, geometric conditioning, topological invariants, noise perturbation sensitivity, and multilateration solving:
```bash
npm test -- --run
```

### Backend Verification (pytest)
Executes 37 tests covering FastAPI REST endpoints, WebSocket broadcasts, ML inference, and analytical ground-truth trilateration:
```bash
.\ble-indoor-positioning\.venv\Scripts\python.exe -m pytest
```

### Production Build Verification
Verifies zero TypeScript errors and compiles production assets:
```bash
npx tsc --noEmit
npm run build
```

---

## 📁 Repository Structure

```text
Dissertation/
├── ble-indoor-positioning/      # Python Backend Engine & ML Pipeline
│   ├── server/                  # FastAPI REST and WebSocket server (app.py)
│   ├── localization/            # TrilaterationEngine, KalmanFilter2D, GDOP solver
│   ├── feature_engineering/     # 60-feature extractor & dataset quality auditor
│   ├── training/                # Super Learner Tournament & CV training pipeline
│   ├── collector/               # Serial ESP32 BLE receiver packet collector
│   ├── tests/                   # Python pytest suite (37 tests)
│   └── pipeline.py              # ML pipeline entry point with streaming telemetry
├── src/                         # Frontend React 19 Application
│   ├── components/
│   │   ├── monitor/             # SpatialView (2D/3D), FloorPlan, TagDetail
│   │   ├── admin/               # FloorEditor (Schematic Studio), RoomDesignWizard
│   │   ├── control/             # Service daemon lifecycle control panel
│   │   └── reports/             # Positioning analytics, CSV export, telemetry charts
│   ├── lib/
│   │   ├── geometry.ts          # Metric transforms, Heron's formula, readiness evaluation
│   │   ├── simulation.ts        # Physics log-distance simulation engine
│   │   ├── datasource.ts        # Real-time WebSocket / REST live telemetry adapter
│   │   └── rbac.ts              # Role-based access control (Admin, Operator, Viewer)
│   └── __tests__/               # Vitest suites (geometry, pipeline, simulation, components)
├── control.py                   # Operations Console Desktop Host
├── launch.bat                   # Single-click desktop launcher
├── index.html                   # Standalone HTML5 shell
├── package.json                 # React dependencies and scripts
└── vite.config.ts               # Vite 8 + Tailwind CSS v4 configuration
```

---

## 📄 License
Academic Dissertation Research Project — Licensed under the MIT License.
