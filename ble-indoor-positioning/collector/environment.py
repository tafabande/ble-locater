"""Indoor Positioning — Experimental Environment Data Model.

Represents the physical 2D layout of the experiment: test area boundaries,
4 BLE anchor receiver nodes, target tag token, and geometric barrier obstacles.
Provides serialization to JSON session metadata and automated raycast LOS/NLOS analysis.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from collector.geometry import (
    euclidean_distance,
    segment_intersects_circle,
    segment_intersects_oriented_box,
)


BARRIER_TYPES = [
    "Concrete wall",
    "Wall",
    "Door",
    "Human body",
    "Cloth",
    "WiFi source",
    "Bluetooth device",
    "Other",
]

BARRIER_SHAPES = [
    "Rectangle",
    "Line",
    "Circle",
]


@dataclass
class ExperimentArea:
    """Dimensions and grid divisions of the physical laboratory test area."""
    width_m: float = 5.0
    height_m: float = 5.0
    grid_spacing_m: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width_m": float(self.width_m),
            "height_m": float(self.height_m),
            "grid_spacing_m": float(self.grid_spacing_m),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExperimentArea:
        return cls(
            width_m=float(data.get("width_m", 5.0)),
            height_m=float(data.get("height_m", 5.0)),
            grid_spacing_m=float(data.get("grid_spacing_m", 1.0)),
        )


@dataclass
class AnchorNode:
    """BLE receiver anchor node placed on the physical grid."""
    id: str  # e.g. "ANCHOR_01"
    label: str  # e.g. "Node A"
    x_m: float
    y_m: float
    is_placed: bool = True

    @property
    def anchor_id(self) -> str:
        return self.id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "x_m": round(float(self.x_m), 3),
            "y_m": round(float(self.y_m), 3),
            "is_placed": bool(self.is_placed),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AnchorNode:
        return cls(
            id=str(data["id"]),
            label=str(data.get("label", data["id"])),
            x_m=float(data.get("x_m", 0.0)),
            y_m=float(data.get("y_m", 0.0)),
            is_placed=bool(data.get("is_placed", True)),
        )


class TargetNode:
    """Movable BLE beacon tag whose ground-truth location is being recorded."""
    def __init__(
        self,
        id: Optional[str] = None,
        label: str = "Target",
        device_mac: Optional[str] = None,
        x_m: float = 2.5,
        y_m: float = 2.5,
        movement_mode: str = "stationary",
        target_id: Optional[str] = None,
        mac: Optional[str] = None,
    ) -> None:
        self.id = id or target_id or "TARGET_01"
        self.label = label
        self.device_mac = device_mac or mac or "52:06:26:03:01:DA"
        self.x_m = float(x_m)
        self.y_m = float(y_m)
        self.movement_mode = movement_mode

    @property
    def target_id(self) -> str:
        return self.id

    @property
    def mac(self) -> str:
        return self.device_mac

    @mac.setter
    def mac(self, val: str) -> None:
        self.device_mac = val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "device_mac": self.device_mac,
            "x_m": round(float(self.x_m), 3),
            "y_m": round(float(self.y_m), 3),
            "movement_mode": self.movement_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TargetNode:
        return cls(
            id=str(data.get("id", data.get("target_id", "TARGET_01"))),
            label=str(data.get("label", "Target")),
            device_mac=str(data.get("device_mac", data.get("mac", "52:06:26:03:01:DA"))),
            x_m=float(data.get("x_m", 2.5)),
            y_m=float(data.get("y_m", 2.5)),
            movement_mode=str(data.get("movement_mode", "stationary")),
        )


class BarrierObject:
    """Environmental obstacle or RF interference source placed on the grid."""
    def __init__(
        self,
        id: Optional[str] = None,
        name: str = "Wall 1",
        barrier_type: Optional[str] = None,
        shape: str = "Rectangle",
        x_m: float = 2.0,
        y_m: float = 2.0,
        width_m: float = 2.0,
        depth_m: float = 0.2,
        rotation_deg: float = 0.0,
        blocks_los: bool = True,
        obstacle_type: Optional[str] = None,
    ) -> None:
        self.id = id or str(uuid.uuid4())[:8]
        self.name = name
        self.barrier_type = barrier_type or obstacle_type or "Concrete wall"
        self.shape = shape
        self.x_m = float(x_m)
        self.y_m = float(y_m)
        self.width_m = float(width_m)
        self.depth_m = float(depth_m)
        self.rotation_deg = float(rotation_deg)
        self.blocks_los = bool(blocks_los)

    @property
    def obstacle_type(self) -> str:
        return self.barrier_type

    @obstacle_type.setter
    def obstacle_type(self, val: str) -> None:
        self.barrier_type = val

    def intersects_path(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> bool:
        """Determine whether this barrier occludes the straight-line RF path between p1 and p2."""
        if not self.blocks_los:
            return False

        if self.shape == "Circle":
            radius = max(0.1, self.width_m / 2.0)
            return segment_intersects_circle(p1, p2, (self.x_m, self.y_m), radius)

        # Default Rectangle / Line oriented box
        w = max(0.05, self.width_m)
        d = max(0.05, self.depth_m)
        return segment_intersects_oriented_box(p1, p2, (self.x_m, self.y_m), w, d, self.rotation_deg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "barrier_type": self.barrier_type,
            "shape": self.shape,
            "x_m": round(float(self.x_m), 3),
            "y_m": round(float(self.y_m), 3),
            "width_m": round(float(self.width_m), 3),
            "depth_m": round(float(self.depth_m), 3),
            "rotation_deg": round(float(self.rotation_deg), 1),
            "blocks_los": bool(self.blocks_los),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BarrierObject:
        return cls(
            id=str(data.get("id", str(uuid.uuid4())[:8])),
            name=str(data.get("name", "Barrier")),
            barrier_type=str(data.get("barrier_type", data.get("obstacle_type", "Concrete wall"))),
            shape=str(data.get("shape", "Rectangle")),
            x_m=float(data.get("x_m", 2.0)),
            y_m=float(data.get("y_m", 2.0)),
            width_m=float(data.get("width_m", 2.0)),
            depth_m=float(data.get("depth_m", 0.2)),
            rotation_deg=float(data.get("rotation_deg", 0.0)),
            blocks_los=bool(data.get("blocks_los", True)),
        )


class EnvironmentLayout:
    """Complete experimental environment layout model."""

    def __init__(
        self,
        area: Optional[ExperimentArea] = None,
        anchors: Optional[Any] = None,
        target: Optional[TargetNode] = None,
        barriers: Optional[List[BarrierObject]] = None,
    ) -> None:
        self.area = area or ExperimentArea()
        if isinstance(anchors, list):
            self.anchors = {a.id: a for a in anchors}
        elif isinstance(anchors, dict):
            self.anchors = anchors
        else:
            self.anchors = self._create_default_anchors(self.area.width_m, self.area.height_m)
        self.target = target or TargetNode(x_m=self.area.width_m / 2.0, y_m=self.area.height_m / 2.0)
        self.barriers = barriers if barriers is not None else []

    @classmethod
    def create_default(cls, width_m: float = 5.0, height_m: float = 5.0) -> EnvironmentLayout:
        return cls(area=ExperimentArea(width_m=width_m, height_m=height_m))

    @staticmethod
    def _create_default_anchors(width_m: float, height_m: float) -> Dict[str, AnchorNode]:
        """Generate default 4-anchor setup at the four corners of the test area."""
        return {
            "ANCHOR_01": AnchorNode(id="ANCHOR_01", label="Node A", x_m=0.0, y_m=0.0),
            "ANCHOR_02": AnchorNode(id="ANCHOR_02", label="Node B", x_m=width_m, y_m=0.0),
            "ANCHOR_03": AnchorNode(id="ANCHOR_03", label="Node C", x_m=0.0, y_m=height_m),
            "ANCHOR_04": AnchorNode(id="ANCHOR_04", label="Node D", x_m=width_m, y_m=height_m),
        }

    def reset_to_area(self, width_m: float, height_m: float, grid_spacing_m: float = 1.0) -> None:
        """Update test area dimensions and reposition corner anchors if at previous boundaries."""
        old_w = self.area.width_m
        old_h = self.area.height_m

        self.area.width_m = width_m
        self.area.height_m = height_m
        self.area.grid_spacing_m = grid_spacing_m

        # If anchors were at old corners, update them
        for anc in self.anchors.values():
            if abs(anc.x_m - old_w) < 0.05:
                anc.x_m = width_m
            if abs(anc.y_m - old_h) < 0.05:
                anc.y_m = height_m
            # Clamp to boundaries
            anc.x_m = min(width_m, anc.x_m)
            anc.y_m = min(height_m, anc.y_m)

        if self.target:
            self.target.x_m = min(width_m, self.target.x_m)
            self.target.y_m = min(height_m, self.target.y_m)

    def get_anchor_distances(self) -> Dict[str, float]:
        """Compute Euclidean distance in metres from target to each placed anchor."""
        if not self.target:
            return {}
        target_pos = (self.target.x_m, self.target.y_m)
        distances = {}
        for anc_id, anc in self.anchors.items():
            if anc.is_placed:
                dist = euclidean_distance((anc.x_m, anc.y_m), target_pos)
                distances[anc_id] = round(dist, 3)
        return distances

    def get_anchor_los_status(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Evaluate geometric Line-of-Sight between target and each placed anchor.

        Returns:
            Dict mapping anchor_id to tuple of (is_los: bool, obstacle_name: Optional[str]).
        """
        if not self.target:
            return {}

        target_pos = (self.target.x_m, self.target.y_m)
        status = {}
        for anc_id, anc in self.anchors.items():
            if not anc.is_placed:
                continue

            anc_pos = (anc.x_m, anc.y_m)
            is_blocked = False
            blocking_barrier: Optional[BarrierObject] = None

            for barrier in self.barriers:
                if barrier.intersects_path(anc_pos, target_pos):
                    is_blocked = True
                    blocking_barrier = barrier
                    break

            if is_blocked and blocking_barrier:
                status[anc_id] = (False, blocking_barrier.barrier_type or blocking_barrier.name)
            else:
                status[anc_id] = (True, None)

        return status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete environment model to structured dictionary."""
        return {
            "area": self.area.to_dict(),
            "anchors": {k: v.to_dict() for k, v in self.anchors.items()},
            "target": self.target.to_dict() if self.target else None,
            "barriers": [b.to_dict() for b in self.barriers],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EnvironmentLayout:
        """Reconstruct complete environment model from structured dictionary."""
        area = ExperimentArea.from_dict(data.get("area", {}))
        anchors = {}
        for k, v in data.get("anchors", {}).items():
            anchors[k] = AnchorNode.from_dict(v)

        target = TargetNode.from_dict(data["target"]) if data.get("target") else None
        barriers = [BarrierObject.from_dict(b) for b in data.get("barriers", [])]
        return cls(area=area, anchors=anchors, target=target, barriers=barriers)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> EnvironmentLayout:
        return cls.from_dict(json.loads(json_str))
