"""Indoor Positioning — Persistent ESP32 Node Registry & Hardware MAC Binding.

Manages persistent associations between ESP32 hardware silicon MAC addresses
and logical positioning nodes (Node A, Node B, Node C, Node D) located at the room corners.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
REGISTRY_FILE = CONFIG_DIR / "node_registry.json"
METADATA_FILE = CONFIG_DIR / "anchors_metadata.json"

DEFAULT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "NODE_A": {
        "anchor_id": "ANCHOR_01",
        "display_name": "ESP32-A (Corner SW)",
        "corner": "SW",
        "mac": "24:6F:28:1A:4C:01",
        "default_pos": [0.2, 0.2],
        "status": "ready",
        "last_flashed": None,
    },
    "NODE_B": {
        "anchor_id": "ANCHOR_02",
        "display_name": "ESP32-B (Corner SE)",
        "corner": "SE",
        "mac": "24:6F:28:1A:4C:02",
        "default_pos": [4.8, 0.2],
        "status": "ready",
        "last_flashed": None,
    },
    "NODE_C": {
        "anchor_id": "ANCHOR_03",
        "display_name": "ESP32-C (Corner NW)",
        "corner": "NW",
        "mac": "24:6F:28:1A:4C:03",
        "default_pos": [0.2, 4.8],
        "status": "ready",
        "last_flashed": None,
    },
    "NODE_D": {
        "anchor_id": "ANCHOR_04",
        "display_name": "ESP32-D (Corner NE)",
        "corner": "NE",
        "mac": "24:6F:28:1A:4C:04",
        "default_pos": [4.8, 4.8],
        "status": "ready",
        "last_flashed": None,
    },
}


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to uppercase colon-separated format (e.g. 24:6F:28:1A:4C:01)."""
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    if len(cleaned) == 12:
        return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return mac.strip().upper()


def load_node_registry() -> Dict[str, Dict[str, Any]]:
    """Load the persistent node registry from disk, creating default if missing."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all 4 canonical keys exist
                for k, v in DEFAULT_REGISTRY.items():
                    if k not in data:
                        data[k] = v.copy()
                return data
        except Exception:
            pass

    # Save and return default registry
    save_node_registry(DEFAULT_REGISTRY)
    return DEFAULT_REGISTRY.copy()


def save_node_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    """Save the node registry to disk and update anchors_metadata companion."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    # Automatically synchronize anchors_metadata.json for the rest of the ecosystem
    sync_anchors_metadata(registry)


def sync_anchors_metadata(registry: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Synchronize anchors_metadata.json with the node registry."""
    if registry is None:
        registry = load_node_registry()

    metadata: Dict[str, Dict[str, Any]] = {}
    for node_key, info in registry.items():
        anchor_id = info.get("anchor_id", f"ANCHOR_{node_key[-1]}")
        metadata[anchor_id] = {
            "mac": info.get("mac", "Unknown"),
            "name": info.get("display_name", f"ESP32 {node_key}"),
            "node_key": node_key,
            "corner": info.get("corner", "Unknown"),
            "default_pos": info.get("default_pos", [0.0, 0.0]),
        }

    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass


def bind_mac_to_node(
    node_key: str,
    mac: str,
    status: str = "configured",
    display_name: Optional[str] = None
) -> Dict[str, Any]:
    """Permanently bind a hardware MAC address to a node (Node A, B, C, or D).

    Ensures the MAC is unique: if another node previously held this MAC,
    it is transferred with a notice.
    """
    normalized = normalize_mac(mac)
    registry = load_node_registry()

    if node_key not in registry:
        raise KeyError(f"Unknown node key: {node_key}. Expected one of {list(registry.keys())}")

    # Remove this MAC from any other node to maintain strict 1:1 binding
    for other_key, info in registry.items():
        if other_key != node_key and info.get("mac", "").upper() == normalized:
            info["mac"] = ""
            info["status"] = "unassigned"

    node = registry[node_key]
    node["mac"] = normalized
    node["status"] = status
    node["last_flashed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if display_name:
        node["display_name"] = display_name

    save_node_registry(registry)
    return node


def get_node_by_mac(mac: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Look up a node by its hardware MAC address."""
    normalized = normalize_mac(mac)
    registry = load_node_registry()
    for node_key, info in registry.items():
        if info.get("mac", "").upper() == normalized:
            return node_key, info
    return None


def get_node_by_anchor_id(anchor_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Look up a node by its anchor ID (e.g. ANCHOR_01, NODE_A)."""
    aid_upper = anchor_id.strip().upper()
    registry = load_node_registry()
    for node_key, info in registry.items():
        if (
            info.get("anchor_id", "").upper() == aid_upper
            or node_key.upper() == aid_upper
            or info.get("display_name", "").upper().startswith(aid_upper)
        ):
            return node_key, info
    return None
