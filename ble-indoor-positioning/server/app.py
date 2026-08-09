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

from feature_engineering.engineer import compute_window_features, compute_cross_window_features
from localization.trilateration import TrilaterationEngine, KalmanFilter2D
from learning.calibration_storage import CalibrationStorage
from engineering.geofence_engine import GeofenceEngine

# Logger config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BLE_SERVER")

# ──────────────────────────────────────────────────────────────────────
#  DEFAULT CONFIGURATION & STATE
# ──────────────────────────────────────────────────────────────────────

DEFAULT_ANCHORS_CONFIG = {
    # Room A (Top-Left: X=0..5, Y=5..10) - ICU Bedroom 1
    "ANCHOR_01": (0.2, 5.2),
    "ANCHOR_02": (4.8, 5.2),
    "ANCHOR_03": (2.5, 9.8),
    # Room B (Top-Right: X=5..10, Y=5..10) - Patient Bedroom 2
    "ANCHOR_04": (5.2, 5.2),
    "ANCHOR_05": (9.8, 5.2),
    "ANCHOR_06": (7.5, 9.8),
    # Room C (Bottom-Left: X=0..5, Y=0..5) - Medical Station
    "ANCHOR_07": (0.2, 0.2),
    "ANCHOR_08": (4.8, 0.2),
    "ANCHOR_09": (2.5, 4.8),
    # Room D (Bottom-Right: X=5..10, Y=0..5) - Emergency Ward
    "ANCHOR_10": (5.2, 0.2),
    "ANCHOR_11": (9.8, 0.2),
    "ANCHOR_12": (7.5, 4.8),
}

def resolve_room_name(x: float, y: float) -> str:
    """Resolves 2D coordinates to 4-room hospital floorplan names."""
    if x < 5.0 and y >= 5.0:
        return "Room A (ICU Bedroom 1)"
    elif x >= 5.0 and y >= 5.0:
        return "Room B (Patient Bedroom 2)"
    elif x < 5.0 and y < 5.0:
        return "Room C (Medical Station)"
    else:
        return "Room D (Emergency Ward)"

def resolve_room_name_with_hysteresis(x: float, y: float, current_room: str) -> str:
    """Resolves 2D coordinates to room names with a 0.3m hysteresis margin to prevent boundary flickering."""
    margin = 0.3
    if "Room A" in current_room:
        if x > 5.0 + margin or y < 5.0 - margin: return resolve_room_name(x, y)
        return current_room
    elif "Room B" in current_room:
        if x < 5.0 - margin or y < 5.0 - margin: return resolve_room_name(x, y)
        return current_room
    elif "Room C" in current_room:
        if x > 5.0 + margin or y > 5.0 + margin: return resolve_room_name(x, y)
        return current_room
    elif "Room D" in current_room:
        if x < 5.0 - margin or y > 5.0 + margin: return resolve_room_name(x, y)
        return current_room
    return resolve_room_name(x, y)

class OnlineDistanceLearner:
    """
    Runtime Online Learning & Adaptive Calibrator with Persistent Calibration File Storage.
    Continuously updates path-loss parameters (path-loss exponent eta & distance bias offset)
    using live ground-truth feedback (true_x, true_y or real 5m calibration).
    Performs persistent auto-saving to models/learned_calibrations.json every 100 observations or 60s.
    """
    def __init__(self, learning_rate: float = 0.08, tx_power_1m: float = -77.8):
        self.learning_rate = learning_rate
        self.tx_power_1m = tx_power_1m
        self.anchor_eta = defaultdict(lambda: 2.7)   # anchor -> learned pathloss exp
        self.anchor_bias = defaultdict(float)         # anchor -> learned bias correction in meters
        self.anchor_samples = defaultdict(int)         # anchor -> learned sample count
        self.samples_learned_count = 0
        self.unpersisted_samples = 0
        self.last_save_time = time.time()
        self.mae_accumulator = []
        self.is_active = True
        self.calib_filepath = os.path.join(PROJECT_ROOT, "models", "learned_calibrations.json")
        self.load()

    def load(self):
        """Loads learned calibration parameters via CalibrationStorage."""
        data = CalibrationStorage.load(self.calib_filepath)
        anchors_data = data.get("anchors", {})
        for anc_id, params in anchors_data.items():
            self.anchor_eta[anc_id] = float(params.get("eta", 2.7))
            self.anchor_bias[anc_id] = float(params.get("bias", 0.0))
            self.anchor_samples[anc_id] = int(params.get("samples", 0))
        self.samples_learned_count = int(data.get("total_samples", sum(self.anchor_samples.values())))

    def save(self):
        """Saves current learned calibration parameters via CalibrationStorage."""
        if CalibrationStorage.save(self, self.calib_filepath):
            self.unpersisted_samples = 0
            self.last_save_time = time.time()

    def learn_sample(self, anchor_id: str, rssi: float, true_dist: float, raw_pred_dist: float) -> dict:
        import math
        if true_dist <= 0.05 or not np.isfinite(true_dist):
            return {}

        # 1. Compute empirical path loss exponent from current true distance & RSSI
        log_d = math.log10(max(0.1, true_dist))
        if abs(log_d) > 0.01:
            eta_sample = (self.tx_power_1m - rssi) / (10.0 * log_d)
            eta_sample = max(1.5, min(5.0, eta_sample))
            current_eta = self.anchor_eta[anchor_id]
            self.anchor_eta[anchor_id] = (1.0 - self.learning_rate) * current_eta + self.learning_rate * eta_sample

        # 2. Update distance additive bias (error correction)
        error = true_dist - raw_pred_dist
        current_bias = self.anchor_bias[anchor_id]
        self.anchor_bias[anchor_id] = (1.0 - self.learning_rate) * current_bias + self.learning_rate * error

        self.samples_learned_count += 1
        self.anchor_samples[anchor_id] += 1
        self.unpersisted_samples += 1

        abs_err = abs(error)
        self.mae_accumulator.append(abs_err)
        if len(self.mae_accumulator) > 200:
            self.mae_accumulator.pop(0)

        # Auto-save policy: every 100 observations or 60 seconds
        if self.unpersisted_samples >= 100 or (time.time() - self.last_save_time) >= 60.0:
            self.save()

        return {
            "anchor": anchor_id,
            "true_dist": round(true_dist, 2),
            "raw_pred": round(raw_pred_dist, 2),
            "learned_eta": round(self.anchor_eta[anchor_id], 3),
            "learned_bias": round(self.anchor_bias[anchor_id], 3),
            "samples": self.anchor_samples[anchor_id],
            "current_mae": round(sum(self.mae_accumulator) / max(1, len(self.mae_accumulator)), 3)
        }

    def calibrate_prediction(self, anchor_id: str, raw_pred_dist: float, rssi: float) -> float:
        import math
        eta = self.anchor_eta[anchor_id]
        bias = self.anchor_bias[anchor_id]

        # Physics prediction with learned path loss
        log_term = (self.tx_power_1m - rssi) / (10.0 * max(1.0, eta))
        phys_dist = math.pow(10.0, max(-1.0, min(2.5, log_term)))

        # Weighted blend between (raw_pred + bias) and learned physical model
        calibrated = 0.5 * (raw_pred_dist + bias) + 0.5 * phys_dist
        return max(0.1, min(25.0, calibrated))

    def get_summary(self) -> dict:
        mae = round(sum(self.mae_accumulator) / max(1, len(self.mae_accumulator)), 3) if self.mae_accumulator else 0.0
        avg_eta = round(float(np.mean(list(self.anchor_eta.values()))) if self.anchor_eta else 2.7, 3)
        return {
            "active": self.is_active,
            "samples_learned": self.samples_learned_count,
            "average_learned_pathloss": avg_eta,
            "live_mae_error": mae,
            "learned_biases": {k: round(v, 3) for k, v in self.anchor_bias.items()},
            "anchor_samples": dict(self.anchor_samples)
        }


# GeofenceEngine is imported from engineering.geofence_engine (line 37)


state = {
    "model": None,
    "scaler": None,
    "model_metadata": None,
    "zone_model": None,
    "zone_scaler": None,
    "zone_prediction": "Unknown",
    "current_room": "Room A (ICU Bedroom 1)",
    "anchors_config": DEFAULT_ANCHORS_CONFIG.copy(),
    "trilateration_engine": TrilaterationEngine(DEFAULT_ANCHORS_CONFIG),
    "kalman_filter": KalmanFilter2D(dt=0.1, process_noise=0.05, measurement_noise=0.8),
    "online_learner": OnlineDistanceLearner(),
    "geofence_engine": GeofenceEngine(),
    "alerts": [],          # list of recent alert dicts
    "latest_alert": None,  # most recent alert dict
    "last_raw_packets": defaultdict(list),  # anchor -> list of (timestamp, rssi)
    "anchor_window_history": defaultdict(list), # anchor -> list of feature dicts for cross-window computation
    "estimated_distances": {},  # anchor -> estimated_dist
    "estimated_motions": {},    # anchor -> estimated_motion
    "last_position": {"x": 2.5, "y": 7.5, "uncertainty": 0.0, "gdop": 0.0, "zone": "Unknown", "room": "Room A (ICU Bedroom 1)"},
    "history": [],  # list of {"timestamp": t, "x": x, "y": y}
    "active_connections": []
}


def load_ml_assets():
    """Load model, scaler, and configuration on server startup."""
    model_path = os.path.join(PROJECT_ROOT, "models", "distance_estimator.joblib")
    scaler_path = os.path.join(PROJECT_ROOT, "models", "scaler.joblib")
    meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")
    zone_model_path = os.path.join(PROJECT_ROOT, "models", "zone_classifier.joblib")
    zone_scaler_path = os.path.join(PROJECT_ROOT, "models", "zone_scaler.joblib")

    if os.path.exists(model_path) and os.path.exists(scaler_path):
        try:
            state["model"] = joblib.load(model_path)
            state["scaler"] = joblib.load(scaler_path)
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    state["model_metadata"] = json.load(f)
            logger.info("✅ Champion distance model loaded cleanly.")
        except Exception as e:
            logger.error(f"Failed to load distance model assets: {e}")

    if os.path.exists(zone_model_path) and os.path.exists(zone_scaler_path):
        try:
            state["zone_model"] = joblib.load(zone_model_path)
            state["zone_scaler"] = joblib.load(zone_scaler_path)
            logger.info("✅ Champion zone classifier loaded cleanly.")
        except Exception as e:
            logger.error(f"Failed to load zone classifier assets: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_ml_assets()
    state["online_learner"].load()
    try:
        yield
    finally:
        state["online_learner"].save()


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
    true_x: Optional[float] = None
    true_y: Optional[float] = None


class ConfigUpdate(BaseModel):
    anchor_id: str
    x: float
    y: float


# ──────────────────────────────────────────────────────────────────────
#  LIVE DATA STREAM & REAL-TIME LOCALIZATION
# ──────────────────────────────────────────────────────────────────────

ZONE_BOUNDS = {
    "Very Close (<=0.75m)": (0.10, 0.90),
    "Close (0.75-1.5m)": (0.60, 1.65),
    "Mid (1.5-2.5m)": (1.35, 2.65),
    "Far (2.5-4m)": (2.35, 4.15),
    "Very Far (4m+)": (3.85, 25.0),
}


def predict_distance_for_anchor(anchor_id: str, rssi_list: List[int], timestamps: List[int]) -> Optional[float]:
    """Helper to perform feature engineering, cross-window computation, and hybrid distance prediction."""
    if not rssi_list or len(rssi_list) < 1:
        return None

    try:
        group = pd.DataFrame({
            "rssi": rssi_list,
            "timestamp": timestamps
        })

        features = compute_window_features(group)
        features["window_start"] = int(timestamps[0]) if timestamps else int(time.time() * 1000)

        # Maintain a rolling history buffer of up to 10 windows per anchor
        history = state["anchor_window_history"][anchor_id]
        history.append(features)
        if len(history) > 10:
            history.pop(0)

        # Compute cross-window features if history is available
        hist_df = pd.DataFrame(history)
        hist_df = compute_cross_window_features(hist_df)
        latest_features = hist_df.iloc[-1].to_dict()

        pred_dist = None
        predicted_zone = None

        # 1. Continuous Distance Regressor Inference
        if state["model"] is not None and state["scaler"] is not None and state["model_metadata"] is not None:
            try:
                feature_cols = state["model_metadata"].get("feature_cols", [])
                if feature_cols and all(col in latest_features for col in feature_cols):
                    X = np.array([[latest_features[col] for col in feature_cols]], dtype=float)
                    if np.all(np.isfinite(X)):
                        X_scaled = state["scaler"].transform(X)
                        pred_dist = float(state["model"].predict(X_scaled)[0])
            except Exception as e:
                logger.warning(f"ML continuous distance inference warning for {anchor_id}: {e}")

        # 2. XGBoost Zone Classifier Inference
        if state["zone_model"] is not None and state["model_metadata"] is not None:
            try:
                feature_cols = state["model_metadata"].get("feature_cols", [])
                if feature_cols and all(col in latest_features for col in feature_cols):
                    X_zone = np.array([[latest_features[col] for col in feature_cols]], dtype=float)
                    if np.all(np.isfinite(X_zone)):
                        if state["zone_scaler"] is not None:
                            X_zone = state["zone_scaler"].transform(X_zone)
                        zone_pred = state["zone_model"].predict(X_zone)[0]
                        predicted_zone = str(zone_pred)
            except Exception as e:
                logger.warning(f"Zone classifier inference warning for {anchor_id}: {e}")

        # 3. Hybrid Strategy & Zone Clamping
        if pred_dist is None:
            indoor_pl = features.get("path_loss_indoor", 2.5)
            pred_dist = float(indoor_pl)

        if predicted_zone and predicted_zone in ZONE_BOUNDS:
            z_min, z_max = ZONE_BOUNDS[predicted_zone]
            pred_dist = max(z_min, min(z_max, pred_dist))

        # 4. Apply Online Self-Learning Calibrator
        avg_rssi = float(np.mean(rssi_list))
        calibrated_dist = state["online_learner"].calibrate_prediction(anchor_id, pred_dist, avg_rssi)
        return round(max(0.1, min(25.0, calibrated_dist)), 2)
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
            valid_packets = [(t, r) for (t, r) in packets if (now_ms - t) < 2000]
            state["last_raw_packets"][anchor_id] = valid_packets

            if valid_packets:
                times = [t for (t, _) in valid_packets]
                rssis = [r for (_, r) in valid_packets]
                dist = predict_distance_for_anchor(anchor_id, rssis, times)
                if dist is not None:
                    if anchor_id in state["estimated_distances"]:
                        prev_d = state["estimated_distances"][anchor_id]
                        dist = 0.4 * prev_d + 0.6 * dist
                    active_distances[anchor_id] = round(float(dist), 2)

        state["estimated_distances"] = active_distances

        # 1. Require at least 3 active anchors for robust trilateration
        if len(active_distances) < 3:
            return

        # 2. Select Top 4 Nearest Anchors to eliminate distant wall-attenuated noise
        sorted_anchors = sorted(active_distances.items(), key=lambda item: item[1])
        top_k_distances = dict(sorted_anchors[:4])

        # 3. Run Trilateration on Top 4 nearest anchors
        pos, uncertainty, gdop = state["trilateration_engine"].estimate_position(top_k_distances)

        # 4. Kalman trajectory smoothing
        smoothed_x, smoothed_y = state["kalman_filter"].filter(pos[0], pos[1])

        # 5. XGBoost ML Zone Prediction via majority voting across active anchors
        zone_str = "Unknown"
        if state["zone_model"] is not None and state["model_metadata"] is not None:
            try:
                feature_cols = state["model_metadata"].get("feature_cols", [])
                zone_votes = []
                for anchor_id in active_distances.keys():
                    hist = state["anchor_window_history"].get(anchor_id, [])
                    if hist and feature_cols:
                        latest = hist[-1]
                        if all(col in latest for col in feature_cols):
                            X_z = np.array([[latest[col] for col in feature_cols]], dtype=float)
                            if np.all(np.isfinite(X_z)):
                                if state["zone_scaler"] is not None:
                                    X_z = state["zone_scaler"].transform(X_z)
                                zone_votes.append(str(state["zone_model"].predict(X_z)[0]))
                if zone_votes:
                    from collections import Counter
                    zone_str = Counter(zone_votes).most_common(1)[0][0]
            except Exception as e:
                logger.warning(f"Zone majority voting failed: {e}")
        # Fallback to distance-based heuristic if ML classifier unavailable
        if zone_str == "Unknown":
            dist_from_origin = np.sqrt(smoothed_x**2 + smoothed_y**2)
            if dist_from_origin <= 0.75: zone_str = "Very Close (<=0.75m)"
            elif dist_from_origin <= 1.5: zone_str = "Close (0.75-1.5m)"
            elif dist_from_origin <= 2.5: zone_str = "Mid (1.5-2.5m)"
            elif dist_from_origin <= 4.0: zone_str = "Far (2.5-4m)"
            else: zone_str = "Very Far (4m+)"
        state["zone_prediction"] = zone_str

        # 6. Room resolution with hysteresis & Geofence Alert Evaluation
        prev_room = state["current_room"]
        room_name = resolve_room_name_with_hysteresis(smoothed_x, smoothed_y, prev_room)
        state["current_room"] = room_name

        if prev_room != room_name:
            alert = state["geofence_engine"].evaluate_transition("TAG_01", prev_room, room_name)
            if alert:
                state["alerts"].append(alert)
                if len(state["alerts"]) > 50:
                    state["alerts"].pop(0)
                state["latest_alert"] = alert
                logger.warning(f"🚨 GEOFENCE ALERT: {alert['message']}")

        state["last_position"] = {
            "x": round(float(smoothed_x), 2),
            "y": round(float(smoothed_y), 2),
            "uncertainty": round(float(uncertainty), 2),
            "gdop": round(float(gdop), 2),
            "zone": zone_str,
            "room": room_name
        }

        state["history"].append({
            "timestamp": now_ms,
            "x": round(float(smoothed_x), 2),
            "y": round(float(smoothed_y), 2)
        })

        if len(state["history"]) > 100:
            state["history"].pop(0)

    except Exception as e:
        logger.error(f"Localization engine error: {e}")


# ──────────────────────────────────────────────────────────────────────
#  REST API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────

SYNTHETIC_DATA_PATH = os.path.join(PROJECT_ROOT, "datasets", "synthetic_observations.csv")

@app.post("/api/observation")
def add_raw_packet(packet: PacketData):
    """Receives a single raw BLE observation packet using packet timestamp."""
    try:
        pkt_time = int(packet.timestamp) if packet.timestamp > 0 else int(time.time() * 1000)
        rssi_val = max(-120, min(0, int(packet.rssi)))
        anchor_id = str(packet.anchor).strip()

        if not anchor_id:
            raise HTTPException(status_code=400, detail="Anchor ID cannot be empty.")

        tx = getattr(packet, "true_x", None)
        ty = getattr(packet, "true_y", None)
        if tx is not None and ty is not None:
            file_exists = os.path.exists(SYNTHETIC_DATA_PATH)
            with open(SYNTHETIC_DATA_PATH, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write("timestamp,anchor,mac,rssi,true_x,true_y\n")
                f.write(f"{pkt_time},{anchor_id},{packet.mac},{rssi_val},{tx:.3f},{ty:.3f}\n")

            if anchor_id in state["anchors_config"]:
                ax, ay = state["anchors_config"][anchor_id]
                import math
                true_dist = math.sqrt((tx - ax)**2 + (ty - ay)**2)
                raw_est = state["estimated_distances"].get(anchor_id, true_dist)
                state["online_learner"].learn_sample(anchor_id, rssi_val, true_dist, raw_est)

        state["last_raw_packets"][anchor_id].append((pkt_time, rssi_val))
        perform_localization()

        return {"status": "success", "active_anchors": list(state["last_raw_packets"].keys())}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing packet: {e}")
        raise HTTPException(status_code=500, detail=f"Internal packet processing error: {e}")


@app.post("/api/observation/batch")
def add_raw_packets_batch(packets: List[PacketData]):
    """Receives a BATCH of BLE observation packets in a single HTTP request for 12x performance boost."""
    try:
        for packet in packets:
            pkt_time = int(packet.timestamp) if packet.timestamp > 0 else int(time.time() * 1000)
            rssi_val = max(-120, min(0, int(packet.rssi)))
            anchor_id = str(packet.anchor).strip()
            if anchor_id:
                tx = getattr(packet, "true_x", None)
                ty = getattr(packet, "true_y", None)
                if tx is not None and ty is not None:
                    # Persist synthetic training data to CSV (same as single-packet endpoint)
                    file_exists = os.path.exists(SYNTHETIC_DATA_PATH)
                    with open(SYNTHETIC_DATA_PATH, "a", encoding="utf-8") as f:
                        if not file_exists:
                            f.write("timestamp,anchor,mac,rssi,true_x,true_y\n")
                        f.write(f"{pkt_time},{anchor_id},{packet.mac},{rssi_val},{tx:.3f},{ty:.3f}\n")

                    if anchor_id in state["anchors_config"]:
                        ax, ay = state["anchors_config"][anchor_id]
                        import math
                        true_dist = math.sqrt((tx - ax)**2 + (ty - ay)**2)
                        raw_est = state["estimated_distances"].get(anchor_id, true_dist)
                        state["online_learner"].learn_sample(anchor_id, rssi_val, true_dist, raw_est)

                state["last_raw_packets"][anchor_id].append((pkt_time, rssi_val))

        perform_localization()
        return {"status": "success", "processed": len(packets)}
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise HTTPException(status_code=500, detail=f"Internal batch processing error: {e}")


class DirectLearningInput(BaseModel):
    anchor_id: str
    rssi: float
    true_distance: float


@app.post("/api/learn")
def direct_online_learn(item: DirectLearningInput):
    """Direct ground-truth learning endpoint: system adjusts path-loss and distance bias live from actual distance feedback."""
    try:
        raw_est = state["estimated_distances"].get(item.anchor_id, item.true_distance)
        res = state["online_learner"].learn_sample(item.anchor_id, item.rssi, item.true_distance, raw_est)
        perform_localization()
        return {"status": "learned", "details": res, "summary": state["online_learner"].get_summary()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Online learning update failed: {e}")


@app.get("/api/state")
def get_position_state():
    """Retrieve full location coordinates, estimated distances, history, runtime learning metrics, and geofence alerts."""
    return {
        "position": state["last_position"],
        "distances": state["estimated_distances"],
        "anchors": state["anchors_config"],
        "history": state["history"],
        "zone": state["zone_prediction"],
        "learning": state["online_learner"].get_summary(),
        "alerts": state["alerts"],
        "latest_alert": state["latest_alert"]
    }


@app.get("/api/alerts")
def get_alerts():
    """Retrieve recent geofence room transition alerts."""
    return {
        "alerts": state["alerts"],
        "latest": state["latest_alert"],
        "count": len(state["alerts"])
    }


@app.post("/api/alerts/clear")
def clear_alerts():
    """Clear geofence alert history log."""
    state["alerts"].clear()
    state["latest_alert"] = None
    return {"status": "success", "message": "Alert history cleared."}


@app.get("/api/confidence_heatmap")
def get_confidence_heatmap(step: float = 0.5):
    """
    Computes a 2D spatial grid map of Geometric Dilution of Precision (GDOP)
    and Localization Confidence (%) across floorplan bounds.
    """
    try:
        active_anchors = list(state["estimated_distances"].keys())
        heatmap_data = state["trilateration_engine"].compute_gdop_grid(
            bounds_x=(0.0, 10.0),
            bounds_y=(0.0, 10.0),
            step=max(0.2, min(2.0, step)),
            active_anchors=active_anchors
        )
        return heatmap_data
    except Exception as e:
        logger.error(f"Error computing confidence heatmap: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmap: {e}")



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
    last_sent_alert_time = 0
    try:
        while True:
            current_data = {
                "event": "position_update",
                "data": {
                    "position": state["last_position"],
                    "distances": state["estimated_distances"],
                    "history": state["history"],
                    "zone": state["zone_prediction"],
                    "room": state["current_room"],
                    "alert": state["latest_alert"]
                }
            }
            await websocket.send_json(current_data)
            await asyncio.sleep(0.1)
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

