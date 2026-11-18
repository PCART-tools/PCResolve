## @package tests.test_syntax_facts

import ast
import gc
import weakref

import pytest

from pcresolve import FlowAnalyzer
from pcresolve.runtime.limits import AnalysisBudget, AnalysisLimits, AnalysisLimitExceeded
from pcresolve.facts.import_facts import import_facts
from pcresolve.flow.proofs import syntax_facts
from pcresolve.flow.proofs._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs._class_partial import _namespace as partial_namespace
from pcresolve.flow.proofs._class_type_tests import _namespace as type_namespace


SOURCE = '''import functools
from functools import partial
class Public:
    def method(self, value):
        return isinstance(value, Public)
'''


def analyzer_at(tmp_path):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    return analyzer


def test_structure_retains_statement_walk_order_parents_and_import_order():
    body = ast.parse(SOURCE + 'result = [x + 1 for x in values]\n').body
    nodes, parents = [], {}
    for statement in body:
        for node in ast.walk(statement):
            nodes.append(node)
            parents.update((child, node) for child in ast.iter_child_nodes(node))
    facts = syntax_facts.body_syntax(body, len(nodes))
    assert facts.nodes == tuple(nodes)
    assert dict(facts.parents) == parents
    assert facts.imports == tuple(fact for node in nodes for fact in import_facts(node))
    with pytest.raises(TypeError):
        facts.parents[body[0]] = body[1]
    with pytest.raises(syntax_facts.SyntaxLimit):
        syntax_facts.body_syntax(body, len(nodes) - 1)


def test_namespace_guards_share_structure_without_sharing_their_answers(tmp_path, monkeypatch):
    analyzer = analyzer_at(tmp_path)
    owner = analyzer._definition_index.find('main', 'Public', kind='class')[0][0]
    original, built = syntax_facts.body_syntax, []

    def counted(body, limit):
        built.append(tuple(body))
        return original(body, limit)

    monkeypatch.setattr(syntax_facts, 'body_syntax', counted)
    assert _stable_builtin_namespace(analyzer, owner)[0]
    assert _stable_builtin_namespace(analyzer, owner, ('isinstance',))[0]
    assert partial_namespace(analyzer)
    assert type_namespace(analyzer, owner)
    assert len(built) == 1
    body = analyzer.module_bodies['main'][0][1]
    facts = analyzer._syntax_facts(body, 1000000)
    with pytest.raises(syntax_facts.SyntaxLimit):
        analyzer._syntax_facts(body, len(facts.nodes) - 1)


def test_structure_cache_follows_source_generation_and_analyzer_lifetime(tmp_path):
    analyzer = analyzer_at(tmp_path)
    body = analyzer.module_bodies['main'][0][1]
    facts = analyzer._syntax_facts(body, 1000000)
    analyzer._index(preserve_source_facts=True)
    assert analyzer._syntax_facts(analyzer.module_bodies['main'][0][1], 1000000) is facts
    other = FlowAnalyzer(project_root=tmp_path)
    other._index()
    assert other._syntax_facts(other.module_bodies['main'][0][1], 1000000) is not facts

    (tmp_path / 'main.py').write_text(SOURCE + 'changed = True\n', encoding='utf-8')
    analyzer._index(preserve_source_facts=True)
    assert not analyzer._syntax_fact_cache
    assert analyzer._syntax_facts(analyzer.module_bodies['main'][0][1], 1000000) is not facts
    added = tmp_path / 'extra.py'
    added.write_text('extra = 1\n', encoding='utf-8')
    analyzer.add_files([added])
    analyzer._index(preserve_source_facts=True)
    assert not analyzer._syntax_fact_cache
    analyzer._syntax_facts(analyzer.module_bodies['extra'][0][1], 1000000)
    added.unlink()
    analyzer._index(preserve_source_facts=True)
    assert not analyzer._syntax_fact_cache
    assert any(item['reason'] == 'source_unavailable' for item in analyzer.index_boundaries)


def test_budgeted_guard_keeps_node_charges_even_after_structure_was_cached(tmp_path):
    analyzer = analyzer_at(tmp_path)
    body = analyzer.module_bodies['main'][0][1]
    analyzer._syntax_facts(body, 1000000)
    owner = analyzer._definition_index.find('main', 'Public', kind='class')[0][0]
    analyzer._analysis_budget = AnalysisBudget(AnalysisLimits(max_work=3))
    assert analyzer._syntax_facts(body, 1000000) is None
    with pytest.raises(AnalysisLimitExceeded) as caught:
        _stable_builtin_namespace(analyzer, owner)
    assert caught.value.reason == 'work'
    assert caught.value.work == 4


def test_shared_structure_does_not_mix_protected_builtin_policies(tmp_path):
    analyzer = analyzer_at(tmp_path)
    path = tmp_path / 'main.py'
    path.write_text('import builtins\nbuiltins.property = opaque\n' + SOURCE, encoding='utf-8')
    analyzer._index()
    owner = analyzer._definition_index.find('main', 'Public', kind='class')[0][0]
    assert _stable_builtin_namespace(analyzer, owner)[0] is False
    assert _stable_builtin_namespace(analyzer, owner, ('isinstance',))[0] is True


def test_syntax_cache_is_released_with_its_analyzer(tmp_path):
    analyzer = analyzer_at(tmp_path)
    facts = analyzer._syntax_facts(analyzer.module_bodies['main'][0][1], 1000000)
    reference = weakref.ref(facts)
    del facts, analyzer
    gc.collect()
    assert reference() is None


def test_builtin_scope_retains_parameters_stores_and_definition_evaluations(tmp_path):
    analyzer = analyzer_at(tmp_path)
    node = ast.parse('''def holder():
    captured = None
    def sample(property, /, value=0, *args, flag=False, **kwargs):
        global dict
        nonlocal captured
        dict = value
        try:
            pass
        except Exception as list:
            pass
        def child(arg=(tuple := factory)):
            pass
        callback = lambda set: set
        return property
''').body[0].body[1]
    facts = analyzer._builtin_scope_facts(node)
    assert facts.bound == frozenset([
        'property', 'value', 'args', 'flag', 'kwargs', 'dict', 'list',
        'child', 'tuple', 'callback'])
    assert facts.loaded == frozenset(['value', 'Exception', 'property'])
    assert facts.globals == frozenset(['dict'])
    assert facts.nonlocals == frozenset(['captured'])


@pytest.mark.parametrize('source', [
    'lambda dict, /, *args, flag=False, **kwargs: dict',
    'async def sample(dict, /, *args, flag=False, **kwargs): return dict',
])
def test_builtin_scope_keeps_lambda_and_async_parameter_names(tmp_path, source):
    analyzer = analyzer_at(tmp_path)
    node = ast.parse(source).body[0]
    node = node.value if isinstance(node, ast.Expr) else node
    facts = analyzer._builtin_scope_facts(node)
    assert facts.bound == frozenset(['dict', 'args', 'flag', 'kwargs'])
    assert facts.loaded == frozenset(['dict'])
