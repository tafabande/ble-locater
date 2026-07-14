# Volume 7: Testing and Validation Plan

# TESTING AND VALIDATION PLAN (TVP)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** TVP-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Purpose
Define verification and validation activities for hardware, firmware, software, machine learning, and localization.

---

# 2. Test Levels
- **Unit Testing**: Isolated verification of individual code functions.
- **Integration Testing**: Testing interfaces between modules (e.g., Firmware ↔ Server).
- **System Testing**: End-to-end operational test of the full hardware/software stack.
- **Acceptance Testing**: Validating system performance against user requirements and success criteria.

---

# 3. Hardware Tests
Verify BLE scanning, Wi-Fi connectivity, power stability, and anchor coordinate accuracy.

---

# 4. Firmware Tests
Validate MAC filtering, observation window generation, RSSI statistics calculation, JSON formatting, and communication recovery after connection loss.

---

# 5. Collector Tests
Verify serial parsing, file creation, invalid packet handling, and timestamp integrity.

---

# 6. ML Tests
Validate dataset integrity, preprocessing steps, model training runtime, inference latency, and MAE/RMSE/R² evaluation metrics.

---

# 7. Localization Tests
Check distance prediction accuracy, trilateration correctness (using synthetic input coordinates), and Kalman filter stability.

---

# 8. Experimental Validation
Perform trials at known distances (0.25–5 m) in open space, with obstacles, human body occlusion, wireless interference, and motion.

---

# 9. Performance Metrics
- **BLE Packet Reception Rate**
- **Mean Absolute Error (MAE)** of distance estimates
- **Root Mean Square Error (RMSE)** of distance estimates
- **Median Localization Error**
- **Update Rate** (≥1 Hz)
- **End-to-End Latency** (<100 ms)

---

# 10. Stress Testing
Continuous operation for ≥8 hours, packet bursts, temporary Wi-Fi loss, and recovery upon anchor restart.

---

# 11. Acceptance Criteria
Each subsystem must meet documented requirements before integration. End-to-end localization must outperform the baseline RSSI log-distance path-loss model under defined test conditions.

---

# 12. Reporting
Record environment parameters, system configuration, dataset version, software version, results, observations, and corrective actions for every test.
