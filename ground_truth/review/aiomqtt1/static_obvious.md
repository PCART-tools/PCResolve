# aiomqtt1 — static_obvious (6 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| async_pattern.py:5:15 | `Client('test.mosquitto.org')` | library / aiomqtt | library / aiomqtt | direct_import | static_obvious | v: direct import-backed API call |
| async_pattern.py:6:14 | `client.publish('temperature', payload='25.3')` | library / aiomqtt | library / aiomqtt | direct_import | static_obvious | v: direct import-backed API call |
| async_pattern.py:7:19 | `client.messages()` | library / aiomqtt | library / aiomqtt | direct_import | static_obvious | v: direct import-backed API call |
| async_pattern.py:8:18 | `client.subscribe('temperature')` | library / aiomqtt | library / aiomqtt | direct_import | static_obvious | v: direct import-backed API call |
| async_pattern.py:13:7 | `asyncio.run(mqtt_example())` | library / asyncio | library / asyncio | direct_import | static_obvious | v: direct import-backed API call |
| async_pattern.py:13:19 | `mqtt_example()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
