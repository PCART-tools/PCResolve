## @package tests.test_dependency_recomputation
#  Dirty-summary scheduling must preserve synchronous fixed-point semantics.

import pcresolve.return_resolution as resolution
from pcresolve.return_resolution import CallBinding, ReturnCall, resolve_return_dependencies


def value(kind, source):
    return dict(kind=kind, source=source, relation='direct', evidence=[], conditions=[])


def test_stable_returns_are_not_recomputed_each_round(monkeypatch):
    summaries = {'leaf': [value('parameter', 'p')]}
    calls = {}
    for index in range(6):
        target = 'leaf' if index == 0 else 'chain%d' % (index - 1)
        name = 'chain%d' % index
        calls[name] = ReturnCall(name, target, (CallBinding('parameter', 'p', (value('parameter', 'p'),)),))
        summaries[name] = [value('call_result', name)]
    calls['stable'] = ReturnCall('stable', None,
        (CallBinding('parameter', 'p', (value('parameter', 'p'),)),),
        (dict(value('parameter', 'p'), evidence=[{'marker': 'stable'}]),))
    summaries['unrelated'] = [value('call_result', 'stable')]
    selected = []
    original = resolution.select_dependencies
    def count(values, path):
        if any(item.get('evidence') == [{'marker': 'stable'}] for item in values):
            selected.append(True)
        return original(values, path)
    monkeypatch.setattr(resolution, 'select_dependencies', count)
    result = resolve_return_dependencies('chain5', 'p', summaries, calls)
    assert result.status == 'converged' and result.iterations == 8
    assert result.paths[0]['call_context'] == ['chain%d' % i for i in range(5, -1, -1)]
    assert len(selected) == 1


def test_binding_dependencies_are_included_in_dirty_propagation():
    summaries = {'entry': [value('call_result', 'outer')],
                 'producer': [value('parameter', 'x')],
                 'identity': [value('parameter', 'p')]}
    calls = {
        'inner': ReturnCall('inner', 'producer',
            (CallBinding('parameter', 'x', (value('parameter', 'input'),)),)),
        'outer': ReturnCall('outer', 'identity',
            (CallBinding('parameter', 'p', (value('call_result', 'inner'),)),))}
    result = resolve_return_dependencies('entry', 'input', summaries, calls)
    assert result.status == 'converged' and result.iterations == 3
    assert result.paths[0]['source'] == 'input'
    assert result.paths[0]['call_context'] == ['inner', 'outer']


def test_dependency_discovery_preserves_iterables_and_ignores_unused_opaque_bindings():
    summaries = {'entry': iter([value('call_result', 'call')]),
                 'helper': iter([value('parameter', 'p')])}
    calls = {'call': ReturnCall('call', 'helper',
        (CallBinding('parameter', 'p', (value('parameter', 'input'),)),))}
    assert resolve_return_dependencies('entry', 'input', summaries, calls).paths
    opaque = {'entry': [value('call_result', 'call')], 'helper': []}
    calls = {'call': ReturnCall('call', 'helper', (CallBinding('parameter', 'p', ('opaque',)),))}
    assert resolve_return_dependencies('entry', 'input', opaque, calls).paths == ()
