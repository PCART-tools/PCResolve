# Contrucao — Suspicious Records (1)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| main.py:10:8 | `data.decompose()` | library / bs4 | unknown / unknown | library_result_boundary | manual_reasoned | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=bs4 pcresolve=unknown<br>expected library, pcresolve=unknown<br>verification_level=manual_reasoned |
