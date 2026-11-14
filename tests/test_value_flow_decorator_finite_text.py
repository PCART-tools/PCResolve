## @package tests.test_value_flow_decorator_finite_text

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow.proofs._decorator_text as text_protocol


SOURCE = '''TEXT = 'Input description'
def documentation(*pieces):
    def decorate(fn):
        name = fn.__qualname__.split('.')[0]
        intro = 'The {} method.'.format(name)
        fn.__doc__ = intro + ''.join(pieces) + (fn.__doc__ if fn.__doc__ is not None else '')
        return fn
    return decorate
class Model:
    @documentation(TEXT, ' Tail')
    def forward(self, **kwargs):
        """Existing documentation."""
        return kwargs.pop('legacy')
'''


def decoration(tmp_path, source=SOURCE):
    (tmp_path / 'sample.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Model.forward'))
    return result.functions[0]['decorator_effects'][0]


def test_finite_source_text_and_function_metadata_preserve_execution(tmp_path):
    fact = decoration(tmp_path)
    assert fact['body_binding_status'] == 'preserved'
    assert fact['identity_status'] == 'preserved'
    assert not fact['boundaries']
    assert fact['runtime_target_confirmed'] is False
    assert {'str.split', 'str.format', 'str.join'} <= {
        effect['target'] for effect in fact['effects'] if isinstance(effect['target'], str)}
    assert any(e['source_text'] == "TEXT = 'Input description'" for e in fact['evidence'])


@pytest.mark.parametrize('source', [
    SOURCE.replace("TEXT = 'Input description'", 'TEXT = opaque()'),
    SOURCE + '\nTEXT = opaque()\n',
    SOURCE + '\ndef change():\n    global TEXT\n    TEXT = opaque()\n',
    SOURCE + '\nimport sample\nsample.TEXT = opaque()\n',
    SOURCE.replace("'The {} method.'", "'The {0.__class__} method.'"),
    SOURCE.replace("'The {} method.'", "'The {0[0]} method.'"),
    SOURCE.replace("'The {} method.'", "'The {0:{1}} method.'"),
    SOURCE.replace("split('.')", "split(opaque())"),
    SOURCE.replace("split('.')", "split('')"),
    SOURCE.replace("documentation(TEXT, ' Tail')", 'documentation(*opaque())'),
    SOURCE.replace("fn.__qualname__", 'opaque'),
    SOURCE.replace("' Tail'", 'opaque'),
    SOURCE.replace('class Model:\n', 'class Model:\n    TEXT = opaque()\n'),
    SOURCE.replace("TEXT = 'Input description'\n", '') + "\nTEXT = 'Input description'\n",
    SOURCE.replace('name = fn.__qualname__',
                   'fn.__qualname__ = opaque()\n        name = fn.__qualname__'),
    SOURCE + '\nexec("TEXT = opaque()")\n',
    SOURCE + '\nnamespace = globals()\nopaque(namespace)\n',
])
def test_open_captures_and_unsupported_format_protocols_retain_boundaries(tmp_path, source):
    fact = decoration(tmp_path, source)
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


def test_literal_scan_budget_and_source_edits_cannot_reuse_a_stale_fact(tmp_path, monkeypatch):
    witness = tmp_path / 'unrelated.py'
    witness.write_text('def utility(): return 1\n', encoding='utf-8')
    assert str(witness) in decoration(tmp_path)['source_hashes']
    analyzer = FlowAnalyzer(project_root=tmp_path)
    entry = FunctionRef('sample', 'Model.forward')

    def status():
        return analyzer.analyze(entry).functions[0]['decorator_effects'][0]['body_binding_status']

    assert status() == 'preserved'
    with monkeypatch.context() as patch:
        patch.setattr(text_protocol, '_TEXT_BINDING_NODE_LIMIT', 1)
        assert status() == 'unknown'
    assert status() == 'preserved'
    decoration(tmp_path, SOURCE + '\nTEXT = opaque()\n')
    analyzer.add_files([tmp_path / 'sample.py'])
    assert status() == 'unknown'
