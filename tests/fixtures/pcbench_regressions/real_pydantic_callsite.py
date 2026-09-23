from pydantic.main import create_model


def entry(name):
    return create_model(model_name=name)
