#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs_flash.h"

#include "wifi.h"
#include "audio.h"
#include "websocket_client.h"

static const char *TAG = "main";

/* Configuration - hardcoded, modify as needed */
#define WIFI_SSID     "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"
#define WS_URI        "ws://192.168.1.100:8765/"

/* Audio buffer size */
#define AUDIO_BUFFER_SIZE  512

static uint8_t audio_buffer[AUDIO_BUFFER_SIZE];
static bool ws_connected = false;

/**
 * @brief WebSocket event handler
 */
static void on_websocket_event(const ws_event_data_t *event)
{
    switch (event->type) {
    case WS_EVENT_CONNECTED:
        ESP_LOGI(TAG, "WebSocket connected");
        ws_connected = true;
        break;

    case WS_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "WebSocket disconnected");
        ws_connected = false;
        break;

    case WS_EVENT_TEXT:
        ESP_LOGI(TAG, "Received text: %.*s", event->len, event->data);
        break;

    case WS_EVENT_BINARY:
        ESP_LOGD(TAG, "Received audio: %d bytes", event->len);
        audio_speaker_write(event->data, event->len);
        break;

    case WS_EVENT_ERROR:
        ESP_LOGE(TAG, "WebSocket error");
        break;
    }
}

/**
 * @brief Audio recording task
 */
static void audio_record_task(void *arg)
{
    ESP_LOGI(TAG, "Audio recording task started");

    while (1) {
        if (!ws_connected) {
            vTaskDelay(pdMS_TO_TICKS(500));
            continue;
        }

        int bytes_read = audio_mic_read(audio_buffer, AUDIO_BUFFER_SIZE);
        if (bytes_read > 0) {
            websocket_client_send_binary(audio_buffer, bytes_read);
        }
    }
}

/**
 * @brief Main application
 */
void app_main(void)
{
    ESP_LOGI(TAG, "DeskRobot ESP32 Firmware v1.0");
    ESP_LOGI(TAG, "================================");
    ESP_LOGI(TAG, "WiFi: %s", WIFI_SSID);
    ESP_LOGI(TAG, "Server: %s", WS_URI);

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* Connect to WiFi */
    ESP_LOGI(TAG, "Connecting to WiFi...");
    if (!wifi_connect(WIFI_SSID, WIFI_PASSWORD)) {
        ESP_LOGE(TAG, "WiFi connection failed!");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }
    ESP_LOGI(TAG, "WiFi connected");

    /* Initialize audio */
    if (!audio_init()) {
        ESP_LOGE(TAG, "Audio initialization failed!");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }
    ESP_LOGI(TAG, "Audio initialized");

    /* Initialize WebSocket */
    if (!websocket_client_init(WS_URI, on_websocket_event)) {
        ESP_LOGE(TAG, "WebSocket initialization failed!");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }

    /* Connect to WebSocket server */
    if (!websocket_client_connect(15000)) {
        ESP_LOGE(TAG, "WebSocket connection failed! Retrying...");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }

    /* Start audio recording task */
    xTaskCreate(audio_record_task, "audio_record", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "System ready! Streaming audio...");

    /* Main loop */
    while (1) {
        websocket_client_process();

        /* Check connection, reconnect if needed */
        if (!websocket_client_is_connected()) {
            ESP_LOGI(TAG, "Reconnecting to WebSocket...");
            if (!websocket_client_connect(10000)) {
                ESP_LOGE(TAG, "Reconnection failed");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
