# polire — manual_reasoned (8 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| polire/custom/custom.py:38:8 | `self.reg.fit(X, y)` | unknown / unknown | local / local | polymorphic_library_receiver | manual_reasoned | v: self.reg can be an xgboost or sklearn regressor depending on the constructor arg |
| polire/custom/custom.py:53:15 | `self.reg.predict(np.asarray([X1.ravel(), X2.ravel()]).T)` | unknown / unknown | local / local | polymorphic_library_receiver | manual_reasoned | v: self.reg can be an xgboost or sklearn regressor depending on the constructor arg |
| polire/custom/custom.py:59:15 | `self.reg.predict(X)` | unknown / unknown | local / local | polymorphic_library_receiver | manual_reasoned | v: self.reg can be an xgboost or sklearn regressor depending on the constructor arg |
| tests/polire_basic.py:48:12 | `NSGP()` | unknown / unknown | unknown / unknown | unreachable_unresolved_receiver | manual_reasoned | v: the skipped test references NSGP without importing it, so model and y_new have n |
| tests/polire_basic.py:50:4 | `model.fit(X, y, **{'ECM': X @ X.T})` | unknown / unknown | unknown / unknown | unreachable_unresolved_receiver | manual_reasoned | v: the skipped test references NSGP without importing it, so model and y_new have n |
| tests/polire_basic.py:51:12 | `model.predict(X_new)` | unknown / unknown | unknown / unknown | unreachable_unresolved_receiver | manual_reasoned | v: the skipped test references NSGP without importing it, so model and y_new have n |
| tests/polire_basic.py:54:11 | `y_new.sum()` | unknown / unknown | unknown / unknown | unreachable_unresolved_receiver | manual_reasoned | v: the skipped test references NSGP without importing it, so model and y_new have n |
| tests/polire_basic.py:54:26 | `y_new.sum()` | unknown / unknown | unknown / unknown | unreachable_unresolved_receiver | manual_reasoned | v: the skipped test references NSGP without importing it, so model and y_new have n |
