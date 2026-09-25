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
        "locked": False,
        "last_flashed": None,
    },
    "NODE_B": {
        "anchor_id": "ANCHOR_02",
        "display_name": "ESP32-B (Corner SE)",
        "corner": "SE",
        "mac": "24:6F:28:1A:4C:02",
        "default_pos": [4.8, 0.2],
        "status": "ready",
        "locked": False,
        "last_flashed": None,
    },
    "NODE_C": {
        "anchor_id": "ANCHOR_03",
        "display_name": "ESP32-C (Corner NW)",
        "corner": "NW",
        "mac": "24:6F:28:1A:4C:03",
        "default_pos": [0.2, 4.8],
        "status": "ready",
        "locked": False,
        "last_flashed": None,
    },
    "NODE_D": {
        "anchor_id": "ANCHOR_04",
        "display_name": "ESP32-D (Corner NE)",
        "corner": "NE",
        "mac": "24:6F:28:1A:4C:04",
        "default_pos": [4.8, 4.8],
        "status": "ready",
        "locked": False,
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
            "locked": bool(info.get("locked", False)),
            "default_pos": info.get("default_pos", [0.0, 0.0]),
        }

    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass


def is_node_locked(node_key: str) -> bool:
    """Check if a node has its hardware MAC permanently locked."""
    registry = load_node_registry()
    if node_key in registry:
        return bool(registry[node_key].get("locked", False))
    return False


def set_node_lock(node_key: str, locked: bool) -> Dict[str, Any]:
    """Lock or unlock a node to prevent or allow MAC modification."""
    registry = load_node_registry()
    if node_key not in registry:
        raise KeyError(f"Unknown node key: {node_key}. Expected one of {list(registry.keys())}")
    registry[node_key]["locked"] = bool(locked)
    save_node_registry(registry)
    return registry[node_key]


def lock_node(node_key: str) -> Dict[str, Any]:
    """Permanently lock a node's hardware MAC binding."""
    return set_node_lock(node_key, True)


def unlock_node(node_key: str) -> Dict[str, Any]:
    """Unlock a node's hardware MAC binding to allow reassignment or replacement."""
    return set_node_lock(node_key, False)


def bind_mac_to_node(
    node_key: str,
    mac: str,
    status: str = "configured",
    display_name: Optional[str] = None,
    force_unlock: bool = False,
) -> Dict[str, Any]:
    """Permanently bind a hardware MAC address to a node (Node A, B, C, or D).

    Strictly enforces hardware locking:
    1. If the node is locked and new MAC differs from its locked MAC:
       Rejects with PermissionError unless force_unlock is True.
    2. If the MAC is already locked to another node:
       Rejects with PermissionError unless force_unlock is True.
    3. If not locked, any previous assignment is cleanly transferred.
    """
    normalized = normalize_mac(mac)
    registry = load_node_registry()

    if node_key not in registry:
        raise KeyError(f"Unknown node key: {node_key}. Expected one of {list(registry.keys())}")

    # Check 1: Target node is locked and cannot be replaced with another MAC
    target_node = registry[node_key]
    if target_node.get("locked", False) and not force_unlock:
        curr_mac = target_node.get("mac", "")
        if curr_mac and curr_mac.upper() != normalized:
            raise PermissionError(
                f"Node {node_key} is LOCKED with MAC {curr_mac}. "
                f"Cannot replace its MAC with {normalized} unless {node_key} is unlocked first."
            )

    # Check 2: MAC is already bound to another node
    for other_key, info in registry.items():
        if other_key != node_key and info.get("mac", "").upper() == normalized:
            if info.get("locked", False) and not force_unlock:
                raise PermissionError(
                    f"MAC address {normalized} is LOCKED to {other_key} ({info.get('display_name', '')}). "
                    f"Cannot assign it to {node_key} unless {other_key} is unlocked first."
                )
            # Transfer MAC if other node is unlocked
            info["mac"] = ""
            info["status"] = "unassigned"

    target_node["mac"] = normalized
    target_node["status"] = status
    target_node["last_flashed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if display_name:
        target_node["display_name"] = display_name

    save_node_registry(registry)
    return target_node


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
