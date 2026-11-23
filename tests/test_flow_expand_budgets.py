## @package tests.test_flow_expand_budgets
#  Expansions reuse configured fact allowances and isolate branch environments.

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.transfer.environment import copy_environment


SOURCE = (
    'class Worker:\n'
    '    def __init__(self):\n'
    '        self.value = 1\n'
    '\n'
    '    def convert(self, value):\n'
    '        return value\n'
    '\n'
    '\n'
    'def entry(value):\n'
    '    worker = Worker()\n'
    '    return worker.convert(value)\n'
)


def test_copy_environment_isolates_bindings_and_value_records():
    evidence = [{'lineno': 1}]
    binding = {'kind': 'parameter', 'source': 'value', 'evidence': evidence}
    env = {'value': [binding], 'other': []}
    copied = copy_environment(env)
    copied['value'][0]['kind'] = 'literal'
    copied['value'].append({'kind': 'literal'})
    copied['other'].append({'kind': 'literal'})
    assert env['value'][0]['kind'] == 'parameter'
    assert len(env['value']) == 1
    assert env['other'] == []
    # Nested evidence is immutable by convention and stays shared.
    # 嵌套证据按约定不可变，保持共享。
    assert copied['value'][0]['evidence'] is evidence


def test_expand_restores_configured_fact_allowances(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef(module='main', qualname='entry'), max_depth=2,
                              max_functions=3, max_call_contexts=9)
    # Simulate previous queries that consumed the shared fact allowances.
    # 模拟此前查询已消耗共享事实额度。
    for name in ('_fact_functions', '_fact_calls', '_object_fact_functions',
                 '_object_fact_steps', '_effect_fact_functions', '_effect_fact_steps'):
        setattr(analyzer, name, 0)
    call = next(item for item in result.calls if item.target is not None)
    seen = []
    original = type(analyzer)._walk

    ## Capture the fact allowance each expansion starts from.
    def walk(active, *arguments, **keywords):
        seen.append((active._fact_functions, active._fact_calls,
                     active._object_fact_functions, active._object_fact_steps,
                     active._effect_fact_functions, active._effect_fact_steps))
        return original(active, *arguments, **keywords)

    monkeypatch.setattr(type(analyzer), '_walk', walk)
    analyzer.expand(result, call.id, additional_depth=1)
    assert seen and seen[0] == (3, 9, 3, 9, 3, 9)
