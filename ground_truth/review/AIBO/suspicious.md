# AIBO — Suspicious Records (9)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| functions/mujoco.py:40:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/mujoco.py:115:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/mujoco.py:207:12 | `x.reshape(self.policy_shape)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/push_utils.py:52:16 | `fixture.shape.draw(body, fixture)` | local / local | unknown / unknown | monkey_patched_local_method | static_context | kind mismatch: expected=local pcresolve=unknown<br>owner mismatch: expected=local pcresolve=unknown |
| functions/push_utils.py:198:14 | `world.CreateStaticBody(position=(0, 0), shapes=b2PolygonS...` | library / Box2D | unknown / unknown | box2d_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/push_utils.py:211:14 | `world.CreateStaticBody(position=pos, shapes=b2PolygonShap...` | library / Box2D | unknown / unknown | box2d_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/rover_utils.py:44:17 | `params.reshape((-1, self.d))` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/rover_utils.py:164:16 | `lX.all(axis=1)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| functions/rover_utils.py:164:33 | `hX.all(axis=1)` | library / numpy | unknown / unknown | numpy_array_receiver | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
