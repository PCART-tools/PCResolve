# greenbenchmark — Needs Annotation (229 records)

These records do not yet have `verification_level` or
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| run_cached_script.py:12:0 | `parser.add_argument('json_file', help='the json file with interacti...` |  /  | library / argparse | - | - |  |
| run_cached_script.py:13:7 | `parser.parse_args()` |  /  | library / argparse | - | - |  |
| run_cached_script.py:22:4 | `device.drag(s, e, 500, 20, -1)` |  /  | library / com | - | - |  |
| run_cached_script.py:29:4 | `device.drag(s, e, 500, 20, -1)` |  /  | library / com | - | - |  |
| run_cached_script.py:37:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | library / com | - | - |  |
| run_cached_script.py:39:5 | `ViewClient(device, serialno, **kwargs2)` |  /  | library / com | - | - |  |
| run_cached_script.py:46:16 | `action.get('type')` |  /  | library / json | - | - |  |
| run_cached_script.py:48:16 | `action.get('position')` |  /  | library / json | - | - |  |
| run_cached_script.py:49:8 | `vc.touch(x, y)` |  /  | library / com | - | - |  |
| run_cached_script.py:51:8 | `device.type(action.get('text'))` |  /  | library / com | - | - |  |
| run_cached_script.py:51:20 | `action.get('text')` |  /  | library / json | - | - |  |
| run_cached_script.py:53:14 | `action.get('duration')` |  /  | library / json | - | - |  |
| run_cached_script.py:59:16 | `action.get('position')` |  /  | library / json | - | - |  |
| run_cached_script.py:62:8 | `device.shell('input keyevent KEYCODE_BACK')` |  /  | library / com | - | - |  |
| report_all_results.py:19:0 | `parser.add_argument('--all_figures', action='store_true')` |  /  | library / argparse | - | - |  |
| report_all_results.py:20:0 | `parser.add_argument('--single_experiment', action='store_true')` |  /  | library / argparse | - | - |  |
| report_all_results.py:21:0 | `parser.add_argument('results_directory', help='the directory with a...` |  /  | library / argparse | - | - |  |
| report_all_results.py:23:7 | `parser.parse_args()` |  /  | library / argparse | - | - |  |
| report_all_results.py:32:24 | `v.armW.mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:33:24 | `v.memW.mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:34:24 | `v.g3dW.mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:35:24 | `v.kfcW.mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:36:31 | `v.temperature.mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:37:25 | `energy_csv.groupby(['timestamp'])` |  /  | library / pandas | - | - |  |
| report_all_results.py:42:36 | `(energy_csv['timestamp'] - energy_csv['timestamp'].shift()).fillna(0)` |  /  | library / pandas | - | - |  |
| report_all_results.py:42:61 | `energy_csv['timestamp'].shift()` |  /  | library / pandas | - | - |  |
| report_all_results.py:52:11 | `df_energy.loc[t1:t2, [power_feature, 'timestamp_delta']].product(ax...` |  /  | local / local | - | - |  |
| report_all_results.py:52:11 | `df_energy.loc[t1:t2, [power_feature, 'timestamp_delta']].product(ax...` |  /  | local / local | - | - |  |
| report_all_results.py:66:33 | `df_energy['temperature'].mean()` |  /  | library / pandas | - | - |  |
| report_all_results.py:79:11 | `sample1.var()` |  /  | local / local | - | - |  |
| report_all_results.py:80:11 | `sample2.var()` |  /  | local / local | - | - |  |
| report_all_results.py:81:12 | `sample2.mean()` |  /  | local / local | - | - |  |
| report_all_results.py:81:29 | `sample1.mean()` |  /  | local / local | - | - |  |
| report_all_results.py:88:8 | `experiments_report_data.append(experiment_report_data)` |  /  | local / local | - | - |  |
| report_all_results.py:90:4 | `df.to_csv(dir_path + '/_results.csv')` |  /  | library / pandas | - | - |  |
| report_all_results.py:92:25 | `df[['energy_arm', 'energy_mem', 'energy_g3d', 'energy_kfc']].sum(ax...` |  /  | library / pandas | - | - |  |
| report_all_results.py:97:29 | `group.mean()` |  /  | unknown / unknown | - | - |  |
| report_all_results.py:97:52 | `group.std()` |  /  | unknown / unknown | - | - |  |
| report_all_results.py:99:44 | `df.groupby('experiment')` |  /  | library / pandas | - | - |  |
| report_all_results.py:99:44 | `df.groupby('experiment').transform(lambda g: replace(g, stds=2))` |  /  | library / pandas | - | - |  |
| report_all_results.py:100:4 | `df.dropna(inplace=True)` |  /  | library / pandas | - | - |  |
| report_all_results.py:102:23 | `df['experiment'].unique()` |  /  | library / pandas | - | - |  |
| report_all_results.py:105:17 | `df.groupby('experiment')` |  /  | library / pandas | - | - |  |
| report_all_results.py:121:29 | `experiment.replace(experiment_pivot + '-lint-', '')` |  /  | local / local | - | - |  |
| report_all_results.py:122:29 | `experiment.replace('-', ' ')` |  /  | local / local | - | - |  |
| report_all_results.py:122:29 | `experiment.replace('-', ' ').title()` |  /  | local / local | - | - |  |
| report_all_results.py:128:13 | `fig.add_subplot(111)` |  /  | library / matplotlib | - | - |  |
| report_all_results.py:129:8 | `sm.graphics.violinplot(consumption_by_experiment, ax=ax, labels=exp...` |  /  | library / statsmodels | - | - |  |
| report_all_results.py:131:8 | `ax.set_ylabel('Energy Consumption (J)')` |  /  | library / matplotlib | - | - |  |
| report_all_results.py:146:14 | `df_without_blankapp['experiment'].apply(lambda x: experiments_witho...` |  /  | library / pandas | - | - |  |
| report_all_results.py:146:64 | `experiments_without_blankapp.index(x)` |  /  | local / local | - | - |  |
| report_all_results.py:150:25 | `axes.get_xlim()` |  /  | library / matplotlib | - | - |  |
| report_all_results.py:150:44 | `axes.get_xlim()` |  /  | library / matplotlib | - | - |  |
| report_all_results.py:167:14 | `df_without_blankapp['experiment'].apply(lambda x: experiments_witho...` |  /  | library / pandas | - | - |  |
| report_all_results.py:167:64 | `experiments_without_blankapp.index(x)` |  /  | local / local | - | - |  |
| report_all_results.py:184:29 | `group[energy_feature].mean()` |  /  | local / local | - | - |  |
| report_all_results.py:185:28 | `group[energy_feature].std()` |  /  | local / local | - | - |  |
| report_all_results.py:192:33 | `group[energy_feature].mean()` |  /  | local / local | - | - |  |
| report_all_results.py:192:64 | `df_experiment_pivot[energy_feature].mean()` |  /  | local / local | - | - |  |
| report_all_results.py:194:53 | `df_experiment_pivot[energy_feature].mean()` |  /  | local / local | - | - |  |
| report_all_results.py:198:4 | `df_statistics.to_csv(dir_path + '/_%s_statistics.csv' % energy_feat...` |  /  | library / pandas | - | - |  |
| report_all_results.py:202:8 | `df_statistics[['n', 'sample_mean', 'sample_std']].to_latex(buf=f)` |  /  | library / pandas | - | - |  |
| report_all_results.py:204:8 | `df_statistics[['welchsttest_statistic', 'welchsttest_p']].to_latex(...` |  /  | library / pandas | - | - |  |
| report_all_results.py:206:8 | `df_statistics[['mean_difference', 'cohensd', 'improvement', 'saving...` |  /  | library / pandas | - | - |  |
| report_all_results.py:208:8 | `df_statistics[['n', 'sample_mean', 'sample_std', 'mean_difference',...` |  /  | library / pandas | - | - |  |
| report_all_results.py:214:9 | `df_energy[power_feature].plot(color='darkblue', linewidth=1.0)` |  /  | local / local | - | - |  |
| report_all_results.py:215:29 | `df_event.iterrows()` |  /  | local / local | - | - |  |
| report_all_results.py:217:8 | `ax.axvline(timestamp, color='darkblue', linestyle='--', alpha=0.5, ...` |  /  | local / local | - | - |  |
| report_all_results.py:219:13 | `df_energy[power_feature].max()` |  /  | local / local | - | - |  |
| report_all_results.py:219:46 | `df_energy[power_feature].min()` |  /  | local / local | - | - |  |
| report_all_results.py:220:13 | `df_energy[power_feature].max()` |  /  | local / local | - | - |  |
| report_all_results.py:223:4 | `ax.annotate('t0 - InteractionStarted', xy=(df_event.loc['Interactio...` |  /  | local / local | - | - |  |
| report_all_results.py:226:4 | `ax.annotate('tn - InteractionEnded', xy=(df_event.loc['InteractionE...` |  /  | local / local | - | - |  |
| report_all_results.py:232:13 | `df_energy[power_feature].max()` |  /  | local / local | - | - |  |
| report_all_results.py:232:46 | `df_energy[power_feature].min()` |  /  | local / local | - | - |  |
| report_all_results.py:233:8 | `ax.text(textX, textY, 'Area=%.2fJ' % energy_consumption, ha='center...` |  /  | local / local | - | - |  |
| report_all_results.py:234:4 | `ax.set_ylabel('Power (W)')` |  /  | local / local | - | - |  |
| report_all_results.py:235:4 | `ax.set_xlabel('Timestamp (s)')` |  /  | local / local | - | - |  |
| report_all_results.py:236:4 | `ax.get_xaxis()` |  /  | local / local | - | - |  |
| report_all_results.py:236:4 | `ax.get_xaxis().get_offset_text()` |  /  | local / local | - | - |  |
| report_all_results.py:236:4 | `ax.get_xaxis().get_offset_text().set_visible(False)` |  /  | local / local | - | - |  |
| report_all_results.py:239:8 | `ax.set_ylim([0, ymax])` |  /  | local / local | - | - |  |
| report_all_results.py:245:4 | `ax.fill_between(df_energy_to_fill.index, 0, df_energy_to_fill[power...` |  /  | local / local | - | - |  |
| report_all_results.py:258:9 | `df[consumption_feature].plot()` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:23:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:24:25 | `vc.findViewById('me.writeily:id/fab_expand_menu_button')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:26:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:27:10 | `vc.findViewById('me.writeily:id/create_folder')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:28:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:30:10 | `vc.findViewWithText(u'Create')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:37:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:38:25 | `vc.findViewById('me.writeily:id/fab_expand_menu_button')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:40:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:41:25 | `vc.findViewById('me.writeily:id/create_note')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:43:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:45:10 | `vc.findViewById('me.writeily:id/note_content')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:45:60 | `vc.findViewById('id/no_id/14')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:47:10 | `vc.findViewWithContentDescription(u'Navigate up')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:49:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:50:6 | `vc.findViewWithContentDescription(u'More options')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:51:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:52:6 | `vc.findViewWithText(u'Settings')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:53:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:54:6 | `vc.findViewWithContentDescription(u'Navigate up')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:64:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:65:10 | `vc.findViewWithText('folder-one')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:75:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:76:10 | `vc.findViewWithText('folder-two')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:79:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:80:10 | `vc.findViewWithText('folder-two')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:83:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:84:10 | `vc.findViewWithText('folder-two')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:89:8 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:90:14 | `vc.findViewWithText('folder-one')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:96:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:97:10 | `vc.findViewWithText('folder-two')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:99:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:101:9 | `vc.findViewWithText(u'note-two')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:102:10 | `vc.findViewWithText(u'note-three')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:103:10 | `vc.findViewWithText(u'note-four')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:105:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:106:10 | `vc.findViewWithContentDescription(u'Move')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:107:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:108:10 | `vc.findViewWithText(u'folder-one')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:109:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:110:10 | `vc.findViewWithText(u'Move here')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:111:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:116:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:118:9 | `vc.findViewWithText(u'folder-one')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:120:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:121:10 | `vc.findViewWithContentDescription(u'Move')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:122:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:123:10 | `vc.findViewWithText(u'folder-three')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:124:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:125:10 | `vc.findViewWithText(u'Move here')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:127:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:128:9 | `vc.findViewWithText(u'folder-three')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:130:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:131:10 | `vc.findViewWithContentDescription(u'Delete')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:132:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/writely-pro-view_holder.py:133:10 | `vc.findViewWithText(u'OK')` |  /  | local / local | - | - |  |
| tests/hold.py:7:9 | `MonkeyRunner.waitForConnection(timeout=60, deviceId=serialno)` |  /  | library / com | - | - |  |
| tests/hold.py:10:0 | `device.touch(x, y, MonkeyDevice.DOWN)` |  /  | library / com | - | - |  |
| tests/hold.py:11:0 | `MonkeyRunner.sleep(no_of_seconds)` |  /  | library / com | - | - |  |
| tests/hold.py:13:0 | `device.touch(x, y, MonkeyDevice.UP)` |  /  | library / com | - | - |  |
| tests/simplegallery.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/simplegallery.py:18:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:19:8 | `vc.findViewWithText(u'Allow')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:26:8 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:27:14 | `vc.findViewById('com.simplemobiletools.gallery:id/dir_name')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:27:78 | `vc.findViewById('id/no_id/18')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:30:8 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:31:21 | `vc.findViewById('com.simplemobiletools.gallery:id/media_item_holder')` |  /  | local / local | - | - |  |
| tests/simplegallery.py:31:94 | `vc.findViewById('id/no_id/11')` |  /  | local / local | - | - |  |
| tests/gnucash.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/gnucash.py:18:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:19:6 | `vc.findViewWithTextOrRaise(u'Next')` |  /  | local / local | - | - |  |
| tests/gnucash.py:23:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:24:6 | `vc.findViewWithTextOrRaise(u'Disable crash reports')` |  /  | local / local | - | - |  |
| tests/gnucash.py:27:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:28:8 | `vc.findViewWithText(u'Allow')` |  /  | local / local | - | - |  |
| tests/gnucash.py:31:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:32:6 | `vc.findViewWithTextOrRaise(u'Assets')` |  /  | local / local | - | - |  |
| tests/gnucash.py:33:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:34:15 | `vc.findViewWithContentDescriptionOrRaise(u'More options')` |  /  | local / local | - | - |  |
| tests/gnucash.py:36:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:37:15 | `vc.findViewWithTextOrRaise(u'Edit Account')` |  /  | local / local | - | - |  |
| tests/gnucash.py:43:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/gnucash.py:44:10 | `vc.findViewWithTextOrRaise(account)` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:18:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:19:6 | `vc.findViewWithTextOrRaise(u'Continue')` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:20:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:21:15 | `vc.findViewWithContentDescription(u'Color')` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:28:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/acrylicpaint.py:29:17 | `vc.findViewById('id/no_id/1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/talalarmo.py:18:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:19:12 | `vc.findViewWithText(u'Tap here\nto set alarm')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:23:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:24:15 | `vc.findViewById('id/no_id/19')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:24:49 | `vc.findViewById('id/no_id/9')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:25:14 | `vc.findViewWithText(u'OFF')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:25:45 | `vc.findViewWithText(u'ON')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:26:14 | `vc.findViewById('id/no_id/21')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:26:48 | `vc.findViewById('id/no_id/11')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:32:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:41:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:42:15 | `vc.findViewWithText(u'Settings')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:44:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:45:10 | `vc.findViewWithText(u'Theme')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:46:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/talalarmo.py:47:10 | `vc.findViewWithText(next_theme)` |  /  | local / local | - | - |  |
| tests/test_helper.py:11:4 | `view.touch()` |  /  | local / local | - | - |  |
| tests/test_helper.py:13:16 | `view.getXY()` |  /  | local / local | - | - |  |
| tests/test_helper.py:14:25 | `view.getWidth()` |  /  | local / local | - | - |  |
| tests/test_helper.py:14:46 | `view.getHeight()` |  /  | local / local | - | - |  |
| tests/test_helper.py:18:4 | `device.type(text)` |  /  | local / local | - | - |  |
| tests/test_helper.py:23:4 | `device.shell('input keyevent KEYCODE_BACK')` |  /  | local / local | - | - |  |
| tests/test_helper.py:33:12 | `view.getXY()` |  /  | local / local | - | - |  |
| tests/test_helper.py:34:15 | `view.getWidth()` |  /  | local / local | - | - |  |
| tests/test_helper.py:34:36 | `view.getHeight()` |  /  | local / local | - | - |  |
| tests/test_helper.py:45:4 | `device.drag(s, e, 500, 20, -1)` |  /  | local / local | - | - |  |
| tests/test_helper.py:56:4 | `json_data.update({serialno: interaction})` |  /  | library / json | - | - |  |
| tests/uhabits.py:14:19 | `ViewClient.connectToDeviceOrExit(**kwargs1)` |  /  | local / local | - | - |  |
| tests/uhabits.py:20:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:22:10 | `vc.findViewWithContentDescription(u'Add habit')` |  /  | local / local | - | - |  |
| tests/uhabits.py:23:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:25:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:26:17 | `vc.findViewWithText(u'Save')` |  /  | local / local | - | - |  |
| tests/uhabits.py:33:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:34:10 | `vc.findViewWithTextOrRaise(habit_name)` |  /  | local / local | - | - |  |
| tests/uhabits.py:35:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:38:10 | `vc.findViewWithContentDescription(u'Navigate up')` |  /  | local / local | - | - |  |
| tests/uhabits.py:41:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:42:12 | `vc.findViewById('org.isoron.uhabits:id/next')` |  /  | local / local | - | - |  |
| tests/uhabits.py:42:61 | `vc.findViewById('id/no_id/23')` |  /  | local / local | - | - |  |
| tests/uhabits.py:49:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:50:6 | `vc.findViewWithContentDescription(u'More options')` |  /  | local / local | - | - |  |
| tests/uhabits.py:51:0 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:52:6 | `vc.findViewWithText(u'About')` |  /  | local / local | - | - |  |
| tests/uhabits.py:66:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:69:13 | `vc.findViewWithText(habit_name)` |  /  | local / local | - | - |  |
| tests/uhabits.py:70:10 | `vc.findViewWithContentDescription(u'More options')` |  /  | local / local | - | - |  |
| tests/uhabits.py:71:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:72:10 | `vc.findViewWithText('Delete')` |  /  | local / local | - | - |  |
| tests/uhabits.py:73:4 | `vc.dump(window='-1')` |  /  | local / local | - | - |  |
| tests/uhabits.py:74:10 | `vc.findViewWithText('OK')` |  /  | local / local | - | - |  |
