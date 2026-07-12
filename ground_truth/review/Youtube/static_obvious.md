# Youtube — static_obvious (82 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| FuunyClusters.py:24:0 | `logging.basicConfig(level=logging.INFO)` | library / logging | library / logging | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:30:9 | `open(name + '.pkl', 'wb')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:31:8 | `pickle.dump(obj, f, protocol=2)` | library / pickle | library / pickle | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:34:9 | `open(name + '.pkl', 'rb')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:35:15 | `pickle.load(f)` | library / pickle | library / pickle | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:39:8 | `gensim.models.Word2Vec.load_word2vec_format('vectors.bin', binary=T...` | library / gensim | library / gensim | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:44:20 | `tuple(model[word])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:47:0 | `print('Vectors Loaded.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:51:14 | `tuple(model[cat[0]])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:53:0 | `print('InitSeeds Loaded.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:63:0 | `print(str(degree) + ' closest points per cluster')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:63:6 | `str(degree)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:65:11 | `dict()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:66:9 | `range(0, len(cat))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:66:17 | `len(cat)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:71:4 | `len(Rseeds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:72:5 | `len(model.vocab)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:83:12 | `len(Rseeds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:84:5 | `len(model.vocab)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:89:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:90:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:91:4 | `print(str(numInter) + ' more iterations left ...')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:91:10 | `str(numInter)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:92:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:93:9 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:95:14 | `list(set(curVecs) - set(Rseeds))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:95:19 | `set(curVecs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:95:34 | `set(Rseeds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:98:33 | `Kmeans.kmeans(np.array(curVecs), np.array(Rseeds), maxiter=1, metri...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| FuunyClusters.py:98:47 | `np.array(curVecs)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:98:66 | `np.array(Rseeds)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:99:4 | `print(str(time.time() - t0))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:99:10 | `str(time.time() - t0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:99:14 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:101:4 | `print('Level ' + str(level) + ' Done.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:101:20 | `str(level)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:105:4 | `print('Mapping Centroids to Labels')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:106:20 | `dict()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:108:33 | `tuple(c)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:112:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:114:4 | `print('Computing the next level of seeds')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:119:15 | `sorted(zip(range(0, transform.shape[0]), np.argmax(transform, axis=...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:119:22 | `zip(range(0, transform.shape[0]), np.argmax(transform, axis=1), np....` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:119:26 | `range(0, transform.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:119:54 | `np.argmax(transform, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:119:85 | `np.amax(transform, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:119:121 | `operator.itemgetter(1, 2)` | library / operator | library / operator | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:120:19 | `defaultdict(list)` | library / collections | library / collections | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:128:15 | `pyprind.ProgBar(len(Rseeds))` | library / pyprind | library / pyprind | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:128:31 | `len(Rseeds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:129:22 | `enumerate(Rseeds)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:131:19 | `np.array(curVecs)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| FuunyClusters.py:133:21 | `tuple(n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:135:48 | `tuple(cent)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:137:42 | `tuple(new)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:140:8 | `my_prbar.update()` | library / pyprind | library / pyprind | transitive_method | static_obvious | v: direct import-backed API call (pyprind) |
| FuunyClusters.py:145:38 | `tuple(n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:146:4 | `print(wordsTemp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| FuunyClusters.py:147:4 | `save_obj(wordsTemp, path + 'words' + str(level))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| FuunyClusters.py:147:38 | `str(level)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:25:11 | `issparse(X)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct scipy.sparse API call |
| Kmeans.py:26:12 | `np.asanyarray(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:27:35 | `issparse(centres)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct scipy.sparse API call |
| Kmeans.py:32:14 | `ValueError('kmeans: X %s and centres %s must have the same number o...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:34:8 | `print('kmeans: X %s  centres %s  delta=%.2g  maxiter=%d  metric=%s'...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:35:11 | `np.arange(N)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:37:17 | `range(1, maxiter + 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:38:12 | `cdist_sparse(np.float16(X), np.float16(centres), metric=metric, p=p)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| Kmeans.py:38:26 | `np.float16(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:38:41 | `np.float16(centres)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:46:18 | `range(k)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:47:16 | `np.where(xtoc == jc)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:48:15 | `len(c)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:58:12 | `issparse(X)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct scipy.sparse API call |
| Kmeans.py:58:26 | `issparse(Y)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct scipy.sparse API call |
| Kmeans.py:61:23 | `cdist(X, Y, **kwargs)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct import from scipy.spatial.distance |
| Kmeans.py:64:8 | `np.empty((X.shape[0], Y.shape[0]), np.float64)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kmeans.py:66:20 | `enumerate(X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:69:20 | `enumerate(Y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:72:20 | `enumerate(X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:73:24 | `enumerate(Y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kmeans.py:85:8 | `cdist(X, centres, metric=metric, p=p)` | library / scipy | library / scipy | transitive_method | static_obvious | v: direct import from scipy.spatial.distance |
