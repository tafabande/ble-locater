import math
from collector.emulator import calculate_stats

def test_statistics_engine_math_advanced():
    packets = [{'timestamp': 100, 'rssi': -55}, {'timestamp': 200, 'rssi': -58}, {'timestamp': 310, 'rssi': -56}, {'timestamp': 400, 'rssi': -60}, {'timestamp': 505, 'rssi': -57}]
    mac = '52:06:26:03:01:DA'
    anchor_id = 'A1'
    window_start_ms = 0
    obs = calculate_stats(packets, anchor_id, mac, window_start_ms)
    assert obs['packet_count'] == 5
    assert obs['rssi_mean'] == -57.2
    assert obs['rssi_min'] == -60
    assert obs['rssi_max'] == -55
    assert obs['rssi_range'] == 5
    assert obs['rssi_delta_mean'] == 3.0
    assert obs['max_consecutive_gap_ms'] == 110
    rssis = [-55, -58, -56, -60, -57]
    mean = sum(rssis) / len(rssis)
    expected_variance = sum(((r - mean) ** 2 for r in rssis)) / len(rssis)
    expected_std = math.sqrt(expected_variance)
    assert math.isclose(obs['rssi_variance'], expected_variance, abs_tol=0.01)
    assert math.isclose(obs['rssi_std'], expected_std, abs_tol=0.01)
    assert obs['rssi_median'] == -57.0
    assert obs['percentile_25'] == -58.0
    assert obs['percentile_75'] == -56.0
    norm_diffs = [(r - mean) / expected_std for r in rssis]
    expected_skewness = sum((d ** 3 for d in norm_diffs)) / 5
    expected_kurtosis = sum((d ** 4 for d in norm_diffs)) / 5
    assert math.isclose(obs['skewness'], expected_skewness, abs_tol=0.001)
    assert math.isclose(obs['kurtosis'], expected_kurtosis, abs_tol=0.001)
    assert obs['packet_loss_estimate'] == 0.0

def test_statistics_engine_mode_and_packet_loss():
    packets = [{'timestamp': 100, 'rssi': -50}, {'timestamp': 300, 'rssi': -55}, {'timestamp': 400, 'rssi': -55}, {'timestamp': 710, 'rssi': -60}]
    obs = calculate_stats(packets, 'A1', '52:06:26:03:01:DA', 0)
    assert obs['rssi_mode'] == -55
    assert math.isclose(obs['packet_loss_estimate'], 3.0 / 7.0, abs_tol=0.001)
    assert obs['max_consecutive_gap_ms'] == 310
