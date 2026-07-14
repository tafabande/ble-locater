import math
from collector.emulator import calculate_stats


def test_statistics_engine_math_advanced():
    """Validates the mathematical correctness of advanced features in the statistics engine.
    
    This matches the exact logic implemented in C++ in Statistics.cpp.
    """
    # Sample packet buffer
    packets = [
        {"timestamp": 100, "rssi": -55},
        {"timestamp": 200, "rssi": -58},
        {"timestamp": 310, "rssi": -56},
        {"timestamp": 400, "rssi": -60},
        {"timestamp": 505, "rssi": -57}
    ]
    
    mac = "52:06:26:03:01:DA"
    anchor_id = "A1"
    window_start_ms = 0
    
    obs = calculate_stats(packets, anchor_id, mac, window_start_ms)
    
    # 1. Standard metrics
    assert obs["packet_count"] == 5
    assert obs["rssi_mean"] == -57.2
    assert obs["rssi_min"] == -60
    assert obs["rssi_max"] == -55
    assert obs["rssi_range"] == 5
    assert obs["rssi_delta_mean"] == 3.0
    assert obs["max_consecutive_gap_ms"] == 110 # Max gap is 110 (200 to 310)

    # 2. Population Variance & Standard Deviation
    rssis = [-55, -58, -56, -60, -57]
    mean = sum(rssis) / len(rssis)
    expected_variance = sum((r - mean)**2 for r in rssis) / len(rssis)
    expected_std = math.sqrt(expected_variance)
    
    assert math.isclose(obs["rssi_variance"], expected_variance, abs_tol=0.01)
    assert math.isclose(obs["rssi_std"], expected_std, abs_tol=0.01)
    
    # 3. Median & Mode
    # Sorted: [-60, -58, -57, -56, -55]
    assert obs["rssi_median"] == -57.0
    # Mode: Each appears once, max(set(sorted_rssis), key=rssis.count) will pick the first unique value based on occurrences.
    # We will test Mode with duplicate values below for a stronger assert.
    
    # 4. Percentiles (Linear Interpolation)
    # index_25 = 0.25 * 4 = 1.0 -> sorted[1] = -58.0
    # index_75 = 0.75 * 4 = 3.0 -> sorted[3] = -56.0
    assert obs["percentile_25"] == -58.0
    assert obs["percentile_75"] == -56.0
    
    # 5. Skewness & Kurtosis
    norm_diffs = [(r - mean) / expected_std for r in rssis]
    expected_skewness = sum(d**3 for d in norm_diffs) / 5
    expected_kurtosis = sum(d**4 for d in norm_diffs) / 5

    
    assert math.isclose(obs["skewness"], expected_skewness, abs_tol=0.001)
    assert math.isclose(obs["kurtosis"], expected_kurtosis, abs_tol=0.001)

    # 6. Packet Loss (All gaps around 100ms, none lost)
    assert obs["packet_loss_estimate"] == 0.0


def test_statistics_engine_mode_and_packet_loss():
    """Verifies Mode RSSI and Packet Loss Estimate calculations under missing packet scenarios."""
    # Simulating standard 100ms interval beacon with missing advertisements:
    # Gap 1: 200ms (1 lost packet)
    # Gap 2: 100ms (0 lost)
    # Gap 3: 310ms (2 lost packets)
    packets = [
        {"timestamp": 100, "rssi": -50},
        {"timestamp": 300, "rssi": -55},  # Gap = 200 -> lost = round(200/100)-1 = 1
        {"timestamp": 400, "rssi": -55},  # Gap = 100 -> lost = round(100/100)-1 = 0
        {"timestamp": 710, "rssi": -60}   # Gap = 310 -> lost = round(310/100)-1 = 2
    ]
    
    obs = calculate_stats(packets, "A1", "52:06:26:03:01:DA", 0)
    
    # Mode RSSI: -55 is the only duplicate, so it is the clear mode
    assert obs["rssi_mode"] == -55
    
    # Packet Loss Estimate:
    # Total packets received = 4
    # Lost packets = 1 + 0 + 2 = 3
    # Loss estimate = 3 / (4 + 3) = 3/7 = 0.428571...
    assert math.isclose(obs["packet_loss_estimate"], 3.0 / 7.0, abs_tol=0.001)
    assert obs["max_consecutive_gap_ms"] == 310
