#include <stdio.h>
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "main.h"
#include "config_manager.h"
#include "uart_handler.h"
#include "Statistics.h"
#include "BLEScanner.h"
#include "Observation.h"

static const char *TAG = "APP_MAIN";

static void observation_task(void *pvParameters);

// Global static instances of statistics engine and scanner
static Statistics s_stats;
static BLEScanner s_scanner(&s_stats);

extern "C" void app_main(void) {
    ESP_LOGI(TAG, "Initializing C++ BLE Anchor Node...");

    // 1. Initialize NVS and Config
    esp_err_t err = config_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize config manager: %s", esp_err_to_name(err));
        return;
    }

    // 2. Initialize UART console commands and communication
    err = uart_handler_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize UART: %s", esp_err_to_name(err));
        return;
    }

    // 3. Initialize BLE scanner
    err = s_scanner.init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize BLE stack: %s", esp_err_to_name(err));
        return;
    }

    err = s_scanner.start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start BLE scanning: %s", esp_err_to_name(err));
        return;
    }

    // 4. Spawn periodic observation aggregation task
    BaseType_t ret = xTaskCreate(observation_task, "observation_task", 4096, NULL, 5, NULL);
    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create observation task");
        return;
    }

    ESP_LOGI(TAG, "System running. Tag target MAC: %s", g_config.target_mac);
}

static void observation_task(void *pvParameters) {
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t interval = pdMS_TO_TICKS(1000); // 1-second window
    int window_counter = 0;

    while (1) {
        vTaskDelayUntil(&last_wake_time, interval);

        uint64_t current_time_ms = esp_timer_get_time() / 1000;

        // In NORMAL or DUAL mode, calculate stats and output JSON + debug log block
        if (g_config.mode == MODE_NORMAL || g_config.mode == MODE_DUAL) {
            AggregatedStats stats_result;
            bool success = s_stats.calculate_and_clear(stats_result, 1000);
            
            if (success) {
                window_counter++;
                
                // 1. Build and transmit JSON observation
                std::string json_str = Observation::build_json(
                    stats_result, 
                    g_config.anchor_id, 
                    g_config.target_mac, 
                    current_time_ms
                );
                uart_send_json_observation(json_str.c_str());

                // 2. Print readable diagnostic log block requested by the user
                char debug_log[256];
                snprintf(debug_log, sizeof(debug_log),
                         "\nWindow %d\n"
                         "Packets %d\n"
                         "Mean %.2f\n"
                         "Variance %.2f\n"
                         "Output Success\n",
                         window_counter,
                         stats_result.packet_count,
                         stats_result.rssi_mean,
                         stats_result.rssi_variance);
                uart_send_string(debug_log);
            }
        }
    }
}
