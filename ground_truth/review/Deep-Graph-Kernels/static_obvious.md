# Deep-Graph-Kernels — static_obvious (69 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kronecker_Generator.py:12:4 | `sparse.csr_matrix(np.array([[0, 2], [5, 0]]))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:12:22 | `np.array([[0, 2], [5, 0]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:13:4 | `sparse.csr_matrix(np.array([[1, 2], [3, 4]]))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:13:22 | `np.array([[1, 2], [3, 4]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:14:0 | `sparse.kron(A, B)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:14:0 | `sparse.kron(A, B).toarray()` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:15:0 | `sparse.kron(A, B)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:15:0 | `sparse.kron(A, B).todense()` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:20:5 | `lil_matrix((100, 100))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:21:13 | `rand(10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:23:11 | `rand(100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:28:5 | `lil_matrix((100, 100))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:29:13 | `rand(10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:31:11 | `rand(100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:36:5 | `sparse.kron(A1, B1)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:36:5 | `sparse.kron(A1, B1).toarray()` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:39:5 | `sparse.kronsum(A1, B1)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:39:5 | `sparse.kronsum(A1, B1).toarray()` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:11 | `dia_matrix((np.array([np.array([2] * 5), np.array([1] * 5), np.arra...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:24 | `np.array([np.array([2] * 5), np.array([1] * 5), np.array([1] * 5)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:35 | `np.array([2] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:51 | `np.array([1] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:68 | `np.array([1] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:43:87 | `np.array([0, 1, -1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:11 | `dia_matrix((np.array([np.array([2] * 5), np.array([1] * 5), np.arra...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:24 | `np.array([np.array([2] * 5), np.array([1] * 5), np.array([1] * 5)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:35 | `np.array([2] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:51 | `np.array([1] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:68 | `np.array([1] * 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:45:87 | `np.array([0, 1, -1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:47:5 | `np.linspace(0, 1, 5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:48:4 | `populatematrix1(len(dx))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| Kronecker_Generator.py:48:20 | `len(dx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:49:0 | `print(x.shape, type(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:49:16 | `type(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:50:4 | `populatematrix2(len(dx))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| Kronecker_Generator.py:50:20 | `len(dx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:51:0 | `print(y.shape, type(y))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:51:16 | `type(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:52:4 | `kron(x, y)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:53:0 | `print(z.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:59:15 | `scipy.sparse.lil_matrix((numVertices, numVertices))` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:60:8 | `SparseGraph(numVertices, W=weightMatrix)` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:65:0 | `print(graph.size)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:68:4 | `np.reshape(np.random.random_integers(0, 1, size=100), (10, 10))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:68:15 | `np.random.random_integers(0, 1, size=100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:69:3 | `nx.DiGraph(a)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:74:10 | `scipy.linalg.expm(a, q=None)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:75:0 | `print('debug')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:78:6 | `np.sum(Mat_Exp)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:79:10 | `np.cumsum(Mat_Exp)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:102:33 | `float('inf')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:104:12 | `initialGraph.getWeightMatrix()` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:105:12 | `np.diag(W)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:105:24 | `np.zeros(W.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:106:18 | `ValueError('Initial graph must have all self-edges')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:118:33 | `float('inf')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:127:12 | `self.initialGraph.adjacencyMatrix()` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:130:17 | `range(1, self.k)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:131:17 | `np.kron(Wi, W)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:133:16 | `VertexList(Wi.shape[0], 0)` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:134:16 | `SparseGraph(vList, self.initialGraph.isUndirected())` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:134:35 | `self.initialGraph.isUndirected()` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:148:16 | `VertexList(numVertices, numFeatures)` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:149:23 | `SparseGraph(vList)` | library / apgl | library / apgl | direct_import | static_obvious | v: direct import-backed API call |
| Kronecker_Generator.py:153:17 | `range(numVertices)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| Kronecker_Generator.py:156:20 | `KroneckerGenerator(initialGraph, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| Kronecker_Generator.py:158:16 | `generator.generate()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| Kronecker_Generator.py:159:8 | `print(graph.size)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
