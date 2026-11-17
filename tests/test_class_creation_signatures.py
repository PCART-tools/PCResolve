## @package tests.test_class_creation_signatures

import ast
import inspect
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''from inspect import Signature, Parameter
class Base:
    def __init_subclass__(cls):
        cls.signature = Signature([
            Parameter('self', Parameter.POSITIONAL_OR_KEYWORD),
            Parameter('option', Parameter.KEYWORD_ONLY, default=None)])
class Public(Base):
    def __init__(self, **kwargs): fixed(**kwargs)
def fixed(allowed=0): return allowed
'''


def prepare(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    return FlowAnalyzer(project_root=root), path


def test_creation_binds_native_signature_construction_from_literal_metadata(tmp_path):
    analyzer, path = prepare(tmp_path)
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    hook = binding['class_creation_hooks'][0]
    proof = hook['signature_creations'][0]
    assert proof['kind'] == 'source_native_signature_creation'
    assert proof['status'] == 'source_bound'
    assert proof['result_kind'] == 'native_inspect_signature'
    assert proof['runtime_creation_confirmed'] is False
    assert proof['source_hashes'] == result.inputs['sha256']
    assert set(proof['assumptions']).issubset(hook['assumptions'])
    assert hook['attributes'] == ['signature']
    cls = runpy.run_path(str(path))['Public']
    assert isinstance(cls.signature, inspect.Signature)
    assert str(cls.signature) == '(self, *, option=None)'


@pytest.mark.parametrize('old,new', [
    ("default=None", 'default=cls'),
    ("default=None", 'default=opaque()'),
    ("'option'", 'cls'),
    ("'option'", "'self'"),
    ("'option'", "'not valid'"),
    ('Parameter.KEYWORD_ONLY', 'opaque.kind'),
    ('Signature([', 'opaque(['),
    ('Signature([', 'Signature(opaque(['),
    ('default=None)])', 'default=None)], return_annotation=cls)'),
    ('default=None)])', 'default=None)], **options)'),
    ('class Base:', 'Signature = opaque\nclass Base:'),
    ('class Base:', 'Parameter = opaque\nclass Base:'),
    ('class Base:', 'Parameter.KEYWORD_ONLY = opaque\nclass Base:'),
    ('class Base:', 'expose(Signature)\nclass Base:'),
])
def test_open_or_invalid_signature_inputs_do_not_authorize_creation(tmp_path, old, new):
    source = SOURCE.replace(old, new)
    # One deliberately opaque nested call still needs syntactically valid input.
    if new == 'Signature(opaque([':
        source = source.replace('default=None)])', 'default=None)]))')
    analyzer, _ = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


@pytest.mark.parametrize('tail', [
    'Parameter.KEYWORD_ONLY.__class__.__lt__ = opaque',
    'import inspect\ninspect._ParameterKind.__lt__ = opaque',
    'held = Parameter.KEYWORD_ONLY\nexpose(held.__class__)',
    'expose(Parameter.KEYWORD_ONLY)',
    'saved = [Parameter.KEYWORD_ONLY]\nexpose(saved)',
])
def test_native_signature_protocol_does_not_ignore_visible_kind_mutation(tmp_path, tail):
    analyzer, _ = prepare(tmp_path, SOURCE + tail + '\n')
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_kind_capabilities_in_a_module_without_definitions_are_audited(tmp_path):
    (tmp_path / 'extra.py').write_text('from inspect import Parameter\n'
        'held = Parameter.KEYWORD_ONLY\nexpose(held.__class__)\n', encoding='utf-8')
    analyzer, _ = prepare(tmp_path, 'import extra\n' + SOURCE)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_a_kind_alias_export_is_not_lost_at_an_import_boundary(tmp_path):
    (tmp_path / 'extra.py').write_text('from inspect import Parameter\n'
        'held = Parameter.KEYWORD_ONLY\n', encoding='utf-8')
    source = 'from extra import held\nexpose(held.__class__)\n' + SOURCE
    analyzer, _ = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


MARKER = '''class Marker:
    def __repr__(self): return '<MARKER>'
MARK = Marker()
'''


def test_signature_default_can_retain_a_source_marker_without_invoking_its_methods(tmp_path):
    analyzer, _ = prepare(tmp_path, MARKER + SOURCE.replace('default=None', 'default=MARK'))
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    proof = result.inputs['entry_binding']['class_creation_hooks'][0]['signature_creations'][0]
    default = proof['default_bindings'][0]
    assert default['kind'] == 'source_marker_metadata_default'
    assert default['binding_name'] == 'MARK'
    assert default['allocation']['protocol'] == 'builtin_object_new_and_init_no_arguments'
    assert default['runtime_creation_confirmed'] is False
    assert default['signature_use'] == 'opaque_reference_storage'
    assert proof['value_operations'] == 'storage_only'


@pytest.mark.parametrize('marker', [
    'class Marker:\n    def __init__(self): opaque()\nMARK = Marker()\n',
    'class Marker:\n    def __new__(cls): return opaque()\nMARK = Marker()\n',
    'class Marker(opaque): pass\nMARK = Marker()\n',
    '@opaque\nclass Marker: pass\nMARK = Marker()\n',
    'class Marker(metaclass=opaque): pass\nMARK = Marker()\n',
    'class Marker: pass\nMARK = Marker(opaque)\n',
    'class Marker: pass\nMARK = Marker()\nMARK = opaque\n',
    'class Marker: pass\nMARK = Marker()\nMarker.__new__ = opaque\n',
    'class Marker: pass\nMARK = Marker()\nopaque(Marker)\n',
])
def test_open_marker_allocation_or_binding_does_not_authorize_signature_creation(tmp_path, marker):
    analyzer, _ = prepare(tmp_path, marker + SOURCE.replace('default=None', 'default=MARK'))
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_an_opaque_marker_signature_does_not_acquire_callback_free_equality(tmp_path):
    source = MARKER + SOURCE.replace("cls.signature = Signature([", "if Signature([").replace(
        "default=None)])", "default=MARK)]) == Signature([]):\n            cls.equal = True")
    analyzer, _ = prepare(tmp_path, source)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


@pytest.mark.parametrize('tail', [
    'def query(value): return value is Parameter.KEYWORD_ONLY\n',
    'def query(value): return Parameter.KEYWORD_ONLY is not value\n',
    'def query(value):\n    kind = Parameter.KEYWORD_ONLY\n    return value is kind\n',
])
def test_kind_identity_queries_do_not_expose_the_enum_capability(tmp_path, tail):
    analyzer, _ = prepare(tmp_path, SOURCE + tail)
    assert analyzer.analyze(FunctionRef('example', 'Public')).inputs['entry_binding']['status'] == 'source_bound'


KIND_DECORATOR = '''import inspect
from functools import partial
from inspect import Parameter, Signature

def make_keyword_only(func=None):
    decorator = partial(make_keyword_only)
    if func is None:
        return decorator
    signature = inspect.signature(func)
    POK = Parameter.POSITIONAL_OR_KEYWORD
    KWO = Parameter.KEYWORD_ONLY
    assert signature.parameters['option'].kind == POK
    func.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name == 'option' else param
        for param in signature.parameters.values()])
    return func

@make_keyword_only()
def source_function(self, option):
    pass
'''


def test_native_kind_comparisons_follow_a_fresh_source_signature(tmp_path):
    analyzer, _ = prepare(tmp_path, KIND_DECORATOR + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


def test_native_kind_comparisons_survive_a_stack_of_the_same_signature_decorator(tmp_path):
    source = KIND_DECORATOR.replace('@make_keyword_only()',
        '@make_keyword_only()\n@make_keyword_only()') + SOURCE
    analyzer, _ = prepare(tmp_path, source)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


def test_curried_signature_decorator_can_bind_its_keyword_options(tmp_path):
    source = KIND_DECORATOR.replace(
        'def make_keyword_only(func=None):',
        'def make_keyword_only(func=None, **kwargs):').replace(
        'partial(make_keyword_only)', 'partial(make_keyword_only, **kwargs)')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


def test_curried_signature_factory_can_extract_a_local_keyword_default(tmp_path):
    source = KIND_DECORATOR.replace(
        'def make_keyword_only(func=None):',
        'def make_keyword_only(func=None, **kwargs):').replace(
        'partial(make_keyword_only)', 'partial(make_keyword_only, **kwargs)').replace(
        '    if func is None:', "    addendum = kwargs.pop('addendum', None)\n    if func is None:")
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


def test_curried_signature_decorator_rejects_effects_before_early_return(tmp_path):
    source = KIND_DECORATOR.replace(
        'def make_keyword_only(func=None):',
        'def make_keyword_only(func=None, **kwargs):').replace(
        'partial(make_keyword_only)', 'partial(make_keyword_only, **kwargs)').replace(
        '    if func is None:', '    kwargs.clear()\n    if func is None:')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert not _kind_aliases_closed(analyzer, caller)


def test_signature_source_can_pass_through_a_documentation_only_decorator(tmp_path):
    source = KIND_DECORATOR.replace('@make_keyword_only()\ndef source_function(self, option):',
        'def documentation_only(func):\n'
        '    func.__doc__ = "source documentation"\n'
        '    return func\n\n'
        '@make_keyword_only()\n'
        '@documentation_only\n'
        'def source_function(self, option=(1, 2)):\n')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


def test_signature_source_survives_unresolved_documentation_formatting_on_normal_return(tmp_path):
    source = KIND_DECORATOR.replace('@make_keyword_only()\ndef source_function(self, option):',
        'class Substitution:\n'
        '    def __init__(self): self.params = {}\n'
        '    def __call__(self, func):\n'
        '        if func.__doc__:\n'
        '            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params\n'
        '        return func\n'
        'doc_only = Substitution()\n\n'
        '@make_keyword_only()\n'
        '@doc_only\n'
        'def source_function(self, option):\n'
        '    """%(unknown_documentation)s"""\n')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert _kind_aliases_closed(analyzer, caller)


@pytest.mark.parametrize(('signature_mutation', 'expected'), [
    ('', True),
    ('        func.__signature__ = Signature([])\n', False),
])
def test_signature_source_uses_fresh_function_proof_for_lower_doc_formatter(
        tmp_path, monkeypatch, signature_mutation, expected):
    source = KIND_DECORATOR.replace('@make_keyword_only()\ndef source_function(self, option):',
        'class Cache(dict):\n'
        '    def __missing__(self, key): return "formatted"\n'
        'class Substitution:\n'
        '    def __init__(self): self.params = Cache()\n'
        '    def __call__(self, func):\n'
        '        if func.__doc__:\n'
        '            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params\n'
        '        return func\n'
        'class ArtistPropertiesSubstitution(Substitution):\n'
        '    def __call__(self, obj):\n'
        '        super().__call__(obj)\n'
        '        if isinstance(obj, type) and obj.__init__ != object.__init__:\n'
        '            self(obj.__init__)\n'
        '        return obj\n'
        'documentation = ArtistPropertiesSubstitution()\n\n'
        '@make_keyword_only()\n'
        '@documentation\n'
        'def source_function(self, option):\n'
        '    """Documentation for %(unresolved)s."""\n')
    if signature_mutation:
        source = source.replace('        return func\n', signature_mutation + '        return func\n')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._decorator_effects import _DecoratorEffects
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    original_fact = _DecoratorEffects.fact

    def unresolved_ordinary_effect(self, expression, *args, **kwargs):
        fact = original_fact(self, expression, *args, **kwargs)
        if (type(self) is _DecoratorEffects and isinstance(expression, ast.Name)
                and expression.id == 'documentation'):
            fact['boundaries'].append({'reason': 'decorator_call_unresolved',
                'evidence': {'lineno': expression.lineno}})
        return fact

    monkeypatch.setattr(_DecoratorEffects, 'fact', unresolved_ordinary_effect)
    evidence = []
    assert _kind_aliases_closed(analyzer, caller, evidence) is expected
    if expected:
        assert len(evidence) == 1
        assert evidence[0]['freshness']['function']['qualname'] == 'source_function'
        assert evidence[0]['identity_status'] == 'preserved'
        assert evidence[0]['body_binding_status'] == 'preserved'
        assert evidence[0]['boundaries'] == []
        assert _kind_aliases_closed(analyzer, caller, evidence) is True
        assert len(evidence) == 1
    else:
        assert evidence == []


@pytest.mark.parametrize('failure_kind', ['open_alias', 'budget'])
def test_late_kind_alias_failure_does_not_publish_staged_decorator_evidence(
        tmp_path, monkeypatch, failure_kind):
    source = KIND_DECORATOR.replace('@make_keyword_only()\ndef source_function(self, option):',
        'class Cache(dict):\n'
        '    def __missing__(self, key): return "formatted"\n'
        'class Substitution:\n'
        '    def __init__(self): self.params = Cache()\n'
        '    def __call__(self, func):\n'
        '        if func.__doc__:\n'
        '            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params\n'
        '        return func\n'
        'class ArtistPropertiesSubstitution(Substitution):\n'
        '    def __call__(self, obj):\n'
        '        super().__call__(obj)\n'
        '        if isinstance(obj, type) and obj.__init__ != object.__init__:\n'
        '            self(obj.__init__)\n'
        '        return obj\n'
        'documentation = ArtistPropertiesSubstitution()\n\n'
        '@make_keyword_only()\n'
        '@documentation\n'
        'def source_function(self, option):\n'
        '    """Documentation for %(unresolved)s."""\n')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs.callables.decorators._decorator_effects import _DecoratorEffects
    import pcresolve.flow.proofs.namespaces.metadata._metadata_signature as metadata_signature
    original_fact = _DecoratorEffects.fact

    def unresolved_ordinary_effect(self, expression, *args, **kwargs):
        fact = original_fact(self, expression, *args, **kwargs)
        if (type(self) is _DecoratorEffects and isinstance(expression, ast.Name)
                and expression.id == 'documentation'):
            fact['boundaries'].append({'reason': 'decorator_call_unresolved',
                'evidence': {'lineno': expression.lineno}})
        return fact

    monkeypatch.setattr(_DecoratorEffects, 'fact', unresolved_ordinary_effect)

    def fail_after_local_proof(*args):
        if failure_kind == 'budget':
            from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
            raise _ClassEffectLimit()
        return False

    monkeypatch.setattr(metadata_signature, 'imported_kind_aliases_are_closed', fail_after_local_proof)
    evidence = []
    if failure_kind == 'budget':
        from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
        with pytest.raises(_ClassEffectLimit):
            metadata_signature._kind_aliases_closed(analyzer, caller, evidence)
    else:
        assert not metadata_signature._kind_aliases_closed(analyzer, caller, evidence)
    assert evidence == []


def test_kind_comparisons_do_not_accept_a_replaced_input_signature(tmp_path):
    source = KIND_DECORATOR.replace('@make_keyword_only()',
        '@make_keyword_only()\n@custom_signature').replace(
        '@make_keyword_only()', '@make_keyword_only()')
    source = source.replace('def make_keyword_only(func=None):',
        'def custom_signature(func):\n    func.__signature__ = Signature([])\n    return func\n\n'
        'def make_keyword_only(func=None):')
    analyzer, _ = prepare(tmp_path, source + SOURCE)
    analyzer._index()
    caller = analyzer._definition_index.find('example', 'Base.__init_subclass__')[0][0]
    from pcresolve.flow.proofs._metadata_signature import _kind_aliases_closed
    assert not _kind_aliases_closed(analyzer, caller)


@pytest.mark.parametrize('tail', [
    'def query(value): return value == Parameter.KEYWORD_ONLY\n',
    'def query(value):\n    kind = Parameter.KEYWORD_ONLY\n    return kind < value\n',
    'def query(value): return value is expose(Parameter.KEYWORD_ONLY)\n',
    'def query(value): return value is Parameter.KEYWORD_ONLY.__class__\n',
])
def test_nonidentity_kind_operations_and_nested_exposures_remain_open(tmp_path, tail):
    analyzer, _ = prepare(tmp_path, SOURCE + tail)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))
