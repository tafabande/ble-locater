"""Unit tests for ESP32 Node Registry, Hardware MAC binding, and configuration persistence."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from collector.node_registry import (
    normalize_mac,
    load_node_registry,
    save_node_registry,
    bind_mac_to_node,
    get_node_by_mac,
    get_node_by_anchor_id,
    sync_anchors_metadata,
)


def test_normalize_mac():
    assert normalize_mac("24:6f:28:1a:4c:01") == "24:6F:28:1A:4C:01"
    assert normalize_mac("24-6F-28-1A-4C-01") == "24:6F:28:1A:4C:01"
    assert normalize_mac("246f281a4c01") == "24:6F:28:1A:4C:01"
    assert normalize_mac("AABBCCDDEEFF") == "AA:BB:CC:DD:EE:FF"


def test_registry_loading_and_saving(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        reg = load_node_registry()
        assert "NODE_A" in reg
        assert "NODE_B" in reg
        assert "NODE_C" in reg
        assert "NODE_D" in reg
        assert reg["NODE_A"]["corner"] == "SW"
        assert reg["NODE_B"]["corner"] == "SE"
        assert reg["NODE_C"]["corner"] == "NW"
        assert reg["NODE_D"]["corner"] == "NE"


def test_bind_mac_permanence(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        # Bind hardware MAC to NODE_A
        test_mac = "AA:BB:CC:11:22:33"
        node = bind_mac_to_node("NODE_A", test_mac, status="provisioned")
        assert node["mac"] == test_mac
        assert node["status"] == "provisioned"

        # Verify lookup
        found = get_node_by_mac(test_mac)
        assert found is not None
        node_key, info = found
        assert node_key == "NODE_A"
        assert info["corner"] == "SW"

        # Ensure binding transfers if assigned elsewhere
        bind_mac_to_node("NODE_B", test_mac, status="reassigned")
        reg = load_node_registry()
        assert reg["NODE_B"]["mac"] == test_mac
        assert reg["NODE_A"]["mac"] == ""


def test_get_node_by_anchor_id(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        res_a = get_node_by_anchor_id("ANCHOR_01")
        assert res_a is not None
        assert res_a[0] == "NODE_A"

        res_c = get_node_by_anchor_id("NODE_C")
        assert res_c is not None
        assert res_c[1]["corner"] == "NW"


def test_node_mac_locking_enforcement(monkeypatch):
    """Verify that a locked node cannot have its MAC replaced with another MAC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        mac_a = "AA:BB:CC:11:22:33"
        mac_new = "AA:BB:CC:99:88:77"
        nr.bind_mac_to_node("NODE_A", mac_a)
        nr.lock_node("NODE_A")

        assert nr.is_node_locked("NODE_A") is True

        # Attempting to replace NODE_A's MAC while locked must raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            nr.bind_mac_to_node("NODE_A", mac_new)
        assert "LOCKED" in str(exc_info.value)
        assert mac_a in str(exc_info.value)

        # Confirm registry was NOT modified
        reg = nr.load_node_registry()
        assert reg["NODE_A"]["mac"] == mac_a


def test_prevent_assigning_locked_mac_elsewhere(monkeypatch):
    """Verify that a MAC locked to NODE_A cannot be assigned to NODE_B."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        mac_a = "C8:2E:18:26:39:A0"
        nr.bind_mac_to_node("NODE_A", mac_a)
        nr.lock_node("NODE_A")

        # Attempting to assign NODE_A's locked MAC to NODE_B must raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            nr.bind_mac_to_node("NODE_B", mac_a)
        assert "LOCKED" in str(exc_info.value)
        assert "NODE_A" in str(exc_info.value)

        # Confirm NODE_B does not get the MAC and NODE_A still retains it
        reg = nr.load_node_registry()
        assert reg["NODE_A"]["mac"] == mac_a
        assert reg["NODE_B"]["mac"] != mac_a


def test_unlock_allows_reassignment(monkeypatch):
    """Verify that explicitly unlocking a node permits MAC replacement and reassignment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "node_registry.json"
        tmp_meta = Path(tmpdir) / "anchors_metadata.json"

        import collector.node_registry as nr
        monkeypatch.setattr(nr, "REGISTRY_FILE", tmp_reg)
        monkeypatch.setattr(nr, "METADATA_FILE", tmp_meta)
        monkeypatch.setattr(nr, "CONFIG_DIR", Path(tmpdir))

        mac_original = "11:22:33:44:55:66"
        mac_replacement = "AA:BB:CC:DD:EE:FF"
        nr.bind_mac_to_node("NODE_A", mac_original)
        nr.lock_node("NODE_A")
        assert nr.is_node_locked("NODE_A") is True

        # Unlock
        nr.unlock_node("NODE_A")
        assert nr.is_node_locked("NODE_A") is False

        # Now replacing MAC succeeds cleanly
        node = nr.bind_mac_to_node("NODE_A", mac_replacement)
        assert node["mac"] == mac_replacement
        reg = nr.load_node_registry()
        assert reg["NODE_A"]["mac"] == mac_replacement


def test_recording_nodes_sync_status_configured_and_online(monkeypatch):
    """Verify get_nodes_sync_status accurately differentiates configured vs unconfigured and online vs offline."""
    import queue
    import time
    from collector.recording import RecordingEngine

    pq = queue.Queue()
    engine = RecordingEngine(pq)

    # Simulate node A having received packets recently, node B having an old timestamp
    now = time.time()
    engine.node_health["NODE_A"] = {"last_seen": now - 1.0, "rssi": -65, "packets": 42, "ip": "192.168.1.101"}
    engine.node_health["NODE_B"] = {"last_seen": now - 30.0, "rssi": -90, "packets": 5, "ip": "192.168.1.102"}
    engine.node_health["NODE_C"] = {"last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""}
    engine.node_health["NODE_D"] = {"last_seen": 0.0, "rssi": -99, "packets": 0, "ip": ""}

    status = engine.get_nodes_sync_status()
    assert "online_count" in status
    assert "configured_count" in status
    assert "nodes" in status

    # NODE_A is online (seen 1s ago < 7s timeout)
    assert status["nodes"]["NODE_A"]["online"] is True
    # NODE_B is offline (seen 30s ago > 7s timeout)
    assert status["nodes"]["NODE_B"]["online"] is False
    # NODE_A has default valid MAC in registry, so configured is True
    assert status["nodes"]["NODE_A"]["configured"] is True


def test_canvas_editor_node_status_management():
    """Verify CanvasEditor correctly stores and resolves node health status for anchor rendering."""
    import tkinter as tk
    from collector.canvas_editor import CanvasEditor
    from collector.environment import EnvironmentLayout

    root = tk.Tk()
    root.withdraw()
    try:
        canvas = tk.Canvas(root, width=400, height=300)
        editor = CanvasEditor(canvas, layout=EnvironmentLayout())

        test_status = {
            "NODE_A": {"online": True, "configured": True, "mac": "AA:BB:CC:DD:EE:01", "locked": True},
            "NODE_B": {"online": False, "configured": True, "mac": "AA:BB:CC:DD:EE:02", "locked": False},
            "NODE_C": {"online": False, "configured": False, "mac": "Unassigned", "locked": False},
            "NODE_D": {"online": False, "configured": False, "mac": "Unassigned", "locked": False},
        }

        editor.set_nodes_status(test_status)
        assert editor.nodes_status == test_status

        # Query by ANCHOR_01 and verify mapping to NODE_A
        st_a = editor._get_node_status_for_anchor("ANCHOR_01")
        assert st_a["online"] is True
        assert st_a["configured"] is True

        # Query by ANCHOR_02 and verify mapping to NODE_B (offline)
        st_b = editor._get_node_status_for_anchor("ANCHOR_02")
        assert st_b["online"] is False
        assert st_b["configured"] is True

        # Query by ANCHOR_03 (unconfigured & offline)
        st_c = editor._get_node_status_for_anchor("ANCHOR_03")
        assert st_c["online"] is False
        assert st_c["configured"] is False

        # Redraw triggers cleanly without exception
        editor.redraw()
    finally:
        root.destroy()

