def replacement(sequence):
    return ()


try:
    tuple = replacement
except Exception:
    pass


def run(*args):
    return tuple(args)
