# gistable — dynamic_probe (2 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| snippet.py:26:18 | `(xedges[1:] - xedges[:-1]).reshape((1, nbins_x))` | library / numpy | library / numpy | transitive_method | dynamic_probe | v: probe confirms ndarray.reshape() is numpy method after to_numpy conversion bound |
| snippet.py:27:18 | `(yedges[1:] - yedges[:-1]).reshape((nbins_y, 1))` | library / numpy | library / numpy | transitive_method | dynamic_probe | v: probe confirms ndarray.reshape() is numpy method after to_numpy conversion bound |
