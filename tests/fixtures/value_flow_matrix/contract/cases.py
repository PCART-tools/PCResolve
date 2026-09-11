from helper import helper


def entry(value):
    return helper(value)


def twice(value):
    helper(value)
    return helper(value)
