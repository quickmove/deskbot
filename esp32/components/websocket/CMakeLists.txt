idf_component_register(SRCS "websocket_client.c"
                    INCLUDE_DIRS "."
                    REQUIRES esp_websocket_client esp_netif)
