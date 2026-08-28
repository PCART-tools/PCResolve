import numpy as np
import pandas as pd


class Holder:
    def fit(self, value):
        self.payload = value

    def reshape_payload(self):
        return self.payload.reshape(1, -1)


class Base:
    def fit(self, value):
        return self._fit(value)

    def reshape_payload(self):
        return self.payload.reshape(1, -1)


class Child(Base):
    def _fit(self, value):
        self.payload = value
        return self


class Uncalled:
    def fit(self, value):
        self.payload = value

    def reshape_payload(self):
        return self.payload.reshape(1, -1)


class NumpyField:
    def fit(self, value):
        self.payload = value

    def total(self):
        return (self.payload * 2).sum()


class PandasField:
    def fit(self, value):
        self.payload = value

    def total(self):
        return (self.payload * 2).sum()


class SharedBase:
    def reshape_payload(self):
        return self.payload.reshape(1, -1)


class SharedNumpy(SharedBase):
    def fit(self, value):
        self.payload = value


class SharedPandas(SharedBase):
    def fit(self, value):
        self.payload = value


direct = Holder()
direct.fit(np.array([1, 2]))
direct.reshape_payload()

inherited = Child()
inherited.fit(np.array([1, 2]))
inherited.reshape_payload()

uncalled = Uncalled()
uncalled.reshape_payload()

numpy_field = NumpyField()
numpy_field.fit(np.array([1, 2]))
numpy_field.total()

pandas_field = PandasField()
pandas_field.fit(pd.DataFrame([1, 2]))
pandas_field.total()

shared_numpy = SharedNumpy()
shared_numpy.fit(np.array([1, 2]))
shared_numpy.reshape_payload()

shared_pandas = SharedPandas()
shared_pandas.fit(pd.DataFrame([1, 2]))
shared_pandas.reshape_payload()
