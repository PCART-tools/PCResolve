## @package tests.test_class_creation_native_queries

import copy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


HELPER = '''def checker(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
'''
SOURCE = '''from helper import checker as check
class Base:
    def __init_subclass__(cls):
        if check(cls):
            opaque(cls)
        cls.marker = True
class Public(Base):
    def __init__(self, **kwargs): fixed(**kwargs)
def fixed(allowed=0): return allowed
'''


def analyzer(root, source=SOURCE, helper=HELPER, include_helper=True):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    support = root / 'helper.py'
    support.write_text(helper, encoding='utf-8')
    files = [path, support] if include_helper else [path]
    return FlowAnalyzer(source_files=files, import_roots=[root]), support


def test_creation_effects_consume_the_source_protocol_and_prune_the_unreachable_branch(tmp_path):
    flow, _ = analyzer(tmp_path)
    result = flow.analyze(FunctionRef('example', 'Public'))
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    hook = binding['class_creation_hooks'][0]
    assert hook['attributes'] == ['marker']
    assert len(hook['native_type_queries']) == 1
    query = hook['native_type_queries'][0]
    assert query['receiver_class'] == hook['receiver_class']
    assert query['source_protocol']['result'] is False
    assert query['source_protocol']['source_hashes'] == result.inputs['sha256']
    assert set(query['source_protocol']['assumptions']).issubset(hook['assumptions'])
    assert set(hook['assumptions']).issubset(binding['assumptions'])
    assert 'source_class_creation_native_queries' in binding['assumptions']


def test_import_roots_do_not_implicitly_admit_dependency_code(tmp_path):
    flow, support = analyzer(tmp_path, include_helper=False)
    with pytest.raises(ValueError):
        flow.analyze(FunctionRef('example', 'Public'))
    assert str(support) not in flow.files
    flow.add_files([support])
    assert flow.analyze(FunctionRef('example', 'Public')).inputs['entry_binding']['status'] == 'source_bound'


def test_opted_in_protocol_dependencies_have_separate_versions_and_scope(tmp_path):
    flow, support = analyzer(tmp_path, include_helper=False)
    flow = FlowAnalyzer(source_files=flow.files, import_roots=flow.roots,
                        support_source_protocols=True)
    result = flow.analyze(FunctionRef('example', 'Public'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert str(support) not in result.inputs['sha256']
    assert str(support) not in result.inputs['source_files']
    assert set(result.inputs['supporting_source_sha256']) == {str(support)}
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    protocol = hook['native_type_queries'][0]['source_protocol']
    assert protocol['source_hashes'] == {
        **result.inputs['sha256'], **result.inputs['supporting_source_sha256']}
    support.write_text(HELPER.replace('return False', 'return True'))
    with pytest.raises(ValueError):
        flow.analyze(FunctionRef('example', 'Public'))


def test_protocol_dependency_options_require_an_explicit_boolean(tmp_path):
    with pytest.raises(ValueError, match='support_source_protocols'):
        FlowAnalyzer(project_root=tmp_path, support_source_protocols=1)


def test_expansion_checks_dependency_versions_and_preserves_the_parent(tmp_path):
    flow, support = analyzer(tmp_path, SOURCE + '\ndef client(**kwargs): return Public(**kwargs)\n',
                             include_helper=False)
    flow = FlowAnalyzer(source_files=flow.files, import_roots=flow.roots,
                        support_source_protocols=True)
    parent = flow.analyze(FunctionRef('example', 'client'))
    before = copy.deepcopy(parent.to_dict())
    call = next(item for item in parent.calls if item.target and item.target.qualname == 'Public.__init__')
    child = flow.expand(parent, call.id)
    assert child.inputs['supporting_source_sha256'] == parent.inputs['supporting_source_sha256']
    assert parent.to_dict() == before
    support.write_text(HELPER.replace('return False', 'return True'))
    with pytest.raises(ValueError, match='[Ss]ource.*changed'):
        flow.expand(parent, call.id)


@pytest.mark.parametrize('source,helper', [
    (SOURCE, HELPER.replace('return False', 'return True')),
    (SOURCE, HELPER + '\nchecker.__code__ = opaque\n'),
    (SOURCE + '\nopaque(check)\n', HELPER),
    (SOURCE + '\ncheck = opaque\n', HELPER),
    (SOURCE.replace('check(cls)', 'check(opaque)'), HELPER),
    (SOURCE.replace('check(cls)', 'check(cls, opaque)'), HELPER),
    (SOURCE.replace('check(cls)', 'check(cls, flag=True)'), HELPER),
    (SOURCE, HELPER.replace('iter(value)', 'opaque(value)')),
])
def test_open_calls_and_observable_helper_replacements_do_not_preserve_the_constructor(
        tmp_path, source, helper):
    flow, _ = analyzer(tmp_path, source, helper)
    with pytest.raises(ValueError):
        flow.analyze(FunctionRef('example', 'Public'))


def test_a_native_query_inside_a_classmethod_keeps_its_actual_caller_evidence(tmp_path):
    source = SOURCE.replace('        if check(cls):',
        '        cls.refresh()\n    @classmethod\n    def refresh(receiver):\n        if check(receiver):')
    source = source.replace('opaque(cls)', 'opaque(receiver)').replace('cls.marker', 'receiver.marker')
    flow, _ = analyzer(tmp_path, source)
    result = flow.analyze(FunctionRef('example', 'Public'))
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert hook['native_type_queries'][0]['caller']['qualname'] == 'Base.refresh'
    assert hook['native_type_queries'][0]['parameter'] == 'receiver'
