import os
import sys
import pytest
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from server.app import GeofenceEngine, resolve_room_name, resolve_room_name_with_hysteresis

def test_room_name_resolution():
    assert resolve_room_name(2.0, 7.0) == 'Room A (Executive Suite 1)'
    assert resolve_room_name(7.0, 7.0) == 'Room B (Meeting Room 2)'
    assert resolve_room_name(2.0, 2.0) == 'Room C (Operations Hub)'
    assert resolve_room_name(7.0, 2.0) == 'Room D (Main Entrance)'

def test_room_name_hysteresis():
    current = 'Room A (Executive Suite 1)'
    res = resolve_room_name_with_hysteresis(5.1, 5.1, current)
    assert res == current
    res_far = resolve_room_name_with_hysteresis(7.0, 2.0, current)
    assert 'Room D' in res_far

def test_geofence_alert_trigger():
    engine = GeofenceEngine()
    alert = engine.evaluate_transition('TAG_01', 'Room A (Executive Suite 1)', 'Room D (Main Entrance)')
    assert alert is not None
    assert alert['type'] == 'GEOFENCE_ALERT'
    assert alert['severity'] == 'HIGH'
    assert alert['patient'] == 'TAG_01'
    assert alert['from'] == 'Room A (Executive Suite 1)'
    assert alert['to'] == 'Room D (Main Entrance)'
    no_alert = engine.evaluate_transition('TAG_01', 'Room A (Executive Suite 1)', 'Room A (Executive Suite 1)')
    assert no_alert is None
    warn_alert = engine.evaluate_transition('TAG_01', 'Room A (Executive Suite 1)', 'Room B (Meeting Room 2)')
    assert warn_alert is not None
    assert warn_alert['severity'] == 'WARNING'
