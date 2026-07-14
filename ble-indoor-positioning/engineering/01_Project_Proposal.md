# Volume 1: Project Proposal

# PROJECT PROPOSAL

## AI-Assisted Indoor Bluetooth Low Energy Positioning System Using ESP32 Anchor Nodes and Machine Learning

**Document ID:** PPS-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Project Type:** Telecommunications Engineering Capstone / Research Project
**Date:** July 2026

---

# Document Revision History

| Version | Date      | Author          | Description              |
| ------- | --------- | --------------- | ------------------------ |
| 1.0     | July 2026 | Bleigh TJ Bande | Initial project proposal |

---

# Table of Contents

1. Executive Summary
2. Background
3. Problem Statement
4. Motivation
5. Project Aim
6. Project Objectives
7. Research Questions
8. Scope
9. Expected Deliverables
10. Technical Approach
11. Project Feasibility
12. Project Risks
13. Project Schedule
14. Required Resources
15. Success Criteria
16. Future Work
17. Conclusion

---

# 1. Executive Summary

Indoor positioning has become an important enabling technology for smart buildings, asset tracking, industrial automation, healthcare, logistics, and robotics. While the Global Positioning System (GPS) provides accurate outdoor positioning, it performs poorly indoors due to signal attenuation caused by building structures.

Bluetooth Low Energy (BLE) has emerged as an attractive alternative because BLE tags are inexpensive, energy efficient, and widely supported. However, indoor BLE positioning remains challenging because Received Signal Strength Indicator (RSSI) measurements fluctuate significantly due to environmental conditions, obstacles, interference, and multipath propagation.

This project proposes an AI-assisted indoor positioning system that combines BLE scanning using ESP32 anchor nodes with Machine Learning-based distance estimation. Instead of relying solely on traditional path-loss equations, the system will learn signal behavior from experimentally collected data and estimate distances using statistical BLE features. The estimated distances will then be combined using trilateration to calculate the location of a BLE tag, while a Kalman filter will reduce trajectory noise.

The project aims to demonstrate that integrating machine learning with classical localization techniques can improve indoor positioning accuracy and robustness.

---

# 2. Background

Indoor positioning systems have gained significant attention due to their applications in:

* Warehouse inventory management
* Hospital equipment tracking
* Smart factories
* University laboratories
* Asset management
* Indoor robotics
* Navigation assistance

BLE technology provides a practical platform for indoor localization because it offers:

* Low power consumption
* Low hardware cost
* Wide availability
* Compatibility with ESP32 hardware

Most RSSI-based localization systems estimate distance using the logarithmic path-loss model. However, this model assumes stable propagation conditions, which rarely exist indoors. Variations in signal strength often lead to inaccurate distance estimates and poor localization performance.

Machine learning provides an opportunity to model these complex relationships directly from observed data, allowing the system to adapt to realistic indoor environments.

---

# 3. Problem Statement

Current RSSI-based indoor positioning systems experience significant localization errors because RSSI measurements are affected by environmental factors that cannot be adequately modeled using simple mathematical equations.

Common sources of error include:

* Multipath reflections
* Human body attenuation
* Wall penetration losses
* Furniture obstruction
* Bluetooth interference
* Wi-Fi interference
* Antenna orientation
* Device hardware variations

As a result, traditional distance estimation methods frequently produce unreliable localization results.

A more intelligent approach is required to improve distance estimation while maintaining low hardware cost.

---

# 4. Motivation

The motivation behind this project is to investigate whether machine learning can improve BLE distance estimation sufficiently to enhance indoor localization accuracy without requiring expensive hardware such as Ultra-Wideband (UWB) systems.

The project also provides an opportunity to integrate knowledge from:

* Telecommunications Engineering
* Wireless Communications
* Signal Processing
* Embedded Systems
* Data Science
* Artificial Intelligence
* Software Engineering

The resulting platform will serve both as an educational research project and as a foundation for future indoor positioning research.

---

# 5. Project Aim

To design, implement, and evaluate an AI-assisted indoor positioning system that estimates the location of BLE tags using ESP32 anchor nodes and machine learning-enhanced distance estimation.

---

# 6. Project Objectives

## Primary Objective

Develop a real-time indoor BLE positioning system capable of accurately estimating the position of a BLE tag using multiple ESP32 anchor nodes.

## Specific Objectives

1. Develop BLE scanning firmware for ESP32 anchor nodes.
2. Design a standardized BLE observation data format.
3. Collect high-quality BLE datasets under controlled indoor conditions.
4. Engineer statistical features from BLE observations.
5. Train regression models to estimate distance.
6. Compare machine learning predictions with conventional path-loss estimates.
7. Implement trilateration using estimated distances.
8. Apply Kalman filtering to reduce localization noise.
9. Develop a real-time visualization dashboard.
10. Evaluate localization performance using experimental measurements.

---

# 7. Research Questions

The project seeks to answer the following questions:

1. Can machine learning improve BLE distance estimation compared to the logarithmic path-loss model?

2. Which BLE-derived statistical features contribute most significantly to distance estimation?

3. What localization accuracy can be achieved using low-cost ESP32 hardware?

4. How does environmental interference affect positioning performance?

5. Can Kalman filtering significantly improve localization stability?

---

# 8. Scope

The project includes:

* BLE advertisement scanning
* ESP32 anchor development
* Data collection
* Machine learning
* Distance estimation
* Trilateration
* Kalman filtering
* Dashboard visualization

The project excludes:

* GPS integration
* Ultra-Wideband positioning
* Computer vision
* Cloud deployment
* Multi-building localization

---

# 9. Expected Deliverables

The project will deliver:

* ESP32 BLE scanner firmware
* Python data collection tools
* BLE calibration dataset
* Feature engineering pipeline
* Machine learning regression model
* Trilateration engine
* Kalman filtering module
* Visualization dashboard
* Technical documentation
* Experimental evaluation report
* Public GitHub repository

---

# 10. Technical Approach

The project follows a modular systems engineering methodology.

### Stage 1 — BLE Data Acquisition

ESP32 anchor nodes scan BLE advertisements and collect signal statistics.

### Stage 2 — Feature Engineering

Raw BLE measurements are transformed into statistical features suitable for machine learning.

### Stage 3 — Machine Learning

A regression model predicts the distance between the BLE tag and each anchor node.

### Stage 4 — Localization

Estimated distances from multiple anchors are combined using trilateration.

### Stage 5 — Filtering

A Kalman filter smooths the estimated trajectory.

### Stage 6 — Visualization

A dashboard presents the estimated tag position and system diagnostics in real time.

---

# 11. Project Feasibility

## Technical Feasibility

The required hardware and software technologies are mature, well documented, and readily available.

## Financial Feasibility

The project uses affordable ESP32 development boards and commercially available BLE tags, minimizing hardware costs.

## Operational Feasibility

The modular architecture allows each subsystem to be developed and validated independently before full integration.

---

# 12. Project Risks

| Risk                       | Impact | Mitigation                                             |
| -------------------------- | ------ | ------------------------------------------------------ |
| RSSI instability           | High   | Feature engineering and machine learning               |
| Hardware failure           | Medium | Spare ESP32 anchors                                    |
| Insufficient training data | High   | Controlled calibration experiments                     |
| Wireless interference      | Medium | Multiple observation windows and statistical filtering |
| Model overfitting          | Medium | Cross-validation and independent testing datasets      |

---

# 13. Project Schedule

| Phase    | Description                     |
| -------- | ------------------------------- |
| Phase 1  | Repository setup and planning   |
| Phase 2  | ESP32 firmware development      |
| Phase 3  | Dataset collection              |
| Phase 4  | Feature engineering             |
| Phase 5  | Machine learning model training |
| Phase 6  | Real-time inference             |
| Phase 7  | Trilateration                   |
| Phase 8  | Kalman filtering                |
| Phase 9  | Dashboard development           |
| Phase 10 | Testing and evaluation          |
| Phase 11 | Documentation and final report  |

---

# 14. Required Resources

## Hardware

* ESP32 development boards (minimum three)
* BLE beacon/tag
* Laptop or workstation
* Wi-Fi router
* Measuring tape for calibration
* Tripods or fixed anchor mounts (recommended)

## Software

* ESP-IDF
* Visual Studio Code
* Python
* Git
* Scikit-learn
* Pandas
* NumPy
* SciPy
* Streamlit
* FastAPI

---

# 15. Success Criteria

The project shall be considered successful if it:

* Detects BLE advertisements reliably.
* Produces repeatable BLE observation windows.
* Trains a machine learning model that improves distance estimation over a baseline path-loss model.
* Estimates indoor positions using three or more anchors.
* Produces smooth, stable trajectories after filtering.
* Provides real-time visualization of the estimated tag position.
* Is fully documented and reproducible.

---

# 16. Future Work

Potential future enhancements include:

* Direct location prediction using machine learning.
* BLE fingerprinting.
* Multi-floor positioning.
* Adaptive anchor calibration.
* Multi-tag tracking.
* Mobile application support.
* Cloud-based analytics.
* Integration with additional sensors such as IMUs.

---

# 17. Conclusion

This project proposes a modular and extensible indoor positioning system that combines Bluetooth Low Energy technology, ESP32 anchor nodes, machine learning, trilateration, and state estimation techniques.

By separating data acquisition, distance estimation, localization, and filtering into independent components, the system aims to improve positioning accuracy while remaining cost-effective and scalable. The project also provides a platform for future research into intelligent indoor localization using low-cost wireless technologies.
