# simulation — Suspicious Records (15)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| analytical.py:44:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| analytical.py:45:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| analytical.py:51:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | local / local | conversion_boundary | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| data.py:153:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| data.py:154:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| data.py:157:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | local / local | conversion_boundary | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| discretization.py:54:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:31:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:42:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:43:8 | `g.bounding_box()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:54:27 | `g.cell_diameters()` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:56:20 | `g.closest_cell(np.array([xc_eval, np.zeros_like(xc_eval)]))` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
| export_results.py:80:8 | `time_list.append('t = ' + np.str(time) + ' [s]')` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| export_results.py:83:13 | `delimiter.join(header_list)` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| solve.py:48:8 | `gb.grids_of_dimension(2)` | library / porepy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=porepy pcresolve=local<br>expected library, pcresolve=local |
