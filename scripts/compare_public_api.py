#!/usr/bin/env python3
## @package scripts.compare_public_api
#  Compare the current public exports and legacy paths with a frozen manifest.

import argparse
import importlib
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


def compare(before, current):
    """Compare pre-refactor exports and verify actual legacy module identities."""
    differences = {}
    old_exports, new_exports = before['exports'], current['exports']
    missing = sorted(set(old_exports) - set(new_exports))
    added = sorted(set(new_exports) - set(old_exports))
    changed = {}
    for name in sorted(set(old_exports) & set(new_exports)):
        old, new = old_exports[name], new_exports[name]
        issues = []
        if old['qualname'] != new['qualname']:
            issues.append('qualname')
        old_signature, new_signature = old['signature'], new['signature']
        if new_signature is not None:
            new_signature = new_signature.replace('pcresolve.flow.analyzer.FunctionRef',
                                                  'pcresolve.flow.FunctionRef')
        if old_signature != new_signature:
            issues.append('signature')
        try:
            original = importlib.import_module(old['module'])
            for part in old['qualname'].split('.'):
                original = getattr(original, part)
            if original is not getattr(pcresolve, name):
                issues.append('legacy export identity')
        except (ImportError, AttributeError, TypeError):
            issues.append('legacy export unavailable')
        if issues:
            changed[name] = dict(before=old, after=new, issues=issues)
    if missing or added or changed:
        differences['exports'] = dict(missing=missing, added=added, changed=changed)

    old, new = before['legacy_modules'], current['legacy_modules']
    missing, added = sorted(set(old) - set(new)), sorted(set(new) - set(old))
    changed = {name: dict(before=old[name], after=new[name])
               for name in sorted(set(old) & set(new)) if old[name] != new[name]}
    for name in sorted(set(old) & set(new)):
        try:
            alias = importlib.import_module('pcresolve.' + name)
            target = importlib.import_module('pcresolve.' + new[name])
            if alias is not target:
                changed[name] = dict(before=old[name], after=new[name], issue='module identity')
        except ImportError as error:
            changed[name] = dict(before=old[name], after=new[name], issue=str(error))
    if missing or added or changed:
        differences['legacy_modules'] = dict(missing=missing, added=added, changed=changed)
    return differences


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads(args.baseline.read_text(encoding='utf-8'))
    current = manifest()
    differences = compare(before, current)
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
