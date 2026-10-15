## @package tests.test_value_flow_fresh_class_cache

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_fresh_class_cache'
POSITIVE = ['Fresh', 'Direct', 'Probe', 'BothBranches', 'ReplacedDescriptor',
            'LiteralPrivate', 'SyntaxPrivate']
NEGATIVE = ['ExistingDescriptor', 'ConditionalDescriptor', 'OneBranch', 'UnknownValue',
            'ReadBeforeWrite', 'Deleted', 'ReboundName', 'DivergentName',
            'ShadowedGetattr', 'DynamicName', 'ComprehensionWrite', 'OverwrittenPayload',
            'DeferredRead', 'ShadowedLiteralFactory']


@pytest.mark.parametrize('name', POSITIVE)
def test_fresh_literal_payload_reads_preserve_other_method_lookup(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert call.target.qualname == 'Fresh.fixed'
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    proof = call.class_method_bindings[0]['lookup_preservation'][0]
    expected = ('__cache' if name == 'LiteralPrivate' else
                '_SyntaxPrivate__cache' if name == 'SyntaxPrivate' else 'cache')
    assert proof['attributes'] == [expected]
    assert proof['value_completeness'] == 'unmodeled'


@pytest.mark.parametrize('name', NEGATIVE)
def test_unproven_reads_and_names_do_not_preserve_the_old_target(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert not any(f['status'] == 'source_bound' for f in call.class_method_bindings)


def test_runtime_fresh_writes_replace_descriptors_but_reads_can_rebind_the_sink():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in POSITIVE:
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in NEGATIVE:
        assert values[name](old=1) == {'old': 1}


def test_fresh_attribute_proofs_are_query_local():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyzer.analyze(FunctionRef('cases', 'Fresh'))
    snapshot = first.to_dict()
    analyzer.analyze(FunctionRef('cases', 'ExistingDescriptor'))
    assert analyzer.analyze(FunctionRef('cases', 'Fresh')).to_dict() == snapshot
    assert first.to_dict() == snapshot
