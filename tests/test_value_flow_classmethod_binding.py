import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow as flow


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_classmethod_binding'


def analyze(entry, analyzer=None, depth=2):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='wrappers', qualname=entry), max_depth=depth)


def generate(result, caller=None):
    return next(call for call in result.calls if call.callee_name.endswith('.generate')
                and (caller is None or call.caller.qualname == caller))


@pytest.mark.parametrize('entry,receiver,owner', [
    ('direct', 'Backend', 'Backend'), ('imported_alias', 'Backend', 'Backend'),
    ('module_alias', 'Backend', 'Backend'), ('local_alias', 'Backend', 'Backend'),
    ('exported_alias', 'Backend', 'Backend'), ('inherited', 'Derived', 'Backend'),
    ('overridden', 'Override', 'Override')])
def test_source_classmethod_binding_explains_receiver_descriptor_and_implicit_cls(entry, receiver, owner):
    result = analyze(entry)
    call = generate(result)
    assert call.target.qualname == owner + '.generate'
    facts = call.class_method_bindings
    assert len(facts) == 1 and facts[0]['status'] == 'source_bound'
    fact = facts[0]
    assert fact['receiver_class']['qualname'] == receiver
    assert fact['definition_class']['qualname'] == owner
    assert fact['descriptor']['kind'] == 'builtin_classmethod'
    assert fact['implicit_binding']['parameter'] == 'cls'
    assert fact['implicit_binding']['receiver_class'] == fact['receiver_class']
    assert fact['basis'] == 'source_snapshot' and fact['runtime_target_confirmed'] is False
    assert fact['evidence'] and fact['assumptions']
    assert fact['source_hashes'][fact['receiver_class']['file_path']]
    assert fact['receiver_binding_evidence']
    assert any(argument['parameter'] == 'cls' and argument['argument'] == {'receiver': True}
               for argument in call.argument_sources)
    boundary = next(boundary for boundary in result.boundaries
                    if boundary.get('call_id') == call.id
                    and boundary['reason'] == 'dynamic_class_receiver_override_possible')
    assert boundary['boundary_kind'] == 'assumption'
    assert boundary['binding_status'] == 'source_bound'
    assert call.binding_status == 'uncertain'
    json.dumps(result.to_dict())


@pytest.mark.parametrize('entry', [
    'rebound', 'patched', 'reflected', 'escaped', 'unknown', 'mixed', 'returned',
    'unknown_factory', 'custom_meta', 'decorated', 'descriptor', 'shadowed', 'conditional'])
def test_unproved_or_modified_receiver_never_gets_source_bound_fact(entry):
    result = analyze(entry)
    call = generate(result)
    assert not any(fact['status'] == 'source_bound' for fact in call.class_method_bindings)
    assert any(boundary.get('call_id') == call.id
               and boundary.get('boundary_kind') != 'assumption' for boundary in result.boundaries)


@pytest.mark.parametrize('entry,issue', [('patched', 'visible_method_write'),
                                      ('reflected', 'visible_dynamic_attribute_write'),
                                      ('escaped', 'class_escape')])
def test_visible_uncertainty_has_source_evidence_not_just_external_monkeypatch(entry, issue):
    result = analyze(entry)
    call = generate(result)
    assert any(issue == item['reason'] and item.get('evidence')
               for fact in call.class_method_bindings for item in fact['issues'])


def test_repeated_queries_contexts_and_expand_preserve_binding_proofs_without_contamination():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('direct', analyzer)
    saved = first.to_dict()
    assert not any(fact['status'] == 'source_bound'
                   for fact in generate(analyze('returned', analyzer)).class_method_bindings)
    repeated = analyze('direct', analyzer)
    assert generate(first).class_method_bindings == generate(repeated).class_method_bindings
    assert first.to_dict() == saved
    initial = analyze('contexts', analyzer, depth=1)
    snapshot = initial.to_dict()
    edge = initial.find_calls(callee_name='relay')[0]
    expanded = analyzer.expand(initial, edge.id)
    call = generate(expanded, 'relay')
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    assert call.analysis_contexts[0]['class_method_bindings'] == call.class_method_bindings
    assert initial.to_dict() == snapshot


@pytest.mark.parametrize('entry', ['indirect', 'global_write', 'deleted', 'hook', 'code_write',
                                  'global_code_write'])
def test_visible_indirect_or_cross_file_class_changes_do_not_become_source_bound(entry):
    call = generate(analyze(entry))
    assert not any(fact['status'] == 'source_bound' for fact in call.class_method_bindings)


def test_import_alias_of_builtin_attribute_mutator_is_a_visible_cross_file_hazard():
    call = generate(analyze('builtin_alias_write'))
    assert not any(fact['status'] == 'source_bound' for fact in call.class_method_bindings)
    assert any(item['reason'] == 'visible_dynamic_attribute_write'
               for fact in call.class_method_bindings for item in fact['issues'])


def test_conditional_alias_writer_does_not_drop_the_other_source_class():
    call = generate(analyze('branch_write'))
    assert not any(fact['status'] == 'source_bound' for fact in call.class_method_bindings)
    assert any(item['reason'] == 'visible_method_write'
               and item['reachability'] == 'not_proven'
               for fact in call.class_method_bindings for item in fact['issues'])


def test_enclosing_function_can_shadow_builtin_descriptor():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='targets', qualname='nested'))
    assert not any(fact['status'] == 'source_bound'
                   for fact in generate(result).class_method_bindings)


def test_merged_call_does_not_promote_factory_context_using_other_contexts_proof():
    result = analyze('merged_contexts')
    call = generate(result, 'selected')
    assert call.target is None and call.target_status == 'receiver_unresolved'
    assert len(call.class_method_bindings) == 1
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    assert call.class_method_bindings[0]['conditions'][0]['branch'] is True
    contexts = call.analysis_contexts
    assert len(contexts) == 2
    assert sorted(len(context['class_method_bindings']) for context in contexts) == [0, 1]
    assert any(context['target'] is None and not context['class_method_bindings']
               for context in contexts)
    assert len({context['incoming_call_id'] for context in contexts}) == 2
    assert any(boundary.get('call_id') == call.id and boundary['reason'] == 'receiver_unresolved'
               for boundary in result.boundaries)


@pytest.mark.parametrize('visible_write', [False, True])
def test_large_unrelated_source_does_not_hide_a_later_visible_write(tmp_path, visible_write):
    noise = tmp_path / 'a_noise.py'
    noise.write_text('noise = (' + '0,' * 110000 + ')\n', encoding='utf-8')
    selected = sorted(ROOT.glob('*.py')) + [noise]
    if visible_write:
        writer = tmp_path / 'z_writer.py'
        writer.write_text('from targets import Backend\nBackend.generate = unknown_callable\n',
                          encoding='utf-8')
        selected.append(writer)
    analyzer = FlowAnalyzer(source_files=selected, import_roots=[ROOT, tmp_path])
    call = generate(analyze('direct', analyzer))
    if visible_write:
        order = list(analyzer.module_bodies)
        assert order.index('a_noise') < order.index('z_writer')
    writes, truncated = analyzer._class_binding_writes()
    assert not truncated
    fact = call.class_method_bindings[0]
    assert fact['runtime_target_confirmed'] is False
    assert fact['status'] == ('unconfirmed' if visible_write else 'source_bound')
    if visible_write:
        assert any(item['reason'] == 'visible_method_write' and item.get('evidence')
                   for item in fact['issues'])
        assert any(ref.qualname == 'Backend' and attribute == 'generate'
                   for ref, attribute, _, _, _ in writes)


def test_scan_budget_exhaustion_stays_unconfirmed_and_query_cache_resets(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    with monkeypatch.context() as patch:
        patch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 1)
        result = analyze('direct', analyzer)
        call = generate(result)
        assert call.class_method_bindings[0]['status'] == 'unconfirmed'
        assert analyzer._class_binding_writes()[1]
        assert any(item['reason'] == 'class_binding_budget'
                   for item in call.class_method_bindings[0]['issues'])
        assert any(boundary['reason'] == 'class_method_binding_unconfirmed'
                   and boundary.get('call_id') == call.id for boundary in result.boundaries)
    assert generate(analyze('direct', analyzer)).class_method_bindings[0]['status'] == 'source_bound'
