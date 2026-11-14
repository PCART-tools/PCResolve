## @package tests.test_value_flow_membership_order

import ast
from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow.analyzer as flow

ROOT = Path(__file__).parent / 'fixtures/value_flow_membership_order'


@pytest.mark.parametrize('name', ['Factory', 'NotFactory', 'BoolFactory'])
def test_membership_fallback_does_not_reevaluate_a_stateful_operand(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = next(c for c in result.calls if c.callee_name == 'cls.mapping')
    assert call.target.qualname == 'Factory.mapping'
    assert len(call.class_method_bindings) == 1
    assert call.class_method_bindings[0]['status'] == 'source_bound'


@pytest.mark.parametrize('name', ['once', 'not_once'])
def test_operand_evaluation_matches_python_once_in_left_to_right_order(name, monkeypatch):
    trace = []
    original = flow._Summary.expression

    def record(summary, node, env):
        if summary.ref.qualname == name and isinstance(node, ast.Call):
            trace.append(ast.unparse(node.func))
        return original(summary, node, env)

    monkeypatch.setattr(flow._Summary, 'expression', record)
    FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    runtime = []
    values[name](lambda: runtime.append('left') or 1,
                 lambda: runtime.append('right') or {1: True})
    assert trace == runtime == ['left', 'right']


def test_left_operand_effects_still_precede_right_operand_lookup():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'KeyFactory'))
    call = next(c for c in result.calls if c.callee_name == 'cls.mapping')
    assert not any(f['status'] == 'source_bound' for f in call.class_method_bindings)


@pytest.mark.parametrize('name', ['Factory', 'NotFactory', 'BoolFactory'])
def test_membership_call_witness_has_a_runtime_fixed_signature_counterexample(name):
    values = runpy.run_path(str(ROOT / 'cases.py'))
    with pytest.raises(TypeError, match='unexpected keyword argument'):
        values[name](old=1)
