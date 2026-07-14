#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include "main.h"

#ifdef __cplusplus
extern "C" {
#endif

// Initialize configuration subsystem and load settings from NVS
esp_err_t config_init(void);

// Save current settings to NVS
esp_err_t config_save(const anchor_config_t *cfg);

// Load settings from NVS
esp_err_t config_load(anchor_config_t *cfg);

#ifdef __cplusplus
}
#endif

#endif // CONFIG_MANAGER_H
