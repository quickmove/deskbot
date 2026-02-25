#include "audio.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/i2s_std.h"
#include "driver/i2s_common.h"
#include "esp_err.h"

static const char *TAG = "audio";

/* I2S pin configuration for INMP441 microphone */
/* INMP441: WS=15, SCK=16, SD=4 */
#define I2S_MIC_WS_PIN    GPIO_NUM_15
#define I2S_MIC_SCK_PIN   GPIO_NUM_16
#define I2S_MIC_SD_PIN    GPIO_NUM_4

/* I2S pin configuration for MAX98357A speaker */
/* MAX98357A: DIN=22, BCLK=26, LRC=25 */
#define I2S_SPK_DIN_PIN   GPIO_NUM_22
#define I2S_SPK_BCLK_PIN  GPIO_NUM_26
#define I2S_SPK_LRC_PIN   GPIO_NUM_25

/* Audio settings */
#define SAMPLE_RATE       16000

static bool initialized = false;
static i2s_chan_handle_t rx_handle = NULL;
static i2s_chan_handle_t tx_handle = NULL;

bool audio_init(void)
{
    if (initialized) {
        return true;
    }

    ESP_LOGI(TAG, "Initializing I2S for INMP441 microphone...");

    /* Allocate I2S channel */
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num = 6;
    chan_cfg.dma_frame_num = 240;

    esp_err_t ret = i2s_new_channel(&chan_cfg, NULL, &rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to allocate I2S channel: %s", esp_err_to_name(ret));
        return false;
    }

    /* Configure I2S for INMP441 */
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_MSB_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .bclk = I2S_MIC_SCK_PIN,
            .ws = I2S_MIC_WS_PIN,
            .din = I2S_MIC_SD_PIN,
            .dout = I2S_GPIO_UNUSED,
            .invert_flags = {
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    /* Initialize I2S channel in standard mode */
    ret = i2s_channel_init_std_mode(rx_handle, &std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize I2S mode: %s", esp_err_to_name(ret));
        return false;
    }

    /* Enable I2S channel */
    ret = i2s_channel_enable(rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable I2S channel: %s", esp_err_to_name(ret));
        return false;
    }

    /* Initialize I2S for MAX98357A speaker (TX) */
    ESP_LOGI(TAG, "Initializing I2S for MAX98357A speaker...");

    /* Allocate TX channel */
    i2s_chan_config_t tx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    tx_chan_cfg.dma_desc_num = 6;
    tx_chan_cfg.dma_frame_num = 240;

    ret = i2s_new_channel(&tx_chan_cfg, &tx_handle, NULL);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to allocate I2S TX channel: %s", esp_err_to_name(ret));
        return false;
    }

    /* Configure I2S TX for MAX98357A */
    i2s_std_config_t tx_std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_MSB_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .bclk = I2S_SPK_BCLK_PIN,
            .ws = I2S_SPK_LRC_PIN,
            .din = I2S_GPIO_UNUSED,
            .dout = I2S_SPK_DIN_PIN,
            .invert_flags = {
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    ret = i2s_channel_init_std_mode(tx_handle, &tx_std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize I2S TX mode: %s", esp_err_to_name(ret));
        return false;
    }

    ret = i2s_channel_enable(tx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable I2S TX channel: %s", esp_err_to_name(ret));
        return false;
    }

    initialized = true;
    ESP_LOGI(TAG, "I2S microphone initialized successfully");
    ESP_LOGI(TAG, "MIC pins: WS=%d, BCK=%d, SD=%d", I2S_MIC_WS_PIN, I2S_MIC_SCK_PIN, I2S_MIC_SD_PIN);
    ESP_LOGI(TAG, "SPK pins: DIN=%d, BCLK=%d, LRC=%d", I2S_SPK_DIN_PIN, I2S_SPK_BCLK_PIN, I2S_SPK_LRC_PIN);

    return true;
}

int audio_mic_read(uint8_t *buffer, size_t size)
{
    if (!initialized || rx_handle == NULL) {
        return -1;
    }

    size_t bytes_read = 0;
    esp_err_t ret = i2s_channel_read(rx_handle, buffer, size, &bytes_read, portMAX_DELAY);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2S read error: %s", esp_err_to_name(ret));
        return -1;
    }

    return bytes_read;
}

int audio_speaker_write(const uint8_t *buffer, size_t size)
{
    if (!initialized || tx_handle == NULL) {
        return -1;
    }

    size_t bytes_written = 0;
    esp_err_t ret = i2s_channel_write(tx_handle, buffer, size, &bytes_written, portMAX_DELAY);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2S write error: %s", esp_err_to_name(ret));
        return -1;
    }

    return bytes_written;
}

bool audio_is_initialized(void)
{
    return initialized;
}
