import gzip
import json

from Box2D import b2World


class LocalSink:
    def write(self, value):
        return value


def unconstrained_write(out, value):
    out.write(value)


def use_local_sink(sink):
    sink.write("local")


def use_json_decoder(decoder):
    decoder.decode("{}")


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


use_local_sink(LocalSink())
use_json_decoder(json.JSONDecoder())
close_polymorphic(open("plain.txt", "w"))
close_polymorphic(gzip.open("compressed.gz", "wb"))
invoke_forward()
Effector(World())
use_holder(Holder(Payload()))
use_holder_alias(Holder(Payload()))
build_body(PhysicsWrapper())
PhysicsOwner(PhysicsWrapper()).attach()
CalledTransformer().transfer(LocalSink())
