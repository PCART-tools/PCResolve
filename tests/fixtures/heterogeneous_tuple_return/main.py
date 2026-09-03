from provider import make_mixed


def consume(left_value, right_value):
    left_value.reshape(1, -1)
    right_value.upper()


def forward(left_value, right_value):
    left_value.reshape(2, -1)
    right_value.lower()
    return left_value, right_value


left, right = make_mixed()
left.reshape(1, -1)
right.upper()
consume(left, right)
left, right = forward(left, right)
