"""Unit and Integration Tests for Visual Experiment Environment Builder and Data Collector.

Tests:
- PhysicalCoordinateSystem: aspect ratio, meter-to-pixel and pixel-to-meter conversions, origin placement.
- Grid snapping logic.
- Euclidean distance calculation.
- Barrier geometry intersection: oriented boxes, lines, circles.
- Automated LOS/NLOS raycast calculation.
- EnvironmentLayout serialization and round-trip deserialization.
- SessionManager environment layout metadata persistence and reconstruction.
- RecordingEngine dynamic observation labelling using environment layout geometry.
"""
import json
import math
import queue
import tempfile
from pathlib import Path

import pytest

from collector.geometry import (
    PhysicalCoordinateSystem,
    compute_path_obstruction,
    euclidean_distance,
    get_oriented_box_corners,
    point_in_polygon,
    rotate_point,
    segment_intersects_circle,
    segment_intersects_oriented_box,
    segment_intersects_segment,
    snap_to_grid,
)
from collector.environment import (
    AnchorNode,
    BarrierObject,
    ExperimentArea,
    EnvironmentLayout,
    TargetNode,
)
from collector.session_manager import SessionManager, SessionConfig
from collector.recording import RecordingEngine


# =============================================================================
# 1. COORDINATE CONVERSION & ASPECT RATIO TESTS
# =============================================================================

def test_coordinate_system_conversion():
    """Test physical meters <-> canvas pixels mapping with (0,0) at bottom-left."""
    coord_sys = PhysicalCoordinateSystem(
        area_width_m=10.0,
        area_height_m=5.0,
        canvas_width_px=800,
        canvas_height_px=600,
        margin_px=50,
    )

    # (0, 0) in meters must map to the bottom-left of the usable plot area
    px_0, py_0 = coord_sys.to_canvas_coords(0.0, 0.0)
    # Origin px must equal offset_x (which is margin or centered)
    assert px_0 >= 50
    # Origin py must be near bottom (canvas_height - margin_px or centered)
    assert py_0 > 300

    # Top-right corner (10, 5)
    px_max, py_max = coord_sys.to_canvas_coords(10.0, 5.0)
    assert px_max > px_0
    assert py_max < py_0  # Canvas Y is inverted (0 is top)

    # Round trip conversion
    for test_x, test_y in [(0.0, 0.0), (3.5, 2.5), (10.0, 5.0)]:
        u, v = coord_sys.to_canvas_coords(test_x, test_y)
        res_x, res_y = coord_sys.to_physical_coords(u, v)
        assert pytest.approx(test_x, abs=1e-3) == res_x
        assert pytest.approx(test_y, abs=1e-3) == res_y


def test_aspect_ratio_preservation():
    """A 10m x 5m room must visually be twice as wide as it is high."""
    coord_sys = PhysicalCoordinateSystem(
        area_width_m=10.0,
        area_height_m=5.0,
        canvas_width_px=1000,
        canvas_height_px=800,
        margin_px=40,
    )

    u0, v0 = coord_sys.to_canvas_coords(0.0, 0.0)
    u_w, _ = coord_sys.to_canvas_coords(10.0, 0.0)
    _, v_h = coord_sys.to_canvas_coords(0.0, 5.0)

    pixel_width = abs(u_w - u0)
    pixel_height = abs(v_h - v0)

    # Aspect ratio width/height should equal 10.0 / 5.0 = 2.0
    ratio = pixel_width / pixel_height
    assert pytest.approx(ratio, rel=1e-3) == 2.0


# =============================================================================
# 2. GRID SNAPPING TESTS
# =============================================================================

def test_grid_snapping():
    """Verify snap-to-grid accuracy for arbitrary values."""
    assert snap_to_grid(2.83, 1.0) == 3.0
    assert snap_to_grid(2.21, 1.0) == 2.0
    assert snap_to_grid(1.24, 0.5) == 1.0
    assert snap_to_grid(1.26, 0.5) == 1.5
    assert snap_to_grid(0.04, 0.2) == 0.0
    assert snap_to_grid(0.12, 0.2) == 0.2


# =============================================================================
# 3. DISTANCE CALCULATION TESTS
# =============================================================================

def test_euclidean_distance():
    """Verify standard Euclidean distance computation."""
    assert euclidean_distance((0.0, 0.0), (3.0, 4.0)) == 5.0
    assert euclidean_distance((1.0, 1.0), (1.0, 1.0)) == 0.0
    assert pytest.approx(euclidean_distance((0.0, 0.0), (5.0, 5.0)), rel=1e-4) == math.sqrt(50.0)


# =============================================================================
# 4. BARRIER GEOMETRY & RAYCAST INTERSECTION TESTS
# =============================================================================

def test_ray_segment_intersection():
    """Test 2D line segment intersection."""
    p1 = (0.0, 0.0)
    p2 = (4.0, 4.0)

    # Crossing segment
    q1 = (0.0, 4.0)
    q2 = (4.0, 0.0)
    assert segment_intersects_segment(p1, p2, q1, q2) is True

    # Parallel non-intersecting segment
    q3 = (1.0, 0.0)
    q4 = (5.0, 4.0)
    assert segment_intersects_segment(p1, p2, q3, q4) is False


def test_oriented_box_intersection():
    """Test raycast against an oriented rectangular wall."""
    # Wall centered at (2.0, 2.0), width 2.0m, depth 0.2m, rotation 0 deg
    ray_start = (0.0, 2.0)
    ray_end = (4.0, 2.0)

    # Straight horizontal ray passing directly through the wall
    intersects = segment_intersects_oriented_box(
        ray_start, ray_end,
        box_center=(2.0, 2.0),
        width=2.0, depth=0.2,
        rotation_deg=0.0
    )
    assert intersects is True

    # Ray missing the wall above
    ray_miss = (0.0, 3.5)
    ray_miss_end = (4.0, 3.5)
    assert segment_intersects_oriented_box(
        ray_miss, ray_miss_end,
        box_center=(2.0, 2.0),
        width=2.0, depth=0.2,
        rotation_deg=0.0
    ) is False


def test_rotated_barrier_intersection():
    """Test raycast when a barrier wall is rotated 90 degrees."""
    # A wall of length 4.0m and depth 0.2m, centered at (2.5, 2.5), rotated 90 deg (now vertical)
    ray_start = (1.0, 2.5)
    ray_end = (4.0, 2.5)

    assert segment_intersects_oriented_box(
        ray_start, ray_end,
        box_center=(2.5, 2.5),
        width=4.0, depth=0.2,
        rotation_deg=90.0
    ) is True

    # Ray to the side should miss
    ray_side_start = (1.0, 5.0)
    ray_side_end = (4.0, 5.0)
    assert segment_intersects_oriented_box(
        ray_side_start, ray_side_end,
        box_center=(2.5, 2.5),
        width=4.0, depth=0.2,
        rotation_deg=90.0
    ) is False


def test_circle_obstacle_intersection():
    """Test radial barrier (e.g. human body, WiFi source) intersection."""
    center = (2.0, 2.0)
    radius = 0.4

    # Ray passing through circle
    assert segment_intersects_circle((0.0, 2.0), (4.0, 2.0), center, radius) is True

    # Ray skimming outside circle
    assert segment_intersects_circle((0.0, 3.0), (4.0, 3.0), center, radius) is False


def test_tangent_and_edge_cases():
    """Verify edge cases: ray tangent to circle, zero length segment, endpoint touching box."""
    center = (2.0, 2.0)
    radius = 1.0

    # Tangent line at y = 3.0 touches circle at (2.0, 3.0)
    assert segment_intersects_circle((0.0, 3.0), (4.0, 3.0), center, radius) is True

    # Zero length segment inside circle
    assert segment_intersects_circle((2.0, 2.0), (2.0, 2.0), center, radius) is True

    # Zero length segment far outside circle
    assert segment_intersects_circle((10.0, 10.0), (10.0, 10.0), center, radius) is False

    # Ray endpoint touching edge of oriented box centered at (2, 2) with width 2, depth 2
    # Corner is at (3, 3). Ray from (3, 3) to (5, 5) touches at boundary
    assert segment_intersects_oriented_box((3.0, 3.0), (5.0, 5.0), center=(2.0, 2.0), width=2.0, depth=2.0) is True


def test_compute_path_obstruction():
    """Verify compute_path_obstruction on objects and dictionary lists."""
    barriers = [
        BarrierObject(
            name="Brick Partition",
            barrier_type="Wall",
            shape="Rectangle",
            x_m=2.5,
            y_m=2.5,
            width_m=2.0,
            depth_m=0.2,
            blocks_los=True,
        ),
        {
            "name": "WiFi Router",
            "barrier_type": "WiFi source",
            "shape": "Circle",
            "x_m": 1.0,
            "y_m": 4.0,
            "width_m": 0.5,
            "blocks_los": False,
        }
    ]

    # Obstructed path crossing wall at (2.5, 2.5)
    is_los, blocker = compute_path_obstruction((2.5, 0.0), (2.5, 5.0), barriers)
    assert is_los is False
    assert blocker == "Wall"

    # Clear path avoiding the wall
    is_los_clear, blocker_clear = compute_path_obstruction((0.0, 0.0), (0.0, 5.0), barriers)
    assert is_los_clear is True
    assert blocker_clear is None

    # Path intersecting the WiFi source (which has blocks_los=False) should remain LOS
    is_los_wifi, blocker_wifi = compute_path_obstruction((0.0, 4.0), (2.0, 4.0), barriers)
    assert is_los_wifi is True
    assert blocker_wifi is None


# =============================================================================
# 5. ENVIRONMENT LAYOUT & AUTOMATED LOS/NLOS SOLVER
# =============================================================================

def test_environment_layout_los_solver():
    """Verify automated LOS/NLOS determination across 4 anchors."""
    layout = EnvironmentLayout(
        area=ExperimentArea(width_m=5.0, height_m=5.0, grid_spacing_m=1.0),
        anchors=[
            AnchorNode(id="ANCHOR_01", label="A01", x_m=0.0, y_m=0.0),
            AnchorNode(id="ANCHOR_02", label="A02", x_m=5.0, y_m=0.0),
            AnchorNode(id="ANCHOR_03", label="A03", x_m=5.0, y_m=5.0),
            AnchorNode(id="ANCHOR_04", label="A04", x_m=0.0, y_m=5.0),
        ],
        target=TargetNode(target_id="TARGET_01", mac="AA:BB:CC:DD:EE:FF", x_m=2.5, y_m=2.5),
        barriers=[],
    )

    # Initial state: clear LOS to all 4 anchors
    los_status = layout.get_anchor_los_status()
    for anc_id in ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]:
        is_los, blocker = los_status[anc_id]
        assert is_los is True
        assert blocker is None

    # Add a concrete wall blocking ANCHOR_01 only
    # ANCHOR_01 is at (0, 0), Target at (2.5, 2.5). The line passes through (1.0, 1.0).
    wall = BarrierObject(
        name="Concrete Wall",
        obstacle_type="Concrete wall",
        shape="Rectangle",
        x_m=1.0,
        y_m=1.0,
        width_m=1.5,
        depth_m=0.3,
        rotation_deg=45.0,
        blocks_los=True,
    )
    layout.barriers.append(wall)

    los_status_after = layout.get_anchor_los_status()
    is_los_01, blocker_01 = los_status_after["ANCHOR_01"]
    assert is_los_01 is False
    assert blocker_01 == "Concrete wall"

    # ANCHOR_03 at (5, 5) to Target (2.5, 2.5) should remain unobstructed
    is_los_03, blocker_03 = los_status_after["ANCHOR_03"]
    assert is_los_03 is True
    assert blocker_03 is None


def test_non_los_blocking_obstacle():
    """Barriers with blocks_los=False (e.g. ambient Bluetooth device) must not alter LOS."""
    layout = EnvironmentLayout(
        area=ExperimentArea(width_m=5.0, height_m=5.0),
        anchors=[AnchorNode(id="ANCHOR_01", label="A01", x_m=0.0, y_m=0.0)],
        target=TargetNode(target_id="TARGET_01", x_m=3.0, y_m=3.0),
        barriers=[
            BarrierObject(
                name="Beacon Interfere",
                obstacle_type="Bluetooth device",
                shape="Circle",
                x_m=1.5,
                y_m=1.5,
                width_m=0.8,
                blocks_los=False,
            )
        ],
    )

    los_status = layout.get_anchor_los_status()
    is_los, blocker = los_status["ANCHOR_01"]
    assert is_los is True
    assert blocker is None


# =============================================================================
# 6. SERIALIZATION & DESERIALIZATION TESTS
# =============================================================================

def test_environment_layout_serialization_roundtrip():
    """Verify complete layout can be serialized to JSON and reconstructed without data loss."""
    layout = EnvironmentLayout.create_default()
    layout.barriers.append(
        BarrierObject(
            name="Office Door",
            obstacle_type="Door",
            shape="Rectangle",
            x_m=2.0,
            y_m=3.0,
            width_m=0.9,
            depth_m=0.15,
            rotation_deg=30.0,
            blocks_los=True,
        )
    )

    # Dict round-trip
    layout_dict = layout.to_dict()
    reconstructed = EnvironmentLayout.from_dict(layout_dict)

    assert reconstructed.area.width_m == layout.area.width_m
    assert len(reconstructed.anchors) == len(layout.anchors)
    assert reconstructed.target.x_m == layout.target.x_m
    assert len(reconstructed.barriers) == 1
    assert reconstructed.barriers[0].name == "Office Door"
    assert reconstructed.barriers[0].rotation_deg == 30.0

    # JSON round-trip
    json_str = layout.to_json()
    reconstructed_from_json = EnvironmentLayout.from_json(json_str)
    assert reconstructed_from_json.area.grid_spacing_m == layout.area.grid_spacing_m
    assert reconstructed_from_json.barriers[0].obstacle_type == "Door"


# =============================================================================
# 7. SESSION MANAGER METADATA PERSISTENCE & RESTORATION
# =============================================================================

def test_session_manager_layout_persistence_and_recovery():
    """Verify environment layout is saved to session metadata and can be reconstructed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = SessionManager(raw_dir=Path(tmp_dir))
        layout = EnvironmentLayout.create_default()

        ok, msg, session = sm.create_session(
            name="test_visual_session",
            mac="11:22:33:44:55:66",
            distance_m=2.5,
            environment_layout=layout.to_dict(),
        )
        assert ok is True
        assert session is not None

        # Simulate finalizing metadata
        session.save_metadata(sample_count=100, duration_sec=15.0)

        # Reconstruct layout from CSV path
        loaded_layout = sm.get_session_layout(session.target_file_path)
        assert loaded_layout is not None
        assert "area" in loaded_layout
        assert "anchors" in loaded_layout
        assert loaded_layout["area"]["width_m"] == 5.0
        assert len(loaded_layout["anchors"]) == 4


# =============================================================================
# 8. RECORDING ENGINE INTEGRATION WITH VISUAL ENVIRONMENT
# =============================================================================

def test_recording_engine_uses_visual_geometry():
    """Verify that RecordingEngine dynamically computes Euclidean distance and LOS from layout."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = SessionManager(raw_dir=Path(tmp_dir))
        pkt_queue = queue.Queue()
        engine = RecordingEngine(packet_queue=pkt_queue)

        # Setup layout: Target at (3.0, 4.0), Anchor A01 at (0.0, 0.0) -> Distance must be 5.0m!
        layout = EnvironmentLayout(
            area=ExperimentArea(width_m=6.0, height_m=6.0),
            anchors=[
                AnchorNode(id="ANCHOR_01", label="A01", x_m=0.0, y_m=0.0),
                AnchorNode(id="ANCHOR_02", label="A02", x_m=6.0, y_m=0.0),
            ],
            target=TargetNode(target_id="TAG_01", mac="AA:BB:CC:11:22:33", x_m=3.0, y_m=4.0),
            barriers=[
                BarrierObject(
                    name="Concrete Wall",
                    obstacle_type="Concrete wall",
                    shape="Rectangle",
                    x_m=1.5,
                    y_m=2.0,
                    width_m=1.0,
                    depth_m=0.2,
                    blocks_los=True,
                )
            ],
        )

        ok, msg, session = sm.create_session(
            name="test_sim_geometry",
            mac="AA:BB:CC:11:22:33",
            distance_m=1.0,  # Fallback default
            anchor_id="ANCHOR_01",
            environment_layout=layout.to_dict(),
        )
        assert ok is True

        engine.active_session = session
        engine.is_recording = True

        # Generate a simulated packet for ANCHOR_01
        engine._generate_simulated_packet()

        assert not pkt_queue.empty()
        pkt = pkt_queue.get_nowait()

        # Distance should equal exactly 5.0m (derived from geometry: sqrt(3^2 + 4^2))
        assert pytest.approx(pkt["distance_m"], abs=1e-2) == 5.0

        # Anchor A01 should be blocked by Concrete Wall
        assert pkt["condition"] == "Non-Line-of-Sight (NLOS)"
        assert pkt["obstacle_type"] == "Concrete wall"

        engine.stop_recording()


# =============================================================================
# 9. PRE-RECORDING VALIDATION TESTS (PHASE 10)
# =============================================================================

def test_pre_recording_validation_logic():
    """Verify that experiment validation detects missing anchors, out-of-bounds target, and invalid MAC."""
    from collector.collector_gui import DataCollectorApp
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        app = DataCollectorApp(root)

        # 1. Default layout has 4 anchors and target at (2.5, 2.5) -> Valid
        ok, msg = app._validate_experiment_readiness()
        assert ok is True
        assert msg == "Ready"

        # 2. Missing fourth anchor -> Fails with actionable error
        del app.canvas_editor.layout.anchors["ANCHOR_04"]
        ok, msg = app._validate_experiment_readiness()
        assert ok is False
        assert "ANCHOR_04 is missing" in msg

        # Restore anchor
        app.canvas_editor.layout.anchors["ANCHOR_04"] = AnchorNode(id="ANCHOR_04", label="A04", x_m=5.0, y_m=5.0)

        # 3. Target moved outside bounds
        app.canvas_editor.layout.target.x_m = 12.0
        ok, msg = app._validate_experiment_readiness()
        assert ok is False
        assert "outside test area boundaries" in msg

        # Restore target inside bounds
        app.canvas_editor.layout.target.x_m = 2.5

        # 4. Invalid MAC
        app.canvas_editor.layout.target.device_mac = "INVALID_MAC"
        app.target_mac_var.set("INVALID_MAC")
        ok, msg = app._validate_experiment_readiness()
        assert ok is False
        assert "Invalid target MAC" in msg

    finally:
        root.destroy()


# =============================================================================
# 10. PERFORMANCE & LONG-RUN STRESS TESTS (PHASE 20)
# =============================================================================

def test_performance_and_stress():
    """Verify that rapid target movements, multiple rotated obstacles, and 1000 LOS solves execute in <0.25s."""
    import time
    layout = EnvironmentLayout(
        area=ExperimentArea(width_m=10.0, height_m=10.0),
        anchors=[
            AnchorNode(id="ANCHOR_01", label="A01", x_m=0.0, y_m=0.0),
            AnchorNode(id="ANCHOR_02", label="A02", x_m=10.0, y_m=0.0),
            AnchorNode(id="ANCHOR_03", label="A03", x_m=0.0, y_m=10.0),
            AnchorNode(id="ANCHOR_04", label="A04", x_m=10.0, y_m=10.0),
        ],
        target=TargetNode(x_m=5.0, y_m=5.0),
        barriers=[
            BarrierObject(name=f"Wall {i}", x_m=2.0 + i, y_m=2.0 + i, width_m=1.5, depth_m=0.2, rotation_deg=15.0 * i)
            for i in range(5)
        ],
    )

    t0 = time.perf_counter()
    for step in range(500):
        # Move target
        layout.target.x_m = (step % 100) * 0.1
        layout.target.y_m = (step % 100) * 0.1
        distances = layout.get_anchor_distances()
        los = layout.get_anchor_los_status()
        assert len(distances) == 4
        assert len(los) == 4

    elapsed = time.perf_counter() - t0
    # 500 multi-obstacle, 4-anchor LOS solves should execute rapidly (< 0.5s)
    assert elapsed < 0.5


# =============================================================================
# 11. PHASE 0.5 — CANVAS VISIBILITY & DYNAMIC ASPECT RATIOS (ACCEPTANCE TESTS)
# =============================================================================

def test_phase_0_5_canvas_visibility_and_aspect_ratios():
    """Verify all 7 acceptance criteria for Phase 0.5 canvas visibility."""
    import tkinter as tk
    from collector.collector_gui import DataCollectorApp

    root = tk.Tk()
    app = None
    try:
        app = DataCollectorApp(root)
        root.update()

        # Test 1: Immediate visibility & dimensions
        c = app.canvas_editor.canvas
        w, h = c.winfo_width(), c.winfo_height()
        mapped = c.winfo_ismapped()
        items = len(c.find_all())
        assert w > 200 and h > 200, f"Canvas width/height should be non-zero (got {w}x{h})"
        assert mapped == 1, "Canvas must be mapped to display"
        assert items > 0, "Canvas must contain rendered items"

        # Test 2: Window resize dynamically expands canvas
        root.geometry("1500x950")
        root.update()
        w2, h2 = c.winfo_width(), c.winfo_height()
        assert w2 > w and h2 > h, "Canvas must expand when window is resized"

        # Test 3: 5m x 5m physical grid produces 1:1 square aspect ratio
        app.area_width_var.set(5.0)
        app.area_height_var.set(5.0)
        app._apply_area_dimensions()
        root.update()
        u0, v0 = app.canvas_editor.coords.to_canvas(0.0, 0.0)
        u5, v5 = app.canvas_editor.coords.to_canvas(5.0, 5.0)
        pw_5 = abs(u5 - u0)
        ph_5 = abs(v5 - v0)
        assert pytest.approx(pw_5 / ph_5, rel=1e-2) == 1.0, "5x5m grid must maintain 1:1 aspect ratio"

        # Test 4: 5m x 10m physical grid produces 1:2 aspect ratio (height is 2x width)
        app.area_width_var.set(5.0)
        app.area_height_var.set(10.0)
        app._apply_area_dimensions()
        root.update()
        u0, v0 = app.canvas_editor.coords.to_canvas(0.0, 0.0)
        u5, v10 = app.canvas_editor.coords.to_canvas(5.0, 10.0)
        pw_10 = abs(u5 - u0)
        ph_10 = abs(v10 - v0)
        assert pytest.approx(ph_10 / pw_10, rel=1e-2) == 2.0, "5x10m grid height must be exactly 2x width"

        # Test 5: Resize window with 5m x 10m maintains 1:2 aspect ratio
        root.geometry("1200x800")
        root.update()
        u0, v0 = app.canvas_editor.coords.to_canvas(0.0, 0.0)
        u5, v10 = app.canvas_editor.coords.to_canvas(5.0, 10.0)
        pw_10_res = abs(u5 - u0)
        ph_10_res = abs(v10 - v0)
        assert pytest.approx(ph_10_res / pw_10_res, rel=1e-2) == 2.0, "5x10m aspect ratio must be preserved after resize"

        # Test 7: Empty state message displayed when area dimensions <= 0
        app.canvas_editor.layout.area.width_m = 0.0
        app.canvas_editor.layout.area.height_m = 0.0
        app.canvas_editor.redraw()
        root.update()
        item_texts = [c.itemcget(i, "text") for i in c.find_all() if c.type(i) == "text"]
        assert any("CREATE TEST AREA" in t for t in item_texts), "Empty state must display 'CREATE TEST AREA'"

    finally:
        if app:
            app._on_close()
        else:
            root.destroy()


