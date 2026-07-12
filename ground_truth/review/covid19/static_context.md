# covid19 — static_context (22 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| script.py:53:22 | `confirmed.sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .sum( method on pandas Series/DataFrame |
| script.py:54:19 | `deaths.sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .sum( method on pandas Series/DataFrame |
| script.py:55:22 | `recovered.sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .sum( method on pandas Series/DataFrame |
| script.py:76:30 | `(start_date + datetime.timedelta(days=i)).strftime('%m/%d/%Y')` | library / datetime | library / datetime | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:82:0 | `svm_confirmed.fit(X_train_confirmed, y_train_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:83:11 | `svm_confirmed.predict(forecast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:85:16 | `svm_confirmed.predict(X_test_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:98:0 | `svm_deaths.fit(X_train_deaths, y_train_deaths)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:99:11 | `svm_deaths.predict(forecast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:101:16 | `svm_deaths.predict(X_test_deaths)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:114:0 | `svm_recovered.fit(X_train_recovered, y_train_recovered)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:115:11 | `svm_recovered.predict(forecast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:117:16 | `svm_recovered.predict(X_test_recovered)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:128:25 | `poly.fit_transform(X_train_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:129:24 | `poly.fit_transform(X_test_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:130:22 | `poly.fit_transform(forecast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:133:34 | `bayesian_poly.fit_transform(X_train_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:134:33 | `bayesian_poly.fit_transform(X_test_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:135:31 | `bayesian_poly.fit_transform(forecast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:139:0 | `linear_model.fit(poly_X_train_confirmed, y_train_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:140:19 | `linear_model.predict(poly_X_test_confirmed)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| script.py:141:14 | `linear_model.predict(poly_future_forcast)` | library / sklearn | library / sklearn | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
