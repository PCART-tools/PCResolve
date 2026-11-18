import ast
from types import SimpleNamespace

import pytest

from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.transfer.source_evidence import SourceEvidenceMixin


class Host(SourceEvidenceMixin):
    def __init__(self, texts):
        self.ref = FunctionRef(module='main', file_path='main.py')
        self.analyzer = SimpleNamespace(texts=texts)
        self.source_lines = [line.encode('utf-8') for line in texts['main.py'].split('\n')]
        self.evidence_cache = {}


def test_source_evidence_handles_multibyte_and_multiline_and_is_query_local():
    text = "prefix = '字'; invoke(\n    value,\n    other\n)\n"
    node = ast.parse(text).body[1].value
    host = Host({'main.py': text, 'other.py': 'external(1)\n'})
    record = host.evidence(node)
    assert record['source_text'] == 'invoke(\n    value,\n    other\n)'
    assert host.evidence(node) is record
    external_node = ast.parse('external(1)').body[0].value
    external = host.evidence_at(FunctionRef(module='other', file_path='other.py'), external_node)
    assert external['source_text'] == 'external(1)'
    assert external['file_path'] == 'other.py'
    second = Host({'main.py': text})
    assert second.evidence(node) == record
    assert second.evidence(node) is not record


def test_source_evidence_missing_end_line_does_not_cache_partial_result():
    host = Host({'main.py': 'f()\n'})
    node = ast.parse('f()').body[0].value
    node.end_lineno = None
    with pytest.raises(TypeError):
        host.evidence(node)
    assert host.evidence_cache == {}
