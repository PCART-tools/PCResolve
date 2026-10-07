## @package rebound
#  Rebinding a module class prevents identity-based construction inference.


class Replaced:
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


Replaced = unknown_factory()


def select():
    return Replaced
