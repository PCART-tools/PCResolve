def helper(value):
    return value


def entry(value, first, second):
    result = helper(value)
    if first:
        result = helper(result)
    if second:
        pass
    else:
        result = helper(result)
    return result
