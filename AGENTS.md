# BLE Indoor Positioning & Localization Research Platform

Repository: `tafabande/ble-locater` (`c:\Users\DEV\Desktop\Dissertation`)

This repository is the dedicated Python core positioning engine, ML tournament suite, telemetry collector, and academic research platform for the dissertation.

## System Architecture

- **Backend Positioning & REST Engine (`ble-indoor-positioning/server/app.py`):**
  - High-performance FastAPI server with SQLite WAL persistence and real-time WebSocket broadcast (`/ws`).
  - Runs by default on `http://127.0.0.1:8000`.
- **Machine Learning Tournament Engine (`ble-indoor-positioning/learning/`, `training/`):**
  - Super Learner model ensemble (`distance_estimator.joblib`, `coordinate_regressor.joblib`, `zone_classifier.joblib`).
  - Online adaptive calibration and continuous feature engineering.
- **Hardware Telemetry Collector (`ble-indoor-positioning/collector/`):**
  - High-frequency UDP ingest pipeline (`UDP:5005`) capturing multi-anchor ESP32 packets.
- **Desktop Operations Console (`control.py` / `launch.bat`):**
  - Interactive launcher and unified supervisor for the backend, data surveyor, flasher, and model studio.
- **Cross-Repository Automation (`dashboard_pipeline.py`):**
  - Autonomous pipeline connecting this repository to the dedicated frontend dashboard repository.

## Frontend RTLS Dashboard (Separated Repository)

The frontend operations dashboard was separated into its own standalone repository:
- **Repository:** [`tafabande/ble-dashboard`](https://github.com/tafabande/ble-dashboard)
- **Local Directory:** `c:\Users\DEV\Desktop\Dashboard for Tag Movement`
- **Architecture:** React 19 + Vite 8 + Tailwind CSS v4 with zero external cloud dependencies.
- **Serving:** Production host server on `http://127.0.0.1:8443` (with pre-compiled static fallback bundled inside `ble-indoor-positioning/server/static/`).
- **One-Click Launch:** Run `launch.bat dashboard` from this repository or click `🚀 LAUNCH DASHBOARD PIPELINE` in `control.py`.

## Quick Commands

- **Start Operations Hub:** `python control.py` or double-click `launch.bat`
- **Launch Full Stack & Dashboard:** `launch.bat dashboard`
- **Run Diagnostics:** `python control.py --doctor` or `launch.bat doctor`
- **Run Backend Tests:** `.\ble-indoor-positioning\.venv\Scripts\python.exe -m pytest`
