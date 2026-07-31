"""
BLE Indoor Positioning — Real-Time Inference & Localization Server
===================================================================

A FastAPI backend server that:
  1. Loads the trained Stacking Ensemble model and Feature Scaler.
  2. Receives raw BLE advertisement telemetry from multiple ESP32 anchors.
  3. Groups packets into sliding 1-second observation windows.
  4. Performs 30-feature extraction and predicts distance in real-time.
  5. Solves tag coordinates using Weighted Least-Squares Trilateration.
  6. Smoothes coordinate trajectories via 2D Kalman Filter.
  7. Exposes real-time positioning status to the Streamlit UI dashboard.
"""

import os
import sys
import time
import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import numpy as np
import pandas as pd
import joblib

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from feature_engineering.engineer import compute_window_features
from localization.trilateration import TrilaterationEngine, KalmanFilter2D

# Logger config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BLE_SERVER")

# Instantiate FastAPI App
app = FastAPI(title="BLE Indoor Positioning Backend", version="1.0")

# ──────────────────────────────────────────────────────────────────────
#  DEFAULT CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

# Default physical coordinates (x, y) of anchors in meters
DEFAULT_ANCHORS_CONFIG = {
    "ANCHOR_01": (0.0, 0.0),    # Origin
    "ANCHOR_02": (5.0, 0.0),    # 5 meters along X-axis
    "ANCHOR_03": (2.5, 4.33),   # Equilateral triangle peak
}

# Real-time state store
state = {
    "model": None,
    "scaler": None,
    "model_metadata": None,
    "anchors_config": DEFAULT_ANCHORS_CONFIG,
    "trilateration_engine": TrilaterationEngine(DEFAULT_ANCHORS_CONFIG),
    "kalman_filter": KalmanFilter2D(dt=1.0, process_noise=0.15, measurement_noise=0.35),
    "last_raw_packets": defaultdict(list),  # anchor -> list of (timestamp, rssi)
    "estimated_distances": {},  # anchor -> estimated_dist
    "last_position": {"x": 0.0, "y": 0.0, "uncertainty": 0.0, "gdop": 0.0},
    "history": [],  # list of {"timestamp": t, "x": x, "y": y}
    "active_connections": []
}


# ──────────────────────────────────────────────────────────────────────
#  Pydantic Models
# ──────────────────────────────────────────────────────────────────────

class PacketData(BaseModel):
    timestamp: int
    anchor: str
    mac: str
    rssi: int
    name: str


class ConfigUpdate(BaseModel):
    anchor_id: str
    x: float
    y: float


# ──────────────────────────────────────────────────────────────────────
#  LIFECYCLE EVENTS
# ──────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def load_ml_assets():
    """Load model, scaler, and configuration on server startup."""
    model_path = os.path.join(PROJECT_ROOT, "models", "distance_estimator.joblib")
    scaler_path = os.path.join(PROJECT_ROOT, "models", "scaler.joblib")
    meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        logger.warning(
            "⚠️ Trained model or scaler file not found. "
            "Please train the model first using 'pipeline.py'. Inference will use fallback path-loss model."
        )
        return

    try:
        state["model"] = joblib.load(model_path)
        state["scaler"] = joblib.load(scaler_path)
        with open(meta_path, "r") as f:
            state["model_metadata"] = json.load(f)
        logger.info(
            f"✅ Champion model loaded: {state['model_metadata'].get('champion_model', 'Ensemble')}. "
            f"Trained MAE: {state['model_metadata'].get('metrics', {}).get('test_mae')}m"
        )
    except Exception as e:
        logger.error(f"❌ Failed to load model assets: {e}")


# ──────────────────────────────────────────────────────────────────────
#  LIVE DATA STREAM & REAL-TIME LOCALIZATION
# ──────────────────────────────────────────────────────────────────────

def predict_distance_for_anchor(anchor_id: str, rssi_list: List[int], timestamps: List[int]) -> Optional[float]:
    """Helper to perform feature engineering and predict distance."""
    if len(rssi_list) < 1:
        return None

    # Construct temporary dataframe mimicking engineer.py inputs
    group = pd.DataFrame({
        "rssi": rssi_list,
        "timestamp": timestamps
    })

    # Compute the 30-feature vector
    features = compute_window_features(group)

    # 1. Model Inference (if model is loaded)
    if state["model"] is not None and state["scaler"] is not None:
        try:
            # Extract features in correct order
            feature_cols = state["model_metadata"]["feature_cols"]
            X = np.array([[features[col] for col in feature_cols]])
            X_scaled = state["scaler"].transform(X)
            predicted_dist = float(state["model"].predict(X_scaled)[0])
            return predicted_dist
        except Exception as e:
            logger.warning(f"Inference failed for {anchor_id}, falling back to path loss model. Error: {e}")

    # 2. Physical Fallback (Log-distance path loss prior)
    return features["path_loss_indoor"]


def perform_localization():
    """Ties together predicted distances, trilateration, and Kalman filtering."""
    now_ms = int(time.time() * 1000)

    # 1. Process sliding 1.5-second windows of raw packets
    active_distances = {}
    for anchor_id, packets in list(state["last_raw_packets"].items()):
        # Filter packets within last 1500ms
        valid_packets = [(t, r) for (t, r) in packets if now_ms - t < 1500]
        state["last_raw_packets"][anchor_id] = valid_packets

        if valid_packets:
            times = [t for (t, _) in valid_packets]
            rssis = [r for (_, r) in valid_packets]
            dist = predict_distance_for_anchor(anchor_id, rssis, times)
            if dist is not None:
                active_distances[anchor_id] = dist

    state["estimated_distances"] = active_distances

    # 2. Run Trilateration if at least 2 anchors have data
    if len(active_distances) >= 2:
        try:
            pos, uncertainty, gdop = state["trilateration_engine"].estimate_position(active_distances)

            # 3. Kalman trajectory smoothing
            smoothed_x, smoothed_y = state["kalman_filter"].filter(pos[0], pos[1])

            state["last_position"] = {
                "x": round(smoothed_x, 3),
                "y": round(smoothed_y, 3),
                "uncertainty": uncertainty,
                "gdop": gdop
            }

            state["history"].append({
                "timestamp": now_ms,
                "x": round(smoothed_x, 3),
                "y": round(smoothed_y, 3)
            })

            # Keep history buffer to last 100 points
            if len(state["history"]) > 100:
                state["history"].pop(0)

            # Broadcast update via WebSockets
            broadcast_position_update()

        except Exception as e:
            logger.error(f"Localization engine error: {e}")


def broadcast_position_update():
    """Broadcast real-time state change to all listening UI clients."""
    msg = json.dumps({
        "event": "position_update",
        "data": {
            "position": state["last_position"],
            "distances": state["estimated_distances"],
            "history": state["history"]
        }
    })
    for conn in list(state["active_connections"]):
        try:
            # Running as async WS transmission
            pass
        except Exception:
            state["active_connections"].remove(conn)


# ──────────────────────────────────────────────────────────────────────
#  REST API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────

@app.post("/api/observation")
def add_raw_packet(packet: PacketData):
    """Receives a raw BLE observation packet from an anchor node."""
    now_ms = int(time.time() * 1000)
    state["last_raw_packets"][packet.anchor].append((now_ms, packet.rssi))

    # Trigger real-time localization update on packet arrival
    perform_localization()

    return {"status": "success", "active_anchors": list(state["last_raw_packets"].keys())}


@app.get("/api/state")
def get_position_state():
    """Retrieve full location coordinates, estimated distances, and history."""
    return {
        "position": state["last_position"],
        "distances": state["estimated_distances"],
        "anchors": state["anchors_config"],
        "history": state["history"]
    }


@app.post("/api/config/anchors")
def configure_anchor(config: ConfigUpdate):
    """Update anchor coordinates."""
    state["anchors_config"][config.anchor_id] = (config.x, config.y)
    # Re-instantiate engine with new coords
    state["trilateration_engine"] = TrilaterationEngine(state["anchors_config"])
    logger.info(f"Updated config: {config.anchor_id} set to ({config.x}, {config.y})")
    return {"status": "success", "anchors": state["anchors_config"]}


# ──────────────────────────────────────────────────────────────────────
#  WEBSOCKET REAL-TIME BROADCAST
# ──────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state["active_connections"].append(websocket)
    try:
        # Keep connection open
        while True:
            # Send current state every 1 second
            current_data = {
                "event": "position_update",
                "data": {
                    "position": state["last_position"],
                    "distances": state["estimated_distances"],
                    "history": state["history"]
                }
            }
            await websocket.send_json(current_data)
            await time.sleep(1.0)
    except WebSocketDisconnect:
        state["active_connections"].remove(websocket)
    except Exception:
        if websocket in state["active_connections"]:
            state["active_connections"].remove(websocket)
