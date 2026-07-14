# greenbenchmark — static_obvious (260 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| run_cached_script.py:11:9 | `argparse.ArgumentParser(description='Run Android user interaction t...` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| run_cached_script.py:32:4 | `os.system('monkeyrunner tests/hold.py "%s" %d %d' % (serialno, x, y))` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| run_cached_script.py:42:5 | `open(PERSIST_SCRIPT_FILENAME)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run_cached_script.py:43:18 | `json.load(data_file)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| run_cached_script.py:43:18 | `json.load(data_file).get(serialno)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| run_cached_script.py:53:8 | `sleep(action.get('duration'))` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run_cached_script.py:55:8 | `swipeDown()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| run_cached_script.py:57:8 | `swipeUp()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| run_cached_script.py:60:8 | `hold(x, y)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:7:0 | `matplotlib.use('Agg')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:16:29 | `os.listdir(a_dir)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:16:50 | `os.path.isdir(os.path.join(a_dir, name))` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:16:64 | `os.path.join(a_dir, name)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:18:9 | `argparse.ArgumentParser(description='Report a set of Odroid Energy ...` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:26:17 | `pandas.read_csv(results_directory + '/energy_log.csv', parse_dates=...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:28:18 | `pandas.DataFrame([{'timestamp': k, 'armW': v.armW.mean(), 'memW': v...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:46:16 | `pandas.read_csv(results_directory + '/event_log.csv', index_col='ev...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:55:16 | `read_energy_csv(dir_path)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:57:15 | `read_event_csv(dir_path)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:61:12 | `os.path.basename(dir_path)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:67:30 | `int(interaction_end)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:67:53 | `int(interaction_start)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:69:30 | `calculate_energy(df_energy, interaction_start, interaction_end, pow...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:71:12 | `plot_power_feature(df_energy, df_event, power_feature, '%s/%s.pdf' ...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:72:12 | `plot_consumption(df_energy, power_feature, interaction_start, inter...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:77:9 | `len(sample1.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:78:9 | `len(sample2.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:81:47 | `np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:86:18 | `tqdm(get_immediate_subdirectories(dir_path))` | library / tqdm | library / tqdm | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:86:23 | `get_immediate_subdirectories(dir_path)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:87:33 | `report_experiment(dir_path + '/' + subdir)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:89:9 | `pandas.DataFrame(experiments_report_data)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:97:14 | `np.abs(group - group.mean())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:99:89 | `replace(g, stds=2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:102:18 | `list(df['experiment'].unique())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:103:23 | `next((x for x in experiments if x != 'blank-app' and 'lint' not in x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:110:8 | `report_energy_feature(df_grouped, df_experiment_pivot, energy_featu...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:125:29 | `get_experiment_label(experiment, experiment_pivot)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:127:14 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:133:8 | `plt.savefig(dir_path + '/_violinplot_%s.pdf' % energy_feature, bbox...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:134:8 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:142:4 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:145:4 | `plt.scatter(df_without_blankapp['temperatureC'], df_without_blankap...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:146:109 | `plt.cm.get_cmap('jet', len(experiments_without_blankapp))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:146:132 | `len(experiments_without_blankapp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:148:11 | `np.polyfit(df_without_blankapp['temperatureC'], df_without_blankapp...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:149:11 | `plt.gca()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:150:13 | `np.linspace(axes.get_xlim()[0], axes.get_xlim()[1], 10)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:151:4 | `plt.plot(X_plot, m * X_plot + b, '-')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:153:4 | `plt.xlabel(u'Temperature (ºC)')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:154:4 | `plt.ylabel('Energy CPU (J)')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:156:16 | `plt.FuncFormatter(lambda val, loc: experiments_without_blankapp[val])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:158:4 | `plt.colorbar(ticks=range(len(experiments_without_blankapp)), format...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:158:23 | `range(len(experiments_without_blankapp))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:158:29 | `len(experiments_without_blankapp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:160:4 | `plt.savefig(dir_path + '/_results_arm_scatter_energy_T.pdf')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:161:4 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:165:4 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:166:4 | `plt.scatter(df_without_blankapp['duration'], df_without_blankapp['e...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:167:109 | `plt.cm.get_cmap('jet', len(experiments_without_blankapp))` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:167:132 | `len(experiments_without_blankapp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:169:4 | `plt.ylabel('Energy CPU (J)')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:170:4 | `plt.xlabel('Duration (s)')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:172:16 | `plt.FuncFormatter(lambda val, loc: experiments_without_blankapp[val])` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:174:4 | `plt.colorbar(ticks=range(len(experiments_without_blankapp)), format...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:174:23 | `range(len(experiments_without_blankapp))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:174:29 | `len(experiments_without_blankapp)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:176:4 | `plt.savefig(dir_path + '/_results_arm_scatter_energy_duration.pdf')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:177:4 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:186:19 | `len(group.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:187:45 | `scipy.stats.shapiro(group[energy_feature], a=None, reta=False)` | library / scipy | library / scipy | direct_import | static_obvious | v: import-backed dotted module call: scipy.stats.shapiro |
| report_all_results.py:188:48 | `scipy.stats.mannwhitneyu(df_experiment_pivot[energy_feature], group...` | library / scipy | library / scipy | direct_import | static_obvious | v: import-backed dotted module call: scipy.stats.mannwhitneyu |
| report_all_results.py:190:47 | `scipy.stats.ttest_ind(df_experiment_pivot[energy_feature], group[en...` | library / scipy | library / scipy | direct_import | static_obvious | v: import-backed dotted module call: scipy.stats.ttest_ind |
| report_all_results.py:193:25 | `cohensd(df_experiment_pivot[energy_feature], group[energy_feature])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:197:20 | `pandas.DataFrame.from_dict(experiment_statistics, orient='index')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:201:9 | `open(dir_path + '/_%s_descriptive_statistics.tex' % energy_feature,...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:203:9 | `open(dir_path + '/_%s_significance_tests.tex' % energy_feature, 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:205:9 | `open(dir_path + '/_%s_effect_size.tex' % energy_feature, 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:207:9 | `open(dir_path + '/_%s_all_stats.tex' % energy_feature, 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:213:4 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:221:17 | `dict(boxstyle='round', fc='w', ec='none', alpha=0.9)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:222:15 | `dict(arrowstyle='->')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:230:17 | `dict(boxstyle='round', fc='w', ec='0.5', alpha=0.7)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:231:28 | `len(df_energy.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:241:8 | `plt.title('Energy consumption: %.2fJ' % energy_consumption)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:243:8 | `plt.title('Plot of %s' % power_feature)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:244:38 | `int(df_event.loc['InteractionStarted'])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:244:78 | `int(df_event.loc['InteractionEnded'])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:247:4 | `plt.savefig(filename)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:248:4 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:253:37 | `np.zeros(len(df.index))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:253:46 | `len(df.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:254:13 | `range(1, len(df.index))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:254:21 | `len(df.index)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| report_all_results.py:257:4 | `plt.figure()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:259:4 | `plt.title('Plot of %s' % power_feature)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:260:4 | `plt.title('Plot of %s\nEnergy consumption: %.2fJ' % (power_feature,...` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:261:4 | `plt.savefig(filename)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:262:4 | `plt.close()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| report_all_results.py:266:4 | `report_experiment(args.results_directory)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| report_all_results.py:268:4 | `report_set_of_experiments(args.results_directory)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:22:4 | `print('creating folder %s' % name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:25:4 | `touch(expand_menu_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:27:4 | `touch(vc.findViewById('me.writeily:id/create_folder') or vc.views[-2])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:29:4 | `type_text(device, name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:30:4 | `touch(vc.findViewWithText(u'Create'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:32:4 | `print('creating folder %s: done' % name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:36:4 | `print('creating note %s' % name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:39:4 | `touch(expand_menu_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:42:4 | `touch(create_note_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:44:4 | `type_text(device, name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:45:4 | `touch(vc.findViewById('me.writeily:id/note_content') or vc.findView...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:46:4 | `type_text(device, '# Title\n\n_one thing is italic_. **Another thin...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:47:4 | `touch(vc.findViewWithContentDescription(u'Navigate up'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:50:0 | `touch(vc.findViewWithContentDescription(u'More options'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:52:0 | `touch(vc.findViewWithText(u'Settings'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:54:0 | `touch(vc.findViewWithContentDescription(u'Navigate up'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:59:9 | `range(number_of_repeats)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:60:4 | `create_folder('folder-one')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:65:4 | `touch(vc.findViewWithText('folder-one'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:66:24 | `range(20)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:67:8 | `create_folder('folder-one-%d' % folder_one_i)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:69:4 | `create_note('note-one')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:73:4 | `create_folder('folder-two')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:76:4 | `touch(vc.findViewWithText('folder-two'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:77:4 | `create_note('note-two')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:80:4 | `touch(vc.findViewWithText('folder-two'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:81:4 | `create_note('note-three')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:84:4 | `touch(vc.findViewWithText('folder-two'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:85:4 | `create_note('note-four')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:88:24 | `range(10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/writely-pro-view_holder.py:90:8 | `touch(vc.findViewWithText('folder-one'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:91:8 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:97:4 | `touch(vc.findViewWithText('folder-two'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:101:4 | `hold(vc.findViewWithText(u'note-two'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:102:4 | `touch(vc.findViewWithText(u'note-three'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:103:4 | `touch(vc.findViewWithText(u'note-four'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:106:4 | `touch(vc.findViewWithContentDescription(u'Move'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:108:4 | `touch(vc.findViewWithText(u'folder-one'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:110:4 | `touch(vc.findViewWithText(u'Move here'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:112:4 | `create_note('note-five')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:114:4 | `create_folder('folder-three')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:118:4 | `hold(vc.findViewWithText(u'folder-one'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:121:4 | `touch(vc.findViewWithContentDescription(u'Move'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:123:4 | `touch(vc.findViewWithText(u'folder-three'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:125:4 | `touch(vc.findViewWithText(u'Move here'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:128:4 | `hold(vc.findViewWithText(u'folder-three'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:131:4 | `touch(vc.findViewWithContentDescription(u'Delete'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:133:4 | `touch(vc.findViewWithText(u'OK'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/writely-pro-view_holder.py:135:0 | `save_interaction(serialno, 'writely-pro-view_holder_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/hold.py:4:0 | `print(sys.argv)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/hold.py:6:9 | `int(sys.argv[2])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/hold.py:6:26 | `int(sys.argv[3])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/simplegallery.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:21:4 | `touch(allow)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:24:9 | `range(100)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/simplegallery.py:28:4 | `touch(dir)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:32:4 | `touch(media_item)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:33:4 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:34:13 | `range(15)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/simplegallery.py:35:8 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:36:4 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/simplegallery.py:38:0 | `save_interaction(serialno, 'simplegallery_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:20:0 | `touch(next)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:21:0 | `touch(next)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:22:0 | `touch(next)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:24:0 | `touch(vc.findViewWithTextOrRaise(u'Disable crash reports'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:25:0 | `touch(next)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:26:0 | `touch(next)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:30:4 | `touch(allow)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:32:0 | `touch(vc.findViewWithTextOrRaise(u'Assets'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:35:0 | `touch(more_options)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:38:0 | `touch(edit_account)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:39:0 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:40:0 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:42:9 | `range(10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/gnucash.py:44:4 | `touch(vc.findViewWithTextOrRaise(account))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:45:13 | `range(20)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/gnucash.py:46:8 | `touch(more_options)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:47:8 | `touch(edit_account)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:48:8 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:49:4 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/gnucash.py:55:0 | `save_interaction(serialno, 'gnucash_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:19:0 | `touch(vc.findViewWithTextOrRaise(u'Continue'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:23:9 | `range(20)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/acrylicpaint.py:24:13 | `range(10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/acrylicpaint.py:25:8 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:27:4 | `touch(color_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:31:13 | `range(10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/acrylicpaint.py:32:8 | `touch(color_menu)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:33:4 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/acrylicpaint.py:35:0 | `save_interaction(serialno, 'acrylicpaint_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:20:0 | `touch(init_view)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:21:0 | `sleep(65)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:22:0 | `touch(init_view)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:27:9 | `range(200)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/talalarmo.py:28:4 | `touch(ampm_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:29:0 | `touch(onoff_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:31:9 | `range(12)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/talalarmo.py:33:4 | `touch(init_view)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:34:4 | `touch(onoff_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:35:4 | `touch(init_view)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:36:4 | `touch(ampm_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:37:4 | `touch(ampm_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:38:4 | `touch(ampm_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:39:4 | `touch(onoff_switch)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:40:4 | `touch(more_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:43:4 | `touch(settings)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:45:4 | `touch(vc.findViewWithText(u'Theme'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:47:4 | `touch(vc.findViewWithText(next_theme))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:52:4 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/talalarmo.py:54:0 | `save_interaction(serialno, 'talalarmo_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/test_helper.py:15:8 | `interaction.append({'type': 'touch', 'position': touch_coord})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:20:8 | `interaction.append({'type': 'type_text', 'text': text})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:25:8 | `interaction.append({'type': 'back'})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:28:4 | `time.sleep(duration)` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| tests/test_helper.py:30:8 | `interaction.append({'type': 'wait', 'duration': duration})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:36:4 | `os.system('monkeyrunner hold.py %s %d %d' % (view.device.serialno, ...` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| tests/test_helper.py:38:8 | `interaction.append({'type': 'hold', 'position': (x, y)})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:47:8 | `interaction.append({'type': 'swipe_up'})` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:51:11 | `os.path.isfile(filename)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| tests/test_helper.py:54:13 | `open(filename, 'r')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:55:24 | `json.load(data_file)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| tests/test_helper.py:57:9 | `open(filename, 'w')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/test_helper.py:58:8 | `json.dump(json_data, outfile)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| tests/uhabits.py:16:5 | `ViewClient(device, serialno, **kwargs2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:19:4 | `print('Creating habit %s' % habit_name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/uhabits.py:21:4 | `sleep(1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:22:4 | `touch(vc.findViewWithContentDescription(u'Add habit'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:24:4 | `type_text(device, habit_name)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:31:4 | `touch(save_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:34:4 | `touch(vc.findViewWithTextOrRaise(habit_name))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:36:4 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:37:4 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:38:4 | `touch(vc.findViewWithContentDescription(u'Navigate up'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:43:0 | `touch(next_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:44:0 | `touch(next_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:45:0 | `touch(next_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:46:0 | `touch(next_button)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:50:0 | `touch(vc.findViewWithContentDescription(u'More options'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:52:0 | `touch(vc.findViewWithText(u'About'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:53:0 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:54:0 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:55:0 | `back(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:58:9 | `range(10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/uhabits.py:59:4 | `print('Set %d' % k)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/uhabits.py:60:13 | `range(7)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/uhabits.py:61:8 | `add_habit('H%d' % i)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:62:8 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:63:8 | `swipeUp(device)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:67:13 | `range(7)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tests/uhabits.py:69:8 | `hold(vc.findViewWithText(habit_name))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:70:4 | `touch(vc.findViewWithContentDescription(u'More options'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:72:4 | `touch(vc.findViewWithText('Delete'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:74:4 | `touch(vc.findViewWithText('OK'))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| tests/uhabits.py:78:0 | `save_interaction(serialno, 'uhabits_cache.json')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
