def p(x): return x is True
def q(y): return y is True
def entry(x, y):
    a = p(x)
    if a:
        if not p(y):
            return 2
    if q(y):
        return 1
    return 0
