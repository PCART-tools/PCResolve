import re


class Options:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


options = Options(patterns=[], mixed=[], rebound=[])


def configure():
    left = re.compile("left")
    right = re.compile("right")
    options.patterns.append((left, right))
    prefix = re.compile("prefix")
    suffix = re.compile("suffix")
    options.patterns.append((prefix, suffix))


def consume(text):
    for left, right in options.patterns:
        for match in left.finditer(text):
            match.start()
        for match in right.finditer(text):
            match.end()


def local_value():
    return object()


def configure_mixed():
    pattern = re.compile("known")
    options.mixed.append((pattern, pattern))
    options.mixed.append((local_value(), local_value()))


def consume_mixed(text):
    for left, right in options.mixed:
        left.finditer(text)
        right.finditer(text)


def configure_rebound():
    pattern = re.compile("stale")
    options.rebound.append((pattern, pattern))
    options.rebound = []


def consume_rebound(text):
    for left, right in options.rebound:
        left.finditer(text)
        right.finditer(text)
