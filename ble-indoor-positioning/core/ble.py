"""Indoor Positioning — BLE Protocols, Packet Parsing & Hardware Detection.

Provides zero-copy parsing of ESP32 sensor streams, serial port enumeration,
and standard data models.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


@dataclass
class RawPacket:
    """Represents a single raw packet received from a node."""
    timestamp_ms: int
    anchor_id: str
    device_mac: str
    rssi: int
    raw_payload: str = ""
    true_x: Optional[float] = None
    true_y: Optional[float] = None


@dataclass
class WindowObservation:
    """Represents a summary observation over a scanning window."""
    timestamp_ms: int
    anchor_id: str
    device_mac: str
    packet_count: int
    scan_duration_ms: int
    rssi_mean: float
    rssi_median: float
    rssi_std: float
    rssi_variance: float
    rssi_min: int
    rssi_max: int
    rssi_range: int
    advertising_interval_ms: float = 100.0


def list_serial_ports() -> List[Dict[str, str]]:
    """Enumerate all available physical and virtual serial ports on the host."""
    if not SERIAL_AVAILABLE:
        return []
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            "device": port.device,
            "description": port.description or "Unknown Serial Device",
            "hwid": port.hwid or "",
        })
    return ports


def parse_stream_line(line: str, anchor_id_override: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Parse an incoming line from a serial port or stdin.
    
    Returns (record_type, parsed_dict) where record_type is:
    - 'observation': A pre-aggregated window observation from an ESP32 anchor
    - 'raw_packet': A single raw RSSI reading
    - None: Unparseable or empty line
    """
    stripped = line.strip()
    if not stripped:
        return None, None

    now_ms = int(time.time() * 1000)

    # Check for JSON payload
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            msg_type = data.get("type", "raw")
            anchor = anchor_id_override or data.get("anchor_id") or data.get("anchor", "Unknown")
            mac = data.get("device_mac") or data.get("mac") or data.get("device", "Unknown")
            ts = data.get("timestamp", now_ms)
            rssi = data.get("rssi", data.get("rssi_mean", -999))

            if msg_type == "observation" or "packet_count" in data:
                return "observation", {
                    "timestamp": ts,
                    "anchor_id": anchor,
                    "device_mac": mac,
                    "packet_count": int(data.get("packet_count", 1)),
                    "scan_duration_ms": int(data.get("scan_duration_ms", 1000)),
                    "rssi_mean": float(data.get("rssi_mean", rssi)),
                    "rssi_median": float(data.get("rssi_median", rssi)),
                    "rssi_std": float(data.get("rssi_std", 0.0)),
                    "rssi_variance": float(data.get("rssi_variance", 0.0)),
                    "rssi_min": int(data.get("rssi_min", rssi)),
                    "rssi_max": int(data.get("rssi_max", rssi)),
                    "rssi_range": int(data.get("rssi_range", 0)),
                }

            return "raw_packet", {
                "timestamp": ts,
                "anchor_id": anchor,
                "device_mac": mac,
                "rssi": int(rssi) if rssi != -999 else -80,
                "raw_payload": stripped,
            }
        except Exception:
            pass

    # Check for CSV format: timestamp,anchor,mac,rssi[,true_x,true_y]
    parts = [p.strip() for p in stripped.split(",")]
    if len(parts) >= 4:
        try:
            ts = int(float(parts[0])) if parts[0].replace(".", "").isdigit() else now_ms
            anchor = anchor_id_override or parts[1]
            mac = parts[2]
            rssi = int(float(parts[3]))
            tx = float(parts[4]) if len(parts) > 5 and parts[4] != "" else None
            ty = float(parts[5]) if len(parts) > 5 and parts[5] != "" else None

            return "raw_packet", {
                "timestamp": ts,
                "anchor_id": anchor,
                "device_mac": mac,
                "rssi": rssi,
                "true_x": tx,
                "true_y": ty,
                "raw_payload": stripped,
            }
        except Exception:
            pass

    return None, None


def calculate_log_distance(rssi: float, tx_power_1m: float = -59.0, path_loss_exponent: float = 2.7) -> float:
    """Calculate distance in meters from RSSI using standard log-distance path loss."""
    if rssi >= 0 or math.isnan(rssi):
        return 0.1
    exponent = (tx_power_1m - rssi) / (10.0 * path_loss_exponent)
    distance = 10.0 ** exponent
    return max(0.1, min(30.0, distance))
