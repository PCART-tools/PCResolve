# SDOML — static_context (16 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| aia_fits_to_np.py:31:4 | `parser.add_argument('--src', dest='src', required=True)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 30); .add_argument is argparse method |
| aia_fits_to_np.py:32:4 | `parser.add_argument('--target', dest='target', required=True)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 30); .add_argument is argparse method |
| aia_fits_to_np.py:33:4 | `parser.add_argument('--scale', dest='scale', required=True, type=int)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 30); .add_argument is argparse method |
| aia_fits_to_np.py:34:4 | `parser.add_argument('--normalize', dest='normalize', type=bool, def...` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 30); .add_argument is argparse method |
| aia_fits_to_np.py:35:11 | `parser.parse_args()` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 30); .parse_args is argparse method |
| aia_fits_to_np.py:58:13 | `Map(remote)` | library / sunpy | library / sunpy | direct_import | static_context | v: from sunpy.map import Map (line 18); Map is sunpy class |
| aia_fits_to_np.py:68:10 | `fn.split('_')[0].replace('AIA', '')` | python / python | local / local | builtin_method_local_receiver | static_context | v: source context: fn is a filename string yielded by os.walk; split and replace pr |
| aia_fits_to_np.py:70:21 | `fn.split('_')[-1].replace('.fits', '')` | python / python | local / local | builtin_method_local_receiver | static_context | v: source context: fn is a filename string yielded by os.walk; split and replace pr |
| aia_fits_to_np.py:164:4 | `P.map(handle, ts)` | library / multiprocessing | library / multiprocessing | direct_import | static_context | v: P = multiprocessing.Pool(8) (line 163); .map is Pool method |
| hmi_fits_to_np.py:26:4 | `parser.add_argument('--src', dest='src', required=True)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 25); .add_argument is argparse method |
| hmi_fits_to_np.py:27:4 | `parser.add_argument('--target', dest='target', required=True)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 25); .add_argument is argparse method |
| hmi_fits_to_np.py:28:4 | `parser.add_argument('--scale', dest='scale', required=True, type=int)` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 25); .add_argument is argparse method |
| hmi_fits_to_np.py:29:11 | `parser.parse_args()` | library / argparse | library / argparse | direct_import | static_context | v: parser = argparse.ArgumentParser() (line 25); .parse_args is argparse method |
| hmi_fits_to_np.py:36:13 | `Map(remote)` | library / sunpy | library / sunpy | direct_import | static_context | v: from sunpy.map import Map (line 16); Map is sunpy class |
| hmi_fits_to_np.py:83:12 | `p.replace(src, '')` | python / python | library / os | builtin_method_local_receiver | static_context | v: source context: p is a path string yielded by os.walk, so replace is a builtins. |
| hmi_fits_to_np.py:101:4 | `P.map(handle, ts)` | library / multiprocessing | library / multiprocessing | direct_import | static_context | v: P = multiprocessing.Pool(16) (line 100); .map is Pool method |
