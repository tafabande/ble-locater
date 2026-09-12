"""Indoor Positioning — Data Recording Worker Engine.

Manages background packet ingestion from serial ports or simulated beacon generators,
streaming observations to CSV files and forwarding to the UI queue.
"""
from __future__ import annotations

import math
import queue
import random
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ble import parse_stream_line
from core.data import append_raw_record
from collector.session_manager import SessionConfig
from collector.validation import DataQualityValidator, QualityVerdict


class RecordingEngine:
    """Manages active dataset collection stream and persistence."""

    def __init__(self, packet_queue: queue.Queue[Dict[str, Any]]) -> None:
        self.packet_queue = packet_queue
        self.validator = DataQualityValidator()
        self.is_recording = False
        self.is_streaming = False
        self.active_session: Optional[SessionConfig] = None
        self.sample_count = 0

        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None

    def start_recording(self, session: SessionConfig, port: str) -> None:
        self.active_session = session
        self.is_recording = True
        self.sample_count = 0
        self.validator.reset()
        self.stop_event.clear()

        if not self.is_streaming:
            self.is_streaming = True
            self.worker_thread = threading.Thread(target=self._run_stream, args=(port,), daemon=True)
            self.worker_thread.start()

    def stop_recording(self) -> int:
        self.is_recording = False
        return self.sample_count

    def stop_all(self) -> None:
        self.is_recording = False
        self.is_streaming = False
        self.stop_event.set()

    def _run_stream(self, port: str) -> None:
        while not self.stop_event.is_set():
            if port == "Simulated Stream":
                now = time.time()
                dist = self.active_session.distance_m if self.active_session else 1.0
                # Physics model: RSSI = -59 - 10*2.7*log10(d) + noise
                base_rssi = -59.0 - 27.0 * math.log10(max(0.1, dist))
                sim_rssi = int(round(base_rssi + random.gauss(0, 2.0)))

                anchor_id = (
                    self.active_session.anchor_id
                    if self.active_session and self.active_session.anchor_id != "All Anchors"
                    else f"ANCHOR_{random.randint(1, 4):02d}"
                )
                target_mac = self.active_session.target_mac if self.active_session else "52:06:26:03:01:DA"
                cond = self.active_session.condition if self.active_session else "LOS"

                pkt = {
                    "timestamp": int(now * 1000),
                    "anchor_id": anchor_id,
                    "device_mac": target_mac,
                    "rssi": sim_rssi,
                    "distance": dist,
                    "condition": cond,
                }

                self.validator.add_sample(sim_rssi, now)
                verdict = self.validator.evaluate(dist)
                pkt["quality_verdict"] = verdict

                # Append to CSV if currently recording
                if self.is_recording and self.active_session:
                    self.sample_count += 1
                    append_raw_record(
                        filepath=self.active_session.target_file_path,
                        anchor_id=anchor_id,
                        device_mac=target_mac,
                        rssi=sim_rssi,
                        distance_m=dist,
                        condition=cond,
                        tag_height_m=self.active_session.tag_height_m,
                        notes=self.active_session.notes,
                    )
                    pkt["sample_count"] = self.sample_count

                self.packet_queue.put(pkt)
                time.sleep(0.12)  # ~8 Hz
            else:
                try:
                    import serial
                    with serial.Serial(port, 115200, timeout=1.0) as ser:
                        while not self.stop_event.is_set():
                            raw_line = ser.readline().decode("utf-8", errors="ignore")
                            if raw_line:
                                rec_type, parsed = parse_stream_line(raw_line)
                                if parsed and self.active_session:
                                    now = time.time()
                                    rssi = int(parsed.get("rssi", -80))
                                    dist = self.active_session.distance_m
                                    parsed["distance"] = dist
                                    parsed["condition"] = self.active_session.condition

                                    self.validator.add_sample(rssi, now)
                                    parsed["quality_verdict"] = self.validator.evaluate(dist)

                                    if self.is_recording:
                                        self.sample_count += 1
                                        append_raw_record(
                                            filepath=self.active_session.target_file_path,
                                            anchor_id=parsed.get("anchor_id", "Unknown"),
                                            device_mac=parsed.get("device_mac", "Unknown"),
                                            rssi=rssi,
                                            distance_m=dist,
                                            condition=self.active_session.condition,
                                            tag_height_m=self.active_session.tag_height_m,
                                            notes=self.active_session.notes,
                                            raw_payload=raw_line.strip(),
                                        )
                                        parsed["sample_count"] = self.sample_count

                                    self.packet_queue.put(parsed)
                except Exception:
                    time.sleep(1.0)
