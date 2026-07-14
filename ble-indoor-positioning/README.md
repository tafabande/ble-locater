# AI-Assisted Indoor BLE Positioning System

## Overview

This project aims to develop an indoor positioning system using Bluetooth Low Energy (BLE) beacons and multiple ESP32 anchor nodes.

Unlike traditional RSSI-only localization, this project uses Machine Learning to estimate the distance between a BLE tag and each ESP32 anchor before applying trilateration and filtering to estimate the tag's position.

---

## Features

- BLE advertisement scanning
- Rich BLE feature extraction
- Machine Learning distance estimation
- Trilateration
- Kalman filtering
- Real-time visualization

---

## Technologies

- ESP32
- ESP-IDF
- Python
- Scikit-learn
- NumPy
- Pandas
- Streamlit
- FastAPI

---

## Project Status

🚧 In Development

Current milestone:

✔ Repository created

✔ Documentation

✔ BLE Scanner & Telemetry Pipeline

⬜ Dataset Collection

⬜ AI Distance Estimator

⬜ Trilateration

⬜ Kalman Filter

⬜ Dashboard

---

## Hardware Setup

| Anchor ID | Board Type | BLE | Wi-Fi | Role |
| --- | --- | --- | --- | --- |
| **A1** | ESP32 DevKit V1 Type-C (ESP32-WROOM-32E) | ✅ | ✅ | Anchor Node 1 |
| **A2** | NodeMCU-32 v1.3 (ESP32) | ✅ | ✅ | Anchor Node 2 |

---

## Getting Started

### 1. Firmware (ESP32)
The firmware is written in **C++** using ESP-IDF (Bluedroid stack) with an object-oriented architecture (`Packet`, `BLEScanner`, `Statistics`, `Observation` classes).

To compile and flash the firmware:
```bash
cd firmware
idf.py build
idf.py -p <PORT> flash monitor
```

#### Dynamic Serial Commands
The ESP32 firmware features an interactive UART command shell at `115200` baud. You can send the following commands over serial:
- `HELP`: Show help menu.
- `GET_CONFIG`: Print current configuration in JSON.
- `SET_ANCHOR=<id>`: Set the anchor node identifier (e.g. `SET_ANCHOR=A1`).
- `SET_TAG=<mac>`: Set the target BLE beacon MAC address (e.g. `SET_TAG=52:06:26:03:01:DA`).
- `SET_MODE=<NORMAL|RAW|DUAL>`: Set the output mode:
  - `NORMAL`: Sends only aggregated 1-second observation windows (JSON).
  - `RAW`: Sends only raw packet logs as they arrive (JSON).
  - `DUAL`: Sends both.
- `TEST_MATH`: Executes a firmware self-test using a synthetic sequence of RSSI values to verify statistics computations.

### 2. Python Tools

#### Installation
Ensure you have the virtual environment activated and dependencies installed:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### Running the Collector
To read from a physical anchor on serial:
```bash
python collector/collector.py --anchor A1 --tag 52:06:26:03:01:DA --mode NORMAL
```

#### Phase 5.5: Tag Capability Investigation
To connect to the target beacon, authenticate using the password, discover characteristics, and print parsed telemetry:
```bash
python collector/investigate_tag.py
```
This discovers services, logs authentication outcome (Success, Failure, Timeout, Unsupported, Permission Denied), and prints raw telemetry decoded into Hex, ASCII, integers, floats, and JSON formats.

#### Running the Emulator (Local PC Testing)
To verify the entire data collection and aggregation pipeline without physical hardware:
```bash
# Simulates the ESP32 node and pipes data directly into the collector
python collector/emulator.py --mode DUAL --duration 10 | python collector/collector.py --port stdin --anchor A1
```
This generates:
- `datasets/observations.csv`: Aggregated observation windows for machine learning containing 21 descriptive statistical features.
- `datasets/raw_packets.csv`: Raw packet logs for debugging.


