"""Indoor Positioning — Positioning & Geofence Core.

Integrates multilateration/trilateration, Kalman 2D tracking filters,
geofencing, and room hysteresis.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CORE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from localization.trilateration import TrilaterationEngine, KalmanFilter2D
from engineering.geofence_engine import GeofenceEngine


def resolve_room_name(x: float, y: float) -> str:
    """Resolve metric (x, y) coordinates to human-readable room name."""
    if x < 5.0 and y >= 5.0:
        return "Room A (Executive Suite 1)"
    elif x >= 5.0 and y >= 5.0:
        return "Room B (Meeting Room 2)"
    elif x < 5.0 and y < 5.0:
        return "Room C (Operations Hub)"
    else:
        return "Room D (Main Entrance)"


def resolve_room_name_with_hysteresis(x: float, y: float, current_room: str) -> str:
    """Resolve room with hysteresis buffer to prevent rapid flipping at room boundaries."""
    margin = 0.3
    if "Room A" in current_room:
        if x > 5.0 + margin or y < 5.0 - margin:
            return resolve_room_name(x, y)
        return current_room
    elif "Room B" in current_room:
        if x < 5.0 - margin or y < 5.0 - margin:
            return resolve_room_name(x, y)
        return current_room
    elif "Room C" in current_room:
        if x > 5.0 + margin or y > 5.0 + margin:
            return resolve_room_name(x, y)
        return current_room
    elif "Room D" in current_room:
        if x < 5.0 - margin or y > 5.0 + margin:
            return resolve_room_name(x, y)
        return current_room
    return resolve_room_name(x, y)
