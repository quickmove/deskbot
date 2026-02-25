#ifndef AUDIO_H
#define AUDIO_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/**
 * @brief Initialize I2S for microphone (INMP441)
 * @return true on success, false on failure
 */
bool audio_init(void);

/**
 * @brief Read audio data from microphone (blocking)
 * @param buffer Buffer to store audio data
 * @param size Number of bytes to read
 * @return Number of bytes read, or -1 on error
 */
int audio_mic_read(uint8_t *buffer, size_t size);

/**
 * @brief Write audio data to speaker (blocking)
 * @param buffer Buffer containing audio data
 * @param size Number of bytes to write
 * @return Number of bytes written, or -1 on error
 */
int audio_speaker_write(const uint8_t *buffer, size_t size);

/**
 * @brief Check if audio is initialized
 * @return true if initialized, false otherwise
 */
bool audio_is_initialized(void);

#endif // AUDIO_H
