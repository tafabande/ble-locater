"""Indoor Positioning — Data Recording Worker Engine.

Manages background packet ingestion from real physical ESP32 nodes via wireless Wi-Fi UDP
and serial COM ports, streaming observations to canonical raw CSV datasets and forwarding
telemetry to the UI queue. Strictly real hardware data with zero synthetic simulation.
Supports 4-anchor multi-receiver acquisition, stabilization, pause/resume, and safe flushing.
"""
from __future__ import annotations

import csv
import json
import math
import queue
import random
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ble import parse_stream_line
from core.config import get_experiment_receiver_ip, load_anchor_config
from collector.session_manager import SessionConfig, CANONICAL_RAW_HEADERS
from collector.validation import DataQualityValidator, QualityVerdict
from collector.node_registry import get_node_by_mac, get_node_by_anchor_id, load_node_registry


class RecordingEngine:
    """Manages active dataset collection stream, 4-anchor multi-receiver ingestion, and persistence."""

    def __init__(self, packet_queue: queue.Queue[Dict[str, Any]]) -> None:
        self.packet_queue = packet_queue
        self.validator = DataQualityValidator()

        # State flags
        self.is_streaming = False
        self.is_stabilizing = False
        self.is_recording = False
        self.is_paused = False

        self.active_session: Optional[SessionConfig] = None
        self.port: str = "Wireless Wi-Fi (UDP :5005)"
        self.baud_rate: int = 115200

        # Metrics & Counters
        self.raw_packets_count = 0
        self.valid_samples_count = 0
        self.flagged_samples_count = 0
        self.anchor_sample_counts: Dict[str, int] = {f"ANCHOR_{i:02d}": 0 for i in range(1, 5)}
        self.start_record_time: float = 0.0
        self.total_paused_time: float = 0.0
        self.pause_start_time: float = 0.0

        # Thread management
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.file_lock = threading.Lock()
        self.file_handle = None
        self.csv_writer = None
        # The immutable primary record.  Parsed CSV rows are a compatibility
        # view only; this stream is the exact payload sent by each node.
        self.verbatim_file_handle = None
        self.verbatim_file_path: Optional[Path] = None

        # Wireless UDP and 4-Corner Node Synchronization
        self.udp_port = 5005
        self.udp_socket: Optional[socket.socket] = None
        self.experiment_receiver_ip: str = ""
        self.node_health: Dict[str, Dict[str, Any]] = {
            "NODE_A": {"online": False, "last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""},
            "NODE_B": {"online": False, "last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""},
            "NODE_C": {"online": False, "last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""},
            "NODE_D": {"online": False, "last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""},
        }
        self.inter_anchor_matrix: Dict[str, Dict[str, Any]] = {
            "NODE_A": {},
            "NODE_B": {},
            "NODE_C": {},
            "NODE_D": {},
        }
        self.announce_thread: Optional[threading.Thread] = None
        self.node_identity_conflicts: Dict[str, int] = {}

        # Decoupled HTTP telemetry forwarder to FastAPI backend
        self._http_forward_queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=1000)
        self._http_forward_url: str = "http://127.0.0.1:8000/api/telemetry/ingest"
        self._http_forward_thread: Optional[threading.Thread] = None

    def _start_http_forwarder(self) -> None:
        """Start the background forwarder worker if not already running."""
        if self._http_forward_thread is None or not self._http_forward_thread.is_alive():
            self._http_forward_thread = threading.Thread(target=self._http_forward_worker, daemon=True)
            self._http_forward_thread.start()

    def _http_forward_worker(self) -> None:
        """Asynchronously push telemetry to FastAPI without blocking local recording.
        Completely decoupled: failure or offline status of FastAPI never impacts data collection.
        """
        import urllib.request
        while not self.stop_event.is_set():
            try:
                payload = self._http_forward_queue.get(timeout=0.5)
            except Exception:
                continue
            try:
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self._http_forward_url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "CollectorEngine"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=1.0) as _:
                    pass
            except Exception:
                # FastAPI server down or unreachable — silently ignore
                pass

    def _enqueue_http_forward(self, payload: Dict[str, Any]) -> None:
        """Non-blocking fire-and-forget enqueue of telemetry payload."""
        try:
            self._http_forward_queue.put_nowait(payload)
        except Exception:
            pass

    def start_stream(self, port: str = "Wireless Wi-Fi (UDP :5005)", baud_rate: int = 115200) -> None:
        """Start streaming live packets without recording to disk."""
        self.port = port
        self.baud_rate = baud_rate
        self._start_http_forwarder()
        if not self.is_streaming:
            self.is_streaming = True
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._run_stream, daemon=True)
            self.worker_thread.start()

    def start_stabilization(self, session: SessionConfig, port: str = "Wireless Wi-Fi (UDP :5005)") -> None:
        """Initiate pre-recording stabilization countdown."""
        self.active_session = session
        self.port = port
        self.is_stabilizing = True
        self.is_recording = False
        self.is_paused = False
        self.start_stream(port)

    def start_recording(self, session: SessionConfig, port: str = "Wireless Wi-Fi (UDP :5005)") -> None:
        """Start formal dataset recording to disk."""
        self.active_session = session
        self.port = port
        self.is_stabilizing = False
        self.is_recording = True
        self.is_paused = False

        self.raw_packets_count = 0
        self.valid_samples_count = 0
        self.flagged_samples_count = 0
        self.anchor_sample_counts = {f"ANCHOR_{i:02d}": 0 for i in range(1, 5)}
        self.start_record_time = time.time()
        self.total_paused_time = 0.0

        self.validator.reset()

        # Open file handle for streaming append
        with self.file_lock:
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception:
                    pass
            session.target_file_path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure headers exist
            if not session.target_file_path.exists() or session.target_file_path.stat().st_size == 0:
                with open(session.target_file_path, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(CANONICAL_RAW_HEADERS)

            self.file_handle = open(session.target_file_path, "a", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.file_handle)
            self.verbatim_file_path = session.verbatim_capture_file_path
            self.verbatim_file_handle = open(self.verbatim_file_path, "ab")

        self.start_stream(port)

    def pause_recording(self) -> None:
        """Pause writing observations to disk."""
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self.pause_start_time = time.time()

    def resume_recording(self) -> None:
        """Resume writing observations to disk."""
        if self.is_recording and self.is_paused:
            self.is_paused = False
            self.total_paused_time += (time.time() - self.pause_start_time)

    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording, flush file buffer, and calculate final summary statistics."""
        self.is_recording = False
        self.is_stabilizing = False
        self.is_paused = False

        duration_sec = 0.0
        if self.start_record_time > 0:
            duration_sec = max(0.1, (time.time() - self.start_record_time) - self.total_paused_time)

        # Safely flush and close file
        with self.file_lock:
            if self.file_handle:
                try:
                    self.file_handle.flush()
                    self.file_handle.close()
                except Exception:
                    pass
                self.file_handle = None
                self.csv_writer = None
            if self.verbatim_file_handle:
                try:
                    self.verbatim_file_handle.flush()
                    self.verbatim_file_handle.close()
                except Exception:
                    pass
                self.verbatim_file_handle = None

        rate_hz = round(self.valid_samples_count / duration_sec, 2) if duration_sec > 0 else 0.0
        dist = self.active_session.distance_m if self.active_session else 1.0
        verdict = self.validator.evaluate(dist)

        summary = {
            "total_samples": self.valid_samples_count,
            "raw_packets": self.raw_packets_count,
            "flagged_samples": self.flagged_samples_count,
            "anchor_counts": dict(self.anchor_sample_counts),
            "duration_sec": round(duration_sec, 1),
            "average_rate_hz": rate_hz,
            "mean_rssi": verdict.mean_rssi,
            "std_rssi": verdict.std_rssi,
            "quality_status": verdict.status,
            "quality_message": verdict.message,
        }

        # Finalize metadata companion if active session exists
        if self.active_session:
            self.active_session.save_metadata(
                sample_count=self.valid_samples_count,
                duration_sec=duration_sec,
                stats=summary,
            )

        return summary

    def stop_all(self) -> None:
        """Completely shut down streaming workers and close handles."""
        self.is_recording = False
        self.is_streaming = False
        self.is_stabilizing = False
        self.is_paused = False
        self.stop_event.set()

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception:
                pass
            self.udp_socket = None

        with self.file_lock:
            if self.file_handle:
                try:
                    self.file_handle.flush()
                    self.file_handle.close()
                except Exception:
                    pass
                self.file_handle = None
            if self.verbatim_file_handle:
                try:
                    self.verbatim_file_handle.flush()
                    self.verbatim_file_handle.close()
                except Exception:
                    pass
                self.verbatim_file_handle = None

    def append_verbatim_payload(self, payload: bytes) -> None:
        """Append a received node payload unchanged to the session's primary raw log."""
        if not self.is_recording or self.is_paused:
            return
        with self.file_lock:
            if self.verbatim_file_handle:
                try:
                    self.verbatim_file_handle.write(payload)
                    if not payload.endswith(b"\n"):
                        self.verbatim_file_handle.write(b"\n")
                    self.verbatim_file_handle.flush()
                except Exception:
                    pass

    def get_inter_anchor_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Return real-time peer anchor link quality and RSSI values."""
        now = time.time()
        matrix: Dict[str, Dict[str, Any]] = {}
        for fn in ("NODE_A", "NODE_B", "NODE_C", "NODE_D"):
            matrix[fn] = {}
            for tn, info in self.inter_anchor_matrix.get(fn, {}).items():
                matrix[fn][tn] = {
                    "rssi": info["rssi"],
                    "active": (now - info["last_seen"]) < 8.0,
                    "last_seen_sec": round(now - info["last_seen"], 1),
                }
        return matrix

    def get_nodes_sync_status(self) -> Dict[str, Any]:
        """Check live online and synchronization status of all 4 ESP32 wireless nodes."""
        now = time.time()
        online_count = 0
        nodes_status = {}
        registry = load_node_registry()
        for k in ("NODE_A", "NODE_B", "NODE_C", "NODE_D"):
            h = self.node_health.get(k, {})
            last_seen = h.get("last_seen", 0.0)
            is_online = (now - last_seen) < 7.0 if last_seen > 0 else False
            h["online"] = is_online
            if is_online:
                online_count += 1
            reg_info = registry.get(k, {})
            mac_addr = h.get("mac") or reg_info.get("mac") or "Unassigned"
            is_locked = bool(reg_info.get("locked", False))
            is_configured = bool(mac_addr and mac_addr.upper() != "UNASSIGNED" and len(mac_addr) == 17)
            nodes_status[k] = {
                "node_key": k,
                "anchor_id": reg_info.get("anchor_id", f"ANCHOR_0{ord(k[-1]) - ord('A') + 1}"),
                "corner": reg_info.get("corner", ""),
                "display_name": reg_info.get("display_name", k),
                "online": is_online,
                "configured": is_configured,
                "locked": is_locked,
                "mac": mac_addr,
                "rssi": h.get("rssi", -99),
                "packets": h.get("packets", 0),
                "ip": h.get("ip", ""),
                "last_seen_sec": round(now - last_seen, 1) if last_seen > 0 else 999.0,
                "last_flashed": reg_info.get("last_flashed"),
            }
        configured_count = sum(1 for n in nodes_status.values() if n["configured"])
        return {
            "online_count": online_count,
            "configured_count": configured_count,
            "total_count": 4,
            "in_sync": (online_count == 4),
            "nodes": nodes_status,
            "inter_anchor": self.get_inter_anchor_matrix(),
        }

    def feed_packet(self, data: Dict[str, Any]) -> None:
        """Feed external physical hardware packet into active recording session on demand."""
        provenance = str(data.get("provenance", "HARDWARE_WIFI_UDP"))
        if "simulat" in provenance.lower() or "synthetic" in provenance.lower():
            # Refuse synthetic or simulated packets to maintain strict physical dataset integrity
            return

        now = time.time()
        ts_ms = data.get("timestamp") or int(now * 1000)
        anchor_id = data.get("anchor_id") or data.get("anchor", "ANCHOR_01")
        target_mac = data.get("device_mac") or data.get("mac", "Unknown")
        rssi = int(data.get("rssi", -70))

        dist = self.active_session.distance_m if self.active_session else 1.0
        cond = self.active_session.condition if self.active_session else "Line-of-Sight (LOS)"
        obs = self.active_session.obstacle if self.active_session else "No"
        obs_type = self.active_session.obstacle_type if self.active_session else "None"
        motion = self.active_session.motion if self.active_session else "stationary"
        height = self.active_session.tag_height_m if self.active_session else 0.96

        if self.active_session and self.active_session.environment_layout:
            try:
                from collector.environment import EnvironmentLayout
                layout = EnvironmentLayout.from_dict(self.active_session.environment_layout)
                distances = layout.get_anchor_distances()
                if anchor_id in distances:
                    dist = round(distances[anchor_id], 3)
                los_status = layout.get_anchor_los_status()
                if anchor_id in los_status:
                    is_los, blocker = los_status[anchor_id]
                    if not is_los and blocker:
                        cond = "Non-Line-of-Sight (NLOS)"
                        obs = "Yes"
                        obs_type = blocker
                    else:
                        cond = "Line-of-Sight (LOS)"
                        obs = "No"
                        obs_type = "None"
            except Exception:
                pass

        self.validator.add_sample(rssi, now, anchor_id=anchor_id)
        verdict = self.validator.evaluate(dist, anchor_id=anchor_id)
        self.raw_packets_count += 1

        if self.is_recording and not self.is_paused and self.active_session:
            if verdict.is_acceptable:
                self.valid_samples_count += 1
            else:
                self.flagged_samples_count += 1

            self.anchor_sample_counts[anchor_id] = self.anchor_sample_counts.get(anchor_id, 0) + 1
            row = [
                ts_ms,
                anchor_id,
                target_mac,
                rssi,
                f"API_{provenance}",
                dist,
                obs,
                obs_type,
                height,
                motion,
            ]
            with self.file_lock:
                if self.csv_writer:
                    try:
                        self.csv_writer.writerow(row)
                        self.file_handle.flush()
                    except Exception:
                        pass

        pkt = {
            "timestamp": ts_ms,
            "provenance": provenance,
            "anchor_id": anchor_id,
            "device_mac": target_mac,
            "rssi": rssi,
            "distance_m": dist,
            "condition": cond,
            "obstacle_type": obs_type,
            "quality_verdict": verdict,
            "raw_packets": self.raw_packets_count,
            "valid_samples": self.valid_samples_count,
            "flagged_samples": self.flagged_samples_count,
            "anchor_counts": dict(self.anchor_sample_counts),
            "sync_status": self.get_nodes_sync_status(),
        }
        self.packet_queue.put(pkt)

    def _run_stream(self) -> None:
        """Main background ingestion worker for physical hardware.
        Always runs UDP port 5005 listener in background so wireless packets are never missed,
        and runs serial COM reader in parallel if a physical COM port is selected.
        """
        port_lower = self.port.lower()
        if "simulat" in port_lower:
            print("[COLLECTOR ERROR] Simulation sources are permanently removed. Physical ESP32 hardware must be connected via UDP (port 5005) or Serial COM port.")
            self.stop_event.set()
            return

        # Always start wireless UDP 5005 ingestion worker thread
        self.udp_thread = threading.Thread(target=self._run_udp_stream, daemon=True)
        self.udp_thread.start()

        # If a physical COM port is chosen, run serial stream in this worker
        if "udp" not in port_lower and "wireless" not in port_lower:
            while not self.stop_event.is_set():
                self._run_serial_stream()
        else:
            # Pure wireless mode: wait on stop event
            while not self.stop_event.is_set():
                time.sleep(0.5)

    def _collector_announce_worker(self) -> None:
        """Advertise only on the laptop's dedicated experimental hotspot LAN.

        Binding each announce socket to the hotspot address prevents Windows
        from routing a broadcast through a concurrently connected Internet
        Wi-Fi network. ESP32s therefore always learn the hotspot receiver IP.
        """
        hotspot_missing_reported = False
        while not self.stop_event.is_set():
            host_ip = get_experiment_receiver_ip()
            self.experiment_receiver_ip = host_ip
            if not host_ip:
                if not hotspot_missing_reported:
                    print("[COLLECTOR NETWORK] Mobile Hotspot is not active; waiting for the experimental LAN.")
                    hotspot_missing_reported = True
                self.stop_event.wait(2.5)
                continue

            hotspot_missing_reported = False
            payload = json.dumps({
                "cmd": "COLLECTOR_ANNOUNCE",
                "host_ip": host_ip,
                "port": self.udp_port,
                "timestamp": int(time.time() * 1000),
            }).encode("utf-8")
            broadcast_ip = f"{host_ip.rsplit('.', 1)[0]}.255"

            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind((host_ip, 0))
                sock.sendto(payload, (broadcast_ip, self.udp_port))
            except OSError as exc:
                print(f"[COLLECTOR NETWORK] Hotspot discovery announcement failed: {exc}")
            finally:
                if sock:
                    sock.close()

            self.stop_event.wait(2.5)

    def _run_udp_stream(self) -> None:
        """Ingest ESP32 UDP telemetry from the dedicated hotspot LAN on port 5005."""
        sock = None
        try:
            self.experiment_receiver_ip = get_experiment_receiver_ip()
            bind_ip = self.experiment_receiver_ip or "0.0.0.0"
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Do not enable SO_REUSEADDR here. On Windows, sharing a UDP port
            # can make datagram delivery non-deterministic; Collector must be
            # the one exclusive receiver for the experimental port.
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except Exception:
                pass
            # Bind directly to the Mobile Hotspot interface when it is active.
            # On a multi-homed Windows laptop this avoids packets being
            # associated with the Internet-facing Wi-Fi adapter instead.
            sock.bind((bind_ip, self.udp_port))
            sock.settimeout(0.2)
            self.udp_socket = sock
            if not self.experiment_receiver_ip:
                print("[COLLECTOR NETWORK] No Mobile Hotspot adapter detected; UDP listener is idle until it is enabled.")
            else:
                print(f"[COLLECTOR NETWORK] Listening for ESP32 telemetry on {bind_ip}:{self.udp_port}")

            # Start Dynamic Laptop IP Announcement Beacon in background
            self.announce_thread = threading.Thread(target=self._collector_announce_worker, daemon=True)
            self.announce_thread.start()

            while not self.stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(4096)
                    self.append_verbatim_payload(data)
                    line = data.decode("utf-8", errors="replace")
                    if line:
                        self._process_incoming_wireless_packet(line, addr[0])
                except socket.timeout:
                    continue
                except Exception:
                    time.sleep(0.02)
        except Exception as e:
            print(f"[ERROR] UDP stream listener error on port {self.udp_port}: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            self.udp_socket = None

    def _process_incoming_wireless_packet(self, raw_line: str, sender_ip: str) -> None:
        """Process a raw JSON or CSV packet arriving wirelessly over Wi-Fi UDP."""
        try:
            now = time.time()
            ts_ms = int(now * 1000)

            # 1. Parse JSON telemetry
            if raw_line.startswith("{") and raw_line.endswith("}"):
                try:
                    data = json.loads(raw_line)
                except Exception:
                    return

            # Guard: the collector's own announce beacon loops back on the
            # local host (Windows delivers 255.255.255.255 broadcasts to the
            # sender). Ingesting it would fabricate NODE_A observations.
            if data.get("cmd") == "COLLECTOR_ANNOUNCE":
                return

            # Message type resolution (fallback to 'raw' if node/anchor identifier is present)
            msg_type = data.get("type", "raw" if ("node" in data or "anchor" in data or "anchor_id" in data) else None)
            if not msg_type:
                return

            provenance = data.get("provenance", "HARDWARE_WIFI_UDP")
            node_identifier = data.get("node") or data.get("anchor") or data.get("anchor_id", "NODE_A")
            dev_mac = data.get("mac", "")

            # Inter-Anchor Telemetry Handling (Anchor-to-Anchor Mesh Detection)
            if msg_type == "inter_anchor":
                from_node = data.get("from_node", node_identifier)
                to_node = data.get("to_node", "Unknown")
                rssi = int(data.get("rssi", -99))
                if from_node in self.inter_anchor_matrix:
                    self.inter_anchor_matrix[from_node][to_node] = {
                        "rssi": rssi,
                        "last_seen": now,
                        "mac": data.get("to_mac", ""),
                    }
                pkt = {
                    "packet_type": "inter_anchor",
                    "provenance": provenance,
                    "timestamp": ts_ms,
                    "from_node": from_node,
                    "to_node": to_node,
                    "rssi": rssi,
                    "inter_anchor_matrix": self.get_inter_anchor_matrix(),
                    "sync_status": self.get_nodes_sync_status(),
                }
                self.packet_queue.put(pkt)
                return

            # Zero-Config Discovery Handshake Handling
            if msg_type == "discovery_ack":
                node_k = data.get("node", "NODE_A")
                if dev_mac:
                    mac_res = get_node_by_mac(dev_mac)
                    if mac_res:
                        node_k = mac_res[0]
                if node_k in self.node_health:
                    self.node_health[node_k]["online"] = True
                    self.node_health[node_k]["last_seen"] = now
                    self.node_health[node_k]["ip"] = sender_ip
                    self.node_health[node_k]["mac"] = data.get("mac", "")
                return

            # Resolve node identity. The hardware silicon MAC is the source of
            # truth: a board whose MAC is bound in the registry is attributed
            # to that node even if its firmware claims a different node ID.
            node_key = "NODE_A"
            anchor_id = "ANCHOR_01"
            claimed_res = get_node_by_anchor_id(node_identifier)
            # Silicon MAC is the primary source of truth:
            mac_res = get_node_by_mac(dev_mac) if dev_mac else None
            res = mac_res or claimed_res
            if res:
                node_key, info = res
                anchor_id = info.get("anchor_id", f"ANCHOR_{ord(node_key[-1]) - ord('A') + 1:02d}")
                if dev_mac and claimed_res and claimed_res[0] != node_key:
                    self.node_identity_conflicts[node_key] = self.node_identity_conflicts.get(node_key, 0) + 1
            elif node_identifier.upper() in ("NODE_A", "NODE_B", "NODE_C", "NODE_D"):
                node_key = node_identifier.upper()
                anchor_id = f"ANCHOR_{ord(node_key[-1]) - ord('A') + 1:02d}"

            # Heartbeat handling
            if msg_type == "heartbeat":
                if node_key in self.node_health:
                    self.node_health[node_key]["online"] = True
                    self.node_health[node_key]["last_seen"] = now
                    self.node_health[node_key]["ip"] = sender_ip
                    self.node_health[node_key]["mac"] = dev_mac
                # Forward to FastAPI backend (fire-and-forget, decoupled)
                self._enqueue_http_forward({
                    "timestamp": ts_ms,
                    "anchor_id": anchor_id,
                    "device_mac": "None",
                    "rssi": -50,
                    "provenance": "HARDWARE_HEARTBEAT",
                    "raw_payload": f"HEARTBEAT {node_key}",
                    "ip": sender_ip,
                    "anchor_mac": dev_mac,
                })
                # Immediately inform Collector GUI of heartbeat
                pkt = {
                    "packet_type": "heartbeat",
                    "provenance": provenance,
                    "timestamp": ts_ms,
                    "anchor_id": anchor_id,
                    "node_key": node_key,
                    "anchor_mac": dev_mac or self.node_health.get(node_key, {}).get("mac", ""),
                    "sync_status": self.get_nodes_sync_status(),
                }
                self.packet_queue.put(pkt)
                return

            # Observation handling
            rssi = int(data.get("rssi") or data.get("rssi_mean") or data.get("wifi_rssi") or -75)
            target_mac = data.get("tag") or data.get("device_mac") or (self.active_session.target_mac if self.active_session else "Unknown")

            # Update node health
            if node_key in self.node_health:
                self.node_health[node_key]["online"] = True
                self.node_health[node_key]["last_seen"] = now
                self.node_health[node_key]["rssi"] = rssi
                self.node_health[node_key]["packets"] = self.node_health[node_key].get("packets", 0) + 1
                self.node_health[node_key]["ip"] = sender_ip
                if dev_mac:
                    self.node_health[node_key]["mac"] = dev_mac

            dist = self.active_session.distance_m if self.active_session else 1.0
            cond = self.active_session.condition if self.active_session else "Line-of-Sight (LOS)"
            obs = self.active_session.obstacle if self.active_session else "No"
            obs_type = self.active_session.obstacle_type if self.active_session else "None"
            motion = self.active_session.motion if self.active_session else "stationary"
            height = self.active_session.tag_height_m if self.active_session else 0.96

            # Raycast distance and LOS check from 2D visual layout
            if self.active_session and self.active_session.environment_layout:
                try:
                    from collector.environment import EnvironmentLayout
                    layout = EnvironmentLayout.from_dict(self.active_session.environment_layout)
                    distances = layout.get_anchor_distances()
                    if anchor_id in distances:
                        dist = round(distances[anchor_id], 3)
                    los_status = layout.get_anchor_los_status()
                    if anchor_id in los_status:
                        is_los, blocker = los_status[anchor_id]
                        if not is_los and blocker:
                            cond = "Non-Line-of-Sight (NLOS)"
                            obs = "Yes"
                            obs_type = blocker
                        else:
                            cond = "Line-of-Sight (LOS)"
                            obs = "No"
                            obs_type = "None"
                except Exception:
                    pass

            self.validator.add_sample(rssi, now, anchor_id=anchor_id)
            verdict = self.validator.evaluate(dist, anchor_id=anchor_id)
            self.raw_packets_count += 1

            if self.is_recording and not self.is_paused and self.active_session:
                if verdict.is_acceptable:
                    self.valid_samples_count += 1
                else:
                    self.flagged_samples_count += 1

                self.anchor_sample_counts[anchor_id] = self.anchor_sample_counts.get(anchor_id, 0) + 1

                row = [
                    ts_ms,
                    anchor_id,
                    target_mac,
                    rssi,
                    f"WIFI_UDP_{node_key}",
                    dist,
                    obs,
                    obs_type,
                    height,
                    motion,
                ]
                with self.file_lock:
                    if self.csv_writer:
                        try:
                            self.csv_writer.writerow(row)
                            self.file_handle.flush()
                        except Exception:
                            pass

            pkt = {
                "timestamp": ts_ms,
                "provenance": provenance,
                "anchor_id": anchor_id,
                "node_key": node_key,
                "anchor_mac": dev_mac or self.node_health[node_key].get("mac", ""),
                "device_mac": target_mac,
                "rssi": rssi,
                "distance_m": dist,
                "condition": cond,
                "obstacle_type": obs_type,
                "quality_verdict": verdict,
                "raw_packets": self.raw_packets_count,
                "valid_samples": self.valid_samples_count,
                "flagged_samples": self.flagged_samples_count,
                "anchor_counts": dict(self.anchor_sample_counts),
                "sync_status": self.get_nodes_sync_status(),
            }
            self.packet_queue.put(pkt)

            # Forward wireless observation to FastAPI backend (fire-and-forget)
            self._enqueue_http_forward({
                "timestamp": ts_ms,
                "anchor_id": anchor_id,
                "device_mac": target_mac,
                "rssi": rssi,
                "provenance": provenance,
                "raw_payload": raw_line[:128],
                "ip": sender_ip,
                "anchor_mac": dev_mac or self.node_health.get(node_key, {}).get("mac", ""),
            })
        except Exception:
            pass



    def _run_serial_stream(self) -> None:
        """Ingest from physical serial hardware COM port."""
        try:
            import serial
            with serial.Serial(self.port, self.baud_rate, timeout=1.0) as ser:
                while not self.stop_event.is_set():
                    raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not raw_line:
                        continue

                    rec_type, parsed = parse_stream_line(raw_line)
                    if not parsed:
                        continue

                    now = time.time()
                    ts_ms = int(now * 1000)
                    dist = self.active_session.distance_m if self.active_session else 1.0
                    rssi = int(parsed.get("rssi", -80))
                    anchor_id = parsed.get("anchor_id", "ANCHOR_01").strip().upper()
                    target_mac = parsed.get("device_mac") or (self.active_session.target_mac if self.active_session else "Unknown")
                    obs = self.active_session.obstacle if self.active_session else "No"
                    obs_type = self.active_session.obstacle_type if self.active_session else "None"
                    cond = self.active_session.condition if self.active_session else "Line-of-Sight (LOS)"
                    motion = self.active_session.motion if self.active_session else "stationary"
                    height = self.active_session.tag_height_m if self.active_session else 0.96

                    # Resolve node in registry and update live node health
                    res = get_node_by_anchor_id(anchor_id) or (get_node_by_mac(target_mac) if target_mac else None)
                    node_key = res[0] if res else ("NODE_A" if "1" in anchor_id else "NODE_B" if "2" in anchor_id else "NODE_C" if "3" in anchor_id else "NODE_D")
                    if node_key in self.node_health:
                        self.node_health[node_key]["online"] = True
                        self.node_health[node_key]["last_seen"] = now
                        self.node_health[node_key]["rssi"] = rssi
                        self.node_health[node_key]["packets"] = self.node_health[node_key].get("packets", 0) + 1

                    # Check if active session includes an environment layout for dynamic ground-truth
                    if self.active_session and self.active_session.environment_layout:
                        try:
                            from collector.environment import EnvironmentLayout
                            layout = EnvironmentLayout.from_dict(self.active_session.environment_layout)
                            distances = layout.get_anchor_distances()
                            if anchor_id in distances:
                                dist = round(distances[anchor_id], 3)
                            los_status = layout.get_anchor_los_status()
                            if anchor_id in los_status:
                                is_los, blocker = los_status[anchor_id]
                                if not is_los and blocker:
                                    cond = "Non-Line-of-Sight (NLOS)"
                                    obs = "Yes"
                                    obs_type = blocker
                                else:
                                    cond = "Line-of-Sight (LOS)"
                                    obs = "No"
                                    obs_type = "None"
                        except Exception:
                            pass

                    self.validator.add_sample(rssi, now, anchor_id=anchor_id)
                    verdict = self.validator.evaluate(dist, anchor_id=anchor_id)

                    self.raw_packets_count += 1

                    if self.is_recording and not self.is_paused and self.active_session:
                        if verdict.is_acceptable:
                            self.valid_samples_count += 1
                        else:
                            self.flagged_samples_count += 1

                        if anchor_id in self.anchor_sample_counts:
                            self.anchor_sample_counts[anchor_id] += 1
                        else:
                            self.anchor_sample_counts[anchor_id] = 1

                        row = [
                            ts_ms,
                            anchor_id,
                            target_mac,
                            rssi,
                            raw_line[:32],
                            dist,
                            obs,
                            obs_type,
                            height,
                            motion,
                        ]
                        with self.file_lock:
                            if self.csv_writer:
                                try:
                                    self.csv_writer.writerow(row)
                                    self.file_handle.flush()
                                except Exception:
                                    pass

                    pkt = {
                        "timestamp": ts_ms,
                        "provenance": "HARDWARE_SERIAL_COM",
                        "anchor_id": anchor_id,
                        "node_key": node_key,
                        "anchor_mac": self.node_health.get(node_key, {}).get("mac", ""),
                        "device_mac": target_mac,
                        "rssi": rssi,
                        "distance_m": dist,
                        "condition": cond,
                        "obstacle_type": obs_type,
                        "quality_verdict": verdict,
                        "raw_packets": self.raw_packets_count,
                        "valid_samples": self.valid_samples_count,
                        "flagged_samples": self.flagged_samples_count,
                        "anchor_counts": dict(self.anchor_sample_counts),
                        "sync_status": self.get_nodes_sync_status(),
                    }
                    self.packet_queue.put(pkt)

                    # Forward serial observation to FastAPI backend (fire-and-forget)
                    self._enqueue_http_forward({
                        "timestamp": ts_ms,
                        "anchor_id": anchor_id,
                        "device_mac": target_mac,
                        "rssi": rssi,
                        "provenance": "HARDWARE_SERIAL_COM",
                        "raw_payload": raw_line[:128],
                        "ip": "127.0.0.1",
                        "anchor_mac": self.node_health.get(node_key, {}).get("mac", ""),
                    })
        except Exception:
            time.sleep(1.0)
