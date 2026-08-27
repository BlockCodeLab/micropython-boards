devices = {}


def get_device(id, dev=None):
    if id not in devices:
        return None
    if dev is not None:
        devices[id] = dev
    return devices[id]
