"""Indoor Positioning — System & Node Telemetry Core.

Maintains technical monitoring data for ESP32 nodes, packet rates,
dropped packets, connection statistics, and host hardware utilization.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class NodeTelemetry:
    """Live telemetry state for a single BLE anchor node."""
    anchor_id: str
    mac_address: str = "Unknown"
    name: str = ""
    status: str = "OFFLINE"  # ONLINE, DEGRADED, OFFLINE
    last_seen: float = 0.0
    packet_count: int = 0
    dropped_packets: int = 0
    rssi_history: List[int] = field(default_factory=list)
    recent_timestamps: List[float] = field(default_factory=list)
    latency_ms: float = 0.0
    battery_pct: Optional[float] = None
    uptime_sec: float = 0.0
    errors: int = 0

    def record_packet(self, rssi: int, timestamp: Optional[float] = None) -> None:
        now = timestamp or time.time()
        self.last_seen = now
        self.packet_count += 1
        self.rssi_history.append(rssi)
        if len(self.rssi_history) > 50:
            self.rssi_history.pop(0)

        self.recent_timestamps.append(now)
        # Keep timestamps from the last 10 seconds for rate calculation
        cutoff = now - 10.0
        self.recent_timestamps = [t for t in self.recent_timestamps if t >= cutoff]
        self.status = "ONLINE"

    def record_drop(self) -> None:
        self.dropped_packets += 1

    @property
    def packet_rate_hz(self) -> float:
        if len(self.recent_timestamps) < 2:
            return 0.0
        duration = self.recent_timestamps[-1] - self.recent_timestamps[0]
        if duration <= 0:
            return 0.0
        return round(len(self.recent_timestamps) / duration, 1)

    @property
    def average_rssi(self) -> float:
        if not self.rssi_history:
            return -100.0
        return round(sum(self.rssi_history) / len(self.rssi_history), 1)

    def refresh_status(self, timeout_sec: float = 5.0) -> str:
        now = time.time()
        if self.last_seen == 0.0:
            self.status = "OFFLINE"
        elif now - self.last_seen > timeout_sec * 2:
            self.status = "OFFLINE"
        elif now - self.last_seen > timeout_sec:
            self.status = "DEGRADED"
        else:
            self.status = "ONLINE"
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        self.refresh_status()
        return {
            "anchor_id": self.anchor_id,
            "mac_address": self.mac_address,
            "name": self.name or self.anchor_id,
            "status": self.status,
            "last_seen_seconds_ago": round(time.time() - self.last_seen, 1) if self.last_seen > 0 else -1,
            "packet_count": self.packet_count,
            "dropped_packets": self.dropped_packets,
            "average_rssi": self.average_rssi,
            "packet_rate_hz": self.packet_rate_hz,
            "latency_ms": self.latency_ms,
            "battery_pct": self.battery_pct,
            "uptime_sec": self.uptime_sec,
            "errors": self.errors,
        }


class SystemTelemetryManager:
    """Aggregates telemetry across all anchors and host system."""

    def __init__(self, anchor_ids: Optional[List[str]] = None) -> None:
        self.nodes: Dict[str, NodeTelemetry] = {}
        if anchor_ids:
            for aid in anchor_ids:
                self.nodes[aid] = NodeTelemetry(anchor_id=aid)

        self.start_time = time.time()
        self.connection_errors = 0
        self.reconnect_attempts = 0
        self.recent_events: List[Dict[str, Any]] = []

    def get_or_create_node(self, anchor_id: str, mac: str = "", name: str = "") -> NodeTelemetry:
        if anchor_id not in self.nodes:
            self.nodes[anchor_id] = NodeTelemetry(
                anchor_id=anchor_id,
                mac_address=mac or "Unknown",
                name=name or anchor_id,
            )
        node = self.nodes[anchor_id]
        if mac and node.mac_address == "Unknown":
            node.mac_address = mac
        if name and not node.name:
            node.name = name
        return node

    def log_event(self, level: str, message: str, source: str = "System") -> None:
        self.recent_events.append({
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "level": level.upper(),
            "message": message,
            "source": source,
        })
        if len(self.recent_events) > 200:
            self.recent_events.pop(0)

    def get_host_resources(self) -> Dict[str, Any]:
        if not HAS_PSUTIL:
            return {"cpu_percent": 0.0, "ram_percent": 0.0, "ram_used_mb": 0.0}
        try:
            vm = psutil.virtual_memory()
            return {
                "cpu_percent": round(psutil.cpu_percent(), 1),
                "ram_percent": round(vm.percent, 1),
                "ram_used_mb": round(vm.used / (1024 * 1024), 1),
                "ram_total_mb": round(vm.total / (1024 * 1024), 1),
            }
        except Exception:
            return {"cpu_percent": 0.0, "ram_percent": 0.0, "ram_used_mb": 0.0}

    def get_full_telemetry(self) -> Dict[str, Any]:
        now = time.time()
        nodes_dict = {}
        online_count = 0
        total_packets = 0
        total_drops = 0

        for aid, node in self.nodes.items():
            status = node.refresh_status()
            if status == "ONLINE":
                online_count += 1
            total_packets += node.packet_count
            total_drops += node.dropped_packets
            nodes_dict[aid] = node.to_dict()

        return {
            "uptime_seconds": round(now - self.start_time, 1),
            "online_nodes": online_count,
            "total_nodes": len(self.nodes),
            "total_packets": total_packets,
            "total_dropped_packets": total_drops,
            "drop_rate_pct": round((total_drops / max(1, total_packets + total_drops)) * 100, 2),
            "host_resources": self.get_host_resources(),
            "nodes": nodes_dict,
            "recent_events": self.recent_events[-50:],
        }
