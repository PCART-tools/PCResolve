def p(x): return x is True
def q(y): return y is True
def entry(x, y):
    if p(x):
        y = False
    if q(y):
        return 1
    return 0
