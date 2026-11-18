from typing import overload


def fixed(allowed=0):
    return allowed


class OverloadedInit:
    @overload
    def __init__(self, allowed: int):
        ...

    @overload
    def __init__(self, allowed: str):
        ...

    def __init__(self, **kwargs):
        fixed(**kwargs)


class OverloadedNew:
    @overload
    def __new__(cls, allowed: int):
        ...

    @overload
    def __new__(cls, allowed: str):
        ...

    def __new__(cls, **kwargs):
        return fixed(**kwargs)


class EffectfulStub:
    @overload
    def __init__(self, allowed=external()):
        ...

    def __init__(self, **kwargs):
        fixed(**kwargs)


def call_new(**kwargs):
    return OverloadedNew(**kwargs)
