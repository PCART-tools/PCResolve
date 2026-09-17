import json
from bridge import convert
from helpers import identity


def entry(value):
    return convert(value)


def nested(value):
    def identity(item):
        return item
    return identity(value)


def repeated(value):
    first = identity(value); second = identity(first)
    return second


class Decoder:
    def identity(self, value):
        return value

    def parse(self, value):
        return self.identity(value)


def recursive(value):
    return recursive(value)


def unpack(**options):
    return options['value']


def forwarding(**options):
    return unpack(**options)


def consume(value):
    parser = forwarding(value=json.loads)
    return parser(value)
