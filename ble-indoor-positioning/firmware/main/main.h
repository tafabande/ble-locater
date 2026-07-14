#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

// System operation modes
typedef enum {
    MODE_NORMAL = 0, // Summarized observation windows only (JSON)
    MODE_RAW = 1,    // Raw packet streams only (JSON)
    MODE_DUAL = 2    // Both raw packets and summarized windows
} anchor_mode_t;

// Configuration structure
typedef struct {
    char anchor_id[16];
    char target_mac[18]; // Format: "AA:BB:CC:DD:EE:FF"
    anchor_mode_t mode;
} anchor_config_t;

// Event struct for raw packets
typedef struct {
    int64_t timestamp_ms;
    int8_t rssi;
    char mac[18];
} raw_packet_t;

// Global config reference
extern anchor_config_t g_config;

// Helper to check if a MAC address matches target
bool mac_matches_target(const uint8_t *bda);

// Helper to convert MAC bytes to string
void mac_to_str(const uint8_t *bda, char *str);

// Helper to parse MAC string to bytes
bool str_to_mac(const char *str, uint8_t *bda);

#endif // MAIN_H
