#ifndef WEBSOCKET_CLIENT_H
#define WEBSOCKET_CLIENT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/**
 * @brief WebSocket event types
 */
typedef enum {
    WS_EVENT_CONNECTED,
    WS_EVENT_DISCONNECTED,
    WS_EVENT_TEXT,
    WS_EVENT_BINARY,
    WS_EVENT_ERROR
} ws_event_type_t;

/**
 * @brief WebSocket event data
 */
typedef struct {
    ws_event_type_t type;
    const uint8_t *data;
    size_t len;
} ws_event_data_t;

/**
 * @brief WebSocket event callback
 */
typedef void (*ws_event_cb_t)(const ws_event_data_t *event);

/**
 * @brief Initialize WebSocket client
 * @param uri WebSocket server URI (e.g., ws://192.168.1.100:8765/)
 * @param cb Event callback function
 * @return true on success, false on failure
 */
bool websocket_client_init(const char *uri, ws_event_cb_t cb);

/**
 * @brief Connect to WebSocket server (blocking)
 * @param timeout_ms Connection timeout in milliseconds
 * @return true on success, false on failure
 */
bool websocket_client_connect(int timeout_ms);

/**
 * @brief Send binary data to server
 * @param data Data to send
 * @param len Data length
 * @return true on success, false on failure
 */
bool websocket_client_send_binary(const uint8_t *data, size_t len);

/**
 * @brief Send text message to server
 * @param text Text string to send
 * @return true on success, false on failure
 */
bool websocket_client_send_text(const char *text);

/**
 * @brief Check if WebSocket is connected
 * @return true if connected, false otherwise
 */
bool websocket_client_is_connected(void);

/**
 * @brief Disconnect from WebSocket server
 */
void websocket_client_disconnect(void);

/**
 * @brief Process WebSocket events (call from main loop)
 */
void websocket_client_process(void);

#endif // WEBSOCKET_CLIENT_H
