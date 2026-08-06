"""
BLE Indoor Positioning — Live Visualization & Control Dashboard
================================================================
A premium, modern Streamlit UI displaying real-time tracking coordinates,
smoothed Kalman trajectories, distance prediction charts, and system diagnostic telemetry.
Now updated with crash-proof request timeouts and resilient chart handling.
"""

import os
import sys
import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Setup Page Configuration
st.set_page_config(
    page_title="BLE Indoor Positioning Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Sleek CSS Styles for Dark-themed Dashboard
st.markdown("""
<style>
    .reportview-container {
        background: #1e1e2e;
        color: #cdd6f4;
    }
    .main {
        background-color: #1e1e2e;
    }
    .metric-card {
        background-color: #313244;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #45475a;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-title {
        color: #a6adc8;
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .metric-val {
        color: #89b4fa;
        font-size: 28px;
        font-weight: bold;
    }
    .metric-sub {
        color: #a6e3a1;
        font-size: 12px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
#  SIDEBAR CONTROL PANEL
# ──────────────────────────────────────────────────────────────────────

st.sidebar.markdown("<h2 style='color:#89b4fa;'>⚡ System Control Panel</h2>", unsafe_allow_html=True)
st.sidebar.write("Configure physical anchor positions and system parameters.")

# Server Configuration
backend_url = st.sidebar.text_input("FastAPI Backend URL:", value="http://localhost:8000")

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Anchor Coordinates (meters)")

# Coordinates Inputs
a1_x = st.sidebar.number_input("Anchor 01 X:", value=0.0, step=0.5)
a1_y = st.sidebar.number_input("Anchor 01 Y:", value=0.0, step=0.5)

a2_x = st.sidebar.number_input("Anchor 02 X:", value=5.0, step=0.5)
a2_y = st.sidebar.number_input("Anchor 02 Y:", value=0.0, step=0.5)

a3_x = st.sidebar.number_input("Anchor 03 X:", value=2.5, step=0.5)
a3_y = st.sidebar.number_input("Anchor 03 Y:", value=4.33, step=0.5)

# Update Server Configuration Button
if st.sidebar.button("💾 Apply Coordinates"):
    try:
        r1 = requests.post(f"{backend_url}/api/config/anchors", json={"anchor_id": "ANCHOR_01", "x": a1_x, "y": a1_y}, timeout=3.0)
        r2 = requests.post(f"{backend_url}/api/config/anchors", json={"anchor_id": "ANCHOR_02", "x": a2_x, "y": a2_y}, timeout=3.0)
        r3 = requests.post(f"{backend_url}/api/config/anchors", json={"anchor_id": "ANCHOR_03", "x": a3_x, "y": a3_y}, timeout=3.0)
        if r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200:
            st.sidebar.success("✅ Anchor coordinates updated on server!")
        else:
            st.sidebar.error("❌ Failed to update anchor configurations.")
    except Exception as e:
        st.sidebar.error(f"Error connecting to backend: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color:#cba6f7;'>💡 Help & Guidance</h3>", unsafe_allow_html=True)
st.sidebar.write(
    "Coordinate estimation uses Weighted Least-Squares trilateration. "
    "Uncertainty (the glowing translucent circle on the plot) represents estimated standard error based on ML distance model residuals."
)


# ──────────────────────────────────────────────────────────────────────
#  MAIN DASHBOARD GRID
# ──────────────────────────────────────────────────────────────────────

# Header Title
st.markdown("<h1 style='color:#89b4fa;'>⚡ BLE Indoor Positioning Studio</h1>", unsafe_allow_html=True)
st.write("Real-time location coordinate estimations smoothed with a 2D Constant Velocity Kalman Filter.")

# Fetch state from FastAPI backend
server_state = None
try:
    response = requests.get(f"{backend_url}/api/state", timeout=3.0)
    if response.status_code == 200:
        server_state = response.json()
    else:
        st.error(f"⚠️ Backend returned status code {response.status_code}.")
except Exception as e:
    st.info(f"💡 Waiting for connection to FastAPI backend server at {backend_url}. (Status: Offline)")


if server_state:
    position = server_state.get("position", {"x": 0.0, "y": 0.0, "uncertainty": 0.5, "gdop": 1.0})
    distances = server_state.get("distances", {})
    anchors = server_state.get("anchors", {})
    history = server_state.get("history", [])
    learning = server_state.get("learning", {})
    alerts = server_state.get("alerts", [])
    latest_alert = server_state.get("latest_alert", None)

    # Sidebar: Persistent Learning Telemetry
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h3 style='color:#a6e3a1;'>🧠 Online Learning Calibration</h3>", unsafe_allow_html=True)
    st.sidebar.write(f"**Total Samples Persisted:** `{learning.get('samples_learned', 0)}`")
    st.sidebar.write(f"**Avg Path Loss ($\eta$):** `{learning.get('average_learned_pathloss', 2.7):.2f}`")
    st.sidebar.write(f"**Live MAE Error:** `{learning.get('live_mae_error', 0.0):.3f} m`")

    # Banner / Toast for Latest Geofence Alert
    if latest_alert:
        sev = latest_alert.get("severity", "LOW")
        msg = latest_alert.get("message", "")
        if sev == "HIGH":
            st.error(f"🚨 **HIGH SEVERITY ALERT ({latest_alert.get('time')})**: {msg}")
        elif sev == "WARNING":
            st.warning(f"⚠️ **WARNING ({latest_alert.get('time')})**: {msg}")

    # Row 1: Real-time Metric Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>📍 Estimated Position (X, Y)</div>"
            f"<div class='metric-val'>({position.get('x', 0.0):.2f}, {position.get('y', 0.0):.2f}) m</div>"
            f"<div class='metric-sub'>Room: {position.get('room', 'Unknown')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    with m_col2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>🎯 Position Uncertainty (Error Radius)</div>"
            f"<div class='metric-val'>± {position.get('uncertainty', 0.0):.2f} m</div>"
            f"<div class='metric-sub'>Target MAE: 0.35m</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    with m_col3:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>🌐 Active Anchor Nodes</div>"
            f"<div class='metric-val'>{len(distances)} / {len(anchors)}</div>"
            f"<div class='metric-sub'>Online Calibrator ACTIVE</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    with m_col4:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>📉 Dilution of Precision (GDOP)</div>"
            f"<div class='metric-val'>{position.get('gdop', 0.0):.2f}</div>"
            f"<div class='metric-sub'>Values < 3.0 are optimal</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # 4-Tab Modular Dashboard Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ 2D Floorplan", 
        "🧊 3D Building Spatial View", 
        "🚨 Geofence Alerts & Audit Trail", 
        "🧠 ML Online Learning"
    ])

    anchor_x = [coord[0] for coord in anchors.values() if isinstance(coord, (list, tuple)) and len(coord) >= 2]
    anchor_y = [coord[1] for coord in anchors.values() if isinstance(coord, (list, tuple)) and len(coord) >= 2]
    anchor_names = list(anchors.keys())
    max_x = max(anchor_x) if anchor_x else 10.0
    max_y = max(anchor_y) if anchor_y else 10.0

    pos_x = float(position.get("x", 0.0))
    pos_y = float(position.get("y", 0.0))

    # ── TAB 1: 2D FLOORPLAN MAP ──────────────────────────────────────
    with tab1:
        col_plot, col_info = st.columns([2.2, 1.2])

        with col_plot:
            show_heatmap = st.checkbox("🔥 Show Live Localization Confidence Heatmap", value=True)
            fig2d = go.Figure()

            # 0. Live Confidence Heatmap Layer
            if show_heatmap:
                try:
                    h_resp = requests.get(f"{backend_url}/api/confidence_heatmap?step=0.4", timeout=2.0)
                    if h_resp.status_code == 200:
                        h_data = h_resp.json()
                        hx = h_data.get("x", [])
                        hy = h_data.get("y", [])
                        hconf = h_data.get("confidence", [])

                        fig2d.add_trace(go.Heatmap(
                            z=hconf,
                            x=hx,
                            y=hy,
                            colorscale="RdYlGn",
                            zmin=0,
                            zmax=100,
                            opacity=0.45,
                            colorbar=dict(
                                title="Confidence %",
                                titlefont=dict(color="#cdd6f4"),
                                tickfont=dict(color="#cdd6f4"),
                                len=0.75
                            ),
                            hoverinfo="x+y+z",
                            name="Confidence Heatmap"
                        ))
                except Exception as e:
                    pass

            # 1. Plot anchors
            if anchor_x and anchor_y:
                fig2d.add_trace(go.Scatter(
                    x=anchor_x,
                    y=anchor_y,
                    mode="markers+text",
                    marker=dict(size=14, color="#f38ba8", symbol="triangle-up", line=dict(width=2, color="#1e1e2e")),
                    text=anchor_names,
                    textposition="top center",
                    name="Anchors",
                    hoverinfo="text"
                ))

            # 2. Draw trajectory history
            if history:
                hist_x = [h.get("x", 0.0) for h in history]
                hist_y = [h.get("y", 0.0) for h in history]
                fig2d.add_trace(go.Scatter(
                    x=hist_x,
                    y=hist_y,
                    mode="lines",
                    line=dict(color="#cba6f7", width=3, dash="dot"),
                    name="Kalman Trajectory"
                ))

            # 3. Draw current location estimate with Uncertainty Circle
            theta = np.linspace(0, 2*np.pi, 100)
            u_radius = max(0.2, float(position.get("uncertainty", 0.5)))
            circle_x = pos_x + u_radius * np.cos(theta)
            circle_y = pos_y + u_radius * np.sin(theta)

            fig2d.add_trace(go.Scatter(
                x=circle_x,
                y=circle_y,
                fill="toself",
                fillcolor="rgba(137, 180, 250, 0.2)",
                line=dict(color="rgba(137, 180, 250, 0.6)", width=1.5),
                name="Uncertainty Radius",
                hoverinfo="skip"
            ))

            fig2d.add_trace(go.Scatter(
                x=[pos_x],
                y=[pos_y],
                mode="markers",
                marker=dict(size=16, color="#89b4fa", symbol="circle", line=dict(width=2, color="#11111b")),
                name="Tag Position Estimate",
                hoverinfo="x+y"
            ))

            fig2d.update_layout(
                paper_bgcolor="#181825",
                plot_bgcolor="#181825",
                xaxis=dict(gridcolor="#313244", title="X Coordinate (meters)", range=[-1, max_x + 2]),
                yaxis=dict(gridcolor="#313244", title="Y Coordinate (meters)", range=[-1, max_y + 2]),
                height=520,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(font=dict(color="#cdd6f4"))
            )
            st.plotly_chart(fig2d, use_container_width=True)


        with col_info:
            st.subheader("📡 Live Distance Telemetry")
            records = []
            for anchor_name, coord in anchors.items():
                dist = distances.get(anchor_name, None)
                dist_str = f"{dist:.2f} m" if dist is not None else "OFFLINE"
                coord_str = f"({coord[0]:.1f}, {coord[1]:.1f})" if isinstance(coord, (list, tuple)) and len(coord) >= 2 else "(0.0, 0.0)"
                records.append({
                    "Anchor ID": anchor_name,
                    "Coordinates (X,Y)": coord_str,
                    "Distance": dist_str
                })
            df_dist = pd.DataFrame(records)
            st.table(df_dist)

    # ── TAB 2: 3D BUILDING SPATIAL VIEW ─────────────────────────────
    with tab2:
        st.subheader("🧊 3D Spatial Building Map")
        fig3d = go.Figure()

        # Anchors at ceiling height (Z=2.5m)
        anchor_z = [2.5] * len(anchor_x)
        fig3d.add_trace(go.Scatter3d(
            x=anchor_x,
            y=anchor_y,
            z=anchor_z,
            mode="markers+text",
            marker=dict(size=8, color="#f38ba8", symbol="diamond", line=dict(width=1, color="#ffffff")),
            text=anchor_names,
            name="Ceiling Anchors (Z=2.5m)"
        ))

        # Tag position at waist height (Z=0.8m)
        fig3d.add_trace(go.Scatter3d(
            x=[pos_x],
            y=[pos_y],
            z=[0.8],
            mode="markers",
            marker=dict(size=14, color="#89b4fa", symbol="circle"),
            name="Tag Estimate (Z=0.8m)"
        ))

        # Trajectory path in 3D
        if history:
            hx = [h.get("x", 0.0) for h in history]
            hy = [h.get("y", 0.0) for h in history]
            hz = [0.8] * len(hx)
            fig3d.add_trace(go.Scatter3d(
                x=hx,
                y=hy,
                z=hz,
                mode="lines",
                line=dict(color="#cba6f7", width=5),
                name="3D Kalman Path"
            ))

        # Floorplan Wireframe Boundary Lines (Z=0 floor, Z=3.0 ceiling)
        box_x = [0, 10, 10, 0, 0, 0, 10, 10, 0, 0, 10, 10, 10, 10, 0, 0]
        box_y = [0, 0, 10, 10, 0, 0, 0, 10, 10, 0, 0, 0, 10, 10, 10, 10]
        box_z = [0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 0, 3, 3, 0, 0, 3]
        fig3d.add_trace(go.Scatter3d(
            x=box_x,
            y=box_y,
            z=box_z,
            mode="lines",
            line=dict(color="#45475a", width=2, dash="dash"),
            name="Hospital Spatial Wireframe"
        ))

        fig3d.update_layout(
            paper_bgcolor="#181825",
            scene=dict(
                xaxis=dict(title="X (m)", backgroundcolor="#181825", gridcolor="#313244"),
                yaxis=dict(title="Y (m)", backgroundcolor="#181825", gridcolor="#313244"),
                zaxis=dict(title="Height Z (m)", backgroundcolor="#181825", gridcolor="#313244", range=[0, 3.5]),
            ),
            height=550,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(font=dict(color="#cdd6f4"))
        )
        st.plotly_chart(fig3d, use_container_width=True)

    # ── TAB 3: GEOFENCE ALERTS & AUDIT TRAIL ─────────────────────────
    with tab3:
        st.subheader("🚨 Geofence Room Boundary Alert Log")
        if st.button("🗑️ Clear Alert History"):
            try:
                requests.post(f"{backend_url}/api/alerts/clear", timeout=2.0)
                st.success("Alert history cleared.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to clear alerts: {e}")

        if alerts:
            for a in reversed(alerts[-10:]):
                sev = a.get("severity", "LOW")
                badge = "🔴 HIGH" if sev == "HIGH" else ("🟠 WARN" if sev == "WARNING" else "🔵 INFO")
                color = "#f38ba8" if sev == "HIGH" else ("#fab387" if sev == "WARNING" else "#89b4fa")
                st.markdown(
                    f"<div style='background-color:#313244; padding:12px; border-radius:8px; margin-bottom:10px; border-left: 5px solid {color};'>"
                    f"<b>{badge}</b> <span style='font-size:13px; color:#a6adc8;'>Timestamp: {a.get('time')} | Patient: {a.get('patient', 'TAG_01')}</span><br/>"
                    f"<span style='font-size:14px;'>{a.get('message')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No geofence room boundary violations recorded.")

    # ── TAB 4: ML ONLINE LEARNING DIAGNOSTICS ────────────────────────
    with tab4:
        st.subheader("🧠 Online Self-Learning Calibrator Metrics")
        st.write(
            "The `OnlineDistanceLearner` continuously fine-tunes anchor-specific path loss exponents ($\eta$) "
            "and additive distance bias corrections live during operation."
        )

        biases = learning.get("learned_biases", {})
        samples = learning.get("anchor_samples", {})
        if biases:
            df_learn = pd.DataFrame([
                {"Anchor ID": k, "Distance Bias Correction (m)": v, "Samples Learned": samples.get(k, 0)}
                for k, v in biases.items()
            ])
            st.dataframe(df_learn, use_container_width=True)

            fig_bias = go.Figure(go.Bar(
                x=list(biases.keys()),
                y=list(biases.values()),
                marker_color="#89b4fa"
            ))
            fig_bias.update_layout(
                title="Learned Distance Bias Correction per Anchor (meters)",
                paper_bgcolor="#181825",
                plot_bgcolor="#181825",
                xaxis=dict(gridcolor="#313244"),
                yaxis=dict(gridcolor="#313244", title="Bias Offset (m)")
            )
            st.plotly_chart(fig_bias, use_container_width=True)

    # Refresh loop
    time.sleep(1.0)
    st.rerun()
else:
    st.info("💡 Start your FastAPI real-time backend server (`python server/app.py`) to visualize live data.")


