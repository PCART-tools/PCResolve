def pop_last(x, y):
    values = [x, y]
    return values.pop()


def pop_negative(x, y, z):
    values = [x, y, z]
    return values.pop(-2)


def pop_out_of_range(x):
    values = [x]
    return values.pop(3)
