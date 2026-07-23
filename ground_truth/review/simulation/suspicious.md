# simulation — Suspicious Records (2)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| analytical.py:51:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | library / porepy | conversion_boundary | dynamic_probe | owner mismatch: expected=numpy pcresolve=porepy |
| data.py:157:14 | `g.tags['domain_boundary_faces'].nonzero()` | library / numpy | library / porepy | conversion_boundary | dynamic_probe | owner mismatch: expected=numpy pcresolve=porepy |
