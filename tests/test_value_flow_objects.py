import json
from pathlib import Path
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name, depth=2):
    return FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='objects', qualname=name), max_depth=depth)


def test_constructor_field_candidate():
    result = run('Owner.run')
    assert result.calls[0].target.qualname == 'Mapper.resolve'
    assert result.calls[0].parameter_bindings[0]['parameter'] == 'name'
    assert result.trace_parameter('name')['return_paths']
    assert any(b['reason'] == 'constructor_field_assumption' for b in result.boundaries)


def test_conflicting_field_write_rejects_candidate():
    assert run('Changed.run').calls[0].target is None


def test_alias_append_reaches_container_return():
    result = run('appended')
    assert result.trace_parameter('x')['return_paths']
    assert result.calls[0].mutation_flows
    assert result.calls[0].parameter_flows[0]['target_parameter'] == 'object'
    assert not run('appended_return').trace_parameter('x')['return_paths']


def test_clear_removes_content_dependency():
    assert not run('cleared').trace_parameter('x')['return_paths']


def test_dict_get_and_index_select_only_matching_element():
    result = run('dictionary')
    get_call = result.find_calls(callee_name='values.get')[0]
    assert get_call.return_flows
    assert get_call.parameter_bindings[0]['parameter'] == 'key'
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']
    result = run('local_selection')
    assert result.trace_parameter('y')['return_paths']
    assert not result.trace_parameter('x')['return_paths']


def test_cross_call_return_projection_does_not_mix_tuple_elements():
    result = run('second')
    assert result.trace_parameter('y')['return_paths']
    assert not result.trace_parameter('x')['return_paths']


def test_boundary_records_are_unique():
    root = Path(__file__).resolve().parents[1] / 'src'
    result = FlowAnalyzer(project_root=root).analyze(FunctionRef(
        module='pcresolve.cross_file', qualname='ProjectAnalyzer.trace_symbol'))
    records = [json.dumps(b, sort_keys=True) for b in result.boundaries]
    assert len(records) == len(set(records))
    assert all(b['reason'] != 'python_protocol' for b in result.boundaries)
    mapper_calls = result.find_calls(callee_name='self.module_mapper.resolve_module_name')
    assert mapper_calls
    assert all(c.target and c.target.qualname == 'ModuleMapper.resolve_module_name'
               for c in mapper_calls)
    assert result.find_calls(callee_name='tops.append')[0].mutation_flows


def test_known_dict_key_excludes_default():
    result = run('known_default')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']


def test_string_join_consumes_container_contents():
    assert run('joined').trace_parameter('x')['return_paths']


def test_short_circuit_refines_only_following_operand():
    result = run('short_circuit')
    assert result.find_calls(callee_name='x.startswith')[0].target_status == 'python_protocol'


def test_return_projection_survives_intermediate_function():
    result = run('indirect_second', depth=3)
    assert result.trace_parameter('y')['return_paths']
    assert not result.trace_parameter('x')['return_paths']


def test_ambiguous_clear_is_weak_update():
    assert run('conditional_clear').trace_parameter('x')['return_paths']


def test_mapping_overwrite_and_duplicate_keys():
    for name in ('dict_write', 'duplicate_key'):
        result = run(name)
        assert result.trace_parameter('y')['return_paths']
        assert not result.trace_parameter('x')['return_paths']


def test_branch_clear_retains_possible_default():
    result = run('branch_default')
    assert result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
def test_conditional_expression_effects_merge_possible_paths():
    assert run('conditional_append').trace_parameter('x')['return_paths']
    assert run('conditional_expression_clear').trace_parameter('x')['return_paths']
    assert not run('unconditional_short_circuit_clear').trace_parameter('x')['return_paths']
def test_finally_mutates_returned_object_without_rebinding_return():
    assert run('finally_append').trace_parameter('x')['return_paths']
    assert not run('finally_clear').trace_parameter('x')['return_paths']
    result = run('finally_rebind')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']
def test_repeated_call_merges_protocol_return_dependencies():
    result = run('loop_default')
    assert result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
