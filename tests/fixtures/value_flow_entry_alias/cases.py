def fixed(allowed=0):
    return allowed


def implementation(**kwargs):
    return fixed(**kwargs)


public = implementation
del implementation


class Plain:
    def implementation(self, **kwargs):
        return fixed(**kwargs)

    first = second = implementation
    del implementation


class Rebound:
    def implementation(self, **kwargs):
        return fixed(**kwargs)

    alias = implementation
    alias = external


class Changed:
    def implementation(self, **kwargs):
        return fixed(**kwargs)

    alias = implementation


Changed.alias = external


if external:
    class Conditional:
        def implementation(self, **kwargs):
            return fixed(**kwargs)

        alias = implementation
        del implementation
