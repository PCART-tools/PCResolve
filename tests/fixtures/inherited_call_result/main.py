import json
import math


class GrandBase:
    def callback(self):
        return math.ceil


class Base(GrandBase):
    def callback(self):
        return json.loads


class Child(Base):
    pass


class Override(Child):
    def callback(self):
        return math.sqrt


child = Child()
callback = child.callback()
callback("{}")

override = Override()
override_callback = override.callback()
override_callback(4)
