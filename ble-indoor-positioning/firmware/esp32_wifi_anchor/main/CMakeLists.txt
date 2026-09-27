idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES bt esp_wifi esp_event esp_netif lwip nvs_flash esp_driver_gpio esp_driver_uart
)
