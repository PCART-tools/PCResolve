# SDOML — static_obvious (75 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| aia_fits_to_np.py:16:0 | `matplotlib.use('agg', warn=False, force=True)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:24:0 | `warnings.filterwarnings('ignore')` | library / warnings | library / warnings | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:30:13 | `argparse.ArgumentParser()` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:40:12 | `open(fn)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:40:12 | `open(fn).read()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:40:12 | `open(fn).read().strip()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:40:12 | `open(fn).read().strip().split('\n')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:43:15 | `l.split(',')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:44:26 | `float(f)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:51:22 | `getDegrad('%s/degrad_%d.csv' % (path, wl))` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| aia_fits_to_np.py:60:8 | `print('FILE CORRUPTED: %s' % remote)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:66:6 | `np.where(X <= 0.0)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:68:10 | `fn.split('_')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:70:17 | `int(fn.split('_')[-1].replace('.fits', ''))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:70:21 | `fn.split('_')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:72:14 | `max(Xd.meta['EXPTIME'], 0.01)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:88:16 | `skimage.transform.SimilarityTransform(scale=scale_factor, translati...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.SimilarityTransform |
| aia_fits_to_np.py:89:13 | `skimage.transform.warp(X, XForm.inverse, preserve_range=True, mode=...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.warp |
| aia_fits_to_np.py:90:13 | `skimage.transform.warp(validMask, XForm.inverse, preserve_range=Tru...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.warp |
| aia_fits_to_np.py:93:13 | `np.divide(Xr, Xd + 1e-08)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:99:23 | `np.int(X.shape[0] / scale)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:101:13 | `skimage.transform.downscale_local_mean(Xr, (divideFactor, divideFac...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.downscale_local_mean |
| aia_fits_to_np.py:107:8 | `np.savez_compressed(local, x=Xr)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:112:13 | `sunpy.io.read_file_header(remote)` | library / sunpy | library / sunpy | direct_import | static_obvious | v: import-backed dotted module call: sunpy.io.read_file_header |
| aia_fits_to_np.py:116:8 | `print(remote)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:122:13 | `sunpy.io.read_file_header(remote)` | library / sunpy | library / sunpy | direct_import | static_obvious | v: import-backed dotted module call: sunpy.io.read_file_header |
| aia_fits_to_np.py:126:8 | `print(remote)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:131:11 | `parse_args()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| aia_fits_to_np.py:133:14 | `loadAIADegrads('degrad')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| aia_fits_to_np.py:135:4 | `print(args)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:138:11 | `os.path.exists(target)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:139:8 | `os.mkdir(target)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:143:24 | `os.walk(src)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:144:8 | `print(p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:147:15 | `os.path.exists(tp)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:148:12 | `os.mkdir(tp)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:150:22 | `enumerate(files)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:152:16 | `print('\t%04d/%04d' % (fni, len(files)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:152:43 | `len(files)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:153:19 | `fn.endswith('.fits')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:156:15 | `int(fn[-12:-10])` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:157:16 | `ts.append((fn, '%s/%s/%s' % (src, p, fn), '%s/%s/%s' % (target, p, ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:157:78 | `fn.replace('.fits', '.npz')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:159:4 | `ts.sort()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| aia_fits_to_np.py:161:4 | `random.shuffle(ts)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| aia_fits_to_np.py:163:8 | `multiprocessing.Pool(8)` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:14:0 | `matplotlib.use('agg', warn=False, force=True)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:22:0 | `warnings.filterwarnings('ignore')` | library / warnings | library / warnings | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:25:13 | `argparse.ArgumentParser()` | library / argparse | library / argparse | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:35:8 | `print(local)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:38:8 | `print('FILE CORRUPTED: %s' % remote)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:55:12 | `skimage.transform.SimilarityTransform(scale=scale_factor, translati...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.SimilarityTransform |
| hmi_fits_to_np.py:56:9 | `skimage.transform.warp(X, XForm.inverse, preserve_range=True, mode=...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.warp |
| hmi_fits_to_np.py:57:9 | `skimage.transform.warp(validMask, XForm.inverse, preserve_range=Tru...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.warp |
| hmi_fits_to_np.py:60:9 | `np.divide(Xr, Xd + 1e-08)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:63:19 | `np.int(X.shape[0] / scale)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:64:9 | `skimage.transform.downscale_local_mean(Xr, (divideFactor, divideFac...` | library / skimage | library / skimage | direct_import | static_obvious | v: import-backed dotted module call: skimage.transform.downscale_local_mean |
| hmi_fits_to_np.py:68:4 | `np.savez_compressed(local, x=Xr)` | library / numpy | library / numpy | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:71:11 | `parse_args()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| hmi_fits_to_np.py:73:4 | `print(args)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:76:11 | `os.path.exists(target)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:77:8 | `os.mkdir(target)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:81:24 | `os.walk(src)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:82:8 | `print(p)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:85:15 | `os.path.exists(tp)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:86:12 | `os.mkdir(tp)` | library / os | library / os | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:88:22 | `enumerate(files)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:90:16 | `print('\t%04d/%04d' % (fni, len(files)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:90:43 | `len(files)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:91:19 | `fn.endswith('.fits')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:94:12 | `ts.append((fn, '%s/%s/%s' % (src, p, fn), '%s/%s/%s' % (target, p, ...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:94:74 | `fn.replace('.fits', '.npz')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:96:4 | `ts.sort()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| hmi_fits_to_np.py:98:4 | `random.shuffle(ts)` | library / random | library / random | direct_import | static_obvious | v: direct import-backed API call |
| hmi_fits_to_np.py:100:8 | `multiprocessing.Pool(16)` | library / multiprocessing | library / multiprocessing | direct_import | static_obvious | v: direct import-backed API call |
