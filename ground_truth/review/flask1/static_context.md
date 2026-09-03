# flask1 — static_context (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| app.py:5:1 | `app.route('/')` | library / flask | library / flask | transitive_method | static_context | gt: Flask application route decorator<br>v: app is created by Flask(__name__); route() is a Flask application method |
| app.py:10:4 | `app.run()` | library / flask | library / flask | transitive_method | static_context | gt: Flask application runner<br>v: app is created by Flask(__name__); run() is a Flask application method |
| flask_decorator.py:3:9 | `app.test_client()` | library / flask | library / flask | transitive_method | static_context | gt: Flask test client factory<br>v: app is imported from the Flask application module; test_client() returns a Flask |
| flask_decorator.py:4:11 | `client.get('/')` | library / flask | library / flask | transitive_method | static_context | gt: Flask test client request method<br>v: client is returned by Flask test_client(); get() is a Flask test client method |
