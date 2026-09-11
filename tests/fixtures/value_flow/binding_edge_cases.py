def positional_only(value, /):
    return value


def invalid_positional_keyword(x):
    return positional_only(value=x)


def capture_decorator(original):
    def replacement(value):
        return original(value)

    return replacement


@capture_decorator
def captured_replacement(value):
    return value


def call_captured_replacement(x):
    return captured_replacement(x)
