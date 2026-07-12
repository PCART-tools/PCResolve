# machine-learning — static_obvious (39 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| sci.py:9:6 | `np.array([[1, 2], [3, 4]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:11:0 | `print('矩阵行列式：', linalg.det(arr))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:11:27 | `linalg.det(arr)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:12:0 | `print('矩阵的逆：', linalg.inv(arr))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:12:24 | `linalg.inv(arr)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:19:6 | `np.arange(9)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:19:6 | `np.arange(9).reshape((3, 3))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:19:37 | `np.diag([1, 0, 1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:20:20 | `linalg.svd(arr)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:21:0 | `print(spec)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:22:7 | `np.diag(spec)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:24:0 | `print(svd_mat)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:25:0 | `np.allclose(arr, svd_mat)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:35:21 | `np.sin(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:37:4 | `np.arange(-10, 10, 0.1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:42:0 | `optimize.fmin_bfgs(f, 0)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:48:0 | `optimize.fmin_bfgs(f, 3)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:55:0 | `optimize.basinhopping(f, 0)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:63:7 | `optimize.fsolve(f, 1)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:71:8 | `np.linspace(-10, 10, num=20)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:72:8 | `f(xdata)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| sci.py:72:19 | `np.random.randn(xdata.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:75:23 | `np.sin(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:77:28 | `optimize.curve_fit(f2, xdata, ydata, guess)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:85:4 | `np.random.normal(size=1000)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:86:7 | `np.arange(-4, 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:87:0 | `print(bins)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:88:12 | `np.histogram(a, bins=bins, normed=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:89:0 | `print(histogram)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:91:0 | `print(bins)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:95:0 | `print('pdf:', b)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:101:0 | `print('loc:' + str(loc) + 'std:' + str(std))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:101:13 | `str(loc)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:101:29 | `str(std)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| sci.py:103:0 | `np.median(a)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:110:0 | `stats.scoreatpercentile(a, 50)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:117:4 | `np.random.normal(0, 1, size=100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:118:4 | `np.random.normal(1, 1, size=10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| sci.py:119:0 | `stats.ttest_ind(a, b)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
