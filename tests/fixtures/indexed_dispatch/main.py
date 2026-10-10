import json
from helpers import decode as imported_alias


def decode(value):
    return json.loads(value)


def alternate(value):
    return json.dumps(value)


alias = decode


class Base:
    def method(self, value):
        return decode(value)


class Child(Base):
    pass


class Callable:
    def __init__(self, value):
        self.value = value

    def __call__(self, value):
        return alternate(value)


def nested(value):
    def inner(arg):
        return decode(arg)
    renamed = inner
    return renamed(value)


def selected(value, flag):
    if flag:
        callback = decode
    else:
        callback = alternate
    return callback(value)


def run(value):
    alias(value)
    imported_alias(value)
    nested(value)
    selected(value, True)
    child = Child()
    child.method(value)
    callback = Callable(value)
    return callback(value)
