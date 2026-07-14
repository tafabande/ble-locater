#include <string.h>
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "BLEScanner.h"
#include "main.h"
#include "uart_handler.h"

static const char *TAG = "BLE_SCANNER";

BLEScanner* BLEScanner::s_instance = nullptr;

// Scan parameters configuration
static esp_ble_scan_params_t ble_scan_params = {
    .scan_type              = BLE_SCAN_TYPE_PASSIVE,
    .addr_type              = BLE_ADDR_TYPE_PUBLIC,
    .scan_filter_policy     = BLE_SCAN_FILTER_ALLOW_ALL,
    .scan_interval          = 0x0050, // 50 ms
    .scan_window            = 0x0030, // 30 ms
    .scan_duplicate_filter  = BLE_SCAN_DUPLICATE_DISABLE
};

BLEScanner::BLEScanner(Statistics* stats) : m_stats(stats) {
    s_instance = this;
}

BLEScanner::~BLEScanner() {
    if (s_instance == this) {
        s_instance = nullptr;
    }
}

esp_err_t BLEScanner::init() {
    esp_err_t err = esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to release classic BT memory: %s", esp_err_to_name(err));
        return err;
    }

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    err = esp_bt_controller_init(&bt_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "BT controller init failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "BT controller enable failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_bluedroid_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid init failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_bluedroid_enable();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid enable failed: %s", esp_err_to_name(err));
        return err;
    }

    // Register our C-to-C++ gap callback
    err = esp_ble_gap_register_callback([](esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
        gap_callback((uint32_t)event, (void*)param);
    });
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "GAP callback registration failed: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "BLE Stack initialized successfully.");
    return ESP_OK;
}

esp_err_t BLEScanner::start() {
    esp_err_t err = esp_ble_gap_set_scan_params(&ble_scan_params);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set BLE scan parameters: %s", esp_err_to_name(err));
        return err;
    }
    return ESP_OK;
}

esp_err_t BLEScanner::stop() {
    esp_err_t err = esp_ble_gap_stop_scanning();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to stop BLE scanning: %s", esp_err_to_name(err));
        return err;
    }
    ESP_LOGI(TAG, "BLE scanning stopped.");
    return ESP_OK;
}

void BLEScanner::gap_callback(uint32_t event, void *param) {
    esp_ble_gap_cb_param_t *scan_param = (esp_ble_gap_cb_param_t *)param;
    if (s_instance == nullptr) return;

    switch (event) {
        case ESP_GAP_BLE_SCAN_PARAM_SET_COMPLETE_EVT: {
            if (scan_param->scan_param_srv_com.status == ESP_BT_STATUS_SUCCESS) {
                ESP_LOGI(TAG, "Scan parameters set. Starting continuous scan...");
                esp_ble_gap_start_scanning(0); // 0 means scan continuously
            } else {
                ESP_LOGE(TAG, "Failed to set scan parameters, status: %d", scan_param->scan_param_srv_com.status);
            }
            break;
        }
        case ESP_GAP_BLE_SCAN_START_COMPLETE_EVT: {
            if (scan_param->scan_start_cmpl.status == ESP_BT_STATUS_SUCCESS) {
                ESP_LOGI(TAG, "Continuous BLE scan started.");
            } else {
                ESP_LOGE(TAG, "Failed to start BLE scan, status: %d", scan_param->scan_start_cmpl.status);
            }
            break;
        }
        case ESP_GAP_BLE_SCAN_RESULT_EVT: {
            if (scan_param->scan_rst.search_evt == ESP_GAP_SEARCH_INQ_RES_EVT) {
                s_instance->handleScanResult(scan_param->scan_rst.rssi, scan_param->scan_rst.bda);
            }
            break;
        }
        default:
            break;
    }
}

void BLEScanner::handleScanResult(int8_t rssi, const uint8_t* bda) {
    if (mac_matches_target(bda)) {
        char mac_str[18];
        mac_to_str(bda, mac_str);
        uint64_t timestamp_ms = esp_timer_get_time() / 1000;

        Packet pkt(rssi, timestamp_ms, mac_str, -1);

        // Send raw JSON output immediately in RAW or DUAL mode
        if (g_config.mode == MODE_RAW || g_config.mode == MODE_DUAL) {
            raw_packet_t raw_pkt;
            raw_pkt.timestamp_ms = (int64_t)timestamp_ms;
            raw_pkt.rssi = rssi;
            strcpy(raw_pkt.mac, mac_str);
            uart_send_json_raw_packet(&raw_pkt);
        }

        // Push to buffer in NORMAL or DUAL mode for aggregation
        if (g_config.mode == MODE_NORMAL || g_config.mode == MODE_DUAL) {
            m_stats->push_packet(pkt);
        }
    }
}
