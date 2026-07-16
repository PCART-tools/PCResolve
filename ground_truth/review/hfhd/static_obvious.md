# hfhd — static_obvious (375 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| main_test.py:6:22 | `np.column_stack((np.arange(10, 15) / 10, np.flip(np.arange(10, 15) ...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main_test.py:7:13 | `np.arange(10, 15)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main_test.py:7:35 | `np.flip(np.arange(10, 15) / 10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main_test.py:7:43 | `np.arange(10, 15)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main_test.py:8:19 | `np.zeros(factor_loadings.shape)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| main_test.py:9:8 | `sim.Universe(0.01, [1e-09, 0, 0.48, 0.5, 1e-08], [1e-09, 0, 0.48, 0...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main_test.py:18:4 | `u.simulate(1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| main_test.py:19:4 | `u.cond_cov()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:172:8 | `len(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:173:14 | `ValueError('tick_series_list should be a list containing at least t...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:175:14 | `tuple([np.array(x.dropna().index, dtype='uint64') for x in tick_ser...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:175:21 | `np.array(x.dropna().index, dtype='uint64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:176:13 | `tuple([x.dropna().to_numpy(dtype='float64') for x in tick_series_li...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:177:21 | `_refresh_time(indeces, values)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:178:12 | `pd.to_datetime(index)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:179:11 | `pd.DataFrame(rt_data, index=index)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:179:11 | `pd.DataFrame(rt_data, index=index).dropna()` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:207:23 | `np.append(merged_index, index)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:208:19 | `np.sort(np.unique(merged_index))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:208:27 | `np.unique(merged_index)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:211:20 | `np.empty((merged_index.shape[0], len(values)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:211:53 | `len(values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:215:18 | `np.empty(merged_values.shape[1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:218:13 | `range(merged_values.shape[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:219:17 | `range(merged_values.shape[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:221:18 | `np.searchsorted(index, merged_index[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:232:15 | `np.isnan(last_values)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:232:15 | `np.isnan(last_values).any()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:234:29 | `np.full_like(last_values, np.nan)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:298:7 | `len(data.shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:306:12 | `int(np.sqrt(n) * 0.4)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:306:16 | `np.sqrt(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:311:13 | `g(np.arange(1, K) / K)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:311:15 | `np.arange(1, K)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:312:14 | `_preaverage(data, weight)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:315:18 | `pd.Series(data_pa.flatten(), index=index)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:317:18 | `pd.DataFrame(data_pa, index=index)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:347:26 | `int(1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:348:14 | `np.full_like(data, np.nan)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:349:13 | `prange(K - 1, n)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:350:17 | `range(p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:351:28 | `np.dot(weight, data[i - K + 2:i + 1, j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:325:1 | `numba.njit(cache=False, parallel=False, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:371:10 | `np.zeros((int(p * (p + 1) / 2), 2), dtype=np.int16)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:371:20 | `int(p * (p + 1) / 2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:372:13 | `range(p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:373:17 | `range(i, p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:377:14 | `ValueError('Got negative index, \`\`p\`\` probably too large for in...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:401:12 | `np.max([len(x) for x in tick_series_list])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:401:20 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:402:14 | `np.empty((len(tick_series_list), n_max), dtype='uint64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:402:24 | `len(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:404:13 | `np.empty((len(tick_series_list), n_max), dtype='float64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:404:23 | `len(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:406:16 | `enumerate(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:407:14 | `np.array(x.dropna().index, dtype='uint64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:408:12 | `np.array(x.dropna().to_numpy(), dtype='float64')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:433:8 | `np.log(price.dropna())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:563:26 | `_get_indeces_and_values(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:564:14 | `_msrc_pairwise(indeces, values, M, N)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:567:15 | `refresh_time(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:571:14 | `_msrc(data, M, N)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:576:1 | `numba.njit(fastmath=False, parallel=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:647:12 | `int(np.ceil(n ** (1 / 2)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:647:16 | `np.ceil(n ** (1 / 2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:651:12 | `int(np.ceil(n ** (1 / 2)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:651:16 | `np.ceil(n ** (1 / 2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:655:8 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:658:17 | `range(1, M + 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:661:19 | `_get_YY_m(data, N, m)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:665:16 | `_get_YY_m(data, N, 1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:666:16 | `_get_YY_m(data, N, M)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:669:13 | `_get_YY_m(data, 0, 1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:584:1 | `numba.njit(fastmath=False, parallel=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:696:10 | `np.ones((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:700:10 | `_upper_triangular_indeces(p)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:702:13 | `prange(len(idx))` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:702:20 | `len(idx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:710:34 | `np.isnan(values[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:711:34 | `np.isnan(values[j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:714:24 | `_msrc(values[i, :n_not_nans_i].reshape(1, -1), M, N)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:716:31 | `_refresh_time((indeces[i, :n_not_nans_i], indeces[j, :n_not_nans_j]...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:724:43 | `np.isnan(merged_values)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:727:24 | `_msrc(merged_values.T, M, N)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:674:1 | `numba.njit(cache=False, parallel=True)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:837:11 | `refresh_time(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:841:12 | `int(M ** (2 / 3))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:871:11 | `np.minimum(x, 1 - x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1043:8 | `len(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1046:26 | `_get_indeces_and_values(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1047:14 | `_mrc_pairwise(indeces, values, theta, g, bias_correction, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1050:19 | `refresh_time(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1051:19 | `np.diff(data.to_numpy(), axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1054:19 | `np.diff(data.to_numpy(), axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1056:14 | `_mrc(data, theta, g, bias_correction, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1103:14 | `ValueError('Either \`\`theta\`\` or \`\`k\`\` can be specified, but...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1108:12 | `_get_k(n, theta, bias_correction)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1112:24 | `np.sqrt(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1114:24 | `np.power(n, 0.6)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1119:15 | `np.sum(g(np.arange(1, k) / k) ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1119:22 | `g(np.arange(1, k) / k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1119:24 | `np.arange(1, k)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1120:15 | `np.sum((g(np.arange(1, k) / k) - g((np.arange(1, k) - 1) / k)) ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1120:23 | `g(np.arange(1, k) / k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1120:25 | `np.arange(1, k)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1120:44 | `g((np.arange(1, k) - 1) / k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1120:47 | `np.arange(1, k)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1122:17 | `g(np.arange(1, k) / k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1122:19 | `np.arange(1, k)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1123:18 | `_preaverage(data, weight)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1126:27 | `np.isnan(data_pa)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1131:13 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1061:1 | `numba.njit(cache=False, fastmath=False, parallel=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1184:10 | `np.ones((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1188:10 | `_upper_triangular_indeces(p)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1190:13 | `prange(len(idx))` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1190:20 | `len(idx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1198:34 | `np.isnan(values[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1199:34 | `np.isnan(values[j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1204:24 | `_mrc(data, theta, g, bias_correction, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1206:31 | `_refresh_time((indeces[i, :n_not_nans_i], indeces[j, :n_not_nans_j]...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1213:43 | `np.isnan(merged_values)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1217:24 | `_mrc(data, theta, g, bias_correction, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1144:1 | `numba.njit(cache=False, parallel=True, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1230:16 | `np.ceil(np.sqrt(n) * theta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1230:24 | `np.sqrt(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1233:16 | `np.ceil(np.power(n, 0.5 + delta) * theta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1233:24 | `np.power(n, 0.5 + delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1237:11 | `int(k)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1263:14 | `ValueError('x must be >= 0.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1297:14 | `ValueError('x must be >= 0.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1301:26 | `np.sin(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1301:42 | `np.cos(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1342:14 | `ValueError('Specified kernel not implemented.')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1345:8 | `int(c_star * xi_sq ** (2 / 5) * n ** (3 / 5))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1385:26 | `abs(h)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1385:47 | `abs(h)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1508:8 | `len(tick_series_list)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1511:26 | `_get_indeces_and_values(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1512:14 | `_krvm_pairwise(indeces, values, H, kernel)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1515:19 | `refresh_time(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1516:19 | `np.diff(data.to_numpy(), axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1519:19 | `np.diff(data.to_numpy(), axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1521:14 | `_krvm(data.T, H, kernel)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1552:10 | `np.ones((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1556:10 | `_upper_triangular_indeces(p)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1558:13 | `prange(len(idx))` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1558:20 | `len(idx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1566:34 | `np.isnan(values[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1567:34 | `np.isnan(values[j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1572:24 | `_krvm(data.T, H, kernel)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1574:31 | `_refresh_time((indeces[i, :n_not_nans_i], indeces[j, :n_not_nans_j]...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1581:43 | `np.isnan(merged_values)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1585:24 | `_krvm(data.T, H, kernel)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1526:1 | `numba.njit(cache=False, parallel=True, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1622:10 | `gamma(data, 0)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1623:13 | `range(1, n + 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1624:17 | `kernel((h - c) / H)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1631:12 | `gamma(data, h)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1591:1 | `numba.njit(cache=False, parallel=False, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1835:22 | `_get_indeces_and_values(tick_series_list)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1839:13 | `np.diff(values, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1842:13 | `np.column_stack((np.zeros(p), values))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1842:30 | `np.zeros(p)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1844:10 | `_hayashi_yoshida_pairwise(indeces, values, theta, k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1882:10 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1886:10 | `_upper_triangular_indeces(p)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1887:13 | `prange(len(idx))` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1887:20 | `len(idx)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1895:34 | `np.isnan(values[i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1896:34 | `np.isnan(values[j])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1911:13 | `_hayashi_yoshida(a_index, b_index, a_values, b_values, k, theta)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1848:1 | `numba.njit(cache=False, parallel=True, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1954:11 | `len(a_index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1954:27 | `len(a_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1954:45 | `len(b_index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1954:61 | `len(b_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1958:14 | `ValueError('Either \`\`theta\`\` or \`\`k\`\` can be specified, but...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hf.py:1968:12 | `_get_k((a_values.shape[0] + b_values.shape[0]) / 2, theta, True)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1972:17 | `_numba_minimum(np.arange(1, k) / k)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1972:32 | `np.arange(1, k)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1973:19 | `_preaverage(a_values.reshape(-1, 1), weight)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1978:19 | `_preaverage(b_values.reshape(-1, 1), weight)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hf.py:1983:11 | `np.zeros(a_index.shape[0], dtype=np.float64)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1984:13 | `prange(k, a_index.shape[0])` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1987:18 | `np.searchsorted(b_index, start, 'right')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1991:16 | `np.searchsorted(b_index, end, 'left')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1995:18 | `np.sum(a_values[i] * b_values[start_b:end_b + k])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1996:9 | `np.sum(temp)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:1919:1 | `numba.njit(cache=False, parallel=False, fastmath=False)` | library / numba | library / numba | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:2040:10 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:2041:8 | `np.eye(p)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:2042:8 | `np.ones((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hf.py:2044:23 | `enumerate(estimates)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:60:9 | `np.random.normal(0, 1, n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:61:8 | `np.zeros(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:62:14 | `np.zeros(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:63:15 | `np.zeros(n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:66:7 | `min(alpha, beta)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:67:14 | `ValueError('alpha, beta need to be non-negative')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:69:14 | `ValueError('omega needs to be positive')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:72:8 | `print('alpha+beta>=1, variance not defined\n        --> time series...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:75:13 | `range(n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:175:13 | `np.diag([self.uncond_var(self.factor_garch_spec)] * self.n_factors)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:175:22 | `self.uncond_var(self.factor_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:176:13 | `np.diag([self.uncond_var(self.resid_garch_spec)] * self.n_stocks)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:176:22 | `self.uncond_var(self.resid_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:177:13 | `np.diag([self.uncond_var(self.industry_garch_spec)] * self.n_ind)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:177:22 | `self.uncond_var(self.industry_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:196:13 | `pd.DataFrame(self.sigma_sq_resid)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:197:19 | `pd.to_datetime(sr.index, unit=self.freq)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:204:13 | `pd.DataFrame(self.sigma_sq_industry)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:205:19 | `pd.to_datetime(si.index, unit=self.freq)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:212:13 | `pd.DataFrame(self.sigma_sq_factor)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:213:19 | `pd.to_datetime(sf.index, unit=self.freq)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:221:18 | `np.diag(sf[sf.index.date == i].values.flatten())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:224:18 | `np.diag(si[si.index.date == i].values.flatten())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:226:18 | `np.diag(sr[sr.index.date == i].values.flatten())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:256:18 | `ValueError("Only frequency \`\`'s'\`\` or \`\`'m'\`\` supported.")` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:259:30 | `np.zeros((n_periods, self.factor_loadings.shape[1]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:260:31 | `np.zeros((n_periods, self.factor_loadings.shape[1]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:261:17 | `range(self.n_factors)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:263:16 | `garch_11(n_periods, *self.factor_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:266:32 | `np.zeros((n_periods, self.industry_loadings.shape[1]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:267:33 | `np.zeros((n_periods, self.industry_loadings.shape[1]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:268:17 | `range(self.n_ind)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:270:13 | `garch_11(n_periods, *self.industry_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:273:23 | `np.random.normal(0.0, np.sqrt(self.uncond_var(self.resid_garch_spec...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:273:23 | `np.random.normal(0.0, np.sqrt(self.uncond_var(self.resid_garch_spec...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:275:12 | `np.sqrt(self.uncond_var(self.resid_garch_spec))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:275:20 | `self.uncond_var(self.resid_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:280:30 | `np.empty((n_periods, self.n_stocks))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:281:23 | `np.empty((n_periods, self.n_stocks))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:282:17 | `range(self.n_stocks)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:284:16 | `garch_11(n_periods, *self.resid_garch_spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:294:27 | `np.exp(self.log_rets.cumsum(axis=0))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:297:24 | `np.random.normal(0, 1, self.price.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:297:24 | `np.random.normal(0, 1, self.price.size).reshape(self.price.shape[0]...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:301:12 | `int((1 - self.liquidity) * self.price.size)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:302:30 | `np.random.choice(self.ms_noise.size, c, replace=False)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:312:21 | `pd.DataFrame(self.price)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:313:27 | `pd.DataFrame(self.cum_feature)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:314:27 | `pd.to_datetime(self.price.index, unit=self.freq)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:344:11 | `np.min(data)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:345:11 | `np.max(data)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:346:10 | `plt.figure()` | library / matplotlib | library / matplotlib | transitive_method | static_obvious | v: direct matplotlib.pyplot API call |
| hfhd/sim.py:347:9 | `sns.heatmap(data[0], vmin=vmin, vmax=vmax, xticklabels=False, ytick...` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:351:8 | `plt.clf()` | library / matplotlib | library / matplotlib | transitive_method | static_obvious | v: direct matplotlib.pyplot API call |
| hfhd/sim.py:354:8 | `plt.clf()` | library / matplotlib | library / matplotlib | transitive_method | static_obvious | v: direct matplotlib.pyplot API call |
| hfhd/sim.py:355:13 | `sns.heatmap(data[i], vmin=vmin, vmax=vmax, xticklabels=False, ytick...` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:358:11 | `animation.FuncAnimation(fig, animate, init_func=init, frames=np.ara...` | library / matplotlib | library / matplotlib | transitive_method | static_obvious | v: direct numpy API call |
| hfhd/sim.py:359:42 | `np.arange(len(data))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:359:52 | `len(data)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:361:4 | `plt.show()` | library / matplotlib | library / matplotlib | transitive_method | static_obvious | v: direct matplotlib.pyplot API call |
| hfhd/sim.py:395:15 | `np.zeros((n, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:396:10 | `np.zeros((n, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:397:13 | `range(p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:398:36 | `garch_11(size, *spec)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/sim.py:399:26 | `np.linalg.cholesky(corr_matrix)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:403:18 | `np.exp((log_rets - var / 2).cumsum(axis=0))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:406:15 | `np.random.normal(0, 1, price.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:406:15 | `np.random.normal(0, 1, price.size).reshape(price.shape[0], price.sh...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/sim.py:410:8 | `int((1 - liquidity) * price.size)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/sim.py:411:21 | `np.random.choice(ms_noise.size, c, replace=False)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:50:18 | `np.mean([loss_func(S, sigma) for S in S_list], axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:50:27 | `loss_func(S, sigma)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/loss.py:52:26 | `np.mean([loss_func(sigma_hat, sigma) for sigma_hat in sigma_hat_lis...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:52:35 | `loss_func(sigma_hat, sigma)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/loss.py:55:22 | `np.mean([loss_func(hd.fsopt(S, sigma), sigma) for S in S_list], axi...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:55:31 | `loss_func(hd.fsopt(S, sigma), sigma)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/loss.py:55:41 | `hd.fsopt(S, sigma)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/loss.py:64:14 | `ValueError('PRIAL not defined: The sample covariance attained\n    ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/loss.py:107:20 | `np.linalg.inv(sigma_hat)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:108:16 | `np.linalg.inv(sigma)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:110:10 | `np.trace(sigma_hat_inv @ sigma @ sigma_hat_inv)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:111:13 | `np.trace(sigma_hat_inv)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:112:26 | `np.trace(sigma_inv)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:144:11 | `np.trace(delta @ delta)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:195:20 | `np.sqrt(c)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:196:20 | `np.sqrt(c)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/loss.py:199:37 | `np.sqrt((b - x) * (x - a))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:49:15 | `np.linalg.eigh(S)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:50:8 | `np.einsum('ji, jk, ki -> i', u, sigma, u)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:51:15 | `np.diag(d)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:153:8 | `np.cov(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:154:14 | `_linear_shrinkage_intensity(X, S)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:155:17 | `_linear_shrinkage_cov(S, rho_hat)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:193:17 | `np.trace(S)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:194:36 | `np.eye(p)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:223:14 | `np.linalg.eigvalsh(S)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:224:12 | `np.mean(evalues)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:226:12 | `np.linalg.norm(np.outer(X[:, i], X[:, i]) - S, 'fro')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:226:27 | `np.outer(X[:, i], X[:, i])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:227:21 | `range(n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:229:15 | `np.sum(temp)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:230:11 | `np.linalg.norm(S - lambd * np.eye(p), 'fro')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:230:36 | `np.eye(p)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:231:11 | `np.minimum(b_bar_sq, d_sq)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:260:13 | `range(max_iter)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:261:15 | `np.linalg.cond(cov)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:264:14 | `_linear_shrinkage_cov(cov, step)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:459:8 | `np.cov(X)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:460:18 | `_nonlinear_shrinkage_cov(S, n - 1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:600:15 | `np.linalg.eigh(S)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:603:18 | `np.maximum(0, p - n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:604:8 | `np.tile(lambd, (np.minimum(p, n), 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:604:24 | `np.minimum(p, n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:610:22 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:611:14 | `np.mean(np.maximum(1 - x ** 2 / 5, 0) / H, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:611:22 | `np.maximum(1 - x ** 2 / 5, 0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:615:25 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:617:16 | `np.log(np.abs((np.sqrt(5) - x) / (np.sqrt(5) + x)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:617:23 | `np.abs((np.sqrt(5) - x) / (np.sqrt(5) + x))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:617:31 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:617:50 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:620:11 | `np.abs(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:620:24 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:621:43 | `np.abs(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:621:56 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:623:14 | `np.mean(Hftemp / H, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:632:51 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:634:27 | `np.log((1 + np.sqrt(5) * h) / (1 - np.sqrt(5) * h))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:634:39 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:635:32 | `np.sqrt(5)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:635:52 | `np.mean(1 / lambd)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:642:17 | `np.concatenate([dtilde0 * np.ones(p - n), dtilde1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:642:43 | `np.ones(p - n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:644:17 | `np.dot(np.dot(u, np.diag(dtilde)), u.T)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:644:24 | `np.dot(u, np.diag(dtilde))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:644:34 | `np.diag(dtilde)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:663:11 | `(datetime.datetime(2000, 1, 1, 9, 30) + datetime.timedelta(minutes=...` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:663:12 | `datetime.datetime(2000, 1, 1, 9, 30)` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:664:13 | `datetime.timedelta(minutes=np.ceil(6.5 / L * 60))` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:664:40 | `np.ceil(6.5 / L * 60)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:665:20 | `range(L)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:666:15 | `datetime.time(16, 0)` | library / datetime | library / datetime | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:748:15 | `series.index[0].date()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:748:41 | `series.index[-1].date()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:752:19 | `series.index[0].date()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:754:27 | `series.index[0].date()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:760:14 | `_get_partitions(4)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:762:8 | `len(stp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:765:13 | `range(L)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:770:26 | `np.linalg.eigh(estimator(ticks_notj, **kwargs))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:770:41 | `estimator(ticks_notj, **kwargs)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:771:22 | `estimator(ticks_j, **kwargs)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:772:12 | `np.diag(np.diag(P_not_j.T @ Sigma_tilde @ P_not_j))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:772:20 | `np.diag(P_not_j.T @ Sigma_tilde @ P_not_j)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:776:11 | `np.mean(Sigma_hat_list, axis=0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:915:18 | `int(2 * n ** 0.5)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:915:37 | `int(0.2 * n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:915:51 | `int(0.4 * n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:915:65 | `int(0.6 * n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:916:18 | `int(0.8 * n)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:916:32 | `int(n - 2.5 * n ** 0.5)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:916:55 | `int(n - 1.5 * n ** 0.5)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:917:18 | `_nercome(X, m, M)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:918:14 | `_optimal_nere(Sigmas)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:921:24 | `_nercome(X, m, M)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hfhd/hd.py:948:20 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:949:22 | `np.zeros((p, p))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:950:13 | `range(M)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:951:16 | `np.random.randint(0, n, m)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:952:15 | `np.ones(n, dtype=np.int64)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:953:22 | `int(0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| hfhd/hd.py:954:22 | `np.linalg.eigh(np.cov(X[:, mask]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:954:37 | `np.cov(X[:, mask])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:955:22 | `np.cov(X[:, idx_m])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:956:12 | `np.diag(np.diag(P_1.T @ Sigma_tilde @ P_1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:956:20 | `np.diag(P_1.T @ Sigma_tilde @ P_1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:982:13 | `np.linalg.norm(x[0] - x[1], 'fro')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:983:15 | `np.argmin(norms)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:1009:8 | `np.diag(1.0 / np.sqrt(np.diag(cov)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:1009:19 | `np.sqrt(np.diag(cov))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hfhd/hd.py:1009:27 | `np.diag(cov)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
