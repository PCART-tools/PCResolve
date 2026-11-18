## @package tests.test_class_creation_metadata_queries

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


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
class Base:
    def __init_subclass__(cls):
        cls.parameter_count = Observer.count(cls.set_value)
        if Observer.alias(cls.set_value):
            cls.alias_seen = True
class Public(Base):
    def __init__(self, **kwargs): fixed(**kwargs)
    def set_value(self, value):
        """Alias field."""
        self.value = value
def fixed(allowed=0): return allowed
'''


def prepare(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    return FlowAnalyzer(project_root=root), path


def test_creation_consumes_queries_with_a_fresh_native_function_argument(tmp_path):
    analyzer, _ = prepare(tmp_path)
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    hook = binding['class_creation_hooks'][0]
    assert hook['attributes'] == ['parameter_count', 'alias_seen']
    queries = hook['callable_metadata_queries']
    assert len(queries) == 2
    assert {tuple(q['result_shapes']) for q in queries} == {('int',), ('bool',)}
    for query in queries:
        assert query['status'] == 'source_bound'
        assert query['input_binding']['kind'] == 'fresh_source_class_function'
        assert query['input_binding']['attribute'] == 'set_value'
        assert query['input_binding']['receiver_class'] == hook['receiver_class']
        assert query['input_binding']['phase'] == 'before_class_decorators'
        assert query['query']['status'] == 'requires_native_callable_metadata'
        assert query['query']['input_effects']['native_cache_retention'] is True
        assert query['source_hashes'] == result.inputs['sha256']
        assert set(query['assumptions']).issubset(hook['assumptions'])
    # Query returns are native scalar shapes, not invented concrete answers.
    assert all('result' not in query for query in queries)


def test_source_creation_queries_have_an_independent_runtime_control(tmp_path):
    analyzer, path = prepare(tmp_path)
    assert analyzer.analyze(FunctionRef('example', 'Public')).inputs['entry_binding']['status'] == 'source_bound'
    namespace = runpy.run_path(str(path))
    cls = namespace['Public']
    assert cls.parameter_count == 2 and cls.alias_seen is True
    assert cls(allowed=1).__class__ is cls


def test_creation_consumes_native_metadata_of_a_doc_decorated_fresh_method(tmp_path):
    decorator = '''def document(fn):
    fn.__doc__ = 'Generated native documentation.'
    return fn
'''
    source = decorator + SOURCE.replace('    def set_value(self, value):',
                                        '    @document\n    def set_value(self, value):')
    analyzer, _ = prepare(tmp_path, source)
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    queries = result.inputs['entry_binding']['class_creation_hooks'][0]['callable_metadata_queries']
    assert len(queries) == 2
    for query in queries:
        formation = query['input_binding']['metadata_formation']
        assert formation['metadata_shapes']['documentation'] == ['str']
        assert formation['current_namespace_binding_confirmed'] is False
        assert query['input_binding']['status'] == 'source_bound'
        assert set(formation['assumptions']).issubset(query['assumptions'])
        if 'native_documentation_resolution_without_user_callbacks' in query['query']['input_preconditions']['protocols']:
            assert 'source_function_documentation_native_shape_preserved' in query['assumptions']
            assert 'source_function_docstrings_preserved' not in query['assumptions']


@pytest.mark.parametrize('value', ['None', '123', 'opaque'])
def test_doc_metadata_resolution_does_not_assume_original_literal_survived(tmp_path, value):
    decorator = 'def document(fn):\n    fn.__doc__ = ' + value + '\n    return fn\n'
    source = decorator + SOURCE.replace('    def set_value(self, value):',
                                        '    @document\n    def set_value(self, value):')
    analyzer, _ = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


@pytest.mark.parametrize('old,new', [
    ('return len(inspect.signature(fn).parameters)', 'fn.extra = True\n        return 2'),
    ('return len(inspect.signature(fn).parameters)', 'opaque(fn)\n        return 2'),
    ('Observer.count(cls.set_value)', 'Observer.count(opaque)'),
    ('Observer.count(cls.set_value)', 'Observer.count(cls.set_value, opaque)'),
    ('Observer.count(cls.set_value)', 'Observer.count(cls.set_value, flag=True)'),
    ('cls.parameter_count =', 'cls.set_value = opaque\n        cls.parameter_count ='),
    ('cls.parameter_count =', 'cls.set_value.__doc__ = cls\n        cls.parameter_count ='),
    ('cls.parameter_count =',
     'cls.deferred = lambda: Observer.count(cls.set_value)\n        cls.parameter_count ='),
    ('"""Alias field."""', 'pass'),
    ('def set_value(self, value):', '@opaque\n    def set_value(self, value):'),
])
def test_open_inputs_and_effects_do_not_discharge_class_creation(tmp_path, old, new):
    analyzer, _ = prepare(tmp_path, SOURCE.replace(old, new))
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


@pytest.mark.parametrize('tail', [
    'Observer.count = opaque',
    'opaque(Observer)',
    'Observer.count.__wrapped__.__code__ = opaque',
])
def test_query_entry_replacement_and_exposure_remain_boundaries(tmp_path, tail):
    analyzer, _ = prepare(tmp_path, SOURCE + '\n' + tail + '\n')
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_a_constructed_observer_instance_can_expose_its_class_binding(tmp_path):
    replacement = '''def replace(instance):
    instance.__class__.count = staticmethod(lambda fn: -1)
replace(Observer())
'''
    source = SOURCE.replace('class Public(Base):', replacement + 'class Public(Base):')
    analyzer, path = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))
    # A native object allocator still returns an instance whose __class__ can
    # replace the query method. Dropping its class callee from the enclosing
    # escape argument would incorrectly preserve the original cache binding.
    namespace = runpy.run_path(str(path))
    assert namespace['Public'].parameter_count == -1


@pytest.mark.parametrize('mutation', [
    '@classmethod\n    def seed(cls): cls.count = opaque',
    'def __init__(self): type(self).count = opaque',
    'def seed(self): self.__class__.count = opaque',
])
def test_helper_receiver_class_mutations_leave_member_lookup_open(tmp_path, mutation):
    source = SOURCE.replace('class Observer:', 'class Observer:\n    ' + mutation)
    analyzer, _ = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))
