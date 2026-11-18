class Axis:
    def equals(self, other):
        return True


def getattr(obj, name):
    return Axis()


def shadowed_control(obj, name):
    return getattr(obj, name).equals(obj)
