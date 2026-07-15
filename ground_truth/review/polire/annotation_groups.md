# polire -- Annotation Groups (100 groups, 165 records)

## Summary

| Evidence | Groups | Records | Needs Human |
|----------|--------|---------|-------------|
| static_obvious | 27 | 37 | 0 |
| static_context | 6 | 8 | 0 |
| manual_reasoned | 67 | 120 | 120 |
| **Total** | **100** | **165** | **120** |

## Group 1: plt -> library/matplotlib (9 records)

| Evidence | static_obvious |
| Needs human | no (0/9) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ usage.py:3 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.title(r)</code> -- usage.py:43
- <code>plt.show()</code> -- usage.py:44
- <code>plt.close()</code> -- usage.py:45
- <code>plt.title(r)</code> -- usage.py:59
- <code>plt.show()</code> -- usage.py:60
- ... and 4 more

**All bindings (1 unique):**
- <code>usage.py</code> L3: <code>import matplotlib.pyplot</code>

## Group 2: self -> ?/? (8 records)

| Evidence | manual_reasoned |
| Needs human | yes (8/8) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:57 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__calculate_dmat()</code> -- polire/nsgp/nsgp.py:58
- <code>self.__weight_func(s1)</code> -- polire/nsgp/nsgp.py:149
- <code>self.__weight_func(s2)</code> -- polire/nsgp/nsgp.py:153
- <code>self.__get_close_locs()</code> -- polire/nsgp/nsgp.py:222
- <code>self.__learnLocal()</code> -- polire/nsgp/nsgp.py:223
- <code>self._Kernel(self._X, self._X)</code> -- polire/nsgp/nsgp.py:232
- <code>self._Kernel(X, self._X)</code> -- polire/nsgp/nsgp.py:233
- <code>self._Kernel(X, X)</code> -- polire/nsgp/nsgp.py:239

**All bindings (4 unique):**
- <code>polire/nsgp/nsgp.py</code> L57: <code>parameter self</code>
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>
- <code>polire/nsgp/nsgp.py</code> L197: <code>parameter self</code>
- <code>polire/nsgp/nsgp.py</code> L226: <code>parameter self</code>

## Group 3: r -> ?/? (6 records)

| Evidence | manual_reasoned |
| Needs human | yes (6/6) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ usage.py:38 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>r.fit(X, y)</code> -- usage.py:39
- <code>r.predict_grid()</code> -- usage.py:40
- <code>r.fit(X1, y1)</code> -- usage.py:55
- <code>r.predict_grid()</code> -- usage.py:56
- <code>r.fit(X, y)</code> -- usage.py:67
- <code>r.predict(np.array(test_data))</code> -- usage.py:79

**All bindings (3 unique):**
- <code>usage.py</code> L38: <code>for target</code>
- <code>usage.py</code> L54: <code>for target</code>
- <code>usage.py</code> L66: <code>for target</code>

## Group 4: self -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__kernels[i](S1, self._X)</code> -- polire/nsgp/nsgp.py:156
- <code>self.__kernels[i](self._X, S2)</code> -- polire/nsgp/nsgp.py:157
- <code>self.__kernels[i](S1, S2)</code> -- polire/nsgp/nsgp.py:158
- <code>self.__kernels[i](S1, self._X)</code> -- polire/nsgp/nsgp.py:162
- <code>self.__kernels[i](S1)</code> -- polire/nsgp/nsgp.py:164

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 5: nn -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>NaturalNeighbor()</code> @ usage.py:86 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>nn.fit(X, y)</code> -- usage.py:90
- <code>nn.predict(np.array(test_data))</code> -- usage.py:92
- <code>nn.fit(X, y)</code> -- usage.py:99
- <code>nn.predict_grid()</code> -- usage.py:100

**All bindings (2 unique):**
- <code>usage.py</code> L86: <code>NaturalNeighbor()</code>
- <code>usage.py</code> L98: <code>NaturalNeighbor()</code>

## Group 6: self -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/preprocessing/sptial_features.py:58 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.distance(lonlat, self_lonlat)</code> -- polire/preprocessing/sptial_features.py:93
- <code>self.fit(X, y)</code> -- polire/preprocessing/sptial_features.py:130
- <code>self.transform(X)</code> -- polire/preprocessing/sptial_features.py:131

**All bindings (2 unique):**
- <code>polire/preprocessing/sptial_features.py</code> L58: <code>parameter self</code>
- <code>polire/preprocessing/sptial_features.py</code> L129: <code>parameter self</code>

## Group 7: self -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/spatial/spatial.py:41 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._predict(np.asarray([X1.ravel(), X2.ravel()]).T)</code> -- polire/spatial/spatial.py:53
- <code>self._average(X)</code> -- polire/spatial/spatial.py:59
- <code>self.distance(X, self.X)</code> -- polire/spatial/spatial.py:62

**All bindings (3 unique):**
- <code>polire/spatial/spatial.py</code> L41: <code>parameter self</code>
- <code>polire/spatial/spatial.py</code> L55: <code>parameter self</code>
- <code>polire/spatial/spatial.py</code> L61: <code>parameter self</code>

## Group 8: self -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/base/base.py:15 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._fit(X, y, **kwargs)</code> -- polire/base/base.py:50
- <code>self._predict(X, **kwargs)</code> -- polire/base/base.py:80
- <code>self._predict_grid(x1lim, x2lim)</code> -- polire/base/base.py:117

**All bindings (3 unique):**
- <code>polire/base/base.py</code> L15: <code>parameter self</code>
- <code>polire/base/base.py</code> L52: <code>parameter self</code>
- <code>polire/base/base.py</code> L82: <code>parameter self</code>

## Group 9: self.model -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ polire/gp/gp.py:31 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.model.optimize_restarts(n_restarts, verbose=verbose)</code> -- polire/gp/gp.py:39
- <code>self.model.predict(X)</code> -- polire/gp/gp.py:53
- <code>self.model.predict(X)</code> -- polire/gp/gp.py:61

**All bindings (3 unique):**
- <code>polire/gp/gp.py</code> L31: <code>parameter self</code>
- <code>polire/gp/gp.py</code> L42: <code>parameter self</code>
- <code>polire/gp/gp.py</code> L57: <code>parameter self</code>

## Group 10: self.reg -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/custom/custom.py:34 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.reg.fit(X, y)</code> -- polire/custom/custom.py:38
- <code>self.reg.predict(np.asarray([X1.ravel(), X2.ravel()]).T)</code> -- polire/custom/custom.py:53
- <code>self.reg.predict(X)</code> -- polire/custom/custom.py:59

**All bindings (3 unique):**
- <code>polire/custom/custom.py</code> L34: <code>parameter self</code>
- <code>polire/custom/custom.py</code> L41: <code>parameter self</code>
- <code>polire/custom/custom.py</code> L55: <code>parameter self</code>

## Group 11: job -> library/multiprocessing (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>mp.Pool()</code> @ polire/nsgp/nsgp.py:115 |
| Owner | multiprocessing |
| Proposed GT | library / multiprocessing |

**Representative expressions:**

- <code>job.map(self._model, list(range(self._X.shape[0])))</code> -- polire/nsgp/nsgp.py:116
- <code>job.map(self._c_inv, self.__kernels)</code> -- polire/nsgp/nsgp.py:117
- <code>job.close()</code> -- polire/nsgp/nsgp.py:118

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L115: <code>mp.Pool()</code>

## Group 12: (self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>(self.y * mask).sum(axis=1)</code> -- polire/spatial/spatial.py:64
- <code>(self.y * mask).sum()</code> -- polire/idw/idw.py:89


## Group 13: KX_test -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self._Kernel(X, self._X)</code> @ polire/nsgp/nsgp.py:233 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>KX_test.dot(self._KX_inv)</code> -- polire/nsgp/nsgp.py:235
- <code>KX_test.dot(self._KX_inv)</code> -- polire/nsgp/nsgp.py:239

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L233: <code>self._Kernel(X, self._X)</code>

## Group 14: KX_test.dot(self._KX_inv) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self._Kernel(X, self._X)</code> @ polire/nsgp/nsgp.py:233 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>KX_test.dot(self._KX_inv).dot(self._y - self._y.mean())</code> -- polire/nsgp/nsgp.py:235
- <code>KX_test.dot(self._KX_inv).dot(KX_test.T)</code> -- polire/nsgp/nsgp.py:239

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L233: <code>self._Kernel(X, self._X)</code>

## Group 15: dst -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self.distance(lonlat, self_lonlat)</code> @ polire/preprocessing/sptial_features.py:93 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>dst.argsort()</code> -- polire/preprocessing/sptial_features.py:95
- <code>dst.argsort()</code> -- polire/preprocessing/sptial_features.py:97

**All bindings (1 unique):**
- <code>polire/preprocessing/sptial_features.py</code> L93: <code>self.distance(lonlat, self_lonlat)</code>

## Group 16: model -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>IDW(exponent=self.idw_exponent)</code> @ polire/preprocessing/sptial_features.py:111 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>model.fit(self_lonlat[idx[i]], self_y_local[idx[i]])</code> -- polire/preprocessing/sptial_features.py:114
- <code>model.predict(lonlat[i][None, :])</code> -- polire/preprocessing/sptial_features.py:115

**All bindings (1 unique):**
- <code>polire/preprocessing/sptial_features.py</code> L111: <code>IDW(exponent=self.idw_exponent)</code>

## Group 17: model -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter model</code> @ tests/polire_basic.py:37 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>model.fit(X, y)</code> -- tests/polire_basic.py:39
- <code>model.predict(X_new)</code> -- tests/polire_basic.py:40

**All bindings (1 unique):**
- <code>tests/polire_basic.py</code> L37: <code>parameter model</code>

## Group 18: model -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | UNRESOLVED |
| Key binding | <code>NSGP()</code> @ tests/polire_basic.py:48 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>model.fit(X, y, **{'ECM': X @ X.T})</code> -- tests/polire_basic.py:50
- <code>model.predict(X_new)</code> -- tests/polire_basic.py:51

**All bindings (1 unique):**
- <code>tests/polire_basic.py</code> L48: <code>NSGP()</code>

## Group 19: new_polygon -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>Polygon(order_poly(new))</code> @ polire/natural_neighbors/natural_neighbors.py:195 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>new_polygon.intersects(self.vertex_poly_map[i])</code> -- polire/natural_neighbors/natural_neighbors.py:199
- <code>new_polygon.intersection(self.vertex_poly_map[i])</code> -- polire/natural_neighbors/natural_neighbors.py:201

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L195: <code>Polygon(order_poly(new))</code>

## Group 20: predictions -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>(tuple) self.model.predict(X)</code> @ polire/gp/gp.py:61 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>predictions.ravel()</code> -- polire/gp/gp.py:63
- <code>predictions.ravel()</code> -- polire/gp/gp.py:65

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L61: <code>(tuple) self.model.predict(X)</code>

## Group 21: r -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ usage3.py:22 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>r.fit(X, y)</code> -- usage3.py:31
- <code>r.predict_grid((0, 3), (0, 3))</code> -- usage3.py:32

**All bindings (1 unique):**
- <code>usage3.py</code> L22: <code>for target</code>

## Group 22: self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/natural_neighbors/natural_neighbors.py:138 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._predict(np.array([X1.ravel(), X2.ravel()]).T)</code> -- polire/natural_neighbors/natural_neighbors.py:147
- <code>self._fit(self.X, self.y)</code> -- polire/natural_neighbors/natural_neighbors.py:168

**All bindings (2 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L138: <code>parameter self</code>
- <code>polire/natural_neighbors/natural_neighbors.py</code> L149: <code>parameter self</code>

## Group 23: self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/idw/idw.py:65 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._predict(np.array([X1.ravel(), X2.ravel()]).T)</code> -- polire/idw/idw.py:74
- <code>self.distance(self.X, X)</code> -- polire/idw/idw.py:81

**All bindings (2 unique):**
- <code>polire/idw/idw.py</code> L65: <code>parameter self</code>
- <code>polire/idw/idw.py</code> L76: <code>parameter self</code>

## Group 24: self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/trend/trend.py:57 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.func((X1, X2), *self.popt)</code> -- polire/trend/trend.py:69
- <code>self.func((x1, x2), *self.popt)</code> -- polire/trend/trend.py:76

**All bindings (2 unique):**
- <code>polire/trend/trend.py</code> L57: <code>parameter self</code>
- <code>polire/trend/trend.py</code> L71: <code>parameter self</code>

## Group 25: self.__c_mat_s1[i, :, :] -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i])</code> -- polire/nsgp/nsgp.py:171
- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i])</code> -- polire/nsgp/nsgp.py:190

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 26: self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma)</code> -- polire/nsgp/nsgp.py:171
- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self.__c_mat_s2[i, :, :])</code> -- polire/nsgp/nsgp.py:190

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 27: self.__v_s1[:, i] -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__v_s1[:, i].reshape(-1, 1)</code> -- polire/nsgp/nsgp.py:177
- <code>self.__v_s1[:, i].reshape(-1, 1)</code> -- polire/nsgp/nsgp.py:185

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 28: self.__v_s1[:, i].reshape(-1, 1) -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__v_s1[:, i].reshape(-1, 1).dot(self.__v_s2[:, j].reshape(1, -1))</code> -- polire/nsgp/nsgp.py:177
- <code>self.__v_s1[:, i].reshape(-1, 1).dot(self.__v_s2[:, i].reshape(1, -1))</code> -- polire/nsgp/nsgp.py:185

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 29: self._y -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:226 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._y.mean()</code> -- polire/nsgp/nsgp.py:235
- <code>self._y.mean()</code> -- polire/nsgp/nsgp.py:236

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L226: <code>parameter self</code>

## Group 30: self.ok -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ polire/kriging/kriging.py:100 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.ok.execute(style='grid', xpoints=x1, ypoints=x2)</code> -- polire/kriging/kriging.py:109
- <code>self.ok.execute(style='points', xpoints=X[:, 0], ypoints=X[:, 1])</code> -- polire/kriging/kriging.py:124

**All bindings (2 unique):**
- <code>polire/kriging/kriging.py</code> L100: <code>parameter self</code>
- <code>polire/kriging/kriging.py</code> L120: <code>parameter self</code>

## Group 31: self.uk -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ polire/kriging/kriging.py:100 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.uk.execute(style='grid', xpoints=x1, ypoints=x2)</code> -- polire/kriging/kriging.py:114
- <code>self.uk.execute(style='points', xpoints=X[:, 0], ypoints=X[:, 1])</code> -- polire/kriging/kriging.py:129

**All bindings (2 unique):**
- <code>polire/kriging/kriging.py</code> L100: <code>parameter self</code>
- <code>polire/kriging/kriging.py</code> L120: <code>parameter self</code>

## Group 32: vor -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.voronoi</code> @ polire/natural_neighbors/natural_neighbors.py:170 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>vor.add_points(np.array([X[index]]))</code> -- polire/natural_neighbors/natural_neighbors.py:171
- <code>vor.close()</code> -- polire/natural_neighbors/natural_neighbors.py:172

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L170: <code>self.voronoi</code>

## Group 33: x -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter x</code> @ polire/utils/gridding.py:10 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>x.min()</code> -- polire/utils/gridding.py:35
- <code>x.max()</code> -- polire/utils/gridding.py:36

**All bindings (1 unique):**
- <code>polire/utils/gridding.py</code> L10: <code>parameter x</code>

## Group 34: y -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter y</code> @ polire/utils/gridding.py:10 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>y.min()</code> -- polire/utils/gridding.py:33
- <code>y.max()</code> -- polire/utils/gridding.py:34

**All bindings (1 unique):**
- <code>polire/utils/gridding.py</code> L10: <code>parameter y</code>

## Group 35: y_new -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | UNRESOLVED |
| Key binding | <code>model.predict(X_new)</code> @ tests/polire_basic.py:51 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>y_new.sum()</code> -- tests/polire_basic.py:54
- <code>y_new.sum()</code> -- tests/polire_basic.py:54

**All bindings (1 unique):**
- <code>tests/polire_basic.py</code> L51: <code>model.predict(X_new)</code>

## Group 36: bisplev -> library/scipy (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.interpolate import bisplev</code> @ polire/spline/bspline.py:2 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>bisplev(np.linspace(x1min, x1max, self.resolution), np.linspace(x2min, x2max, self.resolution), self</code> -- polire/spline/bspline.py:62
- <code>bisplev(X[ix, 0], X[ix, 1], self.tck)</code> -- polire/spline/bspline.py:74

**All bindings (1 unique):**
- <code>polire/spline/bspline.py</code> L2: <code>from scipy.interpolate import bisplev</code>

## Group 37: Polygon -> library/shapely (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from shapely.geometry.polygon import Polygon</code> @ polire/natural_neighbors/natural_neighbors.py:10 |
| Owner | shapely |
| Proposed GT | library / shapely |

**Representative expressions:**

- <code>Polygon(order_poly(self.vertices[region]))</code> -- polire/natural_neighbors/natural_neighbors.py:124
- <code>Polygon(order_poly(new))</code> -- polire/natural_neighbors/natural_neighbors.py:195

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L10: <code>from shapely.geometry.polygon import Polygon</code>

## Group 38: ((S - self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>((S - self._X) ** 2).sum(axis=1)</code> -- polire/nsgp/nsgp.py:65


## Group 39: (weights * self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>(weights * self.y[:, None]).sum(axis=0)</code> -- polire/idw/idw.py:83


## Group 40: NSGP -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Proposed GT | ? / ? |

**All expressions:**

- <code>NSGP()</code> -- tests/polire_basic.py:48


## Group 41: X1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/natural_neighbors/natural_neighbors.py:146 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X1.ravel()</code> -- polire/natural_neighbors/natural_neighbors.py:147

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L146: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 42: X1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/gp/gp.py:50 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X1.ravel()</code> -- polire/gp/gp.py:51

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L50: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 43: X1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/spatial/spatial.py:52 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X1.ravel()</code> -- polire/spatial/spatial.py:53

**All bindings (1 unique):**
- <code>polire/spatial/spatial.py</code> L52: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 44: X1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/custom/custom.py:52 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X1.ravel()</code> -- polire/custom/custom.py:53

**All bindings (1 unique):**
- <code>polire/custom/custom.py</code> L52: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 45: X1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/idw/idw.py:73 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X1.ravel()</code> -- polire/idw/idw.py:74

**All bindings (1 unique):**
- <code>polire/idw/idw.py</code> L73: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 46: X2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/natural_neighbors/natural_neighbors.py:146 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X2.ravel()</code> -- polire/natural_neighbors/natural_neighbors.py:147

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L146: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 47: X2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/gp/gp.py:50 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X2.ravel()</code> -- polire/gp/gp.py:51

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L50: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 48: X2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/spatial/spatial.py:52 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X2.ravel()</code> -- polire/spatial/spatial.py:53

**All bindings (1 unique):**
- <code>polire/spatial/spatial.py</code> L52: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 49: X2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/custom/custom.py:52 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X2.ravel()</code> -- polire/custom/custom.py:53

**All bindings (1 unique):**
- <code>polire/custom/custom.py</code> L52: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 50: X2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) np.meshgrid(x1, x2)</code> @ polire/idw/idw.py:73 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>X2.ravel()</code> -- polire/idw/idw.py:74

**All bindings (1 unique):**
- <code>polire/idw/idw.py</code> L73: <code>(tuple) np.meshgrid(x1, x2)</code>

## Group 51: arr -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter arr</code> @ polire/natural_neighbors/natural_neighbors.py:15 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>arr.tolist()</code> -- polire/natural_neighbors/natural_neighbors.py:16

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L15: <code>parameter arr</code>

## Group 52: bisplev(X[ix, 0], X[ix, 1], self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>bisplev(X[ix, 0], X[ix, 1], self.tck).item()</code> -- polire/spline/bspline.py:74


## Group 53: grid[0] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>grid[0].ravel()</code> -- polire/utils/gridding.py:67


## Group 54: grid[1] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>grid[1].ravel()</code> -- polire/utils/gridding.py:67


## Group 55: kernel -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | UNRESOLVED |
| Key binding | <code>kern_dict[self.__kernel_name]</code> @ polire/nsgp/nsgp.py:72 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>kernel.K(self._X[self.__close_locs[loc]])</code> -- polire/nsgp/nsgp.py:75

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L72: <code>kern_dict[self.__kernel_name]</code>

## Group 56: mask -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self.radius &gt;= dist</code> @ polire/spatial/spatial.py:63 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>mask.sum(axis=1)</code> -- polire/spatial/spatial.py:64

**All bindings (1 unique):**
- <code>polire/spatial/spatial.py</code> L63: <code>self.radius &gt;= dist</code>

## Group 57: pred_y -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self._predict_grid(x1lim, x2lim)</code> @ polire/base/base.py:117 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pred_y.reshape(self.resolution, self.resolution)</code> -- polire/base/base.py:118

**All bindings (1 unique):**
- <code>polire/base/base.py</code> L117: <code>self._predict_grid(x1lim, x2lim)</code>

## Group 58: predictions -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.model.predict(X)[0].reshape(len(x1), len(x2))</code> @ polire/gp/gp.py:53 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>predictions.ravel()</code> -- polire/gp/gp.py:55

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L53: <code>self.model.predict(X)[0].reshape(len(x1), len(x2))</code>

## Group 59: r.predict_grid((0, 3), (0, 3)) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>for target</code> @ usage3.py:22 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>r.predict_grid((0, 3), (0, 3)).reshape(100, 100)</code> -- usage3.py:32

**All bindings (1 unique):**
- <code>usage3.py</code> L22: <code>for target</code>

## Group 60: s_vec -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.__weight_func(s1)</code> @ polire/nsgp/nsgp.py:149 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>s_vec.sum()</code> -- polire/nsgp/nsgp.py:150

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L149: <code>self.__weight_func(s1)</code>

## Group 61: s_vec -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>self.__weight_func(s2)</code> @ polire/nsgp/nsgp.py:153 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>s_vec.sum()</code> -- polire/nsgp/nsgp.py:154

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L153: <code>self.__weight_func(s2)</code>

## Group 62: self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma).dot(self.__C_inv[j])</code> -- polire/nsgp/nsgp.py:171

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 63: self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma).dot(self.__C_inv[j]) -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma).dot(self.__C_inv[j]).dot(self.__c_mat</code> -- polire/nsgp/nsgp.py:171

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 64: self.__dmat[i] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:57 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__dmat[i].argsort()</code> -- polire/nsgp/nsgp.py:60

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L57: <code>parameter self</code>

## Group 65: self.__v_s2[:, i] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__v_s2[:, i].reshape(1, -1)</code> -- polire/nsgp/nsgp.py:187

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 66: self.__v_s2[:, j] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/nsgp/nsgp.py:122 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.__v_s2[:, j].reshape(1, -1)</code> -- polire/nsgp/nsgp.py:179

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L122: <code>parameter self</code>

## Group 67: self.model.predict(X)[0] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/gp/gp.py:42 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.model.predict(X)[0].reshape(len(x1), len(x2))</code> -- polire/gp/gp.py:53

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L42: <code>parameter self</code>

## Group 68: self.vertex_poly_map -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ polire/natural_neighbors/natural_neighbors.py:105 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.vertex_poly_map.pop(i, None)</code> -- polire/natural_neighbors/natural_neighbors.py:129

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L105: <code>parameter self</code>

## Group 69: self_y_local[:, None] -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self_y_local[:, None].repeat(lonlat.shape[0], 1)</code> -- polire/preprocessing/sptial_features.py:103


## Group 70: weights -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>1 / np.power(dist, self.exponent)</code> @ polire/idw/idw.py:82 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>weights.sum(axis=0)</code> -- polire/idw/idw.py:83

**All bindings (1 unique):**
- <code>polire/idw/idw.py</code> L82: <code>1 / np.power(dist, self.exponent)</code>

## Group 71: y -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>y.reshape(-1, 1)</code> @ polire/gp/gp.py:37 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>y.reshape(-1, 1)</code> -- polire/gp/gp.py:37

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L37: <code>y.reshape(-1, 1)</code>

## Group 72: ExpQuad -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import ExpQuad</code> @ polire/nsgp/nsgp.py:4 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>ExpQuad(input_dim=self._X.shape[1], active_dims=list(range(self._X.shape[1])), ARD=True)</code> -- polire/nsgp/nsgp.py:96

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L4: <code>from GPy.kern import ExpQuad</code>

## Group 73: GPRegression -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.models import GPRegression</code> @ polire/gp/gp.py:6 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>GPRegression(X, y, self.kernel)</code> -- polire/gp/gp.py:38

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L6: <code>from GPy.models import GPRegression</code>

## Group 74: Matern32 -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import Matern32</code> @ usage.py:6 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>Matern32(input_dim=2)</code> -- usage.py:31

**All bindings (1 unique):**
- <code>usage.py</code> L6: <code>from GPy.kern import Matern32</code>

## Group 75: Matern32 -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import Matern32</code> @ polire/nsgp/nsgp.py:4 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>Matern32(input_dim=self._X.shape[1], active_dims=list(range(self._X.shape[1])), ARD=True)</code> -- polire/nsgp/nsgp.py:81

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L4: <code>from GPy.kern import Matern32</code>

## Group 76: Matern52 -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import Matern52</code> @ polire/nsgp/nsgp.py:4 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>Matern52(input_dim=self._X.shape[1], active_dims=list(range(self._X.shape[1])), ARD=True)</code> -- polire/nsgp/nsgp.py:86

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L4: <code>from GPy.kern import Matern52</code>

## Group 77: RBF -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import RBF</code> @ polire/gp/gp.py:7 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>RBF(2, ARD=True)</code> -- polire/gp/gp.py:26

**All bindings (1 unique):**
- <code>polire/gp/gp.py</code> L7: <code>from GPy.kern import RBF</code>

## Group 78: RBF -> library/GPy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from GPy.kern import RBF</code> @ polire/nsgp/nsgp.py:4 |
| Owner | GPy |
| Proposed GT | library / GPy |

**Representative expressions:**

- <code>RBF(input_dim=self._X.shape[1], active_dims=list(range(self._X.shape[1])), ARD=True)</code> -- polire/nsgp/nsgp.py:91

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L4: <code>from GPy.kern import RBF</code>

## Group 79: plt -> library/matplotlib (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ polire/natural_neighbors/natural_neighbors.py:7 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.show()</code> -- polire/natural_neighbors/natural_neighbors.py:133

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L7: <code>import matplotlib.pyplot</code>

## Group 80: mask -> library/numpy (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>np.equal(X[i], self.X).all(axis=1)</code> @ polire/idw/idw.py:87 |
| Owner | numpy |
| Proposed GT | library / numpy |

**Representative expressions:**

- <code>mask.any()</code> -- polire/idw/idw.py:88

**All bindings (1 unique):**
- <code>polire/idw/idw.py</code> L87: <code>np.equal(X[i], self.X).all(axis=1)</code>

## Group 81: OrdinaryKriging -> library/pykrige (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from pykrige.ok import OrdinaryKriging</code> @ polire/kriging/kriging.py:6 |
| Owner | pykrige |
| Proposed GT | library / pykrige |

**Representative expressions:**

- <code>OrdinaryKriging(X[:, 0], X[:, 1], y, variogram_model=self.variogram_model, enable_plotting=self.plot</code> -- polire/kriging/kriging.py:74

**All bindings (1 unique):**
- <code>polire/kriging/kriging.py</code> L6: <code>from pykrige.ok import OrdinaryKriging</code>

## Group 82: UniversalKriging -> library/pykrige (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from pykrige.uk import UniversalKriging</code> @ polire/kriging/kriging.py:7 |
| Owner | pykrige |
| Proposed GT | library / pykrige |

**Representative expressions:**

- <code>UniversalKriging(X[:, 0], X[:, 1], y, variogram_model=self.variogram_model, enable_plotting=self.plo</code> -- polire/kriging/kriging.py:85

**All bindings (1 unique):**
- <code>polire/kriging/kriging.py</code> L7: <code>from pykrige.uk import UniversalKriging</code>

## Group 83: final_regions -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ polire/natural_neighbors/natural_neighbors.py:177 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>final_regions.append(i)</code> -- polire/natural_neighbors/natural_neighbors.py:181

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L177: <code>[]</code>

## Group 84: ixs -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ polire/utils/gridding.py:70 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>ixs.append(ix)</code> -- polire/utils/gridding.py:75

**All bindings (1 unique):**
- <code>polire/utils/gridding.py</code> L70: <code>[]</code>

## Group 85: new -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ polire/natural_neighbors/natural_neighbors.py:183 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>new.append(new_vertices[i])</code> -- polire/natural_neighbors/natural_neighbors.py:186

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L183: <code>[]</code>

## Group 86: results -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ polire/spline/bspline.py:72 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>results.append(interpolated_y)</code> -- polire/spline/bspline.py:77

**All bindings (1 unique):**
- <code>polire/spline/bspline.py</code> L72: <code>[]</code>

## Group 87: Voronoi -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.spatial import Voronoi</code> @ polire/natural_neighbors/natural_neighbors.py:6 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>Voronoi(X, incremental=True)</code> -- polire/natural_neighbors/natural_neighbors.py:111

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L6: <code>from scipy.spatial import Voronoi</code>

## Group 88: bisplrep -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.interpolate import bisplrep</code> @ polire/spline/bspline.py:2 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>bisplrep(X[:, 0], X[:, 1], y, kx=self.kx, ky=self.ky, s=self.s)</code> -- polire/spline/bspline.py:47

**All bindings (1 unique):**
- <code>polire/spline/bspline.py</code> L2: <code>from scipy.interpolate import bisplrep</code>

## Group 89: cdist -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.spatial.distance import cdist</code> @ polire/utils/distance.py:5 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>cdist(X1, X2)</code> -- polire/utils/distance.py:51

**All bindings (1 unique):**
- <code>polire/utils/distance.py</code> L5: <code>from scipy.spatial.distance import cdist</code>

## Group 90: curve_fit -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.optimize import curve_fit</code> @ polire/trend/trend.py:2 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>curve_fit(self.func, (X[:, 0], X[:, 1]), y)</code> -- polire/trend/trend.py:54

**All bindings (1 unique):**
- <code>polire/trend/trend.py</code> L2: <code>from scipy.optimize import curve_fit</code>

## Group 91: kdtree -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>spatial.KDTree(points)</code> @ polire/utils/gridding.py:69 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>kdtree.query(point)</code> -- polire/utils/gridding.py:74

**All bindings (1 unique):**
- <code>polire/utils/gridding.py</code> L69: <code>spatial.KDTree(points)</code>

## Group 92: least_squares -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.optimize import least_squares</code> @ polire/nsgp/nsgp.py:5 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>least_squares(__obfunc, np.ones(self._X.shape[1] + 1))</code> -- polire/nsgp/nsgp.py:104

**All bindings (1 unique):**
- <code>polire/nsgp/nsgp.py</code> L5: <code>from scipy.optimize import least_squares</code>

## Group 93: voronoi_plot_2d -> library/scipy (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from scipy.spatial import voronoi_plot_2d</code> @ polire/natural_neighbors/natural_neighbors.py:6 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>voronoi_plot_2d(self.voronoi)</code> -- polire/natural_neighbors/natural_neighbors.py:132

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L6: <code>from scipy.spatial import voronoi_plot_2d</code>

## Group 94: Point -> library/shapely (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from shapely.geometry import Point</code> @ polire/natural_neighbors/natural_neighbors.py:9 |
| Owner | shapely |
| Proposed GT | library / shapely |

**Representative expressions:**

- <code>Point(self.X[index])</code> -- polire/natural_neighbors/natural_neighbors.py:118

**All bindings (1 unique):**
- <code>polire/natural_neighbors/natural_neighbors.py</code> L9: <code>from shapely.geometry import Point</code>

## Group 95: GaussianProcessRegressor -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.gaussian_process import GaussianProcessRegressor</code> @ usage3.py:13 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>GaussianProcessRegressor(normalize_y=True, kernel=Matern())</code> -- usage3.py:28

**All bindings (1 unique):**
- <code>usage3.py</code> L13: <code>from sklearn.gaussian_process import GaussianProcessRegressor</code>

## Group 96: KNeighborsRegressor -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.neighbors import KNeighborsRegressor</code> @ usage3.py:12 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>KNeighborsRegressor(n_neighbors=3, weights='distance')</code> -- usage3.py:26

**All bindings (1 unique):**
- <code>usage3.py</code> L12: <code>from sklearn.neighbors import KNeighborsRegressor</code>

## Group 97: LinearRegression -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.linear_model import LinearRegression</code> @ usage3.py:11 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>LinearRegression(normalize=True)</code> -- usage3.py:25

**All bindings (1 unique):**
- <code>usage3.py</code> L11: <code>from sklearn.linear_model import LinearRegression</code>

## Group 98: LinearRegression -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.linear_model import LinearRegression</code> @ tests/polire_basic.py:15 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>LinearRegression()</code> -- tests/polire_basic.py:33

**All bindings (1 unique):**
- <code>tests/polire_basic.py</code> L15: <code>from sklearn.linear_model import LinearRegression</code>

## Group 99: Matern -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.gaussian_process.kernels import Matern</code> @ usage3.py:14 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>Matern()</code> -- usage3.py:28

**All bindings (1 unique):**
- <code>usage3.py</code> L14: <code>from sklearn.gaussian_process.kernels import Matern</code>

## Group 100: RandomForestRegressor -> library/sklearn (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from sklearn.ensemble import RandomForestRegressor</code> @ usage3.py:10 |
| Owner | sklearn |
| Proposed GT | library / sklearn |

**Representative expressions:**

- <code>RandomForestRegressor()</code> -- usage3.py:24

**All bindings (1 unique):**
- <code>usage3.py</code> L10: <code>from sklearn.ensemble import RandomForestRegressor</code>
