## @package pcresolve._class_definition
#  Restricted namespace evaluation shared by source class binding proofs.

import ast
import copy
from dataclasses import asdict, replace

from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts
from ._stdlib_function_decorators import namespace_function_decorator
from ._property_namespace import property_declaration, property_assignment
from ._function_namespace import wrapper_creation
from ._contextmanager_namespace import contextmanager_declaration
from ._function_factory import factory_wrapper
from ._metadata_creation import regex_pattern, static_cache
from ._runtime_namespace import unmodified
from ._source_callable_metadata import wrapper_metadata

_CLASS_DEFINITION_NODE_LIMIT = 2000


def _namespace_syntax(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Function bodies are deferred. Defaults, annotations and decorators
            # can execute while forming the class namespace and remain in scope.
            children = []
            for name, value in ast.iter_fields(node):
                if name == 'body':
                    continue
                if isinstance(value, ast.AST):
                    children.append(value)
                elif isinstance(value, list):
                    children.extend(item for item in value if isinstance(item, ast.AST))
        else:
            children = list(ast.iter_child_nodes(node))
        pending.extend(reversed(children))


def _literal(value):
    if value is None or any(isinstance(node, ast.Call) for node in ast.walk(value)):
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


def _source_function_decoration(analyzer, target, dependencies, assumptions):
    # Reuse the bounded execution-effect proof; identity alone permits unknown
    # helper calls and is not enough to authorize class namespace formation.
    active = getattr(analyzer, '_namespace_decoration_active', set())
    ref = target[0]
    if ref in active or len(active) >= 8:
        return None
    analyzer._namespace_decoration_active = active
    active.add(ref)
    try:
        facts = analyzer._decoration_facts(target)
        if (len(facts) == 1 and facts[0]['body_binding_status'] != 'preserved'):
            facts = analyzer._fresh_decoration_facts(target) or facts
    finally:
        active.remove(ref)
    if (len(facts) != 1 or facts[0]['body_binding_status'] != 'preserved'
            or facts[0]['identity_status'] != 'preserved' or facts[0]['boundaries']):
        return None
    fact = facts[0]
    if dependencies is not None:
        dependencies.update(fact['source_hashes'])
    assumptions.update(fact['assumptions'])
    return 'source_function_namespace_preservation'


## Recognize Matplotlib's source-bound docstring substitution object on methods.
#  @param analyzer Fixed source snapshot and import bindings.
#  @param owner Class whose namespace is being formed.
#  @param member Decorated method definition.
#  @param dependencies Optional source paths supporting the protocol.
#  @param assumptions Optional set collecting the proof premises.
#  @return A narrow identity-preserving premise, or None for other decorators.
def _matplotlib_docstring_identity(analyzer, owner, member, dependencies, assumptions):
    if (assumptions is None or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], ast.Attribute)
            or not isinstance(member.decorator_list[0].value, ast.Name)):
        return None
    alias = member.decorator_list[0].value.id
    decorator_name = member.decorator_list[0].attr
    module = analyzer.imports.get(owner.module, {}).get(alias)
    if (decorator_name not in ('interpd', 'dedent_interpd')
            or module not in ('matplotlib._docstring', 'matplotlib.docstring')
            or not analyzer._stable_import_name(owner.module + '.' + alias)):
        return None
    prop_matches = analyzer._definition_index.find(
        module, '_ArtistPropertiesSubstitution', kind='class')
    base_matches = analyzer._definition_index.find(module, 'Substitution', kind='class')
    if len(prop_matches) != 1 or len(base_matches) != 1:
        return None
    prop_ref, prop = prop_matches[0]
    base_ref, base = base_matches[0]
    if (prop.decorator_list or base.decorator_list
            or not any(isinstance(item, ast.Name) and item.id == 'Substitution'
                       for item in prop.bases)):
        return None
    if any(isinstance(node, ast.Name) and node.id == '_ArtistPropertiesSubstitution'
           and isinstance(node.ctx, ast.Store)
           for _, body in analyzer.module_bodies.get(module, [])
           for statement in body for node in ast.walk(statement)):
        return None
    prop_call = [item for item in prop.body
                 if isinstance(item, ast.FunctionDef) and item.name == '__call__']
    base_call = [item for item in base.body
                 if isinstance(item, ast.FunctionDef) and item.name == '__call__']
    if len(prop_call) != 1 or len(base_call) != 1:
        return None
    expected_prop = ast.parse('''
def __call__(self, obj):
    super().__call__(obj)
    if isinstance(obj, type) and obj.__init__ != object.__init__:
        self(obj.__init__)
    return obj
''').body[0]
    expected_base = ast.parse('''
def __call__(self, func):
    if func.__doc__:
        func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
    return func
''').body[0]
    if (ast.dump(prop_call[0], include_attributes=False)
            != ast.dump(expected_prop, include_attributes=False)
            or ast.dump(base_call[0], include_attributes=False)
            != ast.dump(expected_base, include_attributes=False)
            or analyzer.imports.get(module, {}).get('inspect') != 'inspect'
            or not analyzer._stable_import_name(module + '.inspect')
            or not unmodified(analyzer, 'inspect.cleandoc')):
        return None
    if any(analyzer._builtin_name_status(prop_ref, prop_call[0], name)
           != 'confirmed_builtin' for name in ('super', 'isinstance', 'type', 'object')):
        return None
    aliases = {'interpd', 'dedent_interpd'}
    bindings = [statement for _, body in analyzer.module_bodies.get(module, [])
                for statement in body if isinstance(statement, (ast.Assign, ast.AnnAssign))
                and any(isinstance(target, ast.Name) and target.id in aliases
                        for target in (statement.targets if isinstance(statement, ast.Assign)
                                       else [statement.target]))]
    if (len(bindings) != 1 or not isinstance(bindings[0], ast.Assign)
            or not all(any(isinstance(target, ast.Name) and target.id == name
                           for target in bindings[0].targets) for name in aliases)
            or not isinstance(bindings[0].value, ast.Call)
            or not isinstance(bindings[0].value.func, ast.Name)
            or bindings[0].value.func.id != '_ArtistPropertiesSubstitution'
            or bindings[0].value.args or bindings[0].value.keywords):
        return None
    if any(isinstance(node, ast.Name) and node.id in aliases
           and isinstance(node.ctx, ast.Store)
           and node not in bindings[0].targets
           for _, body in analyzer.module_bodies.get(module, [])
           for statement in body for node in ast.walk(statement)):
        return None
    if dependencies is not None:
        dependencies.update((prop_ref.file_path, base_ref.file_path))
    assumptions.update(('source_snapshot_bindings_hold',
        'matplotlib_docstring_identity_decorator', 'standard_library_inspect_binding',
        'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_function_mutation'))
    return 'matplotlib_docstring_identity_decorator'


## Recognize the exact Matplotlib docstring + keyword-only decorator chain.
#  The outer docstring decorator returns the same function; the inner factory
#  creates the forwarding wrapper. Keep this limited to the known order and
#  source protocols rather than composing arbitrary decorators.
def matplotlib_docstring_keyword_only_chain(analyzer, owner, target,
                                            dependencies=None, assumptions=None):
    ref, member = target
    if (assumptions is None or ref.module != 'matplotlib.patches'
            or not isinstance(member, ast.FunctionDef)
            or len(member.decorator_list) != 2):
        return None
    outer, inner = member.decorator_list
    if (not isinstance(outer, ast.Attribute)
            or not isinstance(outer.value, ast.Name)
            or outer.value.id != '_docstring'
            or outer.attr != 'dedent_interpd'
            or not isinstance(inner, ast.Call)
            or not isinstance(inner.func, ast.Attribute)
            or not isinstance(inner.func.value, ast.Name)
            or inner.func.value.id != '_api'
            or inner.func.attr != 'make_keyword_only'
            or analyzer.imports.get(owner.module, {}).get('_docstring') != 'matplotlib._docstring'
            or analyzer.imports.get(owner.module, {}).get('_api') != 'matplotlib._api'
            or not analyzer._stable_import_name(owner.module + '._docstring')
            or not analyzer._stable_import_name(owner.module + '._api')):
        return None
    identity_probe = copy.copy(member)
    identity_probe.decorator_list = [outer]
    factory_probe = copy.copy(member)
    factory_probe.decorator_list = [inner]
    identity = _matplotlib_docstring_identity(
        analyzer, owner, identity_probe, dependencies, assumptions)
    wrapper = factory_wrapper(analyzer, (ref, factory_probe))
    forwarding = wrapper.get('forwarding') if wrapper else None
    if (identity != 'matplotlib_docstring_identity_decorator'
            or wrapper is None or wrapper.get('kind') != 'source_matplotlib_keyword_only_wrapper'
            or forwarding is None
            or forwarding.get('forwarded_function') != asdict(ref)
            or forwarding.get('argument_scope') != 'same_args_and_kwargs'
            or forwarding.get('normal_return_paths') !=
                'all_explicit_returns_forward_original_args_kwargs'):
        return None
    if dependencies is not None:
        dependencies.update(wrapper.get('source_hashes', {}))
    assumptions.update(wrapper.get('assumptions', ()))
    assumptions.add('matplotlib_docstring_identity_over_keyword_only_wrapper')
    return wrapper


def _matplotlib_private_attribute_descriptor(analyzer, owner, expression, shadowed,
                                             dependencies=None):
    """Prove the bounded same-name class write used by Matplotlib's helper."""
    if (not isinstance(expression, ast.Call)
            or not isinstance(expression.func, ast.Attribute)
            or not isinstance(expression.func.value, ast.Name)
            or expression.func.value.id in shadowed
            or expression.func.value.id != '_api'
            or expression.func.attr != 'deprecate_privatize_attribute'
            or analyzer.imports.get(owner.module, {}).get('_api') != 'matplotlib._api'
            or not analyzer._stable_import_name(owner.module + '._api')
            or not expression.args
            or any(not isinstance(value, ast.Constant)
                   or type(value.value) not in (str, bool, type(None), int, float)
                   for value in expression.args)
            or any(keyword.arg is None or not isinstance(keyword.value, ast.Constant)
                   or type(keyword.value.value) not in (str, bool, type(None), int, float)
                   for keyword in expression.keywords)):
        return None
    helper = analyzer._resolve_class(owner, '_api.deprecate_privatize_attribute')
    if helper is None or helper[0].module != 'matplotlib._api.deprecation':
        return None
    ref, cls = helper
    if (cls.decorator_list or cls.bases or analyzer.definition_conditions.get(ref)
            or not analyzer._stable_import_name(ref.module + '.' + ref.qualname)):
        return None
    methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
    if (len(methods) != 2 or set(methods) != {'__init__', '__set_name__'}
            or any(node.decorator_list for node in methods.values())):
        return None
    expected = ast.parse('''
def __init__(self, *args, **kwargs):
    self.deprecator = deprecated(*args, **kwargs)
def __set_name__(self, owner, name):
    setattr(owner, name, self.deprecator(
        property(lambda self: getattr(self, f"_{name}"),
                 lambda self, value: setattr(self, f"_{name}", value)),
        name=name))
''').body
    def without_docstring(node):
        clone = copy.copy(node)
        clone.body = list(node.body)
        if (clone.body and isinstance(clone.body[0], ast.Expr)
                and isinstance(clone.body[0].value, ast.Constant)
                and isinstance(clone.body[0].value.value, str)):
            clone.body.pop(0)
        return clone
    if any(ast.dump(without_docstring(methods[name]), include_attributes=False)
           != ast.dump(without_docstring(expected[index]), include_attributes=False)
           for index, name in enumerate(('__init__', '__set_name__'))):
        return None
    deprecated = analyzer._definition_index.find(ref.module, 'deprecated')
    if (len(deprecated) != 1 or not isinstance(deprecated[0][1], ast.FunctionDef)
            or analyzer._scope_facts(deprecated[0][1]).globals
            or analyzer._scope_facts(deprecated[0][1]).nonlocals
            or not analyzer._stable_import_name(ref.module + '.deprecated')):
        return None
    if dependencies is not None:
        dependencies.add(ref.file_path)
    return 'matplotlib_private_attribute_descriptor_same_name_write'


def _matplotlib_deprecated_classproperty(analyzer, owner, member, dependencies=None,
                                         assumptions=None):
    """Recognize Matplotlib's bounded deprecated classproperty descriptor chain."""
    if (assumptions is None or len(member.decorator_list) != 2
            or not isinstance(member.decorator_list[0], ast.Call)
            or not isinstance(member.decorator_list[0].func, ast.Attribute)
            or not isinstance(member.decorator_list[0].func.value, ast.Name)
            or member.decorator_list[0].func.value.id != '_api'
            or member.decorator_list[0].func.attr != 'deprecated'
            or len(member.decorator_list[0].args) != 1
            or not isinstance(member.decorator_list[0].args[0], ast.Constant)
            or type(member.decorator_list[0].args[0].value) is not str
            or member.decorator_list[0].keywords
            or not isinstance(member.decorator_list[1], ast.Attribute)
            or not isinstance(member.decorator_list[1].value, ast.Name)
            or member.decorator_list[1].value.id != '_api'
            or member.decorator_list[1].attr != 'classproperty'
            or analyzer.imports.get(owner.module, {}).get('_api') != 'matplotlib._api'
            or not analyzer._stable_import_name(owner.module + '._api')):
        return None

    api_classes = analyzer._definition_index.find('matplotlib._api', 'classproperty', kind='class')
    deprecators = analyzer._definition_index.find(
        'matplotlib._api.deprecation', 'deprecated')
    if (len(api_classes) != 1 or len(deprecators) != 1
            or not analyzer._stable_import_name('matplotlib._api.classproperty')
            or not analyzer._stable_import_name('matplotlib._api.deprecation.deprecated')):
        return None
    class_ref, class_node = api_classes[0]
    if class_node.bases or class_node.decorator_list or class_node.keywords:
        return None

    def without_docstring(node):
        clone = copy.copy(node)
        clone.body = list(node.body)
        if (clone.body and isinstance(clone.body[0], ast.Expr)
                and isinstance(clone.body[0].value, ast.Constant)
                and type(clone.body[0].value.value) is str):
            clone.body.pop(0)
        return clone

    expected_class = ast.parse('''
class classproperty:
    def __init__(self, fget, fset=None, fdel=None, doc=None):
        self._fget = fget
        if fset is not None or fdel is not None:
            raise ValueError('classproperty only implements fget.')
        self.fset = fset
        self.fdel = fdel
        self._doc = doc
    def __get__(self, instance, owner):
        return self._fget(owner)
    @property
    def fget(self):
        return self._fget
''').body[0]
    class_body = class_node.body[1:] if (class_node.body
        and isinstance(class_node.body[0], ast.Expr)
        and isinstance(class_node.body[0].value, ast.Constant)
        and type(class_node.body[0].value.value) is str) else class_node.body
    if (len(class_body) != len(expected_class.body)
            or any(ast.dump(without_docstring(actual), include_attributes=False)
                != ast.dump(without_docstring(expected), include_attributes=False)
                for actual, expected in zip(class_body, expected_class.body))):
        return None

    deprecated_ref, deprecated = deprecators[0]
    if (not isinstance(deprecated, ast.FunctionDef) or deprecated.decorator_list
            or analyzer._scope_facts(deprecated).globals
            or analyzer._scope_facts(deprecated).nonlocals):
        return None
    nested = [node for node in deprecated.body if isinstance(node, ast.FunctionDef)
              and node.name == 'deprecate']
    if len(nested) != 1 or nested[0].decorator_list:
        return None
    function = nested[0]
    branch_owner = next((node for node in function.body if isinstance(node, ast.If)), None)
    branch = (branch_owner.orelse[0] if branch_owner and branch_owner.orelse
              and isinstance(branch_owner.orelse[0], ast.If) else None)
    expected_branch = ast.parse('''
def deprecate(obj):
    if isinstance(obj, type):
        pass
    elif isinstance(obj, (property, classproperty)):
        if obj_type is None:
            obj_type = 'attribute'
        func = None
        name = name or obj.fget.__name__
        old_doc = obj.__doc__
        class _deprecated_property(type(obj)):
            def __get__(self, instance, owner=None):
                if instance is not None or owner is not None and isinstance(self, classproperty):
                    emit_warning()
                return super().__get__(instance, owner)
            def __set__(self, instance, value):
                if instance is not None:
                    emit_warning()
                return super().__set__(instance, value)
            def __delete__(self, instance):
                if instance is not None:
                    emit_warning()
                return super().__delete__(instance)
            def __set_name__(self, owner, set_name):
                nonlocal name
                if name == '<lambda>':
                    name = set_name
        def finalize(_, new_doc):
            return _deprecated_property(fget=obj.fget, fset=obj.fset,
                                        fdel=obj.fdel, doc=new_doc)
''').body[0].body[0].orelse[0]
    if (branch is None
            or ast.dump(branch.test, include_attributes=False)
                != ast.dump(expected_branch.test, include_attributes=False)
            or ast.dump(ast.Module(body=branch.body, type_ignores=[]), include_attributes=False)
                != ast.dump(ast.Module(body=expected_branch.body, type_ignores=[]), include_attributes=False)
            or not any(isinstance(node, ast.Return)
                and isinstance(node.value, ast.Call)
                and ast.unparse(node.value.func) == 'finalize'
                and ast.unparse(node.value) == 'finalize(wrapper, new_doc)'
                for node in function.body)):
        return None

    if dependencies is not None:
        dependencies.update((class_ref.file_path, deprecated_ref.file_path))
    assumptions.update(('matplotlib_deprecated_classproperty_descriptor',
        'source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
        'no_unmodeled_indirect_class_mutation'))
    return 'matplotlib_deprecated_classproperty_descriptor'


## Identify class-definition operations that can change a source namespace.
#  @param analyzer Snapshot lookup machinery confirming builtin method descriptors.
#  @param hierarchy Bounded source MRO, whose metaclasses/hooks are checked separately.
#  @param declaration Optional predicate confirming a harmless typing declaration.
#  @param dependencies Optional set collecting additional source construction premises.
#  @param assumptions Optional set enabling and collecting standard decorator premises.
#  @return Tuples of neutral issue reason, source owner and AST witness.
#  @throws _ClassEffectLimit When inspecting the hierarchy exceeds the node limit.
def namespace_issues(analyzer, hierarchy, declaration=None, dependencies=None,
                     assumptions=None):
    inspected = [0]

    def plain_instance(value, owner, shadowed, seen):
        if (not isinstance(value, ast.Call) or value.args or value.keywords
                or not isinstance(value.func, (ast.Name, ast.Attribute))):
            return False
        try:
            name = ast.unparse(value.func)
        except RecursionError:
            raise _ClassEffectLimit()
        head = name.partition('.')[0]
        if head in shadowed or not analyzer._stable_import_name(owner.module + '.' + head):
            return False
        target = analyzer._resolve_class(owner, name)
        if target is None or '.' in target[0].qualname or target[0] in seen:
            return False
        if not analyzer._stable_import_name(target[0].module + '.' + target[0].qualname):
            return False
        sources = analyzer._class_mro(target[0].module, target[0].qualname)
        forbidden = {'__new__', '__init__', '__init_subclass__', '__set_name__',
                     '__getattribute__', '__getattr__', '__del__'}
        if (not sources or len(sources) > 64 or any(cls.keywords or cls.decorator_list
                or analyzer.definition_conditions.get(ref)
                or forbidden & statement_scope_facts(cls.body).bound for ref, cls in sources)):
            return False
        writes, truncated = analyzer._class_binding_writes()
        if truncated:
            raise _ClassEffectLimit()
        if any(attribute in forbidden | {'__class__', '__bases__', '*'}
               and any(written == ref for ref, _ in sources)
               for written, attribute, _, _, _ in writes):
            return False
        if inspect(sources, seen):
            return False
        if dependencies is not None:
            dependencies.update(ref.file_path for ref, _ in sources)
        return True

    def inspect(sources, seen):
        if len(seen) > 32:
            raise _ClassEffectLimit()
        issues = []
        for owner, cls in sources:
            if owner in seen:
                issues.append(('namespace_unconfirmed', owner, cls))
                continue
            for _ in _namespace_syntax(cls):
                inspected[0] += 1
                if inspected[0] > _CLASS_DEFINITION_NODE_LIMIT:
                    raise _ClassEffectLimit()
            shadowed = set()
            properties = set()
            for member in cls.body:
                property_premise = None
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if declaration is not None and declaration(owner, cls, member):
                        bound = statement_scope_facts([member]).bound
                        shadowed.update(bound)
                        properties.difference_update(bound)
                        continue
                    ref = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)
                    if member.decorator_list and analyzer._descriptor_kind((ref, member)) is None:
                        cached = (static_cache(analyzer, owner, member, shadowed)
                                  if assumptions is not None else None)
                        property_premise = (property_declaration(
                            analyzer, owner, member, shadowed, properties, dependencies)
                            if assumptions is not None else None)
                        premise = property_premise or (namespace_function_decorator(
                            analyzer, owner, member, shadowed, dependencies)
                            if assumptions is not None else None)
                        if premise is None and cached is not None:
                            premise = cached['kind']
                            assumptions.update(cached['assumptions'])
                            if dependencies is not None:
                                dependencies.update(cached['source_hashes'])
                        if premise is None and assumptions is not None:
                            premise = contextmanager_declaration(
                                analyzer, owner, member, shadowed, dependencies, assumptions)
                            if premise:
                                assumptions.update(['standard_builtin_namespace_preserved',
                                    'no_unmodeled_indirect_builtin_mutation',
                                    'standard_library_default_wraps_metadata_protocol',
                                    'no_unmodeled_indirect_module_mutation',
                                    'no_unmodeled_indirect_function_mutation',
                                    'no_external_monkeypatch_or_import_hook'])
                        if premise is None and assumptions is not None:
                            premise = _source_function_decoration(
                                analyzer, (ref, member), dependencies, assumptions)
                        if premise is None:
                            premise = _matplotlib_docstring_identity(
                                analyzer, owner, member, dependencies, assumptions)
                        if premise is None and assumptions is not None:
                            premise = _matplotlib_deprecated_classproperty(
                                analyzer, owner, member, dependencies, assumptions)
                        if premise is None and assumptions is not None:
                            chain = matplotlib_docstring_keyword_only_chain(
                                analyzer, owner, (ref, member), dependencies, assumptions)
                            if chain is not None:
                                premise = 'matplotlib_docstring_identity_over_keyword_only_wrapper'
                        if premise is None and assumptions is not None:
                            metadata = wrapper_metadata(
                                analyzer, (ref, member), '_supports_rasterization')
                            if metadata is not None:
                                if dependencies is not None:
                                    dependencies.update(metadata['source_hashes'])
                                assumptions.update(metadata['assumptions'])
                                premise = 'source_matplotlib_rasterization_wrapper_creation'
                        if premise is None and assumptions is not None:
                            wrapper = (wrapper_creation(analyzer, (ref, member))
                                       or factory_wrapper(analyzer, (ref, member)))
                            if wrapper is not None:
                                # Namespace formation needs the result's native
                                # descriptor kind, not preservation of its body.
                                # Constructor/body selection still uses the
                                # independent, stricter decoration proof above.
                                if dependencies is not None:
                                    dependencies.update(wrapper['source_hashes'])
                                assumptions.update(wrapper['assumptions'])
                                premise = 'source_native_function_wrapper_creation'
                        if premise is None:
                            issues.append(('namespace_unconfirmed', owner, member))
                        else:
                            assumptions.add(premise)
                            if property_premise:
                                assumptions.add('no_unmodeled_indirect_builtin_mutation')
                    expressions = member.args.defaults + [v for v in member.args.kw_defaults if v is not None]
                    parameters = member.args.posonlyargs + member.args.args + member.args.kwonlyargs
                    parameters += [arg for arg in (member.args.vararg, member.args.kwarg) if arg is not None]
                    expressions += [arg.annotation for arg in parameters if arg.annotation is not None]
                    if member.returns is not None:
                        expressions.append(member.returns)
                    if any(not (isinstance(value, ast.Name) or _literal(value)) for value in expressions):
                        issues.append(('definition_evaluation_unconfirmed', owner, member))
                elif isinstance(member, (ast.Assign, ast.AnnAssign)):
                    targets = member.targets if isinstance(member, ast.Assign) else [member.target]
                    constructed_property = (property_assignment(
                        analyzer, owner, cls, member, shadowed, dependencies)
                        if assumptions is not None else None)
                    private_descriptor = (_matplotlib_private_attribute_descriptor(
                        analyzer, owner, member.value, shadowed, dependencies)
                        if assumptions is not None and member.value is not None else None)
                    pattern = (regex_pattern(analyzer, owner, member.value, shadowed)
                               if assumptions is not None else None)
                    if (not all(isinstance(target, ast.Name) for target in targets)
                            or member.value is not None and not (_literal(member.value)
                                or constructed_property
                                or private_descriptor
                                or pattern is not None
                                or plain_instance(member.value, owner, shadowed, seen + (owner,)))
                            or isinstance(member, ast.AnnAssign)
                            and not isinstance(member.annotation, (ast.Name, ast.Constant))):
                        issues.append(('namespace_unconfirmed', owner, member))
                    elif constructed_property:
                        assumptions.update([constructed_property, 'standard_builtin_namespace_preserved',
                                            'no_unmodeled_indirect_builtin_mutation'])
                    elif private_descriptor:
                        assumptions.update([private_descriptor, 'builtin_type_set_name_protocol',
                            'source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
                            'no_unmodeled_indirect_class_mutation'])
                    elif pattern is not None:
                        assumptions.update(pattern['assumptions'])
                        if dependencies is not None:
                            dependencies.update(pattern['source_hashes'])
                elif not (isinstance(member, ast.Pass) or isinstance(member, ast.Expr)
                          and isinstance(member.value, ast.Constant) and isinstance(member.value.value, str)):
                    issues.append(('namespace_unconfirmed', owner, member))
                bound = statement_scope_facts([member]).bound
                shadowed.update(bound)
                properties.difference_update(bound)
                if property_premise:
                    properties.add(member.name)
        return issues

    return inspect(hierarchy, ())
