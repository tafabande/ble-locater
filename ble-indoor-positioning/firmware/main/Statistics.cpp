#include <math.h>
#include <algorithm>
#include <map>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "Statistics.h"

static const char *TAG = "STATISTICS";

Statistics::Statistics() {
    m_mutex = xSemaphoreCreateMutex();
    if (m_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create statistics mutex");
    }
}

Statistics::~Statistics() {
    if (m_mutex != NULL) {
        vSemaphoreDelete((SemaphoreHandle_t)m_mutex);
    }
}

void Statistics::push_packet(const Packet& pkt) {
    if (m_mutex == NULL) return;
    if (xSemaphoreTake((SemaphoreHandle_t)m_mutex, portMAX_DELAY) == pdTRUE) {
        m_packets.push_back(pkt);
        xSemaphoreGive((SemaphoreHandle_t)m_mutex);
    }
}

bool Statistics::calculate_and_clear(AggregatedStats& out_stats, uint64_t window_duration_ms) {
    if (m_mutex == NULL) return false;

    std::vector<Packet> local_packets;

    // Fast copy and clear under mutex
    if (xSemaphoreTake((SemaphoreHandle_t)m_mutex, portMAX_DELAY) == pdTRUE) {
        if (!m_packets.empty()) {
            local_packets = std::move(m_packets);
            m_packets.clear();
        }
        xSemaphoreGive((SemaphoreHandle_t)m_mutex);
    }

    int count = local_packets.size();
    if (count == 0) {
        return false;
    }

    out_stats.packet_count = count;

    // Sort packets by timestamp (should already be sorted, but let's be safe)
    std::sort(local_packets.begin(), local_packets.end(), [](const Packet& a, const Packet& b) {
        return a.timestamp < b.timestamp;
    });

    // 1. Mean RSSI
    double rssi_sum = 0.0;
    int rssi_min = local_packets[0].rssi;
    int rssi_max = local_packets[0].rssi;

    std::vector<int> rssis;
    rssis.reserve(count);

    for (const auto& pkt : local_packets) {
        rssi_sum += pkt.rssi;
        rssis.push_back(pkt.rssi);
        if (pkt.rssi < rssi_min) rssi_min = pkt.rssi;
        if (pkt.rssi > rssi_max) rssi_max = pkt.rssi;
    }

    double rssi_mean = rssi_sum / count;
    out_stats.rssi_mean = rssi_mean;
    out_stats.rssi_min = rssi_min;
    out_stats.rssi_max = rssi_max;
    out_stats.rssi_range = rssi_max - rssi_min;

    // Sort RSSIs for median and percentiles
    std::sort(rssis.begin(), rssis.end());

    // 2. Median RSSI
    if (count % 2 == 1) {
        out_stats.rssi_median = rssis[count / 2];
    } else {
        out_stats.rssi_median = (rssis[count / 2 - 1] + rssis[count / 2]) / 2.0;
    }

    // 3. Mode RSSI
    int mode_val = rssis[0];
    int max_freq = 0;
    int current_val = rssis[0];
    int current_freq = 0;
    for (int r : rssis) {
        if (r == current_val) {
            current_freq++;
        } else {
            if (current_freq > max_freq) {
                max_freq = current_freq;
                mode_val = current_val;
            }
            current_val = r;
            current_freq = 1;
        }
    }
    if (current_freq > max_freq) {
        mode_val = current_val;
    }
    out_stats.rssi_mode = mode_val;

    // 4. Percentiles (Linear Interpolation method)
    auto get_percentile = [&rssis, count](double p) -> double {
        double idx = p * (count - 1);
        int low = (int)floor(idx);
        int high = (int)ceil(idx);
        if (low == high) return rssis[low];
        return rssis[low] + (idx - low) * (rssis[high] - rssis[low]);
    };
    out_stats.percentile_25 = get_percentile(0.25);
    out_stats.percentile_75 = get_percentile(0.75);

    // 5. Variance, Standard Deviation, Skewness, Kurtosis
    double variance_sum = 0.0;
    double skewness_sum = 0.0;
    double kurtosis_sum = 0.0;

    for (int r : rssis) {
        double diff = r - rssi_mean;
        variance_sum += diff * diff;
    }
    double rssi_variance = variance_sum / count;
    double rssi_std = sqrt(rssi_variance);

    out_stats.rssi_variance = rssi_variance;
    out_stats.rssi_std = rssi_std;

    if (rssi_std > 0.0001) {
        for (int r : rssis) {
            double normalized_diff = (r - rssi_mean) / rssi_std;
            skewness_sum += pow(normalized_diff, 3);
            kurtosis_sum += pow(normalized_diff, 4);
        }
        out_stats.skewness = skewness_sum / count;
        out_stats.kurtosis = kurtosis_sum / count;
    } else {
        out_stats.skewness = 0.0;
        out_stats.kurtosis = 0.0;
    }

    // 6. Consecutive Packet metrics (Delta Mean, Advertising Interval, Gaps, Loss)
    double rssi_delta_mean = 0.0;
    double advertising_interval_ms = 0.0;
    uint64_t max_consecutive_gap_ms = 0;
    int lost_packets = 0;

    if (count > 1) {
        double delta_sum = 0.0;
        for (int i = 1; i < count; i++) {
            delta_sum += abs(local_packets[i].rssi - local_packets[i - 1].rssi);
            
            uint64_t gap = local_packets[i].timestamp - local_packets[i - 1].timestamp;
            if (gap > max_consecutive_gap_ms) {
                max_consecutive_gap_ms = gap;
            }

            // Estimate lost packets based on standard 100ms advertising interval
            int expected_gaps = (int)round((double)gap / 100.0);
            if (expected_gaps > 1) {
                lost_packets += (expected_gaps - 1);
            }
        }
        rssi_delta_mean = delta_sum / (count - 1);
        advertising_interval_ms = (double)(local_packets[count - 1].timestamp - local_packets[0].timestamp) / (count - 1);
    } else {
        max_consecutive_gap_ms = window_duration_ms;
    }

    out_stats.rssi_delta_mean = rssi_delta_mean;
    out_stats.advertising_interval_ms = advertising_interval_ms;
    out_stats.max_consecutive_gap_ms = max_consecutive_gap_ms;

    if (count + lost_packets > 0) {
        out_stats.packet_loss_estimate = (double)lost_packets / (count + lost_packets);
    } else {
        out_stats.packet_loss_estimate = 0.0;
    }

    return true;
}

// Global math verification function
extern "C" void run_statistics_self_test(void) {
    Statistics stats;
    
    // Synthetic packet list: Known Mean, Known Gaps
    stats.push_packet(Packet(-55, 100, "52:06:26:03:01:DA"));
    stats.push_packet(Packet(-58, 200, "52:06:26:03:01:DA"));
    stats.push_packet(Packet(-56, 310, "52:06:26:03:01:DA"));
    stats.push_packet(Packet(-60, 400, "52:06:26:03:01:DA"));
    stats.push_packet(Packet(-57, 505, "52:06:26:03:01:DA"));

    AggregatedStats res;
    bool success = stats.calculate_and_clear(res, 1000);

    if (!success) {
        ESP_LOGE("SELF_TEST", "MATH TEST: FAILED - Calculation returned false");
        return;
    }

    bool passed = true;

    // Check packet count
    if (res.packet_count != 5) {
        ESP_LOGE("SELF_TEST", "FAIL: Count. Expected 5, got %d", res.packet_count);
        passed = false;
    }
    // Check mean: expected -57.2
    if (fabs(res.rssi_mean - (-57.2)) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Mean. Expected -57.2, got %.2f", res.rssi_mean);
        passed = false;
    }
    // Check min: -60, max: -55
    if (res.rssi_min != -60 || res.rssi_max != -55 || res.rssi_range != 5) {
        ESP_LOGE("SELF_TEST", "FAIL: Min/Max/Range. Got Min=%d, Max=%d, Range=%d", res.rssi_min, res.rssi_max, res.rssi_range);
        passed = false;
    }
    // Check variance: expected 3.36
    if (fabs(res.rssi_variance - 3.36) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Variance. Expected 3.36, got %.2f", res.rssi_variance);
        passed = false;
    }
    // Check std: expected sqrt(3.36) = 1.833
    if (fabs(res.rssi_std - sqrt(3.36)) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Std. Expected 1.83, got %.2f", res.rssi_std);
        passed = false;
    }
    // Check median: sorted is [-60, -58, -57, -56, -55], middle is -57.0
    if (fabs(res.rssi_median - (-57.0)) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Median. Expected -57.0, got %.2f", res.rssi_median);
        passed = false;
    }
    // Check delta RSSI: consecutive diffs are [3, 2, 4, 3], mean is 3.0
    if (fabs(res.rssi_delta_mean - 3.0) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Delta Mean. Expected 3.0, got %.2f", res.rssi_delta_mean);
        passed = false;
    }
    // Check advertising interval: span (505 - 100) / 4 = 101.25
    if (fabs(res.advertising_interval_ms - 101.25) > 0.001) {
        ESP_LOGE("SELF_TEST", "FAIL: Adv Interval. Expected 101.25, got %.2f", res.advertising_interval_ms);
        passed = false;
    }
    // Check max gap: expected 110 (between 200 and 310)
    if (res.max_consecutive_gap_ms != 110) {
        ESP_LOGE("SELF_TEST", "FAIL: Max Gap. Expected 110, got %llu", res.max_consecutive_gap_ms);
        passed = false;
    }

    if (passed) {
        ESP_LOGI("SELF_TEST", "MATH TEST: PASSED");
        printf("MATH TEST: PASSED\n");
    } else {
        ESP_LOGE("SELF_TEST", "MATH TEST: FAILED");
        printf("MATH TEST: FAILED\n");
    }
}
