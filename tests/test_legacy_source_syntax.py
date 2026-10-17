## @package tests.test_legacy_source_syntax

import ast
import hashlib

import pytest

from pcresolve.source_syntax import parse_python_source
from pcresolve.source_snapshot import SourceStore, FLOW_SOURCE, OWNERSHIP_SOURCE


def test_legacy_attributes_preserve_original_names_and_byte_coordinates():
    text = "label = '对象.async()'  # .async()\n对象.async(1)\nx.asynx(2)\nx.await(3)\n"
    tree = parse_python_source(text)
    attrs = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
    assert [node.attr for node in attrs] == ['async', 'asynx', 'await']
    assert ast.get_source_segment(text, attrs[0]) == '对象.async'
    assert tree.body[0].value.value == '对象.async()'


@pytest.mark.parametrize('text', ['def async(): pass\n', 'x.async(\n', 'x.async =\n'])
def test_other_invalid_syntax_is_not_repaired(text):
    with pytest.raises(SyntaxError):
        parse_python_source(text)


def test_modern_async_syntax_is_unchanged():
    text = 'async def entry():\n    return await task()\n'
    assert ast.dump(parse_python_source(text)) == ast.dump(ast.parse(text))


def test_flow_legacy_parse_keeps_text_hash_and_ownership_policy(tmp_path):
    path = tmp_path / 'legacy.py'
    text = 'x.async(1)\n'
    path.write_text(text, encoding='utf-8')
    store = SourceStore()
    for policy, valid in [(OWNERSHIP_SOURCE, False), (FLOW_SOURCE, True),
                          (OWNERSHIP_SOURCE, False), (FLOW_SOURCE, True)]:
        document = store.snapshot([str(path)], policy).documents[str(path)]
        assert (document.tree is not None) is valid
        assert document.text == text
        assert document.sha256 == hashlib.sha256(text.encode()).hexdigest()
