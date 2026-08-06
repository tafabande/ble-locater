"""
Geofence Alert Engine & SQLite Audit Log Database
==================================================
Evaluates room-to-room transitions against configurable rules (geofence_rules.json)
and persists historical alert audit trails into SQLite database (alerts.db).
"""

import os
import json
import time
import sqlite3
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict

logger = logging.getLogger("GEOFENCE_ENGINE")

@dataclass
class GeofenceRule:
    from_room: str
    to_room: str
    severity: str
    message: str

class AlertHistoryDB:
    """SQLite persistent audit log for RTLS hospital alerts."""
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "alerts.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS geofence_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER,
                        time_str TEXT,
                        patient_id TEXT,
                        from_room TEXT,
                        to_room TEXT,
                        severity TEXT,
                        message TEXT,
                        acknowledged INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize alerts database: {e}")

    def log_alert(self, alert_event: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO geofence_alerts (timestamp, time_str, patient_id, from_room, to_room, severity, message, acknowledged)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    alert_event.get("timestamp_ms", int(time.time() * 1000)),
                    alert_event.get("time", time.strftime("%H:%M:%S")),
                    alert_event.get("patient", "TAG_01"),
                    alert_event.get("from", "Unknown"),
                    alert_event.get("to", "Unknown"),
                    alert_event.get("severity", "LOW"),
                    alert_event.get("message", "")
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert alert into SQLite audit log: {e}")

    def get_recent_alerts(self, limit: int = 50) -> List[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM geofence_alerts ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to read alerts from SQLite audit log: {e}")
            return []

    def clear_history(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM geofence_alerts")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear alerts database: {e}")


class GeofenceEngine:
    """
    Modular Geofence Engine that loads rules dynamically from JSON
    and records alerts to a SQLite audit trail.
    """
    def __init__(self, rules_filepath: str = None):
        if rules_filepath is None:
            rules_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "geofence_rules.json")
        self.rules_filepath = rules_filepath
        self.rules: List[GeofenceRule] = []
        self.db = AlertHistoryDB()
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.rules_filepath):
            try:
                with open(self.rules_filepath, "r", encoding="utf-8") as f:
                    rules_data = json.load(f)
                self.rules = [
                    GeofenceRule(
                        from_room=item.get("from", ""),
                        to_room=item.get("to", ""),
                        severity=item.get("severity", "LOW"),
                        message=item.get("message", "")
                    )
                    for item in rules_data
                ]
                logger.info(f"Loaded {len(self.rules)} geofence rules from {self.rules_filepath}")
            except Exception as e:
                logger.error(f"Failed to parse geofence rules: {e}")
                self._load_default_rules()
        else:
            self._load_default_rules()

    def _load_default_rules(self):
        self.rules = [
            GeofenceRule("Room A", "Room D", "HIGH", "🚨 CRITICAL: Patient exited ICU (Room A) directly into Emergency Ward (Room D)!"),
            GeofenceRule("Room A", "Room B", "WARNING", "⚠️ WARNING: Patient exited ICU (Room A) into Patient Bedroom 2 (Room B)."),
            GeofenceRule("Room A", "Room C", "WARNING", "⚠️ WARNING: Patient exited ICU (Room A) into Medical Station (Room C)."),
            GeofenceRule("Room C", "Room D", "LOW", "ℹ️ INFO: Tag moved from Medical Station (Room C) to Emergency Ward (Room D).")
        ]

    def evaluate_transition(self, tag_id: str, old_room: str, new_room: str) -> Optional[dict]:
        if not old_room or not new_room or old_room == new_room:
            return None

        matched_rule = None
        for r in self.rules:
            if r.from_room in old_room and r.to_room in new_room:
                matched_rule = r
                break

        if not matched_rule:
            if "Room A" in old_room:
                matched_rule = GeofenceRule("Room A", new_room, "HIGH", f"🚨 CRITICAL: Tag {tag_id} exited ICU (Room A) into {new_room}!")
            else:
                matched_rule = GeofenceRule(old_room, new_room, "LOW", f"ℹ️ Tag {tag_id} moved from {old_room} to {new_room}.")

        timestamp_str = time.strftime("%H:%M:%S", time.localtime())
        alert_event = {
            "type": "GEOFENCE_ALERT",
            "severity": matched_rule.severity,
            "patient": tag_id,
            "from": old_room,
            "to": new_room,
            "time": timestamp_str,
            "timestamp_ms": int(time.time() * 1000),
            "message": matched_rule.message
        }

        # Log alert to persistent SQLite audit database
        self.db.log_alert(alert_event)

        return alert_event
