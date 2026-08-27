import asyncio
import time
from random import randint

from .script_manager import Program, ScriptManager

_script_manager = ScriptManager()


def blocklay():
    return Program(_script_manager)


def start():
    global start_time
    event_loop = asyncio.new_event_loop()
    start_time = time.ticks_ms()
    event_loop.run_forever()
    for script in _script_manager:
        script.start()


def stop():
    event_loop = asyncio.get_event_loop()
    event_loop.stop()
    for script in _script_manager:
        script.stop()
    event_loop.close()


def millisecs():
    return time.ticks_diff(time.ticks_ms(), start_time)
