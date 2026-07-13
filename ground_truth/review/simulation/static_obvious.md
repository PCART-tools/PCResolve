# simulation — static_obvious (149 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| plot_results.py:30:0 | `matplotlib.use('agg', warn=False, force=True)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:45:10 | `np.loadtxt(file_name_0, skiprows=1, delimiter=',', encoding='utf-8')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:46:10 | `np.loadtxt(file_name_1, skiprows=1, delimiter=',', encoding='utf-8')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:47:11 | `np.loadtxt(file_name_2, skiprows=1, delimiter=',', encoding='utf-8')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:48:11 | `np.loadtxt(file_name_3, skiprows=1, delimiter=',', encoding='utf-8')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:49:13 | `np.loadtxt(file_name_4, skiprows=1, delimiter=',', encoding='utf-8')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:52:0 | `sns.set_context('paper')` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:53:0 | `sns.set_palette('tab10', 10)` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:54:0 | `itertools.cycle(sns.color_palette())` | library / itertools | library / itertools | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:54:16 | `sns.color_palette()` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:58:7 | `plt.figure(constrained_layout=False)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:64:5 | `sns.axes_style('whitegrid')` | library / seaborn | library / seaborn | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:74:16 | `enumerate(plot_times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| plot_results.py:76:12 | `next(ax1._get_lines.prop_cycler)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| plot_results.py:87:40 | `'t = {} s'.format(np.int(times))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| plot_results.py:87:58 | `np.int(times)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:94:30 | `FormatStrFormatter('%.4f')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:103:7 | `os.path.exists(output_folder)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| plot_results.py:104:4 | `os.makedirs(output_folder)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:66:20 | `np.zeros((len(times), g.num_cells))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:66:30 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:67:24 | `np.zeros((len(times), g.dim * g.num_cells))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:67:34 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:68:25 | `np.zeros((len(times), len(y_max)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:68:35 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:68:47 | `len(y_max)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:87:12 | `np.tan(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:91:10 | `np.zeros(n_series)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:93:13 | `range(n_series)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:117:13 | `range(len(times))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:117:19 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| analytical.py:120:16 | `np.sum(np.sin(aa_n) / (aa_n - np.sin(aa_n) * np.cos(aa_n)) * (np.co...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:121:14 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:121:39 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:121:54 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:122:15 | `np.cos(aa_n * xc / a)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:122:41 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:123:14 | `np.exp(-aa_n ** 2 * c_f * times[t] / a ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:129:18 | `np.sum(np.sin(aa_n) * np.cos(aa_n) / (aa_n - np.sin(aa_n) * np.cos(...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:130:13 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:130:28 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:131:22 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:131:37 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:132:14 | `np.exp(-aa_n ** 2 * c_f * times[t] / a ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:135:18 | `np.sum(np.cos(aa_n) / (aa_n - np.sin(aa_n) * np.cos(aa_n)) * np.sin...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:136:13 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:136:37 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:136:52 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:137:14 | `np.sin(aa_n * xc / a)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:138:14 | `np.exp(-aa_n ** 2 * c_f * times[t] / a ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:141:17 | `np.sum(np.sin(aa_n) * np.cos(aa_n) / (aa_n - np.sin(aa_n) * np.cos(...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:142:14 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:142:29 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:142:53 | `np.sin(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:142:68 | `np.cos(aa_n)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:143:14 | `np.exp(-aa_n ** 2 * c_f * times[t] / a ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:148:41 | `np.array((ux, uy))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| analytical.py:148:41 | `np.array((ux, uy)).ravel('F')` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:46:19 | `np.where(time_values == x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:54:20 | `np.max(g.cell_diameters())` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:55:14 | `np.arange(0, a, half_max_diam)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:56:35 | `np.array([xc_eval, np.zeros_like(xc_eval)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:56:54 | `np.zeros_like(xc_eval)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:57:13 | `np.unique(closest_cells, return_index=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:58:28 | `np.sort(idx)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:62:17 | `np.zeros([len(time_levels), len(xc_plot)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:62:27 | `len(time_levels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:62:45 | `len(xc_plot)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:63:17 | `np.zeros([len(time_levels), len(xc_plot)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:63:27 | `len(time_levels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:63:45 | `len(xc_plot)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:64:18 | `np.zeros([len(time_levels), len(xc_plot)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:64:28 | `len(time_levels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:64:46 | `len(xc_plot)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:65:18 | `np.zeros([len(time_levels), len(xc_plot)])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:65:28 | `len(time_levels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:65:46 | `len(xc_plot)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:66:16 | `enumerate(time_levels)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:75:11 | `os.path.exists(output_folder)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:76:8 | `os.makedirs(output_folder)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:80:34 | `np.str(time)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:85:15 | `np.reshape(x_dimless, np.array([len(x_dimless), 1]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:85:37 | `np.array([len(x_dimless), 1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:85:47 | `len(x_dimless)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| export_results.py:88:13 | `np.hstack((xdim_col, pn_dimless.T))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:89:4 | `np.savetxt(output_folder + '/' + 'times.csv', plot_times, delimiter...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:97:13 | `np.hstack((xdim_col, pn_dimless.T))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:98:4 | `np.savetxt(output_folder + '/' + 'p_numerical.csv', pn_csv, delimit...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:106:13 | `np.hstack((xdim_col, pe_dimless.T))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:107:4 | `np.savetxt(output_folder + '/' + 'p_exact.csv', pe_csv, delimiter=d...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:112:14 | `np.hstack((xdim_col, uxn_dimless.T))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:113:4 | `np.savetxt(output_folder + '/' + 'ux_numerical.csv', uxn_csv, delim...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:121:14 | `np.hstack((xdim_col, uxe_dimless.T))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| export_results.py:122:4 | `np.savetxt(output_folder + '/' + 'ux_exact.csv', uxe_csv, delimiter...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:36:18 | `np.arange(time_parameters['initial_time'], time_parameters['final_t...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:166:11 | `np.in1d(b_faces, x_min)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:166:11 | `np.in1d(b_faces, x_min).nonzero()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:167:11 | `np.in1d(b_faces, x_max)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:167:11 | `np.in1d(b_faces, x_max).nonzero()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:168:12 | `np.in1d(b_faces, y_min)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:168:12 | `np.in1d(b_faces, y_min).nonzero()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:169:12 | `np.in1d(b_faces, y_max)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:169:12 | `np.in1d(b_faces, y_max).nonzero()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:174:18 | `np.array([None] * b_faces.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:181:14 | `pp.BoundaryCondition(g, b_faces, labels_flow)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:184:21 | `np.zeros(g.num_faces)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:204:18 | `np.array([None] * b_faces.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:211:14 | `pp.BoundaryConditionVectorial(g, b_faces, labels_mech)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:214:21 | `np.zeros((len(times), g.num_faces * g.dim))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:214:31 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| data.py:216:13 | `range(len(times))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| data.py:216:19 | `len(times)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| data.py:235:20 | `dict()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| data.py:280:14 | `np.ones(g.num_cells)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:281:11 | `pp.SecondOrderTensor(kxx)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:290:29 | `np.ones(g.num_cells)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:294:8 | `pp.initialize_default_data(g, d, kw_f, specified_parameters_flow)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:307:19 | `np.ones(g.num_cells)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:308:26 | `np.ones(g.num_cells)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:309:14 | `pp.FourthOrderTensor(mu_lame, lambda_lame)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:320:8 | `pp.initialize_default_data(g, d, kw_m, specified_parameters_mechanics)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:323:4 | `pp.set_state(d, {kw_m: {'bc_values': bc_dict[kw_m]['bc_values'][0]}})` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| data.py:342:4 | `pp.set_state(data_dictionary, state)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:35:4 | `pp.initialize_default_data(g, d, kw_f)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| main.py:36:4 | `pp.initialize_default_data(g, d, kw_m)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| create_grid.py:28:17 | `pp.FractureNetwork2d(None, None, domain)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:48:19 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| discretization.py:48:19 | `super().assemble_matrix_rhs(g, d)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| discretization.py:63:23 | `pp.Biot(kw_m, kw_f, v_0, v_1)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:79:23 | `pp.Mpsa(kw_m)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:82:23 | `ImplicitMpfa(kw_f)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| discretization.py:83:23 | `pp.BiotStabilization(kw_f, v_1)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:85:35 | `pp.GradP(kw_m)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:86:35 | `pp.DivU(kw_m, kw_f, v_0)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| discretization.py:89:16 | `pp.Assembler(gb)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:61:20 | `np.zeros((len(time_values), g.num_cells))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:61:30 | `len(time_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| solve.py:62:20 | `np.zeros((len(time_values), g.dim * g.num_cells))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:62:30 | `len(time_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| solve.py:73:16 | `pp.Assembler(gb)` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:76:13 | `range(len(time_values) - 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| solve.py:76:19 | `len(time_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| solve.py:79:8 | `pp.set_state(d, {variable_m: displacement, variable_f: pressure})` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:80:8 | `pp.set_state(d, {kw_m: {'bc_values': bc_dict[kw_m]['bc_values'][t]}})` | library / porepy | library / porepy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:97:8 | `sys.stdout.write('\rSimulation progress: %d%%' % np.ceil(t / (len(t...` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:99:15 | `np.ceil(t / (len(time_values) - 2) * 100)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:99:29 | `len(time_values)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| solve.py:101:8 | `sys.stdout.flush()` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
| solve.py:103:4 | `sys.stdout.write('\nThe simulation has ended without any errors!\n')` | library / sys | library / sys | direct_import | static_obvious | v: direct import-backed API call |
