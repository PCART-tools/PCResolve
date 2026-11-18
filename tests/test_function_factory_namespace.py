## @package tests.test_function_factory_namespace

import ast

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs._class_definition import namespace_issues
from pcresolve.flow.proofs._constructor_entry import binding as constructor_binding
from pcresolve.flow.proofs._function_factory import factory_wrapper


SOURCE = '''import functools
import inspect
REGISTRY = {}
def decorate(version, name, fn=None):
    decorator = functools.partial(decorate, version, name)
    if fn is None:
        return decorator
    signature = inspect.signature(fn)
    POK = inspect.Parameter.POSITIONAL_OR_KEYWORD
    KWO = inspect.Parameter.KEYWORD_ONLY
    assert name in signature.parameters and signature.parameters[name].kind == POK, (
        f'invalid parameter {name!r} for {fn.__name__}')
    names = [*signature.parameters]
    name_idx = names.index(name)
    kwonly = [name for name in names[name_idx:]
              if signature.parameters[name].kind == POK]
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if len(args) > name_idx:
            opaque(version, fn)
        return fn(*args, **kwargs)
    wrapper.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name in kwonly else param
        for param in signature.parameters.values()])
    REGISTRY[wrapper] = decorator
    return wrapper
class Public:
    def __init__(self, **kwargs): pass
    @decorate('1.0', name='value')
    def method(self, value=None, *, exact=True, **kwargs): return value
'''


def prepare(root, text=SOURCE):
    (root / 'example.py').write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, analyzer._definition_index.find('example', 'Public.method')[0]


def test_factory_signature_operations_construct_a_native_wrapper_without_running_it(tmp_path):
    analyzer, target = prepare(tmp_path)
    fact = factory_wrapper(analyzer, target)
    assert fact['result_kind'] == 'native_function'
    assert fact['body_binding_status'] == 'unmodeled'
    assert fact['runtime_factory_executed'] is False
    assert fact['forwarding']['maximum_positional_count'] == 1
    assert fact['forwarding']['forwarded_function'] == fact['function']
    assert fact['forwarding']['other_paths'] == 'forwarded_on_normal_return'
    assert fact['forwarding']['normal_return_paths'] == (
        'all_explicit_returns_forward_original_args_kwargs')
    assert fact['registry_writes'][0]['object_kind'] == 'source_builtin_dict'
    assert not namespace_issues(analyzer, analyzer._class_mro('example', 'Public'),
                                assumptions=set())


def test_constructor_entry_uses_exact_source_wrapper_argument_forwarding(tmp_path):
    source = SOURCE.replace(
        'class Public:\n    def __init__(self, **kwargs): pass',
        "class Public:\n    @decorate('1.0', name='value')\n"
        '    def __init__(self, value=None, **kwargs): pass')
    (tmp_path / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    cls = next((ref, node) for ref, node in analyzer.classes if ref.qualname == 'Public')
    target = analyzer._constructor_target(cls)

    fact = constructor_binding(analyzer, cls, target)

    assert fact['status'] == 'source_bound'
    forwarding = fact['constructor_wrapper_forwarding']['forwarding']
    assert forwarding['forwarded_function'] == fact['target']
    assert forwarding['argument_scope'] == 'same_args_and_kwargs'


@pytest.mark.parametrize('old,new', [
    ('signature = inspect.signature(fn)', 'signature = opaque(fn)'),
    ('signature = inspect.signature(fn)', 'signature = inspect.signature(opaque)'),
    ('REGISTRY = {}', 'REGISTRY = opaque'),
    ('REGISTRY[wrapper] = decorator', 'opaque(wrapper)'),
    ('REGISTRY[wrapper] = decorator', 'REGISTRY[opaque] = decorator'),
    ('REGISTRY[wrapper] = decorator', 'fn.__code__ = opaque'),
    ('return wrapper', 'return opaque'),
    ('name=\'value\'', 'name=opaque()'),
    ('name=\'value\'', 'name=\'missing\''),
    ('@functools.wraps(fn)', '@opaque'),
    ('def wrapper(*args, **kwargs):', 'def wrapper(*args, value=opaque(), **kwargs):'),
    ('    return wrapper', '    global bad\n    return wrapper'),
])
def test_unsupported_immediate_effects_or_arguments_stay_open(tmp_path, old, new):
    analyzer, target = prepare(tmp_path, SOURCE.replace(old, new))
    assert factory_wrapper(analyzer, target) is None


@pytest.mark.parametrize('tail', [
    'inspect.signature = opaque',
    'functools.partial = opaque',
    'REGISTRY = opaque',
    'saved = REGISTRY\nopaque(saved)',
    'decorate.__code__ = opaque',
    'opaque(inspect)',
    'saved = inspect.signature\nopaque(saved)',
    'saved = inspect\nopaque(saved)',
    "__import__('inspect').signature = opaque",
])
def test_namespace_mutation_and_escaped_registry_invalidate_construction(tmp_path, tail):
    analyzer, target = prepare(tmp_path, SOURCE + '\n' + tail + '\n')
    assert factory_wrapper(analyzer, target) is None


def test_an_arbitrary_wrapper_body_only_loses_the_forwarding_claim(tmp_path):
    text = SOURCE.replace('return fn(*args, **kwargs)', 'return opaque(fn, args, kwargs)')
    analyzer, target = prepare(tmp_path, text)
    fact = factory_wrapper(analyzer, target)
    assert fact is not None and 'forwarding' not in fact


def test_forwarding_uses_the_final_closure_cell_value(tmp_path):
    text = SOURCE.replace('    REGISTRY[wrapper]', '    name_idx = 0\n    REGISTRY[wrapper]')
    analyzer, target = prepare(tmp_path, text)
    assert factory_wrapper(analyzer, target)['forwarding']['maximum_positional_count'] == 0


def test_both_normal_wrapper_branches_forward_unchanged_arguments(tmp_path):
    text = SOURCE.replace(
        '        if len(args) > name_idx:\n            opaque(version, fn)\n',
        "        if len(args) <= name_idx and 'value' not in kwargs:\n"
        '            return fn(*args, **kwargs)\n'
        '        if len(args) > name_idx:\n            opaque(version, fn)\n')
    analyzer, target = prepare(tmp_path, text)
    fact = factory_wrapper(analyzer, target)
    assert fact is not None
    assert fact['forwarding']['normal_return_paths'] == (
        'all_explicit_returns_forward_original_args_kwargs')


def test_mutating_forwarded_kwargs_disables_the_forwarding_claim(tmp_path):
    text = SOURCE.replace(
        '        if len(args) > name_idx:\n            opaque(version, fn)\n',
        "        kwargs['value'] = None\n"
        '        if len(args) > name_idx:\n            opaque(version, fn)\n')
    analyzer, target = prepare(tmp_path, text)
    fact = factory_wrapper(analyzer, target)
    assert fact is not None and 'forwarding' not in fact


@pytest.mark.parametrize('old,new', [
    ('*args, **kwargs', '*fn, **kwargs'),
    ('len(args) > name_idx', 'len(args) > args'),
    ('    signature = inspect.signature(fn)', '    len = 0\n    signature = inspect.signature(fn)'),
])
def test_shadowed_wrapper_or_closure_names_cannot_be_a_forwarding_proof(tmp_path, old, new):
    analyzer, target = prepare(tmp_path, SOURCE.replace(old, new))
    fact = factory_wrapper(analyzer, target)
    assert fact is None or 'forwarding' not in fact


def test_runtime_lookup_cannot_reuse_a_rebound_inspect_module_alias(tmp_path):
    analyzer, target = prepare(tmp_path, SOURCE + '\ninspect = opaque\n')
    assert factory_wrapper(analyzer, target) is None


def test_a_previous_wrapper_invocation_cannot_change_a_captured_forwarding_target(tmp_path):
    text = SOURCE.replace('        if len(args)', '        nonlocal fn\n        if len(args)')
    text = text.replace('            opaque(version, fn)', '            fn = replacement')
    analyzer, target = prepare(tmp_path, text)
    fact = factory_wrapper(analyzer, target)
    assert fact is None or 'forwarding' not in fact


def test_visible_closure_cell_mutation_invalidates_function_metadata_assumptions(tmp_path):
    analyzer, target = prepare(tmp_path, SOURCE + '\nsaved.cell_contents = opaque\n')
    assert factory_wrapper(analyzer, target) is None


def test_fact_caches_refresh_on_source_changes(tmp_path):
    analyzer, target = prepare(tmp_path)
    assert factory_wrapper(analyzer, target)
    (tmp_path / 'patch.py').write_text('import inspect\ninspect.signature = opaque\n')
    analyzer.add_files([tmp_path / 'patch.py'])
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Public.method')[0]
    assert factory_wrapper(analyzer, target) is None


def test_function_summary_publishes_conditional_forwarding_without_body_identity(tmp_path):
    analyzer, target = prepare(tmp_path)
    result = analyzer.analyze(FunctionRef('example', 'Public.method'))
    summary = next(item for item in result.functions if item['function']['qualname'] == 'Public.method')
    fact, = summary['source_wrapper_forwarding']
    assert fact['function']['qualname'] == 'Public.method'
    assert fact['forwarding']['maximum_positional_count'] == 1
    assert fact['body_binding_status'] == 'unmodeled'
    assert any(item['reason'] == 'decorator_effect_unconfirmed' for item in result.boundaries)


def test_wrapper_calls_keep_a_nominal_target_and_an_effect_boundary(tmp_path):
    text = SOURCE.replace('class Public:', '''@decorate('1.0', name='value')
def public(value=None, **kwargs): return kwargs
def client(**kwargs): return public(**kwargs)
class Public:''')
    analyzer, _ = prepare(tmp_path, text)
    result = analyzer.analyze(FunctionRef('example', 'client'))
    call, = result.find_calls(callee_name='public')
    assert call.target.qualname == 'public'
    assert any(item.get('call_id') == call.id and item['reason']
               == 'identity_decorator_effects_unmodeled' for item in result.boundaries)


def test_lambda_summaries_do_not_request_decorator_attributes(tmp_path):
    analyzer, target = prepare(tmp_path)
    assert factory_wrapper(analyzer, (target[0], ast.parse('lambda value: value').body[0].value)) is None
