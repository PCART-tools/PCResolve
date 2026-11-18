## @package tests.test_source_iterability_protocol

import pytest

from pcresolve import FlowAnalyzer
from pcresolve.flow.proofs._source_protocols import SourceProtocolResolver
from pcresolve.frontend.source_snapshot import FLOW_SOURCE, SourceStore


PROBE = '''def probe(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True
'''


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def reader(root):
    return SourceProtocolResolver([root], analyzer_factory=FlowAnalyzer)


def test_native_metaclass_iterability_is_a_conditional_source_protocol(tmp_path):
    put(tmp_path, 'example.py', PROBE)
    fact = reader(tmp_path).iterability('example', 'probe')
    assert fact['status'] == 'requires_native_type_input'
    assert fact['precondition'] == {'argument': {'position': 0}, 'exact_metaclass': 'type'}
    assert fact['result'] is False
    assert fact['effects'] == 'none_if_precondition'
    assert fact['runtime_input_confirmed'] is False
    assert fact['source_binding']['target']['qualname'] == 'probe'


def test_predicate_lookup_can_follow_an_implicit_parent_child_module_binding(tmp_path):
    put(tmp_path, 'pkg/__init__.py', 'from .impl import *\n__all__ = [] + impl.__all__\n')
    put(tmp_path, 'pkg/impl.py', "__all__ = ['probe']\n" + PROBE)
    fact = reader(tmp_path).iterability('pkg', 'probe')
    assert fact is not None and fact['result'] is False
    assert fact['source_binding']['target']['module'] == 'pkg.impl'


@pytest.mark.parametrize('tail', [
    'impl.probe.__code__ = opaque',
    'saved = impl.probe\nopaque(saved)',
    'opaque(impl)',
])
def test_implicit_module_alias_does_not_hide_callable_mutation_or_exposure(tmp_path, tail):
    put(tmp_path, 'pkg/__init__.py', 'from .impl import *\n__all__ = [] + impl.__all__\n'
        + tail + '\n')
    put(tmp_path, 'pkg/impl.py', "__all__ = ['probe']\n" + PROBE)
    assert reader(tmp_path).iterability('pkg', 'probe') is None


def test_exported_metadata_decorator_does_not_change_the_protocol_body(tmp_path):
    put(tmp_path, 'pkg/__init__.py', 'if enabled:\n    from .impl import *\n')
    put(tmp_path, 'pkg/decorators.py', '''def mark(module):
    def decorate(fn):
        fn.__module__ = module
        return fn
    return decorate
''')
    put(tmp_path, 'pkg/impl.py', "from .decorators import mark\n__all__ = ['probe']\n"
        + PROBE.replace('def probe', "@mark('public')\ndef probe"))
    fact = reader(tmp_path).iterability('pkg', 'probe')
    assert fact['result'] is False
    assert fact['source_binding']['may_be_unbound']
    assert fact['decorator_effects'][0]['body_binding_status'] == 'preserved'
    assert len(fact['source_hashes']) == 3


@pytest.mark.parametrize('mutation', [
    '\niter = opaque\n',
    '\nTypeError = opaque\n',
    '\nprobe.__code__ = opaque\n',
    '\nsaved = probe\nsaved.__defaults__ = opaque\n',
    '\nopaque(probe)\n',
    '\nregistry = [probe]\n',
    '\ndef writer():\n    global probe\n    probe = opaque\n',
])
def test_shadowed_protocols_or_exposed_function_bindings_remain_open(tmp_path, mutation):
    put(tmp_path, 'example.py', PROBE + mutation)
    assert reader(tmp_path).iterability('example', 'probe') is None


@pytest.mark.parametrize('before,after', [
    ('iter(value)', 'opaque(value)'),
    ('except TypeError:', 'except Exception:'),
    ('return False', 'return opaque(value)'),
    ('iter(value)', 'iter(value)\n        opaque(value)'),
    ('def probe(value)', 'async def probe(value)'),
])
def test_a_similar_name_or_partial_body_match_does_not_prove_the_protocol(tmp_path, before, after):
    put(tmp_path, 'example.py', PROBE.replace(before, after))
    assert reader(tmp_path).iterability('example', 'probe') is None


def test_a_decorator_that_replaces_the_function_body_keeps_the_query_open(tmp_path):
    put(tmp_path, 'example.py', '''def decorate(fn):
    fn.__code__ = opaque
    return fn
''' + PROBE.replace('def probe', '@decorate\ndef probe'))
    assert reader(tmp_path).iterability('example', 'probe') is None


def test_an_ordinary_call_to_the_function_is_not_a_function_object_escape(tmp_path):
    put(tmp_path, 'example.py', PROBE + '\nanswer = probe(0)\n')
    assert reader(tmp_path).iterability('example', 'probe')


def test_builtin_mutation_in_the_public_export_module_invalidates_the_helper(tmp_path):
    put(tmp_path, 'pkg/__init__.py',
        'from .impl import probe\nimport builtins\nbuiltins.iter = opaque\n')
    put(tmp_path, 'pkg/impl.py', PROBE)
    assert reader(tmp_path).iterability('pkg', 'probe') is None


def test_missing_analysis_provider_does_not_promote_a_source_reference_to_a_body_proof(tmp_path):
    put(tmp_path, 'example.py', PROBE)
    resolver = SourceProtocolResolver([tmp_path])
    assert resolver.iterability('example', 'probe') is None
    assert resolver.last_boundary == 'source_protocol_analysis_provider_unavailable'


def test_ambient_primary_files_have_a_separate_explicit_module_budget(tmp_path):
    put(tmp_path, 'example.py', PROBE)
    paths = [put(tmp_path, 'ambient%d.py' % index, '# Primary source context.\n')
             for index in range(70)]
    snapshot = SourceStore().snapshot([str(path) for path in paths], FLOW_SOURCE)
    ambient = [(path.stem, snapshot.documents[str(path)]) for path in paths]
    resolver = SourceProtocolResolver([tmp_path], analyzer_factory=FlowAnalyzer,
                                     ambient_documents=ambient, max_ambient_modules=70)
    fact = resolver.iterability('example', 'probe')
    assert fact is not None and len(fact['source_hashes']) == 71
    bounded = SourceProtocolResolver([tmp_path], analyzer_factory=FlowAnalyzer,
                                    ambient_documents=ambient, max_ambient_modules=69)
    assert bounded.iterability('example', 'probe') is None
    assert bounded.last_boundary == 'source_protocol_ambient_module_budget'


def test_irrelevant_ambient_literals_do_not_repeat_alias_and_escape_work(tmp_path):
    put(tmp_path, 'example.py', PROBE)
    path = put(tmp_path, 'ambient.py', 'DATA = (' + '0,' * 500 + ')\n')
    snapshot = SourceStore().snapshot([str(path)], FLOW_SOURCE)
    resolver = SourceProtocolResolver([tmp_path], analyzer_factory=FlowAnalyzer,
        ambient_documents=[('ambient', snapshot.documents[str(path)])], max_nodes=1000)
    assert resolver.iterability('example', 'probe') is not None


@pytest.mark.parametrize('text', [
    'import example as ns\nsaved = ns\nsaved.probe.__code__ = opaque\n',
    'import example as ns\nopaque(ns)\n',
    'import example as ns\nsaved = ns\nopaque(saved)\n',
])
def test_ambient_module_aliases_cannot_hide_helper_mutation_or_exposure(tmp_path, text):
    put(tmp_path, 'example.py', PROBE)
    path = put(tmp_path, 'ambient.py', text)
    snapshot = SourceStore().snapshot([str(path)], FLOW_SOURCE)
    resolver = SourceProtocolResolver([tmp_path], analyzer_factory=FlowAnalyzer,
        ambient_documents=[('ambient', snapshot.documents[str(path)])])
    assert resolver.iterability('example', 'probe') is None
