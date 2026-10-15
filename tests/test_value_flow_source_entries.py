## @package tests.test_value_flow_source_entries
#  Source definition activation and bounded nested mapping effect composition.
import ast
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures/flow_source_entries'


def analyzer():
    return FlowAnalyzer(project_root=ROOT)


def analyze(name, depth=2):
    return analyzer().analyze(FunctionRef(module='library', qualname=name), max_depth=depth)


def test_try_class_methods_are_locatable_and_keep_activation_uncertainty():
    result = analyze('Fallback.run')
    assert result.entry.qualname == 'Fallback.run'
    assert result.find_calls(callee_name='fixed')[0].parameter_flows
    assert any(b['reason'] == 'conditional_definition_unconfirmed' for b in result.boundaries)


def test_conditional_duplicate_definitions_require_a_location():
    engine = analyzer()
    with pytest.raises(ValueError, match='exactly one'):
        engine.analyze(FunctionRef(module='library', qualname='Choice.run'))
    definitions = [ref for ref, node in engine.definitions if ref.qualname == 'Choice.run']
    assert len(definitions) == 2
    for definition in definitions:
        assert engine.analyze(definition).entry == definition


def test_constant_definition_conditions_reach_the_call_flow():
    result = analyze('Never.run')
    flow = result.find_calls(callee_name='fixed')[0].parameter_flows[0]
    assert any(c.get('test', {}).get('source_text') == 'False' and c.get('branch') is True
               for c in flow['conditions'])


def test_multiline_unicode_definition_conditions_use_cached_source_lines(tmp_path):
    source = '''if ("中文"
        and enabled):
    class Selected:
        def run(self, **kwargs):
            return fixed(**kwargs)

def fixed(allowed=None):
    return allowed
'''
    (tmp_path / 'library.py').write_text(source, encoding='utf-8')
    expected = ast.get_source_segment(source, ast.parse(source).body[0].test)
    with patch('ast.get_source_segment', side_effect=AssertionError('Whole-file rescan')):
        result = FlowAnalyzer(project_root=tmp_path).analyze(
            FunctionRef(module='library', qualname='Selected.run'))
    boundary = next(b for b in result.boundaries
                    if b['reason'] == 'conditional_definition_unconfirmed')
    assert boundary['conditions'][0]['test']['source_text'] == expected


def test_lambda_entry_no_longer_requires_a_statement_list_for_unused_parameters():
    result = analyze('lambda_forward')
    ref = result.find_calls(callee_name='target')[0].target
    inner = analyzer().analyze(ref)
    assert inner.entry == ref


def test_composed_finite_delete_retains_normal_return_identity_and_exclusions():
    result = analyze('finite_return', 1)
    call = result.find_calls(callee_name='clean')[0]
    assert call.effects and all(e['status'] == 'bounded' for e in call.effects)
    assert all(e['completion'] == 'normal_return' for e in call.effects)
    assert call.result_sources[0]['container_object']['identity'] == 'argument_alias'
    sink = result.find_calls(callee_name='fixed')[0]
    contents = [value for argument in sink.argument_sources for value in argument['sources']
                if value.get('kind') == 'parameter']
    assert contents and all(['out'] in value.get('excluded_paths', [])
                           and ['p'] in value.get('excluded_paths', []) for value in contents)


def test_unknown_sequence_cannot_publish_complete_composed_effects():
    result = analyze('unknown_keys')
    call = result.find_calls(callee_name='clean')[0]
    assert not any(e.get('status') == 'bounded' for e in call.effects)
    assert not any(v.get('container_object') for v in call.result_sources)


def test_queries_do_not_leak_conditional_or_composed_effect_state():
    engine = analyzer()
    first = engine.analyze(FunctionRef(module='library', qualname='finite_return'))
    original = asdict(first)
    engine.analyze(FunctionRef(module='library', qualname='Never.run'))
    second = engine.analyze(FunctionRef(module='library', qualname='finite_return'))
    assert asdict(first) == original == asdict(second)


@pytest.mark.parametrize('extra', [
    '    opaque(mapping)\n',
    "    mapping.clear()\n",
    "    mapping = {'value': 0}\n",
])
def test_composition_never_ignores_additional_helper_effects(tmp_path, extra):
    source = '''
def delete_keys(mapping, keys):
    for key in keys:
        if key in mapping:
            del mapping[key]
EXTRA
def clean(mapping, keys):
    delete_keys(mapping, keys)
    return mapping
def entry(**kwargs):
    return clean(kwargs, ('out',))
'''.replace('EXTRA', extra)
    (tmp_path / 'library.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='library', qualname='entry'))
    call = result.find_calls(callee_name='clean')[0]
    if 'clear()' in extra:
        assert not result.trace_parameter('kwargs')['return_paths']
    else:
        assert not any(v.get('container_object') for v in call.result_sources)


def test_parameter_shadowing_does_not_resolve_the_module_helper(tmp_path):
    source = (ROOT / 'library.py').read_text(encoding='utf-8').replace(
        'def clean(mapping, keys):', 'def clean(mapping, keys, delete_keys):')
    (tmp_path / 'library.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='library', qualname='finite_return'))
    call = result.find_calls(callee_name='clean')[0]
    assert not any(v.get('container_object') for v in call.result_sources)


def test_composed_effect_call_depth_is_bounded(tmp_path):
    source = (ROOT / 'library.py').read_text(encoding='utf-8')
    source += '\n'.join('def layer%d(mapping, keys):\n    %s(mapping, keys)\n    return mapping\n' %
        (index, 'delete_keys' if index == 0 else 'layer%d' % (index - 1)) for index in range(20))
    source += "\ndef root(**kwargs):\n    return layer19(kwargs, ('out',))\n"
    (tmp_path / 'library.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='library', qualname='root'))
    assert any(b['reason'] in ('mapping_effect_budget', 'container_return_budget') for b in result.boundaries)
