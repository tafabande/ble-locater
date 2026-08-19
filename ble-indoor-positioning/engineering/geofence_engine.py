import os
import json
import time
import sqlite3
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from sqlmodel import SQLModel, Session, select
from server.db import create_db_engine, GeofenceAlert

logger = logging.getLogger('GEOFENCE_ENGINE')

@dataclass
class GeofenceRule:
    from_room: str
    to_room: str
    severity: str
    message: str

class AlertHistoryDB:

    def __init__(self, db_path: str=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'alerts.db')
        self.db_path = db_path
        self.engine = create_db_engine(self.db_path)
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            SQLModel.metadata.create_all(self.engine)
        except Exception as e:
            logger.error(f'Failed to initialize alerts database: {e}')

    def log_alert(self, alert_event: dict):
        try:
            alert = GeofenceAlert(
                timestamp=alert_event.get('timestamp_ms', int(time.time() * 1000)),
                time_str=alert_event.get('time', time.strftime('%H:%M:%S')),
                patient_id=alert_event.get('patient', 'TAG_01'),
                from_room=alert_event.get('from', 'Unknown'),
                to_room=alert_event.get('to', 'Unknown'),
                severity=alert_event.get('severity', 'LOW'),
                message=alert_event.get('message', ''),
                acknowledged=0
            )
            with Session(self.engine) as session:
                session.add(alert)
                session.commit()
        except Exception as e:
            logger.error(f'Failed to insert alert into SQLite audit log: {e}')

    def get_recent_alerts(self, limit: int=50) -> List[dict]:
        try:
            with Session(self.engine) as session:
                statement = select(GeofenceAlert).order_by(GeofenceAlert.id.desc()).limit(limit)
                results = session.exec(statement).all()
                return [r.model_dump() for r in results]
        except Exception as e:
            logger.error(f'Failed to read alerts from SQLite audit log: {e}')
            return []

    def clear_history(self):
        try:
            with Session(self.engine) as session:
                alerts = session.exec(select(GeofenceAlert)).all()
                for a in alerts:
                    session.delete(a)
                session.commit()
        except Exception as e:
            logger.error(f'Failed to clear alerts database: {e}')

class GeofenceEngine:

    def __init__(self, rules_filepath: str=None):
        if rules_filepath is None:
            rules_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'geofence_rules.json')
        self.rules_filepath = rules_filepath
        self.rules: List[GeofenceRule] = []
        self.db = AlertHistoryDB()
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.rules_filepath):
            try:
                with open(self.rules_filepath, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                self.rules = [GeofenceRule(from_room=item.get('from', ''), to_room=item.get('to', ''), severity=item.get('severity', 'LOW'), message=item.get('message', '')) for item in rules_data]
                logger.info(f'Loaded {len(self.rules)} geofence rules from {self.rules_filepath}')
            except Exception as e:
                logger.error(f'Failed to parse geofence rules: {e}')
                self._load_default_rules()
        else:
            self._load_default_rules()

    def _load_default_rules(self):
        self.rules = [GeofenceRule('Room A', 'Room D', 'HIGH', '🚨 CRITICAL: Patient exited ICU (Room A) directly into Emergency Ward (Room D)!'), GeofenceRule('Room A', 'Room B', 'WARNING', '⚠️ WARNING: Patient exited ICU (Room A) into Patient Bedroom 2 (Room B).'), GeofenceRule('Room A', 'Room C', 'WARNING', '⚠️ WARNING: Patient exited ICU (Room A) into Medical Station (Room C).'), GeofenceRule('Room C', 'Room D', 'LOW', 'ℹ️ INFO: Tag moved from Medical Station (Room C) to Emergency Ward (Room D).')]

    def evaluate_transition(self, tag_id: str, old_room: str, new_room: str) -> Optional[dict]:
        if not old_room or not new_room or old_room == new_room:
            return None
        matched_rule = None
        for r in self.rules:
            if r.from_room in old_room and r.to_room in new_room:
                matched_rule = r
                break
        if not matched_rule:
            if 'Room A' in old_room:
                matched_rule = GeofenceRule('Room A', new_room, 'HIGH', f'🚨 CRITICAL: Tag {tag_id} exited ICU (Room A) into {new_room}!')
            else:
                matched_rule = GeofenceRule(old_room, new_room, 'LOW', f'ℹ️ Tag {tag_id} moved from {old_room} to {new_room}.')
        timestamp_str = time.strftime('%H:%M:%S', time.localtime())
        alert_event = {'type': 'GEOFENCE_ALERT', 'severity': matched_rule.severity, 'patient': tag_id, 'from': old_room, 'to': new_room, 'time': timestamp_str, 'timestamp_ms': int(time.time() * 1000), 'message': matched_rule.message}
        self.db.log_alert(alert_event)
        return alert_event
