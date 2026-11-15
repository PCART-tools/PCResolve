## @package tests.test_call_expression_state_contract
#  The call transfer pipeline has an explicit, ordered internal state contract.

import ast
from dataclasses import fields, is_dataclass
from pathlib import Path

import pcresolve.flow.transfer.call_expression as call_expression


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
    state_type = call_expression._CallExpressionState
    assert is_dataclass(state_type)

    state_fields = {item.name for item in fields(state_type)}
    module_path = Path(call_expression.__file__)
    tree = ast.parse(module_path.read_text(encoding='utf-8'))
    phase_methods = {
        node.name: node for node in ast.walk(tree)
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
    source = Path(call_expression.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    method = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef) and node.name == 'call_expression')
    invoked = [node.func.attr for node in ast.walk(method)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr in EXPECTED_PHASES]
    assert invoked == list(EXPECTED_PHASES)
    assert 'SimpleNamespace' not in source
