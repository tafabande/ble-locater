"""Indoor Positioning — Interactive 2D Experiment Environment Canvas.

Provides visual layout construction, grid snapping, coordinate rendering,
anchor and movable target placement, rotatable barrier obstacles,
and real-time Line-of-Sight (LOS) propagation raycast visualization.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple
import tkinter as tk

from collector.geometry import (
    PhysicalCoordinateSystem,
    euclidean_distance,
    get_oriented_box_corners,
    point_in_polygon,
    snap_to_grid,
)
from collector.environment import (
    AnchorNode,
    BarrierObject,
    EnvironmentLayout,
    TargetNode,
)


class CanvasEditor:
    """Controller for 2D laboratory test-area canvas rendering and interactive editing."""

    BARRIER_COLORS = {
        "Concrete wall": {"fill": "#3F3F46", "outline": "#71717A"},
        "Wall": {"fill": "#27272A", "outline": "#52525B"},
        "Door": {"fill": "#B45309", "outline": "#F59E0B"},
        "Human body": {"fill": "#52525B", "outline": "#A1A1AA"},
        "Cloth": {"fill": "#0F766E", "outline": "#2DD4BF"},
        "WiFi source": {"fill": "#3F3F46", "outline": "#A1A1AA"},
        "Bluetooth device": {"fill": "#27272A", "outline": "#71717A"},
        "Other": {"fill": "#18181B", "outline": "#3F3F46"},
    }

    ANCHOR_COLORS = {
        "ANCHOR_01": "#10B981",  # Node A (SW) - Emerald
        "ANCHOR_02": "#F59E0B",  # Node B (SE) - Amber
        "ANCHOR_03": "#F43F5E",  # Node C (NW) - Rose
        "ANCHOR_04": "#14B8A6",  # Node D (NE) - Teal
    }

    def __init__(
        self,
        parent_or_canvas: tk.Widget,
        layout: Optional[EnvironmentLayout] = None,
        on_selection_changed: Optional[Any] = None,
        on_layout_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        if isinstance(parent_or_canvas, tk.Canvas):
            self.canvas = parent_or_canvas
            self.canvas.config(bg="#09090B", highlightthickness=1, highlightbackground="#3F3F46")
        else:
            self.canvas = tk.Canvas(
                parent_or_canvas,
                bg="#09090B",
                highlightthickness=1,
                highlightbackground="#3F3F46",
                width=800,
                height=500,
            )
            self.canvas.pack(fill="both", expand=True)

        self.layout = layout or EnvironmentLayout()
        self.on_selection_changed = on_selection_changed
        self.on_layout_changed = on_layout_changed

        self.coords = PhysicalCoordinateSystem(
            width_m=self.layout.area.width_m,
            height_m=self.layout.area.height_m,
        )

        # Editor state
        self.current_tool: str = "select"  # "select", "add_node", "add_target", "add_barrier"
        self.snap_to_grid: bool = True
        self.show_paths: bool = True
        self.show_distances: bool = True
        self.show_los: bool = True
        self.is_locked: bool = False

        # Selection: tuple of (type, id) e.g. ("anchor", "ANCHOR_01"), ("target", "TARGET_01"), ("barrier", barrier_id)
        self.selected_item: Optional[Tuple[str, str]] = None

        # Drag tracking
        self.drag_start_canvas: Optional[Tuple[float, float]] = None
        self.drag_start_phys: Optional[Tuple[float, float]] = None

        self._bind_events()

    def render(self) -> None:
        """Alias for redraw()."""
        self.redraw()

    def set_tool_mode(self, tool: str) -> None:
        """Alias for set_tool()."""
        self.set_tool(tool)

    @property
    def tool_mode(self) -> str:
        return self.current_tool

    @tool_mode.setter
    def tool_mode(self, tool: str) -> None:
        self.set_tool(tool)

    @property
    def selected_object(self) -> Optional[Any]:
        if not self.selected_item:
            return None
        item_type, item_id = self.selected_item
        if item_type == "anchor":
            return self.layout.anchors.get(item_id)
        elif item_type == "target":
            return self.layout.target
        elif item_type == "barrier":
            return next((b for b in self.layout.barriers if b.id == item_id), None)
        return None

    def _bind_events(self) -> None:
        c = self.canvas
        c.bind("<Configure>", self._on_configure)
        c.bind("<Button-1>", self._on_mouse_down)
        c.bind("<B1-Motion>", self._on_mouse_drag)
        c.bind("<ButtonRelease-1>", self._on_mouse_up)

    def set_tool(self, tool: str) -> None:
        """Set active interaction mode."""
        self.current_tool = tool
        self.canvas.config(cursor="crosshair" if tool.startswith("add_") else "arrow")

    def set_locked(self, locked: bool) -> None:
        """Lock or unlock canvas geometry (e.g. during active recording)."""
        self.is_locked = locked
        if locked:
            self.set_tool("select")
        self.redraw()

    def set_layout(self, layout: EnvironmentLayout) -> None:
        """Replace active layout and update coordinates."""
        self.layout = layout
        self.coords.set_dimensions(layout.area.width_m, layout.area.height_m)
        self.selected_item = None
        self.redraw()
        if self.on_layout_changed:
            self.on_layout_changed()

    def _on_configure(self, event: tk.Event) -> None:
        self.coords.set_canvas_size(event.width, event.height)
        self.redraw()

    # =========================================================================
    # DRAWING ROUTINES
    # =========================================================================
    def redraw(self) -> None:
        """Complete redraw of the 2D experimental workspace."""
        c = self.canvas
        c.delete("all")

        # Synchronize coordinate engine with current physical dimensions
        self.coords.set_dimensions(self.layout.area.width_m, self.layout.area.height_m)

        # Empty state check
        if self.layout.area.width_m <= 0 or self.layout.area.height_m <= 0:
            self._draw_empty_state()
            self._draw_diagnostics()
            return

        # 1. Physical Grid & Boundary
        self._draw_grid()

        # 2. RF Propagation Paths (Target to Anchors)
        if self.show_paths:
            self._draw_propagation_paths()

        # 3. Environmental Barriers
        self._draw_barriers()

        # 4. 4 Anchors
        self._draw_anchors()

        # 5. Target Beacon Tag
        self._draw_target()

        # 6. Locked Watermark Overlay
        if self.is_locked:
            self._draw_locked_watermark()

        # 7. Live Diagnostic Overlay
        self._draw_diagnostics()

    def _draw_empty_state(self) -> None:
        """Render informative empty state when physical test area is not configured."""
        c = self.canvas
        w = max(400, self.canvas.winfo_width())
        h = max(300, self.canvas.winfo_height())
        cx = w / 2.0
        cy = h / 2.0

        # Card background
        card_w, card_h = 380, 200
        c.create_rectangle(
            cx - card_w / 2, cy - card_h / 2,
            cx + card_w / 2, cy + card_h / 2,
            fill="#0F172A", outline="#38BDF8", width=2, dash=(4, 4),
        )

        c.create_text(
            cx, cy - 55,
            text="CREATE TEST AREA",
            fill="#38BDF8", font=("Segoe UI", 13, "bold"),
        )
        c.create_text(
            cx, cy - 20,
            text="Enter physical dimensions in the left panel\nand click 'Apply Area Dimensions'.",
            fill="#F8FAFC", font=("Segoe UI", 10), justify="center",
        )
        c.create_text(
            cx, cy + 30,
            text="Canonical Example:\n5.0m × 5.0m  (Grid 1.0m)",
            fill="#94A3B8", font=("Segoe UI", 9, "bold"), justify="center",
        )
        c.create_text(
            cx, cy + 70,
            text="Quick Presets: 3×3m · 5×5m · 5×10m · 10×10m",
            fill="#0EA5E9", font=("Segoe UI", 8),
        )

    def _draw_diagnostics(self) -> None:
        """Render live diagnostic bar showing canvas size, mapping, and scale."""
        c = self.canvas
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        mapped = "YES" if self.canvas.winfo_ismapped() else "NO"
        scale_val = self.coords.scale
        w_m = self.layout.area.width_m
        h_m = self.layout.area.height_m

        diag_text = (
            f"Canvas: {c_w}×{c_h} px  |  Scale: {scale_val:.1f} px/m  |  "
            f"Mapped: {mapped}  |  Aspect: {w_m:.1f}m × {h_m:.1f}m"
        )
        # Draw small status pill at bottom right
        c.create_rectangle(
            c_w - 380, c_h - 24, c_w - 8, c_h - 6,
            fill="#0A1628", outline="#1E3A5F", width=1,
        )
        c.create_text(
            c_w - 194, c_h - 15,
            text=diag_text,
            fill="#64748B", font=("Segoe UI", 7, "bold"),
        )

    def _draw_grid(self) -> None:
        c = self.canvas
        area = self.layout.area
        w_m = area.width_m
        h_m = area.height_m
        spacing = area.grid_spacing_m

        # Top Canvas Header Banner
        header_text = f"📡 EXPERIMENTAL 2D ENVIRONMENT CANVAS  |  Area: {w_m:.1f}m × {h_m:.1f}m  |  Grid: {spacing:.1f}m"
        c.create_rectangle(14, 8, 440, 30, fill="#0F1D36", outline="#0284C7", width=1)
        c.create_text(227, 19, text=header_text, fill="#38BDF8", font=("Segoe UI", 8, "bold"))

        # Outer boundary corners in canvas pixels
        u0, v0 = self.coords.to_canvas(0.0, 0.0)
        u1, v1 = self.coords.to_canvas(w_m, h_m)

        # Draw physical boundary fill & prominent border
        c.create_rectangle(u0, v1, u1, v0, fill="#0A1628", outline="#38BDF8", width=2)

        # Internal grid lines
        x_steps = int(math.floor(w_m / spacing))
        for i in range(1, x_steps + 1):
            gx = i * spacing
            if gx < w_m:
                gu0, gv0 = self.coords.to_canvas(gx, 0.0)
                gu1, gv1 = self.coords.to_canvas(gx, h_m)
                c.create_line(gu0, gv0, gu1, gv1, fill="#1E3A5F", dash=(2, 2))

        y_steps = int(math.floor(h_m / spacing))
        for j in range(1, y_steps + 1):
            gy = j * spacing
            if gy < h_m:
                gu0, gv0 = self.coords.to_canvas(0.0, gy)
                gu1, gv1 = self.coords.to_canvas(w_m, gy)
                c.create_line(gu0, gv0, gu1, gv1, fill="#1E3A5F", dash=(2, 2))

        # Axis tick marks and distance labels along bottom (X) and left (Y)
        for i in range(0, x_steps + 1):
            gx = round(i * spacing, 2)
            if gx <= w_m:
                gu, gv = self.coords.to_canvas(gx, 0.0)
                c.create_line(gu, gv, gu, gv + 5, fill="#38BDF8", width=1)
                c.create_text(gu, gv + 15, text=f"{gx:.1f}m", fill="#94A3B8", font=("Segoe UI", 8))

        for j in range(0, y_steps + 1):
            gy = round(j * spacing, 2)
            if gy <= h_m:
                gu, gv = self.coords.to_canvas(0.0, gy)
                c.create_line(gu - 5, gv, gu, gv, fill="#38BDF8", width=1)
                c.create_text(gu - 20, gv, text=f"{gy:.1f}m", fill="#94A3B8", font=("Segoe UI", 8))

        # Origin marker at (0.0, 0.0)
        c.create_oval(u0 - 4, v0 - 4, u0 + 4, v0 + 4, fill="#38BDF8", outline="#FFFFFF", width=1)
        c.create_text(u0 - 18, v0 + 16, text="(0,0) Origin", fill="#38BDF8", font=("Segoe UI", 8, "bold"))

    def _draw_propagation_paths(self) -> None:
        """Render Line-of-Sight and Non-Line-of-Sight rays from target to all anchors."""
        target = self.layout.target
        if not target:
            return

        c = self.canvas
        tu, tv = self.coords.to_canvas(target.x_m, target.y_m)
        los_status = self.layout.get_anchor_los_status()
        distances = self.layout.get_anchor_distances()

        for anc_id, anc in self.layout.anchors.items():
            if not anc.is_placed:
                continue

            au, av = self.coords.to_canvas(anc.x_m, anc.y_m)
            is_los, obstacle_name = los_status.get(anc_id, (True, None))

            line_color = "#10B981" if is_los else "#EF4444"
            dash_pattern = () if is_los else (5, 4)

            # Draw ray
            c.create_line(au, av, tu, tv, fill=line_color, width=2, dash=dash_pattern)

            # Draw mid-ray distance badge
            if self.show_distances or self.show_los:
                mid_u = (au + tu) / 2.0
                mid_v = (av + tv) / 2.0
                dist_val = distances.get(anc_id, 0.0)
                if self.show_distances and self.show_los:
                    tag_text = f"{dist_val:.2f}m LOS" if is_los else f"{dist_val:.2f}m NLOS ({obstacle_name})"
                elif self.show_distances:
                    tag_text = f"{dist_val:.2f}m"
                else:
                    tag_text = "LOS" if is_los else f"NLOS ({obstacle_name})"

                c.create_rectangle(mid_u - 46, mid_v - 9, mid_u + 46, mid_v + 9, fill="#1E293B", outline=line_color)
                c.create_text(mid_u, mid_v, text=tag_text, fill="#FFFFFF", font=("Segoe UI", 7, "bold"))

    def _draw_barriers(self) -> None:
        c = self.canvas
        for barrier in self.layout.barriers:
            is_selected = (self.selected_item == ("barrier", barrier.id))
            col_spec = self.BARRIER_COLORS.get(barrier.barrier_type, self.BARRIER_COLORS["Other"])

            fill_col = col_spec["fill"]
            outline_col = "#F59E0B" if is_selected else col_spec["outline"]
            border_w = 3 if is_selected else 1

            if barrier.shape == "Circle":
                radius = max(0.1, barrier.width_m / 2.0)
                cu, cv = self.coords.to_canvas(barrier.x_m, barrier.y_m)
                r_px = radius * self.coords.scale
                c.create_oval(
                    cu - r_px, cv - r_px, cu + r_px, cv + r_px,
                    fill=fill_col, outline=outline_col, width=border_w,
                )
                c.create_text(cu, cv, text=barrier.name, fill="#FFFFFF", font=("Segoe UI", 8, "bold"))
            else:
                # Oriented Rectangle / Line
                corners = get_oriented_box_corners(
                    center=(barrier.x_m, barrier.y_m),
                    width=barrier.width_m,
                    depth=barrier.depth_m,
                    rotation_deg=barrier.rotation_deg,
                )
                poly_pts = []
                for pt in corners:
                    pu, pv = self.coords.to_canvas(pt[0], pt[1])
                    poly_pts.extend([pu, pv])

                c.create_polygon(poly_pts, fill=fill_col, outline=outline_col, width=border_w)

                # Center label
                cu, cv = self.coords.to_canvas(barrier.x_m, barrier.y_m)
                c.create_text(cu, cv, text=barrier.name, fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

            if is_selected:
                # Draw rotation handle indicator
                cu, cv = self.coords.to_canvas(barrier.x_m, barrier.y_m)
                c.create_oval(cu - 4, cv - 4, cu + 4, cv + 4, fill="#F59E0B", outline="#FFFFFF")

    def _draw_anchors(self) -> None:
        c = self.canvas
        for anc_id, anc in self.layout.anchors.items():
            if not anc.is_placed:
                continue

            is_selected = (self.selected_item == ("anchor", anc_id))
            u, v = self.coords.to_canvas(anc.x_m, anc.y_m)
            r = 13

            # Selection halo
            if is_selected:
                c.create_oval(u - r - 4, v - r - 4, u + r + 4, v + r + 4, outline="#F59E0B", width=2, dash=(3, 3))

            # Main badge
            node_color = self.ANCHOR_COLORS.get(anc_id, "#38BDF8")
            c.create_oval(u - r, v - r, u + r, v + r, fill="#0284C7", outline=node_color, width=2)

            # Node Letter (A, B, C, D)
            letter = anc.label.replace("Node ", "") if anc.label else anc_id[-1]
            c.create_text(u, v, text=letter, fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

            # Label tag with coordinates
            c.create_text(
                u, v - 20,
                text=f"{anc.label} ({anc.x_m:.2f}m, {anc.y_m:.2f}m)",
                fill="#E2E8F0", font=("Segoe UI", 8, "bold"),
            )

    def _draw_target(self) -> None:
        target = self.layout.target
        if not target:
            return

        c = self.canvas
        u, v = self.coords.to_canvas(target.x_m, target.y_m)
        r = 12
        is_selected = (self.selected_item == ("target", target.id))

        if is_selected:
            c.create_oval(u - r - 4, v - r - 4, u + r + 4, v + r + 4, outline="#F59E0B", width=2, dash=(3, 3))

        # Radial pulse rings
        c.create_oval(u - r - 2, v - r - 2, u + r + 2, v + r + 2, outline="#FB923C", width=1)
        # Beacon center
        c.create_oval(u - r, v - r, u + r, v + r, fill="#EA580C", outline="#FFEDD5", width=2)
        c.create_text(u, v, text="🎯", font=("Segoe UI", 9))

        # Coordinate pill below
        c.create_rectangle(u - 48, v + 16, u + 48, v + 32, fill="#1E293B", outline="#F97316")
        c.create_text(u, v + 24, text=f"({target.x_m:.2f}m, {target.y_m:.2f}m)", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))

    def _draw_locked_watermark(self) -> None:
        c = self.canvas
        w = self.canvas.winfo_width()
        c.create_rectangle(w - 260, 12, w - 16, 42, fill="#7F1D1D", outline="#EF4444", width=2)
        c.create_text(w - 138, 27, text="🔒 CONFIGURATION LOCKED", fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

    # =========================================================================
    # INTERACTIVE MOUSE HANDLING
    # =========================================================================
    def _on_mouse_down(self, event: tk.Event) -> None:
        if self.is_locked:
            return

        click_phys = self.coords.to_physical(event.x, event.y)
        if self.snap_to_grid:
            click_phys = snap_to_grid(click_phys[0], click_phys[1], self.layout.area.grid_spacing_m)

        # Tool dispatch
        if self.current_tool == "add_node":
            self._handle_add_node(click_phys)
            return
        elif self.current_tool == "add_target":
            self._handle_add_target(click_phys)
            return
        elif self.current_tool == "add_barrier":
            self._handle_add_barrier(click_phys)
            return

        # Default SELECT tool: Hit testing
        hit = self._hit_test(event.x, event.y)
        self.selected_item = hit
        self.drag_start_canvas = (event.x, event.y)

        if hit:
            item_type, item_id = hit
            if item_type == "target" and self.layout.target:
                self.drag_start_phys = (self.layout.target.x_m, self.layout.target.y_m)
            elif item_type == "anchor" and item_id in self.layout.anchors:
                anc = self.layout.anchors[item_id]
                self.drag_start_phys = (anc.x_m, anc.y_m)
            elif item_type == "barrier":
                bar = next((b for b in self.layout.barriers if b.id == item_id), None)
                if bar:
                    self.drag_start_phys = (bar.x_m, bar.y_m)

        self._notify_selection_changed()
        self.redraw()

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if self.is_locked or not self.selected_item or not self.drag_start_canvas or not self.drag_start_phys:
            return

        # Calculate physical delta
        curr_phys = self.coords.to_physical(event.x, event.y, clamp=False)
        start_phys = self.coords.to_physical(self.drag_start_canvas[0], self.drag_start_canvas[1], clamp=False)

        dx = curr_phys[0] - start_phys[0]
        dy = curr_phys[1] - start_phys[1]

        new_x = self.drag_start_phys[0] + dx
        new_y = self.drag_start_phys[1] + dy

        if self.snap_to_grid:
            new_x, new_y = snap_to_grid(new_x, new_y, self.layout.area.grid_spacing_m)

        # Clamp to area
        new_x = max(0.0, min(self.layout.area.width_m, new_x))
        new_y = max(0.0, min(self.layout.area.height_m, new_y))

        item_type, item_id = self.selected_item
        if item_type == "target" and self.layout.target:
            self.layout.target.x_m = round(new_x, 3)
            self.layout.target.y_m = round(new_y, 3)
        elif item_type == "anchor" and item_id in self.layout.anchors:
            anc = self.layout.anchors[item_id]
            anc.x_m = round(new_x, 3)
            anc.y_m = round(new_y, 3)
        elif item_type == "barrier":
            bar = next((b for b in self.layout.barriers if b.id == item_id), None)
            if bar:
                bar.x_m = round(new_x, 3)
                bar.y_m = round(new_y, 3)

        self.redraw()
        if self.on_layout_changed:
            self.on_layout_changed()
        self._notify_selection_changed()

    def _on_mouse_up(self, event: tk.Event) -> None:
        self.drag_start_canvas = None
        self.drag_start_phys = None

    def _hit_test(self, u_px: float, v_px: float) -> Optional[Tuple[str, str]]:
        """Determine which object (if any) was clicked on the canvas."""
        # 1. Target test
        if self.layout.target:
            tu, tv = self.coords.to_canvas(self.layout.target.x_m, self.layout.target.y_m)
            if math.hypot(u_px - tu, v_px - tv) <= 18:
                return ("target", self.layout.target.id)

        # 2. Anchors test
        for anc_id, anc in self.layout.anchors.items():
            if anc.is_placed:
                au, av = self.coords.to_canvas(anc.x_m, anc.y_m)
                if math.hypot(u_px - au, v_px - av) <= 18:
                    return ("anchor", anc_id)

        # 3. Barriers test
        click_phys = self.coords.to_physical(u_px, v_px, clamp=False)
        for barrier in reversed(self.layout.barriers):
            if barrier.shape == "Circle":
                if euclidean_distance(click_phys, (barrier.x_m, barrier.y_m)) <= (barrier.width_m / 2.0):
                    return ("barrier", barrier.id)
            else:
                corners = get_oriented_box_corners(
                    center=(barrier.x_m, barrier.y_m),
                    width=barrier.width_m,
                    depth=barrier.depth_m,
                    rotation_deg=barrier.rotation_deg,
                )
                if point_in_polygon(click_phys, corners):
                    return ("barrier", barrier.id)

        return None

    def _handle_add_node(self, pos: Tuple[float, float]) -> None:
        """Place next available or selected anchor."""
        unplaced = [aid for aid, a in self.layout.anchors.items() if not a.is_placed]
        target_aid = unplaced[0] if unplaced else "ANCHOR_01"

        anc = self.layout.anchors[target_aid]
        anc.x_m = pos[0]
        anc.y_m = pos[1]
        anc.is_placed = True

        self.selected_item = ("anchor", target_aid)
        self.set_tool("select")
        self.redraw()
        if self.on_layout_changed:
            self.on_layout_changed()
        self._notify_selection_changed()

    def _handle_add_target(self, pos: Tuple[float, float]) -> None:
        """Move or create target tag."""
        if not self.layout.target:
            self.layout.target = TargetNode(x_m=pos[0], y_m=pos[1])
        else:
            self.layout.target.x_m = pos[0]
            self.layout.target.y_m = pos[1]

        self.selected_item = ("target", self.layout.target.id)
        self.set_tool("select")
        self.redraw()
        if self.on_layout_changed:
            self.on_layout_changed()
        self._notify_selection_changed()

    def _handle_add_barrier(self, pos: Tuple[float, float]) -> None:
        """Create new barrier obstacle at clicked coordinate."""
        new_barrier = BarrierObject(
            name=f"Wall {len(self.layout.barriers) + 1}",
            barrier_type="Concrete wall",
            shape="Rectangle",
            x_m=pos[0],
            y_m=pos[1],
            width_m=2.0,
            depth_m=0.25,
            rotation_deg=0.0,
        )
        self.layout.barriers.append(new_barrier)
        self.selected_item = ("barrier", new_barrier.id)
        self.set_tool("select")
        self.redraw()
        if self.on_layout_changed:
            self.on_layout_changed()
        self._notify_selection_changed()

    def delete_selected(self) -> None:
        """Delete currently selected barrier or unplace anchor."""
        if self.is_locked or not self.selected_item:
            return

        item_type, item_id = self.selected_item
        if item_type == "barrier":
            self.layout.barriers = [b for b in self.layout.barriers if b.id != item_id]
            self.selected_item = None
            self.redraw()
            if self.on_layout_changed:
                self.on_layout_changed()
            self._notify_selection_changed()
        elif item_type == "anchor" and item_id in self.layout.anchors:
            self.layout.anchors[item_id].is_placed = False
            self.selected_item = None
            self.redraw()
            if self.on_layout_changed:
                self.on_layout_changed()
            self._notify_selection_changed()

    def _notify_selection_changed(self) -> None:
        if not self.on_selection_changed:
            return

        obj = self.selected_object
        try:
            self.on_selection_changed(obj)
        except TypeError:
            item_type = self.selected_item[0] if self.selected_item else None
            self.on_selection_changed(item_type, obj)
