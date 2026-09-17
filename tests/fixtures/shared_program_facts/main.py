import json


def decode(value, /, *, loader=json.loads):
    return loader(value)


def entry(value):
    return decode(value)


class Decoder:
    def parse(self, value, /, *, strict=True):
        return decode(value)


def repeated(value):
    decode(value); return decode(value)


callback = lambda value, /, *, loader=json.loads: loader(value)
