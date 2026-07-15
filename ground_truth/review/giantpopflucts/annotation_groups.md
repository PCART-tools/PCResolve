# giantpopflucts -- Annotation Groups (23 groups, 75 records)

## Summary

| Evidence | Groups | Records | Needs Human |
|----------|--------|---------|-------------|
| static_obvious | 5 | 48 | 0 |
| static_context | 15 | 20 | 0 |
| manual_reasoned | 3 | 6 | 6 |
| awaiting_review | -- | 1 | 1 |
| **Total** | **23** | **75** | **7** |

## Group 1: plt -> library/matplotlib (14 records)

| Evidence | static_obvious |
| Needs human | no (0/14) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ scaling_var.py:5 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure()</code> -- scaling_var.py:104
- <code>plt.plot(ms, vs, 'o', alpha=0.1, markersize=4, color=grey)</code> -- scaling_var.py:106
- <code>plt.plot(tc, xc, 'k')</code> -- scaling_var.py:107
- <code>plt.fill_between(tc, lci, uci, color='k', alpha=0.4)</code> -- scaling_var.py:108
- <code>plt.plot(tc[tc &lt; 3e-05], a1 * tc[tc &lt; 3e-05] ** (-1), '--', color=blue, linewidth=3)</code> -- scaling_var.py:117
- ... and 9 more

**All bindings (1 unique):**
- <code>scaling_var.py</code> L5: <code>import matplotlib.pyplot</code>

## Group 2: plt -> library/matplotlib (11 records)

| Evidence | static_obvious |
| Needs human | no (0/11) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ plot_msd.py:5 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure(figsize=[5, 4.8])</code> -- plot_msd.py:25
- <code>plt.errorbar(group['dt'] + i / 70, group['msd'], fmt='o-', yerr=2 * group['msd stderr'], color=color</code> -- plot_msd.py:29
- <code>plt.plot([0, 1 + i / 70], [0, msd[0]], '--', color=colors[i], alpha=0.8)</code> -- plot_msd.py:30
- <code>plt.legend(title='Batch', frameon=False)</code> -- plot_msd.py:32
- <code>plt.ylabel('MSD Estimate')</code> -- plot_msd.py:33
- ... and 6 more

**All bindings (1 unique):**
- <code>plot_msd.py</code> L5: <code>import matplotlib.pyplot</code>

## Group 3: plt -> library/matplotlib (8 records)

| Evidence | static_obvious |
| Needs human | no (0/8) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ stan_model/plot_rawdisplacements.py:4 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure()</code> -- stan_model/plot_rawdisplacements.py:21
- <code>plt.legend(handles[3:], labels[3:], title='Replicate', frameon=False, loc=(1.05, 0))</code> -- stan_model/plot_rawdisplacements.py:29
- <code>plt.errorbar([0, 1, 2], means, yerr=np.vstack((lci, uci)), fmt='ks', zorder=10, alpha=0.7)</code> -- stan_model/plot_rawdisplacements.py:43
- <code>plt.ylabel('log $f_t-$ log $f_{t-1}$')</code> -- stan_model/plot_rawdisplacements.py:44
- <code>plt.xlabel('Second Day, $t$')</code> -- stan_model/plot_rawdisplacements.py:45
- ... and 3 more

**All bindings (1 unique):**
- <code>stan_model/plot_rawdisplacements.py</code> L4: <code>import matplotlib.pyplot</code>

## Group 4: plt -> library/matplotlib (8 records)

| Evidence | static_obvious |
| Needs human | no (0/8) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ stan_model/plot_variance_components.py:2 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure(figsize=[4.7, 5])</code> -- stan_model/plot_variance_components.py:23
- <code>plt.errorbar(errors['x'], errors['med'], yerr=np.vstack((np.array(errors['l']), np.array(errors['u']</code> -- stan_model/plot_variance_components.py:47
- <code>plt.xlabel('')</code> -- stan_model/plot_variance_components.py:48
- <code>plt.ylabel('Variance between replicates')</code> -- stan_model/plot_variance_components.py:49
- <code>plt.yscale('log')</code> -- stan_model/plot_variance_components.py:50
- ... and 3 more

**All bindings (1 unique):**
- <code>stan_model/plot_variance_components.py</code> L2: <code>import matplotlib.pyplot</code>

## Group 5: plt -> library/matplotlib (7 records)

| Evidence | static_obvious |
| Needs human | no (0/7) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import matplotlib.pyplot</code> @ plot_rawdisplacements.py:4 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.figure()</code> -- plot_rawdisplacements.py:28
- <code>plt.legend(handles[3:], labels[3:], title='Replicate', frameon=False, loc=(1.05, 0))</code> -- plot_rawdisplacements.py:62
- <code>plt.ylabel('log $f_t-$ log $f_{t-1}$')</code> -- plot_rawdisplacements.py:63
- <code>plt.xlabel('Second Day, $t$')</code> -- plot_rawdisplacements.py:64
- <code>plt.title('Batch {}'.format(batch))</code> -- plot_rawdisplacements.py:65
- ... and 2 more

**All bindings (1 unique):**
- <code>plot_rawdisplacements.py</code> L4: <code>import matplotlib.pyplot</code>

## Group 6: df_freq -> library/pandas (4 records)

| Evidence | static_context |
| Needs human | no (0/4) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>df_freq.merge(df_ploidy,on='barcode',how='inner')</code> @ get_frequencies.py:38 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df_freq.merge(df_ploidy, on='barcode', how='inner')</code> -- get_frequencies.py:38
- <code>df_freq.drop_duplicates(subset='barcode', inplace=True)</code> -- get_frequencies.py:40
- <code>df_freq.iterrows()</code> -- get_frequencies.py:48
- <code>df_freq.to_csv('frequencies.csv', index=False)</code> -- get_frequencies.py:57

**All bindings (1 unique):**
- <code>get_frequencies.py</code> L38: <code>df_freq.merge(df_ploidy,on='barcode',how='inner')</code>

## Group 7: p -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>comprehension target</code> @ stan_model/plot_variance_components.py:25 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>p.get_x()</code> -- stan_model/plot_variance_components.py:25
- <code>p.get_width()</code> -- stan_model/plot_variance_components.py:25
- <code>p.get_height()</code> -- stan_model/plot_variance_components.py:26

**All bindings (2 unique):**
- <code>stan_model/plot_variance_components.py</code> L25: <code>comprehension target</code>
- <code>stan_model/plot_variance_components.py</code> L26: <code>comprehension target</code>

## Group 8: fit -> library/pystan (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>sm.sampling(data=data_dic, iter=1000, chains=4,control=dict(max_treedepth=20,ada</code> @ stan_model/linear_model_noncentered.py:57 |
| Owner | pystan |
| Proposed GT | library / pystan |

**Representative expressions:**

- <code>fit.extract([pp])</code> -- stan_model/linear_model_noncentered.py:61
- <code>fit.extract(['alpha'])</code> -- stan_model/linear_model_noncentered.py:63
- <code>fit.extract(['s_mean'])</code> -- stan_model/linear_model_noncentered.py:64

**All bindings (1 unique):**
- <code>stan_model/linear_model_noncentered.py</code> L57: <code>sm.sampling(data=data_dic, iter=1000, chains=4,control=dict(max_treedepth=20,ada</code>

## Group 9: msd[tp[1] - tp[0]] -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Proposed GT | ? / ? |

**All expressions:**

- <code>msd[tp[1] - tp[0]].append(ms)</code> -- msd_log_calc.py:127
- <code>msd[tp[1] - tp[0]].append(ms)</code> -- msd_log_calc.py:150


## Group 10: logf -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>trafo(np.array(df00[['Batch_{}_t_{}'.format(1,ti)]]))</code> @ msd_log_calc.py:47 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>logf.flatten()</code> -- msd_log_calc.py:48

**All bindings (1 unique):**
- <code>msd_log_calc.py</code> L47: <code>trafo(np.array(df00[['Batch_{}_t_{}'.format(1,ti)]]))</code>

## Group 11: a3 -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>sns.stripplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)</code> @ plot_rawdisplacements.py:57 |
| Owner | seaborn |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>a3.get_legend_handles_labels()</code> -- plot_rawdisplacements.py:61

**All bindings (1 unique):**
- <code>plot_rawdisplacements.py</code> L57: <code>sns.stripplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)</code>

## Group 12: a3 -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>sns.swarmplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)</code> @ stan_model/plot_rawdisplacements.py:24 |
| Owner | seaborn |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>a3.get_legend_handles_labels()</code> -- stan_model/plot_rawdisplacements.py:28

**All bindings (1 unique):**
- <code>stan_model/plot_rawdisplacements.py</code> L24: <code>sns.swarmplot(data=dp,x='t',y='logdiff',hue='rep',alpha=0.5,dodge=True)</code>

## Group 13: df -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.concat(dfs)</code> @ plot_msd.py:22 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df.groupby(by=['Batch'])</code> -- plot_msd.py:27

**All bindings (1 unique):**
- <code>plot_msd.py</code> L22: <code>pd.concat(dfs)</code>

## Group 14: df -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.DataFrame({'variance':varl,'name':names,'Batch':batches})</code> @ stan_model/plot_variance_components.py:22 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df.groupby(by=['name', 'Batch'])</code> -- stan_model/plot_variance_components.py:33

**All bindings (1 unique):**
- <code>stan_model/plot_variance_components.py</code> L22: <code>pd.DataFrame({'variance':varl,'name':names,'Batch':batches})</code>

## Group 15: df.iloc[:, :-13] -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.read_csv('TableS3.csv')</code> @ get_frequencies.py:19 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df.iloc[:, :-13].copy()</code> -- get_frequencies.py:32

**All bindings (1 unique):**
- <code>get_frequencies.py</code> L19: <code>pd.read_csv('TableS3.csv')</code>

## Group 16: df.iloc[:, :-13].copy() -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.read_csv('TableS3.csv')</code> @ get_frequencies.py:19 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df.iloc[:, :-13].copy().dropna()</code> -- get_frequencies.py:32

**All bindings (1 unique):**
- <code>get_frequencies.py</code> L19: <code>pd.read_csv('TableS3.csv')</code>

## Group 17: df.loc[:, df.columns != 'barcode'] -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.read_csv('TableS3.csv')</code> @ get_frequencies.py:19 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df.loc[:, df.columns != 'barcode'].sum(axis=0)</code> -- get_frequencies.py:31

**All bindings (1 unique):**
- <code>get_frequencies.py</code> L19: <code>pd.read_csv('TableS3.csv')</code>

## Group 18: df_freq -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>df_freq.merge(df_fitness,on='barcode',how='inner')</code> @ get_frequencies.py:37 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>df_freq.merge(df_fitness, on='barcode', how='inner')</code> -- get_frequencies.py:37

**All bindings (1 unique):**
- <code>get_frequencies.py</code> L37: <code>df_freq.merge(df_fitness,on='barcode',how='inner')</code>

## Group 19: dp -> library/pandas (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pd.concat(dps)</code> @ plot_rawdisplacements.py:55 |
| Owner | pandas |
| Proposed GT | library / pandas |

**Representative expressions:**

- <code>dp.to_csv('raw_displacement_batch{}.csv'.format(batch), index=False)</code> -- plot_rawdisplacements.py:56

**All bindings (1 unique):**
- <code>plot_rawdisplacements.py</code> L55: <code>pd.concat(dps)</code>

## Group 20: sm -> library/pystan (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>pystan.StanModel(model_code=stancode)</code> @ stan_model/linear_model_noncentered.py:56 |
| Owner | pystan |
| Proposed GT | library / pystan |

**Representative expressions:**

- <code>sm.sampling(data=data_dic, iter=1000, chains=4, control=dict(max_treedepth=20, adapt_delta=0.8))</code> -- stan_model/linear_model_noncentered.py:57

**All bindings (1 unique):**
- <code>stan_model/linear_model_noncentered.py</code> L56: <code>pystan.StanModel(model_code=stancode)</code>

## Group 21: ps -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ scaling_var.py:43 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>ps.append(p1)</code> -- scaling_var.py:48

**All bindings (1 unique):**
- <code>scaling_var.py</code> L43: <code>[]</code>

## Group 22: xis -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ scaling_var.py:73 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>xis.append(xc)</code> -- scaling_var.py:79

**All bindings (1 unique):**
- <code>scaling_var.py</code> L73: <code>[]</code>

## Group 23: xs -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ scaling_var.py:66 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>xs.append(np.mean(x[(t &gt;= ti * (1 - window)) &amp; (t &lt;= ti * (1 + window))]))</code> -- scaling_var.py:68

**All bindings (1 unique):**
- <code>scaling_var.py</code> L66: <code>[]</code>

## Awaiting Review (1 records)

| Expression | File:Line | GT | Notes |
|------------|-----------|----|-------|
| <code>scipy.stats.norm().ppf(1 - 0.05 / len(df_freq))</code> | get_frequencies.py:42 | library/scipy | import-backed dotted module call: scipy.stats.norm().ppf |
