# simulation — dynamic_probe (15 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| analytical.py:44:8 | `g.bounding_box()` | library / porepy | library / porepy | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| analytical.py:45:8 | `g.bounding_box()` | library / porepy | library / porepy | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| analytical.py:51:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | library / porepy | conversion_boundary | dynamic_probe | v: runtime probe: domain_boundary_faces receiver is numpy.ndarray; nonzero is bound |
| export_results.py:31:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.grid_bucket.GridBucket and the boun |
| export_results.py:42:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| export_results.py:43:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| export_results.py:54:27 | `g.cell_diameters()` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and cell_diamet |
| export_results.py:56:20 | `g.closest_cell(np.array([xc_eval, np.zeros_like(xc_eval)]))` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and closest_cel |
| export_results.py:80:8 | `time_list.append('t = ' + np.str(time) + ' [s]')` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.list; append is bound to the list |
| export_results.py:83:13 | `delimiter.join(header_list)` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.str; join is bound to the string |
| data.py:153:8 | `g.bounding_box()` | library / porepy | library / porepy | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| data.py:154:8 | `g.bounding_box()` | library / porepy | library / porepy | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.structured.CartGrid and bounding_bo |
| data.py:157:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | library / porepy | conversion_boundary | dynamic_probe | v: runtime probe: domain_boundary_faces receiver is numpy.ndarray; nonzero is bound |
| discretization.py:54:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.grid_bucket.GridBucket and the boun |
| solve.py:48:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | v: PorePy 0.5.0 probe: receiver is porepy.grids.grid_bucket.GridBucket and the boun |
