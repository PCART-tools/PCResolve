class Connector:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.closed = False
        return kwargs


def unknown_mapping_write(mapping, value):
    mapping["feature"] = value
