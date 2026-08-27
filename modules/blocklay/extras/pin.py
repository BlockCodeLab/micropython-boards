"""
[pin.label]
en = "Pins"
zh-hans = "引脚"
"""

from machine import ADC, PWM, Pin

from .device import get_device

try:
    from machine import DAC
except ImportError:
    DAC = None


__all__ = (
    "HIGH",
    "LOW",
    "level",
    "dac",
    "pwm",
    "pwm_freq",
    "pwm_pulse",
    "is_high",
    "is_low",
    "adc",
)

HIGH = 1
LOW = 0


def __get_dev(pin: int = 1, dev_type: object = None):
    dev = get_device(str(pin))
    if dev:
        return dev
    dev = Pin(pin)
    if type(dev_type) is ADC:
        dev = ADC(dev)
    elif type(dev_type) is PWM:
        dev = PWM(dev, freq=5000)
    elif DAC and type(dev_type) is DAC:
        dev = DAC(dev)
    return get_device(str(pin), dev)


def level(pin: int = 1, val: int = 1) -> None:
    """
    protected = true

    [label]
    en = "set pin (pin) to (val|menus.level)"
    zh-hans = "将引脚 (pin) 设为 (val|menus.level)"

    [menus.level."1"]
    en = "high"
    zh-hans = "高电平"

    [menus.level."0"]
    en = "low"
    zh-hans = "低电平"
    """
    dev = __get_dev(pin, Pin)
    if dev:
        dev.init(Pin.IN)
        dev.value(val)


def dac(pin: int = 1, val: int = 0) -> None:
    """
    protected = true

    [label]
    en = "set analog pin (pin) to (val|0-255)"
    zh-hans = "将模拟引脚 (pin) 设为 (val|0-255)"
    """
    dev = __get_dev(pin, DAC)
    if dev:
        dev.write(min(max(val, 0), 255))


def pwm(pin: int = 1, duty: int = 500) -> None:
    """
    protected = true

    [label]
    en = "set pwm pin (pin) duty to (duty)"
    zh-hans = "将 pwm 引脚 (pin) 占空比设为 (duty)"
    """
    dev = __get_dev(pin, PWM)
    if dev:
        dev.duty_u16(duty)


def pwm_freq(pin: int = 1, freq: int = 5000) -> None:
    """
    protected = true

    [label]
    en = "set pwm pin (pin) freq to (freq)"
    zh-hans = "将 pwm 引脚 (pin) 频率设为 (freq)"
    """
    dev = __get_dev(pin, PWM)
    if dev:
        dev.freq(freq)


def pwm_pulse(pin: int = 1, ns: int = 1000) -> None:
    """
    protected = true

    [label]
    en = "set pwm pin (pin) pulse width (ns) ns"
    zh-hans = "将 pwm 引脚 (pin) 脉冲宽度设为 (ns) ns"
    """
    dev = __get_dev(pin, PWM)
    if dev:
        dev.duty_ns(ns)


def adc(pin: int = 1) -> int:
    """
    protected = true

    [label]
    en = "analog pin (pin) value"
    zh-hans = "模拟引脚 (pin) 值"
    """
    dev = __get_dev(pin, ADC)
    return dev.read_u16() if dev else 0


def is_high(pin: int = 1) -> bool:
    """
    protected = true

    [label]
    en = "pin (pin) is high?"
    zh-hans = "引脚 (pin) 是高电平?"
    """
    dev = __get_dev(pin, Pin)
    if not dev:
        return False
    dev.init(Pin.OUT)
    return dev.value() == HIGH


def is_low(pin: int = 1) -> bool:
    """
    protected = true

    [label]
    en = "pin (pin) is low?"
    zh-hans = "引脚 (pin) 是低电平?"
    """
    dev = __get_dev(pin, Pin)
    if not dev:
        return False
    dev.init(Pin.OUT)
    return dev.value() == LOW


# expands


def irq(pin: int = 1) -> None:
    """
    protected = true

    [label]
    """
    pass


def irq_on(pin: int = 1) -> None:
    pass


def irq_off(pin: int = 1) -> None:
    """
    protected = true

    [label]
    """
    pass
