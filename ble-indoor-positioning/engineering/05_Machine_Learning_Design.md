# Volume 5: Machine Learning Design Document

# MACHINE LEARNING DESIGN DOCUMENT (MLDD)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** MLDD-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Purpose
Specify the end-to-end machine learning pipeline for estimating BLE tag distance from engineered BLE features.

---

# 2. ML Problem
Supervised regression: predict distance (meters) from BLE observation windows.

---

# 3. Dataset
Each row represents a 1-second observation window with a measured ground-truth distance.

---

# 4. Input Features
- `rssi_mean`
- `rssi_min`
- `rssi_max`
- `rssi_std`
- `rssi_variance`
- `rssi_range`
- `rssi_delta_mean`
- `packet_count`
- `advertising_interval_ms`
- `scan_duration_ms`

---

# 5. Target
`distance_m` (measured with a tape measure during calibration).

---

# 6. Data Collection
Collect data at fixed distances (0.25–5 m) under open space, obstacles, people, interference, and motion. Split by experiment, not randomly, to avoid leakage.

---

# 7. Preprocessing
Remove invalid rows, handle missing values, compute engineered features, label observations, and version datasets.

---

# 8. Model Selection
Baseline: `RandomForestRegressor`. Compare with Gradient Boosting, XGBoost/LightGBM (optional), and Extra Trees.

---

# 9. Training Pipeline
Load dataset → preprocess → split train/validation/test → train → evaluate → save model (`.pkl`).

---

# 10. Evaluation
Metrics: MAE, RMSE, R². Report error by distance band and by environment.

---

# 11. Cross Validation
Use k-fold cross-validation and hold out entire experimental sessions for final testing.

---

# 12. Feature Importance
Record permutation or tree-based feature importance to identify influential BLE measurements.

---

# 13. Model Deployment
Load serialized model on the localization server. One prediction per observation window.

---

# 14. Inference Pipeline
Observation → feature engineering → `model.predict()` → estimated distance → trilateration.

---

# 15. Experiment Tracking
Store model version, dataset version, parameters, metrics, and notes for every experiment.

---

# 16. Retraining Strategy
Retrain after adding significant new environments or hardware changes. Maintain semantic model versions.

---

# 17. Acceptance Criteria
Baseline model outperforms log-distance path-loss baseline using MAE on unseen test data.
