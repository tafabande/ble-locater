#ifndef BLE_SCANNER_H
#define BLE_SCANNER_H

#include "esp_err.h"
#include "Statistics.h"

class BLEScanner {
private:
    Statistics* m_stats;
    static BLEScanner* s_instance;

    // Static GAP callback to interface with ESP-IDF C API
    static void gap_callback(uint32_t event, void *param);

public:
    BLEScanner(Statistics* stats);
    ~BLEScanner();

    // Initialize BLE controller and stack
    esp_err_t init();

    // Start passive scan
    esp_err_t start();

    // Stop scan
    esp_err_t stop();

    // Accessor to get static instance for C callbacks
    static BLEScanner* getInstance() { return s_instance; }
    
    // Internal processor for scan results
    void handleScanResult(int8_t rssi, const uint8_t* bda);
};

#endif // BLE_SCANNER_H
