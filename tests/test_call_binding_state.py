import ast
from types import SimpleNamespace

import pytest

from pcresolve.flow.transfer.call_binding_state import CallArgumentsBinding, CallArgumentValues, has_invalid_binding, record_actual_values, record_argument_binding, record_protocol_values, record_syntax_binding, unbound_default_arguments
from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef
from pcresolve.flow.transfer.call_expression import CallExpressionMixin
from pcresolve.flow.transfer.summary_call_evidence import CallEvidenceMixin


@pytest.mark.parametrize(('signature', 'records', 'invalid'), [
    (True, [], False),
    (False, [], False),
    (False, [{'status': 'unresolved', 'binding_kind': 'explicit'}], False),
    (True, [{'status': 'unresolved', 'binding_kind': 'explicit'}], True),
    (True, [{'status': 'unresolved', 'binding_kind': 'starred'}], True),
    (True, [{'status': 'unresolved', 'binding_kind': 'expanded_keyword'}], True),
    (True, [{'status': 'unresolved', 'binding_kind': 'dynamic_starred'}], False),
    (False, [{'status': 'missing', 'binding_kind': 'required'}], True),
    (True, [{'status': 'duplicate', 'binding_kind': 'explicit'}], True),
    (True, [{'status': 'exact', 'binding_kind': 'explicit'}], False),
])
def test_binding_rejection_requires_proven_invalidity(signature, records, invalid):
    assert has_invalid_binding(signature, records) is invalid


@pytest.mark.parametrize(('path', 'kind', 'destination', 'expected'), [
    ([], 'explicit', None, {'destination_kind': 'unresolved'}),
    ([0, 'name'], 'starred', 'parameter', {'destination_kind': 'parameter',
                                             'target_path': [0, 'name'], 'binding_kind': 'starred'}),
])
def test_publish_argument_binding_preserves_optional_fields(path, kind, destination, expected):
    call = SimpleNamespace(parameter_bindings=[])
    record = {'argument': {'position': 0}, 'node': None, 'parameter': 'value',
              'target_path': path, 'status': 'exact', 'binding_kind': kind}
    if destination is not None:
        record['destination_kind'] = destination
    record_argument_binding(call, record)
    assert call.parameter_bindings == [{**{'argument': {'position': 0}, 'parameter': 'value',
                                          'status': 'exact'}, **expected}]


def test_argument_value_writes_preserve_order_unknown_parameter_and_original_protocol_values():
    arguments = CallArgumentValues()
    record = {'argument': {'position': 0}, 'node': None, 'parameter': None,
              'target_path': [], 'status': 'unresolved', 'binding_kind': 'dynamic_starred'}
    original = [{'source': 'a'}]
    record_protocol_values(arguments, record, original)
    record_actual_values(arguments, record, [{'source': 'a', 'value_incomplete': True}])
    record_actual_values(arguments, record, [{'source': 'a', 'value_incomplete': True}, {'source': 'b'}])
    assert arguments.protocol_values[0] is original
    assert arguments.actual_values[None] == [{'source': 'a', 'value_incomplete': True}, {'source': 'b'}]
    with pytest.raises(TypeError, match='position must be an integer'):
        record_protocol_values(arguments, dict(record, argument={'position': 'invalid'}), original)
    assert arguments.protocol_values == {0: original}


@pytest.mark.parametrize(('expression', 'supplied', 'expected'), [
    ('target()', [], ['first', 'second', 'named']),
    ('target(1)', ['first'], ['second', 'named']),
    ('target(*args)', [], ['named']),
    ('target(**kwargs)', [], []),
    ('target(*(1,))', ['first'], ['second', 'named']),
    ("target(**{'named': 9})", ['named'], ['first', 'second']),
])
def test_default_binding_selection_keeps_dynamic_expansion_conservative(expression, supplied, expected):
    params = ast.parse('def target(first=1, second=2, *, named=3): pass').body[0].args
    node = ast.parse(expression).body[0].value
    binding = CallArgumentsBinding(params, params.posonlyargs + params.args, [], None, False)
    call = SimpleNamespace(parameter_bindings=[{'parameter': name, 'status': 'exact'} for name in supplied])
    assert [arg.arg for arg, _ in unbound_default_arguments(node, binding, call.parameter_bindings)] == expected


@pytest.mark.parametrize(('source', 'records', 'expected'), [
    ('target()', [{'status': 'missing'}], True),
    ('target(value)', [{'status': 'unresolved', 'binding_kind': 'explicit'}], True),
    ('target(*args)', [{'status': 'unresolved', 'binding_kind': 'dynamic_starred'}], False),
    ('target(value)', [{'status': 'exact', 'binding_kind': 'explicit'}], False),
    ('target()', [], False),
])
def test_real_binding_phase_uses_binding_records(source, records, expected):
    target = ast.parse('def target(value): pass').body[0]
    node = ast.parse(source).body[0].value
    calls = []

    def bind(call_node, params, positional, call):
        calls.append((call_node, params, positional, call))
        return records

    host = SimpleNamespace(bind_call_arguments=bind, analyzer=SimpleNamespace(return_summaries={}))
    call = SimpleNamespace(binding_status='complete')
    state = SimpleNamespace(self=host, node=node, target=(object(), target),
                            canonical='module.target', bound_receiver=False, call=call)
    result = CallExpressionMixin._bind_call_parameters(host, state)
    assert calls == [(node, target.args, target.args.args, call)]
    assert result.params is target.args
    assert result.positional == target.args.args
    assert result.records is records
    assert result.invalid is expected
    assert not hasattr(state, 'actual_values')
    assert not hasattr(state, 'capture_values')


def test_real_binding_phase_preserves_unavailable_signature():
    node = ast.parse('external(*args)').body[0].value
    host = SimpleNamespace(analyzer=SimpleNamespace(return_summaries={}))
    call = SimpleNamespace(binding_status='complete')
    state = SimpleNamespace(self=host, node=node, target=None, name='external',
                            builtin_status=None, canonical='module.external',
                            bound_receiver=False, call=call)
    result = CallExpressionMixin._bind_call_parameters(host, state)
    assert call.binding_status == 'unavailable'
    assert result.invalid is False
    assert result.params is None and result.positional == []
    assert result.records[0]['binding_kind'] == 'dynamic_starred'


def test_unavailable_signature_preserves_each_argument_and_order():
    node = ast.parse('external(first, *items, named=value, **options)').body[0].value
    host = SimpleNamespace(analyzer=SimpleNamespace(return_summaries={}))
    call = SimpleNamespace(binding_status='complete')
    state = SimpleNamespace(node=node, target=None, name='external', builtin_status=None,
                            canonical='module.external', bound_receiver=False, call=call)
    binding = CallExpressionMixin._bind_call_parameters(host, state)
    assert call.binding_status == 'unavailable'
    assert not binding.invalid
    assert [record['argument'] for record in binding.records] == [
        {'position': 0}, {'position': 1}, {'keyword': 'named'}, {'keyword': None}]
    assert [record['node'] for record in binding.records] == [
        node.args[0], node.args[1].value, node.keywords[0].value, node.keywords[1].value]
    assert [record['binding_kind'] for record in binding.records] == [
        'explicit', 'dynamic_starred', 'explicit', 'explicit']
    assert all(record['status'] == 'unresolved' and record['parameter'] is None
               for record in binding.records)


def test_bound_instance_parameter_is_explicit_binding_result():
    method = ast.parse('def method(self, value): pass').body[0]
    node = ast.parse('obj.method(1)').body[0].value
    calls = []
    def bind(call_node, params, positional, call):
        calls.append((call_node, params, positional, call))
        return []
    host = SimpleNamespace(bind_call_arguments=bind, analyzer=SimpleNamespace(return_summaries={}))
    call = SimpleNamespace(binding_status='complete', argument_sources=[], parameter_bindings=[])
    receiver = [{'instance_type': {'module': 'm', 'qualname': 'C'}}]
    state = SimpleNamespace(node=node, target=(object(), method), canonical='m.C.method',
                            bound_receiver=True, dispatch_kind='instance_method',
                            descriptor_kind=None, receiver_sources=receiver, call=call)
    result = CallExpressionMixin._bind_call_parameters(host, state)
    assert result.instance_parameter == 'self'
    assert [arg.arg for arg in result.positional] == ['value']
    assert calls == [(node, method.args, result.positional, call)]
    assert call.parameter_bindings == [{'argument': {'receiver': True}, 'parameter': 'self',
        'status': 'exact', 'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'}]
    assert not hasattr(state, 'instance_parameter')


@pytest.mark.parametrize(('expression', 'status', 'invalid'), [
    ('target()', 'invalid', True),
    ('target(1)', 'complete', False),
    ('target(1, value=2)', 'invalid', True),
    ('target(*args)', 'uncertain', False),
    ('target(**kwargs)', 'uncertain', False),
])
def test_real_syntax_binder_and_binding_phase_agree(expression, status, invalid):
    class Host(CallEvidenceMixin, CallExpressionMixin):
        def __init__(self):
            self.analyzer = SimpleNamespace(return_summaries={})
            self.result = SimpleNamespace(boundaries=[])

    host = Host()
    target = ast.parse('def target(value): pass').body[0]
    node = ast.parse(expression).body[0].value
    call = SimpleNamespace(id='call', binding_status='complete', binding_issues=[])
    state = SimpleNamespace(self=host, node=node, target=(object(), target),
                            canonical='module.target', bound_receiver=False, call=call)
    binding = host._bind_call_parameters(state)
    assert binding.invalid is invalid
    assert call.binding_status == status
    assert binding.records
    assert all(isinstance(record['status'], str) and isinstance(record['binding_kind'], str)
               for record in binding.records)


def test_record_binding_preserves_existing_evidence_and_deduplicates_issues():
    ref = FunctionRef(module='module', qualname='entry')
    result = FlowAnalysis(ref, {}, boundaries=[{'reason': 'prior'}])
    call = FlowCall('call', ref, 'target', 1, 0,
                    binding_issues=[{'kind': 'dynamic_expansion'}, {'kind': 'prior'}])
    signature = FunctionSignature.from_ast(ast.parse('def target(value): pass').body[0].args)
    records, reasons = bind_ast_call(ast.parse('target(*values)').body[0].value, signature)
    record_syntax_binding(result, call, records, reasons)
    assert call.binding_issues == [{'kind': 'dynamic_expansion'}, {'kind': 'prior'}]
    assert call.binding_status == 'uncertain'
    assert result.boundaries == [{'reason': 'prior'},
                                 {'call_id': 'call', 'reason': 'dynamic_argument_expansion'}]
