## @package custom_descriptors
#  A source class with a builtin descriptor name is a custom decorator.

from provider import External


def replacement():
    return None


class classmethod:
    def __new__(cls, function):
        return replacement


class staticmethod:
    def __new__(cls, function):
        return replacement


class ClassSelected:
    @classmethod
    def choose(cls):
        return External


class StaticSelected:
    @staticmethod
    def choose():
        return External


def select_class():
    return ClassSelected.choose()


def select_static():
    return StaticSelected.choose()
