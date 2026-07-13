# qho — static_context (10 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| qho.py:177:10 | `fig.add_subplot(121)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:178:10 | `fig.add_subplot(122)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:180:4 | `ax1.set_xlabel('time', fontsize=16)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:181:4 | `ax1.set_title('Control', fontsize=18)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:182:4 | `ax1.tick_params(axis='both', which='major', labelsize=16)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:184:4 | `ax2.set_xlabel('time', fontsize=16)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:185:4 | `ax2.set_title('State', fontsize=18)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:186:4 | `ax2.tick_params(axis='both', which='major', labelsize=16)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:189:4 | `ax1.plot(tm, uopt)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| qho.py:190:4 | `ax2.plot(t, np.abs(qho.Y.T) ** 2)` | library / matplotlib | library / matplotlib | transitive_method | static_context | v: receiver ownership inferred through return-value propagation |
