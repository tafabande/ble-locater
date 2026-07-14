# Volume 10: Developer Manual

# DEVELOPER MANUAL (DEV)

## AI-Assisted Indoor BLE Positioning System

**Document ID:** DEV-001
**Version:** 1.0
**Status:** Draft
**Prepared By:** Bleigh TJ Bande
**Date:** July 2026

---

# 1. Introduction
Guide for developers contributing to firmware, server, ML, and dashboard.

---

# 2. Repository Layout
- [firmware/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/firmware): ESP32 scanning firmware code.
- [collector/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/collector): Serial and network data collection scripts.
- [feature_engineering/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/feature_engineering): Code for parsing and preprocessing observation statistics.
- [training/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/training): Model training and evaluation scripts.
- [models/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/models): Saved serialized model objects (`.pkl`).
- [localization/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/localization): Trilateration and Kalman filtering algorithms.
- [server/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/server): FastAPI application endpoints.
- [dashboard/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/dashboard): Streamlit visualization interface.
- [tests/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/tests): Automated test suite.
- [docs/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/docs) & [engineering/](file:///c:/Users/User/Desktop/final%20year/ble-indoor-positioning/engineering): Architectural design and project documentation.

---

# 3. Development Environment Setup
To set up your environment:
1. Install Git, Python 3.10+, and the ESP-IDF toolchain.
2. Initialize and activate the virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your workspace in VS Code.

---

# 4. Git Workflow
- Use feature branches (`feature/feature-name`) branched from `main`.
- Propose changes through Pull Requests (PRs).
- Ensure code passes reviews and tests before merging.
- Use semantic commit messages (e.g., `feat: ...`, `fix: ...`, `docs: ...`).
- Use Git tags for project releases (e.g., `v1.0.0`).

---

# 5. Coding Standards
- Follow PEP 8 guidelines for Python code.
- Write descriptive function, class, and variable names.
- Document functions and classes clearly with docstrings.
- Design modular, clean ESP-IDF components for C/C++ firmware.

---

# 6. Firmware Development
- Compile and flash the ESP32 using the ESP-IDF CLI (`idf.py build`, `idf.py flash`, `idf.py monitor`).
- Ensure the scanner firmware generates correct observation windows and outputs valid JSON objects as specified in the ICD.

---

# 7. Python Development
- Run the serial collector to gather raw test data.
- Train the model using the training scripts and verify the model output quality.
- Start the server and the dashboard to test the real-time pipeline.

---

# 8. Testing
- Run the automated unit tests in the `tests/` directory before committing code.
- Validate that all internal and external communication interfaces comply with the ICD after changes are made to the firmware or APIs.

---

# 9. Logging & Debugging
- Use structured logging with explicit severity levels (DEBUG, INFO, WARNING, ERROR).
- Preserve complete traceback details on unhandled exceptions.
- Always include firmware version and server version details in bug reports.

---

# 10. Versioning
- Apply Semantic Versioning (`MAJOR.MINOR.PATCH`) to software releases.
- Version machine learning models semantically along with the dataset versions they were trained on.
- Maintain a changelog file documenting key updates.

---

# 11. Contribution Checklist
- [ ] Code builds without errors.
- [ ] Automated tests pass successfully.
- [ ] Relevant documentation has been updated.
- [ ] Interfaces match the current ICD or changes have been approved and documented.
- [ ] Pull request review has been completed.

---

# 12. Future Contributors
Read the System Design Specification (SDS), Software Architecture Design (SAD), Hardware Design Specification (HDS), Machine Learning Design Document (MLDD), and Interface Control Document (ICD) before implementing new features.
