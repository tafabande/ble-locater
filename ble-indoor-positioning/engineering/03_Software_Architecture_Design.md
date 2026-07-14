# Volume 3: Software Architecture Design

# SOFTWARE ARCHITECTURE DESIGN (SAD)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** SAD-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Purpose
Defines the software architecture, modules, interfaces, and implementation strategy for the Indoor BLE Positioning System.

---

# 2. Architecture Overview
Layers:
1. Firmware (ESP32 BLE Scanner)
2. Data Collection
3. Feature Engineering
4. Machine Learning
5. Localization
6. Server/API
7. Dashboard

---

# 3. Repository Structure
```text
ble-indoor-positioning/
 ├── firmware/
 ├── collector/
 ├── feature_engineering/
 ├── training/
 ├── models/
 ├── localization/
 ├── server/
 ├── dashboard/
 ├── tests/
 └── docs/
```

---

# 4. Firmware Module
Responsibilities:
- Scan BLE advertisements
- Filter target MAC
- Build 1-second observation windows
- Compute RSSI statistics
- Send JSON to server

---

# 5. Collector Module
Receives serial/Wi-Fi messages and stores validated observations into CSV/Parquet.

---

# 6. Feature Engineering
Computes:
- RSSI mean
- min/max
- variance
- std deviation
- range
- delta
- packet rate
- advertising interval

---

# 7. Machine Learning
Baseline: RandomForestRegressor.
Inputs: engineered features.
Output: predicted distance (m).
Metrics: MAE, RMSE, R².

---

# 8. Localization
Uses predicted distances and anchor coordinates.
Algorithm:
- Weighted Trilateration
- Least Squares (future)

---

# 9. Tracking
Kalman Filter smooths estimated positions and velocities.

---

# 10. Server
FastAPI service:
- `POST /observations`
- `GET /position`
- `GET /anchors`
- `GET /health`

---

# 11. Dashboard
Displays:
- Anchor map
- Tag position
- RSSI charts
- Distance history
- System status

---

# 12. JSON Observation Schema
```json
{
  "anchor_id": "string",
  "timestamp": 1234567890,
  "device_mac": "string",
  "packet_count": 0,
  "scan_duration_ms": 0,
  "rssi_mean": 0.0,
  "rssi_std": 0.0,
  "rssi_variance": 0.0,
  "rssi_min": 0,
  "rssi_max": 0,
  "rssi_range": 0,
  "advertising_interval_ms": 0
}
```

---

# 13. Error Handling
Validate input, log errors, retry communication, health monitoring.

---

# 14. Logging
Structured timestamped logs for firmware, server, and ML inference.

---

# 15. Testing
Unit, integration, calibration, localization, and end-to-end tests.

---

# 16. Coding Standards
PEP8 for Python, modular ESP-IDF components, documented APIs, Git feature branches.

---

# 17. Future Extensions
Multi-tag tracking, 3D localization, fingerprinting, model comparison, cloud sync.
