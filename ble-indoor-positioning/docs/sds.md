# AI-Assisted Indoor BLE Positioning System

## System Design Specification (SDS)

### Version 1.0

---

# 1. Executive Summary

## Project Title

AI-Assisted Indoor Bluetooth Low Energy (BLE) Positioning System Using ESP32 Anchor Nodes

## Project Purpose

The purpose of this project is to design, implement, and evaluate an indoor positioning system capable of estimating the location of a Bluetooth Low Energy (BLE) tag using multiple ESP32 anchor nodes.

Unlike conventional RSSI-based localization systems that directly convert RSSI into distance using mathematical path-loss equations, this project introduces a Machine Learning-based distance estimation model. The model learns the characteristics of radio propagation in indoor environments and predicts distance more accurately by considering multiple signal features rather than RSSI alone.

The estimated distances from multiple anchors are then used by a trilateration engine to compute the position of the BLE tag. Finally, a filtering algorithm smooths the resulting trajectory to reduce measurement noise.

---

# 2. Problem Statement

Indoor positioning remains a difficult engineering problem because BLE signal strength is highly susceptible to environmental effects such as:

* Multipath propagation
* Human body attenuation
* Walls and furniture
* RF interference
* Device orientation
* Antenna polarization
* Bluetooth traffic congestion

Traditional distance estimation methods assume ideal propagation conditions, resulting in large localization errors indoors.

This project aims to reduce these errors through machine learning and statistical signal analysis.

---

# 3. Project Objectives

## Primary Objective

Develop an indoor BLE positioning system capable of estimating the location of a BLE tag using multiple ESP32 anchors.

## Secondary Objectives

* Design a reusable BLE data acquisition platform.
* Collect high-quality BLE datasets.
* Engineer robust signal features.
* Train and evaluate regression models.
* Implement real-time distance estimation.
* Perform trilateration.
* Smooth trajectories using state estimation.
* Build a visualization dashboard.

---

# 4. Project Scope

The project includes:

* ESP32 BLE scanning
* Dataset collection
* Feature engineering
* Machine learning
* Distance estimation
* Trilateration
* Kalman filtering
* Real-time visualization

The project excludes:

* GPS
* Ultra-Wideband (UWB)
* Camera-based localization
* Fingerprinting-based localization (future work)

---

# 5. Success Criteria

The project shall be considered successful if it can:

* Detect BLE advertisements reliably.
* Estimate distance more accurately than a traditional RSSI path-loss model.
* Compute indoor tag positions using three or more anchors.
* Produce stable trajectories after filtering.
* Operate continuously in real time.

---

# 6. High-Level System Architecture

System Pipeline:

BLE Tag

↓

BLE Advertisement

↓

ESP32 Anchor Nodes

↓

BLE Feature Extraction

↓

Feature Engineering

↓

Machine Learning Distance Estimator

↓

Distance Estimates

↓

Trilateration Engine

↓

Kalman Filter

↓

Estimated Position

↓

Dashboard

---

# 7. Hardware Architecture

## BLE Tag

Responsibilities

* Broadcast BLE advertisements
* Maintain fixed advertisement interval
* Low power operation

---

## ESP32 Anchor

Responsibilities

* Continuous BLE scanning
* Filter advertisements
* Compute signal statistics
* Transmit observation windows

Each anchor has:

* Unique ID
* Known coordinates
* Wi-Fi connectivity
* BLE receiver

---

## Server

Responsibilities

* Receive anchor observations
* Perform inference
* Compute localization
* Store historical data
* Provide dashboard API

---

# 8. Software Architecture

The software is divided into independent modules.

Firmware Layer

* BLE Scanner
* Packet Buffer
* Statistics Engine
* Communication Module

Python Layer

* Collector
* Feature Engineering
* ML Inference
* Localization
* Visualization

---

# 9. Repository Structure

ble-indoor-positioning/

docs/

firmware/

collector/

datasets/

feature_engineering/

training/

models/

localization/

server/

dashboard/

tests/

README.md

requirements.txt

LICENSE

---

# 10. Data Flow

Step 1

BLE Tag broadcasts advertisements.

↓

Step 2

ESP32 scans advertisements.

↓

Step 3

Packets are buffered for one observation window.

↓

Step 4

Signal statistics are computed.

↓

Step 5

Observation window transmitted.

↓

Step 6

Python server performs preprocessing.

↓

Step 7

Machine learning predicts distance.

↓

Step 8

Distances from all anchors collected.

↓

Step 9

Trilateration computes position.

↓

Step 10

Kalman filter smooths trajectory.

↓

Step 11

Dashboard updated.

---

# 11. Observation Window Specification

One observation window represents one second of BLE scanning.

Each observation becomes one training sample.

Fields

timestamp

anchor_id

device_mac

packet_count

scan_duration_ms

rssi_mean

rssi_min

rssi_max

rssi_std

rssi_variance

rssi_range

rssi_delta_mean

advertising_interval

distance_m (training only)

---

# 12. Dataset Specification

Target Variable

distance_m

Independent Variables

RSSI Mean

RSSI Variance

RSSI Standard Deviation

RSSI Range

RSSI Delta

Packet Count

Packets Per Second

Advertising Interval

Scan Duration

Future Variables

Battery Voltage

Temperature

Humidity

---

# 13. Feature Engineering

Each observation window is transformed into features.

Calculations include

Mean

Median

Variance

Standard Deviation

Minimum

Maximum

Range

Rolling Mean

Rolling Variance

RSSI Velocity

Packet Arrival Rate

These features become the model input.

---

# 14. Machine Learning Design

Problem Type

Regression

Baseline Model

Random Forest Regressor

Future Models

Gradient Boosting

XGBoost

LightGBM

Neural Networks

Evaluation Metrics

Mean Absolute Error

Root Mean Square Error

R² Score

Cross Validation Score

Feature Importance

---

# 15. Localization Engine

Input

Anchor Coordinates

Predicted Distances

Output

Estimated X Coordinate

Estimated Y Coordinate

Localization Method

Weighted Trilateration

Future

Least Squares Optimization

Nonlinear Optimization

Particle Localization

---

# 16. Tracking Engine

Initial Version

Kalman Filter

Inputs

Previous Position

Current Position

Velocity Estimate

Outputs

Filtered Position

Filtered Velocity

Future

Extended Kalman Filter

Particle Filter

---

# 17. Calibration Procedure

Calibration Distances

0.25 m

0.50 m

0.75 m

1.00 m

1.25 m

1.50 m

2.00 m

2.50 m

3.00 m

4.00 m

5.00 m

Each distance shall be recorded under

Open Space

Wall Obstruction

Human Obstruction

Bluetooth Interference

Moving Tag

Different Rooms

Each experiment shall contain sufficient observations to characterize natural signal variability.

---

# 18. Experimental Methodology

Experiment 1

Baseline Open Environment

Objective

Measure BLE characteristics without interference.

Experiment 2

Human Body Blocking

Objective

Measure attenuation.

Experiment 3

Wall Blocking

Objective

Measure structural attenuation.

Experiment 4

Bluetooth Congestion

Objective

Measure RF interference.

Experiment 5

Motion

Objective

Measure temporal signal variation.

---

# 19. Functional Requirements

The system shall

Scan BLE advertisements continuously.

Compute observation statistics.

Export standardized observation windows.

Predict distance.

Perform trilateration.

Display position.

Store observations.

Allow retraining.

---

# 20. Non-Functional Requirements

Real-Time Operation

Reliable Communication

Modular Design

Maintainability

Scalability

Reproducibility

Portable Deployment

Open Source Compatibility

---

# 21. Performance Targets

BLE Detection Rate

> 95%

Distance Estimation

Target Mean Absolute Error below 0.3 m in controlled indoor calibration (0.5–3 m). Performance beyond this range should be reported separately.

Localization

Target median position error below 1.0 m in the defined test environment.

Observation Window

1 second

Prediction Latency

Below 100 ms on the server after receiving an observation window.

---

# 22. Risk Assessment

Risk

RSSI instability

Mitigation

Feature engineering

Machine learning

Filtering

Risk

Anchor failure

Mitigation

Redundant anchors

Health monitoring

Risk

Wireless interference

Mitigation

Longer observation windows

Adaptive filtering

---

# 23. Development Roadmap

Phase 1

Repository Setup

Phase 2

Development Environment

Phase 3

Documentation

Phase 4

BLE Scanner

Phase 5

Serial Collector

Phase 6

Dataset Collection

Phase 7

Feature Engineering

Phase 8

Machine Learning

Phase 9

Real-Time Inference

Phase 10

Multiple Anchors

Phase 11

Trilateration

Phase 12

Kalman Filter

Phase 13

Dashboard

Phase 14

Performance Evaluation

Phase 15

Final Documentation

---

# 24. Deliverables

Firmware

Python Collector

Dataset

Machine Learning Model

Localization Engine

Dashboard

Technical Documentation

Experimental Results

GitHub Repository

---

# 25. Future Enhancements

* Direct location prediction using deep learning.
* BLE fingerprinting.
* Multi-floor positioning.
* Automatic anchor calibration.
* Dynamic confidence estimation.
* Mobile application.
* Cloud synchronization.
* Multi-tag tracking.
* Web-based monitoring interface.

---

# 26. Definition of Done

The project is complete when:

1. Three ESP32 anchors operate simultaneously.
2. Observation windows are generated consistently.
3. A trained regression model estimates distance.
4. Trilateration computes indoor position.
5. A Kalman filter smooths the trajectory.
6. A dashboard visualizes the tag in real time.
7. Experimental results are documented and reproducible.
8. Source code and documentation are published in the GitHub repository.

---

# 27. Engineering Philosophy

This project follows a modular systems engineering approach.

Every subsystem must be independently testable before integration.

The implementation sequence is:

1. Reliable BLE measurement.
2. Reliable dataset collection.
3. Reliable feature engineering.
4. Reliable distance estimation.
5. Reliable localization.
6. Reliable trajectory filtering.
7. Reliable visualization.

Machine learning is used only where it provides measurable value: improving distance estimation from noisy radio measurements. Geometry and filtering remain responsible for computing and stabilizing the final position, creating a system that is explainable, extensible, and suitable for engineering evaluation.
