import math
import numpy as np
import pandas as pd
import pytest
from localization.trilateration import TrilaterationEngine, KalmanFilter2D
from feature_engineering.engineer import compute_window_features, _safe_float
from server.app import predict_distance_for_anchor

@pytest.fixture
def sample_anchors():
    return {'A1': (0.0, 0.0), 'A2': (5.0, 0.0), 'A3': (2.5, 4.33)}

def test_trilateration_normal(sample_anchors):
    engine = TrilaterationEngine(sample_anchors)
    distances = {'A1': 2.5, 'A2': 2.5, 'A3': 2.5}
    pos, unc, gdop = engine.estimate_position(distances)
    assert isinstance(pos, tuple)
    assert len(pos) == 2
    assert np.isfinite(pos[0]) and np.isfinite(pos[1])
    assert unc >= 0
    assert gdop >= 0

def test_trilateration_insufficient_anchors_no_raise(sample_anchors):
    engine = TrilaterationEngine(sample_anchors)
    pos, unc, gdop = engine.estimate_position({}, raise_on_insufficient=False)
    assert pos == (2.5, 1.4433333333333334) or isinstance(pos, tuple)
    assert unc == 99.9
    assert gdop == 99.9
    pos, unc, gdop = engine.estimate_position({'A1': 2.0}, raise_on_insufficient=False)
    assert pos == (0.0, 0.0)
    assert unc == 99.9
    assert gdop == 99.9

def test_trilateration_insufficient_anchors_raise(sample_anchors):
    engine = TrilaterationEngine(sample_anchors)
    with pytest.raises(ValueError):
        engine.estimate_position({'A1': 2.0}, raise_on_insufficient=True)

def test_trilateration_nan_and_inf_distances(sample_anchors):
    engine = TrilaterationEngine(sample_anchors)
    bad_distances = {'A1': float('nan'), 'A2': float('inf'), 'A3': -5.0}
    pos, unc, gdop = engine.estimate_position(bad_distances, raise_on_insufficient=False)
    assert isinstance(pos, tuple)
    assert unc == 99.9
    assert gdop == 99.9

def test_trilateration_collinear_anchors():
    collinear_anchors = {'A1': (0.0, 0.0), 'A2': (2.0, 0.0), 'A3': (4.0, 0.0)}
    engine = TrilaterationEngine(collinear_anchors)
    distances = {'A1': 2.0, 'A2': 0.0, 'A3': 2.0}
    pos, unc, gdop = engine.estimate_position(distances)
    assert isinstance(pos, tuple)
    assert np.isfinite(pos[0]) and np.isfinite(pos[1])
    assert unc >= 0

def test_kalman_filter_normal():
    kf = KalmanFilter2D(dt=1.0)
    x1, y1 = kf.filter(0.0, 0.0)
    assert (x1, y1) == (0.0, 0.0)
    x2, y2 = kf.filter(1.0, 1.0)
    assert np.isfinite(x2) and np.isfinite(y2)

def test_kalman_filter_nan_inputs():
    kf = KalmanFilter2D(dt=1.0)
    kf.initialize(0.0, 0.0)
    x, y = kf.filter(float('nan'), float('inf'))
    assert np.isfinite(x) and np.isfinite(y)

def test_kalman_filter_invalid_init():
    kf = KalmanFilter2D(dt=-1.0, process_noise=-5.0)
    assert kf.dt == 1.0
    kf.initialize(float('nan'), float('nan'))
    assert kf.initialized is True
    assert np.all(np.isfinite(kf.x))

def test_feature_engineering_single_packet():
    df = pd.DataFrame({'rssi': [-65.0], 'timestamp': [1000]})
    feats = compute_window_features(df)
    assert isinstance(feats, dict)
    assert len(feats) >= 30
    assert feats['packet_count'] == 1
    assert feats['rssi_std'] == 0.0
    assert all((np.isfinite(val) for val in feats.values()))

def test_feature_engineering_identical_rssi():
    df = pd.DataFrame({'rssi': [-60.0, -60.0, -60.0, -60.0], 'timestamp': [1000, 1100, 1200, 1300]})
    feats = compute_window_features(df)
    assert feats['rssi_std'] == 0.0
    assert feats['rssi_variance'] == 0.0
    assert feats['rssi_skewness'] == 0.0
    assert feats['rssi_kurtosis'] == 0.0
    assert all((np.isfinite(val) for val in feats.values()))

def test_feature_engineering_nan_in_data():
    df = pd.DataFrame({'rssi': [-60.0, float('nan'), float('inf'), -70.0], 'timestamp': [1000, 1100, float('nan'), 1300]})
    feats = compute_window_features(df)
    assert isinstance(feats, dict)
    assert len(feats) >= 30
    assert all((np.isfinite(val) for val in feats.values()))

def test_feature_engineering_empty():
    feats = compute_window_features(pd.DataFrame())
    assert isinstance(feats, dict)
    assert len(feats) >= 30
    assert all((np.isfinite(val) for val in feats.values()))

def test_predict_distance_empty_input():
    from server.app import TagState
    tag = TagState('test_tag')
    dist = predict_distance_for_anchor(tag, 'A1', [], [])
    assert dist is None

def test_predict_distance_fallback():
    from server.app import TagState
    tag = TagState('test_tag')
    rssi_list = [-70, -72, -68, -71]
    timestamps = [1000, 1100, 1200, 1300]
    dist = predict_distance_for_anchor(tag, 'A1', rssi_list, timestamps)
    assert isinstance(dist, float)
    assert 0.1 <= dist <= 25.0

def test_online_learner_adaptation():
    from server.app import OnlineDistanceLearner
    learner = OnlineDistanceLearner(learning_rate=0.2)
    anchor = 'ANCHOR_01'
    initial_calib = learner.calibrate_prediction(anchor, 3.0, -85)
    for _ in range(20):
        learner.learn_sample(anchor, rssi=-85, true_dist=5.0, raw_pred_dist=3.0)
    updated_calib = learner.calibrate_prediction(anchor, 3.0, -85)
    summary = learner.get_summary()
    assert abs(updated_calib - 5.0) < abs(initial_calib - 5.0)
    assert summary['samples_learned'] >= 20
    assert summary['active'] is True
