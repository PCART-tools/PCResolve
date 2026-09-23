def create_model(__model_name, *, __config=None, **field_definitions):
    return __model_name, field_definitions


def pydantic_style(name):
    return create_model(model_name=name)


def positional(value, *items):
    return value, items


def duplicate(value):
    return positional(value, value=value)


def literal_star(left, right):
    return positional(*(left, right))
