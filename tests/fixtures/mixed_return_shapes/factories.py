def choose(flag):
    if flag:
        return {}
    return 42


def identity(value):
    return value


def forward(value):
    return identity(value)


def recursive(flag):
    if flag:
        return {}
    return recursive(flag)


class Factory:
    def dictionary(self):
        return {}

    def build(self, flag):
        if flag:
            return {}
        return None
