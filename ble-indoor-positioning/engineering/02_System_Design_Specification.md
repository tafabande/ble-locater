# Volume 2: System Design Specification

# SYSTEM DESIGN SPECIFICATION (SDS)

## AI-Assisted Indoor Bluetooth Low Energy Positioning System Using ESP32 Anchor Nodes and Machine Learning

**Document ID:** SDS-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# Revision History

| Version | Date      | Description                         |
| ------- | --------- | ----------------------------------- |
| 1.0     | July 2026 | Initial System Design Specification |

---

# Table of Contents

1. Introduction
2. System Overview
3. Design Objectives
4. Functional Requirements
5. Non-Functional Requirements
6. System Context
7. Overall Architecture
8. Hardware Architecture
9. Software Architecture
10. Data Architecture
11. Machine Learning Architecture
12. Localization Architecture
13. Communication Architecture
14. Error Handling
15. System States
16. Performance Requirements
17. Verification Criteria
18. Design Decisions
19. Future Expansion

---

# 1. Introduction

This document specifies the technical architecture of the AI-Assisted Indoor BLE Positioning System.

Its purpose is to define every subsystem required to acquire BLE measurements, estimate distances using machine learning, determine the position of a BLE tag through trilateration, and present the estimated location to the user in real time.

This document serves as the primary engineering reference for implementation.

---

# 2. System Overview

The proposed system consists of four logical layers:

Layer 1 – Data Acquisition

ESP32 anchor nodes receive BLE advertisement packets and compute statistical measurements.

↓

Layer 2 – Data Intelligence

Machine learning predicts the distance between each anchor and the BLE tag.

↓

Layer 3 – Localization

Distances from multiple anchors are combined using trilateration and filtered to obtain a stable position estimate.

↓

Layer 4 – Visualization

The estimated position and diagnostics are presented through a graphical dashboard.

---

# 3. Design Objectives

The system shall:

* Continuously monitor BLE advertisements.
* Produce standardized observation windows.
* Estimate anchor-to-tag distance using machine learning.
* Estimate two-dimensional position using trilateration.
* Filter noisy position estimates.
* Support real-time operation.
* Remain modular and extensible.

---

# 4. Functional Requirements

## FR-001

The ESP32 shall continuously scan for BLE advertisements.

---

## FR-002

The ESP32 shall identify the target BLE tag using its MAC address.

---

## FR-003

The ESP32 shall buffer observations for a configurable observation window.

Default:

1 second

---

## FR-004

Each observation window shall produce statistical signal features.

---

## FR-005

Observation windows shall be transmitted to the localization server.

---

## FR-006

The server shall perform feature preprocessing.

---

## FR-007

The machine learning model shall estimate the distance between each anchor and the BLE tag.

---

## FR-008

The localization engine shall compute the BLE tag position.

---

## FR-009

The tracking engine shall smooth the estimated trajectory.

---

## FR-010

The dashboard shall display the current position and system status.

---

# 5. Non-Functional Requirements

| Requirement        | Target                                                |
| ------------------ | ----------------------------------------------------- |
| Availability       | >95% during testing sessions                          |
| Prediction latency | <100 ms after observation reception                   |
| Scalability        | Support additional anchors without redesign           |
| Maintainability    | Modular codebase with documented interfaces           |
| Extensibility      | New ML models can be substituted with minimal changes |
| Reproducibility    | Training and evaluation procedures documented         |

---

# 6. System Context

External Entities

* BLE Tag
* ESP32 Anchors
* Localization Server
* Dashboard User

System Boundary

The system begins when BLE advertisements are received by the ESP32 anchors and ends when the estimated tag position is displayed to the user.

---

# 7. Overall System Architecture

```
BLE Tag
    │
    ▼
ESP32 Anchor Nodes
    │
    ▼
Observation Window Generator
    │
    ▼
Communication Layer
    │
    ▼
Localization Server
    │
    ▼
Feature Engineering
    │
    ▼
Distance Regression Model
    │
    ▼
Distance Estimates
    │
    ▼
Weighted Trilateration
    │
    ▼
Kalman Filter
    │
    ▼
Dashboard
```

---

# 8. Hardware Architecture

## BLE Tag

Responsibilities

* Periodically transmit BLE advertisements.
* Maintain a stable advertising interval.
* Operate on battery power.

---

## ESP32 Anchor

Responsibilities

* Scan BLE advertisements.
* Filter advertisements by target device.
* Maintain an observation buffer.
* Compute signal statistics.
* Transmit observation windows.

Each anchor has

* Unique identifier
* Known fixed coordinates
* Wi-Fi interface
* BLE radio

---

## Localization Server

Responsibilities

* Receive observations.
* Run machine learning inference.
* Execute localization.
* Store historical measurements.
* Provide dashboard data.

---

# 9. Software Architecture

The software is organized into independent modules.

```
Firmware

├── BLE Scanner

├── Packet Buffer

├── Statistics Engine

└── Communication Module

↓

Collector

↓

Feature Engineering

↓

Inference Engine

↓

Localization Engine

↓

Tracking Engine

↓

Visualization
```

Each module has clearly defined inputs and outputs.

---

# 10. Data Architecture

Observation Window

| Field                   | Description                |
| ----------------------- | -------------------------- |
| timestamp               | Observation time           |
| anchor_id               | Anchor identifier          |
| device_mac              | BLE tag MAC address        |
| packet_count            | Advertisements received    |
| scan_duration_ms        | Window duration            |
| rssi_mean               | Average RSSI               |
| rssi_min                | Minimum RSSI               |
| rssi_max                | Maximum RSSI               |
| rssi_std                | Standard deviation         |
| rssi_variance           | Variance                   |
| rssi_range              | Maximum minus minimum RSSI |
| rssi_delta_mean         | Mean RSSI change           |
| advertising_interval_ms | Estimated interval         |

Training Label

distance_m

---

# 11. Machine Learning Architecture

Problem Type

Regression

Inputs

* RSSI Mean
* RSSI Standard Deviation
* RSSI Variance
* RSSI Range
* Packet Count
* Scan Duration
* Estimated Advertising Interval

Output

Estimated Distance

Baseline Algorithm

Random Forest Regressor

Evaluation Metrics

* Mean Absolute Error (MAE)
* Root Mean Square Error (RMSE)
* R² Score

Future candidate models

* Gradient Boosting
* XGBoost
* LightGBM

---

# 12. Localization Architecture

Inputs

* Anchor coordinates
* Predicted distances

Algorithm

Weighted Trilateration

Output

Estimated X coordinate

Estimated Y coordinate

If more than three anchors are available, the localization engine shall solve an overdetermined system using least-squares optimization.

---

# 13. Communication Architecture

## Development Mode

ESP32

↓

USB Serial

↓

Collector

## Deployment Mode

ESP32

↓

Wi-Fi

↓

Localization Server

Recommended message format

JSON

Each message shall contain one observation window.

---

# 14. Error Handling

Firmware

* Lost advertisement packets
* BLE scan timeout
* Communication timeout

Server

* Missing observations
* Invalid feature vectors
* Model loading failure
* Localization failure

Dashboard

* Connection loss
* Stale data detection
* User notification

All recoverable errors shall be logged with timestamps.

---

# 15. System State Model

ESP32 Anchor

```
Initialize

↓

Scanning

↓

Packet Buffering

↓

Statistics Calculation

↓

Transmission

↓

Scanning
```

Localization Server

```
Waiting

↓

Observation Received

↓

Feature Engineering

↓

Inference

↓

Localization

↓

Filtering

↓

Dashboard Update

↓

Waiting
```

---

# 16. Performance Requirements

| Parameter                | Target                     |
| ------------------------ | -------------------------- |
| Observation window       | 1 second (configurable)    |
| Prediction latency       | <100 ms                    |
| Localization update rate | ≥1 Hz                      |
| Supported anchors        | Minimum 3                  |
| Supported BLE tags       | Initially 1 (expandable)   |
| Continuous runtime       | ≥8 hours during evaluation |

---

# 17. Verification Criteria

The design will be verified through:

* Unit testing of each software module.
* Integration testing between firmware and server.
* Controlled calibration experiments.
* Regression model evaluation using unseen test data.
* Localization accuracy measurements in a defined indoor test area.
* End-to-end system demonstrations.

Each subsystem must pass verification before integration into the complete system.

---

# 18. Design Decisions

**DD-001**
Machine learning shall estimate **distance**, not **position**, to preserve explainability and allow established geometric localization methods.

**DD-002**
ESP32 anchors shall transmit observation summaries rather than raw packet streams to reduce bandwidth and processing overhead.

**DD-003**
The baseline machine learning model shall be a Random Forest Regressor due to its robustness with nonlinear relationships and moderate-sized datasets.

**DD-004**
Weighted trilateration shall be used for localization because it allows anchors with more reliable measurements to contribute more strongly to the final position estimate.

**DD-005**
Kalman filtering shall be applied after localization rather than before, ensuring smoothing occurs on the estimated trajectory rather than on individual measurements.

---

# 19. Future Expansion

The architecture has been designed to support:

* Four or more anchor nodes.
* Multi-tag tracking.
* Three-dimensional localization.
* Automatic anchor calibration.
* Confidence estimation for each position.
* Mobile and web-based dashboards.
* Alternative regression models.
* BLE fingerprinting experiments.
* Hybrid localization with additional sensors (e.g., IMUs).

---

# Appendix A – Primary Data Flow

```
BLE Advertisement

↓

ESP32 Scan

↓

Observation Window

↓

Feature Engineering

↓

Distance Estimation

↓

Distance Set

↓

Trilateration

↓

Kalman Filter

↓

Estimated Position

↓

Dashboard
```

---

# Appendix B – Development Milestones

| Milestone | Deliverable                  |
| --------- | ----------------------------- |
| M1        | ESP32 BLE scanner            |
| M2        | Observation window generator |
| M3        | Serial collector             |
| M4        | Dataset collection           |
| M5        | Feature engineering pipeline |
| M6        | Distance regression model    |
| M7        | Real-time inference server   |
| M8        | Trilateration engine         |
| M9        | Kalman filter                |
| M10       | Live dashboard               |
| M11       | System validation            |
| M12       | Final documentation          |
