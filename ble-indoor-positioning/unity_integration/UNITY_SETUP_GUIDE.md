# Unity 3D Integration Guide — BLE Indoor Positioning

This guide will walk you through setting up a simple Unity 3D scene that listens to the live positioning telemetry from your Python backend and visualises the BLE tag's movement in real-time.

## Prerequisites
1. Unity Hub and a recent version of the Unity Editor installed (e.g., Unity 2021, 2022, or 2023).
2. The Python Control Center running with the **Backend Server** started.

## Step 1: Create a New Unity Project
1. Open **Unity Hub**.
2. Click **New project**.
3. Select the **3D Core** template.
4. Name your project (e.g., `BLE-Indoor-Positioning-Vis`) and click **Create project**.

## Step 2: Set Up the Scene
Once the Unity Editor opens, we'll create the objects to represent our environment and the moving tag.

1. **Create the Floor:**
   - In the **Hierarchy** window, right-click and choose **3D Object > Plane**.
   - Select the Plane, go to the **Inspector**, and set its Position to `(0, 0, 0)`.
   - Scale it up slightly if needed (e.g., `Scale X: 2, Z: 2`).

2. **Create the BLE Tag:**
   - Right-click in the **Hierarchy** and choose **3D Object > Sphere**.
   - Rename it to `BLE_Tag`.
   - Set its Position to `(0, 0.5, 0)` so it sits on top of the floor.
   - Optional: Give it a bright red material so it's easy to see.

3. **Adjust the Camera:**
   - Select the **Main Camera**.
   - Move it to get a top-down bird's-eye view. Try Position: `(2.5, 8, -2)` and Rotation: `(60, 0, 0)`.

## Step 3: Add the Tracking Script
1. In the **Project** window at the bottom, right-click the `Assets` folder and choose **Create > C# Script**.
2. Name the script exactly `TagVisualizer`.
3. Double-click the script to open it in your code editor (Visual Studio/Rider).
4. **Copy the contents of `TagVisualizer.cs`** (found in this folder) and replace everything in the newly created script. Save the file.
5. Go back to Unity. Wait a second for it to compile the script.
6. Click and drag the `TagVisualizer` script from the Project window onto the `BLE_Tag` object in the Hierarchy.

## Step 4: Run the Visualisation
1. Open the Python Control Center (`control.py`) on your machine.
2. Click **Start Backend**.
3. Click **Start Simulation** (or start the physical collector) so that data is being generated.
4. Go back to Unity and press the **Play** button at the top of the editor.

**Result:** You should see the sphere smoothly moving across the plane in real-time, matching the exact coordinates calculated by the Python machine learning and trilateration algorithms!

## Troubleshooting
- **Nothing moves:** Ensure your Python backend is running on `127.0.0.1:8000`. You can check the Unity Console window (Ctrl+Shift+C) for any connection error logs.
- **The sphere flies off-screen:** The scale might be too large. Select `BLE_Tag`, look at the Tag Visualizer script in the Inspector, and reduce the `Scale Factor`.
