class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed


class Direct(Base):
    pass


class Alias(Base):
    pass


class Keyword(Base):
    pass


class Local(Base):
    pass


class Explicit(Base):
    pass


class Unused(Base):
    pass


def mutate(other):
    if other is not None:
        other.fixed = staticmethod(lambda **kwargs: kwargs)


def touch_direct(receiver, other=None):
    receiver.cache = {}
    mutate(other)


touch_direct.__defaults__ = (Direct,)


def touch_alias(receiver, other=None):
    receiver.cache = {}
    mutate(other)


alias = touch_alias
alias.__defaults__ = (Alias,)


def touch_keyword(receiver, *, other=None):
    receiver.cache = {}
    mutate(other)


touch_keyword.__kwdefaults__['other'] = Keyword


def touch_local(receiver, other=None):
    receiver.cache = {}
    mutate(other)


def touch_explicit(receiver, other=None):
    receiver.cache = {}
    mutate(other)


def touch_unused(receiver, other=None):
    receiver.cache = {}


touch_unused.__defaults__ = (Unused,)


def direct(**kwargs):
    touch_direct(Direct)
    return Direct.fixed(**kwargs)


def aliased(**kwargs):
    touch_alias(Alias)
    return Alias.fixed(**kwargs)


def keyword(**kwargs):
    touch_keyword(Keyword)
    return Keyword.fixed(**kwargs)


def local(**kwargs):
    touch_local.__defaults__ = (Local,)
    touch_local(Local)
    return Local.fixed(**kwargs)


def explicit(**kwargs):
    touch_explicit(Explicit, None)
    return Explicit.fixed(**kwargs)


def unused(**kwargs):
    touch_unused(Unused)
    return Unused.fixed(**kwargs)
