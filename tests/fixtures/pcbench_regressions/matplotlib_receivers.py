# Reduced from Matplotlib patches.py 3.5.0-3.7.0.
def interpd(function):
    return function


class Artist:
    def __init__(self):
        pass

    def update(self, properties):
        return properties

    def _internal_update(self, properties):
        return self.update(properties)


class Patch(Artist):
    def __init__(self, **kwargs):
        super().__init__()
        self._internal_update(kwargs)


class FancyArrowPatch(Patch):
    @interpd
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FancyBboxPatch(Patch):
    @interpd
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Shadow(Patch):
    @interpd
    def __init__(self, **kwargs):
        super().__init__()
        self.update({**kwargs})
