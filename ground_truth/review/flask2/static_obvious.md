# flask2 — static_obvious (48 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| app.py:4:10 | `Flask(__name__)` | library / flask | library / flask | direct_import | static_obvious | gt: Flask constructor<br>v: direct import-backed API call |
| app.py:26:16 | `abort(401, description='invalid authorization token')` | library / flask | library / flask | direct_import | static_obvious | gt: flask abort()<br>v: direct import-backed API call |
| app.py:27:19 | `f(*args, **kwargs)` | local / local | local / local | local_call | static_obvious | gt: local wrapper calls decorated function via parameter f<br>v: project-local function/method call |
| app.py:35:19 | `f(*args, **kwargs)` | local / local | local / local | local_call | static_obvious | gt: local wrapper calls decorated function via parameter f<br>v: project-local function/method call |
| app.py:45:15 | `jsonify({'tasks': tasks})` | library / flask | library / flask | direct_import | static_obvious | gt: flask jsonify()<br>v: direct import-backed API call |
| app.py:41:5 | `app.route('/api/tasks', methods=['GET'])` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.route() decorator expression, flask via factory return<br>v: decorator expression is import-backed usage |
| app.py:51:15 | `next((task for task in tasks if task['id'] == task_id), None)` | python / python | python / python | builtin | static_obvious | gt: Python builtin next()<br>v: Python builtin function call |
| app.py:53:12 | `abort(404, description='Task Not Found')` | library / flask | library / flask | direct_import | static_obvious | gt: flask abort()<br>v: direct import-backed API call |
| app.py:54:15 | `jsonify({'task': task})` | library / flask | library / flask | direct_import | static_obvious | gt: flask jsonify()<br>v: direct import-backed API call |
| app.py:48:5 | `app.route('/api/tasks/<int:task_id>', methods=['GET'])` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.route() decorator expression, flask via factory return<br>v: decorator expression is import-backed usage |
| app.py:61:12 | `abort(400, description='Missing Required Parameters')` | library / flask | library / flask | direct_import | static_obvious | gt: flask abort()<br>v: direct import-backed API call |
| app.py:70:15 | `jsonify({'task': task})` | library / flask | library / flask | direct_import | static_obvious | gt: flask jsonify()<br>v: direct import-backed API call |
| app.py:57:5 | `app.route('/api/tasks', methods=['POST'])` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.route() decorator expression, flask via factory return<br>v: decorator expression is import-backed usage |
| app.py:76:15 | `next((task for task in tasks if task['id'] == task_id), None)` | python / python | python / python | builtin | static_obvious | gt: Python builtin next()<br>v: Python builtin function call |
| app.py:78:12 | `abort(404, description='Task Not Found')` | library / flask | library / flask | direct_import | static_obvious | gt: flask abort()<br>v: direct import-backed API call |
| app.py:81:12 | `abort(400, description='Missing Request')` | library / flask | library / flask | direct_import | static_obvious | gt: flask abort()<br>v: direct import-backed API call |
| app.py:87:15 | `jsonify({'task': task})` | library / flask | library / flask | direct_import | static_obvious | gt: flask jsonify()<br>v: direct import-backed API call |
| app.py:73:5 | `app.route('/api/tasks/<int:task_id>', methods=['PUT'])` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.route() decorator expression, flask via factory return<br>v: decorator expression is import-backed usage |
| app.py:103:22 | `getattr(error, 'description', None)` | python / python | python / python | builtin | static_obvious | gt: Python builtin getattr()<br>v: Python builtin function call |
| app.py:105:57 | `str(error)` | python / python | python / python | builtin | static_obvious | gt: Python builtin str()<br>v: Python builtin function call |
| app.py:107:19 | `jsonify({'error': description, 'status_code': error.code})` | library / flask | library / flask | direct_import | static_obvious | gt: flask jsonify()<br>v: direct import-backed API call |
| app.py:89:5 | `app.errorhandler(400)` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.errorhandler() decorator expression, flask via factory return<br>v: decorator expression is import-backed usage |
| app.py:90:5 | `app.errorhandler(401)` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.errorhandler() decorator expression<br>v: decorator expression is import-backed usage |
| app.py:91:5 | `app.errorhandler(404)` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.errorhandler() decorator expression<br>v: decorator expression is import-backed usage |
| app.py:92:5 | `app.errorhandler(500)` | library / flask | library / flask | decorator_expression | static_obvious | gt: @app.errorhandler() decorator expression<br>v: decorator expression is import-backed usage |
| app.py:115:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory function call<br>v: project-local function/method call |
| flask_decorator.py:5:8 | `func()` | local / local | local / local | local_call | static_obvious | gt: local parameter call in run_test<br>v: project-local function/method call |
| flask_decorator.py:6:8 | `print(f'[✓] Test Pass: {test_name}')` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:9:8 | `print(f'[×] Test Failed: {test_name} - Assertion Error: {str(e)}')` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:9:66 | `str(e)` | python / python | python / python | builtin | static_obvious | gt: Python builtin str()<br>v: Python builtin function call |
| flask_decorator.py:11:8 | `print(f'[×] Test Exception: {test_name} - Unexpected Error: {str(e)}')` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:11:70 | `str(e)` | python / python | python / python | builtin | static_obvious | gt: Python builtin str()<br>v: Python builtin function call |
| flask_decorator.py:20:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory call in test<br>v: project-local function/method call |
| flask_decorator.py:29:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory call in test<br>v: project-local function/method call |
| flask_decorator.py:36:11 | `len(data['tasks'])` | python / python | python / python | builtin | static_obvious | gt: Python builtin len()<br>v: Python builtin function call |
| flask_decorator.py:41:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory call in test<br>v: project-local function/method call |
| flask_decorator.py:57:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory call in test<br>v: project-local function/method call |
| flask_decorator.py:63:20 | `len(initial_response.json['tasks'])` | python / python | python / python | builtin | static_obvious | gt: Python builtin len()<br>v: Python builtin function call |
| flask_decorator.py:76:11 | `len(updated_response.json['tasks'])` | python / python | python / python | builtin | static_obvious | gt: Python builtin len()<br>v: Python builtin function call |
| flask_decorator.py:85:10 | `create_app()` | local / local | local / local | local_call | static_obvious | gt: local factory call in test<br>v: project-local function/method call |
| flask_decorator.py:121:12 | `len(tests)` | python / python | python / python | builtin | static_obvious | gt: Python builtin len()<br>v: Python builtin function call |
| flask_decorator.py:123:4 | `print('=' * 50)` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:124:4 | `print('Test Suite Running')` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:125:4 | `print('=' * 50 + '\n')` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:128:11 | `run_test(name, test_func)` | local / local | local / local | local_call | static_obvious | gt: local function run_test()<br>v: project-local function/method call |
| flask_decorator.py:131:4 | `print('\n' + '=' * 50)` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:132:4 | `print(f'Test Result: Pass {passed} Cases; Failed {total - passed} C...` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| flask_decorator.py:133:4 | `print('=' * 50)` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
