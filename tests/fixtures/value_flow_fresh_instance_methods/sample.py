class Base:
    def update(self, props):
        for key, value in props.items():
            func = getattr(self, f'set_{key}', None)
            if not callable(func):
                raise AttributeError(key)
            func(value)


class Box(Base):
    def __init__(self, **kwargs):
        self.update(kwargs)

    def set_allowed(self, value):
        self.allowed = value
