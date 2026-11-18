def normalize(text):
    if text.endswith('_missing'):
        raise ValueError(text)
    return text


class Document:
    def __call__(self, func):
        label = func.__qualname__
        try:
            func.__doc__ = normalize(label)
        except ValueError as error:
            raise KeyError(label) from error
        return func


def fixed(allowed=0):
    return allowed


@Document()
def entry(**kwargs):
    return fixed(**kwargs)
