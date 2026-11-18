def fixed(allowed=0):
    return allowed


class Factory:
    def __new__(cls, **kwargs):
        if 'key' in cls.mapping(**kwargs):
            return 1
        return 0

    @classmethod
    def mapping(cls, **kwargs):
        fixed(**kwargs)
        opaque(cls)
        return unknown_mapping()


class NotFactory(Factory):
    def __new__(cls, **kwargs):
        if 'key' not in cls.mapping(**kwargs):
            return 1
        return 0


class BoolFactory(Factory):
    def __new__(cls, flag=False, **kwargs):
        if 'key' in cls.mapping(**kwargs) and flag:
            return 1
        return 0


class KeyFactory(Factory):
    def __new__(cls, **kwargs):
        if cls.key() in cls.mapping(**kwargs):
            return 1
        return 0

    @classmethod
    def key(cls):
        opaque(cls)
        return 'key'


def once(left, right):
    return left() in right()


def not_once(left, right):
    return left() not in right()
