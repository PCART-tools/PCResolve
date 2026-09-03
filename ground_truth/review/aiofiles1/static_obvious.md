# aiofiles1 — static_obvious (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| async_pattern.py:5:15 | `aiofiles.open('test.txt', mode='w')` | library / aiofiles | library / aiofiles | - | static_obvious | v: direct import-backed API call |
| async_pattern.py:8:15 | `aiofiles.open('test.txt', mode='r')` | library / aiofiles | library / aiofiles | - | static_obvious | v: direct import-backed API call |
| async_pattern.py:13:7 | `asyncio.run(async_file_io())` | library / asyncio | library / asyncio | - | static_obvious | v: direct import-backed API call |
| async_pattern.py:13:19 | `async_file_io()` | local / local | local / local | - | static_obvious | v: project-local function/method call |
