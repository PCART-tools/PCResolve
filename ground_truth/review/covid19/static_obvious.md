# covid19 — static_obvious (67 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| script.py:3:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:18:7 | `pd.read_csv('data/covid19.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| script.py:42:8 | `pd.unique(data['Date'])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| script.py:43:12 | `pd.unique(data['Country/Region'])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| script.py:56:4 | `world_cases.append(total_confirmed)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:57:4 | `world_deaths.append(total_deaths)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:58:4 | `world_recovered.append(total_recovered)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:61:16 | `np.array([i for i in range(len(dates))])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:61:16 | `np.array([i for i in range(len(dates))]).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:61:37 | `range(len(dates))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:61:43 | `len(dates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:63:14 | `np.array(world_cases)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:63:14 | `np.array(world_cases).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:65:15 | `np.array(world_deaths)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:65:15 | `np.array(world_deaths).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:67:18 | `np.array(world_recovered)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:67:18 | `np.array(world_recovered).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:71:11 | `np.array([i for i in range(len(dates) + day_span)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:71:11 | `np.array([i for i in range(len(dates) + day_span)]).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| script.py:71:32 | `range(len(dates) + day_span)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:71:38 | `len(dates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:73:21 | `datetime.datetime.strptime('1/22/2020', '%m/%d/%Y')` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| script.py:75:9 | `range(len(forecast))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:75:15 | `len(forecast)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:76:8 | `forecast_dates.append((start_date + datetime.timedelta(days=i)).str...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:76:44 | `datetime.timedelta(days=i)` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| script.py:79:75 | `train_test_split(epidemic_days, world_cases, test_size=0.25, shuffl...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:81:16 | `SVR(shrinking=True, kernel='poly', gamma=0.01, epsilon=1, degree=5,...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:86:0 | `plt.plot(y_test_confirmed)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:87:0 | `plt.plot(svm_test_pred)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:88:0 | `plt.legend(['Data', 'Forecast'])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:89:0 | `print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:89:14 | `mean_absolute_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:90:0 | `print('MSE:', mean_squared_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:90:13 | `mean_squared_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:92:0 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:95:63 | `train_test_split(epidemic_days, world_deaths, test_size=0.25, shuff...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:97:13 | `SVR(shrinking=True, kernel='poly', gamma=0.01, epsilon=1, degree=5,...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:102:0 | `plt.plot(y_test_deaths)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:103:0 | `plt.plot(svm_test_pred)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:104:0 | `plt.legend(['Data', 'Forecast'])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:105:0 | `print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:105:14 | `mean_absolute_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:106:0 | `print('MSE:', mean_squared_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:106:13 | `mean_squared_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:108:0 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:111:75 | `train_test_split(epidemic_days, world_recovered, test_size=0.25, sh...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:113:16 | `SVR(shrinking=True, kernel='poly', gamma=0.01, epsilon=1, degree=5,...` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:118:0 | `plt.plot(y_test_recovered)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:119:0 | `plt.plot(svm_test_pred)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:120:0 | `plt.legend(['Data', 'Forecast'])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:121:0 | `print('MAE:', mean_absolute_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:121:14 | `mean_absolute_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:122:0 | `print('MSE:', mean_squared_error(svm_test_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:122:13 | `mean_squared_error(svm_test_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:124:0 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:127:7 | `PolynomialFeatures(degree=3)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:132:16 | `PolynomialFeatures(degree=4)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:138:15 | `LinearRegression(normalize=True, fit_intercept=False)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:142:0 | `print('MAE:', mean_absolute_error(test_linear_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:142:14 | `mean_absolute_error(test_linear_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:143:0 | `print('MSE:', mean_squared_error(test_linear_pred, y_test_confirmed))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| script.py:143:13 | `mean_squared_error(test_linear_pred, y_test_confirmed)` | library / sklearn | library / sklearn | direct_import | static_obvious | v: direct import-backed API call |
| script.py:145:0 | `plt.plot(y_test_confirmed)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:146:0 | `plt.plot(test_linear_pred)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:147:0 | `plt.legend(['Test Data', 'Polynomial Regression Predictions'])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| script.py:148:0 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
