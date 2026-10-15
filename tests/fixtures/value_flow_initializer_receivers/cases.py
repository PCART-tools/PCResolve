class Base:
    def __init__(self, **kwargs):
        self.fixed(**kwargs)

    def fixed(self, allowed=0):
        return allowed


class Open(Base):
    def fixed(self, **kwargs):
        return kwargs


class Fixed(Base):
    def fixed(self, supported=0):
        return supported


class Inherited(Base):
    pass


class Shadowed(Base):
    fixed = None


class AliasBase:
    def __init__(this, /, **kwargs):
        alias = this
        alias.fixed(**kwargs)

    def fixed(this, allowed=0):
        return allowed


class AliasOpen(AliasBase):
    def fixed(this, **kwargs):
        return kwargs


class ChangedBase:
    def __init__(self, **kwargs):
        self.fixed = kwargs['callback']
        self.fixed(**kwargs)

    def fixed(self, allowed=0):
        return allowed


class Changed(ChangedBase):
    def fixed(self, **kwargs):
        return kwargs


def construct_open(**kwargs):
    return Open(**kwargs)
