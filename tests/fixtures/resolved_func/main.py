import polars as pl
from polars import DataFrame
from polars import LazyFrame as LF

pl.DataFrame({'a': [1, 2, 3]})
DataFrame({'a': [1, 2, 3]})
LF({'a': [1, 2, 3]})

df = pl.DataFrame({'a': [1, 2, 3]})
df.select(pl.col('a'))


def foo():
    pass
foo()
