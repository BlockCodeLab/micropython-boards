include(boards/mpconfigboard_esp32s3_common.cmake)

if(NOT MICROPY_DIR)
  get_filename_component(MICROPY_DIR ${CMAKE_CURRENT_LIST_DIR}/../../../.. ABSOLUTE)
endif()

list(APPEND SDKCONFIG_DEFAULTS
  boards/sdkconfig.240mhz
  boards/sdkconfig.flash_qio_80m
  boards/sdkconfig.spiram_oct
  ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(C_MODULES_DIR ${MICROPY_DIR}/../cmodules)

set(USER_C_MODULES ${C_MODULES_DIR}/cmodules.esp32.cmake)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_DIR}/../modules/manifest.esp32.py)
