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
