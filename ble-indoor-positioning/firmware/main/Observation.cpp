#include <stdio.h>
#include "Observation.h"

std::string Observation::build_json(const AggregatedStats& stats, 
                                    const std::string& anchor_id, 
                                    const std::string& target_mac, 
                                    uint64_t timestamp_ms) {
    char buf[768];
    snprintf(buf, sizeof(buf),
             "{"
             "\"type\":\"observation\","
             "\"anchor_id\":\"%s\","
             "\"timestamp\":%llu,"
             "\"device_mac\":\"%s\","
             "\"packet_count\":%d,"
             "\"scan_duration_ms\":1000,"
             "\"rssi_mean\":%.2f,"
             "\"rssi_std\":%.2f,"
             "\"rssi_variance\":%.2f,"
             "\"rssi_min\":%d,"
             "\"rssi_max\":%d,"
             "\"rssi_range\":%d,"
             "\"rssi_delta_mean\":%.2f,"
             "\"advertising_interval_ms\":%.2f,"
             "\"rssi_median\":%.2f,"
             "\"rssi_mode\":%d,"
             "\"skewness\":%.4f,"
             "\"kurtosis\":%.4f,"
             "\"percentile_25\":%.2f,"
             "\"percentile_75\":%.2f,"
             "\"packet_loss_estimate\":%.4f,"
             "\"max_consecutive_gap_ms\":%llu"
             "}",
             anchor_id.c_str(),
             timestamp_ms,
             target_mac.c_str(),
             stats.packet_count,
             stats.rssi_mean,
             stats.rssi_std,
             stats.rssi_variance,
             stats.rssi_min,
             stats.rssi_max,
             stats.rssi_range,
             stats.rssi_delta_mean,
             stats.advertising_interval_ms,
             stats.rssi_median,
             stats.rssi_mode,
             stats.skewness,
             stats.kurtosis,
             stats.percentile_25,
             stats.percentile_75,
             stats.packet_loss_estimate,
             stats.max_consecutive_gap_ms);
    return std::string(buf);
}
