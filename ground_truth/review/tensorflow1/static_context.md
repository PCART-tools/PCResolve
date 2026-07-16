# tensorflow1 — static_context (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| tf_decorator.py:8:8 | `super().__init__(**kwargs)` | library / tensorflow | library / tensorflow | transitive_method | static_context | v: CustomLayer inherits tensorflow.keras.layers.Layer; super().__init__ resolves to |
| tf_decorator.py:18:17 | `super().get_config()` | library / tensorflow | library / tensorflow | transitive_method | static_context | v: CustomLayer inherits tensorflow.keras.layers.Layer; super().get_config resolves  |
| tf_decorator.py:19:8 | `config.update({'units': self.units})` | python / python | unknown / unknown | builtin | static_context | v: config is the mapping returned by the Keras Layer get_config() contract |
| tf_decorator.py:22:29 | `CustomLayer(10, input_shape=(5,))` | local / local | local / local | decorated_callable_receiver | static_context | v: decorated local callable; primary identity is local, decorator evidence in decor |
