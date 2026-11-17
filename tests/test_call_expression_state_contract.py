## @package tests.test_call_expression_state_contract
#  The call transfer pipeline has an explicit, ordered internal state contract.

import ast
from types import SimpleNamespace
from pathlib import Path

import pytest

import pcresolve.flow.transfer.call_expression as call_expression
import pcresolve.flow.transfer.call_expression_state as call_expression_state
import pcresolve.flow.transfer.call_entry as call_entry
from pcresolve.flow.analyzer import FlowAnalyzer
from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.transfer.call_binding_state import CallArgumentsBinding, CallArgumentValues, CallEffectsResult


EXPECTED_PHASES = (
    '_resolve_callee_and_construction',
    '_resolve_receiver_dispatch',
    '_resolve_callable_binding',
    '_create_flow_call_record',
    '_complete_call_target_metadata',
    '_bind_call_parameters',
    '_map_call_arguments',
    '_analyze_call_effects',
    '_resolve_container_and_protocol_results',
    '_resolve_return_sources',
)


def test_call_expression_state_declares_all_phase_fields():
    state_type = call_expression_state._CallExpressionState
    state_fields = set(state_type.__slots__)
    assert 'self' not in state_fields
    assert 'location' not in state_fields
    assert 'container_result' not in state_fields
    assert not {'constructor_values', 'literal_join'} & state_fields
    assert 'function_names' not in state_fields
    assert 'current_descriptor' not in state_fields
    assert 'fresh_instance_method_bindings' not in state_fields
    assert 'allocation_values' not in state_fields
    assert 'nominal_target' not in state_fields
    assert 'callable_instance_cause' not in state_fields
    assert not {'field_evidence', 'global_declarations', 'global_rebound'} & state_fields
    assert 'effective_name' not in state_fields
    assert not {'body_preserved', 'decorated_target_candidate', 'decoration_facts',
                'identity_decorator', 'wrapper_forwarding_candidate'} & state_fields
    assert not {'effects_complete', 'selected_target', 'capture_values'} & state_fields
    assert not {'actual_values', 'protocol_values'} & state_fields
    assert not {'params', 'positional', 'records', 'instance_parameter', 'invalid_binding'} & state_fields
    transfer_tree = ast.parse(Path(call_expression.__file__).read_text(encoding='utf-8'))
    phase_methods = {
        node.name: node for node in ast.walk(transfer_tree)
        if isinstance(node, ast.FunctionDef) and node.name in EXPECTED_PHASES
    }

    assert set(EXPECTED_PHASES) <= phase_methods.keys()
    used_fields = {
        node.attr for phase in phase_methods.values() for node in ast.walk(phase)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name) and node.value.id == 'state'
    }
    assert used_fields <= state_fields


def test_call_expression_runs_phases_in_the_existing_order():
    source = Path(call_entry.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    method = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef) and node.name == 'call_expression')
    invoked = [node.func.attr for node in ast.walk(method)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr in EXPECTED_PHASES]
    assert invoked == list(EXPECTED_PHASES)
    assert 'SimpleNamespace' not in source


def test_literal_string_join_result_is_passed_to_argument_mapping(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def entry(values):\n'
        "    return ','.join(values)\n", encoding='utf-8')
    observed = []
    original = call_expression.CallExpressionMixin._map_call_arguments

    def record(self, state, binding, literal_join):
        if self.ref.qualname == 'entry' and state.name == "','.join":
            observed.append(literal_join)
        return original(self, state, binding, literal_join)

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_map_call_arguments', record)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)

    calls = result.find_calls(callee_name="','.join")
    assert len(calls) == 1
    assert observed == [True]
    assert calls[0].target_status == 'python_protocol'
    assert calls[0].parameter_bindings[0]['parameter'] == 'iterable'


def test_call_expression_distinguishes_empty_result_from_unresolved():
    class Host(call_expression.CallExpressionMixin):
        def __init__(self, container_result):
            self.evaluated_calls = set()
            self.analyzer = SimpleNamespace(_class_return_stack=[])
            self.remaining = 2
            self.container_result = container_result
            self.invoked = []

        def _resolve_container_and_protocol_results(self, state, effects):
            self.invoked.append('container')
            assert effects.container_result is self.container_result
            return self.container_result

        def _resolve_return_sources(self, state, effects, allocation_values):
            self.invoked.append('return')
            assert effects.container_result is self.container_result
            return [{'kind': 'fallback'}]

    def phase(self, state, *args):
        self.invoked.append('phase')

    def resolve_callee(self, state):
        self.invoked.append('phase')
        return call_entry.CalleeResolution([], None, [], [], False)
    def resolve_receiver(self, state, callee):
        self.invoked.append('phase')
        return call_entry.ReceiverDispatchResult(None, callee.allocation_values, None)
    Host._resolve_callee_and_construction = resolve_callee
    Host._resolve_receiver_dispatch = resolve_receiver
    def resolve_callable(self, state):
        self.invoked.append('phase')
        return call_entry.CallableBindingResult([], None, call_entry.CallDecorationResult(
            None, False, False, False, []))
    Host._resolve_callable_binding = resolve_callable
    Host._create_flow_call_record = phase
    Host._complete_call_target_metadata = phase
    def bind(self, state):
        self.invoked.append('phase')
        return CallArgumentsBinding(None, [], [], None, False)
    def map_arguments(self, state, binding, literal_join):
        self.invoked.append('phase')
        assert isinstance(binding, CallArgumentsBinding)
        return CallArgumentValues()
    Host._bind_call_parameters = bind
    Host._map_call_arguments = map_arguments
    def effects(self, state, binding, arguments, constructor_values):
        self.invoked.append('phase')
        assert isinstance(binding, CallArgumentsBinding)
        return CallEffectsResult(binding.invalid, self.container_result, False, None, {}, arguments, None)
    Host._analyze_call_effects = effects
    node = ast.parse('f()').body[0].value
    empty = Host([])
    assert empty.call_expression(node, {}) == []
    assert empty.invoked == ['phase'] * 8 + ['container']
    unresolved = Host(None)
    assert unresolved.call_expression(node, {}) == [{'kind': 'fallback'}]
    assert unresolved.invoked == ['phase'] * 8 + ['container', 'return']


def test_unmodeled_nonlocal_write_name_overwrite_observed_without_output_change(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def entry():\n'
        '    value = {}\n'
        '    def writer():\n'
        '        nonlocal value\n'
        '        value = []\n'
        '    writer()\n'
        '    return value\n', encoding='utf-8')

    def analyze():
        return FlowAnalyzer(project_root=str(tmp_path)).analyze(
            FunctionRef(module='sample', qualname='entry'), max_depth=3).to_dict()

    baseline = analyze()
    original = call_expression.CallExpressionMixin._analyze_call_effects
    observed = []

    def restore_name(self, state, binding, arguments, constructor_values):
        name = state.name
        result = original(self, state, binding, arguments, constructor_values)
        if result.effective_name != name:
            observed.append((name, result.effective_name, state.builtin_status))
        assert not hasattr(state, 'effective_name')
        return result

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_analyze_call_effects', restore_name)
    assert analyze() == baseline
    assert ('writer', 'value', None) in observed
    assert any(boundary['reason'] == 'capture_binding_write_unmodeled'
               for boundary in baseline['boundaries'])


def test_builtin_super_and_shadowed_super_keep_distinct_resolution(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'class Base:\n'
        '    def method(self): return 1\n'
        'class Child(Base):\n'
        '    def method(self): return super(Child, self).method()\n'
        'def shadowed():\n'
        '    value = {}\n'
        '    def super(*args):\n'
        '        nonlocal value\n'
        '        value = []\n'
        '    return super(Child, Child())\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._analyze_call_effects
    seen = []

    def observe(self, state, binding, arguments, constructor_values):
        before, builtin, target = state.name, state.builtin_status, state.target
        result = original(self, state, binding, arguments, constructor_values)
        if before == 'super':
            seen.append((builtin, target is not None, result.effective_name, state.name))
        assert not hasattr(state, 'effective_name')
        return result

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_analyze_call_effects', observe)
    analyzer = FlowAnalyzer(project_root=str(tmp_path))
    analyzer.analyze(FunctionRef(module='sample', qualname='Child.method'), max_depth=3)
    analyzer.analyze(FunctionRef(module='sample', qualname='shadowed'), max_depth=3)
    assert ('confirmed_builtin', False, 'super', 'super') in seen
    assert ('source_binding', True, 'value', 'super') in seen


def test_real_call_stages_initialize_binding_before_downstream_consumption(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def target(value):\n'
        '    return value\n'
        'def entry(value):\n'
        '    return target(value)\n', encoding='utf-8')
    events = []
    container_handoff = []
    binding_handoff = []
    arguments_handoff = []
    constructor_handoff = []
    metadata_handoff = []
    binding_fact_handoff = []
    cause_handoff = []
    decoration_handoff = []
    callee_handoff = []
    receiver_handoff = []
    required_after = {
        '_resolve_callee_and_construction': ('name', 'target', 'binding'),
        '_create_flow_call_record': ('call', 'call_id'),
    }

    def wrap(name, original):
        def observing(self, state, *args):
            selected = (self.ref.qualname == 'entry' and isinstance(state.node.func, ast.Name)
                        and state.node.func.id == 'target')
            if selected and name == '_create_flow_call_record':
                assert not hasattr(state, 'call')
                assert not hasattr(state, 'global_declarations')
                assert not hasattr(state, 'global_rebound')
            if selected and name == '_bind_call_parameters':
                assert not hasattr(state, 'records')
            output = original(self, state, *args)
            if selected:
                assert all(hasattr(state, field) for field in required_after.get(name, ()))
                assert not hasattr(state, 'constructor_values')
                assert not hasattr(state, 'literal_join')
                if name == '_resolve_callee_and_construction':
                    assert isinstance(output, call_entry.CalleeResolution)
                    assert output.global_declarations == []
                    assert output.global_rebound is False
                    callee_handoff.append(output)
                if name == '_resolve_receiver_dispatch':
                    assert isinstance(output, call_entry.ReceiverDispatchResult)
                    assert output.field_evidence is None
                    receiver_handoff.append(output)
                if name == '_create_flow_call_record':
                    assert isinstance(output, list)
                    assert len(binding_fact_handoff) == 1
                    assert args[0] is binding_fact_handoff[0]
                    assert args[2] is decoration_handoff[0]
                    assert args[4] is callee_handoff[0].global_rebound
                    constructor_handoff.append(output)
                if name == '_complete_call_target_metadata':
                    assert args[3] is receiver_handoff[0].field_evidence
                if name == '_complete_call_target_metadata':
                    assert isinstance(output, bool)
                    assert len(cause_handoff) == 1 and args[1] is cause_handoff[0]
                    assert args[2] is decoration_handoff[0]
                    metadata_handoff.append(output)
                if name == '_resolve_callable_binding':
                    assert isinstance(output, call_entry.CallableBindingResult)
                    binding_fact_handoff.append(output.fresh_instance_method_bindings)
                    cause_handoff.append(output.callable_instance_cause)
                    assert isinstance(output.decoration, call_entry.CallDecorationResult)
                    decoration_handoff.append(output.decoration)
                if name == '_analyze_call_effects':
                    assert not hasattr(state, 'container_result')
                    assert not hasattr(state, 'instance_parameter')
                    assert len(binding_handoff) == 1 and args[0] is binding_handoff[0]
                    assert len(arguments_handoff) == 1 and args[1] is arguments_handoff[0]
                    assert len(constructor_handoff) == 1 and args[2] is constructor_handoff[0]
                    assert output.arguments is arguments_handoff[0]
                    container_handoff.append(output)
                if name == '_resolve_container_and_protocol_results':
                    assert len(container_handoff) == 1
                    assert args[0] is container_handoff[0]
                if name == '_resolve_return_sources':
                    assert len(container_handoff) == 1
                    assert args[0] is container_handoff[0]
                if name == '_bind_call_parameters':
                    assert isinstance(output, CallArgumentsBinding)
                    binding_handoff.append(output)
                if name == '_map_call_arguments':
                    assert len(binding_handoff) == 1
                    assert args[0] is binding_handoff[0]
                    assert len(metadata_handoff) == 1 and args[1] is metadata_handoff[0]
                    assert isinstance(output, CallArgumentValues)
                    arguments_handoff.append(output)
                events.append((name, id(state)))
            return output
        return observing

    for name in EXPECTED_PHASES:
        method = getattr(call_expression.CallExpressionMixin, name)
        monkeypatch.setattr(call_expression.CallExpressionMixin, name, wrap(name, method))
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert [name for name, _ in events] == list(EXPECTED_PHASES)
    assert len({identity for _, identity in events}) == 1
    assert len(container_handoff) == 1
    assert len(binding_handoff) == 1
    assert len(arguments_handoff) == 1
    assert result.find_calls(callee_name='target')


def test_real_call_stages_distinguish_invalid_binding_and_unavailable_target(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def target(value):\n'
        '    return value\n'
        'def entry(value):\n'
        '    target()\n'
        '    return unknown(*value)\n', encoding='utf-8')
    original_binding = call_expression.CallExpressionMixin._bind_call_parameters
    original_completion = call_expression.CallExpressionMixin._resolve_container_and_protocol_results
    bindings = {}
    completions = {}

    def observe_binding(self, state):
        result = original_binding(self, state)
        if self.ref.qualname == 'entry':
            bindings[state.name] = (result.invalid, state.call.binding_status,
                                    tuple(record['binding_kind'] for record in result.records))
        return result

    def observe_completion(self, state, container_result):
        result = original_completion(self, state, container_result)
        if self.ref.qualname == 'entry':
            completions[state.name] = result
        return result

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_bind_call_parameters', observe_binding)
    monkeypatch.setattr(call_expression.CallExpressionMixin,
                        '_resolve_container_and_protocol_results', observe_completion)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert bindings['target'] == (True, 'invalid', ('required',))
    assert bindings['unknown'] == (False, 'unavailable', ('dynamic_starred',))
    assert completions['target'] == []
    assert completions['unknown'] is None
    assert result.find_calls(callee_name='target')
    assert result.find_calls(callee_name='unknown')


def test_instance_parameter_reaches_effects_through_real_call_entry(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'class Box:\n'
        '    def method(self, value): return value\n'
        'def entry(value):\n'
        '    box = Box()\n'
        '    return box.method(value)\n', encoding='utf-8')
    observed = []
    original = call_expression.CallExpressionMixin._analyze_call_effects

    def observe(self, state, binding, arguments, constructor_values):
        if self.ref.qualname == 'entry' and state.name == 'box.method':
            observed.append((binding.instance_parameter, hasattr(state, 'instance_parameter')))
        return original(self, state, binding, arguments, constructor_values)

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_analyze_call_effects', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='box.method')
    assert observed == [('self', False)]


@pytest.mark.parametrize('inject_previously_valid', [False, True])
def test_receiver_conflict_updates_effect_result_and_stops_result_propagation(
        tmp_path, monkeypatch, inject_previously_valid):
    (tmp_path / 'sample.py').write_text(
        'class Box:\n'
        '    def method(self, value): return value\n'
        'def entry(value):\n'
        '    box = Box()\n'
        '    return box.method(self=box, value=value)\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._analyze_call_effects
    finish = call_expression.CallExpressionMixin._resolve_container_and_protocol_results
    bind = call_expression.CallExpressionMixin._bind_call_parameters
    observed = []

    def observe(self, state, binding, arguments, constructor_values):
        result = original(self, state, binding, arguments, constructor_values)
        if self.ref.qualname == 'entry' and state.name == 'box.method':
            observed.append(('effects', binding.invalid, result.invalid_binding))
        return result

    def complete(self, state, effects):
        result = finish(self, state, effects)
        if self.ref.qualname == 'entry' and state.name == 'box.method':
            observed.append(('result', effects.invalid_binding, result))
        return result

    def bind_with_controlled_validity(self, state):
        binding = bind(self, state)
        if inject_previously_valid and self.ref.qualname == 'entry' and state.name == 'box.method':
            return binding._replace(invalid=False)
        return binding

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_analyze_call_effects', observe)
    monkeypatch.setattr(call_expression.CallExpressionMixin, '_bind_call_parameters', bind_with_controlled_validity)
    monkeypatch.setattr(call_expression.CallExpressionMixin,
                        '_resolve_container_and_protocol_results', complete)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='box.method')
    assert observed == [('effects', not inject_previously_valid, True), ('result', True, [])]


def test_effect_completeness_reaches_real_return_resolution(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def identity(value): return value\n'
        'def entry(value):\n'
        '    known = identity(value)\n'
        '    return missing(known)\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._resolve_return_sources
    observed = {}

    def observe(self, state, effects, allocation_values):
        if self.ref.qualname == 'entry':
            selected = effects.selected_target
            observed[state.name] = (effects.effects_complete,
                                    selected[0].qualname if selected is not None else None,
                                    hasattr(state, 'effects_complete'),
                                    hasattr(state, 'selected_target'))
        return original(self, state, effects, allocation_values)

    monkeypatch.setattr(call_expression.CallExpressionMixin, '_resolve_return_sources', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='identity')
    assert result.find_calls(callee_name='missing')
    assert observed == {'identity': (True, 'identity', False, False),
                        'missing': (False, None, False, False)}


def test_real_callee_candidates_have_explicit_target_shape(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'class Item:\n'
        '    def __init__(self): pass\n'
        'def identity(value): return value\n'
        'def entry(value):\n'
        '    identity(value)\n'
        '    Item()\n'
        '    return missing(value)\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._resolve_callable_binding
    observed = {}
    original_create = call_expression.CallExpressionMixin._create_flow_call_record
    def observe_create(self, state, fresh_bindings, nominal_target, decoration,
                       global_declarations, global_rebound):
        if self.ref.qualname == 'entry':
            for target in [state.target, nominal_target, *state.bounded_targets]:
                if target is not None:
                    assert isinstance(target[0], FunctionRef)
                    assert isinstance(target[1], (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            assert state.constructor_class is None or isinstance(state.constructor_class, FunctionRef)
            assert state.allocation_class is None or isinstance(state.allocation_class, FunctionRef)
            observed[state.name] = (state.target[0].qualname if state.target else None,
                                    state.constructor_class.qualname if state.constructor_class else None)
        assert isinstance(decoration, call_entry.CallDecorationResult)
        return original_create(self, state, fresh_bindings, nominal_target, decoration,
                               global_declarations, global_rebound)
    monkeypatch.setattr(call_expression.CallExpressionMixin, '_create_flow_call_record', observe_create)
    FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert observed == {'identity': ('identity', None), 'Item': ('Item.__init__', 'Item'),
                        'missing': (None, None)}


def test_effect_capture_values_reach_real_result_stage(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def entry(value):\n'
        '    def nested():\n'
        '        return value\n'
        '    return nested()\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._resolve_container_and_protocol_results
    observed = []
    def observe(self, state, effects):
        if self.ref.qualname == 'entry' and state.name == 'nested':
            observed.append((effects.capture_values, hasattr(state, 'capture_values')))
        return original(self, state, effects)
    monkeypatch.setattr(call_expression.CallExpressionMixin,
                        '_resolve_container_and_protocol_results', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='nested')
    assert len(observed) == 1 and observed[0][1] is False
    assert 'value' in observed[0][0]
    assert any(item.get('source') == 'value' for item in observed[0][0]['value'])


def test_distinct_real_calls_have_independent_argument_values(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def target(value): return value\n'
        'def entry(first, second):\n'
        '    target(first)\n'
        '    return target(second)\n', encoding='utf-8')
    original = call_expression.CallExpressionMixin._map_call_arguments
    seen = []
    def observe(self, state, binding, literal_join):
        result = original(self, state, binding, literal_join)
        if self.ref.qualname == 'entry' and state.name == 'target':
            seen.append(result)
        return result
    monkeypatch.setattr(call_expression.CallExpressionMixin, '_map_call_arguments', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert len(result.find_calls(callee_name='target')) == 2
    assert len(seen) == 2 and seen[0] is not seen[1]
    assert seen[0].actual_values is not seen[1].actual_values
    assert {value['source'] for value in seen[0].actual_values['value']} == {'first'}
    assert {value['source'] for value in seen[1].actual_values['value']} == {'second'}
    seen[0].actual_values['probe'] = []
    assert 'probe' not in seen[1].actual_values


def test_real_unknown_call_uses_typed_argument_value_writers(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def entry(value):\n'
        '    return unknown(*value)\n', encoding='utf-8')
    protocol_writer = call_expression.record_protocol_values
    actual_writer = call_expression.record_actual_values
    seen = []
    def observe_protocol(arguments, record, values):
        protocol_writer(arguments, record, values)
        seen.append(('protocol', record['parameter'], arguments.protocol_values.get(0)))
    def observe_actual(arguments, record, values):
        actual_writer(arguments, record, values)
        seen.append(('actual', record['parameter'], arguments.actual_values.get(None)))
    monkeypatch.setattr(call_expression, 'record_protocol_values', observe_protocol)
    monkeypatch.setattr(call_expression, 'record_actual_values', observe_actual)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='unknown')
    assert [item[:2] for item in seen] == [('protocol', None), ('actual', None)]
    assert all(any(value.get('source') == 'value' for value in item[2]) for item in seen)


def test_real_argument_mapping_publishes_syntax_binding_through_typed_consumer(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def target(value): return value\n'
        'def entry(value): return target(value)\n', encoding='utf-8')
    original = call_expression.record_argument_binding
    recorded = []

    def observe(call, record):
        original(call, record)
        if call.callee_name == 'target':
            recorded.append((record['parameter'], dict(call.parameter_bindings[-1])))

    monkeypatch.setattr(call_expression, 'record_argument_binding', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    assert result.find_calls(callee_name='target')
    assert recorded == [('value', {'argument': {'position': 0}, 'parameter': 'value',
                                  'status': 'exact', 'destination_kind': 'parameter'})]


def test_real_argument_mapping_selects_defaults_via_explicit_inputs(tmp_path, monkeypatch):
    (tmp_path / 'sample.py').write_text(
        'def target(first=1, *, named=2): return first\n'
        'def entry(): return target()\n', encoding='utf-8')
    original = call_expression.unbound_default_arguments
    observed = []

    def observe(node, binding, published):
        selected = original(node, binding, published)
        if isinstance(node.func, ast.Name) and node.func.id == 'target':
            observed.append([arg.arg for arg, _ in selected])
        return selected

    monkeypatch.setattr(call_expression, 'unbound_default_arguments', observe)
    result = FlowAnalyzer(project_root=str(tmp_path)).analyze(
        FunctionRef(module='sample', qualname='entry'), max_depth=2)
    target = result.find_calls(callee_name='target')[0]
    assert observed == [['first', 'named']]
    assert [(item['parameter'], item['source_text']) for item in target.parameter_bindings
            if item.get('binding_kind') == 'default'] == [('first', '1'), ('named', '2')]
