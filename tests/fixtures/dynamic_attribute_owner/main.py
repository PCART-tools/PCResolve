import json


class Axis:
    def equals(self, other):
        return True


class Frame:
    def dynamic_axis(self, name):
        return getattr(self, name)

    def local_axis(self, name):
        return Axis()

    def forwarded_axis(self, name):
        return self.dynamic_axis(name)

    def check(self, other, name):
        return all([self.dynamic_axis(name).equals(other),
                    self.local_axis(name).equals(other),
                    self.forwarded_axis(name).equals(other)])


def controls(value):
    return json.loads(value), [1].copy()


def invoke_dynamic(obj, name):
    return getattr(obj, name)()


def invoke_indirect(obj, name):
    selected = getattr(obj, name)
    selected()
    selected.equals(obj)
