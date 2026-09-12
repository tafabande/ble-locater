"""Indoor Positioning — Administrator Connection & Network Monitor.

Monitors connectivity to backend REST endpoints, WebSocket telemetry streams,
and physical hardware serial COM interfaces.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import BACKEND_URL, WS_URL
from core.ble import list_serial_ports


@dataclass
class ConnectionStatus:
    """Status snapshot of an individual interface connection."""
    target: str
    is_online: bool
    latency_ms: float
    message: str
    last_check_time: float


class ConnectionMonitor:
    """Monitors REST API, WebSocket, and serial port connectivity."""

    def __init__(self, backend_url: str = BACKEND_URL) -> None:
        self.backend_url = backend_url
        self.connection_attempts = 0
        self.failed_attempts = 0

    def ping_backend(self, timeout_sec: float = 2.0) -> ConnectionStatus:
        """Execute an HTTP ping to the backend /api/state endpoint."""
        self.connection_attempts += 1
        t0 = time.time()
        url = f"{self.backend_url}/api/state"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RTLS-AdminMonitor/2.0"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                elapsed_ms = round((time.time() - t0) * 1000, 1)
                data = json.loads(resp.read().decode("utf-8"))
                return ConnectionStatus(
                    target=url,
                    is_online=True,
                    latency_ms=elapsed_ms,
                    message=f"HTTP 200 OK · Tags: {data.get('total_tags', 0)}",
                    last_check_time=time.time(),
                )
        except Exception as e:
            self.failed_attempts += 1
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            return ConnectionStatus(
                target=url,
                is_online=False,
                latency_ms=elapsed_ms,
                message=f"Connection failed: {e}",
                last_check_time=time.time(),
            )

    def scan_serial_interfaces(self) -> List[Dict[str, str]]:
        """List active physical and virtual COM ports."""
        return list_serial_ports()

    def get_connection_statistics(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.connection_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate_pct": round(
                ((self.connection_attempts - self.failed_attempts) / max(1, self.connection_attempts)) * 100, 1
            ),
        }
