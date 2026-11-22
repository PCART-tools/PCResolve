def p(x): return x is True
def q(y): return y is True
def entry(x, y):
    if p(x):
        y = x
    b = q(y)
    if b:
        return 1
    return 0
