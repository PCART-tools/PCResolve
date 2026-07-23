def reshape_once(value):
    return value.reshape(1, -1)


def reshape_twice(value):
    return reshape_once(value)
