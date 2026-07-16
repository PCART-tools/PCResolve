# tensorflow1 — static_obvious (6 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| tf_decorator.py:8:8 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tf_decorator.py:15:15 | `tf.matmul(inputs, self.w)` | library / tensorflow | library / tensorflow | direct_import | static_obvious | v: direct import-backed API call |
| tf_decorator.py:18:17 | `super()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| tf_decorator.py:22:8 | `tf.keras.Sequential([CustomLayer(10, input_shape=(5,))])` | library / tensorflow | library / tensorflow | direct_import | static_obvious | v: direct import-backed API call |
| tf_decorator.py:27:15 | `tf.keras.models.load_model('custom_model.keras')` | library / tensorflow | library / tensorflow | direct_import | static_obvious | v: direct import-backed API call |
| tf_decorator.py:28:0 | `print(loaded_model.summary())` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
