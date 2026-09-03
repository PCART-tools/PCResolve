## @package tests.test_regression_finite_eval_selection
#  Bounded eval of qualified names uses source alternatives, never execution.

import pytest

from pcresolve import analyze_project


def _calls(tmp_path, source):
    (tmp_path / 'models.py').write_text('''
class First:
    pass
class Second:
    pass
''', encoding='utf-8')
    (tmp_path / 'main.py').write_text(source, encoding='utf-8')
    return {call.func_name: call.top_library for call in
            analyze_project(str(tmp_path)).all_api_calls}


def test_guarded_qualified_eval_names_are_local_alternatives(tmp_path):
    calls = _calls(tmp_path, '''
import models
selected = 'First'
if selected in ['First', 'Second']:
    constructor = eval(f'models.{selected}')
    constructor()
''')
    assert calls['constructor'] == 'local'
    assert calls['eval'] == 'python'


@pytest.mark.parametrize('body', [
    "constructor = eval(f'models.{selected}')",
    "if selected in ['First', 'Second']:\n    selected = arbitrary()\n    constructor = eval(f'models.{selected}')",
    "if selected in ['First', 'Second']:\n    constructor = eval(f'models.{selected}()', globals())",
])
def test_open_eval_or_modified_guard_remains_unknown(tmp_path, body):
    calls = _calls(tmp_path, '''
import models
from runtime import selected, arbitrary
%s
constructor()
''' % body)
    assert calls['constructor'] == 'unknown'


def test_namespace_attribute_guard_before_constructor_arguments(tmp_path):
    calls = _calls(tmp_path, '''
import models
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--name')
parser.add_argument('--dim', type=int)
args = parser.parse_args()
if args.name in ['First', 'Second']:
    constructor = eval(f'models.{args.name}')
    constructor(args.dim)
''')
    assert calls['constructor'] == 'local'


@pytest.mark.parametrize('source', [
    "if selected in ['First', 'Second']:\n    def deferred():\n        constructor = eval(f'models.{selected}')\n        constructor()",
    "if args.name in ['First', 'Second']:\n    args.name = arbitrary()\n    constructor = eval(f'models.{args.name}')\n    constructor()",
    "if selected in ['First', 'Second']:\n    models = arbitrary()\n    constructor = eval(f'models.{selected}')\n    constructor()",
    "if selected in ['First', 'Second']:\n    models.First = arbitrary()\n    constructor = eval(f'models.{selected}')\n    constructor()",
    "if selected in ['First', 'Second']:\n    arbitrary(models)\n    constructor = eval(f'models.{selected}')\n    constructor()",
    "if args.name in ['First', 'Second']:\n    args.change()\n    constructor = eval(f'models.{args.name}')\n    constructor()",
])
def test_guard_or_namespace_identity_cannot_escape_its_binding(tmp_path, source):
    calls = _calls(tmp_path, '''
import models
from runtime import selected, args, arbitrary
%s
''' % source)
    assert calls['constructor'] == 'unknown'


@pytest.mark.parametrize('mutation', [
    'arbitrary([models])',
    'alias = models; alias.First = arbitrary()',
])
def test_import_namespace_escape_cannot_prove_finite_eval(tmp_path, mutation):
    calls = _calls(tmp_path, '''
import models
from runtime import arbitrary
selected = 'First'
if selected in ['First', 'Second']:
    %s
    constructor = eval(f'models.{selected}')
    constructor()
''' % mutation)
    assert calls['constructor'] == 'unknown'


def test_custom_equality_does_not_prove_formatted_name(tmp_path):
    calls = _calls(tmp_path, '''
import models
class Name:
    def __eq__(self, other):
        return True
    def __format__(self, spec):
        return 'Missing'
selected = Name()
if selected in ['First', 'Second']:
    constructor = eval(f'models.{selected}')
    constructor()
''')
    assert calls['constructor'] == 'unknown'


@pytest.mark.parametrize('before', [
    'models.First = arbitrary()', 'alias = models',
    'arbitrary(models)', 'models.mutate()',
])
def test_namespace_must_be_stable_outside_guard_too(tmp_path, before):
    calls = _calls(tmp_path, '''
import models
from runtime import arbitrary
%s
selected = 'First'
if selected in ['First', 'Second']:
    constructor = eval(f'models.{selected}')
    constructor()
''' % before)
    assert calls['constructor'] == 'unknown'
