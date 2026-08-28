import json
import multiprocessing as mp


def local_handler(value):
    return value


class HandlerFactory:
    def imported_handler(self, _):
        return json.loads

    def mixed_handler(self, enabled):
        if enabled:
            return json.loads
        return local_handler

    def run(self):
        pool = mp.Pool(1)
        self.handlers = pool.map(self.imported_handler, [True])
        self.handlers[0]("{}")

        self.mixed = pool.map(self.mixed_handler, [True, False])
        self.mixed[0]("{}")

        self.handlers = [local_handler]
        self.handlers[0]("value")


factory = HandlerFactory()
factory.run()
