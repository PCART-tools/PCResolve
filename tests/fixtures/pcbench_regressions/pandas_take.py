# Reduced from pandas 2.0.0 pandas/core/generic.py and core/frame.py.
def validate_take(args, kwargs):
    return kwargs


class PandasObject:
    pass


class OpsMixin:
    pass


class NDFrame(PandasObject):
    def take(self, indices, axis=0, **kwargs):
        validate_take((), kwargs)
        return indices


class DataFrame(OpsMixin, NDFrame):
    pass


def call_take(frame, indices):
    return frame.take(indices)
