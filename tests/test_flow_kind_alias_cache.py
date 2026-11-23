## @package tests.test_flow_kind_alias_cache
#  Kind-alias module scans reuse one syntax index per source generation.

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs.namespaces.metadata import _metadata_signature
from pcresolve.flow.proofs.namespaces.metadata import _kind_alias_scan


SOURCE = (
    'def helper(value):\n'
    '    return value\n'
    '\n'
    '\n'
    'class Holder:\n'
    '    attribute = helper(1)\n'
)


def test_kind_alias_module_scan_is_reused_per_generation(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index(preserve_source_facts=True)
    scans = []
    original = _kind_alias_scan.inspect_module_kind_aliases

    ## Record each per-module kind-alias scan.
    def counted(*arguments, **keywords):
        scans.append(arguments[0])
        return original(*arguments, **keywords)

    monkeypatch.setattr(_metadata_signature, 'inspect_module_kind_aliases', counted)
    reference = FunctionRef('main', 'helper', str(tmp_path / 'main.py'))
    first = _metadata_signature._kind_aliases_closed(analyzer, reference)
    after_first = len(scans)
    second = _metadata_signature._kind_aliases_closed(analyzer, reference)
    assert after_first == len(analyzer.module_bodies)
    assert len(scans) == after_first
    assert second == first
    assert len(analyzer._module_syntax_index_cache) == len(analyzer.module_bodies)
