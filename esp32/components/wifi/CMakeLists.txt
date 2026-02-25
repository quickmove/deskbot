idf_component_register(SRCS "wifi.c"
                    INCLUDE_DIRS "."
                    REQUIRES esp_wifi esp_netif
                    PRIV_REQUIRES nvs_flash)
