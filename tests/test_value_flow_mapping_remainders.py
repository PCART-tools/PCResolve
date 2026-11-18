## @package tests.test_value_flow_mapping_remainders

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_mapping_remainders'


def analyze(name, **limits):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=name), max_depth=3, **limits)


def named(result, name, caller):
    return next(c for c in result.calls if c.caller.qualname == caller and c.callee_name == name)


def remainder(call):
    return next(e for e in call.effects if e['kind'] == 'mapping_remainder')


def test_bounded_writes_and_unrelated_calls_preserve_only_the_open_remainder():
    result = analyze('root')
    normal = named(result, 'normalize', 'root')
    proof = remainder(normal)
    assert proof['excluded_paths'] == [['V'], ['VI'], ['p'], ['w']]
    assert proof['completion'] == 'normal_return'
    assert proof['value_completeness'] == 'unaffected_keys_only'
    assert normal.result_sources[0]['container_object']['identity'] == 'argument_alias'
    assert named(result, 'result.pop', 'root').target_status == 'local_container_protocol'
    filtered = remainder(named(result, 'filter_keys', 'root'))
    assert filtered['excluded_paths'] == [['p'], ['w']]
    values = [v for a in named(result, 'fixed', 'root').argument_sources for v in a['sources']
              if v.get('kind') == 'parameter' and v.get('source') == 'kwargs']
    assert values
    assert all(all([key] in v['excluded_paths'] for key in ('p', 'w', 'V', 'VI', 'out'))
               for v in values)
    assert not any(v.get('kind') == 'parameter' and v.get('source') == 'args'
                   and v.get('output_path') == ['*'] for a in named(result, 'fixed', 'root').argument_sources
                   for v in a['sources'])


def test_tuple_slot_retains_identity_but_other_slot_cannot_recover_the_mapping():
    result = analyze('tuple_root')
    proof = remainder(named(result, 'packed', 'tuple_root'))
    assert proof['return_path'] == [1]
    assert named(result, 'result.pop', 'tuple_root').target_status == 'local_container_protocol'
    other = analyze('tuple_other')
    assert not any(v.get('kind') == 'parameter' and v.get('source') == 'kwargs'
                   for a in named(other, 'fixed', 'tuple_other').argument_sources for v in a['sources'])


@pytest.mark.parametrize('name', ['clear_before', 'clear_after', 'finite_root'])
def test_cleared_or_finite_contents_cannot_regain_an_open_root(name):
    result = analyze(name)
    assert not any(v.get('kind') == 'parameter' and v.get('source') == 'kwargs'
                   for a in named(result, 'fixed', name).argument_sources for v in a['sources'])


def test_copy_is_a_distinct_object_and_removals_keep_previous_exclusions():
    result = analyze('copy_before')
    assert named(result, 'normalize', 'copy_before').result_sources[0]['container_object']
    assert any(v.get('kind') == 'parameter' and v.get('source') == 'kwargs'
               for a in named(result, 'fixed', 'copy_before').argument_sources for v in a['sources'])


@pytest.mark.parametrize('helper', ['cleared', 'rebuilt', 'changed', 'rebound_key', 'growing_keys',
                                    'escaped_keys', 'unclear', 'recursive', 'bad_tuple'])
def test_unproved_helper_body_has_no_remainder_fact(helper, tmp_path):
    source = (ROOT / 'cases.py').read_text(encoding='utf-8')
    extra = (', ["out"]' if helper in ('rebound_key', 'growing_keys', 'escaped_keys')
             else ', unknown' if helper in ('unclear', 'bad_tuple') else '')
    source += '\ndef probe(**kwargs):\n return ' + helper + '(kwargs' + extra + ')\n'
    (tmp_path / 'cases.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='cases', qualname='probe'))
    assert not any(e['kind'] == 'mapping_remainder' for c in result.calls for e in c.effects)


@pytest.mark.parametrize('name', ['alias_root', 'escaped_global', 'unknown_input',
                                'captured_alias', 'self_reference', 'modified_keys'])
def test_aliases_escape_or_unknown_shape_cannot_license_remainder(name):
    assert not any(e['kind'] == 'mapping_remainder' for c in analyze(name).calls
                   if c.caller.qualname == name for e in c.effects)


def test_budget_is_explicit_and_does_not_become_an_empty_remainder():
    result = analyze('root', max_call_contexts=1)
    assert not any(e['kind'] == 'mapping_remainder' for c in result.calls for e in c.effects)
    assert any('budget' in b['reason'] or 'limit' in b['reason'] for b in result.boundaries)


def test_closed_branch_key_alternatives_form_a_conservative_union():
    result = analyze('branch_keys')
    proof = remainder(named(result, 'filter_keys', 'branch_keys'))
    assert proof['excluded_paths'] == [['p'], ['w']]
    assert len(proof['finite_sequence_sources']['keys']) == 2


def test_root_and_expansion_queries_do_not_reuse_another_calls_remainder_state():
    analyzer = FlowAnalyzer(project_root=ROOT)
    selector = FunctionRef(module='cases', qualname='root')
    first = analyzer.analyze(selector)
    snapshot = first.to_dict()
    analyzer.analyze(FunctionRef(module='cases', qualname='unsafe_root'))
    assert analyzer.analyze(selector).to_dict() == snapshot
    call = named(first, 'normalize', 'root')
    analyzer.expand(first, call.id)
    assert first.to_dict() == snapshot


def test_independent_local_runtime_controls_confirm_clear_copy_filter_and_tuple_selection():
    import runpy

    namespace = runpy.run_path(str(ROOT / 'cases.py'), init_globals={'notify': lambda *args: None})
    mapping = {'old': 7, 'p': 2, 'out': 3}
    output = namespace['normalize']((), mapping)
    assert output is mapping
    namespace['filter_keys'](output, ['p', 'out'])
    assert mapping == {'old': 7}
    _, projected = namespace['packed'](mapping)
    assert projected is mapping
    assert namespace['clear_before'](old=7) == 0
    assert namespace['clear_after'](old=7) == 0
    assert namespace['copy_before'](allowed=7) == 7
    with pytest.raises(TypeError, match='old'):
        namespace['copy_before'](old=7)


def test_finite_key_ceiling_is_a_budget_boundary_not_a_no_effect_proof(tmp_path):
    body = ''.join("    mapping['k%d'] = None\n" % i for i in range(70))
    (tmp_path / 'cases.py').write_text('def helper(mapping):\n' + body
        + '    return mapping\n\ndef root(**kwargs):\n    return helper(kwargs)\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='cases', qualname='root'))
    assert not any(e['kind'] == 'mapping_remainder' for c in result.calls for e in c.effects)
    assert any(b['reason'] == 'mapping_remainder_budget' for b in result.boundaries)
