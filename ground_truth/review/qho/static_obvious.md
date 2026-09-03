# qho — static_obvious (61 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| mult_banded.py:36:8 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:47:10 | `pos(u - k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| mult_banded.py:47:28 | `range(m)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:50:10 | `pos(k - u)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| mult_banded.py:50:28 | `range(m)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:53:11 | `range(zl[k], n - zr[k])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:53:41 | `range(m)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:55:25 | `np.hstack((np.zeros(zr[k]), v, np.zeros(zl[k])))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:55:36 | `np.zeros(zr[k])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:55:54 | `np.zeros(zl[k])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:57:11 | `sum([pad(k, ab[k, loc[k]] * x[loc[k]]) for k in range(m)])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:57:16 | `pad(k, ab[k, loc[k]] * x[loc[k]])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| mult_banded.py:57:55 | `range(m)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| mult_banded.py:67:9 | `np.random.randn(m, n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:68:8 | `np.random.randn(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:69:8 | `mult_banded((l, u), ab, x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| mult_banded.py:70:8 | `solve_banded((l, u), ab, b)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| mult_banded.py:72:4 | `print(x - y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:4:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:27:17 | `np.zeros(N)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:29:12 | `np.arange(modes)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:32:17 | `np.zeros((3, modes))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:36:17 | `np.zeros((3, modes))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:40:17 | `np.zeros((3, modes))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:41:12 | `np.sqrt(j + 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:46:17 | `np.zeros((modes, N + 1), dtype=complex)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:49:17 | `np.zeros((modes, N + 1), dtype=complex)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:60:17 | `range(self.N)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:62:16 | `mult_banded((1, 1), np.conj(ab), self.Y[:, k])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:62:34 | `np.conj(ab)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:63:28 | `solve_banded((1, 1), ab, b, overwrite_ab=True, overwrite_b=True, de...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:74:31 | `np.conj(self.Y[self.f, -1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:76:17 | `range(self.N)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:79:16 | `mult_banded((1, 1), np.conj(ab), self.Z[:, k + 1])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:79:34 | `np.conj(ab)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:80:26 | `solve_banded((1, 1), ab, b, overwrite_ab=True, overwrite_b=True, de...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:91:15 | `np.array_equal(u, self.u)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:92:12 | `self._solve_state(u)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:94:31 | `sum(u ** 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:94:41 | `abs(self.Y[self.f, -1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:102:15 | `np.array_equal(u, self.u)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:103:12 | `self._solve_state(u)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:105:8 | `self._solve_adjoint(u)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:107:14 | `range(1, self.N + 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:111:14 | `np.dot(self.Z[:, j] + self.Z[:, j - 1], mult_banded((1, 1), self.X,...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:112:14 | `mult_banded((1, 1), self.X, self.Y[:, j] + self.Y[:, j - 1])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:115:35 | `np.real(np.array(ip))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:115:43 | `np.array(ip)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:135:8 | `np.linspace(0, T, N + 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:141:13 | `np.ones(N)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:144:10 | `QHO(modes, N, T, 0, 1, g)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:146:11 | `fmin_bfgs(qho.cost, u, qho.grad, args=(), gtol=1e-06, norm=np.inf, ...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:151:13 | `range(4)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| qho.py:156:12 | `np.repeat(uopt, 2 * np.ones(N, dtype=int))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:156:29 | `np.ones(N, dtype=int)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:159:12 | `np.linspace(0, T, N + 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:165:14 | `QHO(modes, N, T, 0, 1, g)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| qho.py:168:15 | `fmin_bfgs(qho.cost, u, qho.grad, args=(), gtol=1e-06, norm=np.inf, ...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:176:10 | `plt.figure(1, (16, 7))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:190:15 | `np.abs(qho.Y.T)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| qho.py:192:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
