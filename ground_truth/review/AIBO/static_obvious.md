# AIBO — static_obvious (487 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| run.py:23:9 | `argparse.ArgumentParser()` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| run.py:40:14 | `eval(f'synthetic.{args.func}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:65:10 | `Exception('function not defined')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:71:55 | `re.split('_\|-', args.method)` | library / re | library / re | direct_import | static_obvious | v: direct import-backed API call |
| run.py:83:15 | `float(acqf_mode[3:])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:88:7 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:89:11 | `AIBO(f=f, fname=fname, lb=f.lb, ub=f.ub, n_init=50, max_evals=args....` | library / AIBO | library / AIBO | direct_import | static_obvious | v: direct import-backed API call |
| run.py:117:4 | `AIBO.optimize()` | library / AIBO | library / AIBO | direct_import | static_obvious | v: direct import-backed API call |
| run.py:118:4 | `print('cost time:', time.time() - t0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:118:23 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:119:4 | `print('=' * 20)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:124:9 | `np.random.rand(f.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:127:7 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:128:9 | `cma.CMAEvolutionStrategy(x0=x0, sigma0=sigma0, inopts={'bounds': [0...` | library / cma | library / cma | direct_import | static_obvious | v: direct import-backed API call |
| run.py:147:11 | `f(np.array(f.lb) + (np.array(f.ub) - np.array(f.lb)) * x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| run.py:147:13 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:147:29 | `np.array(f.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:147:44 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:149:15 | `len(xs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:150:19 | `len(xs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:154:12 | `print(es.sigma)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:155:12 | `print('{}) {} fbest={}'.format(n_evals, args.func, es.best.f))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:155:18 | `'{}) {} fbest={}'.format(n_evals, args.func, es.best.f)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:157:4 | `print('best y:', es.best.f)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:158:4 | `print('best x:', es.best.x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:159:4 | `print('cost time:', time.time() - t0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:159:23 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:169:7 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:186:4 | `print('cost time:', time.time() - t0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:186:23 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:189:15 | `np.argmin(fX)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:191:4 | `print('best x:', x_best)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:192:4 | `print('best y:', f_best)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:201:7 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:202:59 | `np.zeros(f.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:202:79 | `np.ones(f.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:224:11 | `f(np.array(f.lb) + (np.array(f.ub) - np.array(f.lb)) * x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| run.py:224:13 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:224:29 | `np.array(f.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:224:44 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:225:21 | `np.array(y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:225:21 | `np.array(y).reshape(-1, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:228:17 | `len(xs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:229:15 | `len(xs)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:231:12 | `print('{}) {} fbest={}'.format(n_evals, args.func, algorithm.result...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:231:18 | `'{}) {} fbest={}'.format(n_evals, args.func, algorithm.result().F[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:234:4 | `print('best y:', res.F[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:235:4 | `print('cost time:', time.time() - t0)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:235:23 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:240:14 | `np.random.rand()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:242:12 | `ng.p.Array(init=init)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:242:12 | `ng.p.Array(init=init).set_bounds(lower=f.lb, upper=f.ub)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:243:10 | `ng.optimizers.RandomSearch(parametrization=param, budget=args.iters...` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:258:15 | `range(0, len(f.lb))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:258:24 | `len(f.lb)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:259:8 | `bounds.append((float(f.lb[idx]), float(f.ub[idx])))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:259:25 | `float(f.lb[idx])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:259:43 | `float(f.ub[idx])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:260:10 | `scipy.optimize.dual_annealing(f, bounds=bounds, maxfun=args.iters, ...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:265:4 | `print('best y:', res.fun)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:269:14 | `np.random.rand()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:271:12 | `ng.p.Array(init=init)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:271:12 | `ng.p.Array(init=init).set_bounds(lower=f.lb, upper=f.ub)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:272:9 | `ng.optimizers.DE(parametrization=param, budget=args.iters, num_work...` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:278:12 | `ng.p.Array(init=init)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:278:12 | `ng.p.Array(init=init).set_bounds(lower=f.lb, upper=f.ub)` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:279:10 | `ng.optimizers.NGOpt(parametrization=param, budget=args.iters, num_w...` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:282:4 | `print('best y:', f(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:286:12 | `ng.p.Array(init=0.5 * (f.lb + f.ub))` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:286:12 | `ng.p.Array(init=0.5 * (f.lb + f.ub)).set_bounds(lower=f.lb, upper=f...` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:287:9 | `ng.optimizers.GeneticDE(parametrization=param, budget=args.iters, n...` | library / nevergrad | library / nevergrad | direct_import | static_obvious | v: direct import-backed API call |
| run.py:290:4 | `print('best y:', f(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:296:15 | `range(0, len(f.lb))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:296:24 | `len(f.lb)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:297:8 | `bounds.append((float(f.lb[idx]), float(f.ub[idx])))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:297:25 | `float(f.lb[idx])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:297:43 | `float(f.ub[idx])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:298:10 | `scipy.optimize.minimize(f, x0=np.array(f.lb) + (np.array(f.ub) - np...` | library / scipy | library / scipy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:299:33 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:299:51 | `np.array(f.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:299:72 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:299:88 | `np.random.rand(f.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:307:7 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:307:25 | `np.array(f.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:307:40 | `np.array(f.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:307:56 | `np.random.rand(f.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| run.py:308:9 | `pybobyqa.solve(f, x0, bounds=(f.lb, f.ub), maxfun=args.iters)` | library / pybobyqa | library / pybobyqa | direct_import | static_obvious | v: direct import-backed API call |
| run.py:309:4 | `print('best y:', soln.f)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| run.py:313:7 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| run.py:327:4 | `print('no such method')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:13:25 | `float('inf')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:18:8 | `os.makedirs('result/' + foldername, exist_ok=True)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:21:71 | `str(len(self.results))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:21:75 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:22:28 | `json.dumps(self.results)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:23:13 | `open(trace_path, 'a')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:24:12 | `f.write(final_results_str + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:31:12 | `print('')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:32:12 | `print('=' * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:33:12 | `print('iteration:', self.counter, 'total samples:', len(self.results))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:33:64 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:34:12 | `print('=' * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:35:12 | `print('current best f(x):', self.curt_best)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:36:12 | `print('current best x:', np.around(self.curt_best_x, decimals=2))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:36:37 | `np.around(self.curt_best_x, decimals=2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:39:11 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:45:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:46:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:48:23 | `tracker('Griewank' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/test.py:48:42 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:52:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:54:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/test.py:57:17 | `np.sum(x ** 2 / 4000)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:57:35 | `np.prod(np.cos(x / np.sqrt(1 + np.arange(self.dim))))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:57:43 | `np.cos(x / np.sqrt(1 + np.arange(self.dim)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:57:52 | `np.sqrt(1 + np.arange(self.dim))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:57:62 | `np.arange(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:64:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:65:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:70:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:73:17 | `np.sum(x ** 2 / 4000, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:73:43 | `np.prod(np.cos(x / np.sqrt(1 + np.arange(self.dim))), axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:73:51 | `np.cos(x / np.sqrt(1 + np.arange(self.dim)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:73:60 | `np.sqrt(1 + np.arange(self.dim))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:73:70 | `np.arange(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:77:5 | `Griewank(dim=dims)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/test.py:78:5 | `Griewank_parallel(dim=dims)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/test.py:80:4 | `np.random.rand(10, dims)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:81:5 | `np.array([f1(x) for x in X])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/test.py:81:15 | `f1(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/test.py:82:5 | `f2(X)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/test.py:83:0 | `print(y1 - y2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/lasso.py:17:26 | `LassoBench.SyntheticBenchmark(pick_bench='synt_hard', noise=noise)` | library / LassoBench | library / LassoBench | direct_import | static_obvious | v: direct import-backed API call |
| functions/lasso.py:20:23 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/lasso.py:21:22 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/lasso.py:26:23 | `tracker(dir_name + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/lasso.py:30:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/lasso.py:32:15 | `np.all(x <= self.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/lasso.py:32:40 | `np.all(x >= self.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:15:18 | `np.array(self.xmin)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:16:18 | `np.array(self.xmax)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:25:23 | `tracker('RobotPush14' + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:30:15 | `np.linalg.norm(np.array(self.gxy) - np.array(self.sxy))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:30:30 | `np.array(self.gxy)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:30:51 | `np.array(self.sxy)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:31:14 | `np.linalg.norm(np.array(self.gxy2) - np.array(self.sxy2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:31:29 | `np.array(self.gxy2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:31:51 | `np.array(self.sxy2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:39:13 | `float(argv[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:40:13 | `float(argv[1])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:41:15 | `float(argv[2])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:42:15 | `float(argv[3])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:43:21 | `int(float(argv[4]) * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:43:25 | `float(argv[4])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:44:21 | `float(argv[5])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:45:14 | `float(argv[6])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:46:14 | `float(argv[7])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:47:16 | `float(argv[8])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:48:16 | `float(argv[9])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:49:22 | `int(float(argv[10]) * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:49:26 | `float(argv[10])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:50:22 | `float(argv[11])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:51:15 | `float(argv[12])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:52:16 | `float(argv[13])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:55:17 | `range(3)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:58:20 | `b2WorldInterface(False)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:62:19 | `make_base(500, 500, world)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:63:19 | `create_body(base, world, 'rectangle', (0.5, 0.5), ofriction, odensi...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:64:20 | `create_body(base, world, 'circle', 1, ofriction, odensity, self.sxy2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:66:20 | `end_effector(world, (rx, ry), base, init_angle, hand_shape, hand_size)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:67:21 | `end_effector(world, (rx2, ry2), base, init_angle2, hand_shape, hand...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:68:27 | `run_simulation(world, body, body2, robot, robot2, xvel, yvel, xvel2...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:71:19 | `np.linalg.norm(np.array(self.gxy) - ret1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:71:34 | `np.array(self.gxy)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:72:19 | `np.linalg.norm(np.array(self.gxy2) - ret2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:72:34 | `np.array(self.gxy2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:74:17 | `np.mean(results)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:80:8 | `PushReward()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:81:8 | `np.random.uniform(f.xmin, f.xmax)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/robot_push.py:82:4 | `print('Input = {}'.format(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:82:10 | `'Input = {}'.format(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:83:4 | `print('Output = {}'.format(f(x)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:83:10 | `'Output = {}'.format(f(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/robot_push.py:83:31 | `f(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/robot_push.py:87:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/push_utils.py:15:22 | `pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), 0,...` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:16:8 | `pygame.display.set_caption('push simulator')` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:17:21 | `pygame.time.Clock()` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:34:12 | `pygame.draw.polygon(self.screen, color, vertices)` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:42:12 | `pygame.draw.circle(self.screen, color, [int(x) for x in position], ...` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:42:52 | `int(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:43:63 | `int(circle.radius * self.PPM)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:53:8 | `pygame.display.flip()` | library / pygame | library / pygame | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:82:11 | `type(new_bodies)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:109:18 | `Exception('%s is not a correct shape' % hand_shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:143:16 | `list(self.hand.position)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:144:16 | `list(self.hand.linearVelocity)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:165:14 | `Exception('%s is not a correct shape' % body_shape)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:207:29 | `np.min(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:207:40 | `np.max(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:207:51 | `np.min(y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:207:62 | `np.max(y)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:210:23 | `zip(centers, boxlen)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:223:18 | `np.array([xvel, yvel])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:224:35 | `np.random.normal(0, 1e-06)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:224:79 | `np.random.normal(0, 1e-06)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:226:19 | `np.array([xvel2, yvel2])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:227:37 | `np.random.normal(0, 1e-06)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:227:82 | `np.random.normal(0, 1e-06)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:229:11 | `np.max([simulation_steps, simulation_steps2])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/push_utils.py:230:13 | `range(tmax + 100)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:237:12 | `list(body.position)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/push_utils.py:237:33 | `list(body2.position)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:9:8 | `np.array([[0.11353145, 0.17251116], [0.4849413, 0.7684513], [0.3884...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:43:12 | `np.array([[0.5, 0.5]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:47:12 | `AABoxes(l, h)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:48:12 | `NegGeom(AABoxes(r_l, r_h))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:48:20 | `AABoxes(r_l, r_h)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:49:16 | `UnionGeom([trees, r_box])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:51:12 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:52:11 | `np.array([0.95, 0.95])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:54:13 | `ConstObstacleCost(obstacles, cost=20.0)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:54:53 | `ConstCost(0.05)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:55:14 | `AdditiveCosts(costs)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:60:27 | `create_cost_small()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:63:11 | `PointBSpline(dim=2, num_points=n_points)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:65:13 | `RoverDomain(cost_fn, start=start, goal=goal, traj=traj, s_range=np....` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:69:33 | `np.array([[-0.1, -0.1], [1.1, 1.1]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:75:8 | `np.array([[0.43143755, 0.20876147], [0.38485367, 0.39183579], [0.02...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:192:12 | `np.array([[0.5, 0.5]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:196:12 | `AABoxes(l, h)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:197:12 | `NegGeom(AABoxes(r_l, r_h))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:197:20 | `AABoxes(r_l, r_h)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:198:16 | `UnionGeom([trees, r_box])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:200:12 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:201:11 | `np.array([0.95, 0.95])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:203:13 | `ConstObstacleCost(obstacles, cost=20.0)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:203:53 | `ConstCost(0.05)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:204:14 | `AdditiveCosts(costs)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:212:27 | `create_cost_large()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:215:11 | `PointBSpline(dim=2, num_points=n_points)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:217:13 | `RoverDomain(cost_fn, start=start, goal=goal, traj=traj, start_miss_...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:225:33 | `np.array([[-0.1, -0.1], [1.1, 1.1]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:243:15 | `np.array([np.zeros(self.x_range[0].shape[0]), np.ones(self.x_range[...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:243:25 | `np.zeros(self.x_range[0].shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:243:61 | `np.ones(self.x_range[0].shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:259:16 | `np.linalg.norm(x - point, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:261:9 | `create_large_domain(force_start=False, force_goal=False, start_miss...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:266:14 | `np.repeat(domain.s_range, n_points, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:268:4 | `ConstantOffsetFn(domain, f_max)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:269:4 | `NormalizedInputFn(f, raw_x_range)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:274:23 | `np.zeros(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:275:23 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:292:23 | `tracker('Rover60' + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:296:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:298:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:300:18 | `f(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:323:6 | `Rover()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:324:8 | `np.random.uniform(f.lb, f.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:325:8 | `np.array([0.02224671, 0.03499271, 0.49767277, 0.34999153, 0.0374352...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:338:8 | `np.array([0.35934683, 0.2623912, 0.06570075, 0.33132122, 0.05750078...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:351:8 | `np.array([0.10176738, 0.42303871, 0.26771983, 0.03132122, 0.1879091...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:364:8 | `np.array([0.64874394, 0.15119416, 0.00807727, 0.26699075, 0.0412074...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:377:8 | `np.array([0.0466706877, 0.654414015, 0.218211757, 3.26349805e-05, 0...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover.py:392:4 | `print('Input = {}'.format(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:392:10 | `'Input = {}'.format(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:393:4 | `print('Output = {}'.format(f(x)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:393:10 | `'Output = {}'.format(f(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover.py:393:31 | `f(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover.py:397:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:13:25 | `float('inf')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:18:8 | `os.makedirs('result/' + foldername, exist_ok=True)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:21:71 | `str(len(self.results))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:21:75 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:22:28 | `json.dumps(self.results)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:23:13 | `open(trace_path, 'a')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:24:12 | `f.write(final_results_str + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:31:12 | `print('')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:32:12 | `print('=' * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:33:12 | `print('iteration:', self.counter, 'total samples:', len(self.results))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:33:64 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:34:12 | `print('=' * 10)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:35:12 | `print('current best f(x):', self.curt_best)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:36:12 | `print('current best x:', np.around(self.curt_best_x, decimals=2))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:36:37 | `np.around(self.curt_best_x, decimals=2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:39:11 | `len(self.results)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:45:25 | `float('inf')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:50:8 | `os.makedirs('result/' + foldername, exist_ok=True)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:51:27 | `datetime.now()` | library / datetime | library / datetime | direct_import | static_obvious | v: import-backed dotted module call: datetime.now |
| functions/synthetic.py:57:22 | `json.dumps(result_dict)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:58:13 | `open(self.trace_path, 'a')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:59:12 | `f.write(results_str + '\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:66:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:67:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:69:8 | `print('####dim:', dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:70:23 | `tracker('Levy' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:70:38 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:73:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:75:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:77:15 | `np.all(x <= self.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:77:40 | `np.all(x >= self.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:79:19 | `range(0, len(x))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:79:28 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:81:12 | `np.array(w)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:83:18 | `np.sin(np.pi * w[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:85:43 | `np.sin(2 * np.pi * w[-1])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:89:19 | `range(1, len(w))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:89:28 | `len(w)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:91:43 | `np.sin(np.pi * wi + 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:104:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:105:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:107:23 | `tracker('Ackley' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:107:40 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:110:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:112:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:115:22 | `np.exp(-0.2 * np.sqrt(np.inner(x, x) / x.size))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:115:36 | `np.sqrt(np.inner(x, x) / x.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:115:44 | `np.inner(x, x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:115:72 | `np.exp(np.cos(2 * np.pi * x).sum() / x.size)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:115:79 | `np.cos(2 * np.pi * x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:115:79 | `np.cos(2 * np.pi * x).sum()` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:122:31 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:123:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:125:23 | `tracker('Rastrigin' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:125:43 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:129:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:131:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:135:31 | `np.sum(x ** 2 - 10 * np.cos(2 * np.pi * x))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:135:46 | `np.cos(2 * np.pi * x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:142:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:143:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:145:23 | `tracker('Rosenbrock' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:145:44 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:149:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:151:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:155:17 | `range(self.dim - 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:165:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:166:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:168:23 | `tracker('Griewank' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:168:42 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:172:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:174:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:177:17 | `np.sum(x ** 2 / 4000)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:177:35 | `np.prod(np.cos(x / np.sqrt(1 + np.arange(self.dim))))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:177:43 | `np.cos(x / np.sqrt(1 + np.arange(self.dim)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:177:52 | `np.sqrt(1 + np.arange(self.dim))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:177:62 | `np.arange(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:184:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:185:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:187:23 | `tracker('Schwefel' + str(dim) + '/' + foldername, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/synthetic.py:187:42 | `str(dim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:191:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:193:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:196:37 | `np.sum(x * np.sin(np.sqrt(np.abs(x))))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:196:46 | `np.sin(np.sqrt(np.abs(x)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:196:53 | `np.sqrt(np.abs(x))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:196:61 | `np.abs(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:204:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:205:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:209:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:21 | `np.exp(-0.2 * np.sqrt(np.mean(x * x, 1)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:35 | `np.sqrt(np.mean(x * x, 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:43 | `np.mean(x * x, 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:62 | `np.exp(np.mean(np.cos(2 * np.pi * x), 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:69 | `np.mean(np.cos(2 * np.pi * x), 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:210:77 | `np.cos(2 * np.pi * x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:217:31 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:218:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:223:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:228:31 | `np.sum(x ** 2 - 10 * np.cos(2 * np.pi * x), axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:228:46 | `np.cos(2 * np.pi * x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:234:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:235:28 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:240:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:243:15 | `np.zeros(len(x))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:243:24 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:244:17 | `range(self.dim - 1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/synthetic.py:252:30 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:253:29 | `np.ones(dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:258:12 | `np.array(x)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:261:17 | `np.sum(x ** 2 / 4000, axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:261:43 | `np.prod(np.cos(x / np.sqrt(1 + np.arange(self.dim))), axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:261:51 | `np.cos(x / np.sqrt(1 + np.arange(self.dim)))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:261:60 | `np.sqrt(1 + np.arange(self.dim))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/synthetic.py:261:70 | `np.arange(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:47:21 | `np.hstack((start[:, None], points))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:50:21 | `np.hstack((points, goal[:, None]))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:55:25 | `zip(self.tck[1], start)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:59:25 | `zip(self.tck[1], goal)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:64:15 | `np.vstack(si.splev(t, self.tck))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:72:16 | `np.exp(-np.sum(((x - point) / 0.25) ** 2))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:72:24 | `np.sum(((x - point) / 0.25) ** 2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:116:30 | `np.random.RandomState(np.random.randint(0, 2 ** 32 - 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:116:52 | `np.random.randint(0, 2 ** 32 - 1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:131:38 | `np.linspace(0, 1.0, n_samples, endpoint=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:137:12 | `np.linalg.norm(points[1:] - points[:-1], axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:138:21 | `np.sum(l * avg_cost)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:180:15 | `np.any(np.hstack([g.contains(X) for g in self.geoms]), axis=1, keep...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:180:22 | `np.hstack([g.contains(X) for g in self.geoms])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:199:15 | `np.ones((X.shape[0], 1))` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:207:15 | `np.sum(np.hstack([f(X) for f in self.fns]), axis=1)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:207:22 | `np.hstack([f(X) for f in self.fns])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:207:33 | `f(X)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:218:21 | `np.ones(centers.shape[0])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:224:15 | `np.exp(-np.sum(((X[:, :, None] - self.c.T[None, :, :]) / self.s.T[N...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:224:15 | `np.exp(-np.sum(((X[:, :, None] - self.c.T[None, :, :]) / self.s.T[N...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:224:23 | `np.sum(((X[:, :, None] - self.c.T[None, :, :]) / self.s.T[None, :, ...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:230:14 | `np.linspace(mi, ma, ngrid_points, endpoint=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:230:77 | `zip(*roverdomain.s_range)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:231:18 | `np.meshgrid(*points)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:232:13 | `np.hstack([g.reshape((-1, 1)) for g in grid_points])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:241:46 | `np.linspace(0.0, 1.0, ntraj_points, endpoint=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:244:14 | `'traj cost: {0}'.format(traj_cost)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:245:4 | `print('traj cost: {0}'.format(traj_cost))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:245:10 | `'traj cost: {0}'.format(traj_cost)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:262:16 | `zip(rectangles.l, rectangles.h)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:271:52 | `range(len(vert_ind[0]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:271:58 | `len(vert_ind[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:271:87 | `range(len(vert_ind))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:271:93 | `len(vert_ind)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:272:49 | `range(len(faces[0]))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:272:55 | `len(faces[0])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:272:81 | `range(len(faces))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:272:87 | `len(faces)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:289:46 | `np.linspace(0.0, 1.0, ntraj_points, endpoint=True)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:292:27 | `generate_verts(rectangles)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:302:11 | `zip(traj_points[:-1, :], traj_points[1:, :])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:303:24 | `Line3DCollection(seg, colors=[(0, 1.0, 0, 1.0)] * len(seg))` | library / mpl_toolkits | library / mpl_toolkits | mpl_toolkits_callable | static_obvious | v: direct import from mpl_toolkits.mplot3d.art3d |
| functions/rover_utils.py:303:72 | `len(seg)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/rover_utils.py:306:24 | `Poly3DCollection(poly3d, facecolors=(0.7, 0.7, 0.7, 1.0), linewidth...` | library / mpl_toolkits | library / mpl_toolkits | mpl_toolkits_callable | static_obvious | v: direct import from mpl_toolkits.mplot3d.art3d |
| functions/rover_utils.py:317:13 | `np.array([[1.0, 1.0], [1.0, 0.0]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:318:12 | `np.ones(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:319:14 | `GMCost(center, sigma)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:320:12 | `np.zeros(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:321:11 | `np.ones(2)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:323:11 | `PointBSpline(dim=2, num_points=3)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:324:8 | `np.array([[0.1, 0.5], [0.3, 1.3], [0.75, 1.2]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:327:13 | `RoverDomain(cost_fn, start=start, goal=goal, traj=traj, s_range=np....` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:331:33 | `np.array([[0.0, 0.0], [2.0, 2.0]])` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/rover_utils.py:334:4 | `plot_2d_rover(domain)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/rover_utils.py:340:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/mujoco.py:11:23 | `np.array([1.41599384, -0.05478602, -0.25522216, -0.25404721, 0.2752...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:14:23 | `np.array([0.19805723, 0.07824488, 0.17120271, 0.32000514, 0.6240188...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:18:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:19:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:21:23 | `gym.make('Hopper-v2')` | library / gym | library / gym | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:25:27 | `tracker('Hopper' + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/mujoco.py:36:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:38:15 | `np.all(x <= self.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:38:40 | `np.all(x >= self.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:38:62 | `'x={}'.format(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:46:17 | `range(self.num_rollouts)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:54:25 | `np.dot(M, inputs)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:63:8 | `print(returns)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:64:28 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:65:15 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:69:23 | `gym.make('HalfCheetah-v2')` | library / gym | library / gym | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:71:20 | `np.array([-0.09292823, 0.07602245, 0.08993747, 0.02011249, 0.079815...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:77:23 | `np.array([0.06852463, 0.35843727, 0.37874848, 0.36028137, 0.4058822...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:84:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:85:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:90:27 | `tracker('HalfCheetah102' + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/mujoco.py:101:21 | `np.dot(M, inputs)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:111:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:113:15 | `np.all(x <= self.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:113:40 | `np.all(x >= self.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:113:62 | `'x={}'.format(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:119:17 | `range(self.num_rollouts)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:122:15 | `len(returns)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:122:34 | `np.std(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:122:50 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:125:28 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:126:15 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:131:23 | `gym.make('Ant-v2')` | library / gym | library / gym | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:132:20 | `np.array([0.556454034, 0.918653169, -0.00359727363, -0.0620272098, ...` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:161:23 | `np.array([0.0982386131, 0.171413676, 0.0923065066, 0.0985791366, 0....` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:191:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:192:28 | `np.ones(self.dim)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:197:27 | `tracker('Ant' + '/' + method, verbose=verbose)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| functions/mujoco.py:203:15 | `len(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:205:15 | `np.all(x <= self.ub)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:205:40 | `np.all(x >= self.lb)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:205:62 | `'x={}'.format(x)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:213:17 | `range(self.num_rollouts)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| functions/mujoco.py:221:25 | `np.dot(M, inputs)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:231:28 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| functions/mujoco.py:232:15 | `np.mean(returns)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
