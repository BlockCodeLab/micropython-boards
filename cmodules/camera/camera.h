#pragma once

// PIN Map (ESP-EYE)
#define CAM_PIN_PWDN -1  // power down is not used
#define CAM_PIN_RESET -1 // reset is not used
#define CAM_PIN_XCLK 4
#define CAM_PIN_SIOD 18 // SDA
#define CAM_PIN_SIOC 23 // SCL

#define CAM_PIN_D7 36
#define CAM_PIN_D6 37
#define CAM_PIN_D5 38
#define CAM_PIN_D4 39
#define CAM_PIN_D3 35
#define CAM_PIN_D2 14
#define CAM_PIN_D1 13
#define CAM_PIN_D0 34
#define CAM_PIN_VSYNC 5
#define CAM_PIN_HREF 27
#define CAM_PIN_PCLK 25

#define XCLK_FREQ_10MHz 10000000
#define XCLK_FREQ_20MHz 20000000

// White Balance
#define WB_NONE 0
#define WB_SUNNY 1
#define WB_CLOUDY 2
#define WB_OFFICE 3
#define WB_HOME 4

// Special Effect
#define EFFECT_NONE 0
#define EFFECT_NEG 1
#define EFFECT_BW 2
#define EFFECT_RED 3
#define EFFECT_GREEN 4
#define EFFECT_BLUE 5
#define EFFECT_RETRO 6
