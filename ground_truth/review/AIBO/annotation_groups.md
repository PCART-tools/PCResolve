# AIBO -- Annotation Groups (101 groups, 172 records)

## Summary

| Evidence | Groups | Records | Needs Human |
|----------|--------|---------|-------------|
| static_obvious | 8 | 10 | 0 |
| static_context | 23 | 52 | 0 |
| manual_reasoned | 70 | 110 | 110 |
| **Total** | **101** | **172** | **110** |

## Group 1: parser -> library/argparse (12 records)

| Evidence | static_context |
| Needs human | no (0/12) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>argparse.ArgumentParser()</code> @ run.py:23 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>parser.add_argument('--func', help='specify the test function')</code> -- run.py:24
- <code>parser.add_argument('--dim', type=int, help='specify the problem dimensions')</code> -- run.py:25
- <code>parser.add_argument('--method', default='AIBO_mixed-grad-EI')</code> -- run.py:26
- <code>parser.add_argument('--batch-size', type=int, default=10)</code> -- run.py:27
- <code>parser.add_argument('--iters', type=int, help='Total evaluation budget')</code> -- run.py:28
- ... and 7 more

**All bindings (1 unique):**
- <code>run.py</code> L23: <code>argparse.ArgumentParser()</code>

## Group 2: plt -> library/matplotlib (8 records)

| Evidence | static_context |
| Needs human | no (0/8) |
| Reason | UNRESOLVED |
| Key binding | <code>import matplotlib.pyplot</code> @ functions/rover_utils.py:228 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.title('traj cost: {0}'.format(traj_cost))</code> -- functions/rover_utils.py:244
- <code>plt.pcolormesh(grid_points[0], grid_points[1], costs.reshape((ngrid_points, -1)), cmap=colormap)</code> -- functions/rover_utils.py:247
- <code>plt.gcf()</code> -- functions/rover_utils.py:249
- <code>plt.plot(traj_points[:, 0], traj_points[:, 1], 'g')</code> -- functions/rover_utils.py:251
- <code>plt.plot([roverdomain.start[0], roverdomain.goal[0]], (roverdomain.start[1], roverdomain.goal[1]), '</code> -- functions/rover_utils.py:253
- ... and 3 more

**All bindings (2 unique):**
- <code>functions/rover_utils.py</code> L228: <code>import matplotlib.pyplot</code>
- <code>functions/rover_utils.py</code> L316: <code>import matplotlib.pyplot</code>

## Group 3: b2PolygonShape -> ?/? (7 records)

| Evidence | manual_reasoned |
| Needs human | yes (7/7) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2PolygonShape(box=hand_size)</code> -- functions/push_utils.py:101
- <code>b2PolygonShape(vertices=hand_size)</code> -- functions/push_utils.py:107
- <code>b2PolygonShape(box=body_size)</code> -- functions/push_utils.py:159
- <code>b2PolygonShape(vertices=body_size)</code> -- functions/push_utils.py:163
- <code>b2PolygonShape(box=(table_length, table_width))</code> -- functions/push_utils.py:187
- <code>b2PolygonShape(vertices=verts)</code> -- functions/push_utils.py:200
- <code>b2PolygonShape(box=blen)</code> -- functions/push_utils.py:213


## Group 4: world -> ?/? (7 records)

| Evidence | manual_reasoned |
| Needs human | yes (7/7) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>b2world_interface.world</code> @ functions/push_utils.py:95 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>world.CreateDynamicBody(position=init_pos, angle=init_angle)</code> -- functions/push_utils.py:96
- <code>world.CreateFrictionJoint(bodyA=base, bodyB=self.hand, maxForce=2, maxTorque=2)</code> -- functions/push_utils.py:118
- <code>world.CreateDynamicBody(position=obj_loc)</code> -- functions/push_utils.py:157
- <code>world.CreateFrictionJoint(bodyA=base, bodyB=link, maxForce=5, maxTorque=2)</code> -- functions/push_utils.py:172
- <code>world.CreateStaticBody(position=(0, 0), shapes=b2PolygonShape(box=(table_length, table_width)))</code> -- functions/push_utils.py:185
- <code>world.CreateStaticBody(position=(0, 0), shapes=b2PolygonShape(vertices=verts))</code> -- functions/push_utils.py:198
- <code>world.CreateStaticBody(position=pos, shapes=b2PolygonShape(box=blen))</code> -- functions/push_utils.py:211

**All bindings (4 unique):**
- <code>functions/push_utils.py</code> L95: <code>b2world_interface.world</code>
- <code>functions/push_utils.py</code> L155: <code>b2world_interface.world</code>
- <code>functions/push_utils.py</code> L184: <code>b2world_interface.world</code>
- <code>functions/push_utils.py</code> L195: <code>b2world_interface.world</code>

## Group 5: ax -> library/matplotlib (6 records)

| Evidence | static_context |
| Needs human | no (0/6) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>plt.gcf().add_subplot(111, projection='3d')</code> @ functions/rover_utils.py:294 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>ax.scatter((roverdomain.start[0], roverdomain.goal[0]), (roverdomain.start[1], roverdomain.goal[1]),</code> -- functions/rover_utils.py:297
- <code>ax.add_collection3d(Line3DCollection(seg, colors=[(0, 1.0, 0, 1.0)] * len(seg)))</code> -- functions/rover_utils.py:303
- <code>ax.add_collection3d(Poly3DCollection(poly3d, facecolors=(0.7, 0.7, 0.7, 1.0), linewidth=0.5))</code> -- functions/rover_utils.py:306
- <code>ax.set_xlim(s_range[0][0], s_range[1][0])</code> -- functions/rover_utils.py:310
- <code>ax.set_ylim(s_range[0][1], s_range[1][1])</code> -- functions/rover_utils.py:311
- ... and 1 more

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L294: <code>plt.gcf().add_subplot(111, projection='3d')</code>

## Group 6: algorithm -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>GA(pop_size=pop_size,n_offsprings=n_offsprings)</code> @ run.py:206 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>algorithm.setup(problem, termination=termination)</code> -- run.py:207
- <code>algorithm.ask()</code> -- run.py:211
- <code>algorithm.tell(infills=pop)</code> -- run.py:227
- <code>algorithm.result()</code> -- run.py:231
- <code>algorithm.result()</code> -- run.py:233

**All bindings (1 unique):**
- <code>run.py</code> L206: <code>GA(pop_size=pop_size,n_offsprings=n_offsprings)</code>

## Group 7: b2Vec2 -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2Vec2(self.SCREEN_WIDTH / (2 * self.PPM), self.SCREEN_HEIGHT / (self.PPM * 2))</code> -- functions/push_utils.py:18
- <code>b2Vec2(rlvel)</code> -- functions/push_utils.py:138
- <code>b2Vec2(lvel)</code> -- functions/push_utils.py:138
- <code>b2Vec2(desired_vel[0] + np.random.normal(0, 1e-06), desired_vel[1] + np.random.normal(0, 1e-06))</code> -- functions/push_utils.py:224
- <code>b2Vec2(desired_vel2[0] + np.random.normal(0, 1e-06), desired_vel2[1] + np.random.normal(0, 1e-06))</code> -- functions/push_utils.py:227


## Group 8: self -> ?/? (5 records)

| Evidence | manual_reasoned |
| Needs human | yes (5/5) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover_utils.py:119 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.set_params(params)</code> -- functions/rover_utils.py:120
- <code>self.estimate_cost(n_samples=n_samples)</code> -- functions/rover_utils.py:122
- <code>self.cost_fn(points)</code> -- functions/rover_utils.py:133
- <code>self.start_miss_cost(points[0], self.start)</code> -- functions/rover_utils.py:141
- <code>self.goal_miss_cost(points[-1], self.goal)</code> -- functions/rover_utils.py:143

**All bindings (2 unique):**
- <code>functions/rover_utils.py</code> L119: <code>parameter self</code>
- <code>functions/rover_utils.py</code> L129: <code>parameter self</code>

## Group 9: self.env -> ?/? (4 records)

| Evidence | manual_reasoned |
| Needs human | yes (4/4) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:68 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.env.seed(1234)</code> -- functions/mujoco.py:70
- <code>self.env.reset()</code> -- functions/mujoco.py:94
- <code>self.env.step(action)</code> -- functions/mujoco.py:102
- <code>self.env.render()</code> -- functions/mujoco.py:106

**All bindings (2 unique):**
- <code>functions/mujoco.py</code> L68: <code>parameter self</code>
- <code>functions/mujoco.py</code> L93: <code>parameter self</code>

## Group 10: self.env -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:34 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.env.reset()</code> -- functions/mujoco.py:47
- <code>self.env.step(action)</code> -- functions/mujoco.py:57
- <code>self.env.render()</code> -- functions/mujoco.py:61

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L34: <code>parameter self</code>

## Group 11: self.env -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:201 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.env.reset()</code> -- functions/mujoco.py:214
- <code>self.env.step(action)</code> -- functions/mujoco.py:224
- <code>self.env.render()</code> -- functions/mujoco.py:228

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L201: <code>parameter self</code>

## Group 12: self.hand -> ?/? (3 records)

| Evidence | manual_reasoned |
| Needs human | yes (3/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:94 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.hand.CreateFixture(shape=rshape, density=0.1, friction=0.1)</code> -- functions/push_utils.py:111
- <code>self.hand.ApplyTorque(torque, wake=True)</code> -- functions/push_utils.py:135
- <code>self.hand.ApplyForce(force, self.hand.position, wake=True)</code> -- functions/push_utils.py:140

**All bindings (2 unique):**
- <code>functions/push_utils.py</code> L94: <code>parameter self</code>
- <code>functions/push_utils.py</code> L130: <code>parameter self</code>

## Group 13: es -> library/cma (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>cma.CMAEvolutionStrategy(\n        x0 = x0,#np.random.rand(f.dim),\n        sigm</code> @ run.py:128 |
| Owner | cma |
| Proposed GT | library / cma |

**Representative expressions:**

- <code>es.stop()</code> -- run.py:145
- <code>es.ask()</code> -- run.py:146
- <code>es.tell(xs, y)</code> -- run.py:148

**All bindings (1 unique):**
- <code>run.py</code> L128: <code>cma.CMAEvolutionStrategy(\n        x0 = x0,#np.random.rand(f.dim),\n        sigm</code>

## Group 14: returns -> python/python (3 records)

| Evidence | static_context |
| Needs human | no (0/3) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ functions/mujoco.py:42 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>returns.append(totalr)</code> -- functions/mujoco.py:62
- <code>returns.append(totalr)</code> -- functions/mujoco.py:121
- <code>returns.append(totalr)</code> -- functions/mujoco.py:229

**All bindings (3 unique):**
- <code>functions/mujoco.py</code> L42: <code>[]</code>
- <code>functions/mujoco.py</code> L117: <code>[]</code>
- <code>functions/mujoco.py</code> L209: <code>[]</code>

## Group 15: ', ' -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>', '.join(print_state[:3])</code> -- functions/push_utils.py:149
- <code>', '.join(print_state[3:])</code> -- functions/push_utils.py:149


## Group 16: b2CircleShape -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2CircleShape(radius=hand_size)</code> -- functions/push_utils.py:104
- <code>b2CircleShape(radius=body_size)</code> -- functions/push_utils.py:161


## Group 17: guiWorld -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>class guiWorld</code> @ functions/push_utils.py:10 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>guiWorld(self.TARGET_FPS)</code> -- functions/push_utils.py:67
- <code>guiWorld(self.TARGET_FPS)</code> -- functions/push_utils.py:74

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L10: <code>class guiWorld</code>

## Group 18: pop -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>algorithm.ask()</code> @ run.py:211 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>pop.get('X')</code> -- run.py:223
- <code>pop.set('F', np.array(y).reshape(-1, 1))</code> -- run.py:225

**All bindings (1 unique):**
- <code>run.py</code> L211: <code>algorithm.ask()</code>

## Group 19: roverdomain -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter roverdomain</code> @ functions/rover_utils.py:227 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>roverdomain.cost_fn(points)</code> -- functions/rover_utils.py:235
- <code>roverdomain.estimate_cost()</code> -- functions/rover_utils.py:238

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L227: <code>parameter roverdomain</code>

## Group 20: self -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover.py:233 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.fn_instance(self.project_input(x))</code> -- functions/rover.py:234
- <code>self.project_input(x)</code> -- functions/rover.py:234

**All bindings (1 unique):**
- <code>functions/rover.py</code> L233: <code>parameter self</code>

## Group 21: self.traj -> ?/? (2 records)

| Evidence | manual_reasoned |
| Needs human | yes (2/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover_utils.py:124 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.traj.set_params(params + self.rnd_stream.normal(0, 0.0001, params.shape), self.start if self.fo</code> -- functions/rover_utils.py:125
- <code>self.traj.get_points(np.linspace(0, 1.0, n_samples, endpoint=True))</code> -- functions/rover_utils.py:131

**All bindings (2 unique):**
- <code>functions/rover_utils.py</code> L124: <code>parameter self</code>
- <code>functions/rover_utils.py</code> L129: <code>parameter self</code>

## Group 22: actions -> python/python (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ functions/mujoco.py:44 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>actions.append(action)</code> -- functions/mujoco.py:56
- <code>actions.append(action)</code> -- functions/mujoco.py:223

**All bindings (2 unique):**
- <code>functions/mujoco.py</code> L44: <code>[]</code>
- <code>functions/mujoco.py</code> L211: <code>[]</code>

## Group 23: obs -> python/python (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>[]</code> @ functions/push_utils.py:196 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>obs.append(tmp)</code> -- functions/push_utils.py:203
- <code>obs.append(tmp)</code> -- functions/push_utils.py:215

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L196: <code>[]</code>

## Group 24: observations -> python/python (2 records)

| Evidence | static_context |
| Needs human | no (0/2) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ functions/mujoco.py:43 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>observations.append(obs)</code> -- functions/mujoco.py:55
- <code>observations.append(obs)</code> -- functions/mujoco.py:222

**All bindings (2 unique):**
- <code>functions/mujoco.py</code> L43: <code>[]</code>
- <code>functions/mujoco.py</code> L210: <code>[]</code>

## Group 25: si -> library/scipy (2 records)

| Evidence | static_obvious |
| Needs human | no (0/2) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>import scipy.interpolate</code> @ functions/rover_utils.py:6 |
| Owner | scipy |
| Proposed GT | library / scipy |

**Representative expressions:**

- <code>si.splprep(points, k=3)</code> -- functions/rover_utils.py:52
- <code>si.splev(t, self.tck)</code> -- functions/rover_utils.py:64

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L6: <code>import scipy.interpolate</code>

## Group 26: acqf_mode -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>(tuple) re.split('_&#124;-', args.method)</code> @ run.py:71 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>acqf_mode.startswith('UCB')</code> -- run.py:82

**All bindings (1 unique):**
- <code>run.py</code> L71: <code>(tuple) re.split('_&#124;-', args.method)</code>

## Group 27: b2World -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2World(gravity=(0.0, 0.0), doSleep=True)</code> -- functions/push_utils.py:59


## Group 28: b2world_interface -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter b2world_interface</code> @ functions/push_utils.py:94 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2world_interface.add_bodies(self.hand)</code> -- functions/push_utils.py:124

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L94: <code>parameter b2world_interface</code>

## Group 29: b2world_interface -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter b2world_interface</code> @ functions/push_utils.py:154 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2world_interface.add_bodies([link])</code> -- functions/push_utils.py:179

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L154: <code>parameter b2world_interface</code>

## Group 30: b2world_interface -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter b2world_interface</code> @ functions/push_utils.py:183 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2world_interface.add_bodies([base])</code> -- functions/push_utils.py:190

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L183: <code>parameter b2world_interface</code>

## Group 31: b2world_interface -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter b2world_interface</code> @ functions/push_utils.py:194 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>b2world_interface.add_bodies(obs)</code> -- functions/push_utils.py:216

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L194: <code>parameter b2world_interface</code>

## Group 32: costs -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>roverdomain.cost_fn(points)</code> @ functions/rover_utils.py:235 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>costs.reshape((ngrid_points, -1))</code> -- functions/rover_utils.py:247

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L235: <code>roverdomain.cost_fn(points)</code>

## Group 33: fixture.shape -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>for target</code> @ functions/push_utils.py:51 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>fixture.shape.draw(body, fixture)</code> -- functions/push_utils.py:52

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L51: <code>for target</code>

## Group 34: g -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>comprehension target</code> @ functions/rover_utils.py:180 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>g.contains(X)</code> -- functions/rover_utils.py:180

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L180: <code>comprehension target</code>

## Group 35: g -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>comprehension target</code> @ functions/rover_utils.py:232 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>g.reshape((-1, 1))</code> -- functions/rover_utils.py:232

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L232: <code>comprehension target</code>

## Group 36: hX -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self.h.T[None, :, :] &gt; X[:, :, None]</code> @ functions/rover_utils.py:162 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>hX.all(axis=1)</code> -- functions/rover_utils.py:164

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L162: <code>self.h.T[None, :, :] &gt; X[:, :, None]</code>

## Group 37: lX -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>self.l.T[None, :, :] &lt;= X[:, :, None]</code> @ functions/rover_utils.py:161 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>lX.all(axis=1)</code> -- functions/rover_utils.py:164

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L161: <code>self.l.T[None, :, :] &lt;= X[:, :, None]</code>

## Group 38: link -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>world.CreateDynamicBody(position=obj_loc)</code> @ functions/push_utils.py:157 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>link.CreateFixture(shape=linkshape, density=body_density, friction=body_friction)</code> -- functions/push_utils.py:167

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L157: <code>world.CreateDynamicBody(position=obj_loc)</code>

## Group 39: params -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter params</code> @ functions/rover_utils.py:42 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>params.reshape((-1, self.d))</code> -- functions/rover_utils.py:44

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L42: <code>parameter params</code>

## Group 40: robot -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter robot</code> @ functions/push_utils.py:219 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>robot.apply_wrench(rvel, rtor)</code> -- functions/push_utils.py:232

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L219: <code>parameter robot</code>

## Group 41: robot2 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter robot2</code> @ functions/push_utils.py:219 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>robot2.apply_wrench(rvel2, rtor2)</code> -- functions/push_utils.py:234

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L219: <code>parameter robot2</code>

## Group 42: roverdomain -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter roverdomain</code> @ functions/rover_utils.py:281 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>roverdomain.estimate_cost()</code> -- functions/rover_utils.py:286

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L281: <code>parameter roverdomain</code>

## Group 43: roverdomain.traj -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter roverdomain</code> @ functions/rover_utils.py:227 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>roverdomain.traj.get_points(np.linspace(0.0, 1.0, ntraj_points, endpoint=True))</code> -- functions/rover_utils.py:241

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L227: <code>parameter roverdomain</code>

## Group 44: roverdomain.traj -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter roverdomain</code> @ functions/rover_utils.py:281 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>roverdomain.traj.get_points(np.linspace(0.0, 1.0, ntraj_points, endpoint=True))</code> -- functions/rover_utils.py:289

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L281: <code>parameter roverdomain</code>

## Group 45: self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/test.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.dump_trace()</code> -- functions/test.py:40

**All bindings (1 unique):**
- <code>functions/test.py</code> L26: <code>parameter self</code>

## Group 46: self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover.py:251 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.fn_instance(x)</code> -- functions/rover.py:252

**All bindings (1 unique):**
- <code>functions/rover.py</code> L251: <code>parameter self</code>

## Group 47: self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.dump_trace()</code> -- functions/synthetic.py:40

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L26: <code>parameter self</code>

## Group 48: self -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self._rollout(M)</code> -- functions/mujoco.py:120

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L109: <code>parameter self</code>

## Group 49: self.bodies -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:80 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.bodies.append(new_bodies)</code> -- functions/push_utils.py:85

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L80: <code>parameter self</code>

## Group 50: self.clock -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:24 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.clock.tick(self.TARGET_FPS)</code> -- functions/push_utils.py:49

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L24: <code>parameter self</code>

## Group 51: self.fn_instance -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover.py:254 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.fn_instance.get_range()</code> -- functions/rover.py:255

**All bindings (1 unique):**
- <code>functions/rover.py</code> L254: <code>parameter self</code>

## Group 52: self.geom -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover_utils.py:171 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.geom.contains(X)</code> -- functions/rover_utils.py:172

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L171: <code>parameter self</code>

## Group 53: self.geom -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover_utils.py:188 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.geom.contains(X)</code> -- functions/rover_utils.py:189

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L188: <code>parameter self</code>

## Group 54: self.gui_world -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:87 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.gui_world.draw(self.bodies)</code> -- functions/push_utils.py:90

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L87: <code>parameter self</code>

## Group 55: self.results -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/test.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.results.append(self.curt_best)</code> -- functions/test.py:37

**All bindings (1 unique):**
- <code>functions/test.py</code> L26: <code>parameter self</code>

## Group 56: self.results -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:26 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.results.append(self.curt_best)</code> -- functions/synthetic.py:37

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L26: <code>parameter self</code>

## Group 57: self.rnd_stream -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/rover_utils.py:124 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.rnd_stream.normal(0, 0.0001, params.shape)</code> -- functions/rover_utils.py:125

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L124: <code>parameter self</code>

## Group 58: self.screen -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:24 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.screen.fill(bg_color)</code> -- functions/push_utils.py:48

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L24: <code>parameter self</code>

## Group 59: self.synt_bench -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter self</code> @ functions/lasso.py:28 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.synt_bench.evaluate(x)</code> -- functions/lasso.py:34

**All bindings (1 unique):**
- <code>functions/lasso.py</code> L28: <code>parameter self</code>

## Group 60: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/test.py:51 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/test.py:58

**All bindings (1 unique):**
- <code>functions/test.py</code> L51: <code>parameter self</code>

## Group 61: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/lasso.py:28 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(y, x)</code> -- functions/lasso.py:35

**All bindings (1 unique):**
- <code>functions/lasso.py</code> L28: <code>parameter self</code>

## Group 62: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/robot_push.py:37 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, argv)</code> -- functions/robot_push.py:75

**All bindings (1 unique):**
- <code>functions/robot_push.py</code> L37: <code>parameter self</code>

## Group 63: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/rover.py:295 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/rover.py:301

**All bindings (1 unique):**
- <code>functions/rover.py</code> L295: <code>parameter self</code>

## Group 64: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:72 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:96

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L72: <code>parameter self</code>

## Group 65: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:116

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L109: <code>parameter self</code>

## Group 66: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:128 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:136

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L128: <code>parameter self</code>

## Group 67: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:148 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:157

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L148: <code>parameter self</code>

## Group 68: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:171 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:178

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L171: <code>parameter self</code>

## Group 69: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/synthetic.py:190 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(result, x)</code> -- functions/synthetic.py:197

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L190: <code>parameter self</code>

## Group 70: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:34 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(np.mean(returns) * -1, x)</code> -- functions/mujoco.py:64

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L34: <code>parameter self</code>

## Group 71: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(np.mean(returns) * -1, x)</code> -- functions/mujoco.py:125

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L109: <code>parameter self</code>

## Group 72: self.tracker -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/mujoco.py:201 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.tracker.track(np.mean(returns) * -1, x)</code> -- functions/mujoco.py:231

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L201: <code>parameter self</code>

## Group 73: self.world -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter self</code> @ functions/push_utils.py:87 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>self.world.Step(self.TIME_STEP, self.VEL_ITERS, self.POS_ITERS)</code> -- functions/push_utils.py:88

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L87: <code>parameter self</code>

## Group 74: traj -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>PointBSpline(dim=2, num_points=3)</code> @ functions/rover_utils.py:323 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>traj.set_params(start, goal, p.flatten())</code> -- functions/rover_utils.py:325

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L323: <code>PointBSpline(dim=2, num_points=3)</code>

## Group 75: turbo1 -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>Turbo1(\n        f=f,  # Handle to objective function\n        lb=f.lb,  # Numpy</code> @ run.py:170 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>turbo1.optimize()</code> -- run.py:185

**All bindings (1 unique):**
- <code>run.py</code> L170: <code>Turbo1(\n        f=f,  # Handle to objective function\n        lb=f.lb,  # Numpy</code>

## Group 76: world -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>parameter world</code> @ functions/push_utils.py:219 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>world.step()</code> -- functions/push_utils.py:235

**All bindings (1 unique):**
- <code>functions/push_utils.py</code> L219: <code>parameter world</code>

## Group 77: x -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter x</code> @ functions/mujoco.py:34 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>x.reshape(self.policy_shape)</code> -- functions/mujoco.py:40

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L34: <code>parameter x</code>

## Group 78: x -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter x</code> @ functions/mujoco.py:109 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>x.reshape(self.policy_shape)</code> -- functions/mujoco.py:115

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L109: <code>parameter x</code>

## Group 79: x -> ?/? (1 records)

| Evidence | manual_reasoned |
| Needs human | yes (1/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>parameter x</code> @ functions/mujoco.py:201 |
| Owner | None |
| Proposed GT | ? / ? |

**All expressions:**

- <code>x.reshape(self.policy_shape)</code> -- functions/mujoco.py:207

**All bindings (1 unique):**
- <code>functions/mujoco.py</code> L201: <code>parameter x</code>

## Group 80: args.method -> library/argparse (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>parser.parse_args()</code> @ run.py:36 |
| Owner | argparse |
| Proposed GT | library / argparse |

**Representative expressions:**

- <code>args.method.startswith('AIBO')</code> -- run.py:68

**All bindings (1 unique):**
- <code>run.py</code> L36: <code>parser.parse_args()</code>

## Group 81: OpenTuner -> library/baselines (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from baselines.OpenTuner.tuner import OpenTuner</code> @ run.py:323 |
| Owner | baselines |
| Proposed GT | library / baselines |

**Representative expressions:**

- <code>OpenTuner.main(args)</code> -- run.py:325

**All bindings (1 unique):**
- <code>run.py</code> L323: <code>from baselines.OpenTuner.tuner import OpenTuner</code>

## Group 82: Turbo1 -> library/baselines (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from baselines.TuRBO.turbo_1 import Turbo1</code> @ run.py:168 |
| Owner | baselines |
| Proposed GT | library / baselines |

**Representative expressions:**

- <code>Turbo1(f=f, lb=f.lb, ub=f.ub, n_init=2 * args.batch_size, max_evals=args.iters, batch_size=args.batc</code> -- run.py:170

**All bindings (1 unique):**
- <code>run.py</code> L168: <code>from baselines.TuRBO.turbo_1 import Turbo1</code>

## Group 83: current_datetime -> library/datetime (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>datetime.now()</code> @ functions/synthetic.py:51 |
| Owner | datetime |
| Proposed GT | library / datetime |

**Representative expressions:**

- <code>current_datetime.strftime('%Y%m%d_%H%M%S')</code> -- functions/synthetic.py:52

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L51: <code>datetime.now()</code>

## Group 84: mujoco -> library/functions (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import functions.mujoco</code> @ run.py:53 |
| Owner | functions |
| Proposed GT | library / functions |

**Representative expressions:**

- <code>mujoco.HalfCheetah(method=f'{args.method}-{args.batch_size}', verbose=args.verbose)</code> -- run.py:54

**All bindings (1 unique):**
- <code>run.py</code> L53: <code>import functions.mujoco</code>

## Group 85: robot_push -> library/functions (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import functions.robot_push</code> @ run.py:45 |
| Owner | functions |
| Proposed GT | library / functions |

**Representative expressions:**

- <code>robot_push.PushReward(method=f'{args.method}-{args.batch_size}', verbose=args.verbose)</code> -- run.py:46

**All bindings (1 unique):**
- <code>run.py</code> L45: <code>import functions.robot_push</code>

## Group 86: rover -> library/functions (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>import functions.rover</code> @ run.py:49 |
| Owner | functions |
| Proposed GT | library / functions |

**Representative expressions:**

- <code>rover.Rover(method=f'{args.method}-{args.batch_size}', verbose=args.verbose)</code> -- run.py:50

**All bindings (1 unique):**
- <code>run.py</code> L49: <code>import functions.rover</code>

## Group 87: plt -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | UNRESOLVED |
| Key binding | <code>from matplotlib import pyplot</code> @ functions/rover_utils.py:282 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.gcf()</code> -- functions/rover_utils.py:294

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L282: <code>from matplotlib import pyplot</code>

## Group 88: plt.gcf() -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | UNRESOLVED |
| Key binding | <code>import matplotlib.pyplot</code> @ functions/rover_utils.py:228 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.gcf().colorbar(cmesh)</code> -- functions/rover_utils.py:249

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L228: <code>import matplotlib.pyplot</code>

## Group 89: plt.gcf() -> library/matplotlib (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | UNRESOLVED |
| Key binding | <code>from matplotlib import pyplot</code> @ functions/rover_utils.py:282 |
| Owner | matplotlib |
| Proposed GT | library / matplotlib |

**Representative expressions:**

- <code>plt.gcf().add_subplot(111, projection='3d')</code> -- functions/rover_utils.py:294

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L282: <code>from matplotlib import pyplot</code>

## Group 90: Line3DCollection -> library/mpl_toolkits (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | UNRESOLVED |
| Key binding | <code>from mpl_toolkits.mplot3d.art3d import Line3DCollection</code> @ functions/rover_utils.py:283 |
| Owner | mpl_toolkits |
| Proposed GT | library / mpl_toolkits |

**Representative expressions:**

- <code>Line3DCollection(seg, colors=[(0, 1.0, 0, 1.0)] * len(seg))</code> -- functions/rover_utils.py:303

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L283: <code>from mpl_toolkits.mplot3d.art3d import Line3DCollection</code>

## Group 91: Poly3DCollection -> library/mpl_toolkits (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | UNRESOLVED |
| Key binding | <code>from mpl_toolkits.mplot3d.art3d import Poly3DCollection</code> @ functions/rover_utils.py:283 |
| Owner | mpl_toolkits |
| Proposed GT | library / mpl_toolkits |

**Representative expressions:**

- <code>Poly3DCollection(poly3d, facecolors=(0.7, 0.7, 0.7, 1.0), linewidth=0.5)</code> -- functions/rover_utils.py:306

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L283: <code>from mpl_toolkits.mplot3d.art3d import Poly3DCollection</code>

## Group 92: de -> library/nevergrad (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ng.optimizers.DE(parametrization=param, budget = args.iters, num_workers=args.ba</code> @ run.py:272 |
| Owner | nevergrad |
| Proposed GT | library / nevergrad |

**Representative expressions:**

- <code>de.minimize(f)</code> -- run.py:273

**All bindings (1 unique):**
- <code>run.py</code> L272: <code>ng.optimizers.DE(parametrization=param, budget = args.iters, num_workers=args.ba</code>

## Group 93: de -> library/nevergrad (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ng.optimizers.GeneticDE(parametrization=param, budget = args.iters, num_workers=</code> @ run.py:287 |
| Owner | nevergrad |
| Proposed GT | library / nevergrad |

**Representative expressions:**

- <code>de.minimize(f)</code> -- run.py:288

**All bindings (1 unique):**
- <code>run.py</code> L287: <code>ng.optimizers.GeneticDE(parametrization=param, budget = args.iters, num_workers=</code>

## Group 94: ngo -> library/nevergrad (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ng.optimizers.NGOpt(parametrization=param, budget = args.iters, num_workers=args</code> @ run.py:279 |
| Owner | nevergrad |
| Proposed GT | library / nevergrad |

**Representative expressions:**

- <code>ngo.minimize(f)</code> -- run.py:280

**All bindings (1 unique):**
- <code>run.py</code> L279: <code>ng.optimizers.NGOpt(parametrization=param, budget = args.iters, num_workers=args</code>

## Group 95: ran -> library/nevergrad (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>ng.optimizers.RandomSearch(parametrization=param, budget = args.iters, num_worke</code> @ run.py:243 |
| Owner | nevergrad |
| Proposed GT | library / nevergrad |

**Representative expressions:**

- <code>ran.minimize(f)</code> -- run.py:244

**All bindings (1 unique):**
- <code>run.py</code> L243: <code>ng.optimizers.RandomSearch(parametrization=param, budget = args.iters, num_worke</code>

## Group 96: p -> library/numpy (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | RETURN_PROPAGATION |
| Key binding | <code>np.array([[0.1, 0.5], [0.3, 1.3], [0.75, 1.2]])</code> @ functions/rover_utils.py:324 |
| Owner | numpy |
| Proposed GT | library / numpy |

**Representative expressions:**

- <code>p.flatten()</code> -- functions/rover_utils.py:325

**All bindings (1 unique):**
- <code>functions/rover_utils.py</code> L324: <code>np.array([[0.1, 0.5], [0.3, 1.3], [0.75, 1.2]])</code>

## Group 97: GA -> library/pymoo (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from pymoo.algorithms.soo.nonconvex.ga import GA</code> @ run.py:196 |
| Owner | pymoo |
| Proposed GT | library / pymoo |

**Representative expressions:**

- <code>GA(pop_size=pop_size, n_offsprings=n_offsprings)</code> -- run.py:206

**All bindings (1 unique):**
- <code>run.py</code> L196: <code>from pymoo.algorithms.soo.nonconvex.ga import GA</code>

## Group 98: NoTermination -> library/pymoo (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from pymoo.core.termination import NoTermination</code> @ run.py:199 |
| Owner | pymoo |
| Proposed GT | library / pymoo |

**Representative expressions:**

- <code>NoTermination()</code> -- run.py:203

**All bindings (1 unique):**
- <code>run.py</code> L199: <code>from pymoo.core.termination import NoTermination</code>

## Group 99: Problem -> library/pymoo (1 records)

| Evidence | static_obvious |
| Needs human | no (0/1) |
| Reason | TRANSITIVE_IMPORT |
| Key binding | <code>from pymoo.core.problem import Problem</code> @ run.py:197 |
| Owner | pymoo |
| Proposed GT | library / pymoo |

**Representative expressions:**

- <code>Problem(n_var=f.dim, n_obj=1, n_constr=0, xl=np.zeros(f.dim), xu=np.ones(f.dim))</code> -- run.py:202

**All bindings (1 unique):**
- <code>run.py</code> L197: <code>from pymoo.core.problem import Problem</code>

## Group 100: results -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ functions/robot_push.py:54 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>results.append(-(initial_dist - ret1 - ret2))</code> -- functions/robot_push.py:73

**All bindings (1 unique):**
- <code>functions/robot_push.py</code> L54: <code>[]</code>

## Group 101: w -> python/python (1 records)

| Evidence | static_context |
| Needs human | no (0/1) |
| Reason | LOCAL_DEFINITION |
| Key binding | <code>[]</code> @ functions/synthetic.py:78 |
| Owner | None |
| Proposed GT | python / python |

**Representative expressions:**

- <code>w.append(1 + (x[idx] - 1) / 4)</code> -- functions/synthetic.py:80

**All bindings (1 unique):**
- <code>functions/synthetic.py</code> L78: <code>[]</code>
