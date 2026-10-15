## @package tests.test_value_flow_callable_instance_binding
#  Conditional source bindings and constructor-state limits for callable instances.
import copy
from pathlib import Path

import pytest
import pcresolve._callable_instance_binding as instance_binding

from pcresolve import FlowAnalyzer, FunctionRef


PROVIDER = '''
DEFAULTS = {}
DEFAULTS['allowed'] = None

class Validator:
    def __init__(self, defaults, fname=None, method=None):
        self.defaults = defaults
        self.fname = fname
        self.method = method

    def __call__(self, args, kwargs):
        return kwargs

validator = Validator(DEFAULTS, fname='check', method='kwargs')
'''
CONSUMER = '''
import provider as nv
def entry(**kwargs):
    return nv.validator((), kwargs)
'''


def analyze(tmp_path, provider=PROVIDER, extra=None, analyzer=None):
    if analyzer is None:
        (tmp_path / 'provider.py').write_text(provider, encoding='utf-8')
        (tmp_path / 'consumer.py').write_text(CONSUMER, encoding='utf-8')
        if extra:
            (tmp_path / 'mutation.py').write_text(extra, encoding='utf-8')
        analyzer = FlowAnalyzer(project_root=tmp_path)
    return analyzer.analyze(FunctionRef(module='consumer', qualname='entry'), max_depth=2)


def call(result):
    return result.find_calls(callee_name='nv.validator')[0]


def test_constructor_backed_callable_has_conditional_binding_and_finite_state(tmp_path):
    result = analyze(tmp_path)
    edge = call(result)
    binding = edge.callable_instance_evidence.get('binding', {})
    assert binding.get('status') == 'source_bound'
    assert binding['basis'] == 'source_snapshot'
    assert binding['runtime_target_confirmed'] is False
    assert binding['target'] == result.to_dict()['calls'][0]['target']
    assert binding['implicit_binding'] == {'parameter': 'self', 'status': 'static_bound'}
    assert binding['receiver_state']['defaults'] == {
        'kind': 'mapping', 'items': {'allowed': {'kind': 'literal', 'value': None}}}
    assert binding['receiver_state']['method'] == {'kind': 'literal', 'value': 'kwargs'}
    assert binding['receiver_state']['fname'] == {'kind': 'literal', 'value': 'check'}
    assert binding['source_hashes'] and binding['evidence'] and binding['assumptions']
    assert not binding['issues']
    assert edge.target_status == 'callable_instance_candidate'
    boundary = next(b for b in result.boundaries if b.get('call_id') == edge.id
                    and b['reason'] == 'dynamic_callable_instance_override_possible')
    assert boundary['boundary_kind'] == 'assumption'
    assert boundary['binding_status'] == 'source_bound'


def test_omitted_constructor_default_is_materialized(tmp_path):
    result = analyze(tmp_path, PROVIDER.replace("fname='check', ", ''))
    assert call(result).callable_instance_evidence['binding']['receiver_state']['fname'] == {
        'kind': 'literal', 'value': None}


@pytest.mark.parametrize('suffix', [
    "validator.method = 'both'", "DEFAULTS['other'] = None", "DEFAULTS.clear()",
    'alias = validator', 'alias = DEFAULTS', 'unknown(validator)',
    'Validator.__call__ = replacement',
    "def mutate():\n    validator.defaults['other'] = None",
    "def mutate():\n    DEFAULTS['other'] = None",
])
def test_visible_state_changes_aliases_or_escapes_never_prove_binding(tmp_path, suffix):
    result = analyze(tmp_path, PROVIDER + '\n' + suffix + '\n')
    assert call(result).callable_instance_evidence.get('binding', {}).get('status') != 'source_bound'


@pytest.mark.parametrize('source', [
    'import provider as p\np.validator.method = "both"',
    'from provider import DEFAULTS as other\nother["extra"] = None',
    'from provider import validator as other\nunknown(other)',
    'from provider import Validator as C\nC.__call__ = replacement',
    'import provider as nv\nother = nv\nother.validator.method = "args"',
])
def test_cross_module_writes_and_aliases_are_not_snapshot_assumptions(tmp_path, source):
    result = analyze(tmp_path, extra=source)
    assert call(result).callable_instance_evidence.get('binding', {}).get('status') != 'source_bound'


@pytest.mark.parametrize('replacement', [
    'self.defaults = unknown(defaults)',
    'self.defaults = defaults\n        unknown(self)',
])
def test_constructor_effects_must_be_closed(tmp_path, replacement):
    result = analyze(tmp_path, PROVIDER.replace('self.defaults = defaults', replacement))
    assert call(result).callable_instance_evidence.get('binding', {}).get('status') != 'source_bound'


@pytest.mark.parametrize('member', [
    'def __getattribute__(self, name):\n        return unknown(name)',
    'def __setattr__(self, name, value):\n        unknown(value)',
    '@property\n    def defaults(self):\n        return unknown()',
])
def test_custom_lookup_and_descriptors_do_not_prove_state(tmp_path, member):
    source = PROVIDER.replace('    def __call__(self, args, kwargs):',
                              '    ' + member + '\n\n    def __call__(self, args, kwargs):')
    result = analyze(tmp_path, source)
    assert call(result).callable_instance_evidence.get('binding', {}).get('status') != 'source_bound'


def test_unknown_constructor_values_remain_unconfirmed(tmp_path):
    result = analyze(tmp_path, PROVIDER.replace("method='kwargs'", 'method=unknown'))
    assert call(result).callable_instance_evidence.get('binding', {}).get('status') != 'source_bound'


def test_repeated_queries_do_not_share_mutable_receiver_state(tmp_path):
    result = analyze(tmp_path)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    first = analyze(tmp_path, analyzer=analyzer)
    original = copy.deepcopy(first.to_dict())
    second = analyze(tmp_path, analyzer=analyzer)
    call(second).callable_instance_evidence['binding']['receiver_state']['method']['value'] = 'both'
    assert first.to_dict() == original
    assert analyze(tmp_path, analyzer=analyzer).to_dict() == original


def test_dictionary_shape_survives_exact_ordinary_helper_bindings(tmp_path):
    provider = PROVIDER.replace('return kwargs', 'return copy_data(kwargs)') + '''
def copy_data(data):
    return data.copy()
'''
    result = analyze(tmp_path, provider)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef(module='consumer', qualname='entry'), max_depth=3)
    edge = result.find_calls(callee_name='data.copy')[0]
    assert edge.target_status == 'local_container_protocol'
    assert any(e['operation'] == 'copy' and e['status'] == 'bounded' for e in edge.effects)


def test_unknown_ordinary_input_does_not_invent_dictionary_copy_protocol(tmp_path):
    analyze(tmp_path)
    (tmp_path / 'provider.py').write_text(PROVIDER + '''
def copy_data(data):
    return data.copy()
''', encoding='utf-8')
    (tmp_path / 'consumer.py').write_text('''
import provider as nv
def unknown(data):
    return nv.copy_data(data)
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef(module='consumer', qualname='unknown'), max_depth=2)
    assert result.find_calls(callee_name='data.copy')[0].target_status == 'receiver_unresolved'


def test_binding_budget_exhaustion_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(instance_binding, 'NODE_LIMIT', 1)
    result = analyze(tmp_path)
    binding = call(result).callable_instance_evidence['binding']
    assert binding['status'] == 'unconfirmed'
    assert any(i['reason'] == 'callable_instance_binding_budget' for i in binding['issues'])


def test_prior_mutation_of_an_alias_blocks_the_copy_proof(tmp_path):
    analyze(tmp_path)
    (tmp_path / 'provider.py').write_text('''
def duplicate(first, second):
    second.clear()
    return first.copy()
''', encoding='utf-8')
    (tmp_path / 'consumer.py').write_text('''
import provider as nv
def entry(**kwargs):
    return nv.duplicate(kwargs, kwargs)
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef(module='consumer', qualname='entry'), max_depth=2)
    edge = result.find_calls(callee_name='first.copy')[0]
    assert edge.target_status == 'receiver_unresolved'
    assert not any(e['operation'] == 'copy' and e['status'] == 'bounded' for e in edge.effects)


def test_shape_metadata_does_not_erase_known_empty_tuple_guard(tmp_path):
    analyze(tmp_path)
    (tmp_path / 'provider.py').write_text('''
def guarded(values, mapping):
    if not values:
        return mapping
    unknown(mapping)
    return mapping
''', encoding='utf-8')
    (tmp_path / 'consumer.py').write_text('''
import provider as nv
def entry(**kwargs):
    mapping = nv.guarded((), kwargs)
    mapping.pop('out', None)
    return mapping
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef(module='consumer', qualname='entry'), max_depth=2)
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and any(['out'] in p.get('excluded_paths', []) for p in paths)


@pytest.mark.parametrize('statement', [
    "self.defaults['old'] = None", "self.defaults.update({'old': None})", 'escape(self)'
])
def test_instance_state_mutation_in_methods_is_not_a_closed_binding(tmp_path, statement):
    source = PROVIDER.replace('return kwargs', statement + '\n        return kwargs')
    result = analyze(tmp_path, source)
    assert call(result).callable_instance_evidence['binding']['status'] == 'unconfirmed'
