# Youtube — dynamic_probe (9 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kmeans.py:27:14 | `centres.todense()` | library / scipy | library / numpy | transitive_method | dynamic_probe | gt: scipy sparse .todense()<br>v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:67:19 | `cdist(x.todense(), Y, **kwargs)` | library / scipy | library / scipy | transitive_method | dynamic_probe | v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:67:26 | `x.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | gt: scipy sparse .todense()<br>v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:70:21 | `cdist(X, y.todense(), **kwargs)` | library / scipy | library / scipy | transitive_method | dynamic_probe | v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:70:31 | `y.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | gt: scipy sparse .todense()<br>v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:74:25 | `cdist(x.todense(), y.todense(), **kwargs)` | library / scipy | library / scipy | transitive_method | dynamic_probe | v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:74:32 | `x.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | gt: scipy sparse .todense()<br>v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:74:45 | `y.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | gt: scipy sparse .todense()<br>v: probe confirms .todense() __module__ is scipy.sparse._base; scipy sparse method. |
| Kmeans.py:86:11 | `D.argmin(axis=1)` | library / numpy | library / numpy | transitive_method | dynamic_probe | gt: .argmin() on numpy array from cdist<br>v: probe confirms cdist() returns numpy.ndarray, .argmin() is numpy method; PCResol |
