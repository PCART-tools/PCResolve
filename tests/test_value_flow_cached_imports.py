## @package tests.test_value_flow_cached_imports

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve._cached_imports as cached


def analyze(tmp_path, prefix='from dependency import ready\n', export='def value(): return 7\n'):
    (tmp_path / 'dependency.py').write_text('ready = 1\n' + export, encoding='utf-8')
    (tmp_path / 'sample.py').write_text(prefix + '''
def entry(**kwargs):
    from dependency import value as selected
    return kwargs.pop('legacy', 0)
''', encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'entry'))


def test_cached_import_requires_prior_module_initialization_and_stable_source_export(tmp_path):
    result = analyze(tmp_path)
    record = result.functions[0]['cached_local_imports'][0]
    assert record['kind'] == 'source_cached_import_binding'
    assert record['status'] == 'bound_on_normal_cached_import_return'
    assert record['runtime_import_confirmed'] is False
    assert record['bindings'] == [
        {'name': 'selected', 'module': 'dependency', 'attribute': 'value'}]
    assert record['effects'] == 'module_execution_not_required_if_cache_preserved'
    assert str(tmp_path / 'sample.py') in record['source_hashes']
    assert str(tmp_path / 'dependency.py') in record['source_hashes']
    assert record['assumptions']


@pytest.mark.parametrize('prefix,export', [
    ('', 'def value(): return 7\n'),
    ('if flag:\n    from dependency import ready\n', 'def value(): return 7\n'),
    ('from dependency import ready\n', 'value = opaque()\n'),
    ('from dependency import ready\n', 'if flag:\n    def value(): return 7\n'),
    ('from dependency import ready\n', 'def __getattr__(name): return opaque\n'),
    ('from dependency import ready\n', 'exec("value = opaque")\n'),
    ('from dependency import ready\n', 'setattr(opaque, "value", unknown)\n'),
    ('from dependency import ready\nimport sys\ndel sys.modules["dependency"]\n',
     'def value(): return 7\n'),
    ('from dependency import ready\nimport sys\nsys.modules.clear()\n',
     'def value(): return 7\n'),
    ('from dependency import ready\n__builtins__ = opaque\n', 'def value(): return 7\n'),
    ('from dependency import ready\nimport builtins\nbuiltins.__import__ = opaque\n',
     'def value(): return 7\n'),
    ('from dependency import ready\nimport sys\ncache = sys.modules\nopaque(cache)\n',
     'def value(): return 7\n'),
    ('from dependency import ready\nimport dependency\ndependency.__class__ = opaque\n',
     'def value(): return 7\n'),
])
def test_open_initialization_or_export_cannot_supply_a_cached_binding(tmp_path, prefix, export):
    result = analyze(tmp_path, prefix, export)
    assert not result.functions[0].get('cached_local_imports')


def test_cached_import_budget_does_not_reuse_a_prior_complete_fact(tmp_path, monkeypatch):
    assert analyze(tmp_path).functions[0]['cached_local_imports']
    with monkeypatch.context() as patch:
        patch.setattr(cached, '_CACHED_IMPORT_NODE_LIMIT', 1)
        assert not analyze(tmp_path).functions[0].get('cached_local_imports')
    assert analyze(tmp_path).functions[0]['cached_local_imports']
