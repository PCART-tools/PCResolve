import json


class Decode:
    def __call__(self, api):
        return api.loads('{}')


class Child(Decode):
    pass


class Alternate:
    def __call__(self, api):
        return api.dumps({})


class Holder:
    def __init__(self, callback):
        self.callback = callback


def forward(holder, api):
    return holder.callback(api)


def make():
    return Decode()


callback = Decode()
alias = callback
alias(json)
child = Child()
child(json)
other = Alternate()
other(json)
forward(Holder(callback), json)
generated = make()
generated(json)
Decode().__call__(json)
