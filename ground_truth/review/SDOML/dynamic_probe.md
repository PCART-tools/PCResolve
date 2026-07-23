# SDOML — dynamic_probe (3 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| aia_fits_to_np.py:106:13 | `Xr.astype('float32')` | library / numpy | library / numpy | conversion_boundary | dynamic_probe | v: runtime probe: skimage.transform.downscale_local_mean returns numpy.ndarray; ast |
| aia_fits_to_np.py:145:12 | `p.replace(src, '')` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime project probe: p receiver type is builtins.str; replace is bound and its |
| hmi_fits_to_np.py:67:9 | `Xr.astype('float32')` | library / numpy | library / numpy | conversion_boundary | dynamic_probe | v: runtime probe: skimage.transform.downscale_local_mean returns numpy.ndarray; ast |
