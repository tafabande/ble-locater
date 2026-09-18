"""Indoor Positioning — Physical 2D Coordinate & Geometry Engine.

Provides exact mapping between physical metres and canvas pixels,
grid snapping, Euclidean distance calculations, oriented bounding box math,
and 2D ray/segment intersection algorithms for automated Line-of-Sight (LOS)
and Non-Line-of-Sight (NLOS) experimental annotation.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


class PhysicalCoordinateSystem:
    """Manages scaling and coordinate transformation between physical metres and canvas pixels.

    Physical coordinate convention:
    (0.0, 0.0) is at the bottom-left corner of the test area.
    X increases horizontally to the right: [0.0, width_m].
    Y increases vertically upwards: [0.0, height_m].
    """

    def __init__(
        self,
        width_m: float = 5.0,
        height_m: float = 5.0,
        canvas_width_px: int = 800,
        canvas_height_px: int = 600,
        margin_px: int = 40,
        area_width_m: Optional[float] = None,
        area_height_m: Optional[float] = None,
    ) -> None:
        self.width_m = max(0.5, float(area_width_m if area_width_m is not None else width_m))
        self.height_m = max(0.5, float(area_height_m if area_height_m is not None else height_m))
        self.canvas_width_px = max(100, canvas_width_px)
        self.canvas_height_px = max(100, canvas_height_px)
        self.margin_px = margin_px

    def set_dimensions(self, width_m: float, height_m: float) -> None:
        """Update physical dimensions of the experimental area."""
        self.width_m = max(0.5, float(width_m))
        self.height_m = max(0.5, float(height_m))

    def set_canvas_size(self, width_px: int, height_px: int) -> None:
        """Update available canvas drawing dimensions."""
        self.canvas_width_px = max(100, width_px)
        self.canvas_height_px = max(100, height_px)

    @property
    def scale(self) -> float:
        """Pixels per physical metre, preserving true aspect ratio."""
        usable_w = max(10, self.canvas_width_px - 2 * self.margin_px)
        usable_h = max(10, self.canvas_height_px - 2 * self.margin_px)
        return min(usable_w / self.width_m, usable_h / self.height_m)

    @property
    def offset_x(self) -> float:
        """Horizontal pixel offset to center the grid on canvas."""
        usable_w = max(10, self.canvas_width_px - 2 * self.margin_px)
        drawn_w = self.width_m * self.scale
        return self.margin_px + (usable_w - drawn_w) / 2.0

    @property
    def offset_y(self) -> float:
        """Vertical pixel offset to center the grid on canvas."""
        usable_h = max(10, self.canvas_height_px - 2 * self.margin_px)
        drawn_h = self.height_m * self.scale
        return self.margin_px + (usable_h - drawn_h) / 2.0

    def to_canvas(self, x_m: float, y_m: float) -> Tuple[float, float]:
        """Convert physical coordinates (metres) to canvas coordinates (pixels)."""
        u = self.offset_x + (x_m * self.scale)
        # Invert Y so 0m is at the bottom
        v = self.offset_y + ((self.height_m - y_m) * self.scale)
        return round(u, 2), round(v, 2)

    def to_physical(self, u_px: float, v_px: float, clamp: bool = True) -> Tuple[float, float]:
        """Convert canvas pixel coordinates back to physical metres."""
        x_m = (u_px - self.offset_x) / self.scale
        y_m = self.height_m - ((v_px - self.offset_y) / self.scale)
        if clamp:
            x_m = max(0.0, min(self.width_m, x_m))
            y_m = max(0.0, min(self.height_m, y_m))
        return round(x_m, 3), round(y_m, 3)

    to_canvas_coords = to_canvas
    to_physical_coords = to_physical


def snap_to_grid(*args, **kwargs) -> Any:
    """Snap physical coordinates to nearest grid interval.

    Supports:
      snap_to_grid(x, y, grid_spacing) -> (snapped_x, snapped_y)
      snap_to_grid(val, grid_spacing) -> snapped_val
    """
    if len(args) == 3:
        x, y, grid_spacing = args
        if grid_spacing <= 0:
            return x, y
        return round(round(x / grid_spacing) * grid_spacing, 3), round(round(y / grid_spacing) * grid_spacing, 3)
    elif len(args) == 2:
        val, grid_spacing = args
        if grid_spacing <= 0:
            return val
        return round(round(val / grid_spacing) * grid_spacing, 3)
    elif len(args) == 1:
        return args[0]
    return args


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate exact Euclidean distance between two 2D points in physical metres."""
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def rotate_point(point: Tuple[float, float], center: Tuple[float, float], angle_deg: float) -> Tuple[float, float]:
    """Rotate a 2D point counterclockwise around a center point by angle in degrees."""
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    rx = center[0] + (dx * cos_a - dy * sin_a)
    ry = center[1] + (dx * sin_a + dy * cos_a)
    return rx, ry


def _ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Test if triplet of points A, B, C is oriented counter-clockwise."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segment_intersects_segment(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    """Determine whether line segment p1-p2 strictly intersects line segment p3-p4."""
    # Orientation test
    if (_ccw(p1, p3, p4) != _ccw(p2, p3, p4)) and (_ccw(p1, p2, p3) != _ccw(p1, p2, p4)):
        return True

    # Check collinear overlap cases
    def on_segment(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> bool:
        return (
            min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6 and
            min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6 and
            abs((b[1] - a[1]) * (p[0] - a[0]) - (b[0] - a[0]) * (p[1] - a[1])) < 1e-5
        )

    return (
        on_segment(p1, p3, p4) or
        on_segment(p2, p3, p4) or
        on_segment(p3, p1, p2) or
        on_segment(p4, p1, p2)
    )


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def get_oriented_box_corners(
    center: Tuple[float, float],
    width: float,
    depth: float,
    rotation_deg: float,
) -> List[Tuple[float, float]]:
    """Return the four corner coordinates of an oriented rectangle."""
    hw = width / 2.0
    hd = depth / 2.0
    cx, cy = center

    # Local corners before rotation
    local_corners = [
        (cx - hw, cy - hd),
        (cx + hw, cy - hd),
        (cx + hw, cy + hd),
        (cx - hw, cy + hd),
    ]

    if abs(rotation_deg) < 1e-3:
        return local_corners

    return [rotate_point(pt, center, rotation_deg) for pt in local_corners]


def segment_intersects_oriented_box(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    center: Optional[Tuple[float, float]] = None,
    width: float = 2.0,
    depth: float = 0.2,
    rotation_deg: float = 0.0,
    box_center: Optional[Tuple[float, float]] = None,
) -> bool:
    """Test whether segment p1-p2 intersects an oriented rectangular barrier."""
    actual_center = center if center is not None else (box_center if box_center is not None else (0.0, 0.0))
    corners = get_oriented_box_corners(actual_center, width, depth, rotation_deg)

    # 1. If either endpoint is inside the box, the segment intersects
    if point_in_polygon(p1, corners) or point_in_polygon(p2, corners):
        return True

    # 2. Check intersection against each of the 4 edges
    for i in range(4):
        c_a = corners[i]
        c_b = corners[(i + 1) % 4]
        if segment_intersects_segment(p1, p2, c_a, c_b):
            return True

    return False


def segment_intersects_circle(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    center: Tuple[float, float],
    radius: float,
) -> bool:
    """Test whether segment p1-p2 intersects a radial circular obstacle area."""
    # Distance from center to line segment p1-p2
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = center

    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq < 1e-9:
        return euclidean_distance(p1, center) <= radius

    # Projection parameter t clamped to [0, 1]
    t = max(0.0, min(1.0, ((cx - x1) * dx + (cy - y1) * dy) / seg_len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    dist_to_seg = euclidean_distance((proj_x, proj_y), center)
    return dist_to_seg <= radius


def compute_path_obstruction(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    barriers: List[Any],
) -> Tuple[bool, Optional[str]]:
    """Evaluate whether any barrier obstructs the direct line of sight between p1 and p2.

    Args:
        p1: Start point (x, y) in physical metres.
        p2: End point (x, y) in physical metres.
        barriers: List of barrier objects or dictionaries.

    Returns:
        (is_los: bool, blocker_type: Optional[str])
    """
    for barrier in barriers:
        if hasattr(barrier, "intersects_path"):
            if barrier.intersects_path(p1, p2):
                blocker = getattr(barrier, "obstacle_type", getattr(barrier, "barrier_type", getattr(barrier, "name", "Obstacle")))
                return False, blocker
        elif isinstance(barrier, dict):
            if not barrier.get("blocks_los", True):
                continue
            b_shape = barrier.get("shape", "Rectangle")
            bx = float(barrier.get("x_m", 0.0))
            by = float(barrier.get("y_m", 0.0))
            bw = float(barrier.get("width_m", 1.0))
            bd = float(barrier.get("depth_m", 0.2))
            brot = float(barrier.get("rotation_deg", 0.0))
            b_type = barrier.get("obstacle_type", barrier.get("barrier_type", "Obstacle"))

            if b_shape == "Circle":
                rad = max(0.1, bw / 2.0)
                if segment_intersects_circle(p1, p2, (bx, by), rad):
                    return False, b_type
            else:
                if segment_intersects_oriented_box(p1, p2, (bx, by), bw, bd, brot):
                    return False, b_type

    return True, None
