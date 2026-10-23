## @package tests.test_function_metadata_formation

import pytest

from pcresolve import FlowAnalyzer
from pcresolve._function_metadata_formation import metadata_formation
from pcresolve.class_attribute_effects import _ClassEffectLimit


SOURCE = '''def document(fn):
    fn.__doc__ = 'Generated native documentation.'
    return fn
class Public:
    @document
    def set_value(self, value):
        """Original documentation."""
        pass
'''


def prepare(root, source=SOURCE):
    (root / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, analyzer._definition_index.find('example', 'Public.set_value')[0]


def test_doc_decoration_retains_native_function_metadata_formation(tmp_path):
    analyzer, target = prepare(tmp_path)
    proof = metadata_formation(analyzer, target)
    assert proof is not None
    assert proof['status'] == 'source_bound'
    assert proof['phase'] == 'before_name_binding'
    assert proof['metadata_shapes']['documentation'] == ['str']
    assert proof['metadata_shapes']['signature'] == 'native_source_function_signature'
    assert proof['runtime_function_binding_confirmed'] is False
    assert proof['current_namespace_binding_confirmed'] is False
    assert proof['decorations'][0]['effects'][0]['value_shapes'] == ['str']


@pytest.mark.parametrize('decorator', ['', 'fn.__module__ = None\n    '])
def test_plain_or_module_metadata_writes_keep_formation_separate_from_lookup(tmp_path, decorator):
    source = SOURCE.replace("fn.__doc__ = 'Generated native documentation.'", decorator +
                            "fn.__doc__ = 'Generated native documentation.'")
    if not decorator:
        source = source.replace('    @document\n', '')
    analyzer, target = prepare(tmp_path, source)
    proof = metadata_formation(analyzer, target)
    assert proof is not None
    assert proof['metadata_shapes']['documentation'] == ['str']
    assert proof['current_namespace_binding_confirmed'] is False


@pytest.mark.parametrize('old,new', [
    ("'Generated native documentation.'", '123'),
    ("'Generated native documentation.'", 'opaque'),
    ('fn.__doc__ =', 'fn.__signature__ ='),
    ('return fn', 'return opaque'),
    ('return fn', 'expose(fn)\n    return fn'),
])
def test_open_or_non_native_metadata_does_not_satisfy_native_query_inputs(tmp_path, old, new):
    analyzer, target = prepare(tmp_path, SOURCE.replace(old, new))
    assert metadata_formation(analyzer, target) is None


@pytest.mark.parametrize('prefix', [
    '__name__ = None\n',
    '__name__ = opaque\n',
    'def change():\n    global __name__\n    __name__ = opaque\n',
])
def test_formation_does_not_assume_a_modified_module_name_is_native_text(tmp_path, prefix):
    analyzer, target = prepare(tmp_path, prefix + SOURCE.replace('    @document\n', ''))
    assert metadata_formation(analyzer, target) is None


def test_formation_cannot_publish_partial_metadata_after_budget_exhaustion(tmp_path):
    analyzer, target = prepare(tmp_path)
    analyzer._class_effect_fact_steps = 0
    with pytest.raises(_ClassEffectLimit):
        metadata_formation(analyzer, target)
