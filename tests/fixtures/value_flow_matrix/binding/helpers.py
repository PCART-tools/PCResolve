## @package helpers
# Independent call-binding fixture helpers; never imported by the analyzer.


## @param data Value preserved in the return.
## @return The input value.
def identity(data):
    return data


## @param data Value preserved in the return.
## @param ignored Value deliberately discarded.
## @return The first input value.
def defaulted(data, ignored=None):
    return data


## @param first Positional-only value deliberately discarded.
## @param second Positional-only returned value.
## @return The second value.
def positional(first, second, /):
    return second


## @param left Keyword-only value deliberately discarded.
## @param right Keyword-only returned value.
## @return The right value.
def keywords(*, left, right):
    return right


## @param head Value deliberately discarded.
## @param rest Extra positional values; element one is returned.
## @return The second extra positional value.
def variadic(head, *rest):
    return rest[1]


## @param values Extra keyword values.
## @return The value associated with right.
def keyword_variadic(**values):
    return values['right']


## @param ignored Extra positional values deliberately discarded.
## @param result Independently bound keyword-only value.
## @return The keyword-only value.
def after_star(*ignored, result):
    return result
