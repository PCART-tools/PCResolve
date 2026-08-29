# simulation — Suspicious Records (6)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| analytical.py:44:8 | `g.bounding_box()` | library / porepy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=porepy pcresolve=unknown<br>expected library, pcresolve=unknown |
| analytical.py:45:8 | `g.bounding_box()` | library / porepy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=porepy pcresolve=unknown<br>expected library, pcresolve=unknown |
| analytical.py:51:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | unknown / unknown | conversion_boundary | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| data.py:153:8 | `g.bounding_box()` | library / porepy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=porepy pcresolve=unknown<br>expected library, pcresolve=unknown |
| data.py:154:8 | `g.bounding_box()` | library / porepy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=porepy pcresolve=unknown<br>expected library, pcresolve=unknown |
| data.py:157:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | unknown / unknown | conversion_boundary | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
