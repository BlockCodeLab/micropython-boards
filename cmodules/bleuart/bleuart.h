#ifndef MICROPY_INCLUDED_BLEUART_H
#define MICROPY_INCLUDED_BLEUART_H

#include "py/ringbuf.h"
#include "py/runtime.h"

#define BLEUART_MAX_NAME_LEN 32

typedef struct _bleuart_obj_t {
  mp_obj_base_t base;
  mp_obj_t ble_obj;
  mp_obj_t callback;
  uint16_t tx_handle;
  uint16_t rx_handle;
  uint16_t conn_handle;
  ringbuf_t rx_buffer;
  uint8_t* buf_data;
  size_t buf_size;
  bool connected;
  char dev_name[BLEUART_MAX_NAME_LEN];
  size_t dev_name_len;
} bleuart_obj_t;

extern const mp_obj_type_t bleuart_type;

#endif  // MICROPY_INCLUDED_BLEUART_H
