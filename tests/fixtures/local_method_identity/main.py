"""Regression fixture: local method call identity protection.

P0: Methods explicitly defined in project-local classes must be
classified as local regardless of what library APIs the method body
calls internally.

Contract:
- self.local_method()                       -> local
- module_instance.local_method()            -> local
- self.client.do() (where client is external) -> library
- local method return provenance preserved for downstream calls
"""

import json


class Client:
    """Project-local class wrapping json module."""
    def __init__(self):
        self.backend = json

    def do_load(self, s):
        """Local method that internally calls json.loads."""
        return self.backend.loads(s)

    def get_result(self):
        """Local method that returns a library call result."""
        return self.backend.dumps({"key": "value"})


class SubClient(Client):
    """Inherits from Client — do_load is inherited, not locally defined."""
    pass


# Module-level instance
client = Client()

# Inherited instance
sub = SubClient()


def use_module_instance():
    # client.do_load(...) → local (defined in Client class)
    client.do_load('{"a": 1}')

    # client.backend.loads(...) → library (backend is json module)
    client.backend.loads('{"b": 2}')

    # Local method returning library object
    result = client.get_result()
    # result is a json.dumps return → library provenance preserved


def use_constructor():
    # Direct constructor instantiation
    c = Client()
    c.do_load('{"x": 1}')
    c.backend.loads('{"y": 2}')

    # Inherited method (not locally defined) — out of scope
    sub.do_load('{"z": 3}')
