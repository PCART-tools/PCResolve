import json


class Base:
    def read(self):
        return self.payload.loads('{}')


class Child(Base):
    def configure(self, payload):
        self.payload = payload


class Callable:
    def __call__(self, *apis):
        return apis[0].loads('{}')


def positional(*apis):
    return apis[0].loads('{}')


def keyword(**apis):
    return apis['decoder'].loads('{}')


child = Child()
child.configure(json)
child.read()
positional(json)
keyword(decoder=json)
callbacks = {'selected': positional}
callbacks['selected'](json)
callable_api = Callable()
callable_api(json)
