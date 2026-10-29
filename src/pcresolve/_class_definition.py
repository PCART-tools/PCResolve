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
from ._function_factory import _canonical, factory_wrapper
from ._metadata_creation import regex_pattern, static_cache
from ._runtime_namespace import unmodified

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


## Prove a source callable-object decorator preserves decorated function identity.
#  @param analyzer Fixed source snapshot and import bindings.
#  @param owner Class whose namespace is being formed.
#  @param member Decorated method definition.
#  @param dependencies Optional source paths supporting the protocol.
#  @param assumptions Optional set collecting the proof premises.
#  @return A bounded identity-preserving premise, or None when unproven.
def _source_callable_object_identity(analyzer, owner, member, dependencies, assumptions):
    if (assumptions is None or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], ast.Attribute)
            or not isinstance(member.decorator_list[0].value, ast.Name)):
        return None
    alias = member.decorator_list[0].value.id
    decorator_name = member.decorator_list[0].attr
    module = analyzer.imports.get(owner.module, {}).get(alias)
    if (not module or not analyzer._stable_import_name(owner.module + '.' + alias)):
        return None
    module_bodies = analyzer.module_bodies.get(module, [])
    assignments = []
    for module_path, body in module_bodies:
        for statement in body:
            if not isinstance(statement, ast.Assign):
                continue
            names = {node.id for target in statement.targets for node in ast.walk(target)
                     if isinstance(node, ast.Name)}
            if decorator_name in names:
                assignments.append((module_path, body, statement))
    if len(assignments) != 1:
        return None
    module_path, body, assignment = assignments[0]
    value = assignment.value
    if (not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name)
            or value.args or value.keywords):
        return None
    class_name = value.func.id
    binding_statements = [statement for _, statements in module_bodies for statement in statements
                          if decorator_name in statement_scope_facts([statement]).bound]
    if binding_statements != [assignment]:
        return None
    classes = [statement for statement in body if isinstance(statement, ast.ClassDef)
               and statement.name == class_name]
    if len(classes) != 1:
        return None
    decorator_class = classes[0]
    if decorator_class.decorator_list or decorator_class.keywords:
        return None

    def call_method(cls):
        methods = [statement for statement in cls.body if isinstance(statement, ast.FunctionDef)
                   and statement.name == '__call__']
        return methods[0] if len(methods) == 1 and not methods[0].decorator_list else None

    def normalized(method):
        arguments = method.args.posonlyargs + method.args.args
        if (len(arguments) != 2 or method.args.kwonlyargs or method.args.vararg
                or method.args.kwarg or method.args.defaults or method.args.kw_defaults):
            return None
        names = {arguments[0].arg: 'self', arguments[1].arg: 'value'}

        class Rename(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id in names:
                    node.id = names[node.id]
                return node

            def visit_arg(self, node):
                if node.arg in names:
                    node.arg = names[node.arg]
                return node

        result = Rename().visit(ast.fix_missing_locations(ast.Module(
            body=[copy.deepcopy(method)], type_ignores=[])))
        return result.body[0]

    child_call = call_method(decorator_class)
    if child_call is None:
        return None
    inspect_aliases = [name for name, imported in analyzer.imports.get(module, {}).items()
                       if imported == 'inspect']
    if len(inspect_aliases) != 1:
        return None
    inspect_alias = inspect_aliases[0]
    expected_base = ast.parse(f'''def __call__(self, value):
    if value.__doc__:
        value.__doc__ = {inspect_alias}.cleandoc(value.__doc__) % self.params
    return value
''').body[0]
    expected_child = ast.parse('''def __call__(self, value):
    super().__call__(value)
    if isinstance(value, type) and value.__init__ != object.__init__:
        self(value.__init__)
    return value
''').body[0]
    base_call = None
    base_name = None
    if len(decorator_class.bases) == 1 and isinstance(decorator_class.bases[0], ast.Name):
        base_name = decorator_class.bases[0].id
        bases = [statement for statement in body if isinstance(statement, ast.ClassDef)
                 and statement.name == base_name]
        if (len(bases) != 1 or bases[0].bases or bases[0].keywords
                or bases[0].decorator_list):
            return None
        base_call = call_method(bases[0])
        if (base_call is None
                or ast.dump(normalized(base_call), include_attributes=False)
                    != ast.dump(expected_base, include_attributes=False)
                or ast.dump(normalized(child_call), include_attributes=False)
                    != ast.dump(expected_child, include_attributes=False)):
            return None
    elif not decorator_class.bases:
        # A standalone callable decorator may perform the same bounded doc
        # substitution directly while returning the exact decorated object.
        direct = ast.parse(f'''def __call__(self, value):
    if value.__doc__:
        value.__doc__ = {inspect_alias}.cleandoc(value.__doc__) % self.params
    if isinstance(value, type) and value.__init__ != object.__init__:
        self(value.__init__)
    return value
''').body[0]
        simple = ast.parse(f'''def __call__(self, value):
    if value.__doc__:
        value.__doc__ = {inspect_alias}.cleandoc(value.__doc__) % self.params
    return value
''').body[0]
        if ast.dump(normalized(child_call), include_attributes=False) not in {
                ast.dump(direct, include_attributes=False),
                ast.dump(simple, include_attributes=False)}:
            return None
    else:
        return None
    helper_ref = analyzer._definition_index.find(module, class_name, kind='class')
    base_ref = (analyzer._definition_index.find(module, base_name, kind='class')
                if base_name is not None else [])
    if (len(helper_ref) != 1 or base_name is not None and len(base_ref) != 1
            or not analyzer._stable_import_name(module + '.' + class_name)
            or not analyzer._stable_import_name(module + '.' + class_name + '.__call__')
            or base_name is not None and (
                not analyzer._stable_import_name(module + '.' + base_name)
                or not analyzer._stable_import_name(module + '.' + base_name + '.__call__'))
            or analyzer.imports.get(module, {}).get(inspect_alias) != 'inspect'
            or not analyzer._stable_import_name(module + '.' + inspect_alias)
            or not unmodified(analyzer, 'inspect.cleandoc')
            or any(analyzer._builtin_name_status(helper_ref[0][0], child_call, name)
                   != 'confirmed_builtin' for name in ('super', 'isinstance', 'type', 'object'))):
        return None
    owners = [helper_ref[0][0]] + [item[0] for item in base_ref]
    writes, truncated = analyzer._class_binding_writes()
    if truncated or any(owner in owners and attribute in {
            '__call__', '__init__', '__new__', '__getattribute__', '__getattr__',
            '__setattr__', 'params', '__class__', '__bases__', '*'}
            for owner, attribute, _, _, _ in writes):
        return None
    for cls in [decorator_class] + ([base_ref[0][1]] if base_ref else []):
        if any(name in statement_scope_facts(cls.body).bound for name in (
                '__new__', '__getattribute__', '__getattr__', '__setattr__')):
            return None
        init_bindings = [item for item in cls.body
                         if '__init__' in statement_scope_facts([item]).bound]
        if (init_bindings and (len(init_bindings) != 1
                or not isinstance(init_bindings[0], ast.FunctionDef)
                or init_bindings[0].name != '__init__')):
            return None
        for statement in cls.body:
            if 'params' not in statement_scope_facts([statement]).bound:
                continue
            if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                    or not isinstance(statement.targets[0], ast.Name)
                    or statement.targets[0].id != 'params'
                    or not isinstance(statement.value, ast.Dict) or not _literal(statement.value)):
                return None
    initializers = [item for item in decorator_class.body
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__']
    if len(initializers) > 1:
        return None
    initializer_owner = helper_ref[0][0]
    if not initializers and base_ref:
        initializers = [item for item in base_ref[0][1].body
                        if isinstance(item, ast.FunctionDef) and item.name == '__init__']
        initializer_owner = base_ref[0][0]
        if len(initializers) > 1:
            return None
    if initializers:
        initializer = initializers[0]
        init_body = [item for item in initializer.body if not (
            isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
            and type(item.value.value) is str)]
        parameters = initializer.args.posonlyargs + initializer.args.args
        if (len(parameters) != 1 or initializer.decorator_list or initializer.args.defaults
                or initializer.args.kwonlyargs or initializer.args.vararg or initializer.args.kwarg
                or len(init_body) != 1 or not isinstance(init_body[0], ast.Assign)
                or len(init_body[0].targets) != 1
                or not isinstance(init_body[0].targets[0], ast.Attribute)
                or not isinstance(init_body[0].targets[0].value, ast.Name)
                or init_body[0].targets[0].value.id != parameters[0].arg
                or init_body[0].targets[0].attr != 'params'):
            return None
        value = init_body[0].value
        literal_mapping = isinstance(value, ast.Dict) and _literal(value)
        mapping_class = (analyzer._resolve_class(initializer_owner, ast.unparse(value.func))
            if isinstance(value, ast.Call) and isinstance(value.func, (ast.Name, ast.Attribute))
            and not value.args and not value.keywords else None)
        if not literal_mapping and mapping_class is None:
            return None
        if mapping_class is not None and dependencies is not None:
            dependencies.add(mapping_class[0].file_path)
    # Formatting can invoke a mapping callback before the decorated function is
    # stored. A source-visible observer could reach and mutate that function.
    from ._function_observation import nonobserving_source
    observation = nonobserving_source(analyzer)
    if observation is None:
        return None
    if dependencies is not None:
        dependencies.add(module_path)
        dependencies.add(helper_ref[0][0].file_path)
        dependencies.update(item[0].file_path for item in base_ref)
        dependencies.update(observation['source_hashes'])
    assumptions.update(observation['assumptions'])
    assumptions.update(('source_snapshot_bindings_hold',
        'source_callable_object_identity_decorator', 'standard_library_inspect_binding',
        'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_function_mutation'))
    return 'source_callable_object_identity_decorator'


## Compose a source identity decorator with a source argument-forwarding factory.
#  @param analyzer Fixed source snapshot and import bindings.
#  @param owner Class whose namespace is being formed.
#  @param target Decorated source method.
#  @param dependencies Optional source paths supporting the protocol.
#  @param assumptions Optional set collecting the proof premises.
#  @return The generic factory fact, or None when either proof is incomplete.
def source_identity_factory_wrapper_chain(analyzer, owner, target,
                                          dependencies=None, assumptions=None):
    ref, member = target
    if (assumptions is None or not isinstance(member, ast.FunctionDef)
            or len(member.decorator_list) != 2):
        return None
    outer, inner = member.decorator_list
    if (not isinstance(outer, ast.Attribute) or not isinstance(outer.value, ast.Name)
            or not isinstance(inner, ast.Call)):
        return None
    identity_probe = copy.copy(member)
    identity_probe.decorator_list = [outer]
    factory_probe = copy.copy(member)
    factory_probe.decorator_list = [inner]
    identity = _source_callable_object_identity(
        analyzer, owner, identity_probe, dependencies, assumptions)
    wrapper = factory_wrapper(analyzer, (ref, factory_probe))
    forwarding = wrapper.get('forwarding') if wrapper else None
    if (identity != 'source_callable_object_identity_decorator'
            or wrapper is None or wrapper.get('kind') != 'source_function_factory_wrapper_creation'
            or forwarding is None
            or forwarding.get('forwarded_function') != asdict(ref)
            or forwarding.get('argument_scope') != 'same_args_and_kwargs'
            or forwarding.get('normal_return_paths') !=
                'all_explicit_returns_forward_original_args_kwargs'):
        return None
    if dependencies is not None:
        dependencies.update(wrapper.get('source_hashes', {}))
    assumptions.update(wrapper.get('assumptions', ()))
    assumptions.add('source_identity_decorator_over_source_factory_wrapper')
    return wrapper


def _source_same_name_property_descriptor(analyzer, owner, expression, shadowed,
                                          dependencies=None):
    """Prove a source descriptor installs a same-name private property."""
    if (not isinstance(expression, ast.Call)
            or not isinstance(expression.func, ast.Attribute)
            or not isinstance(expression.func.value, ast.Name)
            or expression.func.value.id in shadowed
            or not analyzer.imports.get(owner.module, {}).get(expression.func.value.id)
            or not analyzer._stable_import_name(
                owner.module + '.' + expression.func.value.id)
            or not expression.args
            or any(not isinstance(value, ast.Constant)
                   or type(value.value) not in (str, bool, type(None), int, float)
                   for value in expression.args)
            or any(keyword.arg is None or not isinstance(keyword.value, ast.Constant)
                   or type(keyword.value.value) not in (str, bool, type(None), int, float)
                   for keyword in expression.keywords)):
        return None
    helper = analyzer._resolve_class(
        owner, expression.func.value.id + '.' + expression.func.attr)
    if helper is None:
        return None
    ref, cls = helper
    if (cls.decorator_list or cls.bases or analyzer.definition_conditions.get(ref)
            or not analyzer._stable_import_name(ref.module + '.' + ref.qualname)):
        return None
    methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
    if (len(methods) != 2 or set(methods) != {'__init__', '__set_name__'}
            or any(node.decorator_list for node in methods.values())):
        return None
    initializer, setter = methods['__init__'], methods['__set_name__']
    init_parameters = initializer.args.posonlyargs + initializer.args.args
    set_name_parameters = setter.args.posonlyargs + setter.args.args
    init_body = [statement for statement in initializer.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    setter_body = [statement for statement in setter.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    if (len(init_parameters) != 1 or initializer.args.vararg is None
            or initializer.args.vararg.arg != 'args' or initializer.args.kwarg is None
            or initializer.args.kwarg.arg != 'kwargs' or initializer.args.defaults
            or initializer.args.kwonlyargs or len(init_body) != 1
            or not isinstance(init_body[0], ast.Assign) or len(init_body[0].targets) != 1
            or not isinstance(init_body[0].targets[0], ast.Attribute)
            or not isinstance(init_body[0].targets[0].value, ast.Name)
            or init_body[0].targets[0].value.id != init_parameters[0].arg
            or not isinstance(init_body[0].value, ast.Call)
            or not isinstance(init_body[0].value.func, ast.Name)
            or len(set_name_parameters) != 3 or setter.args.vararg is not None
            or setter.args.kwarg is not None or setter.args.defaults
            or setter.args.kwonlyargs or len(setter_body) != 1
            or not isinstance(setter_body[0], ast.Expr)
            or not isinstance(setter_body[0].value, ast.Call)):
        return None
    init_assignment = init_body[0]
    stored_name = init_assignment.targets[0].attr
    forwarded = init_assignment.value.args
    if (not stored_name.isidentifier() or len(forwarded) != 1
            or not isinstance(forwarded[0], ast.Starred)
            or not isinstance(forwarded[0].value, ast.Name)
            or forwarded[0].value.id != initializer.args.vararg.arg
            or len(init_assignment.value.keywords) != 1
            or init_assignment.value.keywords[0].arg is not None
            or not isinstance(init_assignment.value.keywords[0].value, ast.Name)
            or init_assignment.value.keywords[0].value.id != initializer.args.kwarg.arg):
        return None
    callee_name = init_assignment.value.func.id
    helper_functions = analyzer._definition_index.find(ref.module, callee_name)
    if (len(helper_functions) != 1 or not isinstance(helper_functions[0][1], ast.FunctionDef)
            or analyzer._scope_facts(helper_functions[0][1]).globals
            or analyzer._scope_facts(helper_functions[0][1]).nonlocals
            or not analyzer._stable_import_name(ref.module + '.' + callee_name)):
        return None
    if (any(parameter.annotation is not None for parameter in init_parameters + set_name_parameters)
            or setter.returns is not None):
        return None
    receiver, owner_parameter, name_parameter = (parameter.arg for parameter in set_name_parameters)
    assignment = setter_body[0].value
    if (not isinstance(assignment.func, ast.Name) or assignment.func.id != 'setattr'
            or analyzer._builtin_name_status(ref, setter, 'setattr') != 'confirmed_builtin'
            or len(assignment.args) != 3 or assignment.keywords
            or not all(isinstance(value, ast.Name) for value in assignment.args[:2])
            or [value.id for value in assignment.args[:2]] != [owner_parameter, name_parameter]):
        return None
    decorated = assignment.args[2]
    if (not isinstance(decorated, ast.Call) or not isinstance(decorated.func, ast.Attribute)
            or not isinstance(decorated.func.value, ast.Name)
            or decorated.func.value.id != receiver or decorated.func.attr != stored_name
            or len(decorated.args) != 1 or len(decorated.keywords) != 1
            or decorated.keywords[0].arg != 'name'
            or not isinstance(decorated.keywords[0].value, ast.Name)
            or decorated.keywords[0].value.id != name_parameter):
        return None
    property_call = decorated.args[0]
    if (not isinstance(property_call, ast.Call) or not isinstance(property_call.func, ast.Name)
            or property_call.func.id != 'property' or len(property_call.args) != 2
            or property_call.keywords
            or analyzer._builtin_name_status(ref, setter, 'property') != 'confirmed_builtin'):
        return None
    getter, setter_lambda = property_call.args
    if (not isinstance(getter, ast.Lambda) or not isinstance(setter_lambda, ast.Lambda)
            or len(getter.args.args) != 1 or len(setter_lambda.args.args) != 2
            or getter.args.defaults or setter_lambda.args.defaults
            or not isinstance(getter.body, ast.Call)
            or not isinstance(getter.body.func, ast.Name) or getter.body.func.id != 'getattr'
            or analyzer._builtin_name_status(ref, setter, 'getattr') != 'confirmed_builtin'
            or len(getter.body.args) != 2 or getter.body.keywords
            or not isinstance(getter.body.args[0], ast.Name)
            or getter.body.args[0].id != getter.args.args[0].arg
            or not isinstance(getter.body.args[1], ast.JoinedStr)
            or len(getter.body.args[1].values) != 2
            or not isinstance(getter.body.args[1].values[0], ast.Constant)
            or getter.body.args[1].values[0].value != '_'
            or not isinstance(getter.body.args[1].values[1], ast.FormattedValue)
            or not isinstance(getter.body.args[1].values[1].value, ast.Name)
            or getter.body.args[1].values[1].value.id != name_parameter
            or not isinstance(setter_lambda.body, ast.Call)
            or not isinstance(setter_lambda.body.func, ast.Name)
            or setter_lambda.body.func.id != 'setattr'
            or len(setter_lambda.body.args) != 3 or setter_lambda.body.keywords
            or not isinstance(setter_lambda.body.args[0], ast.Name)
            or setter_lambda.body.args[0].id != setter_lambda.args.args[0].arg
            or not isinstance(setter_lambda.body.args[1], ast.JoinedStr)
            or ast.dump(setter_lambda.body.args[1], include_attributes=False)
                != ast.dump(getter.body.args[1], include_attributes=False)
            or not isinstance(setter_lambda.body.args[2], ast.Name)
            or setter_lambda.body.args[2].id != setter_lambda.args.args[1].arg):
        return None
    if dependencies is not None:
        dependencies.update((ref.file_path, helper_functions[0][0].file_path))
    return 'source_same_name_property_descriptor'


def _source_deprecated_classproperty(analyzer, owner, member, dependencies=None,
                                     assumptions=None):
    """Prove a source deprecation decorator preserves class-property behavior."""
    if assumptions is None or len(member.decorator_list) != 2:
        return None
    deprecation, descriptor = member.decorator_list
    if (not isinstance(deprecation, ast.Call)
            or not isinstance(deprecation.func, ast.Attribute)
            or not isinstance(deprecation.func.value, ast.Name)
            or deprecation.func.value.id in statement_scope_facts([member]).bound
            or len(deprecation.args) != 1
            or not isinstance(deprecation.args[0], ast.Constant)
            or type(deprecation.args[0].value) is not str or deprecation.keywords
            or not isinstance(descriptor, ast.Attribute)
            or not isinstance(descriptor.value, ast.Name)
            or descriptor.value.id in statement_scope_facts([member]).bound):
        return None
    deprecation_alias = deprecation.func.value.id
    descriptor_alias = descriptor.value.id
    if (not analyzer.imports.get(owner.module, {}).get(deprecation_alias)
            or not analyzer.imports.get(owner.module, {}).get(descriptor_alias)
            or not analyzer._stable_import_name(owner.module + '.' + deprecation_alias)
            or not analyzer._stable_import_name(owner.module + '.' + descriptor_alias)):
        return None
    class_selected = analyzer._resolve_class(owner, descriptor_alias + '.' + descriptor.attr)
    canonical = _canonical(analyzer, owner, member, deprecation.func)
    deprecator_selected = (analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
        if canonical and analyzer._stable_import_name(canonical) else None)
    if (class_selected is None or deprecator_selected is None
            or not isinstance(deprecator_selected[1], ast.FunctionDef)):
        return None
    class_ref, class_node = class_selected
    deprecated_ref, deprecated = deprecator_selected
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
    expected_class.name = class_node.name
    class_body = class_node.body[1:] if (class_node.body
        and isinstance(class_node.body[0], ast.Expr)
        and isinstance(class_node.body[0].value, ast.Constant)
        and type(class_node.body[0].value.value) is str) else class_node.body
    if (len(class_body) != len(expected_class.body)
            or any(ast.dump(without_docstring(actual), include_attributes=False)
                != ast.dump(without_docstring(expected), include_attributes=False)
                for actual, expected in zip(class_body, expected_class.body))):
        return None

    if (not isinstance(deprecated, ast.FunctionDef) or deprecated.decorator_list
            or analyzer._scope_facts(deprecated).globals
            or analyzer._scope_facts(deprecated).nonlocals):
        return None
    returned_names = {node.value.id for node in deprecated.body
                      if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)}
    nested = [node for node in deprecated.body if isinstance(node, ast.FunctionDef)
              and node.name in returned_names]
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
    class_name = class_node.name

    class RenameClassName(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == 'classproperty':
                node.id = class_name
            return node

    expected_branch = RenameClassName().visit(expected_branch)
    if (branch is None
            or ast.dump(branch.test, include_attributes=False)
                != ast.dump(expected_branch.test, include_attributes=False)
            or ast.dump(ast.Module(body=branch.body, type_ignores=[]), include_attributes=False)
                != ast.dump(ast.Module(body=expected_branch.body, type_ignores=[]), include_attributes=False)
            or len([node for node in function.body if isinstance(node, ast.Return)]) != 1
            or not any(isinstance(node, ast.Return)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and any(isinstance(candidate, ast.FunctionDef)
                    and candidate.name == node.value.func.id
                    for candidate in ast.walk(function))
                and len(node.value.args) == 2 and not node.value.keywords
                and all(isinstance(argument, ast.Name) for argument in node.value.args)
                for node in function.body)):
        return None

    if dependencies is not None:
        dependencies.update((class_ref.file_path, deprecated_ref.file_path))
    assumptions.update(('source_deprecated_classproperty_descriptor',
        'source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
        'no_unmodeled_indirect_class_mutation'))
    return 'source_deprecated_classproperty_descriptor'


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
                            premise = _source_callable_object_identity(
                                analyzer, owner, member, dependencies, assumptions)
                        if premise is None and assumptions is not None:
                            premise = _source_deprecated_classproperty(
                                analyzer, owner, member, dependencies, assumptions)
                        if premise is None and assumptions is not None:
                            chain = source_identity_factory_wrapper_chain(
                                analyzer, owner, (ref, member), dependencies, assumptions)
                            if chain is not None:
                                premise = 'source_identity_decorator_over_source_factory_wrapper'
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
                    private_descriptor = (_source_same_name_property_descriptor(
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
