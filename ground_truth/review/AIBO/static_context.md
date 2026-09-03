# AIBO — static_context (167 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| run.py:24:0 | `parser.add_argument('--func', help='specify the test function')` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:25:0 | `parser.add_argument('--dim', type=int, help='specify the problem di...` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:26:0 | `parser.add_argument('--method', default='AIBO_mixed-grad-EI')` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:27:0 | `parser.add_argument('--batch-size', type=int, default=10)` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:28:0 | `parser.add_argument('--iters', type=int, help='Total evaluation bud...` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:29:0 | `parser.add_argument('--istrackAF', type=bool, default=False)` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:30:0 | `parser.add_argument('--istrackcands', type=bool, default=False)` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:31:0 | `parser.add_argument('--device', default='cpu')` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:32:0 | `parser.add_argument('--dtype', default='float64')` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:33:0 | `parser.add_argument('--verbose', type=bool, default=False)` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:34:0 | `parser.add_argument('--popsize', type=int, default=50)` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:36:7 | `parser.parse_args()` | library / argparse | library / argparse | argparse_receiver | static_context | v: parser is created by argparse.ArgumentParser |
| run.py:46:8 | `robot_push.PushReward(method=f'{args.method}-{args.batch_size}', ve...` | local / local | local / local | local_constructor | static_context | v: callable is defined in the project-local functions package |
| run.py:50:8 | `rover.Rover(method=f'{args.method}-{args.batch_size}', verbose=args...` | local / local | local / local | local_constructor | static_context | v: callable is defined in the project-local functions package |
| run.py:54:8 | `mujoco.HalfCheetah(method=f'{args.method}-{args.batch_size}', verbo...` | local / local | local / local | local_constructor | static_context | v: callable is defined in the project-local functions package |
| run.py:68:3 | `args.method.startswith('AIBO')` | python / python | python / python | builtin_string_method | static_context | v: receiver is a Python string |
| run.py:82:7 | `acqf_mode.startswith('UCB')` | python / python | python / python | builtin_string_method | static_context | v: receiver is a Python string |
| run.py:145:38 | `es.stop()` | library / cma | library / cma | cma_receiver | static_context | v: es is created by cma.CMAEvolutionStrategy |
| run.py:146:13 | `es.ask()` | library / cma | library / cma | cma_receiver | static_context | v: es is created by cma.CMAEvolutionStrategy |
| run.py:148:8 | `es.tell(xs, y)` | library / cma | library / cma | cma_receiver | static_context | v: es is created by cma.CMAEvolutionStrategy |
| run.py:185:4 | `turbo1.optimize()` | library / baselines | library / baselines | receiver_return | static_context | v: receiver is returned by the import-backed baselines.TuRBO.turbo_1.Turbo1 constru |
| run.py:202:14 | `Problem(n_var=f.dim, n_obj=1, n_constr=0, xl=np.zeros(f.dim), xu=np...` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:203:18 | `NoTermination()` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:206:16 | `GA(pop_size=pop_size, n_offsprings=n_offsprings)` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:207:4 | `algorithm.setup(problem, termination=termination)` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:211:14 | `algorithm.ask()` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:223:13 | `pop.get('X')` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:225:8 | `pop.set('F', np.array(y).reshape(-1, 1))` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:227:8 | `algorithm.tell(infills=pop)` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:231:63 | `algorithm.result()` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:233:10 | `algorithm.result()` | library / pymoo | library / pymoo | pymoo_receiver | static_context | v: callable or receiver is created by pymoo |
| run.py:244:21 | `ran.minimize(f)` | library / nevergrad | library / nevergrad | nevergrad_receiver | static_context | v: optimizer receiver is created by nevergrad |
| run.py:273:21 | `de.minimize(f)` | library / nevergrad | library / nevergrad | nevergrad_receiver | static_context | v: optimizer receiver is created by nevergrad |
| run.py:280:21 | `ngo.minimize(f)` | library / nevergrad | library / nevergrad | nevergrad_receiver | static_context | v: optimizer receiver is created by nevergrad |
| run.py:282:20 | `f(x)` | local / local | local / local | dynamic_local_callable | static_context | v: callable resolves to a project-local synthetic or benchmark object in the surrou |
| run.py:288:21 | `de.minimize(f)` | library / nevergrad | library / nevergrad | nevergrad_receiver | static_context | v: optimizer receiver is created by nevergrad |
| run.py:290:20 | `f(x)` | local / local | local / local | dynamic_local_callable | static_context | v: callable resolves to a project-local synthetic or benchmark object in the surrou |
| functions/test.py:37:8 | `self.results.append(self.curt_best)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/test.py:40:12 | `self.dump_trace()` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/test.py:58:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/lasso.py:34:12 | `self.synt_bench.evaluate(x)` | library / LassoBench | library / LassoBench | lassobench_receiver | static_context | v: synt_bench is created by LassoBench |
| functions/lasso.py:35:8 | `self.tracker.track(y, x)` | local / local | local / local | local_method | static_context | v: tracker is defined in the project |
| functions/robot_push.py:73:12 | `results.append(-(initial_dist - ret1 - ret2))` | python / python | python / python | builtin_container_method | static_context | v: results is an explicit Python list |
| functions/robot_push.py:75:8 | `self.tracker.track(result, argv)` | local / local | local / local | local_method | static_context | v: tracker is defined in the project |
| functions/push_utils.py:18:29 | `b2Vec2(self.SCREEN_WIDTH / (2 * self.PPM), self.SCREEN_HEIGHT / (se...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:48:8 | `self.screen.fill(bg_color)` | library / pygame | library / pygame | pygame_receiver | static_context | v: receiver is created by pygame |
| functions/push_utils.py:49:8 | `self.clock.tick(self.TARGET_FPS)` | library / pygame | library / pygame | pygame_receiver | static_context | v: receiver is created by pygame |
| functions/push_utils.py:52:16 | `fixture.shape.draw(body, fixture)` | local / local | unknown / unknown | monkey_patched_local_method | static_context | v: draw is assigned to project-local my_draw_polygon or my_draw_circle |
| functions/push_utils.py:59:21 | `b2World(gravity=(0.0, 0.0), doSleep=True)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:67:29 | `guiWorld(self.TARGET_FPS)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:74:29 | `guiWorld(self.TARGET_FPS)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:85:12 | `self.bodies.append(new_bodies)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list or string |
| functions/push_utils.py:88:8 | `self.world.Step(self.TIME_STEP, self.VEL_ITERS, self.POS_ITERS)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:90:12 | `self.gui_world.draw(self.bodies)` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:96:20 | `world.CreateDynamicBody(position=init_pos, angle=init_angle)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:101:21 | `b2PolygonShape(box=hand_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:104:21 | `b2CircleShape(radius=hand_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:107:21 | `b2PolygonShape(vertices=hand_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:111:8 | `self.hand.CreateFixture(shape=rshape, density=0.1, friction=0.1)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:118:25 | `world.CreateFrictionJoint(bodyA=base, bodyB=self.hand, maxForce=2, ...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:124:8 | `b2world_interface.add_bodies(self.hand)` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:135:8 | `self.hand.ApplyTorque(torque, wake=True)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:138:21 | `b2Vec2(rlvel)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:138:37 | `b2Vec2(lvel)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:140:8 | `self.hand.ApplyForce(force, self.hand.position, wake=True)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:149:13 | `', '.join(print_state[:3])` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list or string |
| functions/push_utils.py:149:43 | `', '.join(print_state[3:])` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list or string |
| functions/push_utils.py:157:11 | `world.CreateDynamicBody(position=obj_loc)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:159:20 | `b2PolygonShape(box=body_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:161:20 | `b2CircleShape(radius=body_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:163:20 | `b2PolygonShape(vertices=body_size)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:167:4 | `link.CreateFixture(shape=linkshape, density=body_density, friction=...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:172:21 | `world.CreateFrictionJoint(bodyA=base, bodyB=link, maxForce=5, maxTo...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:179:4 | `b2world_interface.add_bodies([link])` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:185:11 | `world.CreateStaticBody(position=(0, 0), shapes=b2PolygonShape(box=(...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:187:15 | `b2PolygonShape(box=(table_length, table_width))` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:190:4 | `b2world_interface.add_bodies([base])` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:198:14 | `world.CreateStaticBody(position=(0, 0), shapes=b2PolygonShape(verti...` | library / Box2D | unknown / unknown | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:200:19 | `b2PolygonShape(vertices=verts)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:203:8 | `obs.append(tmp)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list or string |
| functions/push_utils.py:211:14 | `world.CreateStaticBody(position=pos, shapes=b2PolygonShape(box=blen))` | library / Box2D | unknown / unknown | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:213:19 | `b2PolygonShape(box=blen)` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:215:8 | `obs.append(tmp)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list or string |
| functions/push_utils.py:224:11 | `b2Vec2(desired_vel[0] + np.random.normal(0, 1e-06), desired_vel[1] ...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:227:12 | `b2Vec2(desired_vel2[0] + np.random.normal(0, 1e-06), desired_vel2[1...` | library / Box2D | library / Box2D | box2d_receiver | static_context | v: callable or receiver is created by Box2D |
| functions/push_utils.py:232:12 | `robot.apply_wrench(rvel, rtor)` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:234:12 | `robot2.apply_wrench(rvel2, rtor2)` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/push_utils.py:235:8 | `world.step()` | local / local | local / local | local_method | static_context | v: receiver is an instance of a project-local wrapper class |
| functions/rover.py:234:15 | `self.fn_instance(self.project_input(x))` | local / local | local / local | local_callable | static_context | v: receiver or callable is a project-local rover wrapper or tracker |
| functions/rover.py:234:32 | `self.project_input(x)` | local / local | local / local | local_callable | static_context | v: receiver or callable is a project-local rover wrapper or tracker |
| functions/rover.py:252:15 | `self.fn_instance(x)` | local / local | local / local | local_callable | static_context | v: receiver or callable is a project-local rover wrapper or tracker |
| functions/rover.py:255:15 | `self.fn_instance.get_range()` | local / local | local / local | local_callable | static_context | v: receiver or callable is a project-local rover wrapper or tracker |
| functions/rover.py:301:8 | `self.tracker.track(result, x)` | local / local | local / local | local_callable | static_context | v: receiver or callable is a project-local rover wrapper or tracker |
| functions/synthetic.py:37:8 | `self.results.append(self.curt_best)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/synthetic.py:40:12 | `self.dump_trace()` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:52:15 | `current_datetime.strftime('%Y%m%d_%H%M%S')` | library / datetime | library / datetime | datetime_receiver | static_context | v: current_datetime is returned by datetime.datetime.now |
| functions/synthetic.py:80:12 | `w.append(1 + (x[idx] - 1) / 4)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/synthetic.py:96:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:116:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:136:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:157:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:178:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/synthetic.py:197:8 | `self.tracker.track(result, x)` | local / local | local / local | local_method | static_context | v: method is defined on a project-local tracker or benchmark class |
| functions/rover_utils.py:44:17 | `params.reshape((-1, self.d))` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:52:22 | `si.splprep(points, k=3)` | library / scipy | library / scipy | direct_import | static_context | v: si is the scipy.interpolate import alias |
| functions/rover_utils.py:64:25 | `si.splev(t, self.tck)` | library / scipy | library / scipy | direct_import | static_context | v: si is the scipy.interpolate import alias |
| functions/rover_utils.py:120:8 | `self.set_params(params)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:122:16 | `self.estimate_cost(n_samples=n_samples)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:125:8 | `self.traj.set_params(params + self.rnd_stream.normal(0, 0.0001, par...` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:125:38 | `self.rnd_stream.normal(0, 0.0001, params.shape)` | library / numpy | library / numpy | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:131:17 | `self.traj.get_points(np.linspace(0, 1.0, n_samples, endpoint=True))` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:133:16 | `self.cost_fn(points)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:141:26 | `self.start_miss_cost(points[0], self.start)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:143:26 | `self.goal_miss_cost(points[-1], self.goal)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:164:16 | `lX.all(axis=1)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:164:33 | `hX.all(axis=1)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:172:16 | `self.geom.contains(X)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:180:33 | `g.contains(X)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:189:24 | `self.geom.contains(X)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:232:24 | `g.reshape((-1, 1))` | library / numpy | library / numpy | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:235:12 | `roverdomain.cost_fn(points)` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:238:16 | `roverdomain.estimate_cost()` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:241:18 | `roverdomain.traj.get_points(np.linspace(0.0, 1.0, ntraj_points, end...` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:244:4 | `plt.title('traj cost: {0}'.format(traj_cost))` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:247:12 | `plt.pcolormesh(grid_points[0], grid_points[1], costs.reshape((ngrid...` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:247:59 | `costs.reshape((ngrid_points, -1))` | library / numpy | library / numpy | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:249:8 | `plt.gcf()` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:249:8 | `plt.gcf().colorbar(cmesh)` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:251:4 | `plt.plot(traj_points[:, 0], traj_points[:, 1], 'g')` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:253:4 | `plt.plot([roverdomain.start[0], roverdomain.goal[0]], (roverdomain....` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:294:9 | `plt.gcf()` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:294:9 | `plt.gcf().add_subplot(111, projection='3d')` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:297:4 | `ax.scatter((roverdomain.start[0], roverdomain.goal[0]), (roverdomai...` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:303:4 | `ax.add_collection3d(Line3DCollection(seg, colors=[(0, 1.0, 0, 1.0)]...` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:306:4 | `ax.add_collection3d(Poly3DCollection(poly3d, facecolors=(0.7, 0.7, ...` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:310:4 | `ax.set_xlim(s_range[0][0], s_range[1][0])` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:311:4 | `ax.set_ylim(s_range[0][1], s_range[1][1])` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:312:4 | `ax.set_zlim(s_range[0][2], s_range[1][2])` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:325:4 | `traj.set_params(start, goal, p.flatten())` | local / local | local / local | local_method | static_context | v: receiver or callable is defined by the project-local rover geometry implementati |
| functions/rover_utils.py:325:33 | `p.flatten()` | library / numpy | library / numpy | numpy_array_receiver | static_context | v: receiver is a NumPy array or RandomState |
| functions/rover_utils.py:333:4 | `plt.figure()` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:335:4 | `plt.plot(p[:, 0], p[:, 1], '*g')` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/rover_utils.py:336:4 | `plt.show()` | library / matplotlib | library / matplotlib | matplotlib_receiver | static_context | v: callable or receiver is imported from matplotlib inside the plotting function |
| functions/mujoco.py:40:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: x is converted to a NumPy array before reshape |
| functions/mujoco.py:47:21 | `self.env.reset()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:55:16 | `observations.append(obs)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:56:16 | `actions.append(action)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:57:34 | `self.env.step(action)` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:61:20 | `self.env.render()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:62:12 | `returns.append(totalr)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:64:8 | `self.tracker.track(np.mean(returns) * -1, x)` | local / local | local / local | local_method | static_context | v: method is defined on the project-local benchmark or tracker |
| functions/mujoco.py:70:8 | `self.env.seed(1234)` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:94:17 | `self.env.reset()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:102:30 | `self.env.step(action)` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:106:16 | `self.env.render()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:115:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: x is converted to a NumPy array before reshape |
| functions/mujoco.py:120:21 | `self._rollout(M)` | local / local | local / local | local_method | static_context | v: method is defined on the project-local benchmark or tracker |
| functions/mujoco.py:121:12 | `returns.append(totalr)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:125:8 | `self.tracker.track(np.mean(returns) * -1, x)` | local / local | local / local | local_method | static_context | v: method is defined on the project-local benchmark or tracker |
| functions/mujoco.py:207:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | v: x is converted to a NumPy array before reshape |
| functions/mujoco.py:214:21 | `self.env.reset()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:222:16 | `observations.append(obs)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:223:16 | `actions.append(action)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:224:34 | `self.env.step(action)` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:228:20 | `self.env.render()` | library / gym | library / gym | gym_receiver | static_context | v: env is created by gym.make |
| functions/mujoco.py:229:12 | `returns.append(totalr)` | python / python | python / python | builtin_container_method | static_context | v: receiver is an explicit Python list |
| functions/mujoco.py:231:8 | `self.tracker.track(np.mean(returns) * -1, x)` | local / local | local / local | local_method | static_context | v: method is defined on the project-local benchmark or tracker |
