## @package tests.test_private_observer_results

import ast

import pytest

from pcresolve import FlowAnalyzer
from pcresolve._metadata_calls import _entry


SOURCE = '''import inspect
class Observer:
    def __init__(self, obj): self.o = obj
    @staticmethod
    def count(fn): return len(inspect.signature(fn).parameters)
    def get_setters(self):
        result = []
        for name in dir(self.o):
            if not name.startswith('set_'): continue
            fn = getattr(self.o, name)
            if not callable(fn): continue
            result.append(name[4:])
        return result
class Public:
    def set_value(self, value): pass
def consume(value): return value
def build(cls):
    return consume(Observer(cls).get_setters())
'''


def prepare(root, source=SOURCE):
    (root / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    selected = analyzer._definition_index.find('example', 'Observer.count')[0]
    return analyzer, selected


def test_a_private_data_result_does_not_expose_the_observer_class(tmp_path):
    analyzer, selected = prepare(tmp_path)
    before = ast.dump(analyzer._definition_index.find('example', 'Observer', kind='class')[0][1])
    binding = _entry(analyzer, selected)
    assert binding is not None
    assert binding['status'] == 'source_bound'
    projections = binding['private_query_results']
    assert len(projections) == 1
    proof = projections[0]
    assert proof['kind'] == 'private_observer_data_result'
    assert proof['query']['result_shape'] == 'native_string_list'
    assert proof['owner_class'] == binding['owner_class']
    assert proof['scope'] == 'observer_class_identity_only'
    assert proof['runtime_execution_confirmed'] is False
    assert proof['observation_guard']['source_hashes'] == analyzer.hashes
    assert set(proof['assumptions']).issubset(binding['assumptions'])
    assert ast.dump(analyzer._definition_index.find('example', 'Observer', kind='class')[0][1]) == before


@pytest.mark.parametrize('old,new', [
    ('Observer(cls).get_setters()', 'Observer(cls)'),
    ('Observer(cls).get_setters()', 'Observer(cls).unknown()'),
    ('Observer(cls).get_setters()', 'Observer(cls).get_setters(Observer)'),
    ('Observer(cls).get_setters()', 'Observer(Observer).get_setters()'),
    ('return result', 'return self'),
    ('return result', 'return self.__class__'),
    ('return result', 'opaque(self)\n        return result'),
    ('result.append(name[4:])', 'result.append(self)'),
    ('def consume(value): return value',
     'def consume(value): return value\ndef expose(obj): obj.__class__.count = opaque\nexpose(Observer(Public))'),
    ('def consume(value): return value',
     'def consume(value): return value\nObserver.count = opaque'),
    ('def consume(value): return value',
     'def consume(value): return value\nopaque(Observer)'),
    ('def consume(value): return value',
     'def consume(value): return value\nimport gc\ndef inspect_live(): return gc.get_objects()'),
    ('def consume(value): return value',
     'def consume(value): return value\nimport sys\ndef inspect_live(): return sys._getframe().f_locals'),
])
def test_open_receivers_mutations_and_observation_still_block_binding(tmp_path, old, new):
    analyzer, selected = prepare(tmp_path, SOURCE.replace(old, new))
    assert _entry(analyzer, selected) is None


def test_a_separate_argument_exposure_cannot_hide_in_a_private_result(tmp_path):
    source = SOURCE.replace('consume(Observer(cls).get_setters())',
                            'consume((Observer(cls).get_setters(), Observer))')
    analyzer, selected = prepare(tmp_path, source)
    assert _entry(analyzer, selected) is None


def test_native_input_metadata_remains_a_separate_obligation(tmp_path):
    analyzer, selected = prepare(tmp_path)
    binding = _entry(analyzer, selected)
    assert binding is not None
    query = binding['private_query_results'][0]['query']
    assert query['status'] == 'requires_native_class_metadata'
    # Projection discharges only the observer identity escape. It does not
    # bind a runtime input, prove its lookup protocol, or compute actual names.
    assert query['owner_binding']['status'] == 'requires_source_member_bindings'
    assert query['input_preconditions']['exact_metaclass'] == 'type'
    assert 'result' not in query


def test_private_projection_does_not_replace_the_shared_escape_cache(tmp_path):
    analyzer, selected = prepare(tmp_path)
    original = analyzer._class_binding_writes(include_escapes=True)
    assert any(item[0].qualname == 'Observer' for item in original[0])
    assert _entry(analyzer, selected) is not None
    assert analyzer._class_binding_writes(include_escapes=True) == original


@pytest.mark.parametrize('invocation', ['get_setters(4)', 'get_setters(padding=4)'])
def test_private_projection_binds_literal_query_arguments(tmp_path, invocation):
    source = SOURCE.replace('def get_setters(self):', 'def get_setters(self, padding=2):')
    source = source.replace('get_setters())', invocation + ')')
    analyzer, selected = prepare(tmp_path, source)
    binding = _entry(analyzer, selected)
    assert binding is not None
    query = binding['private_query_results'][0]['query']
    assert query['query_arguments']['defaults'] == {}
    assert (query['query_arguments']['positional'] == [4]
            or query['query_arguments']['keywords'] == {'padding': 4})


@pytest.mark.parametrize('arguments', ['opaque()', '*values', '**values', 'padding=Observer',
                                       'padding=4, **values', '4, padding=4'])
def test_private_projection_rejects_open_or_invalid_query_arguments(tmp_path, arguments):
    source = SOURCE.replace('def get_setters(self):', 'def get_setters(self, padding=2):')
    source = source.replace('get_setters())', 'get_setters(' + arguments + '))')
    analyzer, selected = prepare(tmp_path, source)
    assert _entry(analyzer, selected) is None
