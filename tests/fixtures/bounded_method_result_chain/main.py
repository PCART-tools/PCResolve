import json
import numpy as np


class Forwarder:
    def expose(self, value):
        return value

    def choose(self, condition, left, right):
        if condition:
            return left
        return right


def consume_array(forwarder, value):
    array_value = forwarder.expose(value)
    array_value.reshape(1, -1)


def consume_text(forwarder, value):
    text_value = forwarder.expose(value)
    text_value.strip()


def consume_mixed(forwarder, condition, left, right):
    mixed_value = forwarder.choose(condition, left, right)
    mixed_value.copy()


consume_array(Forwarder(), np.array([1, 2]))
consume_text(Forwarder(), "value")
consume_mixed(
    Forwarder(), True, np.array([1, 2]), json.loads("[1, 2]"))
