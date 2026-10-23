## @package tests.test_callable_metadata_queries

import ast
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve._metadata_queries import metadata_query


SOURCE = '''import inspect
from functools import lru_cache
class Observer:
    @staticmethod
    @lru_cache(maxsize=None)
    def count(fn):
        return len(inspect.signature(fn).parameters)
    @staticmethod
    @lru_cache(maxsize=None)
    def alias(fn):
        text = inspect.getdoc(fn)
        if text is None:
            return False
        return text.startswith('Alias ')
'''


def prepare(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, path


def query(analyzer, name):
    target = analyzer._definition_index.find('example', name)[0]
    return metadata_query(analyzer, target)


@pytest.mark.parametrize('name,shape,protocol', [
    ('Observer.count', 'int', 'native_signature_resolution_without_user_callbacks'),
    ('Observer.alias', 'bool', 'native_documentation_resolution_without_user_callbacks'),
])
def test_native_metadata_queries_are_conditional_effect_templates(tmp_path, name, shape, protocol):
    analyzer, path = prepare(tmp_path)
    fact = query(analyzer, name)
    assert fact is not None
    assert fact['kind'] == 'source_callable_metadata_query'
    assert fact['status'] == 'requires_native_callable_metadata'
    assert fact['result_shapes'] == [shape]
    assert fact['input_preconditions']['parameter'] == 'fn'
    assert protocol in fact['input_preconditions']['protocols']
    assert fact['input_effects']['source_writes'] == []
    assert fact['input_effects']['source_exposures'] == []
    assert fact['input_effects']['native_cache_retention'] is True
    assert fact['runtime_execution_confirmed'] is False
    assert fact['source_hashes'] == {str(path): analyzer.hashes[str(path)]}
    assert fact['construction']['future_body_effects'] == 'unmodeled'


def test_source_query_fact_does_not_discharge_open_decorator_binding(tmp_path):
    analyzer, _ = prepare(tmp_path)
    result = analyzer.analyze(FunctionRef('example', 'Observer.count'))
    summary = next(item for item in result.functions if item['function']['qualname'] == 'Observer.count')
    assert summary['native_callable_metadata_queries'][0]['status'] == 'requires_native_callable_metadata'
    assert any(b['reason'] == 'decorator_effect_unconfirmed' for b in result.boundaries)


def test_query_result_has_an_independent_native_runtime_control(tmp_path):
    analyzer, path = prepare(tmp_path)
    assert query(analyzer, 'Observer.count')['result_shapes'] == ['int']
    namespace = runpy.run_path(str(path))
    def described(one, two=0):
        """Alias documented."""
    assert namespace['Observer'].count(described) == 2
    assert namespace['Observer'].alias(described) is True
    assert namespace['Observer'].count.cache_info().currsize == 1


@pytest.mark.parametrize('body', [
    'fn.__doc__ = "changed"\n        return 0',
    'saved = fn\n        saved.extra = 1\n        return 0',
    'opaque(fn)\n        return 0',
    'return fn()',
    'return fn',
    'saved.append(fn)\n        return 0',
    'global saved\n        saved = fn\n        return 0',
    'text = inspect.getdoc(fn)\n        return text.startswith("Alias ")',
    'return inspect.signature(fn).return_annotation',
    'return len(inspect.signature(fn, eval_str=True).parameters)',
])
def test_open_queries_and_input_capabilities_are_not_readonly(tmp_path, body):
    analyzer, _ = prepare(tmp_path, SOURCE.replace(
        'return len(inspect.signature(fn).parameters)', body))
    assert query(analyzer, 'Observer.count') is None


@pytest.mark.parametrize('tail', [
    'inspect.signature = opaque',
    'saved = inspect\nopaque(saved)',
    'saved = inspect.signature\nopaque(saved)',
    'import builtins\nbuiltins.len = opaque',
    'import builtins\nbuiltins.staticmethod = opaque',
    'import builtins\nbuiltins.getattr = opaque',
    'import builtins\nbuiltins.callable = opaque',
])
def test_replaced_protocols_keep_the_query_open(tmp_path, tail):
    analyzer, _ = prepare(tmp_path, SOURCE + '\n' + tail + '\n')
    assert query(analyzer, 'Observer.count') is None


def test_query_specialization_preserves_source_ast(tmp_path):
    analyzer, _ = prepare(tmp_path)
    target = analyzer._definition_index.find('example', 'Observer.alias')[0]
    before = ast.dump(target[1])
    assert metadata_query(analyzer, target) is not None
    assert ast.dump(target[1]) == before


def test_an_unparsed_primary_module_keeps_the_native_namespace_unconfirmed(tmp_path):
    (tmp_path / 'broken.py').write_text('def broken(:\n', encoding='utf-8')
    analyzer, _ = prepare(tmp_path)
    assert analyzer.index_boundaries
    assert query(analyzer, 'Observer.count') is None
