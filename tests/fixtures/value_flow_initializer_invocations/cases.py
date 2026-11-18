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
    def fixed(this, /, **kwargs):
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


def construct_fixed(**kwargs):
    return Fixed(**kwargs)


def construct_inherited(**kwargs):
    return Inherited(**kwargs)


def construct_alias(**kwargs):
    return AliasOpen(**kwargs)


def construct_shadowed(**kwargs):
    return Shadowed(**kwargs)


def collision(**kwargs):
    return Open(self=1, **kwargs)


def posonly_keyword(**kwargs):
    return AliasOpen(this=1, **kwargs)


def argument_escape(**kwargs):
    return Open(dummy=external(Open), **kwargs)


class EscapedBase(Base):
    def __init__(self, **kwargs):
        alias = self
        external(alias)
        self.fixed(**kwargs)


class Escaped(EscapedBase):
    pass


def construct_escaped(**kwargs):
    return Escaped(**kwargs)


class Lookup(Base):
    def __getattribute__(self, name):
        if name == 'fixed':
            return lambda **kwargs: kwargs
        return object.__getattribute__(self, name)


def construct_lookup(**kwargs):
    return Lookup(**kwargs)
