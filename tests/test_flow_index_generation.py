## @package tests.test_flow_index_generation
#  Index generations require the same source versions and module context.
from pcresolve.flow.index.generation import same_generation
from pcresolve.frontend.source_snapshot import SourceDocument, SourceSnapshot, FLOW_SOURCE, OWNERSHIP_SOURCE


def test_generation_requires_document_identity_and_ordered_roots():
    doc = SourceDocument('x.py', text='x = 1')
    previous = SourceSnapshot(('x.py',), {'x.py': doc}, FLOW_SOURCE)
    same = SourceSnapshot(('x.py',), {'x.py': doc}, FLOW_SOURCE)
    distinct = SourceSnapshot(('x.py',), {'x.py': SourceDocument('x.py', text='x = 1')}, FLOW_SOURCE)
    other_policy = SourceSnapshot(('x.py',), {'x.py': doc}, OWNERSHIP_SOURCE)
    assert same_generation(previous, same, ('one', 'two'), ('one', 'two'))
    assert not same_generation(previous, distinct, ('one',), ('one',))
    assert not same_generation(previous, same, ('one', 'two'), ('two', 'one'))
    assert not same_generation(previous, other_policy, (), ())
    assert not same_generation(None, same, (), ())


def test_generation_rejects_changed_selection_and_file_order():
    first = SourceDocument('a.py', text='a = 1')
    second = SourceDocument('b.py', text='b = 2')
    documents = {'a.py': first, 'b.py': second}
    original = SourceSnapshot(('a.py', 'b.py'), documents, FLOW_SOURCE)
    reversed_files = SourceSnapshot(('b.py', 'a.py'), documents, FLOW_SOURCE)
    removed = SourceSnapshot(('a.py',), {'a.py': first}, FLOW_SOURCE)
    assert not same_generation(original, reversed_files, (), ())
    assert not same_generation(original, removed, (), ())
