#include "websocket_client.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_websocket_client.h"
#include "esp_event.h"

static const char *TAG = "websocket";

static esp_websocket_client_handle_t client = NULL;
static ws_event_cb_t event_callback = NULL;
static bool connected = false;
static bool want_connect = false;
static char ws_uri[256] = {0};

static void websocket_event_handler(void *handler_args, esp_event_base_t base,
                                    int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;

    switch (event_id) {
    case WEBSOCKET_EVENT_CONNECTED:
        ESP_LOGI(TAG, "WebSocket connected");
        connected = true;
        if (event_callback) {
            ws_event_data_t evt = {
                .type = WS_EVENT_CONNECTED,
                .data = NULL,
                .len = 0
            };
            event_callback(&evt);
        }
        break;

    case WEBSOCKET_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "WebSocket disconnected");
        connected = false;
        if (event_callback) {
            ws_event_data_t evt = {
                .type = WS_EVENT_DISCONNECTED,
                .data = NULL,
                .len = 0
            };
            event_callback(&evt);
        }
        break;

    case WEBSOCKET_EVENT_DATA:
        if (event_callback) {
            ws_event_data_t evt = {
                .type = (data->op_code == 0x1) ? WS_EVENT_TEXT : WS_EVENT_BINARY,
                .data = (const uint8_t *)data->data_ptr,
                .len = data->data_len
            };
            event_callback(&evt);
        }
        break;

    case WEBSOCKET_EVENT_ERROR:
        ESP_LOGE(TAG, "WebSocket error");
        if (event_callback) {
            ws_event_data_t evt = {
                .type = WS_EVENT_ERROR,
                .data = NULL,
                .len = 0
            };
            event_callback(&evt);
        }
        break;

    default:
        break;
    }
}

bool websocket_client_init(const char *uri, ws_event_cb_t cb)
{
    if (client != NULL) {
        ESP_LOGW(TAG, "WebSocket client already initialized");
        return true;
    }

    strncpy(ws_uri, uri, sizeof(ws_uri) - 1);
    event_callback = cb;

    esp_websocket_client_config_t config = {
        .uri = ws_uri,
        .task_stack = 4096,
    };

    client = esp_websocket_client_init(&config);
    if (client == NULL) {
        ESP_LOGE(TAG, "Failed to initialize WebSocket client");
        return false;
    }

    ESP_ERROR_CHECK(esp_websocket_register_events(client, WEBSOCKET_EVENT_ANY,
                                                   websocket_event_handler, NULL));

    want_connect = true;
    ESP_LOGI(TAG, "WebSocket client initialized: %s", uri);
    return true;
}

bool websocket_client_connect(int timeout_ms)
{
    if (client == NULL) {
        ESP_LOGE(TAG, "WebSocket client not initialized");
        return false;
    }

    if (connected) {
        return true;
    }

    ESP_LOGI(TAG, "Connecting to WebSocket server...");
    esp_err_t err = esp_websocket_client_start(client);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start WebSocket client: %s", esp_err_to_name(err));
        return false;
    }

    /* Wait for connection */
    int tick = 0;
    while (!connected && tick < timeout_ms / 100) {
        vTaskDelay(pdMS_TO_TICKS(100));
        tick++;
    }

    if (!connected) {
        ESP_LOGE(TAG, "WebSocket connection timeout");
        return false;
    }

    return true;
}

bool websocket_client_send_binary(const uint8_t *data, size_t len)
{
    if (client == NULL || !connected) {
        return false;
    }

    int ret = esp_websocket_client_send_bin(client, (const char *)data, len, portMAX_DELAY);
    return ret >= 0;
}

bool websocket_client_send_text(const char *text)
{
    if (client == NULL || !connected) {
        return false;
    }

    int ret = esp_websocket_client_send_text(client, text, strlen(text), portMAX_DELAY);
    return ret >= 0;
}

bool websocket_client_is_connected(void)
{
    return connected;
}

void websocket_client_disconnect(void)
{
    if (client != NULL) {
        esp_websocket_client_stop(client);
        connected = false;
        want_connect = false;
    }
}

void websocket_client_process(void)
{
    /* This function can be used for additional processing if needed */
    /* The actual event handling is done in the event handler */
}
