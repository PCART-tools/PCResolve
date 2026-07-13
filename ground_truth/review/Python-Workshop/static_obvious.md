# Python-Workshop — static_obvious (139 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| constrained.py:17:10 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:25:28 | `np.array([x[0] + x[1] - 1.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:26:28 | `np.array([1.0, 1.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:28:28 | `np.array([1 - x[0] ** 2 - x[1] ** 2])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:29:28 | `np.array([-x[0] * 2.0, -x[1] * 2.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:34:5 | `np.array([0.0, 0.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:39:0 | `print('+++++++++res', res.x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:46:12 | `np.linspace(0, 2.0 * np.pi, 100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:49:13 | `xrange(len(theta))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:49:20 | `len(theta)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:50:8 | `x_cir.append(np.cos(theta[i]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:50:21 | `np.cos(theta[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:51:8 | `y_cir.append(np.sin(theta[i]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:51:21 | `np.sin(theta[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:52:4 | `plt.plot(x_cir, y_cir)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:55:12 | `np.linspace(0, 1, 100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:58:13 | `xrange(len(t_vec))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:58:20 | `len(t_vec)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:60:8 | `x_line.append(t_loc * 0.0 + (1 - t_loc) * 1.0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:61:8 | `y_line.append(t_loc * 1.0 + (1 - t_loc) * 0.0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:62:4 | `plt.plot(x_line, y_line)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:65:8 | `np.arange(-3.0, 3.0, delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:66:8 | `np.arange(-3.0, 3.0, delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:67:11 | `np.meshgrid(x, y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:69:8 | `np.array(np.zeros((len(y), len(x))))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:69:17 | `np.zeros((len(y), len(x)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:69:27 | `len(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:69:34 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:70:13 | `xrange(len(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:70:20 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:71:17 | `xrange(len(y))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:71:24 | `len(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| constrained.py:75:18 | `np.array([loc_x, loc_y])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:77:21 | `rosen(loc)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| constrained.py:79:13 | `np.arange(0, 1000, 50)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:80:9 | `plt.contour(X, Y, Z, levels)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:81:4 | `plt.clabel(CS, inline=100, fontsize=10)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:82:4 | `plt.plot(res.x[0], res.x[1], '*', markersize=20)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:83:4 | `plt.axes()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:83:4 | `plt.axes().set_aspect('equal', 'datalim')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| constrained.py:84:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:17:10 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:24:5 | `np.array([0.0, 0.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:28:0 | `print('+++++++++res', res.x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:35:8 | `np.arange(-3.0, 3.0, delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:36:8 | `np.arange(-3.0, 3.0, delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:37:11 | `np.meshgrid(x, y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:39:8 | `np.array(np.zeros((len(y), len(x))))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:39:17 | `np.zeros((len(y), len(x)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:39:27 | `len(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:39:34 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:40:13 | `xrange(len(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:40:20 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:41:17 | `xrange(len(y))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:41:24 | `len(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| unconstrained.py:45:18 | `np.array([loc_x, loc_y])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:47:21 | `rosen(loc)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| unconstrained.py:49:13 | `np.arange(0, 1000, 50)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:50:9 | `plt.contour(X, Y, Z, levels)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:51:4 | `plt.clabel(CS, inline=100, fontsize=10)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:52:4 | `plt.plot(res.x[0], res.x[1], '*', markersize=20)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| unconstrained.py:53:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:6:10 | `np.mean(v)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:7:10 | `np.std(v)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:14:10 | `np.poly1d(c[::-1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:19:10 | `np.poly1d(c[::-1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:21:10 | `np.zeros_like(c)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:22:10 | `np.ones_like(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:23:13 | `range(len(c))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:23:19 | `len(c)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:31:15 | `range(len(odrs))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:31:21 | `len(odrs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:33:14 | `np.zeros((odr + 1,))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:36:14 | `np.poly1d(c.x[::-1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:42:21 | `np.sin(x0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:43:21 | `recover(pol(x), yavr, ystd)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:45:18 | `'Order = {0:d}'.format(odr)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:50:4 | `np.random.seed(10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:51:9 | `np.arange(60, 300, 4)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:52:9 | `np.sin(x0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:52:22 | `np.random.normal(0, 0.15, len(x0))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:52:48 | `len(x0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| myregr.py:53:20 | `normalize(x0)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:54:20 | `normalize(y0)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:64:25 | `polynomialResidue(c, x, y)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:65:25 | `polynomialJacobian(c, x, y)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:71:13 | `regs(odrs)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:76:37 | `np.sum(np.abs(c))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:76:44 | `np.abs(c)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:77:13 | `regs(odrs, cons)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| myregr.py:87:8 | `np.polyfit(x0, y0, 16)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:89:17 | `np.abs(s1[3])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| myregr.py:90:17 | `np.abs(s2[3])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:3:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:9:8 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:10:15 | `range(len(odrs))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| skregr.py:10:21 | `len(odrs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| skregr.py:12:14 | `np.column_stack([x ** i for i in range(odr + 1)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:12:45 | `range(odr + 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| skregr.py:16:8 | `plt.subplot(2, 2, idx + 1)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:17:8 | `plt.tight_layout()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:18:8 | `plt.plot(x, y, 'bo', fillstyle='none')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:19:8 | `plt.plot(x, np.sin(x), 'b--', linewidth=2)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:19:20 | `np.sin(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:20:8 | `plt.plot(x, model.predict(X), 'r-', linewidth=2)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:21:8 | `plt.grid()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:22:8 | `plt.title('Order = {0:d}'.format(odr))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:22:18 | `'Order = {0:d}'.format(odr)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| skregr.py:27:4 | `np.random.seed(10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:28:8 | `np.arange(60, 300, 4)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:29:8 | `np.sin(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:29:20 | `np.random.normal(0, 0.15, len(x))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:29:46 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| skregr.py:35:13 | `regs(odrs, linear_model.LinearRegression(normalize=True))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| skregr.py:35:24 | `linear_model.LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:36:13 | `regs(odrs, linear_model.Lasso(alpha=0.0001, normalize=True))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| skregr.py:36:24 | `linear_model.Lasso(alpha=0.0001, normalize=True)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:37:13 | `regs(odrs, linear_model.Ridge(alpha=0.0001, normalize=True))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| skregr.py:37:24 | `linear_model.Ridge(alpha=0.0001, normalize=True)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:40:4 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:41:4 | `plt.semilogy(np.abs(s1[3]), 'bo', label='Simple')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:41:17 | `np.abs(s1[3])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:42:4 | `plt.semilogy(np.abs(s2[3]), 'rs', label='Lasso')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:42:17 | `np.abs(s2[3])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:43:4 | `plt.semilogy(np.abs(s3[3]), 'gv', label='Ridge')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:43:17 | `np.abs(s3[3])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:44:4 | `plt.grid()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:45:4 | `plt.xlabel('Order')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:46:4 | `plt.ylabel('Coefficients')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:47:4 | `plt.legend()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| skregr.py:49:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:5:21 | `np.sqrt(3.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:7:10 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:9:14 | `np.sqrt(3.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:14:28 | `np.array([-18.0 * x[0] - 6.0 * np.sqrt(3.0) * x[1] + 3.0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:14:53 | `np.sqrt(3.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:15:28 | `np.array([-18.0, -6.0 * np.sqrt(3.0)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:15:50 | `np.sqrt(3.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| truss.py:18:0 | `print('+++++++++res', res.x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
