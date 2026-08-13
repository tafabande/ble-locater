import os
import sys
import json
import pytest
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from learning.stage_runtime_learner import StageRuntimeLearner

def test_stage_runtime_learner(tmp_path):
    json_path = str(tmp_path / 'test_pipeline_runtimes.json')
    learner = StageRuntimeLearner(filepath=json_path)
    assert learner.data['total_runs'] == 0
    durations_run1 = {'Feature Engineering': 10.0, 'Regression Tournament': 30.0, 'Classification Tournament': 20.0}
    learner.record_run(durations_run1)
    assert os.path.exists(json_path)
    assert learner.data['total_runs'] == 1
    assert abs(learner.data['stage_runtimes']['Feature Engineering'] - 8.6) < 0.2
    durations_run2 = {'Feature Engineering': 12.0, 'Regression Tournament': 25.0, 'Classification Tournament': 18.0}
    learner.record_run(durations_run2)
    assert learner.data['total_runs'] == 2
    eta_start = learner.compute_historical_eta(current_percent=10.0, elapsed_sec=5.0)
    assert eta_start > 0.0
    eta_near_end = learner.compute_historical_eta(current_percent=90.0, elapsed_sec=45.0)
    assert eta_near_end < eta_start
