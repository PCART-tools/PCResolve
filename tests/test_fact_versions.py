## @package tests.test_fact_versions
#  Structural mutation generations preserve ordered collection behavior.

from copy import deepcopy

import pytest

from pcresolve.call_graph import ClassSummary, FunctionId, ModuleCallGraph, ProjectCallGraph
from pcresolve.fact_versions import VersionedDict, VersionedList


@pytest.mark.parametrize('operation', [
    lambda values: values.update({'c': 3}),
    lambda values: values.setdefault('c', 3),
    lambda values: values.pop('a'),
    lambda values: values.popitem(),
    lambda values: values.clear(),
    lambda values: values.__delitem__('a'),
    lambda values: values.__ior__({'c': 3}),
])
def test_dictionary_mutations_preserve_values_and_advance_generation(operation):
    plain = {'a': 1, 'b': 2}
    changes = []
    watched = VersionedDict(plain, changed=lambda: changes.append(True))
    operation(plain)
    operation(watched)
    assert list(watched.items()) == list(plain.items())
    assert watched.version > 0 and changes


@pytest.mark.parametrize('operation', [
    lambda values: values.append(4),
    lambda values: values.extend([4, 5]),
    lambda values: values.extend(values),
    lambda values: values.insert(1, 4),
    lambda values: values.__setitem__(slice(None, None, 2), [4, 5]),
    lambda values: values.__delitem__(slice(0, 2)),
    lambda values: values.pop(),
    lambda values: values.remove(2),
    lambda values: values.reverse(),
    lambda values: values.sort(),
    lambda values: values.clear(),
    lambda values: values.__iadd__([4]),
    lambda values: values.__imul__(2),
])
def test_list_mutations_preserve_values_and_advance_generation(operation):
    plain = [3, 2, 1]
    changes = []
    watched = VersionedList(plain, changed=lambda: changes.append(True))
    operation(plain)
    operation(watched)
    assert watched == plain
    assert watched.version > 0 and changes


def test_deepcopy_rebinds_nested_change_observers():
    summary = ClassSummary(FunctionId('main', 'A'))
    module = ModuleCallGraph('main', classes={'A': summary})
    graph = ProjectCallGraph({'main': module})
    copied = deepcopy(graph)
    original_version, copied_version = graph.version, copied.version
    copied.modules['main'].classes['A'].methods['method'] = None
    assert copied.version > copied_version
    assert graph.version == original_version
    assert not summary.methods


def test_failed_iterator_extension_retains_partial_update_and_notification():
    def values():
        yield 1
        raise ValueError('interrupted')
    watched = VersionedList()
    with pytest.raises(ValueError, match='interrupted'):
        watched.extend(values())
    assert watched == [1] and watched.version > 0
