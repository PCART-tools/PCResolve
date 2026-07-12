# galax — static_obvious (26 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| getGeometricDistances.py:14:1 | `numpy.savetxt(outFile, numpy.array([columns]), delimiter=',', fmt='...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:14:24 | `numpy.array([columns])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:17:17 | `numpy.histogram(data1[metric])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:18:17 | `numpy.histogram(data2[metric])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:19:9 | `numpy.concatenate((bins1, bins2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:21:6 | `int(len(both) / 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| getGeometricDistances.py:21:10 | `len(both)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| getGeometricDistances.py:22:10 | `numpy.min(both)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:22:26 | `numpy.max(both)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:23:17 | `numpy.histogram(ell[metric], bins=n, range=rnge, normed=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:24:17 | `numpy.histogram(sp[metric], bins=n, range=rnge, normed=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:28:7 | `numpy.minimum(hist1, hist2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:31:7 | `numpy.sum(dy * dx)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:33:13 | `numpy.max(hist1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:34:13 | `numpy.max(hist2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:35:13 | `numpy.max(dy)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:40:23 | `sqrt(separation_BCA)` | library / math | library / math | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:44:7 | `open(outFile, 'a')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| getGeometricDistances.py:45:3 | `numpy.savetxt(f_handle, numpy.array([results]), delimiter=',', fmt=...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:45:27 | `numpy.array([results])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:48:7 | `pd.read_csv(sys.argv[1])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:48:7 | `pd.read_csv(sys.argv[1]).dropna()` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:49:6 | `pd.read_csv(sys.argv[2])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:49:6 | `pd.read_csv(sys.argv[2]).dropna()` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:50:33 | `sys.argv[3].split(',')` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| getGeometricDistances.py:52:1 | `distanceMetric(ell, sp, metrics, outFile)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
