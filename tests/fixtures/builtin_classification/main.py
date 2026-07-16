"""Regression fixture: builtin function and container method classification.

P0: bare builtin calls like getattr()/hasattr()/isinstance() must be
    classified as python, not traced through argument provenance.
P1: builtin container methods like list.append()/dict.get() must be
    classified as python when the receiver variable was assigned from
    a known container literal or constructor AT MODULE LEVEL.
    Function-local containers doing internal data-structure building
    should stay local (1.0.5 container fix over-reach correction).
    Local class methods with the same name (e.g. Bag().get()) remain local.
"""

import json

# ---------------------------------------------------------------------------
# P0: Builtin functions — should be python / python
# ---------------------------------------------------------------------------

value = getattr(json, "loads", None)
flag = hasattr(json, "loads")
check = isinstance(value, type(None))


# ---------------------------------------------------------------------------
# P1: Container methods on known MODULE-LEVEL container receivers → python
# ---------------------------------------------------------------------------

# list literal
items = []
# dict literal
mapping = {}
# set literal
vals = set()
# list() constructor
xs = list()
# dict() constructor
d_ctor = dict()
# list comprehension
comprehension_list = [x for x in range(3)]
# str literal
name = "hello"
# tuple literal
t = (1, 2, 3)
# str from constructor
s_ctor = str(42)

# Flask-style dict-for-error-messages (module-level)
error_messages = {}


def use_containers():
    items.append(1)
    items.extend([2, 3])
    idx = items.index(2)
    mapping["a"] = 1
    v = mapping.get("a", 0)
    vals.add(4)
    return items


def use_list_constructor():
    xs.append(10)
    xs.insert(0, 5)
    xs.pop()
    return xs


def use_dict_constructor():
    v = d_ctor.get("k", 0)
    return v


comprehension_list.append(4)


def use_str_methods():
    name.upper()
    name.replace("h", "H")
    name.startswith("h")
    name.isalpha()


def use_tuple_methods():
    t.count(1)
    t.index(2)


def use_str_constructor():
    return s_ctor.lower()


# Flask-style dict.get use case
def use_dict_get():
    v = error_messages.get(404, "Not Found")
    return v


# ---------------------------------------------------------------------------
# P1: Function-local builtin containers retain Python method ownership
# ---------------------------------------------------------------------------

# Parameter-sourced container (function-local)
def append_from_param(src):
    buf = []
    for x in src:
        buf.append(x)
    return buf


# Local class methods — should stay local / local
class Bag:
    def get(self):
        return 42

    def append(self, x):
        pass

    def pop(self):
        pass


def use_bag():
    b = Bag()
    val = b.get()
    b.append(1)
    b.pop()
    return val


# set literal methods (function-local)
def use_set_literal():
    s = set()
    s.add(1)
    s.discard(1)
    s.pop()
    return s


# Re-binding: container then local class — should clear container kind
def use_rebind():
    x = []
    x.append(0)   # python (list.append)

    x = Bag()
    x.append(1)   # local (not python!)


# Unknown parameter — should NOT be classified as python
def use_unknown_param(obj):
    obj.get("x")
    obj.append(1)
    obj.pop()


# ---------------------------------------------------------------------------
# P1+: defaultdict(list) item kind tracking
# ---------------------------------------------------------------------------
from collections import defaultdict

# Module-level defaultdict for item-kind tracking
d = defaultdict(list)
d2 = defaultdict(dict)


def use_defaultdict_list():
    d["x"].append(1)
    d["y"].append(2)
    return d


def use_defaultdict_dict():
    v = d2["x"].get("a", 0)
    return v


# Unknown factory (variable) — should NOT be forced to python
factory = list


def use_unknown_factory():
    d3 = defaultdict(factory)
    d3["x"].append(1)  # should NOT be forced python


# defaultdict with local class — should stay local
def use_defaultdict_bag():
    d4 = defaultdict(Bag)
    d4["x"].append(1)  # should be local, not python


# Re-binding: defaultdict then local class — should clear item kind
def use_defaultdict_rebind():
    d_rebind = defaultdict(list)
    d_rebind["a"].append(1)  # python (defaultdict produces list values)

    d_rebind = Bag()
    d_rebind.append(2)       # local (not python!)
