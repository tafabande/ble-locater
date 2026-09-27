/*
 * ESP32 Autonomous Wireless BLE Anchor Node Firmware (ESP-IDF Native)
 *
 * Implements:
 *  1. Dual-Role BLE:
 *     - Broadcasts anchor identity beacon (NODE_A, NODE_B, NODE_C, NODE_D)
 *     - Continuously scans for target asset tag MAC and peer anchor beacons
 *  2. Wi-Fi Station & UDP Ingestion on Port 5005:
 *     - Dynamic zero-config discovery: updates host IP on COLLECTOR_ANNOUNCE
 *     - Periodic heartbeats every 2500ms over UDP
 *     - Streams raw tag detections and inter-anchor measurements over UDP & UART
 *  3. Persistent NVS Storage:
 *     - Settings saved permanently in NVS Flash (Node ID, Wi-Fi SSID/Pass, Target Tag, Host IP, Port)
 *  4. Full Serial UART Console Interface for real automated provisioning
 */

#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <ctype.h>
#include <sys/param.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_netif.h"
#include "esp_mac.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/uart.h"

#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include "lwip/netdb.h"

#include "host/ble_gap.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"

#define STATUS_LED_GPIO GPIO_NUM_2
#define UART_CONSOLE_PORT UART_NUM_0
#define UART_BUF_SIZE 1024

static const char *TAG = "WIFI_ANCHOR";

// Persistent Configuration Variables (in NVS "anchor_cfg")
static char g_wifi_ssid[33] = "IndoorPositioning_WiFi";
static char g_wifi_pass[65] = "";
static char g_anchor_id[32] = "NODE_A";
static char g_target_mac[18] = "52:06:26:03:01:DA";
static char g_host_ip[40] = "255.255.255.255";
static uint16_t g_udp_port = 5005;

static char g_device_mac[18] = "00:00:00:00:00:00";
static char g_node_ip[16] = "0.0.0.0";
static bool g_wifi_connected = false;
static int g_udp_sock = -1;
static int g_led_state = 0;
static uint8_t g_ble_own_addr_type;

// Forward declarations
static void load_configuration(void);
static void save_configuration(void);
static void wifi_init_sta(void);
static void send_udp_payload(const char *payload);
static void send_heartbeat(void);
static void start_ble_scan(void);
static void start_ble_adv(void);

// ─────────────────────────────────────────────────────────────────────────────
// NVS Configuration Management
// ─────────────────────────────────────────────────────────────────────────────
static void load_configuration(void) {
    nvs_handle_t h;
    esp_err_t err = nvs_open("anchor_cfg", NVS_READONLY, &h);
    if (err == ESP_OK) {
        size_t s = sizeof(g_wifi_ssid);
        nvs_get_str(h, "ssid", g_wifi_ssid, &s);

        s = sizeof(g_wifi_pass);
        nvs_get_str(h, "pass", g_wifi_pass, &s);

        s = sizeof(g_anchor_id);
        nvs_get_str(h, "anchor", g_anchor_id, &s);

        s = sizeof(g_target_mac);
        nvs_get_str(h, "tag", g_target_mac, &s);

        s = sizeof(g_host_ip);
        nvs_get_str(h, "host", g_host_ip, &s);

        nvs_get_u16(h, "port", &g_udp_port);

        nvs_close(h);
    }

    ESP_LOGI(TAG, "Config Loaded: Anchor=%s Tag=%s SSID='%s' Host=%s:%u",
             g_anchor_id, g_target_mac, g_wifi_ssid, g_host_ip, g_udp_port);
}

static void save_configuration(void) {
    nvs_handle_t h;
    esp_err_t err = nvs_open("anchor_cfg", NVS_READWRITE, &h);
    if (err == ESP_OK) {
        nvs_set_str(h, "ssid", g_wifi_ssid);
        nvs_set_str(h, "pass", g_wifi_pass);
        nvs_set_str(h, "anchor", g_anchor_id);
        nvs_set_str(h, "tag", g_target_mac);
        nvs_set_str(h, "host", g_host_ip);
        nvs_set_u16(h, "port", g_udp_port);
        nvs_commit(h);
        nvs_close(h);
        printf("{\"status\":\"ok\",\"message\":\"Configuration permanently committed to NVS flash\"}\n");
    } else {
        printf("{\"status\":\"error\",\"message\":\"Failed to commit to NVS flash\"}\n");
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Wi-Fi Station
// ─────────────────────────────────────────────────────────────────────────────
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                               int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        g_wifi_connected = false;
        gpio_set_level(STATUS_LED_GPIO, 0);
        ESP_LOGW(TAG, "Wi-Fi disconnected. Reconnecting in 2s...");
        vTaskDelay(pdMS_TO_TICKS(2000));
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        snprintf(g_node_ip, sizeof(g_node_ip), IPSTR, IP2STR(&event->ip_info.ip));
        g_wifi_connected = true;
        gpio_set_level(STATUS_LED_GPIO, 1);
        ESP_LOGI(TAG, "✔ Wi-Fi Connected! IP Address: %s", g_node_ip);
    }
}

static void wifi_init_sta(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = { 0 };
    strncpy((char *)wifi_config.sta.ssid, g_wifi_ssid, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, g_wifi_pass, sizeof(wifi_config.sta.password) - 1);
    wifi_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
}

// ─────────────────────────────────────────────────────────────────────────────
// UDP Ingestion & Transmission on Port 5005
// ─────────────────────────────────────────────────────────────────────────────
static void send_udp_payload(const char *payload) {
    if (!g_wifi_connected || g_udp_sock < 0) return;

    struct sockaddr_in dest_addr;
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(g_udp_port);

    if (strcmp(g_host_ip, "255.255.255.255") == 0 || inet_aton(g_host_ip, &dest_addr.sin_addr) == 0) {
        dest_addr.sin_addr.s_addr = htonl(INADDR_BROADCAST);
    }

    sendto(g_udp_sock, payload, strlen(payload), 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
}

static void send_heartbeat(void) {
    if (!g_wifi_connected) return;

    wifi_ap_record_t ap_info;
    int rssi = -99;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        rssi = ap_info.rssi;
    }

    char hb[320];
    snprintf(hb, sizeof(hb),
             "{\"type\":\"heartbeat\","
             "\"provenance\":\"HARDWARE_WIFI_UDP\","
             "\"node\":\"%s\","
             "\"mac\":\"%s\","
             "\"ip\":\"%s\","
             "\"collector_target\":\"%s\","
             "\"wifi_rssi\":%d}",
             g_anchor_id, g_device_mac, g_node_ip, g_host_ip, rssi);

    send_udp_payload(hb);
}

static void udp_server_task(void *pvParameters) {
    char rx_buffer[1024];

    while (1) {
        if (!g_wifi_connected) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }

        struct sockaddr_in listen_addr;
        listen_addr.sin_addr.s_addr = htonl(INADDR_ANY);
        listen_addr.sin_family = AF_INET;
        listen_addr.sin_port = htons(g_udp_port);

        g_udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
        if (g_udp_sock < 0) {
            ESP_LOGE(TAG, "Unable to create UDP socket: errno %d", errno);
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        int broadcast = 1;
        setsockopt(g_udp_sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));

        int err = bind(g_udp_sock, (struct sockaddr *)&listen_addr, sizeof(listen_addr));
        if (err < 0) {
            ESP_LOGE(TAG, "UDP socket unable to bind: errno %d", errno);
            close(g_udp_sock);
            g_udp_sock = -1;
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        // Set receive timeout
        struct timeval tv = { .tv_sec = 0, .tv_usec = 200000 }; // 200ms
        setsockopt(g_udp_sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        ESP_LOGI(TAG, "📡 Hardware UDP listener active on port %u", g_udp_port);

        uint32_t last_hb_tick = xTaskGetTickCount();

        while (g_wifi_connected) {
            struct sockaddr_in source_addr;
            socklen_t socklen = sizeof(source_addr);
            int len = recvfrom(g_udp_sock, rx_buffer, sizeof(rx_buffer) - 1, 0,
                               (struct sockaddr *)&source_addr, &socklen);

            if (len > 0) {
                rx_buffer[len] = '\0';
                if (strstr(rx_buffer, "COLLECTOR_ANNOUNCE") != NULL) {
                    char sender_ip[16];
                    inet_ntoa_r(source_addr.sin_addr, sender_ip, sizeof(sender_ip));

                    if (strcmp(g_host_ip, sender_ip) != 0) {
                        strncpy(g_host_ip, sender_ip, sizeof(g_host_ip) - 1);
                        ESP_LOGI(TAG, "[AUTO-DISCOVERY] Dynamic Host IP updated to: %s", g_host_ip);
                    }

                    // Send immediate handshake ack back
                    wifi_ap_record_t ap_info;
                    int wifi_rssi = -99;
                    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
                        wifi_rssi = ap_info.rssi;
                    }

                    char ack[320];
                    snprintf(ack, sizeof(ack),
                             "{\"type\":\"discovery_ack\","
                             "\"provenance\":\"HARDWARE_WIFI_UDP\","
                             "\"node\":\"%s\","
                             "\"mac\":\"%s\","
                             "\"ip\":\"%s\","
                             "\"wifi_rssi\":%d}",
                             g_anchor_id, g_device_mac, g_node_ip, wifi_rssi);
                    send_udp_payload(ack);
                }
            }

            // Periodic heartbeat every 2500ms
            if (pdTICKS_TO_MS(xTaskGetTickCount() - last_hb_tick) >= 2500) {
                send_heartbeat();
                last_hb_tick = xTaskGetTickCount();
            }
        }

        if (g_udp_sock != -1) {
            close(g_udp_sock);
            g_udp_sock = -1;
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// NimBLE GAP Callbacks & Dual-Role BLE (Scan & Advertise)
// ─────────────────────────────────────────────────────────────────────────────
static int gap_event_cb(struct ble_gap_event *event, void *arg) {
    if (event->type == BLE_GAP_EVENT_DISC) {
        char dev_mac[18];
        snprintf(dev_mac, sizeof(dev_mac), "%02X:%02X:%02X:%02X:%02X:%02X",
                 event->disc.addr.val[5], event->disc.addr.val[4], event->disc.addr.val[3],
                 event->disc.addr.val[2], event->disc.addr.val[1], event->disc.addr.val[0]);

        int8_t rssi = event->disc.rssi;
        uint64_t ts = esp_timer_get_time() / 1000;

        // 1. Target Tracking Tag Match
        if (strcasecmp(dev_mac, g_target_mac) == 0) {
            g_led_state = !g_led_state;
            gpio_set_level(STATUS_LED_GPIO, g_led_state);

            char json_payload[384];
            snprintf(json_payload, sizeof(json_payload),
                     "{\"type\":\"raw\","
                     "\"provenance\":\"HARDWARE_WIFI_UDP\","
                     "\"node\":\"%s\","
                     "\"mac\":\"%s\","
                     "\"tag\":\"%s\","
                     "\"rssi\":%d,"
                     "\"timestamp\":%llu}",
                     g_anchor_id, g_device_mac, dev_mac, rssi, ts);

            send_udp_payload(json_payload);
            printf("%s\n", json_payload);
            return 0;
        }

        // 2. Peer Anchor Detection (Inter-Anchor Ranging)
        struct ble_hs_adv_fields fields;
        if (ble_hs_adv_parse_fields(&fields, event->disc.data, event->disc.length_data) == 0) {
            char peer_id[32] = {0};
            bool is_peer = false;

            if (fields.name != NULL && fields.name_len > 0) {
                int len = MIN(fields.name_len, (int)sizeof(peer_id) - 1);
                memcpy(peer_id, fields.name, len);
                peer_id[len] = '\0';
                if ((strncmp(peer_id, "NODE_", 5) == 0 || strncmp(peer_id, "ANCHOR_", 7) == 0) &&
                    strcasecmp(peer_id, g_anchor_id) != 0) {
                    is_peer = true;
                }
            } else if (fields.mfg_data != NULL && fields.mfg_data_len >= 4) {
                if (fields.mfg_data[0] == 0x41 && fields.mfg_data[1] == 0x4E && fields.mfg_data[2] == 0x43) {
                    snprintf(peer_id, sizeof(peer_id), "NODE_%c", fields.mfg_data[3]);
                    if (strcasecmp(peer_id, g_anchor_id) != 0) {
                        is_peer = true;
                    }
                }
            }

            if (is_peer) {
                char peer_payload[384];
                snprintf(peer_payload, sizeof(peer_payload),
                         "{\"type\":\"inter_anchor\","
                         "\"provenance\":\"HARDWARE_WIFI_UDP\","
                         "\"from_node\":\"%s\","
                         "\"from_mac\":\"%s\","
                         "\"to_node\":\"%s\","
                         "\"to_mac\":\"%s\","
                         "\"rssi\":%d,"
                         "\"timestamp\":%llu}",
                         g_anchor_id, g_device_mac, peer_id, dev_mac, rssi, ts);

                send_udp_payload(peer_payload);
                printf("%s\n", peer_payload);
            }
        }
    } else if (event->type == BLE_GAP_EVENT_DISC_COMPLETE) {
        start_ble_scan();
    }
    return 0;
}

static void start_ble_scan(void) {
    struct ble_gap_disc_params disc_params = {
        .filter_duplicates = 0,
        .passive = 1,
        .itvl = 80, // 50ms
        .window = 48, // 30ms
        .filter_policy = 0,
        .limited = 0,
    };

    ble_gap_disc(g_ble_own_addr_type, BLE_HS_FOREVER, &disc_params, gap_event_cb, NULL);
}

static void start_ble_adv(void) {
    struct ble_gap_adv_params adv_params = {
        .conn_mode = BLE_GAP_CONN_MODE_NON,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
        .itvl_min = 160,
        .itvl_max = 160,
    };

    struct ble_hs_adv_fields fields;
    memset(&fields, 0, sizeof(fields));

    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (uint8_t *)g_anchor_id;
    fields.name_len = strlen(g_anchor_id);
    fields.name_is_complete = 1;

    char mfg[4] = {'A', 'N', 'C', 'A'};
    if (strlen(g_anchor_id) > 0) {
        mfg[3] = g_anchor_id[strlen(g_anchor_id) - 1];
    }
    fields.mfg_data = (uint8_t *)mfg;
    fields.mfg_data_len = 4;

    ble_gap_adv_set_fields(&fields);
    ble_gap_adv_start(g_ble_own_addr_type, NULL, BLE_HS_FOREVER, &adv_params, gap_event_cb, NULL);
}

static void ble_host_task(void *param) {
    nimble_port_run();
    nimble_port_freertos_deinit();
}

static void on_ble_sync(void) {
    ble_hs_id_infer_auto(0, &g_ble_own_addr_type);
    start_ble_adv();
    start_ble_scan();
    ESP_LOGI(TAG, "✔ BLE Dual-Role Stack Running (Advertising as '%s')", g_anchor_id);
}

// ─────────────────────────────────────────────────────────────────────────────
// Real Serial UART Console Interface for Provisioning
// ─────────────────────────────────────────────────────────────────────────────
static void process_serial_line(char *line) {
    while (*line == ' ' || *line == '\r' || *line == '\n') line++;
    int len = strlen(line);
    while (len > 0 && (line[len - 1] == ' ' || line[len - 1] == '\r' || line[len - 1] == '\n')) {
        line[--len] = '\0';
    }
    if (len == 0) return;

    if (strcasecmp(line, "HELP") == 0) {
        printf("--- ESP32 Anchor Console Commands ---\n");
        printf("GET_CONFIG                    Output current configuration JSON\n");
        printf("GET_MAC                       Print hardware silicon MAC\n");
        printf("SET_ANCHOR=<ID>               Set Anchor Node ID\n");
        printf("SET_TAG=<MAC>                 Set Target Tag MAC\n");
        printf("SET_SSID=<SSID>               Set Wi-Fi SSID\n");
        printf("SET_PASS=<PASS>               Set Wi-Fi Password\n");
        printf("SET_WIFI=<SSID>,<PASS>        Set both SSID and Password\n");
        printf("SET_HOST=<IP>                 Set Host Laptop Receiver IP\n");
        printf("SET_PORT=<PORT>               Set UDP Port\n");
        printf("SAVE_CONFIG                   Commit settings to NVS Flash\n");
        printf("RECONNECT_WIFI                Reconnect to Wi-Fi\n");
        printf("REBOOT                        Reboot ESP32 hardware\n");
    } else if (strcasecmp(line, "GET_MAC") == 0) {
        printf("{\"status\":\"ok\",\"mac\":\"%s\"}\n", g_device_mac);
    } else if (strcasecmp(line, "GET_CONFIG") == 0) {
        printf("{\"status\":\"ok\",\"node\":\"%s\",\"mac\":\"%s\",\"tag\":\"%s\","
               "\"ssid\":\"%s\",\"host\":\"%s\",\"port\":%u,\"ip\":\"%s\"}\n",
               g_anchor_id, g_device_mac, g_target_mac, g_wifi_ssid, g_host_ip, g_udp_port, g_node_ip);
    } else if (strncasecmp(line, "SET_ANCHOR=", 11) == 0) {
        strncpy(g_anchor_id, line + 11, sizeof(g_anchor_id) - 1);
        printf("{\"status\":\"ok\",\"anchor\":\"%s\"}\n", g_anchor_id);
    } else if (strncasecmp(line, "SET_TAG=", 8) == 0) {
        strncpy(g_target_mac, line + 8, sizeof(g_target_mac) - 1);
        printf("{\"status\":\"ok\",\"tag\":\"%s\"}\n", g_target_mac);
    } else if (strncasecmp(line, "SET_SSID=", 9) == 0) {
        strncpy(g_wifi_ssid, line + 9, sizeof(g_wifi_ssid) - 1);
        printf("{\"status\":\"ok\",\"ssid\":\"%s\"}\n", g_wifi_ssid);
    } else if (strncasecmp(line, "SET_PASS=", 9) == 0) {
        strncpy(g_wifi_pass, line + 9, sizeof(g_wifi_pass) - 1);
        printf("{\"status\":\"ok\",\"pass\":\"SET\"}\n");
    } else if (strncasecmp(line, "SET_WIFI=", 9) == 0) {
        char *comma = strchr(line + 9, ',');
        if (comma) {
            *comma = '\0';
            strncpy(g_wifi_ssid, line + 9, sizeof(g_wifi_ssid) - 1);
            strncpy(g_wifi_pass, comma + 1, sizeof(g_wifi_pass) - 1);
            printf("{\"status\":\"ok\",\"ssid\":\"%s\",\"pass\":\"SET\"}\n", g_wifi_ssid);
        }
    } else if (strncasecmp(line, "SET_HOST=", 9) == 0) {
        strncpy(g_host_ip, line + 9, sizeof(g_host_ip) - 1);
        printf("{\"status\":\"ok\",\"host\":\"%s\"}\n", g_host_ip);
    } else if (strncasecmp(line, "SET_PORT=", 9) == 0) {
        g_udp_port = (uint16_t)atoi(line + 9);
        printf("{\"status\":\"ok\",\"port\":%u}\n", g_udp_port);
    } else if (strcasecmp(line, "SAVE_CONFIG") == 0) {
        save_configuration();
    } else if (strcasecmp(line, "RECONNECT_WIFI") == 0) {
        printf("{\"status\":\"ok\",\"message\":\"Reconnecting Wi-Fi...\"}\n");
        wifi_config_t wc = { 0 };
        strncpy((char *)wc.sta.ssid, g_wifi_ssid, sizeof(wc.sta.ssid) - 1);
        strncpy((char *)wc.sta.password, g_wifi_pass, sizeof(wc.sta.password) - 1);
        esp_wifi_disconnect();
        esp_wifi_set_config(WIFI_IF_STA, &wc);
        esp_wifi_connect();
    } else if (strcasecmp(line, "REBOOT") == 0) {
        printf("{\"status\":\"ok\",\"message\":\"Rebooting hardware...\"}\n");
        vTaskDelay(pdMS_TO_TICKS(100));
        esp_restart();
    }
}

static void uart_console_task(void *param) {
    uint8_t *data = (uint8_t *)malloc(UART_BUF_SIZE);
    char line_buf[256];
    int line_idx = 0;

    while (1) {
        int len = uart_read_bytes(UART_CONSOLE_PORT, data, UART_BUF_SIZE - 1, pdMS_TO_TICKS(50));
        for (int i = 0; i < len; i++) {
            char c = (char)data[i];
            if (c == '\n' || c == '\r') {
                if (line_idx > 0) {
                    line_buf[line_idx] = '\0';
                    process_serial_line(line_buf);
                    line_idx = 0;
                }
            } else if (line_idx < sizeof(line_buf) - 1) {
                line_buf[line_idx++] = c;
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// App Entrypoint
// ─────────────────────────────────────────────────────────────────────────────
void app_main(void) {
    // 1. Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Hardware GPIO & Silicon MAC
    gpio_reset_pin(STATUS_LED_GPIO);
    gpio_set_direction(STATUS_LED_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(STATUS_LED_GPIO, 0);

    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    snprintf(g_device_mac, sizeof(g_device_mac), "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    printf("\n--- ESP32 Autonomous Wireless Anchor Node Initializing ---\n");
    printf("[SYSTEM] Silicon Hardware MAC: %s\n", g_device_mac);

    // 3. Load Persistent Configuration from NVS
    load_configuration();

    // 4. Install UART Driver for Console Provisioning
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_CONSOLE_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_CONSOLE_PORT, &uart_config);
    xTaskCreate(uart_console_task, "uart_console", 4096, NULL, 10, NULL);

    // 5. Connect Wi-Fi Station
    wifi_init_sta();

    // 6. Spawn UDP Server Task
    xTaskCreate(udp_server_task, "udp_server", 4096, NULL, 5, NULL);

    // 7. Initialize NimBLE Stack
    ESP_ERROR_CHECK(nimble_port_init());
    ble_hs_cfg.sync_cb = on_ble_sync;
    nimble_port_freertos_init(ble_host_task);

    printf("[SYSTEM] Anchor Ready. Listening for serial commands, collector beacons, or target tags...\n");
}
