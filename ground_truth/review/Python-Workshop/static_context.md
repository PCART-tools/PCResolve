# Python-Workshop — static_context (28 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| constrained.py:38:6 | `minimize(rosen, x0, jac=rosen_der, constraints=cons, method='SLSQP'...` | library / scipy | library / scipy | direct_import | static_context | v: from scipy.optimize import minimize (line 2) |
| unconstrained.py:27:6 | `minimize(rosen, x0, method='BFGS', jac=rosen_der, options={'disp': ...` | library / scipy | library / scipy | direct_import | static_context | v: from scipy.optimize import minimize (line 2) |
| myregr.py:30:8 | `plt.figure()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:34:14 | `minimize(residue, c0, method='SLSQP', jac=jacobian, constraints=cons)` | library / scipy | library / scipy | direct_import | static_context | v: from scipy.optimize import minimize (line 2) |
| myregr.py:39:8 | `plt.subplot(2, 2, idx + 1)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:40:8 | `plt.tight_layout()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:41:8 | `plt.plot(x0, y0, 'bo', fillstyle='none')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:42:8 | `plt.plot(x0, np.sin(x0), 'b--', linewidth=2)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:43:8 | `plt.plot(x0, recover(pol(x), yavr, ystd), 'r-', linewidth=2)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:44:8 | `plt.grid()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:45:8 | `plt.title('Order = {0:d}'.format(odr))` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:56:8 | `plt.figure()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:57:4 | `plt.plot(x0, y0, 'bo', fillstyle='none')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:58:4 | `plt.grid()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:59:4 | `plt.xlabel('x')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:60:4 | `plt.ylabel('y')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:61:4 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:88:4 | `plt.figure()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:89:4 | `plt.semilogy(np.abs(s1[3]), 'bo', label='Simple')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:90:4 | `plt.semilogy(np.abs(s2[3]), 'rs', label='Lasso')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:92:4 | `plt.grid()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:93:4 | `plt.xlabel('Order')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:94:4 | `plt.ylabel('Coefficients')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:95:4 | `plt.legend()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| myregr.py:97:4 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; plt is matplotlib pyplot module |
| skregr.py:13:8 | `model.fit(X, y)` | library / sklearn | library / sklearn | direct_import | static_context | v: model is sklearn linear_model instance (LinearRegression/Lasso/Ridge); .fit is s |
| skregr.py:20:20 | `model.predict(X)` | library / sklearn | library / sklearn | direct_import | static_context | v: model is sklearn linear_model instance; .predict is sklearn estimator method |
| truss.py:16:6 | `minimize(weight, x0, jac=weight_der, constraints=cons, method='SLSQ...` | library / scipy | library / scipy | direct_import | static_context | v: from scipy.optimize import minimize (line 2) |
