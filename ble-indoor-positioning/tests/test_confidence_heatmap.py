import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from localization.trilateration import TrilaterationEngine

def test_confidence_heatmap_generation():
    anchors_config = {
        "ANCHOR_01": (0.0, 0.0),
        "ANCHOR_02": (10.0, 0.0),
        "ANCHOR_03": (5.0, 10.0)
    }
    engine = TrilaterationEngine(anchors_config)

    heatmap = engine.compute_gdop_grid(bounds_x=(0.0, 10.0), bounds_y=(0.0, 10.0), step=1.0)
    
    assert "x" in heatmap
    assert "y" in heatmap
    assert "confidence" in heatmap
    assert "gdop" in heatmap

    # Grid dimensions should match x and y steps (11x11 points for 0..10 step 1)
    assert len(heatmap["x"]) == 11
    assert len(heatmap["y"]) == 11
    assert len(heatmap["confidence"]) == 11
    assert len(heatmap["confidence"][0]) == 11

    # Center of triangle (5.0, 3.33) should have high confidence (> 70%)
    center_y_idx = 3 # y=3.0
    center_x_idx = 5 # x=5.0
    center_conf = heatmap["confidence"][center_y_idx][center_x_idx]
    assert center_conf > 50.0
