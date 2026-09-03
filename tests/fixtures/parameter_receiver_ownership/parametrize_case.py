import pytest


class Model:
    def fit(self, data):
        return data


@pytest.mark.parametrize("model", [Model()])
def test_model(model):
    model.fit([])
