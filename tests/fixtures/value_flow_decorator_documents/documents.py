class Base:
    def method(self):
        """Source documentation, not an executed method."""
        raise RuntimeError('must not be called by the analyzer')


def plain():
    """Plain documentation."""
    raise RuntimeError('must not be called by the analyzer')


def undocumented():
    pass


plain.__doc__ = unknown_document


class Meta(type):
    def __getattribute__(cls, name):
        return unknown_attribute


class CustomBase(metaclass=Meta):
    def method(self):
        """A custom class lookup cannot be treated as a builtin function read."""


class CustomChild(CustomBase):
    def method(self):
        """The inherited metaclass is still custom."""


def replacement(func):
    return unknown_callable


@replacement
def decorated():
    """Not a proof about the bound decorated object."""
