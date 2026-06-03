import io
import os

import bluetooth

try:
    from bleuart import BLEUART
except ImportError:
    from .bleuart_peripheral import BLEUART

__all__ = ("start", "stop", "BLEUART")

_MP_STREAM_POLL = const(3)
_MP_STREAM_POLL_RD = const(0x0001)

# 全局变量，用于跟踪当前活动的 BLE REPL 实例
_current_uart = None
_current_stream = None


class BLEUARTStream(io.IOBase):
    def __init__(self, uart):
        self._uart = uart
        self._uart.irq(self._on_rx)

    def _on_rx(self):
        # 对于某些平台（ESP32）需要主动通知 dupterm 有新数据
        if hasattr(os, "dupterm_notify"):
            os.dupterm_notify(None)

    def readinto(self, buf):
        # 非阻塞：有数据就填充，否则返回 None
        if self._uart.any():
            n = min(len(buf), self._uart.any())
            data = self._uart.read(n)
            buf[:n] = data
            return n
        return None

    def write(self, data):
        # dupterm 要求 write 必须返回写入字节数
        self._uart.write(data)
        return len(data)

    def ioctl(self, op, arg):
        if op == _MP_STREAM_POLL:
            if self._uart.any():
                return _MP_STREAM_POLL_RD
        return 0


def start(name=None):
    """
    启动 BLE REPL 服务。
    name: 广播时显示的设备名（默认为 "repl"）
    返回 BLEUART 实例。
    """
    global _current_uart, _current_stream

    # 如果已有活动的 BLE REPL，先停止它
    if _current_uart is not None:
        stop()

    ble = bluetooth.BLE()
    if name is None:
        name = "repl"
    uart = BLEUART(ble, name=name)
    stream = BLEUARTStream(uart)
    os.dupterm(stream)

    _current_uart = uart
    _current_stream = stream
    return uart


def stop():
    """
    停止当前 BLE REPL 服务。
    移除 dupterm，关闭蓝牙连接，并停止广播。
    """
    global _current_uart, _current_stream

    if _current_uart is None:
        return  # 没有活动实例，无需操作

    # 移除 dupterm，恢复标准 REPL
    try:
        os.dupterm(None)
    except Exception:
        pass

    # 关闭 BLE UART 服务（会断开连接、停止广播）
    try:
        _current_uart.close()
    except Exception:
        pass

    _current_uart = None
    _current_stream = None
