class Worker:
    def expand(self, value):
        return value


def expand_callback(worker, value):
    return worker.expand(value)


CALLBACKS = {"expand": expand_callback}


def dispatch(name, worker, value):
    return CALLBACKS[name](worker, value)


dispatch("expand", Worker(), "value")
