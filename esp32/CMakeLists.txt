cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    components/wifi
    components/audio
    components/websocket
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(deskbot)
