# tensorflow1 — dynamic_probe (5 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| tf_decorator.py:12:17 | `self.add_weight(shape=(input_shape[-1], self.units))` | library / tensorflow | library / tensorflow | transitive_method | dynamic_probe | gt: TensorFlow Keras Layer method<br>v: inspect.getmodule(self.add_weight) reports tensorflow.python.keras.engine.base_l |
| tf_decorator.py:5:1 | `register_keras_serializable(package='MyLayers')` | library / tensorflow | library / tensorflow | direct_import | dynamic_probe | gt: TensorFlow Keras serialization decorator<br>v: inspect.getmodule(register_keras_serializable) reports tensorflow.python.keras.u |
| tf_decorator.py:23:0 | `model.compile(optimizer='adam', loss='mse')` | library / tensorflow | library / tensorflow | transitive_method | dynamic_probe | gt: TensorFlow Keras Model compile method<br>v: inspect.getmodule(model.compile) reports tensorflow.python.keras.engine.training |
| tf_decorator.py:25:0 | `model.save('custom_model.keras')` | library / tensorflow | library / tensorflow | transitive_method | dynamic_probe | gt: TensorFlow Keras Model save method<br>v: inspect.getmodule(model.save) reports tensorflow.python.keras.engine.training |
| tf_decorator.py:28:6 | `loaded_model.summary()` | library / tensorflow | library / tensorflow | transitive_method | dynamic_probe | gt: TensorFlow Keras Model summary method<br>v: inspect.getmodule(loaded_model.summary) reports tensorflow.python.keras.engine.n |
