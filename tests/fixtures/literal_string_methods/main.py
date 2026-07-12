"""Regression fixture: literal string and bytes method calls.

When a method is called on a literal constant (str/bytes),
the callable is always a Python builtin, regardless of
variable naming or scope.
"""

def literal_str_format():
    """Literal str.format() → python."""
    return "{}".format(42)


def literal_bytes_split():
    """Literal bytes.split() → python."""
    return b"hello world".split()


def variable_str_format(msg):
    """Variable str.format() — receiver provenance needed, NOT tested here."""
    return msg.format("test")
