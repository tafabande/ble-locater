import os
import sys
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.app import predict_distance_for_anchor, state, DEFAULT_ANCHORS_CONFIG, perform_localization
from localization.trilateration import TrilaterationEngine

print("--- TESTING DISTANCE PREDICTION & TRILATERATION ---")

# Test RSSI values corresponding to distances ~1m, 2m, 3m
rssis_anchor1 = [-78, -77, -79, -78] # ~1m
rssis_anchor2 = [-85, -84, -86, -85] # ~2.5m
rssis_anchor3 = [-92, -91, -93, -92] # ~4m

t_now = 1000000
times = [t_now - 300, t_now - 200, t_now - 100, t_now]

d1 = predict_distance_for_anchor("ANCHOR_01", rssis_anchor1, times)
d2 = predict_distance_for_anchor("ANCHOR_02", rssis_anchor2, times)
d3 = predict_distance_for_anchor("ANCHOR_03", rssis_anchor3, times)

print(f"Predicted d1 (ANCHOR_01): {d1} m")
print(f"Predicted d2 (ANCHOR_02): {d2} m")
print(f"Predicted d3 (ANCHOR_03): {d3} m")

test_dists = {"ANCHOR_01": d1, "ANCHOR_02": d2, "ANCHOR_03": d3}
engine = TrilaterationEngine(DEFAULT_ANCHORS_CONFIG)
pos, uncertainty, gdop = engine.estimate_position(test_dists)

print(f"Trilateration Estimate Position: ({pos[0]:.2f}, {pos[1]:.2f})")
