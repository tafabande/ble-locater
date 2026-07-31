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
import asyncio
from contextlib import asynccontextmanager
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

# ──────────────────────────────────────────────────────────────────────
#  DEFAULT CONFIGURATION & STATE
# ──────────────────────────────────────────────────────────────────────

DEFAULT_ANCHORS_CONFIG = {
    "ANCHOR_01": (0.0, 0.0),    # Origin
    "ANCHOR_02": (5.0, 0.0),    # 5 meters along X-axis
    "ANCHOR_03": (2.5, 4.33),   # Equilateral triangle peak
}

state = {
    "model": None,
    "scaler": None,
    "model_metadata": None,
    "anchors_config": DEFAULT_ANCHORS_CONFIG.copy(),
    "trilateration_engine": TrilaterationEngine(DEFAULT_ANCHORS_CONFIG),
    "kalman_filter": KalmanFilter2D(dt=1.0, process_noise=0.15, measurement_noise=0.35),
    "last_raw_packets": defaultdict(list),  # anchor -> list of (timestamp, rssi)
    "estimated_distances": {},  # anchor -> estimated_dist
    "last_position": {"x": 0.0, "y": 0.0, "uncertainty": 0.0, "gdop": 0.0},
    "history": [],  # list of {"timestamp": t, "x": x, "y": y}
    "active_connections": []
}


def load_ml_assets():
    """Load model, scaler, and configuration on server startup."""
    model_path = os.path.join(PROJECT_ROOT, "models", "distance_estimator.joblib")
    scaler_path = os.path.join(PROJECT_ROOT, "models", "scaler.joblib")
    meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        logger.warning(
            "⚠️ Trained model or scaler file not found. "
            "Inference will use robust physical path-loss model."
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_ml_assets()
    yield


# Instantiate FastAPI App
app = FastAPI(title="BLE Indoor Positioning Backend", version="1.0", lifespan=lifespan)


# ──────────────────────────────────────────────────────────────────────
#  Pydantic Models
# ──────────────────────────────────────────────────────────────────────

class PacketData(BaseModel):
    timestamp: int
    anchor: str
    mac: str
    rssi: int
    name: str = "BLE_TAG"


class ConfigUpdate(BaseModel):
    anchor_id: str
    x: float
    y: float


# ──────────────────────────────────────────────────────────────────────
#  LIVE DATA STREAM & REAL-TIME LOCALIZATION
# ──────────────────────────────────────────────────────────────────────

def predict_distance_for_anchor(anchor_id: str, rssi_list: List[int], timestamps: List[int]) -> Optional[float]:
    """Helper to perform feature engineering and predict distance."""
    if not rssi_list or len(rssi_list) < 1:
        return None

    try:
        group = pd.DataFrame({
            "rssi": rssi_list,
            "timestamp": timestamps
        })

        features = compute_window_features(group)

        # 1. Model Inference (if model is loaded)
        if state["model"] is not None and state["scaler"] is not None and state["model_metadata"] is not None:
            try:
                feature_cols = state["model_metadata"].get("feature_cols", [])
                if feature_cols and all(col in features for col in feature_cols):
                    X = np.array([[features[col] for col in feature_cols]], dtype=float)
                    if np.all(np.isfinite(X)):
                        X_scaled = state["scaler"].transform(X)
                        pred = float(state["model"].predict(X_scaled)[0])
                        if np.isfinite(pred) and pred > 0:
                            return round(max(0.1, min(25.0, pred)), 3)
            except Exception as e:
                logger.warning(f"ML inference failed for {anchor_id}, falling back to path loss model. Error: {e}")

        # 2. Physical Fallback (Log-distance path loss prior)
        indoor_pl = features.get("path_loss_indoor", 2.0)
        return round(max(0.1, min(25.0, float(indoor_pl))), 3)
    except Exception as e:
        logger.error(f"Distance prediction calculation error for anchor {anchor_id}: {e}")
        return 2.5


def perform_localization():
    """Ties together predicted distances, trilateration, and Kalman filtering safely."""
    try:
        now_ms = int(time.time() * 1000)

        # 1. Process sliding 1.5-second windows of raw packets
        active_distances = {}
        for anchor_id, packets in list(state["last_raw_packets"].items()):
            valid_packets = [(t, r) for (t, r) in packets if (now_ms - t) < 1500]
            state["last_raw_packets"][anchor_id] = valid_packets

            if valid_packets:
                times = [t for (t, _) in valid_packets]
                rssis = [r for (_, r) in valid_packets]
                dist = predict_distance_for_anchor(anchor_id, rssis, times)
                if dist is not None:
                    active_distances[anchor_id] = dist

        state["estimated_distances"] = active_distances

        # 2. Run Trilateration
        pos, uncertainty, gdop = state["trilateration_engine"].estimate_position(active_distances)

        # 3. Kalman trajectory smoothing
        smoothed_x, smoothed_y = state["kalman_filter"].filter(pos[0], pos[1])

        state["last_position"] = {
            "x": round(float(smoothed_x), 3),
            "y": round(float(smoothed_y), 3),
            "uncertainty": float(uncertainty),
            "gdop": float(gdop)
        }

        state["history"].append({
            "timestamp": now_ms,
            "x": round(float(smoothed_x), 3),
            "y": round(float(smoothed_y), 3)
        })

        if len(state["history"]) > 100:
            state["history"].pop(0)

    except Exception as e:
        logger.error(f"Localization engine error: {e}")


# ──────────────────────────────────────────────────────────────────────
#  REST API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────

@app.post("/api/observation")
def add_raw_packet(packet: PacketData):
    """Receives a raw BLE observation packet from an anchor node."""
    try:
        now_ms = int(time.time() * 1000)
        rssi_val = max(-120, min(0, int(packet.rssi)))
        anchor_id = str(packet.anchor).strip()

        if not anchor_id:
            raise HTTPException(status_code=400, detail="Anchor ID cannot be empty.")

        state["last_raw_packets"][anchor_id].append((now_ms, rssi_val))
        perform_localization()

        return {"status": "success", "active_anchors": list(state["last_raw_packets"].keys())}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing packet: {e}")
        raise HTTPException(status_code=500, detail=f"Internal packet processing error: {e}")


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
    try:
        if not (np.isfinite(config.x) and np.isfinite(config.y)):
            raise HTTPException(status_code=400, detail="Coordinates must be finite numeric values.")

        anchor_id = str(config.anchor_id).strip()
        if not anchor_id:
            raise HTTPException(status_code=400, detail="Anchor ID cannot be empty.")

        state["anchors_config"][anchor_id] = (float(config.x), float(config.y))
        state["trilateration_engine"] = TrilaterationEngine(state["anchors_config"])
        logger.info(f"Updated config: {anchor_id} set to ({config.x}, {config.y})")
        return {"status": "success", "anchors": state["anchors_config"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring anchor: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update anchor: {e}")


# ──────────────────────────────────────────────────────────────────────
#  WEBSOCKET REAL-TIME BROADCAST
# ──────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state["active_connections"].append(websocket)
    try:
        while True:
            current_data = {
                "event": "position_update",
                "data": {
                    "position": state["last_position"],
                    "distances": state["estimated_distances"],
                    "history": state["history"]
                }
            }
            await websocket.send_json(current_data)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        if websocket in state["active_connections"]:
            state["active_connections"].remove(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection closed: {e}")
        if websocket in state["active_connections"]:
            state["active_connections"].remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)

