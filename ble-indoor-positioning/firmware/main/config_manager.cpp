#include <string.h>
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "config_manager.h"

static const char *TAG = "CONFIG_MGR";

// Default settings as specified by the user
#define DEFAULT_ANCHOR_ID "A1"
#define DEFAULT_TARGET_MAC "52:06:26:03:01:DA"
#define DEFAULT_MODE MODE_NORMAL

anchor_config_t g_config;

extern "C" esp_err_t config_init(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS flash partition needs formatting...");
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    // Load configuration
    err = config_load(&g_config);
    if (err != ESP_OK) {
        ESP_LOGI(TAG, "No configuration found in NVS, applying defaults.");
        strncpy(g_config.anchor_id, DEFAULT_ANCHOR_ID, sizeof(g_config.anchor_id) - 1);
        strncpy(g_config.target_mac, DEFAULT_TARGET_MAC, sizeof(g_config.target_mac) - 1);
        g_config.mode = DEFAULT_MODE;
        
        // Save default config
        config_save(&g_config);
    } else {
        ESP_LOGI(TAG, "Configuration loaded: Anchor=%s, Tag=%s, Mode=%d",
                 g_config.anchor_id, g_config.target_mac, g_config.mode);
    }
    return ESP_OK;
}

extern "C" esp_err_t config_save(const anchor_config_t *cfg) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open("storage", NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        return err;
    }

    err = nvs_set_str(nvs_handle, "anchor_id", cfg->anchor_id);
    if (err != ESP_OK) goto save_err;

    err = nvs_set_str(nvs_handle, "target_mac", cfg->target_mac);
    if (err != ESP_OK) goto save_err;

    err = nvs_set_u8(nvs_handle, "mode", (uint8_t)cfg->mode);
    if (err != ESP_OK) goto save_err;

    err = nvs_commit(nvs_handle);
    if (err != ESP_OK) goto save_err;

    nvs_close(nvs_handle);
    ESP_LOGI(TAG, "Configuration saved to NVS: Anchor=%s, Tag=%s, Mode=%d",
             cfg->anchor_id, cfg->target_mac, cfg->mode);
    return ESP_OK;

save_err:
    ESP_LOGE(TAG, "Error writing config to NVS: %s", esp_err_to_name(err));
    nvs_close(nvs_handle);
    return err;
}

extern "C" esp_err_t config_load(anchor_config_t *cfg) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open("storage", NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) {
        return err;
    }

    size_t required_size = sizeof(cfg->anchor_id);
    err = nvs_get_str(nvs_handle, "anchor_id", cfg->anchor_id, &required_size);
    if (err != ESP_OK) goto load_err;

    required_size = sizeof(cfg->target_mac);
    err = nvs_get_str(nvs_handle, "target_mac", cfg->target_mac, &required_size);
    if (err != ESP_OK) goto load_err;

    uint8_t raw_mode = 0;
    err = nvs_get_u8(nvs_handle, "mode", &raw_mode);
    if (err != ESP_OK) goto load_err;
    cfg->mode = (anchor_mode_t)raw_mode;

    nvs_close(nvs_handle);
    return ESP_OK;

load_err:
    nvs_close(nvs_handle);
    return err;
}

// Global helper: check if MAC matches target
bool mac_matches_target(const uint8_t *bda) {
    char mac_str[18];
    mac_to_str(bda, mac_str);
    return (strcasecmp(mac_str, g_config.target_mac) == 0);
}

// Convert MAC address bytes to standard string format
void mac_to_str(const uint8_t *bda, char *str) {
    sprintf(str, "%02X:%02X:%02X:%02X:%02X:%02X",
            bda[0], bda[1], bda[2], bda[3], bda[4], bda[5]);
}

// Parse standard MAC address string format to bytes
bool str_to_mac(const char *str, uint8_t *bda) {
    int values[6];
    if (sscanf(str, "%x:%x:%x:%x:%x:%x",
               &values[0], &values[1], &values[2],
               &values[3], &values[4], &values[5]) == 6) {
        for (int i = 0; i < 6; ++i) {
            bda[i] = (uint8_t)values[i];
        }
        return true;
    }
    return false;
}
