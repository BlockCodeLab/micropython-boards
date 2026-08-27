import lvgl as lv
from cst8xx import CST8xx
from machine import I2C, SPI, Pin
from st7789 import ST7789

disp_spi = SPI(
    1,
    baudrate=80_000_000,
    sck=Pin(40, Pin.OUT),
    mosi=Pin(45, Pin.OUT),
    miso=Pin(46, Pin.IN),
)

lv.init()

lcd = ST7789(
    spi=disp_spi,
    res=(240, 320),
    rot=ST7789.LANDSCAPE,
    rst=39,
    dc=41,
    cs=42,
    bl=5,
    factor=8,
)
lcd.set_backlight(80)

touch_i2c = I2C(1, scl=Pin(3), sda=Pin(1), freq=400000)
touch = CST8xx(
    bus=touch_i2c,
    res=(240, 320),
    address=0x1A,
    rst_pin=Pin(2),
    irq_pin=Pin(4),
)

scr = lv.obj()
btn = lv.button(scr)
lbl = lv.label(btn)
lbl.set_text("Press me!")
btn.center()
btn.add_event(lambda event: print("Button clicked!"), lv.EVENT.CLICKED, None)
lv.screen_load(scr)
