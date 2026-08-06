import os
import sys
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.app import OnlineDistanceLearner

def test_online_learning_persistence(tmp_path):
    calib_file = str(tmp_path / "test_calibrations.json")

    # 1. Instantiate learner with custom calib path
    learner = OnlineDistanceLearner()
    learner.calib_filepath = calib_file
    
    # 2. Learn samples for ANCHOR_01 and ANCHOR_02
    learner.learn_sample("ANCHOR_01", rssi=-70, true_dist=3.0, raw_pred_dist=2.5)
    learner.learn_sample("ANCHOR_02", rssi=-65, true_dist=1.5, raw_pred_dist=1.8)
    
    # 3. Explicit save to disk
    learner.save()
    assert os.path.exists(calib_file)

    # 4. Verify JSON content structure
    with open(calib_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["version"] == 1
    assert "ANCHOR_01" in data["anchors"]
    assert "ANCHOR_02" in data["anchors"]
    assert data["anchors"]["ANCHOR_01"]["samples"] >= 1
    assert data["total_samples"] >= 2

    # 5. Instantiate a NEW learner and verify it loads saved calibrations
    new_learner = OnlineDistanceLearner()
    new_learner.calib_filepath = calib_file
    new_learner.load()

    assert new_learner.anchor_samples["ANCHOR_01"] == learner.anchor_samples["ANCHOR_01"]
    assert abs(new_learner.anchor_eta["ANCHOR_01"] - learner.anchor_eta["ANCHOR_01"]) < 1e-4
    assert abs(new_learner.anchor_bias["ANCHOR_01"] - learner.anchor_bias["ANCHOR_01"]) < 1e-4
    assert new_learner.samples_learned_count == learner.samples_learned_count
