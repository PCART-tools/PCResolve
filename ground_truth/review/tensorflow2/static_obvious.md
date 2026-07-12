# tensorflow2 — static_obvious (8 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| tf_decorator.py:10:11 | `MyTensor(x.values + y.values, metadata='added')` | local / local | local / local | - | static_obvious | v: project-local function/method call |
| tf_decorator.py:8:1 | `dispatch.dispatch_for_api(tf.math.add)` | library / tensorflow | library / tensorflow | - | static_obvious | v: import-backed dotted module call |
| tf_decorator.py:12:4 | `MyTensor(tf.constant([1, 2]), 'tensor_a')` | local / local | local / local | - | static_obvious | v: project-local function/method call |
| tf_decorator.py:12:13 | `tf.constant([1, 2])` | library / tensorflow | library / tensorflow | - | static_obvious | v: direct import-backed API call |
| tf_decorator.py:13:4 | `MyTensor(tf.constant([3, 4]), 'tensor_b')` | local / local | local / local | - | static_obvious | v: project-local function/method call |
| tf_decorator.py:13:13 | `tf.constant([3, 4])` | library / tensorflow | library / tensorflow | - | static_obvious | v: direct import-backed API call |
| tf_decorator.py:14:4 | `tf.math.add(a, b)` | library / tensorflow | library / tensorflow | - | static_obvious | v: direct import-backed API call |
| tf_decorator.py:15:0 | `print(c.values)` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
