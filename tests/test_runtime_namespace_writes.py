## @package tests.test_runtime_namespace_writes

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.runtime.limits import AnalysisLimits


SOURCE = '''def fixed(allowed=0): return allowed
def other(allowed=0): return allowed
def client(**kwargs): return fixed(**kwargs)
'''


@pytest.mark.parametrize('tail', [
    "def mutate(): globals()['fixed'] = other",
    "def mutate(name): globals()[name] = other",
    "def mutate(): globals().update({'fixed': other})",
    'import sample\ndef mutate(): sample.fixed = other',
    "import sample\ndef mutate(): setattr(sample, 'fixed', other)",
])
def test_runtime_namespace_writes_do_not_reuse_a_snapshot_callable(tmp_path, tail):
    (tmp_path / 'sample.py').write_text(SOURCE + tail + '\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'client'))
    call = next(call for call in result.calls if call.callee_name == 'fixed')
    assert any(boundary.get('call_id') == call.id and boundary.get('reason') ==
               'dynamic_source_namespace_binding' and boundary.get('boundary_kind') == 'uncertainty'
               for boundary in result.boundaries)


def test_an_unrelated_export_does_not_invalidate_a_fixed_callable(tmp_path):
    (tmp_path / 'sample.py').write_text(SOURCE + '''import sample
def mutate(): sample.version = 'next'
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'client'))
    call = next(call for call in result.calls if call.callee_name == 'fixed')
    assert call.target is not None and call.target.qualname == 'fixed'


def test_runtime_namespace_writes_cannot_leave_a_builtin_name_confirmed(tmp_path):
    (tmp_path / 'sample.py').write_text(SOURCE + '''def check(value): return isinstance(value, int)
def mutate(): globals()['isinstance'] = other
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    ref, node = analyzer._definition_index.find('sample', 'check')[0]
    assert analyzer._builtin_name_status(ref, node, 'isinstance') != 'confirmed_builtin'


def test_unbudgeted_queries_reuse_runtime_namespace_writes_until_source_changes(tmp_path):
    source = tmp_path / 'sample.py'
    source.write_text('def check(value): return isinstance(value, int)\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)

    analyzer.analyze(FunctionRef('sample', 'check'))
    first = analyzer._runtime_namespace_cache
    assert first is not False

    analyzer.analyze(FunctionRef('sample', 'check'))
    assert analyzer._runtime_namespace_cache is first

    analyzer.analysis_limits = AnalysisLimits(max_work=100000)
    analyzer.analyze(FunctionRef('sample', 'check'))
    assert analyzer._runtime_namespace_cache is not first
    budgeted = analyzer._runtime_namespace_cache
    analyzer.analysis_limits = None

    source.write_text("def check(value): return isinstance(value, int)\ndef other(value): return value\ndef mutate(): globals()['isinstance'] = other\n", encoding='utf-8')
    analyzer.analyze(FunctionRef('sample', 'check'))
    assert analyzer._runtime_namespace_cache is not budgeted
    assert analyzer._runtime_namespace_cache[0]['sample'] == {'isinstance'}
