# polire — Needs Annotation (165 records)

These records do not yet have `verification_level` or
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| usage3.py:24:23 | `RandomForestRegressor()` |  /  | library / sklearn | - | - |  |
| usage3.py:25:23 | `LinearRegression(normalize=True)` |  /  | library / sklearn | - | - |  |
| usage3.py:26:23 | `KNeighborsRegressor(n_neighbors=3, weights='distance')` |  /  | library / sklearn | - | - |  |
| usage3.py:28:8 | `GaussianProcessRegressor(normalize_y=True, kernel=Matern())` |  /  | library / sklearn | - | - |  |
| usage3.py:28:58 | `Matern()` |  /  | library / sklearn | - | - |  |
| usage3.py:31:4 | `r.fit(X, y)` |  /  | local / local | - | - |  |
| usage3.py:32:8 | `r.predict_grid((0, 3), (0, 3))` |  /  | local / local | - | - |  |
| usage3.py:32:8 | `r.predict_grid((0, 3), (0, 3)).reshape(100, 100)` |  /  | local / local | - | - |  |
| usage.py:31:7 | `Matern32(input_dim=2)` |  /  | library / GPy | - | - |  |
| usage.py:39:8 | `r.fit(X, y)` |  /  | local / local | - | - |  |
| usage.py:40:17 | `r.predict_grid()` |  /  | local / local | - | - |  |
| usage.py:43:8 | `plt.title(r)` |  /  | library / matplotlib | - | - |  |
| usage.py:44:8 | `plt.show()` |  /  | library / matplotlib | - | - |  |
| usage.py:45:8 | `plt.close()` |  /  | library / matplotlib | - | - |  |
| usage.py:55:8 | `r.fit(X1, y1)` |  /  | local / local | - | - |  |
| usage.py:56:17 | `r.predict_grid()` |  /  | local / local | - | - |  |
| usage.py:59:8 | `plt.title(r)` |  /  | library / matplotlib | - | - |  |
| usage.py:60:8 | `plt.show()` |  /  | library / matplotlib | - | - |  |
| usage.py:61:8 | `plt.close()` |  /  | library / matplotlib | - | - |  |
| usage.py:67:8 | `r.fit(X, y)` |  /  | local / local | - | - |  |
| usage.py:79:17 | `r.predict(np.array(test_data))` |  /  | local / local | - | - |  |
| usage.py:90:4 | `nn.fit(X, y)` |  /  | local / local | - | - |  |
| usage.py:92:13 | `nn.predict(np.array(test_data))` |  /  | local / local | - | - |  |
| usage.py:99:4 | `nn.fit(X, y)` |  /  | local / local | - | - |  |
| usage.py:100:13 | `nn.predict_grid()` |  /  | local / local | - | - |  |
| usage.py:103:4 | `plt.title(nn)` |  /  | library / matplotlib | - | - |  |
| usage.py:104:4 | `plt.show()` |  /  | library / matplotlib | - | - |  |
| usage.py:105:4 | `plt.close()` |  /  | library / matplotlib | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:16:24 | `arr.tolist()` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:111:23 | `Voronoi(X, incremental=True)` |  /  | library / scipy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:118:20 | `Point(self.X[index])` |  /  | library / shapely | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:124:20 | `Polygon(order_poly(self.vertices[region]))` |  /  | library / shapely | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:129:16 | `self.vertex_poly_map.pop(i, None)` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:132:12 | `voronoi_plot_2d(self.voronoi)` |  /  | library / scipy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:133:12 | `plt.show()` |  /  | library / matplotlib | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:147:15 | `self._predict(np.array([X1.ravel(), X2.ravel()]).T)` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:147:39 | `X1.ravel()` |  /  | library / numpy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:147:51 | `X2.ravel()` |  /  | library / numpy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:168:16 | `self._fit(self.X, self.y)` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:171:16 | `vor.add_points(np.array([X[index]]))` |  /  | library / scipy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:172:16 | `vor.close()` |  /  | library / scipy | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:181:24 | `final_regions.append(i)` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:186:24 | `new.append(new_vertices[i])` |  /  | local / local | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:195:30 | `Polygon(order_poly(new))` |  /  | library / shapely | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:199:23 | `new_polygon.intersects(self.vertex_poly_map[i])` |  /  | library / shapely | - | - |  |
| polire/natural_neighbors/natural_neighbors.py:201:28 | `new_polygon.intersection(self.vertex_poly_map[i])` |  /  | library / shapely | - | - |  |
| polire/utils/distance.py:51:11 | `cdist(X1, X2)` |  /  | library / scipy | - | - |  |
| polire/utils/gridding.py:33:12 | `y.min()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:34:12 | `y.max()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:35:12 | `x.min()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:36:12 | `x.max()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:67:9 | `grid[0].ravel()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:67:26 | `grid[1].ravel()` |  /  | local / local | - | - |  |
| polire/utils/gridding.py:74:16 | `kdtree.query(point)` |  /  | library / scipy | - | - |  |
| polire/utils/gridding.py:75:8 | `ixs.append(ix)` |  /  | local / local | - | - |  |
| polire/spline/bspline.py:47:19 | `bisplrep(X[:, 0], X[:, 1], y, kx=self.kx, ky=self.ky, s=self.s)` |  /  | library / scipy | - | - |  |
| polire/spline/bspline.py:62:15 | `bisplev(np.linspace(x1min, x1max, self.resolution), np.linspace(x2m...` |  /  | library / scipy | - | - |  |
| polire/spline/bspline.py:74:29 | `bisplev(X[ix, 0], X[ix, 1], self.tck)` |  /  | library / scipy | - | - |  |
| polire/spline/bspline.py:74:29 | `bisplev(X[ix, 0], X[ix, 1], self.tck).item()` |  /  | library / scipy | - | - |  |
| polire/spline/bspline.py:77:12 | `results.append(interpolated_y)` |  /  | local / local | - | - |  |
| polire/gp/gp.py:26:15 | `RBF(2, ARD=True)` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:37:16 | `y.reshape(-1, 1)` |  /  | local / local | - | - |  |
| polire/gp/gp.py:38:21 | `GPRegression(X, y, self.kernel)` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:39:8 | `self.model.optimize_restarts(n_restarts, verbose=verbose)` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:51:45 | `X1.ravel()` |  /  | library / numpy | - | - |  |
| polire/gp/gp.py:51:57 | `X2.ravel()` |  /  | library / numpy | - | - |  |
| polire/gp/gp.py:53:22 | `self.model.predict(X)[0].reshape(len(x1), len(x2))` |  /  | local / local | - | - |  |
| polire/gp/gp.py:53:22 | `self.model.predict(X)` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:55:15 | `predictions.ravel()` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:61:32 | `self.model.predict(X)` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:63:19 | `predictions.ravel()` |  /  | library / GPy | - | - |  |
| polire/gp/gp.py:65:19 | `predictions.ravel()` |  /  | library / GPy | - | - |  |
| polire/preprocessing/sptial_features.py:93:18 | `self.distance(lonlat, self_lonlat)` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:95:22 | `dst.argsort()` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:97:22 | `dst.argsort()` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:103:19 | `self_y_local[:, None].repeat(lonlat.shape[0], 1)` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:114:20 | `model.fit(self_lonlat[idx[i]], self_y_local[idx[i]])` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:115:27 | `model.predict(lonlat[i][None, :])` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:130:8 | `self.fit(X, y)` |  /  | local / local | - | - |  |
| polire/preprocessing/sptial_features.py:131:15 | `self.transform(X)` |  /  | local / local | - | - |  |
| polire/spatial/spatial.py:53:15 | `self._predict(np.asarray([X1.ravel(), X2.ravel()]).T)` |  /  | local / local | - | - |  |
| polire/spatial/spatial.py:53:41 | `X1.ravel()` |  /  | library / numpy | - | - |  |
| polire/spatial/spatial.py:53:53 | `X2.ravel()` |  /  | library / numpy | - | - |  |
| polire/spatial/spatial.py:59:15 | `self._average(X)` |  /  | local / local | - | - |  |
| polire/spatial/spatial.py:62:15 | `self.distance(X, self.X)` |  /  | local / local | - | - |  |
| polire/spatial/spatial.py:64:15 | `(self.y * mask).sum(axis=1)` |  /  | local / local | - | - |  |
| polire/spatial/spatial.py:64:45 | `mask.sum(axis=1)` |  /  | local / local | - | - |  |
| polire/custom/custom.py:38:8 | `self.reg.fit(X, y)` |  /  | local / local | - | - |  |
| polire/custom/custom.py:53:15 | `self.reg.predict(np.asarray([X1.ravel(), X2.ravel()]).T)` |  /  | local / local | - | - |  |
| polire/custom/custom.py:53:44 | `X1.ravel()` |  /  | library / numpy | - | - |  |
| polire/custom/custom.py:53:56 | `X2.ravel()` |  /  | library / numpy | - | - |  |
| polire/custom/custom.py:59:15 | `self.reg.predict(X)` |  /  | local / local | - | - |  |
| polire/idw/idw.py:74:15 | `self._predict(np.array([X1.ravel(), X2.ravel()]).T)` |  /  | local / local | - | - |  |
| polire/idw/idw.py:74:39 | `X1.ravel()` |  /  | library / numpy | - | - |  |
| polire/idw/idw.py:74:51 | `X2.ravel()` |  /  | library / numpy | - | - |  |
| polire/idw/idw.py:81:15 | `self.distance(self.X, X)` |  /  | local / local | - | - |  |
| polire/idw/idw.py:83:17 | `(weights * self.y[:, None]).sum(axis=0)` |  /  | local / local | - | - |  |
| polire/idw/idw.py:83:59 | `weights.sum(axis=0)` |  /  | local / local | - | - |  |
| polire/idw/idw.py:88:15 | `mask.any()` |  /  | library / numpy | - | - |  |
| polire/idw/idw.py:89:28 | `(self.y * mask).sum()` |  /  | local / local | - | - |  |
| polire/kriging/kriging.py:74:22 | `OrdinaryKriging(X[:, 0], X[:, 1], y, variogram_model=self.variogram...` |  /  | library / pykrige | - | - |  |
| polire/kriging/kriging.py:85:22 | `UniversalKriging(X[:, 0], X[:, 1], y, variogram_model=self.variogra...` |  /  | library / pykrige | - | - |  |
| polire/kriging/kriging.py:109:41 | `self.ok.execute(style='grid', xpoints=x1, ypoints=x2)` |  /  | library / pykrige | - | - |  |
| polire/kriging/kriging.py:114:41 | `self.uk.execute(style='grid', xpoints=x1, ypoints=x2)` |  /  | library / pykrige | - | - |  |
| polire/kriging/kriging.py:124:41 | `self.ok.execute(style='points', xpoints=X[:, 0], ypoints=X[:, 1])` |  /  | library / pykrige | - | - |  |
| polire/kriging/kriging.py:129:41 | `self.uk.execute(style='points', xpoints=X[:, 0], ypoints=X[:, 1])` |  /  | library / pykrige | - | - |  |
| polire/base/base.py:50:15 | `self._fit(X, y, **kwargs)` |  /  | local / local | - | - |  |
| polire/base/base.py:80:15 | `self._predict(X, **kwargs)` |  /  | local / local | - | - |  |
| polire/base/base.py:117:17 | `self._predict_grid(x1lim, x2lim)` |  /  | local / local | - | - |  |
| polire/base/base.py:118:15 | `pred_y.reshape(self.resolution, self.resolution)` |  /  | local / local | - | - |  |
| polire/trend/trend.py:54:31 | `curve_fit(self.func, (X[:, 0], X[:, 1]), y)` |  /  | library / scipy | - | - |  |
| polire/trend/trend.py:69:15 | `self.func((X1, X2), *self.popt)` |  /  | local / local | - | - |  |
| polire/trend/trend.py:76:15 | `self.func((x1, x2), *self.popt)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:58:8 | `self.__calculate_dmat()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:60:12 | `self.__dmat[i].argsort()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:65:42 | `((S - self._X) ** 2).sum(axis=1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:75:24 | `kernel.K(self._X[self.__close_locs[loc]])` |  /  | unknown / unknown | - | - |  |
| polire/nsgp/nsgp.py:81:19 | `Matern32(input_dim=self._X.shape[1], active_dims=list(range(self._X...` |  /  | library / GPy | - | - |  |
| polire/nsgp/nsgp.py:86:19 | `Matern52(input_dim=self._X.shape[1], active_dims=list(range(self._X...` |  /  | library / GPy | - | - |  |
| polire/nsgp/nsgp.py:91:19 | `RBF(input_dim=self._X.shape[1], active_dims=list(range(self._X.shap...` |  /  | library / GPy | - | - |  |
| polire/nsgp/nsgp.py:96:21 | `ExpQuad(input_dim=self._X.shape[1], active_dims=list(range(self._X....` |  /  | library / GPy | - | - |  |
| polire/nsgp/nsgp.py:104:17 | `least_squares(__obfunc, np.ones(self._X.shape[1] + 1))` |  /  | library / scipy | - | - |  |
| polire/nsgp/nsgp.py:116:25 | `job.map(self._model, list(range(self._X.shape[0])))` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:117:23 | `job.map(self._c_inv, self.__kernels)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:118:8 | `job.close()` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:149:20 | `self.__weight_func(s1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:150:42 | `s_vec.sum()` |  /  | library / numpy | - | - |  |
| polire/nsgp/nsgp.py:153:24 | `self.__weight_func(s2)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:154:46 | `s_vec.sum()` |  /  | library / numpy | - | - |  |
| polire/nsgp/nsgp.py:156:43 | `self.__kernels[i](S1, self._X)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:157:43 | `self.__kernels[i](self._X, S2)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:158:45 | `self.__kernels[i](S1, S2)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:162:43 | `self.__kernels[i](S1, self._X)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:164:45 | `self.__kernels[i](S1)` |  /  | library / multiprocessing | - | - |  |
| polire/nsgp/nsgp.py:171:20 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i])` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:171:20 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:171:20 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma).dot(...` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:171:20 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self._Gamma).dot(...` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:177:20 | `self.__v_s1[:, i].reshape(-1, 1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:177:20 | `self.__v_s1[:, i].reshape(-1, 1).dot(self.__v_s2[:, j].reshape(1, -1))` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:179:25 | `self.__v_s2[:, j].reshape(1, -1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:185:16 | `self.__v_s1[:, i].reshape(-1, 1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:185:16 | `self.__v_s1[:, i].reshape(-1, 1).dot(self.__v_s2[:, i].reshape(1, -1))` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:187:21 | `self.__v_s2[:, i].reshape(1, -1)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:190:18 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i])` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:190:18 | `self.__c_mat_s1[i, :, :].dot(self.__C_inv[i]).dot(self.__c_mat_s2[i...` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:222:28 | `self.__get_close_locs()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:223:8 | `self.__learnLocal()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:232:42 | `self._Kernel(self._X, self._X)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:233:18 | `self._Kernel(X, self._X)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:235:12 | `KX_test.dot(self._KX_inv)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:235:12 | `KX_test.dot(self._KX_inv).dot(self._y - self._y.mean())` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:235:52 | `self._y.mean()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:236:14 | `self._y.mean()` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:239:23 | `self._Kernel(X, X)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:239:44 | `KX_test.dot(self._KX_inv)` |  /  | local / local | - | - |  |
| polire/nsgp/nsgp.py:239:44 | `KX_test.dot(self._KX_inv).dot(KX_test.T)` |  /  | local / local | - | - |  |
| tests/polire_basic.py:39:4 | `model.fit(X, y)` |  /  | local / local | - | - |  |
| tests/polire_basic.py:40:12 | `model.predict(X_new)` |  /  | local / local | - | - |  |
| tests/polire_basic.py:33:27 | `LinearRegression()` |  /  | library / sklearn | - | - |  |
| tests/polire_basic.py:48:12 | `NSGP()` |  /  | unknown / unknown | - | - |  |
| tests/polire_basic.py:50:4 | `model.fit(X, y, **{'ECM': X @ X.T})` |  /  | unknown / unknown | - | - |  |
| tests/polire_basic.py:51:12 | `model.predict(X_new)` |  /  | unknown / unknown | - | - |  |
| tests/polire_basic.py:54:11 | `y_new.sum()` |  /  | unknown / unknown | - | - |  |
| tests/polire_basic.py:54:26 | `y_new.sum()` |  /  | unknown / unknown | - | - |  |
