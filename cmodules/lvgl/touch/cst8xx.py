from time import sleep_ms

import lvgl as lv
from machine import Pin

from micropython import const

_CST816S_ID = const(0xB4)
_CST816T_ID = const(0xB5)
_CST816D_ID = const(0xB6)
_CST820_ID = const(0xB7)
_CST826_ID = const(0x11)

_REG_GESTURE_ID = const(0x01)
_REG_FINGER_NUM = const(0x02)  # Number of fingers currently touching the screen
_REG_TOUCHDATA = const(0x03)  # 4 bytes:  X[11:8], X[7:0], Y[11:8], Y[7:0]
_REG_CHIP_ID = const(0xA7)
# _REG_PROJ_ID = const(0xA8)
# _REG_FW_VERSION = const(0xA9)
# _REG_FACTORY_ID = const(0xAA)
_REG_SLEEP_MODE = const(0xE5)
_REG_LONG_PRESS_TICK = const(0xEB)
_REG_MOTION_MASK = const(0xEC)
_REG_IRQ_CTL = const(0xFA)
_REG_DIS_AUTOSLEEP = const(0xFE)

MOTION_MASK_CONTINUOUS_LEFT_RIGHT = const(0b100)
MOTION_MASK_CONTINUOUS_UP_DOWN = const(0b010)
MOTION_MASK_DOUBLE_CLICK = const(0b001)

IRQ_EN_TOUCH = const(0x40)
IRQ_EN_CHANGE = const(0x20)
IRQ_EN_MOTION = const(0x10)
IRQ_EN_LONGPRESS = const(0x01)

CST8XX_PORTRAIT = const(0)
CST8XX_LANDSCAPE = const(1)
CST8XX_INV_PORTRAIT = const(2)
CST8XX_INV_LANDSCAPE = const(3)


class CST8xx_hw:
    def __init__(
        self,
        bus,
        address=0x15,
        rst_pin=None,
        irq_pin=None,
        irq_handler=lambda pin: None,
        irq_en=0x00,
        motion_mask=0b000,
    ):
        self._bus = bus
        self._address = address
        self.rst = Pin(rst_pin, Pin.OUT) if isinstance(rst_pin, int) else rst_pin
        self.reset()
        if self._read(_REG_CHIP_ID)[0] not in (
            _CST816S_ID,
            _CST816T_ID,
            _CST816D_ID,
            _CST820_ID,
            _CST826_ID,
        ):
            raise ValueError("Error:  CST8xx not detected.")
        self.disable_autosleep()

        self.irq = (
            Pin(irq_pin, Pin.IN, Pin.PULL_UP) if isinstance(irq_pin, int) else irq_pin
        )
        if self.irq:
            self.irq.irq(trigger=Pin.IRQ_FALLING, handler=irq_handler)
            self.set_irq_ctl(irq_en, motion_mask)

    def touched(self):
        return self._read(_REG_FINGER_NUM)[0]

    def get_point(self):
        if self.touched() != 1:
            return None
        xy_data = self._read(_REG_TOUCHDATA, 4)
        x = ((xy_data[0] & 0x0F) << 8) + xy_data[1]
        y = ((xy_data[2] & 0x0F) << 8) + xy_data[3]
        return x, y

    def get_gestures(self):
        if not self.touched():
            return None
        return self._read(_REG_GESTURE_ID)[0]

    def get_points(self):
        raise NotImplementedError("get_points() not implemented (yet)")

    def reset(self):
        if self.rst:
            self.rst(0)
            sleep_ms(1)
            self.rst(1)
            sleep_ms(50)

    def disable_autosleep(self, val=0x01):
        self._write(_REG_DIS_AUTOSLEEP, val)

    def set_irq_ctl(self, irq_en, motion_mask=0b000):
        self._write(_REG_IRQ_CTL, irq_en)
        self._write(_REG_MOTION_MASK, motion_mask)

    def set_long_press_tick(self, val):
        self._write(_REG_LONG_PRESS_TICK, val)

    def set_sleep_mode(self, val):
        self._write(_REG_SLEEP_MODE, val)

    def _read(self, reg, length=1):
        return self._bus.readfrom_mem(self._address, int(reg), length)

    def _write(self, reg, val):
        self._bus.writeto_mem(self._address, int(reg), bytes([int(val)]))


class CST8xx(CST8xx_hw):
    PORTRAIT = const(0)
    LANDSCAPE = const(1)
    INV_PORTRAIT = const(2)
    INV_LANDSCAPE = const(3)

    def __init__(self, res, rot=PORTRAIT, **kw):
        super().__init__(**kw)
        self.width, self.height = res

        if not lv.is_initialized():
            lv.init()
        self.rot = rot
        self.point = lv.point_t({"x": 0, "y": 0})
        self.points = [lv.point_t({"x": 0, "y": 0}), lv.point_t({"x": 0, "y": 0})]
        self.state = lv.INDEV_STATE.RELEASED

        self.indev_drv = lv.indev_create()
        self.indev_drv.set_type(lv.INDEV_TYPE.POINTER)
        self.indev_drv.set_read_cb(self.indev_drv_read_cb)

    def indev_drv_read_cb(self, indev_drv, data):
        pos = self.get_point()
        data.point = {
            "x": pos[0] if pos else 0,
            "y": pos[1] if pos else 0,
        }
        data.state = (
            lv.INDEV_STATE.PRESSED if self.touched() else lv.INDEV_STATE.RELEASED
        )
