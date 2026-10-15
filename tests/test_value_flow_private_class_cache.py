## @package tests.test_value_flow_private_class_cache

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_private_class_cache'


@pytest.mark.parametrize('name, attribute', [('____', '__cache'), ('_Named', '_Named__cache')])
def test_private_cache_mangling_matches_the_lexical_class_name(name, attribute):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert call.target.qualname == 'Base.fixed'
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    assert call.class_method_bindings[0]['lookup_preservation'][0]['attributes'] == [attribute]


def test_an_all_underscore_class_does_not_overwrite_a_different_descriptor():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', '___'))
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert not any(f['status'] == 'source_bound' for f in call.class_method_bindings)


def test_runtime_private_attribute_spelling_and_descriptor_effects():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('____', '_Named'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    assert '__cache' in vars(values['____'])
    assert '_Named__cache' in vars(values['_Named'])
    assert values['___'](old=1) == {'old': 1}
    assert '__cache' in vars(values['___'])
    assert isinstance(vars(values['___'])['___cache'], values['Descriptor'])
    assert values['____'].stored() is values['Base']
    assert '__impl' in vars(values['____'])


def test_private_attribute_value_provenance_uses_the_actual_storage_spelling():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', '____.stored'))
    returned = next(f for f in result.functions if f['function']['qualname'] == '____.stored')['returns']
    assert returned[0]['class_type']['qualname'] == 'Base'
    assert returned[0]['attribute_provenance'][0]['storage_attribute'] == '__impl'
