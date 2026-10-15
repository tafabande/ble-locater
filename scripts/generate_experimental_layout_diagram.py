"""Generate high-resolution (300 DPI PNG + vector SVG) academic testbed layout diagram
for Chapter 3 of the BLE Indoor Positioning dissertation.
"""
import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_layout_diagram():
    out_dir_reports = r"c:\Users\DEV\Desktop\Dissertation\ble-indoor-positioning\reports"
    out_dir_artifacts = r"C:\Users\DEV\.gemini\antigravity-ide\brain\0720a890-3203-4c2a-aac8-dac060c0d70a"
    os.makedirs(out_dir_reports, exist_ok=True)
    os.makedirs(out_dir_artifacts, exist_ok=True)

    fig = plt.figure(figsize=(12, 12), dpi=300)
    ax = fig.add_subplot(111)

    # Set boundaries with padding
    ax.set_xlim(-0.8, 6.2)
    ax.set_ylim(-0.8, 6.2)
    ax.set_aspect("equal")

    # Grid and styling
    ax.set_facecolor("#F8FAFC")
    fig.patch.set_facecolor("#FFFFFF")

    # Draw room boundary
    room_rect = patches.Rectangle((0, 0), 5, 5, linewidth=2.5, edgecolor="#0F172A", facecolor="#FFFFFF", zorder=1)
    ax.add_patch(room_rect)

    # Fine grid lines
    for x in np.arange(0, 5.1, 0.5):
        lw = 1.0 if (x % 1.0 == 0) else 0.4
        c = "#CBD5E1" if (x % 1.0 == 0) else "#E2E8F0"
        ax.plot([x, x], [0, 5], color=c, lw=lw, zorder=2)
    for y in np.arange(0, 5.1, 0.5):
        lw = 1.0 if (y % 1.0 == 0) else 0.4
        c = "#CBD5E1" if (y % 1.0 == 0) else "#E2E8F0"
        ax.plot([0, 5], [y, y], color=c, lw=lw, zorder=2)

    # Concentric distance circles from Anchor A (0,0) as subtle visual guides
    for r in [1, 2, 3, 4, 5]:
        theta = np.linspace(0, np.pi/2, 100)
        ax.plot(r * np.cos(theta), r * np.sin(theta), color="#93C5FD", linestyle=":", lw=0.9, alpha=0.7, zorder=2)

    # 4 Anchors
    anchors = [
        {"id": "ANCHOR_01 (Node A)", "pos": (0.0, 0.0), "mac": "C8:2E:18:26:39:A0", "loc": "SW (0.0, 0.0)", "align": (-0.15, -0.25), "ha": "right"},
        {"id": "ANCHOR_02 (Node B)", "pos": (5.0, 0.0), "mac": "D0:EF:76:58:F6:FC", "loc": "SE (5.0, 0.0)", "align": (0.15, -0.25), "ha": "left"},
        {"id": "ANCHOR_03 (Node C)", "pos": (0.0, 5.0), "mac": "D4:8A:FC:CE:E0:44", "loc": "NW (0.0, 5.0)", "align": (-0.15, 0.25), "ha": "right"},
        {"id": "ANCHOR_04 (Node D)", "pos": (5.0, 5.0), "mac": "78:1C:3C:E5:B3:F4", "loc": "NE (5.0, 5.0)", "align": (0.15, 0.25), "ha": "left"},
    ]

    for a in anchors:
        x, y = a["pos"]
        # Anchor marker
        ax.scatter(x, y, s=280, color="#2563EB", edgecolors="#0F172A", linewidth=2.0, zorder=6, marker="s")
        ax.scatter(x, y, s=80, color="#FFFFFF", zorder=7, marker="s")
        # Text callout
        tx, ty = x + a["align"][0], y + a["align"][1]
        ax.annotate(
            f"{a['id']}\n{a['mac']}\nHeight: 0.96m (5V/2A)",
            xy=(x, y), xytext=(tx, ty),
            fontsize=8.5, fontweight="bold", color="#0F172A", ha=a["ha"],
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#EFF6FF", edgecolor="#2563EB", lw=1.2),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="#2563EB", lw=1.2),
            zorder=8
        )

    # 9 Test Coordinates
    test_points = [
        {"pos": (1.0, 1.0), "sess": 1, "win": 101, "desc": "SW Interior Corner", "ha": "left", "va": "bottom", "off": (0.12, 0.12)},
        {"pos": (2.0, 3.0), "sess": 1, "win": 45, "desc": "Interior Transition", "ha": "right", "va": "bottom", "off": (-0.12, 0.12)},
        {"pos": (2.5, 2.5), "sess": 22, "win": 1259, "desc": "Geometric Center\n(Benchmark / Jitter)", "ha": "center", "va": "top", "off": (0.0, -0.18)},
        {"pos": (2.5, 5.0), "sess": 1, "win": 87, "desc": "Mid-North Edge", "ha": "center", "va": "bottom", "off": (0.0, 0.15)},
        {"pos": (3.0, 2.0), "sess": 2, "win": 126, "desc": "SE Transition", "ha": "left", "va": "top", "off": (0.12, -0.12)},
        {"pos": (4.0, 1.0), "sess": 2, "win": 90, "desc": "Near Node B", "ha": "left", "va": "bottom", "off": (0.12, 0.12)},
        {"pos": (4.0, 3.0), "sess": 2, "win": 116, "desc": "East Corridor", "ha": "left", "va": "center", "off": (0.15, 0.0)},
        {"pos": (5.0, 2.5), "sess": 1, "win": 95, "desc": "Mid-East Edge", "ha": "left", "va": "center", "off": (0.15, 0.0)},
        {"pos": (5.0, 5.0), "sess": 1, "win": 42, "desc": "NE Corner Point", "ha": "right", "va": "top", "off": (-0.15, -0.15)},
    ]

    for tp in test_points:
        x, y = tp["pos"]
        is_center = (x == 2.5 and y == 2.5)
        m_size = 240 if is_center else 120
        m_color = "#DC2626" if is_center else "#059669"
        edge_c = "#7F1D1D" if is_center else "#064E3B"

        ax.scatter(x, y, s=m_size, color=m_color, edgecolors=edge_c, linewidth=1.5, zorder=5, marker="o")
        if is_center:
            # Concentric ring for center
            ax.scatter(x, y, s=450, facecolors="none", edgecolors="#DC2626", linewidth=1.8, linestyle="--", zorder=4)

        ox, oy = tp["off"]
        label_text = f"({x:.1f}, {y:.1f})m\n{tp['win']} win ({tp['sess']} sess)"
        if is_center:
            label_text = f"CENTER ({x:.1f}, {y:.1f})m\n1,259 win (22 sess)\nPrimary Benchmark"

        bbox_bg = "#FEF2F2" if is_center else "#ECFDF5"
        bbox_edge = "#DC2626" if is_center else "#059669"
        text_c = "#991B1B" if is_center else "#065F46"

        ax.text(
            x + ox, y + oy, label_text,
            fontsize=7.5, fontweight="bold", color=text_c, ha=tp["ha"], va=tp["va"],
            bbox=dict(boxstyle="round,pad=0.25", facecolor=bbox_bg, edgecolor=bbox_edge, lw=0.9),
            zorder=8
        )

    # Axis Labels & Title
    ax.set_xlabel("X Coordinate (Meters) → East", fontsize=11, fontweight="bold", labelpad=8, color="#0F172A")
    ax.set_ylabel("Y Coordinate (Meters) → North", fontsize=11, fontweight="bold", labelpad=8, color="#0F172A")
    ax.set_xticks(np.arange(0, 5.1, 1.0))
    ax.set_yticks(np.arange(0, 5.1, 1.0))
    ax.tick_params(axis="both", which="major", labelsize=9.5)

    # Title & Legend Box
    title_text = "Physical Experimental Testbed & Surveyed Coordinate Grid"
    subtitle_text = "5.0m × 5.0m Test Area • 4 ESP32-WROOM-32 Anchors (H = 0.96m) • 9 Surveyed Test Points (1,961 Windows)"
    plt.title(f"{title_text}\n{subtitle_text}", fontsize=12, fontweight="bold", pad=15, color="#0F172A")

    # Legend
    legend_elements = [
        patches.Patch(facecolor="#2563EB", edgecolor="#0F172A", label="ESP32 Anchor Node (Height = 0.96m)"),
        patches.Patch(facecolor="#DC2626", edgecolor="#7F1D1D", label="Geometric Center Testbed (22 Sessions, 1,259 Windows)"),
        patches.Patch(facecolor="#059669", edgecolor="#064E3B", label="Perimeter / Transition Survey Points (11 Sessions, 702 Windows)"),
        patches.Rectangle((0, 0), 1, 1, fill=False, edgecolor="#0F172A", linewidth=2.0, label="Room Perimeter (5.0m × 5.0m Boundary)"),
    ]
    ax.legend(handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=8.5, frameon=True)

    plt.tight_layout()

    # Save to reports
    svg_report = os.path.join(out_dir_reports, "experimental_layout_grid.svg")
    png_report = os.path.join(out_dir_reports, "experimental_layout_grid.png")
    plt.savefig(svg_report, format="svg", bbox_inches="tight")
    plt.savefig(png_report, format="png", dpi=300, bbox_inches="tight")
    plt.close()

    # Copy to artifacts brain directory
    svg_art = os.path.join(out_dir_artifacts, "experimental_layout_grid.svg")
    png_art = os.path.join(out_dir_artifacts, "experimental_layout_grid.png")
    shutil.copy2(svg_report, svg_art)
    shutil.copy2(png_report, png_art)
    print(f"Successfully generated:\n- {png_report}\n- {svg_report}\n- {png_art}\n- {svg_art}")

if __name__ == "__main__":
    generate_layout_diagram()
