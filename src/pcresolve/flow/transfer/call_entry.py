## @package pcresolve.flow.transfer.call_entry
#  Explicit call admission and ordered transfer orchestration.

from dataclasses import asdict
from collections import namedtuple

from pcresolve.flow.transfer._summary_support import _call_span
from pcresolve.flow.transfer.call_admission import apply_summary_admission, decide_call_admission
from pcresolve.flow.transfer.call_expression_state import _CallExpressionState


CalleeResolution = namedtuple('CalleeResolution', (
    'function_names', 'nominal_target', 'allocation_values', 'global_declarations', 'global_rebound'))
ReceiverDispatchResult = namedtuple('ReceiverDispatchResult', (
    'current_descriptor', 'allocation_values', 'field_evidence'))
CallDecorationResult = namedtuple('CallDecorationResult', (
    'identity_decorator', 'wrapper_forwarding_candidate', 'decorated_target_candidate',
    'body_preserved', 'decoration_facts'))
CallableBindingResult = namedtuple(
    'CallableBindingResult', ('fresh_instance_method_bindings', 'callable_instance_cause', 'decoration'))


class CallEntryMixin:
    ## Execute one call through the ordered transfer stages.
    def call_expression(self, node,
                        env):
        location = _call_span(node)
        already_evaluated = location in self.evaluated_calls
        in_class_return = bool(not already_evaluated and self.analyzer._class_return_stack)
        admission = decide_call_admission(
            already_evaluated=already_evaluated, in_class_return=in_class_return,
            class_remaining=self.analyzer._fact_calls if in_class_return else 0,
            summary_remaining=self.remaining)
        if admission.charge_class:
            self.analyzer._fact_calls -= 1
        if admission.boundary is not None:
            self.result.boundaries.append({'function': asdict(self.ref),
                'reason': admission.boundary, 'evidence': self.evidence(node)})
            return []
        self.remaining = apply_summary_admission(
            admission, self.remaining, self.evaluated_calls, location)
        state = _CallExpressionState(node=node, env=env)
        callee = self._resolve_callee_and_construction(state)
        receiver = self._resolve_receiver_dispatch(state, callee)
        callable_binding = self._resolve_callable_binding(state)
        constructor_values = self._create_flow_call_record(
            state, callable_binding.fresh_instance_method_bindings,
            callee.nominal_target, callable_binding.decoration,
            callee.global_declarations, callee.global_rebound)
        literal_join = self._complete_call_target_metadata(
            state, receiver.current_descriptor,
            callable_binding.callable_instance_cause, callable_binding.decoration,
            receiver.field_evidence)
        binding = self._bind_call_parameters(state)
        arguments = self._map_call_arguments(state, binding, literal_join)
        effects = self._analyze_call_effects(state, binding, arguments, constructor_values)
        resolved = self._resolve_container_and_protocol_results(state, effects)
        if resolved is not None:
            return resolved
        return self._resolve_return_sources(state, effects, receiver.allocation_values)
