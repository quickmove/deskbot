#ifndef WIFI_H
#define WIFI_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Initialize WiFi station mode and connect to AP
 * @param ssid WiFi SSID
 * @param password WiFi password
 * @return true on success, false on failure
 */
bool wifi_connect(const char *ssid, const char *password);

/**
 * @brief Check if WiFi is connected
 * @return true if connected, false otherwise
 */
bool wifi_is_connected(void);

/**
 * @brief Disconnect from WiFi
 */
void wifi_disconnect(void);

#endif // WIFI_H
