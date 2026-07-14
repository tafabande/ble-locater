#ifndef STATISTICS_H
#define STATISTICS_H

#include <vector>
#include "Packet.h"

// Structure to hold all advanced calculated features
struct AggregatedStats {
    int packet_count;
    double rssi_mean;
    double rssi_std;
    double rssi_variance;
    int rssi_min;
    int rssi_max;
    int rssi_range;
    double rssi_delta_mean;
    double advertising_interval_ms;
    
    // Additional features requested by the user
    double rssi_median;
    int rssi_mode;
    double skewness;
    double kurtosis;
    double percentile_25;
    double percentile_75;
    double packet_loss_estimate;
    uint64_t max_consecutive_gap_ms;
};

class Statistics {
private:
    std::vector<Packet> m_packets;
    void* m_mutex; // FreeRTOS SemaphoreHandle_t represented as void* to avoid header pollution

public:
    Statistics();
    ~Statistics();

    // Push a new packet in a thread-safe manner
    void push_packet(const Packet& pkt);

    // Calculate aggregated statistics over the buffered packets and clear the buffer
    bool calculate_and_clear(AggregatedStats& out_stats, uint64_t window_duration_ms = 1000);
};

#endif // STATISTICS_H
