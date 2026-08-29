def split_parts(text):
    return text.split('|')


def clean(text):
    return text.strip()


def forward(text):
    return split_parts(clean(text))


def identity(value):
    return value


def sliced(value):
    return value[1:]


def mixed(flag):
    if flag:
        return 'abc'
    return 42


def recursive(value):
    return recursive(value)
