# sg-restart-regridder — static_obvious (6 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| experiments_table.py:8:11 | `plt.get_cmap('Dark2')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| experiments_table.py:32:4 | `print(grids.__len__())` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| experiments_table.py:32:10 | `grids.__len__()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| experiments_table.py:34:9 | `pd.DataFrame(grids)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| experiments_table.py:34:9 | `pd.DataFrame(grids).set_index(['Region', 'ID'])` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| experiments_table.py:45:4 | `print(table)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
