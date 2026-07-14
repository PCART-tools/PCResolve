# giantpopflucts — Needs Annotation (74 records)

These records do not yet have `verification_level` or
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| plot_rawdisplacements.py:28:2 | `plt.figure()` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:56:2 | `dp.to_csv('raw_displacement_batch{}.csv'.format(batch), index=False)` |  /  | library / pandas | - | - |  |
| plot_rawdisplacements.py:61:20 | `a3.get_legend_handles_labels()` |  /  | library / seaborn | - | - |  |
| plot_rawdisplacements.py:62:4 | `plt.legend(handles[3:], labels[3:], title='Replicate', frameon=Fals...` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:63:2 | `plt.ylabel('log $f_t-$ log $f_{t-1}$')` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:64:2 | `plt.xlabel('Second Day, $t$')` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:65:2 | `plt.title('Batch {}'.format(batch))` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:67:2 | `plt.tight_layout()` |  /  | library / matplotlib | - | - |  |
| plot_rawdisplacements.py:69:2 | `plt.savefig('raw_displacement_batch{}.pdf'.format(batch), format='p...` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:25:0 | `plt.figure(figsize=[5, 4.8])` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:27:17 | `df.groupby(by=['Batch'])` |  /  | library / pandas | - | - |  |
| plot_msd.py:29:2 | `plt.errorbar(group['dt'] + i / 70, group['msd'], fmt='o-', yerr=2 *...` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:30:2 | `plt.plot([0, 1 + i / 70], [0, msd[0]], '--', color=colors[i], alpha...` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:32:0 | `plt.legend(title='Batch', frameon=False)` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:33:0 | `plt.ylabel('MSD Estimate')` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:34:0 | `plt.xlabel('Time difference, $\\Delta t$')` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:35:0 | `plt.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:36:0 | `plt.yticks([0, 0.005, 0.01, 0.015])` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:37:0 | `plt.xticks([0, 1, 2])` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:38:0 | `plt.tight_layout()` |  /  | library / matplotlib | - | - |  |
| plot_msd.py:40:0 | `plt.savefig('msd_plot_{}_{}.pdf'.format(l, u), format='pdf')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:48:4 | `ps.append(p1)` |  /  | local / local | - | - |  |
| scaling_var.py:68:4 | `xs.append(np.mean(x[(t >= ti * (1 - window)) & (t <= ti * (1 + wind...` |  /  | local / local | - | - |  |
| scaling_var.py:79:4 | `xis.append(xc)` |  /  | local / local | - | - |  |
| scaling_var.py:104:0 | `plt.figure()` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:106:0 | `plt.plot(ms, vs, 'o', alpha=0.1, markersize=4, color=grey)` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:107:0 | `plt.plot(tc, xc, 'k')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:108:0 | `plt.fill_between(tc, lci, uci, color='k', alpha=0.4)` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:117:0 | `plt.plot(tc[tc < 3e-05], a1 * tc[tc < 3e-05] ** (-1), '--', color=b...` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:118:0 | `plt.plot(tc[tc > 0.0008], a2 * tc[tc > 0.0008] ** 0, '--', color=re...` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:120:0 | `plt.xlabel('$\\langle f \\rangle$')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:121:0 | `plt.ylabel('var log $f$')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:123:0 | `plt.yscale('log')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:124:0 | `plt.xscale('log')` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:125:0 | `plt.ylim((0.0008, 0.2))` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:126:0 | `plt.xlim((7e-06, 0.0045))` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:128:0 | `plt.tight_layout()` |  /  | library / matplotlib | - | - |  |
| scaling_var.py:129:0 | `plt.savefig('scaling_1_log.pdf', format='pdf', transparent=True)` |  /  | library / matplotlib | - | - |  |
| msd_log_calc.py:48:16 | `logf.flatten()` |  /  | library / numpy | - | - |  |
| msd_log_calc.py:127:4 | `msd[tp[1] - tp[0]].append(ms)` |  /  | local / local | - | - |  |
| msd_log_calc.py:150:6 | `msd[tp[1] - tp[0]].append(ms)` |  /  | local / local | - | - |  |
| get_frequencies.py:31:10 | `df.loc[:, df.columns != 'barcode'].sum(axis=0)` |  /  | library / pandas | - | - |  |
| get_frequencies.py:32:10 | `df.iloc[:, :-13].copy()` |  /  | library / pandas | - | - |  |
| get_frequencies.py:32:10 | `df.iloc[:, :-13].copy().dropna()` |  /  | library / pandas | - | - |  |
| get_frequencies.py:37:8 | `df_freq.merge(df_fitness, on='barcode', how='inner')` |  /  | library / pandas | - | - |  |
| get_frequencies.py:38:8 | `df_freq.merge(df_ploidy, on='barcode', how='inner')` |  /  | library / pandas | - | - |  |
| get_frequencies.py:40:0 | `df_freq.drop_duplicates(subset='barcode', inplace=True)` |  /  | library / pandas | - | - |  |
| get_frequencies.py:48:13 | `df_freq.iterrows()` |  /  | library / pandas | - | - |  |
| get_frequencies.py:57:0 | `df_freq.to_csv('frequencies.csv', index=False)` |  /  | library / pandas | - | - |  |
| stan_model/plot_rawdisplacements.py:21:2 | `plt.figure()` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:28:20 | `a3.get_legend_handles_labels()` |  /  | library / seaborn | - | - |  |
| stan_model/plot_rawdisplacements.py:29:4 | `plt.legend(handles[3:], labels[3:], title='Replicate', frameon=Fals...` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:43:2 | `plt.errorbar([0, 1, 2], means, yerr=np.vstack((lci, uci)), fmt='ks'...` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:44:2 | `plt.ylabel('log $f_t-$ log $f_{t-1}$')` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:45:2 | `plt.xlabel('Second Day, $t$')` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:46:2 | `plt.title('Batch {}'.format(batch))` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:48:2 | `plt.tight_layout()` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_rawdisplacements.py:50:2 | `plt.show()` |  /  | library / matplotlib | - | - |  |
| stan_model/linear_model_noncentered.py:57:6 | `sm.sampling(data=data_dic, iter=1000, chains=4, control=dict(max_tr...` |  /  | library / pystan | - | - |  |
| stan_model/linear_model_noncentered.py:61:15 | `fit.extract([pp])` |  /  | library / pystan | - | - |  |
| stan_model/linear_model_noncentered.py:63:13 | `fit.extract(['alpha'])` |  /  | library / pystan | - | - |  |
| stan_model/linear_model_noncentered.py:64:13 | `fit.extract(['s_mean'])` |  /  | library / pystan | - | - |  |
| stan_model/plot_variance_components.py:23:0 | `plt.figure(figsize=[4.7, 5])` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:25:12 | `p.get_x()` |  /  | library / seaborn | - | - |  |
| stan_model/plot_variance_components.py:25:28 | `p.get_width()` |  /  | library / seaborn | - | - |  |
| stan_model/plot_variance_components.py:26:12 | `p.get_height()` |  /  | library / seaborn | - | - |  |
| stan_model/plot_variance_components.py:33:15 | `df.groupby(by=['name', 'Batch'])` |  /  | library / pandas | - | - |  |
| stan_model/plot_variance_components.py:47:0 | `plt.errorbar(errors['x'], errors['med'], yerr=np.vstack((np.array(e...` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:48:0 | `plt.xlabel('')` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:49:0 | `plt.ylabel('Variance between replicates')` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:50:0 | `plt.yscale('log')` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:52:0 | `plt.legend(loc='upper left', title='Batch', frameon=False)` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:53:0 | `plt.tight_layout()` |  /  | library / matplotlib | - | - |  |
| stan_model/plot_variance_components.py:54:0 | `plt.savefig('variance_components.pdf', format='pdf')` |  /  | library / matplotlib | - | - |  |
