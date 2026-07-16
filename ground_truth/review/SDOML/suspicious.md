# SDOML — Suspicious Records (6)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| aia_fits_to_np.py:68:10 | `fn.split('_')[0].replace('AIA', '')` | python / python | unknown / unknown | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| aia_fits_to_np.py:68:10 | `fn.split('_')` | python / python | unknown / unknown | builtin | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| aia_fits_to_np.py:70:21 | `fn.split('_')[-1].replace('.fits', '')` | python / python | unknown / unknown | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| aia_fits_to_np.py:70:21 | `fn.split('_')` | python / python | unknown / unknown | builtin | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| aia_fits_to_np.py:106:13 | `Xr.astype('float32')` | library / numpy | local / local | conversion_boundary | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| hmi_fits_to_np.py:67:9 | `Xr.astype('float32')` | library / numpy | library / skimage | conversion_boundary | dynamic_probe | owner mismatch: expected=numpy pcresolve=skimage |
