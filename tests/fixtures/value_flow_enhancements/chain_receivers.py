class Axis:
    def set_ticks(self, ticks):
        return ticks


class OtherAxis:
    def set_ticks(self, ticks):
        return ticks


class NoTicks:
    pass


class Owner:
    def __init__(self):
        self.axis = Axis()

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class Reassigned:
    def __init__(self):
        self.axis = Axis()

    def replace(self, replacement):
        self.axis = replacement

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class DifferentReturns:
    def __init__(self):
        self.axis = Axis()
        self.other_axis = OtherAxis()

    def axis_for_ticks(self, flag):
        if flag:
            return self.axis
        return self.other_axis

    def run(self, flag, ticks):
        return self.axis_for_ticks(flag).set_ticks(ticks)


class UnknownParameter:
    def __init__(self, axis):
        self.axis = axis

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class DynamicAttribute:
    def __init__(self):
        self.axis = Axis()

    def __getattribute__(self, name):
        return super().__getattribute__(name)

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class Bounded:
    def __init__(self, flag):
        self.axis = Axis() if flag else OtherAxis()

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class PartialTypes:
    def __init__(self, flag):
        self.axis = Axis() if flag else NoTicks()

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class PartialReturn:
    def __init__(self):
        self.axis = Axis()

    def axis_for_ticks(self, flag):
        if flag:
            return self.axis

    def run(self, flag, ticks):
        return self.axis_for_ticks(flag).set_ticks(ticks)


class SameFieldBranches:
    def __init__(self):
        self.axis = Axis()

    def axis_for_ticks(self, flag):
        if flag:
            return self.axis
        return self.axis

    def run(self, flag, ticks):
        return self.axis_for_ticks(flag).set_ticks(ticks)


class EarlyInitExit:
    def __init__(self, flag):
        if flag:
            return
        self.axis = Axis()

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)


class DynamicSetattr:
    def __init__(self):
        self.axis = Axis()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

    def axis_for_ticks(self):
        return self.axis

    def run(self, ticks):
        return self.axis_for_ticks().set_ticks(ticks)
