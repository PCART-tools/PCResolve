import json
from .helpers import identity


def entry(value):
    json.loads(value)
    return identity(value)
