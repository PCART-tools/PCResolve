#!/usr/bin/env python3
## @package scripts.compare_public_api
#  Compare the current public exports and legacy paths with a frozen manifest.

import argparse
import inspect
import json
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import pcresolve
from pcresolve.runtime._legacy_imports import _targets


def manifest():
    exports = {}
    for name in sorted(pcresolve.__all__):
        value = getattr(pcresolve, name)
        try:
            signature = str(inspect.signature(value))
        except (TypeError, ValueError):
            signature = None
        exports[name] = dict(module=getattr(value, '__module__', None),
                             qualname=getattr(value, '__qualname__', None),
                             signature=signature)
    legacy = {name[len('pcresolve.'):]: target
              for name, target in _targets('pcresolve').items()
              if name.count('.') == 1}
    return dict(exports=exports, legacy_modules=legacy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads(args.baseline.read_text(encoding='utf-8'))
    current = manifest()
    differences = {}
    for section in ('exports', 'legacy_modules'):
        old, new = before[section], current[section]
        missing, added = sorted(set(old) - set(new)), sorted(set(new) - set(old))
        changed = {name: dict(before=old[name], after=new[name])
                   for name in sorted(set(old) & set(new)) if old[name] != new[name]}
        if missing or added or changed:
            differences[section] = dict(missing=missing, added=added, changed=changed)
    project_config = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', project_config, re.MULTILINE)
    if version_match is None:
        raise RuntimeError('pyproject.toml has no static project version')
    report = dict(version=version_match.group(1), python=sys.version,
                  platform=platform.platform(), baseline=str(args.baseline),
                  exports=current['exports'], legacy_modules=current['legacy_modules'],
                  compatible=not differences, differences=differences)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    print('public API compatible: %s; exports=%d; legacy paths=%d' %
          (not differences, len(current['exports']), len(current['legacy_modules'])))
    return 0 if not differences else 1


if __name__ == '__main__':
    raise SystemExit(main())
