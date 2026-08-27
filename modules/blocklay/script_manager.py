import asyncio


class ScriptManager:
    def __init__(self, iterable=None):
        self._scripts = list(iterable) if iterable is not None else []

    def __getitem__(self, index):
        return self._scripts[index]

    def __setitem__(self, index, value):
        self._scripts[index] = value

    def __delitem__(self, index):
        del self._scripts[index]

    def __len__(self):
        return len(self._scripts)

    def __iter__(self):
        return iter(self._scripts)

    def __contains__(self, script):
        return script in self._scripts

    def append(self, script):
        self._scripts.append(script)

    def __repr__(self):
        return f"{len(self._scripts)} scripts"


class Program:
    _entrypoints = []
    _tasks = []

    def __init__(self, scripts):
        self.event_loop = asyncio.get_event_loop()
        self._scripts = scripts
        scripts.append(self)

    @property
    def scripts(self):
        return self._scripts

    def entry(self, condition=None):
        def entrypoint(script):
            if condition is None:
                self._entrypoints.append(script)
                return script

            async def wrapper():
                while condition:
                    if not await condition():
                        await script()
                    await asyncio.sleep_ms(5)

            self._entrypoints.append(wrapper)
            return wrapper

        return entrypoint

    def start(self):
        for entry in self._entrypoints:
            task = self.event_loop.create_task(entry())
            self._tasks.append(task)

    def stop(self):
        current_task = asyncio.current_task()
        for task in self._tasks:
            if task is not current_task:
                task.cancel()

    def receive(self, msg: str):
        pass

    def broadcast(self, msg: str):
        pass
