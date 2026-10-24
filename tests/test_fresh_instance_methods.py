## @package tests.test_fresh_instance_methods

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow import FlowAnalysis
from pcresolve._function_factory import factory_wrapper


SOURCE = (Path(__file__).parent / 'fixtures' / 'value_flow_fresh_instance_methods'
          / 'sample.py').read_text(encoding='utf-8')


def analyze(root, text=SOURCE, entry='Box', depth=1):
    path = root / 'sample.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    try:
        result = analyzer.analyze(FunctionRef('sample', entry), max_depth=depth)
    except ValueError as exc:
        if str(exc) != 'Entry must identify exactly one available definition':
            raise
        result = None
    return analyzer, result, path


def method_fact(result):
    if result is None:
        return None
    calls = result.find_calls(callee_name='self.update')
    if len(calls) != 1:
        return None
    facts = getattr(calls[0], 'instance_method_bindings', [])
    return facts[0] if len(facts) == 1 else None


def test_source_class_entry_can_bind_a_fresh_receiver_method(tmp_path):
    _, result, path = analyze(tmp_path)
    fact = method_fact(result)
    assert fact is not None and fact['status'] == 'source_bound'
    assert fact['target']['qualname'] == 'Base.update'
    assert fact['receiver_class']['qualname'] == 'Box'
    assert fact['runtime_target_confirmed'] is False
    assert fact['instance_state'] == 'lookup_prefix_only'
    assert fact['origin']['allocation']['kind'] == 'builtin_object_new'
    assert fact['origin']['allocation'] == result.inputs['entry_binding'][
        'fresh_receiver_origin']['allocation']
    assert fact['source_hashes'] == result.inputs['sha256']
    runtime = runpy.run_path(str(path))
    assert runtime['Box'](allowed=1).allowed == 1
    with pytest.raises(AttributeError, match='old'):
        runtime['Box'](old=1)


def test_selected_expansion_reuses_same_snapshot_class_binding_facts(tmp_path):
    analyzer, result, _ = analyze(tmp_path)
    assert result is not None
    update = result.find_calls(callee_name='self.update')[0]
    cached_writes = analyzer._class_binding_write_cache
    assert cached_writes is not None

    expanded = analyzer.expand(result, update.id)

    assert analyzer._class_binding_write_cache is cached_writes
    assert expanded.find_calls(callee_name='self.update')[0].instance_method_bindings[
        0]['status'] == 'source_bound'


def test_fresh_receiver_origin_flows_through_a_proven_super_initializer(tmp_path):
    source = SOURCE.replace('class Base:\n',
        'class Base:\n    def __init__(self, **kwargs):\n        self.update(kwargs)\n\n')
    source = source.replace('class Box(Base):\n    def __init__(self, **kwargs):\n        self.update(kwargs)',
        'class Box(Base):\n    def __init__(self, **kwargs):\n        super().__init__(**kwargs)')
    _, result, _ = analyze(tmp_path, source, depth=3)
    assert result is not None
    super_call = result.find_calls(callee_name='super().__init__')[0]
    binding = super_call.instance_method_bindings[0]
    assert binding['kind'] == 'fresh_source_super_method'
    assert binding['target']['qualname'] == 'Base.__init__'
    assert binding['origin'] == result.inputs['entry_binding']['fresh_receiver_origin']
    update = result.find_calls(callee_name='self.update')[0]
    assert update.instance_method_bindings[0]['status'] == 'source_bound'
    assert update.instance_method_bindings[0]['origin']['path'] == [super_call.id]


def test_fresh_receiver_origin_survives_bounded_setdefault_on_captured_kwargs(tmp_path):
    source = '''class Base:
    def __init__(self, **kwargs):
        self.update(kwargs)
    def update(self, props):
        self.ready = True
class Box(Base):
    def __init__(self, **kwargs):
        kwargs.setdefault('joinstyle', 'round')
        kwargs.setdefault('capstyle', 'round')
        super().__init__(**kwargs)
'''
    _, result, _ = analyze(tmp_path, source, depth=3)
    assert result is not None
    super_call = result.find_calls(callee_name='super().__init__')[0]
    assert super_call.instance_method_bindings[0]['kind'] == 'fresh_source_super_method'
    update = result.find_calls(callee_name='self.update')[0]
    assert update.instance_method_bindings[0]['status'] == 'source_bound'
    assert update.instance_method_bindings[0]['origin']['path'] == [super_call.id]


def test_matplotlib_keyword_only_decorator_proves_original_argument_forwarding(tmp_path):
    package = tmp_path / 'matplotlib'
    api = package / '_api'
    api.mkdir(parents=True)
    (package / '__init__.py').write_text('', encoding='utf-8')
    (api / '__init__.py').write_text(
        'from .deprecation import make_keyword_only\n', encoding='utf-8')
    (api / 'deprecation.py').write_text('''import functools
import inspect
DECORATORS = {}
def warn_deprecated(*args, **kwargs): pass
def make_keyword_only(since, name, func=None):
    """Apply a keyword-only warning wrapper."""
    decorator = functools.partial(make_keyword_only, since, name)
    if func is None:
        return decorator
    signature = inspect.signature(func)
    POK = inspect.Parameter.POSITIONAL_OR_KEYWORD
    KWO = inspect.Parameter.KEYWORD_ONLY
    assert name in signature.parameters and signature.parameters[name].kind == POK
    names = [*signature.parameters]
    name_idx = names.index(name)
    kwonly = [name for name in names[name_idx:]
              if signature.parameters[name].kind == POK]
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > name_idx:
            warn_deprecated(since, name=name)
        return func(*args, **kwargs)
    wrapper.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name in kwonly else param
        for param in signature.parameters.values()])
    DECORATORS[wrapper] = decorator
    return wrapper
''', encoding='utf-8')
    (package / 'patches.py').write_text('''from . import _api
class Artist:
    def update(self, props):
        pass
class Patch(Artist):
    @_api.make_keyword_only("3.6", name="edgecolor")
    def __init__(self, edgecolor=None, **kwargs):
        self.update(kwargs)
class Fancy(Patch):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef('matplotlib.patches', 'Fancy'), max_depth=3)
    target, = analyzer._definition_index.find('matplotlib.patches', 'Patch.__init__')
    fact = factory_wrapper(analyzer, target)
    assert fact is not None
    assert fact['kind'] == 'source_matplotlib_keyword_only_wrapper'
    assert fact['forwarding']['argument_scope'] == 'same_args_and_kwargs'
    assert fact['forwarding']['normal_return_paths'] == (
        'all_explicit_returns_forward_original_args_kwargs')
    super_call = result.find_calls(callee_name='super().__init__')[0]
    assert super_call.instance_method_bindings[0]['kind'] == 'fresh_source_super_method'
    update = result.find_calls(callee_name='self.update')[0]
    assert update.instance_method_bindings[0]['status'] == 'source_bound'
    assert update.instance_method_bindings[0]['origin']['path'] == [super_call.id]


def test_fresh_receiver_crosses_matplotlib_docstring_keyword_only_super_chain(tmp_path):
    package = tmp_path / 'matplotlib'
    api = package / '_api'
    api.mkdir(parents=True)
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / '_docstring.py').write_text('''import inspect
class Substitution:
    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
        return func
class _ArtistPropertiesSubstitution(Substitution):
    def __call__(self, obj):
        super().__call__(obj)
        if isinstance(obj, type) and obj.__init__ != object.__init__:
            self(obj.__init__)
        return obj
dedent_interpd = interpd = _ArtistPropertiesSubstitution()
''', encoding='utf-8')
    (api / '__init__.py').write_text(
        'from .deprecation import make_keyword_only\n', encoding='utf-8')
    (api / 'deprecation.py').write_text('''import functools
import inspect
DECORATORS = {}
def warn_deprecated(*args, **kwargs): pass
def make_keyword_only(since, name, func=None):
    decorator = functools.partial(make_keyword_only, since, name)
    if func is None:
        return decorator
    signature = inspect.signature(func)
    POK = inspect.Parameter.POSITIONAL_OR_KEYWORD
    KWO = inspect.Parameter.KEYWORD_ONLY
    assert name in signature.parameters and signature.parameters[name].kind == POK
    names = [*signature.parameters]
    name_idx = names.index(name)
    kwonly = [name for name in names[name_idx:]
              if signature.parameters[name].kind == POK]
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > name_idx:
            warn_deprecated(since, name=name)
        return func(*args, **kwargs)
    wrapper.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name in kwonly else param
        for param in signature.parameters.values()])
    DECORATORS[wrapper] = decorator
    return wrapper
''', encoding='utf-8')
    (package / '_enums.py').write_text('''from enum import Enum, auto
class _AutoStringNameEnum(Enum): pass
class JoinStyle(str, _AutoStringNameEnum):
    round = auto()
class CapStyle(str, _AutoStringNameEnum):
    round = auto()
''', encoding='utf-8')
    (package / 'patches.py').write_text('''from . import _api, _docstring
from ._enums import JoinStyle, CapStyle
class Artist:
    def update(self, props):
        for key, value in props.items():
            setter = getattr(self, f'set_{key}', None)
            if not callable(setter):
                raise AttributeError(key)
            setter(value)
    def set_allowed(self, value): pass
class Patch(Artist):
    @_api.make_keyword_only("3.6", name="edgecolor")
    def __init__(self, edgecolor=None, **kwargs):
        self.update(kwargs)
class Fancy(Patch):
    @_docstring.dedent_interpd
    @_api.make_keyword_only("3.6", name="path")
    def __init__(self, path=None, **kwargs):
        kwargs.setdefault("joinstyle", JoinStyle.round)
        kwargs.setdefault("capstyle", CapStyle.round)
        super().__init__(**kwargs)
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef('matplotlib.patches', 'Fancy'), max_depth=3)
    assert result is not None
    super_calls = result.find_calls(callee_name='super().__init__')
    assert super_calls, (result.inputs.get('entry_binding'), result.functions)
    super_call = super_calls[0]
    assert len(super_call.instance_method_bindings) == 1
    assert super_call.instance_method_bindings[0]['kind'] == 'fresh_source_super_method'
    update = result.find_calls(callee_name='self.update')[0]
    assert update.instance_method_bindings[0]['status'] == 'source_bound'
    summaries = [item for item in result.functions
                 if item['function']['qualname'] == 'Artist.update']
    assert len(summaries) == 1
    checks = summaries[0].get('fresh_mapping_member_checks', [])
    assert len(checks) == 1
    assert 'set_allowed' in checks[0]['member_names']


def test_fresh_receiver_origin_flows_through_nested_instance_methods(tmp_path):
    source = '''class Base:
    def __init__(self, **kwargs):
        self.update(kwargs)
    def update(self, props):
        self.apply(props)
    def apply(self, props):
        self.ready = True
class Box(Base):
    pass
'''
    _, result, _ = analyze(tmp_path, source, depth=3)
    assert result is not None
    update = result.find_calls(callee_name='self.update')[0]
    apply = result.find_calls(callee_name='self.apply')[0]
    assert update.instance_method_bindings[0]['status'] == 'source_bound'
    assert apply.instance_method_bindings[0]['status'] == 'source_bound'
    assert apply.instance_method_bindings[0]['origin']['current_function']['qualname'] == 'Base.update'
    assert apply.instance_method_bindings[0]['origin']['path'] == [update.id]


def test_incoming_instance_binding_uses_the_exact_receiver_witness(tmp_path):
    source = '''class Base:
    def __init__(self):
        self.update()
    def update(self):
        pass
class Box(Base):
    pass
'''
    analyzer, result, _ = analyze(tmp_path, source)
    update = result.find_calls(callee_name='self.update')[0]
    receiver_arguments = [item for item in update.argument_sources
                          if item.get('argument') == {'receiver': True}]
    assert len(receiver_arguments) == 1
    # The separate receiver witness remains exact even if generic argument
    # projection has lost the instance type while expanding this call.
    for value in receiver_arguments[0]['sources']:
        value.pop('instance_type', None)
    update.receiver_sources[0]['value_incomplete'] = True
    target, = analyzer._definition_index.find('sample', 'Base.update')
    incoming = analyzer._incoming_facts(target, update)
    assert 'self' in incoming, {
        'receiver_sources': [(item.get('source'), item.get('relation'),
            item.get('instance_type'), item.get('value_incomplete'),
            item.get('fresh_receiver_origin') == update.instance_method_bindings[0].get('origin'))
            for item in update.receiver_sources],
        'binding': [(item.get('kind'), item.get('status'), item.get('target'),
            item.get('call_id') == update.id, item.get('receiver_class'))
            for item in update.instance_method_bindings],
        'parameters': [(item.get('argument'), item.get('parameter'), item.get('status'))
            for item in update.parameter_bindings],
        'binding_status': update.binding_status,
        'target_status': update.target_status}
    assert incoming['self'][0]['fresh_receiver_origin']['current_function']['qualname'] == 'Base.update'
    assert incoming['self'][0]['instance_type']['qualname'] == 'Box'


def test_fresh_receiver_origin_crosses_an_exactly_forwarding_super_wrapper(tmp_path):
    source = '''import functools
import inspect
REGISTRY = {}
def decorate(version, name, func=None):
    decorator = functools.partial(decorate, version, name)
    if func is None:
        return decorator
    signature = inspect.signature(func)
    POK = inspect.Parameter.POSITIONAL_OR_KEYWORD
    KWO = inspect.Parameter.KEYWORD_ONLY
    assert name in signature.parameters and signature.parameters[name].kind == POK
    names = [*signature.parameters]
    index = names.index(name)
    kwonly = [name for name in names[index:]
              if signature.parameters[name].kind == POK]
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > index:
            opaque(version, func)
        return func(*args, **kwargs)
    wrapper.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name in kwonly else param
        for param in signature.parameters.values()])
    REGISTRY[wrapper] = decorator
    return wrapper
class Base:
    @decorate('1.0', name='value')
    def __init__(self, value=None, **kwargs):
        self.update(kwargs)
    def update(self, props):
        pass
class Child(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
'''
    analyzer, result, _ = analyze(tmp_path, source, entry='Child', depth=3)
    assert result is not None
    super_calls = result.find_calls(callee_name='super().__init__')
    assert len(super_calls) == 1, (result.inputs.get('entry_binding'), result.boundaries)
    super_call = super_calls[0]
    binding = super_call.instance_method_bindings[0]
    assert binding['kind'] == 'fresh_source_super_method'
    assert binding['descriptor'] == 'source_function_wrapper'
    assert binding['wrapper_forwarding']['forwarded_function']['qualname'] == 'Base.__init__'
    assert any(item.get('argument') == {'receiver': True}
               and item.get('parameter') == 'self' and item.get('status') == 'exact'
               for item in super_call.parameter_bindings)
    update = result.find_calls(callee_name='self.update')[0]
    selected = next(item for item in analyzer._definition_index.find('sample', 'Base.__init__'))
    incoming = analyzer._incoming_facts(selected, super_call)
    assert selected[0].__dict__ == binding['target']
    assert 'self' in incoming, incoming
    assert update.receiver_sources[0].get('fresh_receiver_origin', {}).get(
        'current_function', {}).get('qualname') == 'Base.__init__'
    assert update.instance_method_bindings[0]['status'] == 'source_bound'


def test_fresh_method_lookup_accepts_a_narrow_property_assignment_try(tmp_path):
    source = '''class Base:
    def __init__(self):
        self.callback = None
        try:
            self.axes = None
        except AttributeError:
            pass
        self.update()
    @property
    def axes(self):
        return self._axes
    @axes.setter
    def axes(self, value):
        self._axes = value
    def update(self):
        self.ready = True
class Box(Base):
    pass
'''
    _, result, _ = analyze(tmp_path, source, depth=1)
    assert result is not None
    update = result.find_calls(callee_name='self.update')[0]
    assert update.target_status in ('instance_method', 'receiver_type_evidence')
    assert update.instance_method_bindings[0]['kind'] == 'fresh_source_instance_method'


def test_fresh_method_lookup_rejects_a_property_setter_that_shadows_the_method(tmp_path):
    source = '''class Base:
    def __init__(self):
        self.callback = None
        try:
            self.axes = None
        except AttributeError:
            pass
        self.update()
    @property
    def axes(self):
        return self._axes
    @axes.setter
    def axes(self, value):
        self.update = value
    def update(self):
        self.ready = True
class Box(Base):
    pass
'''
    _, result, _ = analyze(tmp_path, source, depth=1)
    assert result is not None
    update = result.find_calls(callee_name='self.update')[0]
    assert update.target_status == 'receiver_unresolved'
    assert not update.instance_method_bindings


@pytest.mark.parametrize(('prefix', 'bound'), [
    ('if len(kwargs):\n            self.update(kwargs)', True),
    ('opaque(self)\n        if len(kwargs):\n            self.update(kwargs)', False),
    ('self.update = opaque\n        if len(kwargs):\n            self.update(kwargs)', False),
])
def test_lookup_prefix_tracks_receiver_effects_before_a_conditional_call(tmp_path, prefix, bound):
    source = '''class Box:
    def __init__(self, **kwargs):
        PREFIX
    def update(self, props): pass
'''.replace('PREFIX', prefix)
    _, result, _ = analyze(tmp_path, source)
    call = result.find_calls(callee_name='self.update')[-1]
    assert bool(call.instance_method_bindings) is bound


@pytest.mark.parametrize('owner', ['Base', 'Box'])
def test_bounded_class_decoration_preserves_an_unwritten_method(tmp_path, owner):
    text = 'def decorate(cls):\n    cls.label = True\n    return cls\n' + SOURCE
    text = text.replace('class ' + owner, '@decorate\nclass ' + owner)
    _, result, path = analyze(tmp_path, text)
    fact = method_fact(result)
    assert fact is not None and fact['target']['qualname'] == 'Base.update'
    allocation = fact['origin']['allocation']
    assert allocation['class_decorations'] == result.inputs['entry_binding']['class_decorations']
    assert allocation['class_decorations'][0]['attributes'] == ['label']
    assert set(result.inputs['entry_binding']['assumptions']).issubset(allocation['assumptions'])
    with pytest.raises(AttributeError, match='old'):
        runpy.run_path(str(path))['Box'](old=1)


@pytest.mark.parametrize('slot', ['update', 'ready'])
def test_decorator_writes_do_not_license_old_members_or_plain_instance_stores(tmp_path, slot):
    text = ('def decorate(cls):\n    cls.' + slot + ' = opaque\n    return cls\n' + SOURCE)
    text = text.replace('class Base:', '@decorate\nclass Base:')
    if slot == 'ready':
        text = text.replace('self.update(kwargs)', 'self.ready = True\n        self.update(kwargs)')
    _, result, _ = analyze(tmp_path, text)
    assert method_fact(result) is None


def test_decorator_added_names_participate_in_missing_setter_checks(tmp_path):
    text = ('def decorate(cls):\n    cls.set_injected = opaque\n    return cls\n' + SOURCE)
    text = text.replace('class Base:', '@decorate\nclass Base:')
    _, result, _ = analyze(tmp_path, text, depth=2)
    assert method_fact(result) is not None
    checks = [check for function in result.functions
              for check in function.get('fresh_mapping_member_checks', [])]
    assert len(checks) == 1 and 'set_injected' in checks[0]['member_names']
    assert 'set_injected' not in checks[0]['value_stores']


def test_decorator_added_descriptor_can_replace_a_later_instance_method(tmp_path):
    text = '''class Descriptor:
    def __set__(self, receiver, value):
        receiver.update = lambda props: None
descriptor = Descriptor()
def decorate(cls):
    cls.ready = descriptor
    return cls
''' + SOURCE
    text = text.replace('class Base:', '@decorate\nclass Base:')
    text = text.replace('self.update(kwargs)', 'self.ready = True\n        self.update(kwargs)')
    _, result, path = analyze(tmp_path, text)
    assert method_fact(result) is None
    # The old source checker would reject this key, but the descriptor changes
    # the instance method before lookup. A plain-store proof would be false.
    assert runpy.run_path(str(path))['Box'](old=1) is not None


def test_method_queries_do_not_invent_a_fresh_allocation(tmp_path):
    _, result, _ = analyze(tmp_path, entry='Box.__init__')
    assert method_fact(result) is None


def test_plain_new_dictionary_stores_preserve_other_method_lookups(tmp_path):
    text = SOURCE.replace('self.update(kwargs)', 'self.ready = True\n        self.update(kwargs)')
    _, result, _ = analyze(tmp_path, text)
    fact = method_fact(result)
    assert fact is not None and fact['status'] == 'source_bound'
    assert fact['own_attributes'] == ['ready']


@pytest.mark.parametrize('prefix', [
    'opaque(self)', 'opaque()', 'self.update = opaque', 'alias = self',
    'self.__dict__["update"] = opaque', 'self.__class__ = opaque',
    'if opaque:\n            self.ready = True',
])
def test_open_prefixes_do_not_establish_method_binding(tmp_path, prefix):
    text = SOURCE.replace('self.update(kwargs)', prefix + '\n        self.update(kwargs)')
    _, result, _ = analyze(tmp_path, text)
    assert method_fact(result) is None


@pytest.mark.parametrize('extra', [
    '\nopaque(Box)\n', '\nBox.update = opaque\n', '\nBase.update.__code__ = opaque\n',
    '\nimport sys\nsys.settrace(opaque)\n',
    '\nfrom sys import settrace as trace\ntrace(opaque)\n',
])
def test_class_mutation_escape_and_frame_hooks_prevent_a_binding(tmp_path, extra):
    _, result, _ = analyze(tmp_path, SOURCE + extra)
    assert method_fact(result) is None


FRAME_METADATA = '''
import sys
def location():
    frame = sys._getframe()
    while frame:
        module = frame.f_globals.get('__name__', '')
        line = frame.f_lineno
        frame = frame.f_back
    return module, line
'''


def test_readonly_frame_metadata_can_preserve_fresh_instance_lookup(tmp_path):
    _, result, _ = analyze(tmp_path, SOURCE + FRAME_METADATA)
    fact = method_fact(result)
    assert fact is not None
    allocation = fact['origin']['allocation']
    assert allocation['frame_observation'] == 'native_metadata_only'
    guard = allocation['observation_guard']
    assert guard['source_hashes'] == result.inputs['sha256']
    assert guard['frame_metadata'][0]['function']['qualname'] == 'location'
    assert set(guard['assumptions']).issubset(allocation['assumptions'])
    assert set(guard['assumptions']).issubset(fact['assumptions'])


def test_a_native_stack_walk_also_requires_its_complete_metadata_guard(tmp_path):
    extra = '''
import traceback
def location():
    for frame, line in traceback.walk_stack(None):
        if frame is None: break
        module = frame.f_globals.get('__name__', '')
        name = frame.f_code.co_name
    return module, line, name
'''
    _, result, _ = analyze(tmp_path, SOURCE + extra)
    fact = method_fact(result)
    assert fact is not None
    guard = fact['origin']['allocation']['observation_guard']
    assert guard['frame_metadata'][0]['factory'] == 'traceback.walk_stack'


def test_a_stack_walk_that_exposes_frames_cannot_preserve_fresh_lookup(tmp_path):
    extra = '''
import traceback
def observe():
    for frame, line in traceback.walk_stack(None):
        opaque(frame)
'''
    _, result, _ = analyze(tmp_path, SOURCE + extra)
    assert method_fact(result) is None


@pytest.mark.parametrize('operation', [
    'return frame', 'return frame.f_locals', 'opaque(frame)',
    "return frame.f_globals.get('Box')", 'sys.settrace(opaque)',
    'frame.f_trace = opaque',
])
def test_frame_object_escape_or_mutation_still_prevents_a_fresh_binding(tmp_path, operation):
    text = FRAME_METADATA.replace("module = frame.f_globals.get('__name__', '')", operation)
    _, result, _ = analyze(tmp_path, SOURCE + text)
    assert method_fact(result) is None


def test_native_frame_metadata_premise_is_invalidated_after_source_changes(tmp_path):
    analyzer, first, path = analyze(tmp_path, SOURCE + FRAME_METADATA)
    assert method_fact(first) is not None
    path.write_text(SOURCE + FRAME_METADATA.replace('return module, line', 'return frame'),
                    encoding='utf-8')
    assert method_fact(analyzer.analyze(FunctionRef('sample', 'Box'))) is None


def test_a_readonly_frame_query_does_not_hide_a_later_aliased_trace_hook(tmp_path):
    _, result, _ = analyze(tmp_path, SOURCE + FRAME_METADATA
        + '\nfrom sys import settrace as trace\ntrace(opaque)\n')
    assert method_fact(result) is None


@pytest.mark.parametrize('member', [
    'def __getattribute__(self, name): return opaque(self, name)',
    'def __getattr__(self, name): return opaque(self, name)',
    'def __setattr__(self, name, value): opaque(self, name, value)',
    '__slots__ = ()',
    'def __new__(cls): return opaque()',
])
def test_custom_receiver_protocols_do_not_gain_a_plain_dictionary_origin(tmp_path, member):
    text = SOURCE.replace('class Box(Base):', 'class Box(Base):\n    ' + member)
    _, result, _ = analyze(tmp_path, text)
    assert method_fact(result) is None


def test_argument_calls_do_not_approve_a_later_source_body_binding(tmp_path):
    text = SOURCE.replace('self.update(kwargs)', 'self.update(opaque())')
    _, result, _ = analyze(tmp_path, text)
    assert method_fact(result) is None


def test_fresh_lookup_evidence_is_rebuilt_after_source_changes(tmp_path):
    analyzer, first, path = analyze(tmp_path)
    assert method_fact(first) is not None
    path.write_text(SOURCE.replace('self.update(kwargs)', 'opaque(self)\n        self.update(kwargs)'),
                    encoding='utf-8')
    second = analyzer.analyze(FunctionRef('sample', 'Box'))
    assert method_fact(second) is None


@pytest.mark.parametrize('prefix', ['kwargs = None', 'local = 1\n        local = 2',
                                  'self.ready: opaque() = True'])
def test_prefix_rebinding_or_evaluated_annotations_cannot_preserve_lookup(tmp_path, prefix):
    text = SOURCE.replace('self.update(kwargs)', prefix + '\n        self.update(kwargs)')
    _, result, _ = analyze(tmp_path, text)
    assert method_fact(result) is None


def test_property_checker_exposes_a_static_first_iteration_lookup_obligation(tmp_path):
    _, result, _ = analyze(tmp_path, depth=2)
    function = next(item for item in result.functions
                    if item['function']['qualname'] == 'Base.update')
    facts = function.get('fresh_mapping_member_checks', [])
    assert len(facts) == 1
    fact = facts[0]
    assert fact['kind'] == 'fresh_mapping_member_check'
    assert fact['status'] == 'requires_single_exact_mapping_item'
    assert fact['receiver_class']['qualname'] == 'Box'
    assert fact['member_names'] == ['__init__', 'set_allowed', 'update']
    assert fact['value_stores']['set_allowed']['attribute'] == 'allowed'
    assert fact['runtime_lookup_confirmed'] is False


def test_private_member_namespace_uses_the_declaring_class_mangling(tmp_path):
    text = SOURCE.replace('def set_allowed(', 'def __allowed(')
    _, result, _ = analyze(tmp_path, text, depth=2)
    fact = next(item['fresh_mapping_member_checks'][0] for item in result.functions
                if item.get('fresh_mapping_member_checks'))
    assert '_Box__allowed' in fact['member_names']
    assert '__allowed' not in fact['member_names']


def test_merging_an_unproved_checker_context_removes_the_fresh_lookup_proof(tmp_path):
    import copy
    analyzer, result, _ = analyze(tmp_path, depth=2)
    function = next(item for item in result.functions if item.get('fresh_mapping_member_checks'))
    unproved = copy.deepcopy(function)
    unproved['fresh_mapping_member_checks'] = []
    analyzer._merge_summary(result, FlowAnalysis(result.entry, {}, functions=[unproved]))
    assert not function['fresh_mapping_member_checks']


def test_merging_equivalent_lookup_proofs_keeps_fresh_origin_alternatives():
    fields = ('kind', 'status', 'function', 'mapping_parameter', 'receiver_parameter',
        'key_variable', 'value_variable', 'lookup_variable', 'attribute_template',
        'iteration_evidence', 'lookup_evidence', 'guard_evidence', 'raise_evidence',
        'invocation_evidence', 'key_conditions', 'attribute_requires_nondunder',
        'runtime_lookup_confirmed', 'runtime_rejection_confirmed', 'receiver_class',
        'member_names', 'source_hash', 'source_hashes', 'assumptions')
    first = {field: ('proof', field) for field in fields}
    first.update(origin={'path': 'before'}, own_attributes=['before'],
                 temporary_context_effects=[{'receiver_origin': 'before'}], value_stores={})
    second = dict(first, origin={'path': 'after'}, own_attributes=['after'],
                  temporary_context_effects=[{'receiver_origin': 'after'}])

    merged = FlowAnalyzer._merge_fresh_mapping_checks([first], [second])
    assert merged == [first, second]

    second['member_names'] = ['different source layout']
    assert FlowAnalyzer._merge_fresh_mapping_checks([first], [second]) == []


@pytest.mark.parametrize('old,new', [
    ('for key, value in props.items():', 'opaque(self)\n        for key, value in props.items():'),
    ("func = getattr(self, f'set_{key}', None)", "opaque(self)\n            func = getattr(self, f'set_{key}', None)"),
    ('raise AttributeError(key)', 'raise CustomError(key)'),
    ('raise AttributeError(key)', 'raise AttributeError(opaque())'),
    ('func(value)', 'opaque(value)'),
])
def test_unproved_prefix_or_guard_does_not_gain_a_static_member_check(tmp_path, old, new):
    _, result, _ = analyze(tmp_path, SOURCE.replace(old, new), depth=2)
    assert not any(item.get('fresh_mapping_member_checks') for item in result.functions)
