import json


class Worker:
    def expand(self, value):
        return value

    def dynamic_expand(self, value):
        return value

    def lambda_expand(self, value):
        return value

    def assigned_expand(self, value):
        return value

    def decode(self, value):
        return value


def expand_callback(worker, value):
    return worker.expand(value)


CALLBACKS = {"expand": expand_callback}


def dispatch(name, worker, value):
    return CALLBACKS[name](worker, value)


dispatch("expand", Worker(), "value")
selected_callback = CALLBACKS.get("expand")
selected_callback(Worker(), "selected")


def dynamic_callback(worker, value=""):
    return worker.dynamic_expand(value)


DYNAMIC_CALLBACKS = {
    "expand": dynamic_callback,
    "lambda": lambda worker, *values: worker.lambda_expand(values[0]),
}


def dynamic_dispatch(name, values, worker):
    return DYNAMIC_CALLBACKS[name](worker, *values)


class Driver:
    def run(self, values):
        return dynamic_dispatch("expand", values, self)


Driver().run(["value"])


assigned_callback = lambda worker, value: worker.assigned_expand(value)
assigned_callback(Worker(), "assigned")

ambiguous_lambda = lambda receiver: receiver.decode("{}")
ambiguous_lambda(Worker())
ambiguous_lambda(json.JSONDecoder())
