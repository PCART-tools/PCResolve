# hfhd — static_context (39 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| hfhd/hf.py:175:30 | `x.dropna()` | library / pandas | local / local | transitive_method | static_context | gt: pandas method<br>v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:176:20 | `x.dropna()` | library / pandas | local / local | transitive_method | static_context | gt: pandas method<br>v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:407:23 | `x.dropna()` | library / pandas | python / python | transitive_method | static_context | gt: pandas .dropna() on pd.Series<br>v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:408:21 | `x.dropna()` | library / pandas | python / python | transitive_method | static_context | gt: pandas .dropna() on pd.Series<br>v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:433:15 | `price.dropna()` | library / pandas | local / local | transitive_method | static_context | gt: pandas method<br>v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:434:16 | `y.mean()` | library / pandas | library / numpy | transitive_method | static_context | gt: .mean() on pandas Series y<br>v: .mean() on pandas Series |
| hfhd/hf.py:437:25 | `y_hat.mean()` | library / pandas | local / local | transitive_method | static_context | gt: .mean() on pandas Series y_hat per docstring<br>v: .mean() on pandas Series |
| hfhd/hf.py:439:11 | `resid.cumsum()` | library / pandas | local / local | transitive_method | static_context | gt: pandas .cumsum() on Series<br>v: pandas cumsum method on Series/DataFrame |
| hfhd/hf.py:568:15 | `data.to_numpy()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .to_numpy( method on pandas Series/DataFrame |
| hfhd/hf.py:843:9 | `(data - data.shift(K)).dropna()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:843:17 | `data.shift(K)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .shift() method on Series/DataFrame |
| hfhd/hf.py:844:9 | `sk.transpose()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .transpose( method on pandas Series/DataFrame |
| hfhd/hf.py:844:9 | `sk.transpose().dot(sk)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dot( method on pandas Series/DataFrame |
| hfhd/hf.py:847:9 | `(data - data.shift(J)).dropna()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:847:17 | `data.shift(J)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .shift() method on Series/DataFrame |
| hfhd/hf.py:848:9 | `sj.transpose()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .transpose( method on pandas Series/DataFrame |
| hfhd/hf.py:848:9 | `sj.transpose().dot(sj)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dot( method on pandas Series/DataFrame |
| hfhd/hf.py:1050:19 | `refresh_time(tick_series_list).dropna()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:1051:27 | `data.to_numpy()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .to_numpy( method on pandas Series/DataFrame |
| hfhd/hf.py:1515:19 | `refresh_time(tick_series_list).dropna()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| hfhd/hf.py:1516:27 | `data.to_numpy()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .to_numpy( method on pandas Series/DataFrame |
| hfhd/sim.py:199:13 | `sr.between_time('9:30', '16:00', include_start=True, include_end=True)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/sim.py:202:13 | `sr.resample('1d')` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:202:13 | `sr.resample('1d').sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:207:13 | `si.between_time('9:30', '16:00', include_start=True, include_end=True)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/sim.py:210:13 | `si.resample('1d')` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:210:13 | `si.resample('1d').sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:215:13 | `sf.between_time('9:30', '16:00', include_start=True, include_end=True)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/sim.py:218:13 | `sf.resample('1d')` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:218:13 | `sf.resample('1d').sum()` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .resample( method on pandas Series/DataFrame |
| hfhd/sim.py:294:34 | `self.log_rets.cumsum(axis=0)` | library / numpy | local / local | transitive_method | static_context | gt: numpy .cumsum() on ndarray<br>v: ndarray.cumsum() is numpy method |
| hfhd/sim.py:302:8 | `self.ms_noise.ravel()` | library / numpy | library / numpy | transitive_method | static_context | v: ndarray.ravel() is numpy method |
| hfhd/sim.py:311:27 | `self.feature.cumsum(axis=0)` | library / numpy | library / numpy | transitive_method | static_context | v: ndarray.cumsum() is numpy method |
| hfhd/sim.py:318:21 | `self.price.between_time('9:30', '16:00', include_start=True, includ...` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/sim.py:321:27 | `self.cum_feature.between_time('9:30', '16:00', include_start=True, ...` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/sim.py:403:25 | `(log_rets - var / 2).cumsum(axis=0)` | library / numpy | local / local | transitive_method | static_context | gt: numpy .cumsum() on ndarray<br>v: ndarray.cumsum() is numpy method |
| hfhd/sim.py:411:4 | `ms_noise.ravel()` | library / numpy | library / numpy | transitive_method | static_context | v: ndarray.ravel() is numpy method |
| hfhd/hd.py:766:19 | `x.between_time(stp[j], stp[j + 1], True, True)` | library / pandas | local / local | transitive_method | static_context | gt: pandas method<br>v: pandas .between_time( method on pandas Series/DataFrame |
| hfhd/hd.py:768:22 | `x.between_time(stp[j + 1], stp[j], False, False)` | library / pandas | local / local | transitive_method | static_context | gt: pandas method<br>v: pandas .between_time( method on pandas Series/DataFrame |
