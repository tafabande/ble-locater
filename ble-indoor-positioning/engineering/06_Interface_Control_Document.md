# Volume 6: Interface Control Document

# INTERFACE CONTROL DOCUMENT (ICD)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** ICD-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Purpose
Defines all interfaces between firmware, server, ML engine, localization engine, dashboard, and storage.

---

# 2. Interface Overview
Interfaces:
- ESP32 ↔ Collector
- ESP32 ↔ Server
- Server ↔ ML Engine
- ML Engine ↔ Localization Engine
- Server ↔ Dashboard

---

# 3. Serial Interface
115200 baud, UTF-8, newline-delimited JSON during development.

---

# 4. Wi-Fi Interface
HTTP POST or WebSocket carrying one observation window per message.

---

# 5. Observation JSON
```json
{
  "anchor_id": "A1",
  "timestamp": 1234567890,
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "packet_count": 34,
  "scan_duration_ms": 1000,
  "rssi_mean": -58.2,
  "rssi_std": 2.1,
  "rssi_variance": 4.4,
  "rssi_min": -63,
  "rssi_max": -54,
  "rssi_range": 9,
  "rssi_delta_mean": 0.4,
  "advertising_interval_ms": 100
}
```

---

# 6. Prediction Interface
Input: engineered feature vector. Output: `estimated_distance_m`.

---

# 7. Localization Interface
Input: anchor coordinates + predicted distances. Output: `x`, `y`, `confidence`.

---

# 8. REST API
- `POST /observations`
- `GET /position`
- `GET /anchors`
- `GET /health`
- `POST /retrain` (future)

---

# 9. Error Codes
- `400` invalid payload
- `404` unknown anchor
- `422` feature error
- `500` inference failure
- `503` service unavailable

---

# 10. Timing
Observation window = 1 s. Target end-to-end latency < 100 ms after receipt.

---

# 11. Versioning
Include `interface_version` in payloads. Maintain backward compatibility where possible.

---

# 12. Security
Validate payloads, authenticate anchors in deployment, and log all rejected messages.

---

# 13. Verification
Use JSON schema validation, API tests, integration tests, and packet replay.
