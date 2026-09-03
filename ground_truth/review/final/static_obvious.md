# final — static_obvious (105 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| final.py:106:5 | `bee_wrangle()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:108:8 | `ts_bee_prep()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:123:24 | `ts_split(ts_df)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:211:4 | `print('We reject the null hypothesis.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:214:4 | `print('We fail to reject the null hypothesis.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:260:0 | `largest_loss(train)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:289:4 | `print('We can reject the null hypothesis of equal variances.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:291:4 | `print('We fail to reject the null hypothesis that variance is equal.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:312:4 | `print('We reject our null hypothesis that there is no difference in...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:314:4 | `print('we fail to reject our null hypothesis that there is no diffe...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| final.py:380:0 | `select_kbest(X, y, 4)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:391:0 | `select_rfe(X, y, n_features_to_select=4)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:429:0 | `get_baseline_RMSE(y_train, y_validate)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:440:0 | `RMSE(X_train, y_train, X_validate, y_validate)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:454:0 | `test_rmse(X_train, y_train, X_test, y_test)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| final.py:463:0 | `viz_test_perfomance(y_test)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:7:0 | `warnings.filterwarnings('ignore')` | library / warnings | library / warnings | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:21:9 | `pd.read_csv('BeeInformed_States_Loss_Table_by_Year_public_ready_202...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:49:9 | `pd.read_csv('bee_colony_loss.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:89:9 | `pd.read_csv('state_ansi.txt', sep='\|')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:103:9 | `pd.read_csv('state_geocords.csv', index_col=[0])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:117:9 | `prep_bees()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:119:10 | `state_ansi()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:121:10 | `geo_data()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:137:9 | `get_bee_data()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:139:9 | `bee_merged()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| wrangle.py:149:10 | `pd.read_csv('bee_colony_loss.csv')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:159:15 | `pd.get_dummies(df2.season)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:161:10 | `pd.concat([df2, dummy_df], axis=1)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| wrangle.py:185:15 | `pd.to_datetime(df2.year)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:7:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:10:0 | `sns.set_theme()` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:47:4 | `plt.figure(figsize=(16, 8))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:49:4 | `plt.hist(y_validate.colonies_lost, color='blue', alpha=0.5, label='...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:51:4 | `plt.hist(y_validate.colonies_lost_pred_lm, color='red', alpha=0.5, ...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:53:4 | `plt.hist(y_validate.colonies_lost_pred_glm, color='yellow', alpha=0...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:55:4 | `plt.hist(y_validate.colonies_lost_pred_lars, color='green', alpha=0...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:57:4 | `plt.hist(y_validate.colonies_lost_pred_lm2, color='cyan', alpha=0.5...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:58:4 | `plt.xlabel('colony lost')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:59:4 | `plt.ylabel('count')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:60:4 | `plt.title('Comparing the distribution of actual colony lost to pred...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:61:4 | `plt.xlim(0, 2500)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:62:4 | `plt.legend()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:63:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:93:16 | `pd.DataFrame(data=[{'model': 'Baseline', 'RMSE_train': RMSE_train_m...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:112:19 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:114:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:133:22 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:135:24 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:155:20 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:157:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:186:19 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:188:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:198:11 | `pd.DataFrame(metric_df)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:212:15 | `round(mean_squared_error(y_test.colonies_lost, y_test.colonies_lost...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:213:20 | `round(mean_squared_error(y_train.colonies_lost, y_train.baseline_me...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:215:4 | `print(f'The RMSE on test dataset is {rmse_test} while RMSE on basel...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:221:4 | `plt.figure(figsize=(16, 8))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:225:4 | `plt.hist(y_test.colonies_lost_pred_lars, color='green', alpha=0.7, ...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:227:4 | `plt.xlim(0, 1200)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:228:4 | `plt.title('model prediction in test data')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:229:4 | `plt.xlabel('colony lost')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:230:4 | `plt.ylabel('count')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:231:4 | `plt.legend()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:232:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:253:4 | `print('RMSE using Mean on \nTrain: ', round(RMSE_train_mean, 2), '\...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:253:42 | `round(RMSE_train_mean, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:253:84 | `round(RMSE_validate_mean, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:254:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:260:4 | `print('RMSE using Median on \nTrain: ', round(RMSE_train_median, 2)...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:260:44 | `round(RMSE_train_median, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:260:88 | `round(RMSE_validate_median, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| explore.py:299:4 | `plt.title('Annual Colony Loss by Season', fontsize=16)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:301:4 | `plt.ticklabel_format(style='plain', axis='y')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:303:4 | `plt.vlines(x=4, ymin=0, ymax=120000)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:305:4 | `plt.vlines(x=10, ymin=0, ymax=120000)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:307:4 | `plt.annotate('Beginning of Summer', [3.8, 121000], xycoords='data')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:309:4 | `plt.annotate('Beginning of Winter', [9.0, 121000], xycoords='data')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:311:4 | `plt.xlabel('Month')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:313:4 | `plt.ylabel('Colonies Lost')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| explore.py:315:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:5:0 | `warnings.filterwarnings('ignore')` | library / warnings | library / warnings | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:39:19 | `pd.concat([train.reset_index(drop=True), pd.DataFrame(train_scaled,...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:39:61 | `pd.DataFrame(train_scaled, columns=scaled_columns)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:40:22 | `pd.concat([validate.reset_index(drop=True), pd.DataFrame(validate_s...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:40:67 | `pd.DataFrame(validate_scaled, columns=scaled_columns)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:41:17 | `pd.concat([test.reset_index(drop=True), pd.DataFrame(test_scaled, c...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:41:58 | `pd.DataFrame(test_scaled, columns=scaled_columns)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:63:4 | `print('RMSE using Mean on \nTrain: ', round(RMSE_train_mean, 2), '\...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:63:42 | `round(RMSE_train_mean, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:63:84 | `round(RMSE_validate_mean, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:64:4 | `print()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:70:4 | `print('RMSE using Median on \nTrain: ', round(RMSE_train_median, 2)...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:70:44 | `round(RMSE_train_median, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:70:88 | `round(RMSE_validate_median, 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:100:16 | `pd.DataFrame(data=[{'model': 'Baseline', 'RMSE_train': RMSE_train_m...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| regression_models.py:120:19 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:122:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:141:22 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:143:24 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:163:20 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:165:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:194:19 | `round(mean_squared_error(y_train.colonies_lost, y_train.colonies_lo...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:196:22 | `round(mean_squared_error(y_validate.colonies_lost, y_validate.colon...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| regression_models.py:206:4 | `print(metric_df)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
