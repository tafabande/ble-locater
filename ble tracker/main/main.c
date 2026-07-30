#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

#include "host/ble_gap.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"

static const char *TAG = "BLE_SCANNER";

#define ANCHOR_ID "ANCHOR_01"
#define BLINK_GPIO GPIO_NUM_2

// Target BLE Tag MAC: 52:06:26:03:01:DA
#define FILTER_TARGET_MAC 1
static const uint8_t TARGET_MAC[6] = {0xDA, 0x01, 0x03, 0x26, 0x06, 0x52};

static int g_led_state = 0;

static void start_scan(void);

static void host_task(void *param) {
  nimble_port_run();

  nimble_port_freertos_deinit();
}

static int scan_callback(struct ble_gap_event *event, void *arg) {

  if (event->type == BLE_GAP_EVENT_DISC) {
#if FILTER_TARGET_MAC
    if (memcmp(event->disc.addr.val, TARGET_MAC, 6) != 0) {
      return 0;
    }
#endif
    char name[128] = "Unknown";

    if (event->disc.length_data > 0) {
      struct ble_hs_adv_fields fields;
      int rc = ble_hs_adv_parse_fields(&fields, event->disc.data,
                                       event->disc.length_data);

      if (rc == 0) {
        if (fields.name != NULL && fields.name_len > 0) {
          int len = fields.name_len < (int)sizeof(name) - 1 ? fields.name_len : (int)sizeof(name) - 1;
          memcpy(name, fields.name, len);
          name[len] = '\0';
          // Replace commas or newlines with underscores to keep CSV formatting intact
          for (int i = 0; i < len; i++) {
            if (name[i] == ',' || name[i] == '\n' || name[i] == '\r') {
              name[i] = '_';
            }
          }
        } else if (fields.mfg_data != NULL && fields.mfg_data_len > 0) {
          int pos = 0;
          pos += snprintf(name + pos, sizeof(name) - pos, "MFG_");
          for (int i = 0; i < fields.mfg_data_len && pos < (int)sizeof(name) - 3; i++) {
            pos += snprintf(name + pos, sizeof(name) - pos, "%02X", fields.mfg_data[i]);
          }
        }
      }
    }

    // Flash / toggle onboard LED to signal active data packet collection
    g_led_state = !g_led_state;
    gpio_set_level(BLINK_GPIO, g_led_state);

    printf("%lu,%s,%02X:%02X:%02X:%02X:%02X:%02X,%d,%s\n",
           (unsigned long)esp_log_timestamp(),
           ANCHOR_ID,
           event->disc.addr.val[5], event->disc.addr.val[4], event->disc.addr.val[3],
           event->disc.addr.val[2], event->disc.addr.val[1], event->disc.addr.val[0],
           event->disc.rssi,
           name);
  } else if (event->type == BLE_GAP_EVENT_DISC_COMPLETE) {
    ESP_LOGI(TAG, "Discovery complete; restarting scan...");
    start_scan();
  }

  return 0;
}

static void start_scan(void) {
  uint8_t own_addr_type;
  int rc = ble_hs_id_infer_auto(0, &own_addr_type);
  if (rc != 0) {
    ESP_LOGE(TAG, "Error inferring own address type; rc=%d", rc);
    return;
  }

  // Print the CSV header for dataset capture
  printf("timestamp,anchor,mac,rssi,name\n");

  struct ble_gap_disc_params params = {
      .itvl = 0x30,
      .window = 0x30,
      .filter_duplicates = 0,
      .passive = 1
  };

  rc = ble_gap_disc(own_addr_type, BLE_HS_FOREVER, &params, scan_callback, NULL);

  if (rc != 0) {
    ESP_LOGE(TAG, "Scan failed: %d", rc);
  }
}

static void ble_on_sync(void) {
  ESP_LOGI(TAG, "Anchor ID: %s", ANCHOR_ID);
  ESP_LOGI(TAG, "BLE Synced");
  start_scan();
}

void app_main(void) {

  // Configure Onboard Status LED (GPIO 2)
  gpio_reset_pin(BLINK_GPIO);
  gpio_set_direction(BLINK_GPIO, GPIO_MODE_OUTPUT);
  gpio_set_level(BLINK_GPIO, 0); // Off during initialization / standby

  ESP_ERROR_CHECK(nvs_flash_init());

  ESP_ERROR_CHECK(nimble_port_init());

  ble_svc_gap_init();

  ble_svc_gap_device_name_set("ANCHOR_01");

  ble_hs_cfg.sync_cb = ble_on_sync;

  nimble_port_freertos_init(host_task);
}