# 📖 Indoor Positioning System (RTLS) Operator & User Guide

A comprehensive guide for setting up, calibrating, operating, and troubleshooting the **Real-Time Indoor BLE Positioning & Spatial Telemetry System**.

The application architecture is refactored into a **decoupled ecosystem of specialized tools**, each with a single responsibility:

1. **📍 Live Tracking Dashboard** (Web / React 19 + Vite 8) — High-performance 2D & 3D indoor tracking experience.
2. **🛠️ System Administrator & Telemetry Console** (Python GUI) — Infrastructure monitoring, ESP32 node health, dropped packets, connection state, and diagnostics.
3. **📡 Sensor Data Collector** (Python GUI) — Ground-truth survey recording, environmental tagging, and raw dataset generator.
4. **🧠 AI Model Studio & Trainer** (Python GUI) — Super Learner ML tournament, feature engineering, MAE/RMSE metrics, and evaluation plots.
5. **⚡ Application Launcher** (Python GUI) — Unified control room providing single-click entry to all tools.

---

## 📑 Table of Contents

1. [🚀 Quick Start & Application Launch Options](#-quick-start--application-launch-options)
2. [📍 Live Tracking Dashboard](#-live-tracking-dashboard)
3. [🛠️ System Administrator & Telemetry Console](#-system-administrator--telemetry-console)
4. [📡 Sensor Data Collector](#-sensor-data-collector)
5. [🧠 AI Model Studio & Trainer](#-ai-model-studio--trainer)
6. [📻 Hardware & Anchor Mounting Best Practices](#-📻-hardware--anchor-mounting-best-practices)
7. [🔍 Troubleshooting & Diagnostics](#-🔍-troubleshooting--diagnostics)

---

## 🚀 Quick Start & Application Launch Options

### Option 1: Application Launcher & Control Centre (Recommended)
Double-click `control.bat` or run:
```cmd
python control.py
```
This opens the lightweight **Application Launcher**, where you can launch any of the specialized tools independently or click **"Start Full Stack"** to launch all background microservices.

### Option 2: Launch Applications Directly

| Application | Launch Command | Purpose |
|---|---|---|
| **📍 Live Tracking Dashboard** | `launch.bat` or `npm run dev` (`http://127.0.0.1:3000`) | Live indoor tracking map (2D/3D), tag coordinates, and solver telemetry |
| **🛠️ System Administrator** | `python admin_gui.py` | Node health table, dropped packets, connection stats, and event logs |
| **📡 Data Collector** | `python collector_gui.py` | Ground-truth survey collection, live RSSI meter, and raw CSV persistence |
| **🧠 Model Trainer** | `python trainer_gui.py` | Super Learner ML tournament, dataset inspection, and accuracy evaluation |

---

## 🎮 Interactive Quest Guide (How to Play)

Every tab in the **Facility Setup** page features an integrated, game-like walkthrough that explains each tool and guides you through setting up your facility.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎮 CASUAL SETUP QUEST                                 Level 1 • ⭐ 200/500 XP│
├─────────────────────────────────────────────────────────────────────────────┤
│ 🏆 Mission 2: Deploy The Beacons                     [RECOMMENDED]          │
│ 📡 Tracking Boxes Placement (Anchor Layout)                                 │
│                                                                             │
│ 💡 What this option does:                                                   │
│    Positions your BLE receiver anchor nodes automatically around your space.│
│    Offers 4-Corner coverage, 3-Node perimeter, or Single Center Node.       │
│                                                                             │
│ 🤔 Should you use it?                                                       │
│    ⭐ 4-Corner Coverage is strongly recommended for 2D positioning.          │
│    ✔️ Use if: You have 3 or 4 receiver boxes for full (X,Y) coordinates.    │
│    ❌ Skip if: You only possess 1 box (choose Single Center Node instead).  │
│                                                                             │
│ 🎯 Strategy Tip:                                                            │
│    Mount hardware boxes high up on walls (≥2m) with clear line-of-sight.    │
├─────────────────────────────────────────────────────────────────────────────┤
│ [← Previous]              ● ● ○ ○ ○                 [Next Mission →]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Launching the Walkthrough
- Click the prominent **`🎮 Casual Quest Guide`** or **`🎮 Engineer Quest Guide`** button in the top command bar of the Setup page.
- You can also click **`🎮 Quest Guide`** right inside the Casual Setup header.

### Quest Mechanics
1. **Level & XP Progression**: Advance through missions to level up and earn up to **500 XP**.
2. **Pulsing Spotlight Rings**: The guide automatically scrolls to each active tool and highlights it with an animated glowing neon ring (`.tour-target-highlight`).
3. **Structured Guidance**:
   - **💡 What this option does**: Plain-English explanation.
   - **🤔 Should you use it?**: Direct verdict (`MUST-HAVE`, `RECOMMENDED`, `OPTIONAL`, `ADVANCED`) with *Use if...* and *Skip if...* rules.
   - **🎯 Strategy Tip**: Pro engineering heuristics.
4. **Controls**:
   - `[← Previous]` and `[Next Mission →]`
   - Step dots to jump directly to any mission.
   - Minimize button (`_`) collapses the guide into a floating mini HUD pill.
   - Complete all quests to unlock the **Master Facility Architect** achievement badge!

---

## 🏠 Casual Setup Mode (For Non-Engineers)

Designed specifically for non-technical users, operators, and rapid deployments. It eliminates all coordinate geometry, logarithmic path loss exponents ($n$), and raw decibel calculations.

### Step 1: Choose Your Space
Select one of the ready-made visual space presets or input custom meters:
- 🏠 **Single Studio / Office** ($5\text{m} \times 5\text{m}$): Ideal for conference rooms, retail booths, or private suites.
- 🏢 **2-Room Office Suite** ($10\text{m} \times 10\text{m}$): Open workspace plus private conference room divided by a wall.
- 🏬 **4-Room Smart Complex** ($10\text{m} \times 10\text{m}$): Executive office, boardroom, operations room, and reception.
- 🏭 **Open Warehouse / Hall** ($20\text{m} \times 15\text{m}$): High ceilings, aisles, or open showrooms.
- ✏️ **Custom Dimensions**: Type in exact Width and Length in meters.

### Step 2: Tracking Boxes Placement (Anchors)
Choose where your hardware receiver boxes are mounted:
- ⭐ **4-Corner Coverage (Recommended)**: Places 1 anchor in each of the four corners. Best 2D multilateration accuracy with minimal dilution of precision.
- 🔺 **3-Node Triangular Perimeter**: Places 3 anchors in a triangular arrangement along walls. Great for smaller spaces or cost-conscious setups.
- 📍 **Single Center Node**: Places 1 anchor in the room center for room entry/exit presence detection.

### Step 3: Space Environment Profile
Select the room construction type to automatically tune wireless signal penetration:
- 🛋️ **Open Space**: Living rooms, clear hallways, minimal partitions (Path loss exponent $n \approx 2.0$).
- 🚪 **Standard Office**: Drywall partitions, wooden doors, cubicles ($n \approx 2.8$).
- 🧱 **Dense Space**: Concrete walls, metal shelving, heavy inventory ($n \approx 3.5$).

### Step 4: Interactive Room Preview & Test Tag Sandbox
- The live preview displays the room outline, partition walls, and anchor coverage halos.
- **Drag or Click the Test Badge (🏷️)**: Move the test badge across the room in real time to observe live distance calculations to each anchor and verify corner coverage before drilling mounting holes.

### Step 5: Confirm & Activate
- Click **"Confirm & Activate Space"** to commit the layout into local storage and sync with the backend RTLS engine.
- An **"Open Live Monitor →"** button immediately appears to view live tracked tags!

---

## 🛠️ Engineer Studio (Advanced Facilities)

For researchers, facility engineers, and administrators requiring millimeter-level precision and scientific telemetry.

### 1. CAD Floor Plan Designer (`FloorEditor`)
- **Vector Drafting**: Draw arbitrary polygon walls with custom thickness.
- **RF Loss Assignment**: Assign custom attenuation per wall material (e.g. Drywall = $-3.0\text{dB}$, Glass = $-2.0\text{dB}$, Concrete = $-12.0\text{dB}$).
- **Anchor Snapping**: Drag and position anchors to precise coordinates with grid snapping (`G` key).
- **Import/Export**: Load and save CAD floor plans in JSON format.

### 2. Log-Distance ML Calibration (`Calibration`)
- Collects empirical RSSI packets across known distances ($1\text{m}, 2\text{m}, 4\text{m}, 8\text{m}$).
- Runs **Least-Squares Linear Regression** to fit:
  $$\text{RSSI}(d) = -10 \cdot n \cdot \log_{10}(d) + A_0$$
- Computes Root Mean Squared Error (RMSE) and correlation coefficients ($R^2$) to evaluate radio propagation fit.

### 3. Spatial Analytics & Heatmaps (`Analytics`)
- **Packet Loss Analysis**: Real-time packet reception rate per anchor.
- **UART Latency Histograms**: Inspects serial communication jitter.
- **Occupancy & Dwell Heatmaps**: Identifies high-traffic zones and dwell bottlenecks.

### 4. Security Forensics & Geofence Replay (`History`)
- Indexed chronological audit log of all tag movements and boundary breaches.
- **Timeline Scrubber**: Rewind and replay tag movement history second-by-second.
- **Geofence Alarms**: Automated alerts when tags cross restricted perimeter boundaries.

### 5. Hardware Mesh & Daemon Config (`Configuration`)
- Configure WebSocket/REST server endpoints and polling intervals.
- Bind physical ESP32 COM serial ports.
- Adjust 2D Adaptive Kalman Filter process and measurement noise covariances.

---

## 📡 Data Collector Studio (Survey & Ground Truth)

The Data Collector Studio enables systematic site surveys and empirical data collection.

### Survey Planner
- **Uniform Grid Generation**: Generates automated survey calibration points across the floor with configurable spacing (e.g. $1.0\text{m}$, $0.5\text{m}$).
- **Path Optimization (TSP)**: Solves the Traveling Salesperson Problem to calculate the most efficient walk route for the surveyor.
- **Obstacle Line-of-Sight Rays**: Automatically calculates whether physical walls obstruct the direct path between a survey point and an anchor.

### Raw Packet Ingestion & Export
- Live stream of raw BLE advertising packets with MAC addresses, timestamps, RSSI, and frequency channels.
- **CSV Data Sheet Export**: One-click download of calibrated empirical datasets for offline training in Python, Pandas, or CatBoost.

---

## 📻 Hardware & Anchor Mounting Best Practices

To achieve sub-meter indoor positioning accuracy:

```text
       [ESP32 Anchor Node]
       ▲
       │  Mount ≥ 2.0m – 2.5m above the floor
       │  Tilt slightly downward into the tracking zone
       │
       ▼
 ══════════════════════════════════════════ [Floor Level]
```

1. **Mounting Height**:
   - Mount receiver anchors between **2.0m and 2.5m** above the floor.
   - Mounting at eye level causes human bodies to block signals, adding $-5\text{dB}$ to $-15\text{dB}$ of attenuation.
2. **Clear Line of Sight**:
   - Avoid placing anchors behind metal filing cabinets, air ducts, or large concrete pillars.
3. **Corner Placement Geometry**:
   - Place anchors near room corners rather than all in a straight line. Collinear anchors cause mathematical singularities where trilateration cannot distinguish between left and right.
4. **Bluetooth Channel Selection**:
   - BLE advertising uses channels **37 (2402 MHz)**, **38 (2426 MHz)**, and **39 (2480 MHz)**.
   - Ensure high-power 2.4 GHz Wi-Fi access points are set to Wi-Fi channels 1, 6, or 11 to avoid co-channel overlap.

---

## 🔍 Troubleshooting & Diagnostics

### Diagnostic Checklist

| Symptom | Probable Cause | Recommended Fix |
| :--- | :--- | :--- |
| **"No live data source" Screen** | Backend server is not running | Run `launch.bat` or start `python -m uvicorn server.app:app` on port 8000. |
| **"Setup Required" Screen** | No room or anchors configured | Click **"Open Room Designer"** or switch to **Casual Setup** to activate a room layout. |
| **Tag distances jump erratically** | Wrong environment selected | Change Space Environment to **Standard Office** or **Dense Space** in Casual Setup. |
| **Serial port access denied** | Another process is holding COM port | Close other serial monitors (e.g. Arduino IDE, PuTTY) and restart `control.py`. |
| **Anchor packet latency > 200ms** | UART buffer saturation | In **Configuration**, adjust the polling interval to $2000\text{ms} - 2500\text{ms}$. |
| **Browser doesn't show latest updates** | Cached local assets | Hard refresh (`Ctrl + Shift + R`) or clear browser application storage. |

### Running Automated Diagnostic Tests
Execute the comprehensive automated test suite anytime:
```bash
# Run all 60 frontend tests
npm test -- --run

# Run backend Python tests
cd ble-indoor-positioning
.venv\Scripts\python.exe -m pytest
```

---

*Academic Dissertation Research Project — Indoor BLE RTLS Positioning Platform.*
