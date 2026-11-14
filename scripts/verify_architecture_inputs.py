#!/usr/bin/env python3
## @package scripts.verify_architecture_inputs
#  Fail early when the release baseline, source syntax, or API imports are invalid.

import compileall
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / 'tests' / 'baselines' / 'architecture_1_0_8'
REVISION = '7444cc9d4e75f0e71575f4d38e95423c45f60a3f'
SOURCE_SHA256 = 'e77ca58d9d175e0ef06d177f523d0ecb697694211faf229f5becbe0f27dc510f'
CORPUS = {'ground_truth/projects.json': '9c81fcd0f2faaa1d3b9513d5a7e63220ce34c981',
          'tests/fixtures/value_flow_matrix': '48d2eb5b2170f80fd3971d8e9d041c8cb5a7fbdb',
          'tests/fixtures/tested_projects': '9c17e82a30f427c51ef7b5c206abf66ace49af40'}


def check_baselines(directory=BASELINES):
    """Require the complete, versioned pre-refactor baseline inventory."""
    analysis = json.loads((directory / 'analysis.json').read_text(encoding='utf-8'))
    api = json.loads((directory / 'api.json').read_text(encoding='utf-8'))
    for record in (analysis, api):
        if (record.get('revision') != REVISION or record.get('hash_seed') != '0'
                or record.get('source_sha256') != SOURCE_SHA256):
            raise ValueError('Invalid baseline revision, source hash, or hash seed')
    outputs = analysis['outputs']
    if (sum(k.startswith('ownership/') for k in outputs) != 42
            or sum(k.startswith('flow/') for k in outputs) != 83
            or set(outputs) != set(analysis['call_counts'])
            or analysis.get('corpus_git_objects') != CORPUS
            or any(not isinstance(v, str) or len(v) != 64 for v in outputs.values())
            or any(type(v) is not int or v < 0 for v in analysis['call_counts'].values())
            or analysis.get('path_normalization') != 'flow-checkout-root-v2'):
        raise ValueError('Incomplete analysis baseline')
    if (len(api['exports']) != 19 or len(api['legacy_modules']) != 56
            or set(api.get('legacy_original_modules', {})) != set(api['legacy_modules'])
            or any(value != 'pcresolve.' + name
                   for name, value in api['legacy_original_modules'].items())):
        raise ValueError('Incomplete API baseline')
    return api


def main():
    api = check_baselines()
    if not compileall.compile_dir(str(ROOT / 'src' / 'pcresolve'), quiet=1, force=True):
        raise RuntimeError('Source compilation failed')
    from compare_public_api import compare, manifest
    differences = compare(api, manifest())
    if differences:
        raise RuntimeError('API compatibility failed: %s' % differences)
    import pcresolve.cli
    if not callable(pcresolve.cli.main) or importlib.util.find_spec('pcresolve.__main__') is None:
        raise RuntimeError('CLI entry point unavailable')
    print('source compilation, baseline inventory, and public imports passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
