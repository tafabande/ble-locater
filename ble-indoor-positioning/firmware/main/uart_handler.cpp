#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "driver/uart.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "uart_handler.h"
#include "config_manager.h"
#include "Statistics.h"

static const char *TAG = "UART_HANDLER";
#define UART_PORT UART_NUM_0
#define RX_BUF_SIZE 1024

static SemaphoreHandle_t s_uart_mutex = NULL;

static void uart_rx_task(void *pvParameters);
extern void run_statistics_self_test(void); // Declared in Statistics.h / implemented there

esp_err_t uart_handler_init(void) {
    s_uart_mutex = xSemaphoreCreateMutex();
    if (s_uart_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create UART mutex");
        return ESP_ERR_NO_MEM;
    }

    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    esp_err_t err = uart_driver_install(UART_PORT, RX_BUF_SIZE * 2, 0, 0, NULL, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install UART driver: %s", esp_err_to_name(err));
        return err;
    }

    err = uart_param_config(UART_PORT, &uart_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure UART parameters: %s", esp_err_to_name(err));
        return err;
    }

    BaseType_t ret = xTaskCreate(uart_rx_task, "uart_rx_task", 4096, NULL, 10, NULL);
    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create UART RX task");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "UART initialized at 115200 baud.");
    return ESP_OK;
}

void uart_send_string(const char *str) {
    if (s_uart_mutex == NULL) return;
    if (xSemaphoreTake(s_uart_mutex, portMAX_DELAY) == pdTRUE) {
        uart_write_bytes(UART_PORT, str, strlen(str));
        xSemaphoreGive(s_uart_mutex);
    }
}

void uart_send_json_raw_packet(const raw_packet_t *pkt) {
    char buf[128];
    snprintf(buf, sizeof(buf), "{\"type\":\"raw\",\"timestamp\":%lld,\"mac\":\"%s\",\"rssi\":%d}\n",
             pkt->timestamp_ms, pkt->mac, pkt->rssi);
    uart_send_string(buf);
}

void uart_send_json_observation(const char *json_str) {
    char *buf = (char *)malloc(strlen(json_str) + 2);
    if (buf) {
        sprintf(buf, "%s\n", json_str);
        uart_send_string(buf);
        free(buf);
    }
}

static void process_command(const char *cmd) {
    char reply[256];
    
    if (strcasecmp(cmd, "HELP") == 0) {
        snprintf(reply, sizeof(reply), 
                 "\n--- ESP32 Anchor Console Commands ---\n"
                 "HELP                             Show this help message\n"
                 "GET_CONFIG                       Print current settings\n"
                 "SET_ANCHOR=<id>                  Set the Anchor ID (max 15 chars)\n"
                 "SET_TAG=<mac>                    Set the Target Tag MAC Address (e.g. 52:06:26:03:01:DA)\n"
                 "SET_MODE=<NORMAL|RAW|DUAL>       Set the operation mode\n"
                 "TEST_MATH                        Run math aggregation self-test\n"
                 "-------------------------------------\n");
        uart_send_string(reply);
        return;
    }

    if (strcasecmp(cmd, "GET_CONFIG") == 0) {
        snprintf(reply, sizeof(reply),
                 "{\"type\":\"config\",\"anchor_id\":\"%s\",\"target_mac\":\"%s\",\"mode\":%d}\n",
                 g_config.anchor_id, g_config.target_mac, g_config.mode);
        uart_send_string(reply);
        return;
    }

    if (strcasecmp(cmd, "TEST_MATH") == 0) {
        uart_send_string("[INFO] Running statistics aggregation self-test...\n");
        run_statistics_self_test();
        return;
    }

    if (strncasecmp(cmd, "SET_ANCHOR=", 11) == 0) {
        const char *val = cmd + 11;
        if (strlen(val) == 0 || strlen(val) >= sizeof(g_config.anchor_id)) {
            uart_send_string("{\"status\":\"error\",\"message\":\"Invalid anchor ID length\"}\n");
            return;
        }
        strncpy(g_config.anchor_id, val, sizeof(g_config.anchor_id) - 1);
        g_config.anchor_id[sizeof(g_config.anchor_id) - 1] = '\0';
        config_save(&g_config);
        snprintf(reply, sizeof(reply), "{\"status\":\"ok\",\"anchor_id\":\"%s\"}\n", g_config.anchor_id);
        uart_send_string(reply);
        return;
    }

    if (strncasecmp(cmd, "SET_TAG=", 8) == 0) {
        const char *val = cmd + 8;
        uint8_t temp_bda[6];
        if (!str_to_mac(val, temp_bda)) {
            uart_send_string("{\"status\":\"error\",\"message\":\"Invalid MAC address format. Use AA:BB:CC:DD:EE:FF\"}\n");
            return;
        }
        char normalized_mac[18];
        mac_to_str(temp_bda, normalized_mac);
        strncpy(g_config.target_mac, normalized_mac, sizeof(g_config.target_mac) - 1);
        config_save(&g_config);
        snprintf(reply, sizeof(reply), "{\"status\":\"ok\",\"target_mac\":\"%s\"}\n", g_config.target_mac);
        uart_send_string(reply);
        return;
    }

    if (strncasecmp(cmd, "SET_MODE=", 9) == 0) {
        const char *val = cmd + 9;
        anchor_mode_t new_mode;
        if (strcasecmp(val, "NORMAL") == 0) {
            new_mode = MODE_NORMAL;
        } else if (strcasecmp(val, "RAW") == 0) {
            new_mode = MODE_RAW;
        } else if (strcasecmp(val, "DUAL") == 0) {
            new_mode = MODE_DUAL;
        } else {
            uart_send_string("{\"status\":\"error\",\"message\":\"Unknown mode. Use NORMAL, RAW, or DUAL\"}\n");
            return;
        }
        g_config.mode = new_mode;
        config_save(&g_config);
        snprintf(reply, sizeof(reply), "{\"status\":\"ok\",\"mode\":%d}\n", g_config.mode);
        uart_send_string(reply);
        return;
    }

    snprintf(reply, sizeof(reply), "{\"status\":\"error\",\"message\":\"Unknown command: %s. Type HELP for options.\"}\n", cmd);
    uart_send_string(reply);
}

static void uart_rx_task(void *pvParameters) {
    int line_len = 0;
    char line_buf[256];

    while (1) {
        uint8_t ch;
        int len = uart_read_bytes(UART_PORT, &ch, 1, pdMS_TO_TICKS(100));
        if (len > 0) {
            if (ch == '\n' || ch == '\r') {
                if (line_len > 0) {
                    line_buf[line_len] = '\0';
                    process_command(line_buf);
                    line_len = 0;
                }
            } else {
                if (line_len < sizeof(line_buf) - 1) {
                    line_buf[line_len++] = (char)ch;
                } else {
                    line_len = 0;
                }
            }
        }
    }
    vTaskDelete(NULL);
}
