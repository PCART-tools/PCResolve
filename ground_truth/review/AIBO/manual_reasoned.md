# AIBO — manual_reasoned (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| run.py:41:8 | `f_class(dim=args.dim, foldername=f'{args.method}-{args.batch_size}'...` | local / local | local / local | dynamic_local_callable | manual_reasoned | v: callable resolves to a project-local synthetic or benchmark object in the surrou |
| functions/push_utils.py:216:4 | `b2world_interface.add_bodies(obs)` | unknown / unknown | unknown / unknown | unconstrained_dead_code_parameter | manual_reasoned | gt: add_obstacles() has no project call site, so b2world_interface has no concrete o<br>v: method name and surrounding Box2D usage do not prove the receiver object's owner |
| functions/rover_utils.py:286:16 | `roverdomain.estimate_cost()` | unknown / unknown | unknown / unknown | unconstrained_dead_code_parameter | manual_reasoned | gt: plot_3d_forest_rover() has no project call site, so roverdomain has no concrete <br>v: the parameter name suggests RoverDomain but does not statically constrain its ru |
| functions/rover_utils.py:289:18 | `roverdomain.traj.get_points(np.linspace(0.0, 1.0, ntraj_points, end...` | unknown / unknown | unknown / unknown | unconstrained_dead_code_parameter | manual_reasoned | gt: plot_3d_forest_rover() has no project call site, so roverdomain.traj has no conc<br>v: the intended local trajectory type is not established by an executable project c |
