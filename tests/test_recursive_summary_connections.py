import ast
from types import SimpleNamespace

import pytest

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef
from pcresolve.flow.transfer.summary_values import ValuesMixin
from pcresolve.flow.transfer.summary_context_managers import ContextManagersMixin


class Child:
    def __init__(self, result, remaining=3, fail=False):
        self.result = result
        self.remaining = remaining
        self.fail = fail
        self.calls = []
        self.mapping_effects = []
        self.conditions = []
        self.context_cleanup_order = []
        self.context_execution = False

    def expression(self, node, env):
        env['$heap:child'] = ['heap fact']
        env['local'] = ['not exported']
        self.result.boundaries.append({'reason': 'expression boundary'})
        return [{'kind': 'literal', 'value': 9}]

    def block(self, statements, env):
        self.calls.append(SimpleNamespace(id='child', target_status='local_container_protocol',
                                          effects=[{'kind': 'call effect'}]))
        self.mapping_effects.append({'kind': 'mapping effect'})
        self.result.boundaries.append({'reason': 'builtin_boundary', 'call_id': 'child'})
        if self.fail:
            raise RuntimeError('child failed')
        return [('return', {'$heap:result': ['updated']}, ['returned'], False)]


class ValuesHost(ValuesMixin):
    def __init__(self):
        assignment = ast.parse("dispatch = {'k': target}").body[0]
        self.ref = FunctionRef(module='sample', file_path='sample.py')
        self.node = assignment
        self.analyzer = SimpleNamespace(module_bodies={'sample': [('sample.py', [assignment])]},
                                        import_binding_facts={'sample': [{'dispatch': [assignment]}]})
        self.result = FlowAnalysis(self.ref, {}, boundaries=[{'reason': 'prior'}])
        self.remaining = 7

    def _make_child_summary(self, result, ref, node, remaining, *args):
        assert result is self.result and remaining == 7
        return Child(result)

    def marked(self, values, assignment):
        return values


def test_module_dispatch_propagates_child_values_heap_boundary_and_budget():
    parent = ValuesHost()
    env = {'existing': ['prior']}
    result = parent.module_dispatch('dispatch', env)
    assert result == [{'kind': 'literal', 'value': 9}]
    assert env == {'existing': ['prior'], '$heap:child': ['heap fact']}
    assert parent.result.boundaries == [{'reason': 'prior'}, {'reason': 'expression boundary'}]
    assert parent.remaining == 3


class ExitHost(ContextManagersMixin):
    def __init__(self, child_budget=3, fail=False):
        self.ref = FunctionRef(module='sample', file_path='sample.py')
        self.result = FlowAnalysis(self.ref, {}, boundaries=[{'reason': 'prior'}])
        self.remaining = 7
        self.conditions = [{'branch': 'parent'}]
        self.context_cleanup_order = [4]
        self.calls = ['prior call']
        self.mapping_effects = [{'kind': 'prior effect'}]
        self.child_budget = child_budget
        self.fail = fail
        self.analyzer = SimpleNamespace(_context_exit_stack=['prior frame'], _analysis_budget=None,
                                        _fact_calls=1000, _fact_functions=20,
                                        _captures=lambda ref, node: [],
                                        _scope_facts=lambda node: SimpleNamespace(bound=set(), nonlocals=set()))

    def _make_child_summary(self, result, ref, node, remaining, *args):
        assert remaining == self.remaining
        self.child = Child(result, self.child_budget, self.fail)
        return self.child


def exit_call():
    ref = FunctionRef(module='sample', qualname='exit', file_path='sample.py')
    method = ast.parse('def exit():\n    pass\n').body[0]
    call = FlowCall(id='exit', caller=ref, callee_name='exit', lineno=1, col_offset=0,
                    binding_status='complete')
    return ref, method, call


@pytest.mark.parametrize(('child_budget', 'expected'), [(3, 3), (11, 7)])
def test_context_exit_merges_child_results_and_caps_budget(child_budget, expected):
    parent = ExitHost(child_budget)
    ref, method, call = exit_call()
    outcomes, issues = parent.execute_context_exit((ref, method), call, {'$heap:prior': ['old']})
    assert issues == []
    assert outcomes == [('return', {'$heap:prior': ['old'], '$heap:result': ['updated']},
                         ['returned'], False)]
    assert parent.remaining == expected
    assert parent.calls[0] == 'prior call' and [x.id for x in parent.calls[1:]] == ['child']
    assert parent.mapping_effects == [{'kind': 'prior effect'}, {'kind': 'mapping effect'}]
    assert parent.result.boundaries == [{'reason': 'prior'}, {'reason': 'builtin_boundary', 'call_id': 'child'}]
    assert [effect['kind'] for effect in call.effects] == ['call effect', 'mapping effect']
    assert parent.analyzer._context_exit_stack == ['prior frame']
    assert parent.child.conditions == parent.conditions and parent.child.conditions is not parent.conditions
    assert parent.child.context_cleanup_order is parent.context_cleanup_order


def test_context_exit_discards_partial_child_results_after_exception():
    parent = ExitHost(fail=True)
    ref, method, call = exit_call()
    with pytest.raises(RuntimeError, match='child failed'):
        parent.execute_context_exit((ref, method), call, {})
    assert parent.remaining == 7
    assert parent.calls == ['prior call']
    assert parent.mapping_effects == [{'kind': 'prior effect'}]
    assert parent.result.boundaries == [{'reason': 'prior'}]
    assert parent.analyzer._context_exit_stack == ['prior frame']
    parent.fail = False
    outcomes, issues = parent.execute_context_exit((ref, method), call, {})
    assert not issues and outcomes[0][0] == 'return'
    assert [x.id for x in parent.calls[1:]] == ['child']
    assert len(parent.mapping_effects) == len(parent.result.boundaries) == 2
