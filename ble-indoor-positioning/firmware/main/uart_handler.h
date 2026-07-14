#ifndef UART_HANDLER_H
#define UART_HANDLER_H

#include "main.h"

// Initialize the UART subsystem and start the serial command receiver task
esp_err_t uart_handler_init(void);

// Send a plain text string over UART
void uart_send_string(const char *str);

// Thread-safe JSON logging of a raw packet
void uart_send_json_raw_packet(const raw_packet_t *pkt);

// Thread-safe JSON logging of a summarized observation window
void uart_send_json_observation(const char *json_str);

#endif // UART_HANDLER_H
