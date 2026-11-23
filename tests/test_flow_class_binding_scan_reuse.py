## @package tests.test_flow_class_binding_scan_reuse
#  Whole-source class-binding scans never recurse during a scan.

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.index import definitions as index_definitions
from tests.flow_test_support import set_class_binding_limit


SOURCE = (
    'class Worker:\n'
    '    def run(self, value):\n'
    '        return value\n'
    '\n'
    '    def echo(self):\n'
    '        return self.run(1)\n'
    '\n'
    '\n'
    'def entry(value):\n'
    '    worker = Worker()\n'
    '    return worker.run(value)\n'
)


## Write the shared fixture and return an indexed analyzer for it.
def _analyzer(tmp_path):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    return analyzer


def test_nested_escape_scan_reports_truncation_instead_of_rescanning(tmp_path, monkeypatch):
    analyzer = _analyzer(tmp_path)
    nested = []

    ## Request the escape scan from inside the scan, as decorator proofs do.
    def request_escape_scan(active, ref, node, aliases):
        nested.append(active._class_binding_writes(include_escapes=True))
        return False

    monkeypatch.setattr(index_definitions, 'native_class_operand', request_escape_scan)
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert nested
    assert all(result == ([], True) for result in nested)
    assert analyzer._class_binding_escape_cache == (writes, truncated)
    assert analyzer._class_binding_writes(include_escapes=True) == (writes, truncated)


def test_unbudgeted_queries_reuse_syntax_scope_facts(tmp_path):
    analyzer = _analyzer(tmp_path)
    entry = FunctionRef(module='main', qualname='entry')
    analyzer.analyze(entry, max_depth=2)
    scopes = analyzer._scope_fact_cache
    assert scopes
    analyzer.analyze(entry, max_depth=2)
    assert analyzer._scope_fact_cache is scopes
