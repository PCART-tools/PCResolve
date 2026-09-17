def outer(first, second):
    captured = first

    def child(argument):
        nonlocal captured
        unused = lambda: second
        captured = argument
        return captured

    return child(second)
