# Volume 4: Hardware Design Specification

# HARDWARE DESIGN SPECIFICATION (HDS)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** HDS-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Purpose
Define the physical hardware architecture, installation, calibration, and deployment requirements.

---

# 2. System Hardware
- **BLE Tag** (target)
- **ESP32 Anchor Nodes** (minimum 3)
- **Localization Server** (host PC)
- **Wi-Fi Router** (network infrastructure)
- **Power Supplies**

---

# 3. Hardware Architecture
The BLE Tag broadcasts advertisements. ESP32 anchors receive packets and send observation summaries to the server over Serial (development) or Wi-Fi (deployment).

---

# 4. Bill of Materials
- 3x ESP32 Dev Boards
- 1x BLE Beacon/Tag
- USB Cables
- Wi-Fi Router
- Laptop/PC
- Measuring Tape
- Anchor Mounts/Tripods

---

# 5. ESP32 Anchor Specification
Responsibilities:
- BLE Scan
- Observation Window Generation
- Feature Calculation
- JSON Transmission
- Health Monitoring

---

# 6. Anchor Placement
Recommended triangular layout. Mount at consistent height (1.2–1.5 m). Avoid metal surfaces. Record exact (x, y) coordinates.

---

# 7. Calibration Procedure
Measure tag positions at fixed distances (0.25–5 m). Collect multiple observation windows in open space and under interference.

---

# 8. Communication
- **Development**: USB Serial.
- **Deployment**: Wi-Fi JSON messages via UDP/WebSocket/HTTP.

---

# 9. Power Requirements
Stable 5V USB supply during development. Consider UPS/power bank for field tests.

---

# 10. Environmental Considerations
Document walls, furniture, people, Wi-Fi congestion, and BLE interference sources during experiments.

---

# 11. Verification
Verify scan rate, packet reception, communication reliability, and anchor coordinate accuracy before ML testing.

---

# 12. Future Expansion
Support PoE, battery operation, additional anchors, multi-floor deployment, external antennas where applicable.
