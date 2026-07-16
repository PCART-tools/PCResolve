# polire — static_obvious (256 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| usage3.py:4:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:19:4 | `np.array(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:20:4 | `np.array(y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:23:4 | `CustomInterpolator(xgboost.XGBRegressor())` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage3.py:23:23 | `xgboost.XGBRegressor()` | library / xgboost | library / xgboost | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:24:4 | `CustomInterpolator(RandomForestRegressor())` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage3.py:25:4 | `CustomInterpolator(LinearRegression(normalize=True))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage3.py:26:4 | `CustomInterpolator(KNeighborsRegressor(n_neighbors=3, weights='dist...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage3.py:27:4 | `CustomInterpolator(GaussianProcessRegressor(normalize_y=True, kerne...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage3.py:33:4 | `sns.heatmap(Z)` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:34:4 | `plt.title(r)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:35:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| usage3.py:36:4 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:22:4 | `np.array(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:23:4 | `np.array(y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:25:4 | `Random()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:26:4 | `SpatialAverage()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:27:4 | `Spline(kx=1, ky=1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:28:4 | `Trend()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:29:4 | `IDW(coordinate_type='Geographic')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:30:4 | `Kriging()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:31:4 | `GP(Matern32(input_dim=2))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:37:4 | `print('\nTesting on small dataset')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:42:8 | `sns.heatmap(Z)` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:46:4 | `print('\nTesting completed on a small dataset\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:48:4 | `print('\nTesting on a reasonable dataset')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:50:9 | `pd.read_csv('tests/data/30-03-18.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:51:9 | `np.array(df[['longitude', 'latitude']])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:52:9 | `np.array(df['value'])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:58:8 | `sns.heatmap(Z)` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:79:27 | `np.array(test_data)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:80:8 | `print(r)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:81:8 | `print(y_pred)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:85:4 | `print('\nNatural Neighbors - Point Wise')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:86:9 | `NaturalNeighbor()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:87:9 | `pd.read_csv('tests/data/30-03-18.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:88:8 | `np.array(df[['longitude', 'latitude']])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:89:8 | `np.array(df['value'])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:92:24 | `np.array(test_data)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:93:4 | `print(y_pred)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:95:4 | `print('\nNatural Neighbors - Entire Grid')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:98:9 | `NaturalNeighbor()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:101:4 | `print(y_pred)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:102:4 | `sns.heatmap(y_pred)` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| usage.py:109:4 | `print('Testing Gridded Interpolation')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:110:4 | `test_grid()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:111:4 | `print('\nTesting Pointwise Interpolation')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:112:4 | `test_point()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| usage.py:113:4 | `print('\nTesting Natural Neighbors')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| usage.py:114:4 | `test_nn()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| setup.py:3:5 | `open('requirements.txt')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| setup.py:4:19 | `f.read()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| setup.py:4:19 | `f.read().splitlines()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| setup.py:6:0 | `setup(packages=find_packages(exclude=['docs']), python_requires='>=...` | library / setuptools | library / setuptools | direct_import | static_obvious | v: direct import-backed API call |
| setup.py:7:13 | `find_packages(exclude=['docs'])` | library / setuptools | library / setuptools | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:16:11 | `list(row)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:20:9 | `np.where(arr[:, 0] == row[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:21:9 | `np.where(arr[:, 1] == row[1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:22:12 | `np.intersect1d(t1, t2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:43:13 | `np.mean(vertices[:, 0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:44:13 | `np.mean(vertices[:, 1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:50:15 | `atan2(x[0] - mean_x, x[1] - mean_y)` | library / math | library / math | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:52:11 | `sorted(vertices, key=condition)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:91:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:91:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:101:12 | `dict()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:114:46 | `range(len(X))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:114:52 | `len(X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:116:17 | `range(len(self.X))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:116:23 | `len(self.X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:117:20 | `np.where(self.voronoi.point_region == i)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:124:28 | `order_poly(self.vertices[region])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/natural_neighbors/natural_neighbors.py:127:17 | `range(len(self.vertex_poly_map))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:127:23 | `len(self.vertex_poly_map)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:144:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:145:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:146:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:147:29 | `np.array([X1.ravel(), X2.ravel()])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:155:17 | `np.zeros(len(X))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:155:26 | `len(X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:159:21 | `range(len(X))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:159:27 | `len(X)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:160:15 | `is_row_in_array(X[index], self.X)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/natural_neighbors/natural_neighbors.py:161:22 | `get_index(X[index], self.X)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/natural_neighbors/natural_neighbors.py:171:31 | `np.array([X[index]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:184:25 | `range(len(new_vertices))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:184:31 | `len(new_vertices)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:187:22 | `np.array(new)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:188:19 | `len(new)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/natural_neighbors/natural_neighbors.py:195:38 | `order_poly(new)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/natural_neighbors/natural_neighbors.py:204:29 | `np.array([self.y[i] * weights[i] for i in weights])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/natural_neighbors/natural_neighbors.py:204:29 | `np.array([self.y[i] * weights[i] for i in weights]).sum()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:31:29 | `map(np.radians, [X1[:, 0, None], X1[:, 1, None], X2[:, 0, None], X2...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/utils/distance.py:40:8 | `np.sin(dlat / 2.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:41:10 | `np.cos(lat1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:41:25 | `np.cos(lat2.T)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:41:42 | `np.sin(dlon / 2.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:44:12 | `np.arcsin(np.sqrt(a))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/distance.py:44:22 | `np.sqrt(a)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:37:12 | `np.linspace(x_min, x_max, res)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:38:12 | `np.linspace(y_min, y_max, res)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:39:13 | `np.meshgrid(x_arr, y_arr)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:66:13 | `np.asarray([grid[0].ravel(), grid[1].ravel()])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:69:13 | `spatial.KDTree(points)` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| polire/utils/gridding.py:72:20 | `range(X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/spline/bspline.py:35:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/spline/bspline.py:35:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/spline/bspline.py:63:12 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spline/bspline.py:64:12 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spline/bspline.py:73:18 | `range(X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/spline/bspline.py:79:15 | `np.array(results)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:28:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/gp/gp.py:28:8 | `super().__init__()` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/gp/gp.py:35:8 | `np.random.seed(random_state)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:36:11 | `len(y.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/gp/gp.py:47:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:48:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:50:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:51:12 | `np.array([(i, j) for (i, j) in zip(X1.ravel(), X2.ravel())])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/gp/gp.py:51:41 | `zip(X1.ravel(), X2.ravel())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/gp/gp.py:53:55 | `len(x1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/gp/gp.py:53:64 | `len(x2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/preprocessing/sptial_features.py:39:18 | `NotImplementedError('"' + self.coordinate_type + '" is not implemen...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/preprocessing/sptial_features.py:73:18 | `Exception("Not fitted yet. first call the 'fit' method")` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/preprocessing/sptial_features.py:76:11 | `np.all(X == self.X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:80:12 | `np.empty((X.shape[0], X.shape[1] - 3 + self.n_closest * 2 + self.idw))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:85:17 | `np.unique(X[:, 2])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:100:21 | `np.arange(lonlat.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:105:22 | `np.arange(lonlat.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:111:28 | `IDW(exponent=self.idw_exponent)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/preprocessing/sptial_features.py:118:21 | `np.apply_along_axis(for_each_row, axis=1, arr=np.arange(lonlat.shap...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:121:24 | `np.arange(lonlat.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:121:24 | `np.arange(lonlat.shape[0]).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:123:26 | `np.concatenate([X_local[:, 3:], f1, f2, f3], axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/preprocessing/sptial_features.py:125:26 | `np.concatenate([X_local[:, 3:], f1, f2], axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spatial/spatial.py:22:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/spatial/spatial.py:22:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/spatial/spatial.py:29:18 | `NotImplementedError('Only Geographic and Euclidean Coordinates are ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/spatial/spatial.py:50:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spatial/spatial.py:51:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spatial/spatial.py:52:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/spatial/spatial.py:53:29 | `np.asarray([X1.ravel(), X2.ravel()])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/custom/custom.py:31:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/custom/custom.py:31:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/custom/custom.py:50:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/custom/custom.py:51:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/custom/custom.py:52:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/custom/custom.py:53:32 | `np.asarray([X1.ravel(), X2.ravel()])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:42:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/idw/idw.py:42:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/idw/idw.py:53:18 | `NotImplementedError('Only Geographic and Euclidean Coordinates are ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/idw/idw.py:71:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:72:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:73:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:74:29 | `np.array([X1.ravel(), X2.ravel()])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:82:22 | `np.power(dist, self.exponent)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:86:17 | `range(X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/idw/idw.py:87:19 | `np.equal(X[i], self.X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/idw/idw.py:87:19 | `np.equal(X[i], self.X).all(axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/kriging/kriging.py:53:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/kriging/kriging.py:53:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/kriging/kriging.py:94:18 | `ValueError('Choose either Universal or Ordinary - Given argument is...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/kriging/kriging.py:105:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/kriging/kriging.py:106:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/kriging/kriging.py:143:12 | `print('Variance not asked for, while instantiating the object. Retu...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:35:15 | `len(X.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:35:72 | `str(X.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:39:15 | `len(y.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:46:23 | `min(X[:, 0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:47:23 | `max(X[:, 0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:48:23 | `min(X[:, 1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:49:23 | `max(X[:, 1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:71:15 | `len(X.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/base/base.py:71:72 | `str(X.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/trend/polynomials.py:35:14 | `NotImplementedError(f'{order} order polynomial needs to be defined ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/trend/trend.py:38:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/trend/trend.py:38:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/trend/trend.py:41:11 | `_create_polynomial(order)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/trend/trend.py:42:24 | `_create_polynomial(order)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/trend/trend.py:47:22 | `ValueError('Arguments passed are not valid')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/trend/trend.py:66:13 | `np.linspace(x1min, x1max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/trend/trend.py:67:13 | `np.linspace(x2min, x2max, self.resolution)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/trend/trend.py:68:17 | `np.meshgrid(x1, x2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/random/random.py:16:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/random/random.py:16:8 | `super().__init__(resolution, coordinate_type)` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/random/random.py:22:20 | `max(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/random/random.py:23:20 | `min(y)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/random/random.py:30:15 | `np.random.uniform(low=self.ymin, high=self.ymax, size=(self.resolut...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/random/random.py:40:15 | `np.random.uniform(low=self.ymin, high=self.ymax, size=X.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:27:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:27:8 | `super().__init__()` | python / python | local / local | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:51:22 | `np.zeros((self._X.shape[0], self._X.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:52:17 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:53:21 | `range(i, self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:54:36 | `np.linalg.norm(self._X[i] - self._X[j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:61:21 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:65:15 | `np.exp(-(1 / self.__eta) * ((S - self._X) ** 2).sum(axis=1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:69:31 | `np.ix_(sj, sj)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:76:20 | `__D_z(self.__close_locs[loc])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/nsgp/nsgp.py:77:19 | `np.sum(term ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:83:28 | `list(range(self._X.shape[1]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:83:33 | `range(self._X.shape[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:88:28 | `list(range(self._X.shape[1]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:88:33 | `range(self._X.shape[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:93:28 | `list(range(self._X.shape[1]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:93:33 | `range(self._X.shape[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:98:28 | `list(range(self._X.shape[1]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:98:33 | `range(self._X.shape[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:104:41 | `np.ones(self._X.shape[1] + 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:110:15 | `np.linalg.pinv(kern_func(self._X))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:110:30 | `kern_func(self._X)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| polire/nsgp/nsgp.py:115:14 | `mp.Pool()` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:116:46 | `list(range(self._X.shape[0]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:116:51 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:128:11 | `np.all(S1 == S2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:136:22 | `np.zeros((S1.shape[0], self._X.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:137:22 | `np.zeros((S2.shape[0], self._X.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:138:26 | `np.zeros((self._X.shape[0], S1.shape[0], self._X.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:141:26 | `np.zeros((self._X.shape[0], self._X.shape[0], S2.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:144:28 | `np.zeros((self._X.shape[0], S1.shape[0], S2.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:148:23 | `enumerate(S1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:152:27 | `enumerate(S2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:155:21 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:161:21 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:167:21 | `np.zeros((S1.shape[0], S2.shape[0]), dtype='float64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:168:17 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:169:21 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:182:22 | `np.zeros((S1.shape[0], S2.shape[0]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:183:17 | `range(self._X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:184:27 | `np.sqrt(self.__v_s1[:, i].reshape(-1, 1).dot(self.__v_s2[:, i].resh...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:204:15 | `type(self._Gamma)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:204:36 | `type(np.zeros((1, 1)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:205:12 | `np.zeros((1, 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| polire/nsgp/nsgp.py:209:14 | `str(X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:211:14 | `str(X.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| polire/nsgp/nsgp.py:232:27 | `np.linalg.pinv(self._Kernel(self._X, self._X))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:17:4 | `np.random.rand(20, 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:18:4 | `np.random.rand(20)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:20:8 | `np.random.rand(40, 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:38:11 | `time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:43:4 | `print('Passed', 'Time:', np.round(time() - init, 3), 'seconds')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/polire_basic.py:43:29 | `np.round(time() - init, 3)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:43:38 | `time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:23:1 | `pytest.mark.parametrize('model', [IDW(), Spline(), Trend(), Kriging...` | library / pytest | library / pytest | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:26:8 | `IDW()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:27:8 | `Spline()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:28:8 | `Trend()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:30:8 | `Kriging()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:31:8 | `NaturalNeighbor()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:32:8 | `SpatialAverage()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:33:8 | `CustomInterpolator(LinearRegression())` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/polire_basic.py:49:11 | `time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:55:4 | `print('Passed', 'Time:', np.round(time() - init, 3), 'seconds')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/polire_basic.py:55:29 | `np.round(time() - init, 3)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:55:38 | `time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| tests/polire_basic.py:46:1 | `pytest.mark.skip(reason='Temporarily disabled')` | library / pytest | library / pytest | direct_import | static_obvious | v: direct import-backed API call |
