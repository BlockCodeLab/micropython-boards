#include "bleuart.h"

#include "extmod/modbluetooth.h"
#include "py/mperrno.h"
#include "py/mphal.h"

#define INVALID_CONN_HANDLE 0xFFFF

// ----------------------------------------------------------------------
// 常量定义
enum {
  _IRQ_CENTRAL_CONNECT = 1,
  _IRQ_CENTRAL_DISCONNECT = 2,
  _IRQ_GATTS_WRITE = 3,
};

static const uint16_t _FLAG_READ = 0x0002;
static const uint16_t _FLAG_WRITE_NO_RESPONSE = 0x0004;
static const uint16_t _FLAG_WRITE = 0x0008;
static const uint16_t _FLAG_NOTIFY = 0x0010;

// 标准（大端）字节序的 UUID
static const uint8_t _UART_SERVICE_UUID_BE[] = {0x6e, 0x40, 0x00, 0x01, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e};
static const uint8_t _UART_TX_CHAR_UUID_BE[] = {0x6e, 0x40, 0x00, 0x03, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e};
static const uint8_t _UART_RX_CHAR_UUID_BE[] = {0x6e, 0x40, 0x00, 0x02, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e};

// ----------------------------------------------------------------------
// 辅助函数：创建 UUID 对象（存储小端序）
static mp_obj_t create_uuid_from_be_bytes(const uint8_t* be_bytes) {
  mp_obj_bluetooth_uuid_t* self = mp_obj_malloc(mp_obj_bluetooth_uuid_t, &mp_type_bluetooth_uuid);
  self->type = 16;
  for (int i = 0; i < 16; i++) {
    self->data[i] = be_bytes[15 - i];
  }
  return MP_OBJ_FROM_PTR(self);
}

// 构造 advertising payload
static mp_obj_t build_advertising_payload(const char* name, size_t name_len) {
  uint8_t flags[] = {0x02, 0x01, 0x06};
  size_t name_adv_len = name_len + 2;
  uint8_t* name_adv = NULL;
  if (name && name_len > 0) {
    name_adv = m_new(uint8_t, name_adv_len);
    name_adv[0] = name_len + 1;
    name_adv[1] = 0x09;
    memcpy(name_adv + 2, name, name_len);
  }
  uint8_t uuid_le[16];
  for (int i = 0; i < 16; i++) {
    uuid_le[i] = _UART_SERVICE_UUID_BE[15 - i];
  }
  uint8_t uuid_adv[18];
  uuid_adv[0] = 17;
  uuid_adv[1] = 0x07;
  memcpy(uuid_adv + 2, uuid_le, 16);

  size_t total_len = sizeof(flags);
  if (name_adv) total_len += name_adv_len;
  total_len += sizeof(uuid_adv);
  if (total_len > 31 && name_adv) {
    m_del(uint8_t, name_adv, name_adv_len);
    name_adv = NULL;
    total_len = sizeof(flags) + sizeof(uuid_adv);
  }

  uint8_t* payload = m_new(uint8_t, total_len);
  size_t offset = 0;
  memcpy(payload + offset, flags, sizeof(flags));
  offset += sizeof(flags);
  if (name_adv) {
    memcpy(payload + offset, name_adv, name_adv_len);
    offset += name_adv_len;
    m_del(uint8_t, name_adv, name_adv_len);
  }
  memcpy(payload + offset, uuid_adv, sizeof(uuid_adv));

  mp_obj_t bytes_obj = mp_obj_new_bytes(payload, total_len);
  m_del(uint8_t, payload, total_len);
  return bytes_obj;
}

static void bleuart_advertise_start(const char* name, size_t name_len) {
  mp_obj_t payload = build_advertising_payload(name, name_len);
  mp_buffer_info_t adv_bufinfo;
  mp_get_buffer_raise(payload, &adv_bufinfo, MP_BUFFER_READ);
  int err = mp_bluetooth_gap_advertise_start(true, 500000, adv_bufinfo.buf, adv_bufinfo.len, NULL, 0);
  if (err != 0) mp_raise_OSError(err);
}

static void bleuart_advertise_stop(void) {
  mp_bluetooth_gap_advertise_stop();
}

// 事件处理函数（使用底层 C 读取）
static mp_obj_t bleuart_event_handler(mp_obj_t self_in, mp_obj_t event_in, mp_obj_t data_in) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(self_in);
  int event = mp_obj_get_int(event_in);

  switch (event) {
    case _IRQ_CENTRAL_CONNECT: {
      mp_obj_t conn_handle_obj = mp_obj_subscr(data_in, MP_OBJ_NEW_SMALL_INT(0), MP_OBJ_SENTINEL);
      self->conn_handle = mp_obj_get_int(conn_handle_obj);
      self->connected = true;
      break;
    }
    case _IRQ_CENTRAL_DISCONNECT: {
      self->conn_handle = INVALID_CONN_HANDLE;
      self->connected = false;
      bleuart_advertise_start(self->dev_name, self->dev_name_len);
      break;
    }
    case _IRQ_GATTS_WRITE: {
      mp_obj_t value_handle_obj = mp_obj_subscr(data_in, MP_OBJ_NEW_SMALL_INT(1), MP_OBJ_SENTINEL);
      uint16_t value_handle = mp_obj_get_int(value_handle_obj);
      if (value_handle == self->rx_handle) {
        // 直接调用底层 C 函数读取特征值
        const uint8_t* buf;
        size_t len;
        int err = mp_bluetooth_gatts_read(self->rx_handle, &buf, &len);
        if (err == 0 && len > 0) {
          for (size_t i = 0; i < len; i++) {
            ringbuf_put(&self->rx_buffer, buf[i]);
          }
          if (self->callback != mp_const_none) {
            mp_call_function_0(self->callback);
          }
        }
      }
      break;
    }
    default:
      break;
  }
  return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(bleuart_event_handler_obj, bleuart_event_handler);

// ----------------------------------------------------------------------
// 构造函数
static mp_obj_t bleuart_make_new(const mp_obj_type_t* type, size_t n_args, size_t n_kw, const mp_obj_t* args) {
  mp_arg_check_num(n_args, n_kw, 1, 3, true);
  mp_obj_t ble_obj = args[0];
  const char* name = NULL;
  size_t name_len = 0;
  size_t rxbuf_size = 256;
  if (n_args >= 2) {
    name = mp_obj_str_get_str(args[1]);
    name_len = strlen(name);
  } else {
    name = "mpy-uart";
    name_len = strlen(name);
  }
  if (n_args >= 3) {
    rxbuf_size = mp_obj_get_int(args[2]);
  }

  bleuart_obj_t* self = mp_obj_malloc(bleuart_obj_t, &bleuart_type);
  self->ble_obj = ble_obj;
  self->callback = mp_const_none;
  self->conn_handle = INVALID_CONN_HANDLE;
  self->connected = false;
  self->buf_size = rxbuf_size;

  if (name_len >= BLEUART_MAX_NAME_LEN) name_len = BLEUART_MAX_NAME_LEN - 1;
  memcpy(self->dev_name, name, name_len);
  self->dev_name[name_len] = '\0';
  self->dev_name_len = name_len;

  ringbuf_alloc(&self->rx_buffer, rxbuf_size);
  self->buf_data = self->rx_buffer.buf;

  int err = mp_bluetooth_init();
  if (err != 0) mp_raise_OSError(err);

  mp_obj_t service_uuid = create_uuid_from_be_bytes(_UART_SERVICE_UUID_BE);
  mp_obj_t tx_char_uuid = create_uuid_from_be_bytes(_UART_TX_CHAR_UUID_BE);
  mp_obj_t rx_char_uuid = create_uuid_from_be_bytes(_UART_RX_CHAR_UUID_BE);

  // 注册服务（仍使用 Python 方法，因为底层 API 太复杂）
  mp_obj_t services = mp_obj_new_list(0, NULL);
  mp_obj_t service = mp_obj_new_list(0, NULL);
  mp_obj_list_append(service, service_uuid);
  mp_obj_t chars = mp_obj_new_list(0, NULL);
  // TX: READ | NOTIFY
  mp_obj_t tx_char = mp_obj_new_list(0, NULL);
  mp_obj_list_append(tx_char, tx_char_uuid);
  mp_obj_list_append(tx_char, MP_OBJ_NEW_SMALL_INT(_FLAG_READ | _FLAG_NOTIFY));
  mp_obj_list_append(chars, tx_char);
  // RX: WRITE | WRITE_NO_RESPONSE
  mp_obj_t rx_char = mp_obj_new_list(0, NULL);
  mp_obj_list_append(rx_char, rx_char_uuid);
  mp_obj_list_append(rx_char, MP_OBJ_NEW_SMALL_INT(_FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE));
  mp_obj_list_append(chars, rx_char);
  mp_obj_list_append(service, chars);
  mp_obj_list_append(services, service);

  mp_obj_t dest[2];
  mp_load_method(ble_obj, MP_QSTR_gatts_register_services, dest);
  mp_obj_t* call_args = m_new(mp_obj_t, 2 + 1);
  call_args[0] = dest[0];
  call_args[1] = dest[1];
  call_args[2] = services;
  mp_obj_t handles_tuple = mp_call_method_n_kw(1, 0, call_args);
  m_del(mp_obj_t, call_args, 2 + 1);

  mp_obj_t handles = mp_obj_subscr(handles_tuple, MP_OBJ_NEW_SMALL_INT(0), MP_OBJ_SENTINEL);
  self->tx_handle = mp_obj_get_int(mp_obj_subscr(handles, MP_OBJ_NEW_SMALL_INT(0), MP_OBJ_SENTINEL));
  self->rx_handle = mp_obj_get_int(mp_obj_subscr(handles, MP_OBJ_NEW_SMALL_INT(1), MP_OBJ_SENTINEL));

  err = mp_bluetooth_gatts_set_buffer(self->rx_handle, rxbuf_size, true);
  if (err != 0) mp_raise_OSError(err);

  // 设置事件回调（Python 方法）
  mp_obj_t closed[1] = {MP_OBJ_FROM_PTR(self)};
  mp_obj_t callback_closure = mp_obj_new_closure(MP_OBJ_FROM_PTR(&bleuart_event_handler_obj), 1, closed);
  mp_obj_t irq_args[1] = {callback_closure};
  mp_load_method(ble_obj, MP_QSTR_irq, dest);
  call_args = m_new(mp_obj_t, 2 + 1);
  call_args[0] = dest[0];
  call_args[1] = dest[1];
  call_args[2] = irq_args[0];
  mp_call_method_n_kw(1, 0, call_args);
  m_del(mp_obj_t, call_args, 2 + 1);

  bleuart_advertise_start(self->dev_name, self->dev_name_len);

  return MP_OBJ_FROM_PTR(self);
}

// ----------------------------------------------------------------------
// 方法实现
static mp_obj_t bleuart_irq(mp_obj_t self_in, mp_obj_t handler) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(self_in);
  self->callback = handler;
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(bleuart_irq_obj, bleuart_irq);

static mp_obj_t bleuart_any(mp_obj_t self_in) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(self_in);
  return MP_OBJ_NEW_SMALL_INT(ringbuf_avail(&self->rx_buffer));
}
static MP_DEFINE_CONST_FUN_OBJ_1(bleuart_any_obj, bleuart_any);

static mp_obj_t bleuart_read(size_t n_args, const mp_obj_t* args) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(args[0]);
  size_t sz = ringbuf_avail(&self->rx_buffer);
  if (n_args > 1) sz = MIN(sz, mp_obj_get_int(args[1]));
  if (sz == 0) return mp_const_empty_bytes;
  vstr_t vstr;
  vstr_init_len(&vstr, sz);
  for (size_t i = 0; i < sz; i++) vstr.buf[i] = ringbuf_get(&self->rx_buffer);
  return mp_obj_new_bytes_from_vstr(&vstr);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(bleuart_read_obj, 1, 2, bleuart_read);

// 发送数据：直接调用底层 C 函数 mp_bluetooth_gatts_notify_indicate
static mp_obj_t bleuart_write(mp_obj_t self_in, mp_obj_t data_in) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(self_in);
  if (self->conn_handle == INVALID_CONN_HANDLE) {
    return MP_OBJ_NEW_SMALL_INT(0);
  }
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(data_in, &bufinfo, MP_BUFFER_READ);
  const uint8_t* src = bufinfo.buf;
  size_t len = bufinfo.len;
  const size_t chunk_size = 64;
  for (size_t i = 0; i < len; i += chunk_size) {
    size_t chunk_len = MIN(chunk_size, len - i);
    int err = mp_bluetooth_gatts_notify_indicate(self->conn_handle, self->tx_handle, MP_BLUETOOTH_GATTS_OP_NOTIFY, src + i, chunk_len);
    if (err != 0) mp_raise_OSError(err);
    mp_hal_delay_ms(10);
  }
  return MP_OBJ_NEW_SMALL_INT(len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(bleuart_write_obj, bleuart_write);

static mp_obj_t bleuart_close(mp_obj_t self_in) {
  bleuart_obj_t* self = MP_OBJ_TO_PTR(self_in);
  bleuart_advertise_stop();
  (void)mp_bluetooth_deinit();
  if (self->rx_buffer.buf) {
    m_del(uint8_t, self->rx_buffer.buf, self->rx_buffer.size);
    self->rx_buffer.buf = NULL;
  }
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(bleuart_close_obj, bleuart_close);

// ----------------------------------------------------------------------
// 类型定义与模块注册
static const mp_rom_map_elem_t bleuart_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_irq), MP_ROM_PTR(&bleuart_irq_obj)},
    {MP_ROM_QSTR(MP_QSTR_any), MP_ROM_PTR(&bleuart_any_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&bleuart_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&bleuart_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&bleuart_close_obj)},
};
static MP_DEFINE_CONST_DICT(bleuart_locals_dict, bleuart_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    bleuart_type, MP_QSTR_BLEUART, MP_TYPE_FLAG_NONE, make_new, bleuart_make_new, locals_dict, (mp_obj_dict_t*)&bleuart_locals_dict);

static const mp_rom_map_elem_t bleuart_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bleuart)},
    {MP_ROM_QSTR(MP_QSTR_BLEUART), MP_ROM_PTR(&bleuart_type)},
};
static MP_DEFINE_CONST_DICT(bleuart_module_globals, bleuart_module_globals_table);

const mp_obj_module_t bleuart_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&bleuart_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_bleuart, bleuart_module);
