# machine-learning — dynamic_probe (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| sci.py:23:10 | `uarr.dot(sarr)` | library / numpy | library / numpy | transitive_method | dynamic_probe | gt: NumPy ndarray dot method<br>v: type(uarr) is numpy.ndarray and uarr.dot.__self__ is uarr |
| sci.py:23:10 | `uarr.dot(sarr).dot(vharr)` | library / numpy | library / numpy | transitive_method | dynamic_probe | gt: NumPy ndarray dot method after ndarray return<br>v: the intermediate result is numpy.ndarray and abc.dot.__self__ is abc |
| sci.py:94:4 | `stats.norm.pdf(bins)` | library / scipy | library / scipy | transitive_method | dynamic_probe | gt: SciPy normal distribution pdf method<br>v: inspect.getmodule(stats.norm.pdf) reports scipy.stats._distn_infrastructure |
| sci.py:100:11 | `stats.norm.fit(a)` | library / scipy | library / scipy | transitive_method | dynamic_probe | gt: SciPy normal distribution fit method<br>v: inspect.getmodule(stats.norm.fit) reports scipy.stats._continuous_distns |
