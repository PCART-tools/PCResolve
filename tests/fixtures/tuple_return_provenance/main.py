from provider import make_arrays


def use_arrays():
    left, right = make_arrays()
    left_view = left.reshape(1, -1)
    right.reshape(1, -1)
    left_view.reshape(2, 1)
