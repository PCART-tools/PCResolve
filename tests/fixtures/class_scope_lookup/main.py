"""Fixture: verify class-scope name resolution in PCResolve.

Python semantics:
- Class body CAN read its own earlier bindings (bare names).
- Method body CANNOT read enclosing class namespace (bare names).
- Nested class CANNOT read outer class namespace (bare names).
- Class comprehension CANNOT read class namespace.
"""

import requests


# -- Class body: own binding visible --
class C:
    factory = requests.Session
    class_body_lib = factory()          # expect: requests


# -- Class body: local callable shadows --
class D:
    open = lambda value: value
    class_body_local = open("x")        # expect: local


# -- Method body: bare builtin NOT shadowed by class method --
class E:
    def open(self, path):
        return path

    def run(self, path):
        method_bare_builtin = open(path)       # expect: python
        method_self_call = self.open(path)      # expect: local
        return method_bare_builtin, method_self_call


# -- Nested class: outer class namespace NOT visible --
class Outer:
    outer_factory = requests.Session

    class Inner:
        nested_result = outer_factory()   # expect: unknown


# -- Class comprehension: comprehension scope cannot read class namespace --
class F:
    comp_factory = requests.Session
    values = [comp_factory() for _ in range(1)]   # expect: unknown
