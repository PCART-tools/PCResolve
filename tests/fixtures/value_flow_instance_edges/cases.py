class Base:
    def __init__(self, **kwargs):
        self.forward(**kwargs)

    def forward(self, **kwargs):
        self.fixed(**kwargs)

    def fixed(self, allowed=0):
        return allowed


class Open(Base):
    def fixed(self, **kwargs):
        return kwargs


class Fixed(Base):
    def fixed(self, supported=0):
        return supported


def construct_open(**kwargs):
    return Open(**kwargs)


def construct_fixed(**kwargs):
    return Fixed(**kwargs)


def relay(receiver, options):
    receiver.fixed(**options)


class HelperBase(Base):
    def __init__(self, **kwargs):
        relay(self, kwargs)


class HelperOpen(HelperBase):
    def fixed(self, **kwargs):
        return kwargs


class HelperFixed(HelperBase):
    def fixed(self, supported=0):
        return supported


class CollisionBase(Base):
    def __init__(self, **kwargs):
        self.forward(self=1, **kwargs)


class Collision(CollisionBase):
    pass


class PosOnlyBase(Base):
    def __init__(this, /, **kwargs):
        this.forward(this=1, **kwargs)

    def forward(this, /, **kwargs):
        this.fixed(**kwargs)


class PosOnly(PosOnlyBase):
    def fixed(this, /, **kwargs):
        return kwargs


class Escapes(Base):
    def __init__(self, **kwargs):
        external(self)
        self.forward(**kwargs)


class ArgumentEscape(Base):
    def __init__(self, **kwargs):
        self.forward(token=external(self), **kwargs)
