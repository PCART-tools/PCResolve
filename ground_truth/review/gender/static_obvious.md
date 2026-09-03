# gender — static_obvious (10 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| models.py:10:9 | `dict(linear_reg=LinearRegression(normalize=True), decision_tree=Dec...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| models.py:11:15 | `LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:12:18 | `DecisionTreeRegressor(random_state=1, max_depth=10, min_samples_spl...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:13:13 | `AdaBoostRegressor(random_state=1)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:14:14 | `GradientBoostingRegressor(random_state=1)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:15:18 | `RandomForestRegressor(random_state=1)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:16:16 | `ExtraTreesRegressor(bootstrap=False, max_features=0.750000000000000...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:21:17 | `ExtraTreesRegressor(bootstrap=True, max_features=0.6000000000000001...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:25:8 | `SVR(gamma=9e-05, C=10, epsilon=0.2)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| models.py:26:12 | `XGBRegressor(max_depth=9, learning_rate=0.013, n_estimators=2000, s...` | library / xgboost | library / xgboost | direct_import | static_obvious | v: direct import-backed API call |
