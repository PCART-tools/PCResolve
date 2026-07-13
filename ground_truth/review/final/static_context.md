# final — static_context (166 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| final.py:115:0 | `ts_df.head()` | library / pandas | library / pandas | direct_import | static_context | v: ts_df.head() -- ts_df from ts_bee_prep() returns DataFrame; .head is pandas |
| final.py:172:0 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .show is matplotlib |
| final.py:181:0 | `plt.figure(figsize=[16, 9])` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .figure is matplotlib |
| final.py:183:0 | `sns.lmplot(x='colonies_lost', y='beekeeper_colony_ratio', data=trai...` | library / seaborn | library / seaborn | transitive_method | static_context | v: import seaborn as sns; .lmplot is seaborn function |
| final.py:185:0 | `plt.xlim([0, 4000])` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .xlim is matplotlib |
| final.py:187:0 | `plt.ylim([0, 100])` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .ylim is matplotlib |
| final.py:189:0 | `plt.title('Does the number of colonies lost increase as the beekeep...` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .title is matplotlib |
| final.py:190:0 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .show is matplotlib |
| final.py:207:10 | `stats.pearsonr(train.beekeeper_colony_ratio, train.colonies_lost)` | library / scipy | library / scipy | direct_import | static_context | v: from scipy import stats; .pearsonr is scipy function |
| final.py:232:0 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .show is matplotlib |
| final.py:246:0 | `plt.xlabel('Net colony gain / loss')` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .xlabel is matplotlib |
| final.py:247:0 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: import matplotlib.pyplot as plt; .show is matplotlib |
| final.py:280:13 | `stats.levene(train.colonies_lost[train.season == 'summer'], train.c...` | library / scipy | library / scipy | direct_import | static_context | v: from scipy import stats; .levene is scipy function |
| final.py:303:7 | `stats.ttest_ind(winter_loss, summer_loss, equal_var=False)` | library / scipy | library / scipy | direct_import | static_context | v: from scipy import stats; .ttest_ind is scipy function |
| final.py:359:45 | `model.scale_data(train, validate, test, columns)` | local / local | local / local | local_call | static_context | v: model.scale_data -- local function from regression_models import |
| wrangle.py:23:9 | `df.drop(columns=['Column name as written in R Script', 'State abbre...` | library / pandas | library / pandas | direct_import | static_context | v: df is pandas DataFrame from pd.read_csv; .drop is pandas method |
| wrangle.py:43:4 | `df.to_csv('bee_colony_loss.csv')` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .to_csv is pandas method |
| wrangle.py:51:9 | `df.drop(columns='Unnamed: 0')` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .drop is pandas method |
| wrangle.py:53:9 | `df.sort_values(['year', 'state'], ascending=[False, True])` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .sort_values is pandas method |
| wrangle.py:55:9 | `df.dropna()` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .dropna is pandas method |
| wrangle.py:57:15 | `df.state.str.lower().str.replace(' ', '_')` | library / pandas | library / pandas | transitive_method | static_context | v: df.state is pandas Series; .str.lower().str.replace are pandas str accessor meth |
| wrangle.py:57:15 | `df.state.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df.state is pandas Series; .str.lower().str.replace are pandas str accessor meth |
| wrangle.py:59:16 | `df.season.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df.season is pandas Series; .str.lower is pandas str accessor method |
| wrangle.py:63:9 | `df.drop_duplicates()` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .drop_duplicates is pandas method |
| wrangle.py:65:20 | `df.total_loss.astype(float)` | library / pandas | library / pandas | transitive_method | static_context | v: df.total_loss is pandas Series; .astype is pandas method |
| wrangle.py:67:22 | `df.average_loss.astype(float)` | library / pandas | library / pandas | transitive_method | static_context | v: df.average_loss is pandas Series; .astype is pandas method |
| wrangle.py:69:25 | `df.ending_colonies.astype(int)` | library / pandas | library / pandas | transitive_method | static_context | v: df.ending_colonies is pandas Series; .astype is pandas method |
| wrangle.py:71:23 | `df.colonies_lost.astype(int)` | library / pandas | library / pandas | transitive_method | static_context | v: df.colonies_lost is pandas Series; .astype is pandas method |
| wrangle.py:91:17 | `df.columns.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df.columns is pandas Index; .str.lower is pandas str accessor |
| wrangle.py:93:20 | `df.state_name.str.lower().str.replace(' ', '_')` | library / pandas | library / pandas | transitive_method | static_context | v: df.state_name is pandas Series; .str.lower().str.replace are pandas str accessor |
| wrangle.py:93:20 | `df.state_name.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df.state_name is pandas Series; .str.lower().str.replace are pandas str accessor |
| wrangle.py:95:9 | `df.rename(columns={'state': 'ansi', 'state_name': 'state'})` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .rename/.drop are pandas methods |
| wrangle.py:95:9 | `df.rename(columns={'state': 'ansi', 'state_name': 'state'}).drop(co...` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .rename/.drop are pandas methods |
| wrangle.py:105:8 | `df.rename(columns={'name': 'state'})` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .rename is pandas method |
| wrangle.py:107:15 | `df.state.str.lower().str.replace(' ', '_')` | library / pandas | library / pandas | transitive_method | static_context | v: df.state is pandas Series; .str.lower().str.replace are pandas str accessors |
| wrangle.py:107:15 | `df.state.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df.state is pandas Series; .str.lower().str.replace are pandas str accessors |
| wrangle.py:123:9 | `df.merge(df1, on='state', how='left')` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .merge is pandas method |
| wrangle.py:125:9 | `df.merge(df2, on='state', how='left')` | library / pandas | library / pandas | transitive_method | static_context | v: df is pandas DataFrame; .merge is pandas method |
| wrangle.py:151:10 | `df2.drop(columns='Unnamed: 0')` | library / pandas | library / pandas | transitive_method | static_context | v: df2 is pandas DataFrame; .drop is pandas method |
| wrangle.py:153:17 | `df2.season.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df2.season is pandas Series; .str.lower is pandas str accessor |
| wrangle.py:155:16 | `df2.state.str.lower().str.replace(' ', '_')` | library / pandas | library / pandas | transitive_method | static_context | v: df2.state is pandas Series; .str.lower().str.replace are pandas str accessors |
| wrangle.py:155:16 | `df2.state.str.lower()` | library / pandas | library / pandas | transitive_method | static_context | v: df2.state is pandas Series; .str.lower().str.replace are pandas str accessors |
| wrangle.py:165:23 | `df2.average_loss.astype(float)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.average_loss is pandas Series; .astype is pandas method |
| wrangle.py:167:21 | `df2.total_loss.astype(float)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.total_loss is pandas Series; .astype is pandas method |
| wrangle.py:169:24 | `df2.colonies_lost.astype(int)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.colonies_lost is pandas Series; .astype is pandas method |
| wrangle.py:171:26 | `df2.ending_colonies.astype(int)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.ending_colonies is pandas Series; .astype is pandas method |
| wrangle.py:179:37 | `df2.year.astype(str)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.year is pandas Series; .astype is pandas method |
| wrangle.py:181:37 | `df2.year.astype(str)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.year is pandas Series; .astype is pandas method |
| wrangle.py:183:37 | `df2.year.astype(str)` | library / pandas | library / pandas | transitive_method | static_context | v: df2.year is pandas Series; .astype is pandas method |
| explore.py:36:18 | `train_test_split(df, test_size=0.2, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.model_selection import train_test_split |
| explore.py:38:22 | `train_test_split(train, test_size=0.25, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.model_selection import train_test_split |
| explore.py:80:20 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_mean, sq...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:81:23 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:87:23 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_median, ...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:88:26 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:103:9 | `LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| explore.py:105:4 | `lm.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm = LinearRegression(); .fit is sklearn estimator method |
| explore.py:107:39 | `lm.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm is sklearn LinearRegression; .predict is sklearn method |
| explore.py:109:42 | `lm.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm is sklearn LinearRegression; .predict is sklearn method |
| explore.py:112:25 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:114:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:117:16 | `metric_df.append({'model': 'OLS Regressor(normalize = True)', 'RMSE...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| explore.py:125:11 | `LassoLars(alpha=1, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: LassoLars is sklearn class |
| explore.py:127:4 | `lars.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars = LassoLars(); .fit is sklearn estimator method |
| explore.py:129:41 | `lars.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars is sklearn LassoLars; .predict is sklearn method |
| explore.py:131:44 | `lars.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars is sklearn LassoLars; .predict is sklearn method |
| explore.py:133:28 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:135:30 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:138:16 | `metric_df.append({'model': 'LASSOLARS(alpha=1, normalize=True)', 'R...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| explore.py:147:10 | `TweedieRegressor(alpha=5, power=1, warm_start=True)` | library / sklearn | library / sklearn | direct_import | static_context | v: TweedieRegressor is sklearn class |
| explore.py:149:4 | `glm.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm = TweedieRegressor(); .fit is sklearn estimator method |
| explore.py:151:40 | `glm.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm is sklearn TweedieRegressor; .predict is sklearn method |
| explore.py:153:43 | `glm.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm is sklearn TweedieRegressor; .predict is sklearn method |
| explore.py:155:26 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:157:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:160:16 | `metric_df.append({'model': 'Tweedie Regressor(alpha=5, power=1, war...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| explore.py:170:8 | `PolynomialFeatures(degree=2)` | library / sklearn | library / sklearn | direct_import | static_context | v: PolynomialFeatures is sklearn class |
| explore.py:172:22 | `pf.fit_transform(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: pf = PolynomialFeatures(); .fit_transform is sklearn method |
| explore.py:174:25 | `pf.transform(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: pf is sklearn PolynomialFeatures; .transform is sklearn method |
| explore.py:177:10 | `LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| explore.py:179:4 | `lm2.fit(X_train_degree2, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm2 = LinearRegression(); .fit is sklearn method |
| explore.py:181:40 | `lm2.predict(X_train_degree2)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm2 is sklearn LinearRegression; .predict is sklearn method |
| explore.py:183:43 | `lm2.predict(X_validate_degree2)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm2 is sklearn LinearRegression; .predict is sklearn method |
| explore.py:186:25 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:188:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:191:16 | `metric_df.append({'model': 'Polynomial Regression(degree = 2)', 'RM...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| explore.py:205:11 | `LassoLars(alpha=1, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: LassoLars is sklearn class |
| explore.py:207:4 | `lars.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars = LassoLars(); .fit is sklearn estimator method |
| explore.py:209:40 | `lars.predict(X_test)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars is sklearn LassoLars; .predict is sklearn method |
| explore.py:212:21 | `mean_squared_error(y_test.colonies_lost, y_test.colonies_lost_pred_...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:213:26 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_mean, sq...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:250:20 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_mean, sq...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:251:23 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:257:23 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_median, ...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:258:26 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| explore.py:266:12 | `SelectKBest(f_regression, k=k)` | library / sklearn | library / sklearn | direct_import | static_context | v: SelectKBest is sklearn class |
| explore.py:268:4 | `kbest.fit(X, y)` | library / sklearn | library / sklearn | direct_import | static_context | v: kbest = SelectKBest(); .fit is sklearn method |
| explore.py:270:25 | `kbest.get_support()` | library / sklearn | library / sklearn | direct_import | static_context | v: kbest is sklearn SelectKBest; .get_support is sklearn method |
| explore.py:278:8 | `RFE(LinearRegression(), n_features_to_select=n_features_to_select)` | library / sklearn | library / sklearn | direct_import | static_context | v: RFE is sklearn class |
| explore.py:278:12 | `LinearRegression()` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| explore.py:280:4 | `rfe.fit(X, y)` | library / sklearn | library / sklearn | direct_import | static_context | v: rfe = RFE(); .fit is sklearn method |
| explore.py:282:25 | `rfe.get_support()` | library / sklearn | library / sklearn | direct_import | static_context | v: rfe is sklearn RFE; .get_support is sklearn method |
| explore.py:326:11 | `GridSearchCV(LinearRegression(), params, cv=5)` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| explore.py:326:24 | `LinearRegression()` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| explore.py:328:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| explore.py:346:11 | `GridSearchCV(LassoLars(), params, cv=5)` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| explore.py:346:24 | `LassoLars()` | library / sklearn | library / sklearn | direct_import | static_context | v: LassoLars is sklearn class |
| explore.py:348:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| explore.py:367:11 | `GridSearchCV(TweedieRegressor(), params, cv=5, scoring='neg_root_me...` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| explore.py:367:24 | `TweedieRegressor()` | library / sklearn | library / sklearn | direct_import | static_context | v: TweedieRegressor is sklearn class |
| explore.py:369:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| grid_search.py:16:11 | `GridSearchCV(LinearRegression(), params, cv=5)` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| grid_search.py:16:24 | `LinearRegression()` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| grid_search.py:18:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| grid_search.py:36:11 | `GridSearchCV(LassoLars(), params, cv=5)` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| grid_search.py:36:24 | `LassoLars()` | library / sklearn | library / sklearn | direct_import | static_context | v: LassoLars is sklearn class |
| grid_search.py:38:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| grid_search.py:58:11 | `GridSearchCV(TweedieRegressor(), params, cv=5, scoring='neg_root_me...` | library / sklearn | library / sklearn | transitive_method | static_context | v: GridSearchCV is sklearn class |
| grid_search.py:58:24 | `TweedieRegressor()` | library / sklearn | library / sklearn | direct_import | static_context | v: TweedieRegressor is sklearn class |
| grid_search.py:60:4 | `grid.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: grid = GridSearchCV(); .fit is sklearn method |
| regression_models.py:17:27 | `train_test_split(df, test_size=0.2, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.model_selection import train_test_split |
| regression_models.py:19:22 | `train_test_split(train_validate, test_size=0.25, random_state=825)` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.model_selection import train_test_split |
| regression_models.py:27:13 | `MinMaxScaler()` | library / sklearn | library / sklearn | direct_import | static_context | v: MinMaxScaler is sklearn class |
| regression_models.py:29:4 | `scaler.fit(train[columns])` | library / sklearn | library / sklearn | direct_import | static_context | v: scaler = MinMaxScaler(); .fit is sklearn method |
| regression_models.py:31:19 | `scaler.transform(train[columns])` | library / sklearn | library / sklearn | direct_import | static_context | v: scaler is sklearn MinMaxScaler; .transform is sklearn method |
| regression_models.py:32:22 | `scaler.transform(validate[columns])` | library / sklearn | library / sklearn | direct_import | static_context | v: scaler is sklearn MinMaxScaler; .transform is sklearn method |
| regression_models.py:33:18 | `scaler.transform(test[columns])` | library / sklearn | library / sklearn | direct_import | static_context | v: scaler is sklearn MinMaxScaler; .transform is sklearn method |
| regression_models.py:60:20 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_mean, sq...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:61:23 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:67:23 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_median, ...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:68:26 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:87:20 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_mean, sq...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:88:23 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:94:23 | `mean_squared_error(y_train.colonies_lost, y_train.baseline_median, ...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:95:26 | `mean_squared_error(y_validate.colonies_lost, y_validate.baseline_me...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:111:9 | `LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| regression_models.py:113:4 | `lm.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm = LinearRegression(); .fit is sklearn estimator method |
| regression_models.py:115:39 | `lm.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm is sklearn LinearRegression; .predict is sklearn method |
| regression_models.py:117:42 | `lm.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm is sklearn LinearRegression; .predict is sklearn method |
| regression_models.py:120:25 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:122:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:125:16 | `metric_df.append({'model': 'OLS Regressor', 'RMSE_train': rmse_trai...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| regression_models.py:133:11 | `LassoLars(alpha=1)` | library / sklearn | library / sklearn | direct_import | static_context | v: LassoLars is sklearn class |
| regression_models.py:135:4 | `lars.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars = LassoLars(); .fit is sklearn estimator method |
| regression_models.py:137:41 | `lars.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars is sklearn LassoLars; .predict is sklearn method |
| regression_models.py:139:44 | `lars.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: lars is sklearn LassoLars; .predict is sklearn method |
| regression_models.py:141:28 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:143:30 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:146:16 | `metric_df.append({'model': 'LASSOLARS(alpha = 1)', 'RMSE_train': rm...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| regression_models.py:155:10 | `TweedieRegressor(power=1, alpha=0)` | library / sklearn | library / sklearn | direct_import | static_context | v: TweedieRegressor is sklearn class |
| regression_models.py:157:4 | `glm.fit(X_train, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm = TweedieRegressor(); .fit is sklearn estimator method |
| regression_models.py:159:40 | `glm.predict(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm is sklearn TweedieRegressor; .predict is sklearn method |
| regression_models.py:161:43 | `glm.predict(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: glm is sklearn TweedieRegressor; .predict is sklearn method |
| regression_models.py:163:26 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:165:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:168:16 | `metric_df.append({'model': 'Tweedie Regressor(power=1, alpha=0)', '...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
| regression_models.py:178:8 | `PolynomialFeatures(degree=5)` | library / sklearn | library / sklearn | direct_import | static_context | v: PolynomialFeatures is sklearn class |
| regression_models.py:180:22 | `pf.fit_transform(X_train)` | library / sklearn | library / sklearn | direct_import | static_context | v: pf = PolynomialFeatures(); .fit_transform is sklearn method |
| regression_models.py:182:25 | `pf.transform(X_validate)` | library / sklearn | library / sklearn | direct_import | static_context | v: pf is sklearn PolynomialFeatures; .transform is sklearn method |
| regression_models.py:185:10 | `LinearRegression(normalize=True)` | library / sklearn | library / sklearn | direct_import | static_context | v: LinearRegression is sklearn class |
| regression_models.py:187:4 | `lm5.fit(X_train_degree5, y_train.colonies_lost)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm5 = LinearRegression(); .fit is sklearn method |
| regression_models.py:189:40 | `lm5.predict(X_train_degree5)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm5 is sklearn LinearRegression; .predict is sklearn method |
| regression_models.py:191:43 | `lm5.predict(X_validate_degree5)` | library / sklearn | library / sklearn | direct_import | static_context | v: lm5 is sklearn LinearRegression; .predict is sklearn method |
| regression_models.py:194:25 | `mean_squared_error(y_train.colonies_lost, y_train.colonies_lost_pre...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:196:28 | `mean_squared_error(y_validate.colonies_lost, y_validate.colonies_lo...` | library / sklearn | library / sklearn | direct_import | static_context | v: from sklearn.metrics import mean_squared_error |
| regression_models.py:199:16 | `metric_df.append({'model': 'Polynomial Regression(degree = 5)', 'RM...` | library / pandas | library / pandas | transitive_method | static_context | v: metric_df is pandas DataFrame; .append is pandas method |
