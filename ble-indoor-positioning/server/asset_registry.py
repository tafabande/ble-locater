import os
import time
import sqlite3
import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from sqlmodel import SQLModel, Session, select, col
from server.db import create_db_engine, Asset

logger = logging.getLogger('ASSET_REGISTRY')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOM_IDS = {'Room A (ICU Bedroom 1)': 'room_a', 'Room B (Patient Bedroom 2)': 'room_b', 'Room C (Medical Station)': 'room_c', 'Room D (Emergency Ward)': 'room_d'}
ROOM_NAMES = {v: k for k, v in ROOM_IDS.items()}
ROOM_ADJACENCY: Dict[str, Dict[str, int]] = {'room_a': {'room_b': 1, 'room_c': 1, 'room_d': 2}, 'room_b': {'room_a': 1, 'room_d': 1, 'room_c': 2}, 'room_c': {'room_a': 1, 'room_d': 1, 'room_b': 2}, 'room_d': {'room_b': 1, 'room_c': 1, 'room_a': 2}}
ROOM_META = {'room_a': {'name': 'Room A', 'full_name': 'Room A (ICU Bedroom 1)', 'short': 'ICU', 'x': 2.5, 'y': 7.5, 'color': '#89b4fa', 'icon': '🏥'}, 'room_b': {'name': 'Room B', 'full_name': 'Room B (Patient Bedroom 2)', 'short': 'Patient', 'x': 7.5, 'y': 7.5, 'color': '#a6e3a1', 'icon': '🛏️'}, 'room_c': {'name': 'Room C', 'full_name': 'Room C (Medical Station)', 'short': 'Medical', 'x': 2.5, 'y': 2.5, 'color': '#fab387', 'icon': '💊'}, 'room_d': {'name': 'Room D', 'full_name': 'Room D (Emergency Ward)', 'short': 'Emergency', 'x': 7.5, 'y': 2.5, 'color': '#f38ba8', 'icon': '🚑'}}

def get_room_id(room_name: str) -> Optional[str]:
    if room_name in ROOM_IDS:
        return ROOM_IDS[room_name]
    for full_name, rid in ROOM_IDS.items():
        if room_name in full_name or full_name.startswith(room_name):
            return rid
    if room_name in ROOM_ADJACENCY:
        return room_name
    return None

def room_distance(room1: str, room2: str) -> int:
    r1 = get_room_id(room1)
    r2 = get_room_id(room2)
    if r1 is None or r2 is None:
        return 99
    if r1 == r2:
        return 0
    return ROOM_ADJACENCY.get(r1, {}).get(r2, 99)

def get_adjacent_rooms(room_name: str) -> List[dict]:
    rid = get_room_id(room_name)
    if rid is None:
        return []
    neighbors = ROOM_ADJACENCY.get(rid, {})
    result = []
    for neighbor_id, dist in sorted(neighbors.items(), key=lambda x: x[1]):
        meta = ROOM_META.get(neighbor_id, {})
        result.append({'room_id': neighbor_id, 'name': meta.get('full_name', neighbor_id), 'short': meta.get('short', neighbor_id), 'distance': dist, 'icon': meta.get('icon', '📍'), 'color': meta.get('color', '#cdd6f4'), 'x': meta.get('x', 5.0), 'y': meta.get('y', 5.0)})
    return result

class AssetRegistry:

    def __init__(self, db_path: str=None):
        if db_path is None:
            db_path = os.path.join(PROJECT_ROOT, 'models', 'asset_registry.db')
        self.db_path = db_path
        self.engine = create_db_engine(self.db_path)
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            SQLModel.metadata.create_all(self.engine)
            with Session(self.engine) as session:
                count = len(session.exec(select(Asset)).all())
                if count == 0:
                    self._seed_demo_data(session)
        except Exception as e:
            logger.error(f'Failed to initialize asset registry: {e}')

    def _seed_demo_data(self, session: Session):
        now = int(time.time() * 1000)
        demo_assets = [
            ('EQUIP-001', 'ECG Machine #01', 'medical_equipment', 'ICU', 1, 'Room A (ICU Bedroom 1)', 'EC:G1:00:00:00:01', 'active', 'Portable 12-lead ECG'),
            ('EQUIP-002', 'ECG Machine #02', 'medical_equipment', 'Emergency Ward', 1, 'Room D (Emergency Ward)', 'EC:G2:00:00:00:02', 'active', 'Bedside monitor'),
            ('EQUIP-003', 'Infusion Pump #01', 'medical_equipment', 'ICU', 1, 'Room A (ICU Bedroom 1)', 'PU:MP:00:00:00:03', 'active', 'IV infusion pump'),
            ('EQUIP-004', 'Wheelchair #03', 'mobility', 'Medical Station', 1, 'Room C (Medical Station)', 'WC:HR:00:00:00:04', 'active', 'Standard wheelchair'),
            ('EQUIP-005', 'Defibrillator #01', 'medical_equipment', 'Emergency Ward', 1, 'Room D (Emergency Ward)', 'DE:FB:00:00:00:05', 'active', 'AED defibrillator'),
            ('EQUIP-006', 'Portable X-Ray', 'medical_equipment', 'Medical Station', 1, 'Room C (Medical Station)', 'XR:AY:00:00:00:06', 'active', 'Mobile X-ray unit'),
            ('OFFICE-001', 'Printer #01', 'office_equipment', 'Medical Station', 1, 'Room C (Medical Station)', 'PR:NT:00:00:00:07', 'active', 'Network laser printer'),
            ('OFFICE-002', 'Medication Cart #02', 'supply_cart', 'Patient Bedroom', 1, 'Room B (Patient Bedroom 2)', 'CA:RT:00:00:00:08', 'active', 'Locked medication cart'),
            ('STAFF-001', 'Dr. Sarah Chen', 'staff', 'ICU', 1, 'Room A (ICU Bedroom 1)', 'ST:AF:00:00:00:09', 'active', 'ICU attending physician'),
            ('STAFF-002', 'Nurse John', 'staff', 'Patient Bedroom', 1, 'Room B (Patient Bedroom 2)', 'ST:AF:00:00:00:10', 'active', 'Floor nurse'),
            ('PAT-001', 'Patient — Bed 1A', 'patient', 'ICU', 1, 'Room A (ICU Bedroom 1)', 'PA:TN:00:00:00:11', 'active', 'ICU patient, bed 1A'),
            ('PAT-002', 'Patient — Bed 2B', 'patient', 'Patient Bedroom', 1, 'Room B (Patient Bedroom 2)', 'PA:TN:00:00:00:12', 'active', 'General ward patient')
        ]
        try:
            for a in demo_assets:
                asset_obj = Asset(id=a[0], name=a[1], type=a[2], department=a[3], floor=a[4], room=a[5], ble_mac=a[6], status=a[7], notes=a[8], created_at=now)
                session.add(asset_obj)
            session.commit()
            logger.info(f'🏷️ Seeded {len(demo_assets)} demo assets into registry.')
        except Exception as e:
            logger.error(f'Failed to seed demo assets: {e}')

    def get_all(self) -> List[dict]:
        try:
            with Session(self.engine) as session:
                statement = select(Asset).order_by(Asset.type, Asset.name)
                results = session.exec(statement).all()
                return [r.model_dump() for r in results]
        except Exception as e:
            logger.error(f'Failed to fetch assets: {e}')
            return []

    def get_by_id(self, asset_id: str) -> Optional[dict]:
        try:
            with Session(self.engine) as session:
                asset = session.get(Asset, asset_id)
                return asset.model_dump() if asset else None
        except Exception as e:
            logger.error(f'Failed to fetch asset {asset_id}: {e}')
            return None

    def get_by_mac(self, ble_mac: str) -> Optional[dict]:
        try:
            with Session(self.engine) as session:
                statement = select(Asset).where(Asset.ble_mac == ble_mac)
                asset = session.exec(statement).first()
                return asset.model_dump() if asset else None
        except Exception as e:
            logger.error(f'Failed to fetch asset by MAC {ble_mac}: {e}')
            return None

    def create(self, asset_data: dict) -> Optional[dict]:
        try:
            now = int(time.time() * 1000)
            asset = Asset(
                id=asset_data['id'],
                name=asset_data['name'],
                type=asset_data.get('type', 'equipment'),
                department=asset_data.get('department', ''),
                floor=asset_data.get('floor', 1),
                room=asset_data.get('room', ''),
                ble_mac=asset_data.get('ble_mac', ''),
                status=asset_data.get('status', 'active'),
                notes=asset_data.get('notes', ''),
                created_at=now
            )
            with Session(self.engine) as session:
                session.add(asset)
                session.commit()
                session.refresh(asset)
                return asset.model_dump()
        except Exception as e:
            logger.error(f'Failed to create asset: {e}')
            return None

    def update(self, asset_id: str, updates: dict) -> Optional[dict]:
        allowed_fields = {'name', 'type', 'department', 'floor', 'room', 'ble_mac', 'status', 'notes'}
        fields = {k: v for k, v in updates.items() if k in allowed_fields}
        if not fields:
            return self.get_by_id(asset_id)
        try:
            with Session(self.engine) as session:
                asset = session.get(Asset, asset_id)
                if not asset:
                    return None
                for key, val in fields.items():
                    setattr(asset, key, val)
                session.add(asset)
                session.commit()
                session.refresh(asset)
                return asset.model_dump()
        except Exception as e:
            logger.error(f'Failed to update asset {asset_id}: {e}')
            return None

    def delete(self, asset_id: str) -> bool:
        try:
            with Session(self.engine) as session:
                asset = session.get(Asset, asset_id)
                if asset:
                    session.delete(asset)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f'Failed to delete asset {asset_id}: {e}')
            return False

    def get_by_room(self, room_name: str) -> List[dict]:
        try:
            with Session(self.engine) as session:
                statement = select(Asset).where(col(Asset.room).contains(room_name)).order_by(Asset.name)
                results = session.exec(statement).all()
                return [r.model_dump() for r in results]
        except Exception as e:
            logger.error(f'Failed to fetch assets for room {room_name}: {e}')
            return []

    def get_by_type(self, asset_type: str) -> List[dict]:
        try:
            with Session(self.engine) as session:
                statement = select(Asset).where(Asset.type == asset_type).order_by(Asset.name)
                results = session.exec(statement).all()
                return [r.model_dump() for r in results]
        except Exception as e:
            logger.error(f'Failed to fetch assets of type {asset_type}: {e}')
            return []
ASSET_TYPE_ICONS = {'medical_equipment': '🩺', 'office_equipment': '🖨️', 'mobility': '♿', 'supply_cart': '🛒', 'staff': '👤', 'patient': '🏥', 'equipment': '📦'}

@dataclass
class SearchResult:
    asset: dict
    score: float
    proximity_label: str
    distance_rooms: int
    live_position: Optional[dict] = None
    last_seen_seconds: Optional[float] = None

class SearchEngine:

    def __init__(self, registry: AssetRegistry):
        self.registry = registry

    def search(self, query: str, user_room: Optional[str]=None, tag_states: Optional[dict]=None, limit: int=20) -> List[dict]:
        if not isinstance(query, str) or not query.strip():
            return []
        if hasattr(user_room, 'default'):
            user_room = user_room.default if isinstance(user_room.default, str) else None
        elif not isinstance(user_room, str):
            user_room = None
        if hasattr(limit, 'default'):
            limit = limit.default if isinstance(limit.default, int) else 20
        else:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 20
        query_lower = query.strip().lower()
        all_assets = self.registry.get_all()
        now = time.time()
        results = []
        for asset in all_assets:
            text_score = 0.0
            name_lower = (asset.get('name') or '').lower()
            type_lower = (asset.get('type') or '').lower()
            dept_lower = (asset.get('department') or '').lower()
            room_lower = (asset.get('room') or '').lower()
            notes_lower = (asset.get('notes') or '').lower()
            asset_id_lower = (asset.get('id') or '').lower()
            if query_lower == name_lower:
                text_score = 10.0
            elif query_lower in name_lower:
                text_score = 7.0
            elif query_lower in type_lower:
                text_score = 5.0
            elif query_lower in dept_lower:
                text_score = 4.0
            elif query_lower in room_lower:
                text_score = 3.0
            elif query_lower in notes_lower:
                text_score = 2.0
            elif query_lower in asset_id_lower:
                text_score = 2.0
            else:
                words = query_lower.split()
                word_hits = sum((1 for w in words if w in name_lower or w in type_lower or w in dept_lower or (w in room_lower) or (w in notes_lower)))
                if word_hits > 0:
                    text_score = 1.0 + word_hits / max(1, len(words)) * 3.0
                else:
                    continue
            proximity_score = 0.0
            dist_rooms = 99
            proximity_label = 'Unknown'
            asset_room = asset.get('room', '')
            if user_room:
                dist_rooms = room_distance(user_room, asset_room)
                if dist_rooms == 0:
                    proximity_score = 5.0
                    proximity_label = 'Same room'
                elif dist_rooms == 1:
                    proximity_score = 3.0
                    proximity_label = 'Adjacent room'
                elif dist_rooms == 2:
                    proximity_score = 1.0
                    proximity_label = '2 rooms away'
                else:
                    proximity_score = 0.0
                    proximity_label = 'Far away'
            else:
                proximity_label = asset_room or 'Unknown'
            freshness_score = 0.0
            last_seen_seconds = None
            live_position = None
            ble_mac = asset.get('ble_mac', '')
            if tag_states and ble_mac and (ble_mac in tag_states):
                tag = tag_states[ble_mac]
                last_seen = getattr(tag, 'last_seen', None)
                if last_seen:
                    age = now - last_seen
                    last_seen_seconds = round(age, 1)
                    if age < 10:
                        freshness_score = 3.0
                    elif age < 60:
                        freshness_score = 2.0
                    elif age < 300:
                        freshness_score = 1.0
                pos = getattr(tag, 'last_position', None)
                if pos:
                    live_position = pos
                    live_room = tag.current_room if hasattr(tag, 'current_room') else None
                    if live_room:
                        asset_room = live_room
                        dist_rooms = room_distance(user_room, live_room) if user_room else 99
                        if dist_rooms == 0:
                            proximity_score = 5.0
                            proximity_label = 'Same room'
                        elif dist_rooms == 1:
                            proximity_score = 3.0
                            proximity_label = 'Adjacent room'
                        elif dist_rooms == 2:
                            proximity_score = 1.0
                            proximity_label = '2 rooms away'
            confidence_bonus = 0.0
            if live_position and live_position.get('gdop', 99) < 3.0:
                confidence_bonus = 1.0
            total_score = text_score + proximity_score + freshness_score + confidence_bonus
            icon = ASSET_TYPE_ICONS.get(asset.get('type', ''), '📦')
            results.append({'asset': asset, 'score': round(total_score, 2), 'proximity_label': proximity_label, 'distance_rooms': dist_rooms, 'live_position': live_position, 'last_seen_seconds': last_seen_seconds, 'live_room': asset_room, 'icon': icon})
        results.sort(key=lambda r: (-r['score'], r['asset'].get('name', '')))
        return results[:limit]

    def get_nearby(self, user_room: str, tag_states: Optional[dict]=None, max_distance: int=2) -> List[dict]:
        if hasattr(user_room, 'default'):
            user_room = user_room.default if isinstance(user_room.default, str) else ""
        if hasattr(max_distance, 'default'):
            max_distance = max_distance.default if isinstance(max_distance.default, int) else 2
        else:
            try:
                max_distance = int(max_distance)
            except (ValueError, TypeError):
                max_distance = 2
        all_assets = self.registry.get_all()
        now = time.time()
        results = []
        for asset in all_assets:
            asset_room = asset.get('room', '')
            ble_mac = asset.get('ble_mac', '')
            live_position = None
            last_seen_seconds = None
            effective_room = asset_room
            if tag_states and ble_mac and (ble_mac in tag_states):
                tag = tag_states[ble_mac]
                last_seen = getattr(tag, 'last_seen', None)
                if last_seen:
                    last_seen_seconds = round(now - last_seen, 1)
                pos = getattr(tag, 'last_position', None)
                if pos:
                    live_position = pos
                live_room = getattr(tag, 'current_room', None)
                if live_room:
                    effective_room = live_room
            dist = room_distance(user_room, effective_room)
            if dist <= max_distance:
                icon = ASSET_TYPE_ICONS.get(asset.get('type', ''), '📦')
                if dist == 0:
                    proximity_label = 'Same room'
                elif dist == 1:
                    proximity_label = 'Adjacent'
                else:
                    proximity_label = f'{dist} rooms away'
                results.append({'asset': asset, 'proximity_label': proximity_label, 'distance_rooms': dist, 'live_position': live_position, 'last_seen_seconds': last_seen_seconds, 'live_room': effective_room, 'icon': icon})
        results.sort(key=lambda r: (r['distance_rooms'], r['asset'].get('name', '')))
        return results

    def get_context_map(self, user_room: str, tag_states: Optional[dict]=None) -> dict:
        user_room_id = get_room_id(user_room)
        if not user_room_id:
            return {'error': 'Unknown room', 'rooms': [], 'assets': []}
        user_meta = ROOM_META.get(user_room_id, {})
        neighbors = get_adjacent_rooms(user_room)
        nearby_assets = self.get_nearby(user_room, tag_states, max_distance=2)
        assets_by_room: Dict[str, list] = {}
        for item in nearby_assets:
            room_key = item.get('live_room') or item['asset'].get('room', 'Unknown')
            if room_key not in assets_by_room:
                assets_by_room[room_key] = []
            assets_by_room[room_key].append(item)
        rooms = [{'room_id': user_room_id, 'name': user_meta.get('full_name', user_room), 'short': user_meta.get('short', 'You'), 'distance': 0, 'is_user_room': True, 'icon': user_meta.get('icon', '📍'), 'color': user_meta.get('color', '#89b4fa'), 'x': user_meta.get('x', 5.0), 'y': user_meta.get('y', 5.0), 'assets': assets_by_room.get(user_meta.get('full_name', ''), [])}]
        for n in neighbors:
            rooms.append({**n, 'is_user_room': False, 'assets': assets_by_room.get(n['name'], [])})
        return {'user_room': user_meta.get('full_name', user_room), 'user_room_id': user_room_id, 'rooms': rooms, 'total_nearby_assets': len(nearby_assets)}
