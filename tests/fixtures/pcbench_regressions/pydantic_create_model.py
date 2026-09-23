# Reduced from Pydantic 1.5 pydantic/main.py.
def create_model(__model_name, *, __config=None, **field_definitions):
    return __model_name, field_definitions


def captured_old_name(name):
    return create_model(model_name=name)
