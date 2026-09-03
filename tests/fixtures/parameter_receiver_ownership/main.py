import gzip
import json

from Box2D import b2World
from dispatch import CrossFileJsonDispatch


class LocalSink:
    def write(self, value):
        return value


def unconstrained_write(out, value):
    out.write(value)


def use_local_sink(sink):
    sink.write("local")


def use_json_decoder(decoder):
    decoder.decode("{}")


def use_python_text(text):
    text.strip()


def use_python_list(items):
    items.append("value")


def use_named_python_text(text):
    text.upper()


def use_named_python_list(items):
    items.extend(["value"])


def use_named_incompatible_protocol(items):
    items.upper()


def use_named_local_receiver(receiver):
    receiver.write("named local")


def incompatible_python_protocol(number):
    number.strip()


def forwarded_python_protocol(value):
    use_python_text(value)


def normalize_python_text(value):
    return value.strip()


def close_polymorphic(stream):
    stream.close()


def reassigned_parameter(value):
    value = LocalSink()
    value.write("reassigned")


def derived_parameter_item(batch):
    first, second = batch["first"], batch["second"]
    first.to("device")
    second.to("device")


def invoke_forward():
    forward_local(LocalSink())


def forward_local(sink):
    sink.write("forward")


class World:
    def add_bodies(self, bodies):
        return bodies


class Effector:
    def __init__(self, world):
        world.add_bodies([])


class Payload:
    def ping(self):
        return True


class Holder:
    def __init__(self, payload):
        self.payload = payload


class LocalItem:
    def ping(self):
        return True


class LocalItemGroup:
    def __init__(self, items):
        self.items = items

    def ping_all(self):
        return [item.ping() for item in self.items]


class MixedItemGroup:
    def __init__(self, items):
        self.items = items

    def use_all(self):
        return [item.decode("{}") for item in self.items]


class TextHolder:
    def __init__(self, title):
        self.title = title

    def normalize(self):
        self.title.strip()


class UncalledTextHolder:
    def __init__(self, caption):
        self.caption = caption

    def normalize(self):
        self.caption.strip()


class BranchingWriter:
    def __init__(self, compressed):
        self.file = self.open(compressed)

    def write(self):
        self.file.write("value")

    def open(self, compressed):
        if compressed:
            return gzip.open("compressed.gz", "wb")
        return open("plain.txt", "w")


class PhysicsWrapper:
    def __init__(self):
        self.world = b2World()


class PhysicsOwner:
    def __init__(self, wrapper):
        world = wrapper.world
        self.body = world.CreateDynamicBody()

    def attach(self):
        self.body.CreateFixture()


class UncalledTransformer:
    def transfer(self, decoder):
        decoder.decode("uncalled duplicate method")


class CalledTransformer:
    def transfer(self, sink):
        sink.write("called duplicate method")


def build_body(wrapper):
    world = wrapper.world
    body = world.CreateDynamicBody()
    body.CreateFixture()


def use_holder(holder):
    holder.payload.ping()


def use_holder_alias(holder):
    payload = holder.payload
    payload.ping()


class ScopedPythonItemGroup:
    def __init__(self, values):
        self.values = values

    def use_all(self):
        for entry in self.values:
            entry.strip()


class ScopedLocalItemGroup:
    def __init__(self, values):
        self.values = values

    def use_all(self):
        for entry in self.values:
            entry.ping()


class DispatchBase:
    def apply(self, value):
        return self._apply(value)


class JsonDispatch(DispatchBase):
    def _apply(self, value):
        value.raw_decode("{}")


class AmbiguousDispatchBase:
    def apply(self, value):
        return self._apply(value)


class AmbiguousJsonDispatch(AmbiguousDispatchBase):
    def _apply(self, value):
        value.scan_once("{}")


class AmbiguousLocalDispatch(AmbiguousDispatchBase):
    def _apply(self, value):
        value.scan_once()


class LocalScanner:
    def scan_once(self):
        return None


def pass_scoped_python_items():
    values = [" text "]
    ScopedPythonItemGroup(values).use_all()


def pass_scoped_local_items():
    values = [LocalItem()]
    ScopedLocalItemGroup(values).use_all()


use_local_sink(LocalSink())
use_json_decoder(json.JSONDecoder())
use_python_text(" literal ")
use_python_list([])
named_text = " named "
named_items = []
named_local = LocalSink()
use_named_python_text(named_text)
use_named_python_list(named_items)
use_named_incompatible_protocol(named_items)
use_named_local_receiver(named_local)
incompatible_python_protocol(1)
forwarded_python_protocol(" forwarded ")
normalized_text = normalize_python_text(" normalized ")
normalized_text.upper()
close_polymorphic(open("plain.txt", "w"))
close_polymorphic(gzip.open("compressed.gz", "wb"))
invoke_forward()
Effector(World())
use_holder(Holder(Payload()))
use_holder_alias(Holder(Payload()))
LocalItemGroup([LocalItem(), LocalItem()]).ping_all()
local_items = [LocalItem(), LocalItem()]
LocalItemGroup(local_items).ping_all()
MixedItemGroup([LocalItem(), json.JSONDecoder()]).use_all()
TextHolder(" title ").normalize()
BranchingWriter(True).write()
build_body(PhysicsWrapper())
PhysicsOwner(PhysicsWrapper()).attach()
CalledTransformer().transfer(LocalSink())
pass_scoped_python_items()
pass_scoped_local_items()
JsonDispatch().apply(json.JSONDecoder())
AmbiguousJsonDispatch().apply(json.JSONDecoder())
AmbiguousLocalDispatch().apply(LocalScanner())
CrossFileJsonDispatch().apply(json.JSONDecoder())
