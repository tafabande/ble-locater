# 📊 BLE Indoor Positioning Status Report

## 1. Current Dataset Layout
Based on the latest automated dataset audit, here is the current data collection status:

*   **Total Observation Windows**: 28,435
*   **Distance Range**: 0.5m to 5.3m
*   **Anchors Used**: **Only 1** (`ANCHOR_01`)
*   **Device Heights (m)**: 0.0, 0.4, 0.5, 0.74, 0.93, 0.94, 0.96, 1.0, 1.12, 1.22, 1.98
*   **Anchor Heights (m)**: **Only 1** (0.0m)
*   **Device Orientations**: **None** (Currently all logged as `unknown`)
*   **Motion States**: Stationary, Approaching, Moving Away
*   **Obstacle Diversity**: Tape Measure, Human Body, Concrete Wall, Wooden Door, Mattress, Table, Laptop, Wi-Fi Interference

---

## 2. What We Need Next (Data Gaps)
To build a truly robust multi-anchor positioning system, we have some critical missing pieces in the dataset:

1.  **Multiple Anchors (URGENT)**: The model has never seen data from a 2nd or 3rd anchor. We need data collected from multiple anchors simultaneously to test true multilateration or multi-anchor ML features.
2.  **Anchor Heights**: We recently added the `anchor_height_m` feature to the code, but all historical data was collected at `0.0m`. We need physical data collected with anchors placed at different heights (e.g., 1.0m, 2.0m on walls/tripods).
3.  **Device Orientations**: The `orientation` column exists but is empty (`unknown`). We need data specifying if the user is holding the phone in landscape, portrait, in a pocket, or blocking it with their body, as this drastically changes antenna gain and RSSI.

---

## 3. Model Status & Improvements
*   **Champion Architecture**: Ensemble Pipeline (Super Learner)
*   **Outlier Filter**: IsolationForest is actively rejecting transient hardware signal spikes.
*   **Cross-Validation**: We moved from random splitting to **Session-aware Group K-Fold**, which prevents temporal data leakage. 
*   **Latest Accuracy**: 
    *   Models are generally achieving **~0.30m Test MAE** during the tournament.
    *   R² is stabilizing between **0.80 - 0.84** on out-of-session data.

*   **Code Base Upgrades**: 
    *   `anchor_height_m` is fully integrated into the feature engineering pipeline and model training.
    *   The `train.py` script now automatically compares every new run against the previous `model_metadata.json` to tell us immediately if adding data made the models better or worse.
    *   GUI startup times are fixed.
