# System Architecture

## High-Level Pipeline

BLE Tag

↓

ESP32 Anchors

↓

Feature Extraction

↓

Machine Learning Distance Estimator

↓

Distance Estimates

↓

Trilateration

↓

Kalman Filter

↓

Estimated Position

---

## Components

### BLE Tag

Broadcasts BLE advertisement packets.

### ESP32 Anchors

Receive advertisements and compute signal statistics.

### Feature Engineering

Transforms raw BLE measurements into machine learning features.

### Machine Learning

Predicts the distance between each anchor and the BLE tag.

### Trilateration

Calculates the tag position using distances from multiple anchors.

### Kalman Filter

Smooths the estimated trajectory.
