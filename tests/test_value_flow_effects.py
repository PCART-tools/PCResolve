from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix'


def run(group, entry):
    return FlowAnalyzer(project_root=ROOT / group).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_resolved_clear_removes_caller_container_content():
    result = run('containers', 'cross_call_clear')
    assert not result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='clear_values')[0]
    assert any(effect['kind'] == 'container_clear' for effect in call.effects)
    effect = next(effect for effect in call.effects
                  if effect['kind'] == 'container_clear')
    assert Path(effect['evidence'][0]['file_path']).name == 'helpers.py'


def test_nonlocal_write_updates_the_enclosing_binding():
    result = run('control', 'nonlocal_write')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
    call = result.find_calls(callee_name='replace')[0]
    assert any(effect['kind'] == 'nonlocal_write'
               and effect['target'] == 'value' for effect in call.effects)
