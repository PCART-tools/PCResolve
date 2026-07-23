# gistable — static_obvious (7 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| snippet.py:25:24 | `np.histogram2d(xdata, ydata, bins=(nbins_x, nbins_y), normed=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| snippet.py:31:16 | `so.brentq(find_confidence_interval, 0.0, 1.0, args=(pdf, 0.68))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| snippet.py:32:16 | `so.brentq(find_confidence_interval, 0.0, 1.0, args=(pdf, 0.95))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| snippet.py:33:18 | `so.brentq(find_confidence_interval, 0.0, 1.0, args=(pdf, 0.99))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| snippet.py:47:11 | `np.random.normal(10.0, 15.0, size=(12540035, 2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| snippet.py:48:4 | `density_contour(norm[:, 0], norm[:, 1], 100, 100)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| snippet.py:52:0 | `test_density_contour()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
