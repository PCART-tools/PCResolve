## @package pcresolve._constructor_retention
#  Partial fresh-receiver write proofs, separate from execution/completion facts.
#  推导新鲜接收者的部分写入事实，并与执行和完成状态分开。

import ast
from dataclasses import asdict

from .program_facts import SourceSpan
from .scope_facts import function_scope_facts, statement_scope_facts
from ._class_creation import written_attributes
from ._class_definition import _source_callable_object_identity
from ._property_namespace import _stable_builtin_namespace


## Signal an open receiver effect or unsupported constructor behavior.
## 表示接收者效果开放或构造器行为不受支持。
class _OpenReceiver(Exception):
    pass


## Describe root initializer stores retained on normal construction return.
## 描述根初始化器在构造正常返回后保留的属性写入。
#
#  @param analyzer Fixed source generation and bounded source lookup.
#  @param hierarchy Source MRO already checked by the constructor binding.
#  @param target Selected initializer definition pair.
#  @param binding Source class invocation binding, never a runtime observation.
#  @param lookup_name Optional attribute whose writes must be excluded.
#  @param return_effects Whether to return the broader receiver effect summary.
#  @return Store witnesses, or none for open protocols, effects or budgets.
def retained_stores(analyzer, hierarchy, target, binding, *, lookup_name=None,
                    return_effects=False):
    ref, initializer = target
    if (binding['status'] != 'source_bound' or binding['phase'] != '__init__'
            or not hierarchy or len(hierarchy) > 64):
        return None if return_effects else []
    forbidden = {'__setattr__', '__delattr__', '__getattribute__', '__getattr__',
                 '__slots__', '__dict__', '__class__'}
    reflection = {'exec', 'eval', 'globals', 'locals', 'vars', '__import__',
                  '__builtins__', 'getattr', 'compile', 'currentframe', '_getframe',
                  'f_locals', 'f_globals', 'f_back'}
    hook_attributes = written_attributes(binding.get('class_creation_hooks', []))
    namespace = set(hook_attributes)
    namespace.update(written_attributes(binding.get('class_decorations', [])))
    captures = set()
    for _, cls in hierarchy:
        namespace.update(statement_scope_facts(cls.body).bound)
        for method in cls.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            parameters = method.args.posonlyargs + method.args.args
            if not parameters:
                continue
            receiver = parameters[0].arg
            for node in ast.walk(method):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Attribute)
                        and isinstance(node.targets[0].value, ast.Name)
                        and node.targets[0].value.id == receiver
                        and any(isinstance(child, ast.Name) and child.id == receiver
                                and isinstance(child.ctx, ast.Load)
                                for child in ast.walk(node.value))):
                    captures.add(node.targets[0].attr)
    if forbidden & namespace:
        return None if return_effects else []
    identities = {owner for owner, _ in hierarchy}
    mutations, truncated = analyzer._class_binding_writes(include_escapes=True)
    if truncated:
        return None if return_effects else []
    if not return_effects:
        for written, _, reason, owner, node in mutations:
            if written not in identities:
                continue
            # A verified builtin super(Class, self) does not expose Class to user code.
            definitions = analyzer._definition_index.find(owner.module, owner.qualname)
            if (reason == 'visible_class_escape' and isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == 'super'
                    and len(definitions) == 1
                    and analyzer._builtin_name_status(owner, definitions[0][1], 'super')
                    == 'confirmed_builtin'):
                continue
            return []

    remaining = [10000]
    checked = {}
    writes = []
    reads = set()
    calls = set()
    receiver_values = {}
    unknown = object()

    ## Resolve a literal, local, or previously written receiver attribute.
    ## 解析字面量、局部值或先前写入的接收者属性。
    #
    #  @param node Expression whose known value is requested.
    #  @param locals_ Current local literal values.
    #  @param receiver Receiver parameter identifier.
    #  @return Known value, or the local unknown sentinel.
    def known_value(node, locals_, receiver):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return locals_.get(node.id, unknown)
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == receiver):
            return receiver_values.get(node.attr, unknown)
        return unknown

    ## Evaluate a condition only when all required values are statically known.
    ## 仅在所需值均可静态确定时计算条件。
    #
    #  @param node Condition expression to inspect.
    #  @param locals_ Current local literal values.
    #  @param receiver Receiver parameter identifier.
    #  @param owner Source reference owning the method.
    #  @param method Method AST node used for builtin checks.
    #  @return Boolean result, or the unknown sentinel.
    def known_condition(node, locals_, receiver, owner=ref, method=initializer):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'len' and len(node.args) == 1 and not node.keywords
                and analyzer._builtin_name_status(owner, method, 'len')
                    == 'confirmed_builtin'):
            value = known_value(node.args[0], locals_, receiver)
            if type(value) in (tuple, list, dict, str, bytes):
                return bool(len(value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = known_condition(node.operand, locals_, receiver, owner, method)
            return unknown if value is unknown else not value
        if isinstance(node, ast.BoolOp):
            values = [known_condition(value, locals_, receiver, owner, method)
                      for value in node.values]
            if isinstance(node.op, ast.And):
                if False in values:
                    return False
                return all(values) if unknown not in values else unknown
            if True in values:
                return True
            return all(not value for value in values) if unknown not in values else unknown
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left = known_value(node.left, locals_, receiver)
            right = known_value(node.comparators[0], locals_, receiver)
            if left is unknown or right is unknown:
                return unknown
            if isinstance(node.ops[0], ast.Is):
                return left is right
            if isinstance(node.ops[0], ast.IsNot):
                return left is not right
        value = known_value(node, locals_, receiver)
        return unknown if value is unknown else bool(value)

    ## Find a property setter only when builtin property binding is stable.
    ## 仅在内建 property 绑定稳定时查找属性 setter。
    #
    #  @param name Property name to resolve.
    #  @return Owner and setter node, or raises _OpenReceiver on ambiguity.
    def property_setter(name):
        for owner, cls in hierarchy:
            members = [item for item in cls.body
                       if isinstance(item, ast.FunctionDef) and item.name == name]
            if not members:
                continue
            if len(members) != 2:
                raise _OpenReceiver()
            getter, setter = members
            if (len(getter.decorator_list) != 1
                    or not isinstance(getter.decorator_list[0], ast.Name)
                    or getter.decorator_list[0].id != 'property'
                    or analyzer._builtin_name_status(owner, getter, 'property')
                        != 'confirmed_builtin'
                    or len(setter.decorator_list) != 1
                    or not isinstance(setter.decorator_list[0], ast.Attribute)
                    or not isinstance(setter.decorator_list[0].value, ast.Name)
                    or setter.decorator_list[0].value.id != name
                    or setter.decorator_list[0].attr != 'setter'
                    or not _stable_builtin_namespace(analyzer, owner)[0]):
                raise _OpenReceiver()
            return owner, setter
        raise _OpenReceiver()

    decorator_assumptions, decorator_dependencies = set(), set()

    ## Prove a source decorator preserves the callable object's identity.
    ## 证明源码装饰器保留可调用对象身份。
    #
    #  @param owner Class source reference containing the method.
    #  @param method Method node whose decorators are inspected.
    #  @return True when the identity-preserving protocol is proven.
    def callable_object_identity_decorator(owner, method):
        classes = analyzer._definition_index.find(owner.module, owner.qualname, kind='class')
        if len(classes) != 1:
            return False
        assumptions, dependencies = set(), set()
        proven = _source_callable_object_identity(
            analyzer, classes[0][0], method, dependencies, assumptions
        ) == 'source_callable_object_identity_decorator'
        if proven:
            decorator_assumptions.update(assumptions)
            decorator_dependencies.update(dependencies)
        return proven

    ## Confirm a class member is a single immutable literal assignment.
    ## 确认类成员是唯一的不可变字面量赋值。
    #
    #  @param name Class member name to inspect.
    #  @return True when a supported constant binding is found.
    def plain_class_constant(name):
        for owner, cls in hierarchy:
            bindings = []
            for statement in cls.body:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if statement.name == name:
                        bindings.append(statement)
                elif isinstance(statement, ast.Assign):
                    if any(isinstance(target, ast.Name) and target.id == name
                           for target in statement.targets):
                        bindings.append(statement)
                elif isinstance(statement, ast.AnnAssign):
                    if isinstance(statement.target, ast.Name) and statement.target.id == name:
                        bindings.append(statement)
            if not bindings:
                continue
            if len(bindings) != 1 or not isinstance(bindings[0], ast.Assign):
                return False
            statement = bindings[0]
            return (len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == name
                    and isinstance(statement.value, ast.Constant)
                    and type(statement.value.value) in (type(None), bool, int, float, str, bytes))
        return False

    ## Confirm a property getter returns a direct receiver attribute.
    ## 确认属性 getter 直接返回接收者属性。
    #
    #  @param name Property name to inspect.
    #  @return True only for a simple builtin property getter.
    def plain_receiver_property(name):
        for owner, cls in hierarchy:
            members = [item for item in cls.body
                       if isinstance(item, ast.FunctionDef) and item.name == name]
            if not members:
                continue
            getter = members[0]
            body = [item for item in getter.body if not (
                isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
                and type(item.value.value) is str)]
            if (len(members) != 1 or len(getter.decorator_list) != 1
                    or not isinstance(getter.decorator_list[0], ast.Name)
                    or getter.decorator_list[0].id != 'property'
                    or analyzer._builtin_name_status(owner, getter, 'property')
                        != 'confirmed_builtin'
                    or not getter.args.args
                    or len(body) != 1 or not isinstance(body[0], ast.Return)
                    or not isinstance(body[0].value, ast.Attribute)
                    or not isinstance(body[0].value.value, ast.Name)
                    or body[0].value.value.id != getter.args.args[0].arg
                    or body[0].value.attr.startswith('__')):
                return False
            return True
        return False

    ## Consume one unit of the local syntax-inspection budget.
    ## 消耗一单位局部语法检查预算。
    #
    #  @param node AST node being inspected.
    #  @return None; raises _OpenReceiver when the budget is exhausted.
    def charge(node):
        remaining[0] -= 1
        if remaining[0] < 0:
            raise _OpenReceiver()

    ## Resolve the next supported method implementation in the class hierarchy.
    ## 在类继承层次中解析下一个受支持的方法实现。
    #
    #  @param name Method name to resolve.
    #  @param after Optional class reference after which lookup continues.
    #  @return Unique owner and method pair, or raises _OpenReceiver.
    def method_target(name, after=None):
        if name in hook_attributes:
            raise _OpenReceiver()
        start = after is None
        for owner, cls in hierarchy:
            if not start:
                start = owner == after
                continue
            if name not in statement_scope_facts(cls.body).bound:
                continue
            matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
            if (len(matches) != 1 or not isinstance(matches[0][1], ast.FunctionDef)
                    or matches[0][1].decorator_list
                    and not callable_object_identity_decorator(owner, matches[0][1])):
                raise _OpenReceiver()
            return matches[0]
        raise _OpenReceiver()

    ## Traverse a receiver method while collecting reads, writes, and call edges.
    ## 遍历接收者方法并收集读写操作与调用边。
    #
    #  @param definition Owner and method pair to inspect.
    #  @param active Active recursion stack of method identities.
    #  @param initial_values Known argument values for this invocation.
    #  @return None; raises _OpenReceiver for unsupported behavior.
    def inspect(definition, active=(), initial_values=None):
        owner, method = definition
        definition_key = (owner, method.name, method.lineno)
        if definition_key in active or len(active) >= 32:
            raise _OpenReceiver()
        if definition_key in checked:
            return
        checked[definition_key] = (owner, method)
        parameters = method.args.posonlyargs + method.args.args
        if not parameters:
            raise _OpenReceiver()
        receiver = parameters[0].arg
        local_values = dict(initial_values or {})

        ## Detect whether an expression reads the receiver parameter.
        ## 检测表达式是否读取接收者参数。
        #
        #  @param node AST subtree to inspect.
        #  @return True when the receiver is loaded anywhere in the subtree.
        def receiver_read(node):
            return any(isinstance(child, ast.Name) and child.id == receiver
                       and isinstance(child.ctx, ast.Load) for child in ast.walk(node))

        ## Detect reads of attributes captured by receiver closures.
        ## 检测接收者闭包捕获属性的读取。
        #
        #  @param node AST subtree to inspect.
        #  @return True when a captured receiver attribute is read.
        def captured_read(node):
            return any(isinstance(child, ast.Attribute) and child.attr in captures
                       and (not return_effects or child.attr in namespace)
                       and isinstance(child.value, ast.Name) and child.value.id == receiver
                       for child in ast.walk(node))

        ## Inspect one syntax node and recursively validate receiver behavior.
        ## 检查单个语法节点并递归校验接收者行为。
        #
        #  @param node AST node to inspect.
        #  @param parent Parent node used for context-sensitive checks.
        #  @param captured_store Whether a closure store is explicitly permitted.
        #  @return None; raises _OpenReceiver when effects escape the model.
        def visit(node, parent=None, captured_store=False):
            charge(node)
            if (isinstance(node, ast.Return) and method.name == '__init__'
                    and node.value is not None and not (
                        isinstance(node.value, ast.Constant) and node.value.value is None)):
                raise _OpenReceiver()
            if isinstance(node, ast.Raise) and owner != ref and not return_effects:
                # The consumer selects root guards but does not execute these
                # receiver-only callees. Do not use a vacuous normal-return proof.
                raise _OpenReceiver()
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    and node.id in reflection
                    or isinstance(node, ast.Attribute) and node.attr in reflection):
                raise _OpenReceiver()
            if isinstance(node, (ast.Global, ast.Nonlocal, ast.Await, ast.Yield, ast.YieldFrom,
                                 ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
                                 ast.NamedExpr, ast.ClassDef, ast.Import, ast.ImportFrom)):
                raise _OpenReceiver()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if receiver_read(node) and not (isinstance(node, ast.Lambda) and captured_store):
                    raise _OpenReceiver()
                defaults = node.args.defaults + [v for v in node.args.kw_defaults if v is not None]
                for value in defaults:
                    visit(value)
                return
            if isinstance(node, ast.Assign):
                own_store = (len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
                             and isinstance(node.targets[0].value, ast.Name)
                             and node.targets[0].value.id == receiver)
                if (return_effects and own_store and node.targets[0].attr in namespace):
                    value = known_value(node.value, local_values, receiver)
                    if (len(node.targets) != 1 or value is unknown
                            or type(value) not in (type(None), bool, int, float, str, bytes)):
                        raise _OpenReceiver()
                    setter = property_setter(node.targets[0].attr)
                    setter_params = setter[1].args.posonlyargs + setter[1].args.args
                    if len(setter_params) != 2:
                        raise _OpenReceiver()
                    inspect(setter, active + (definition_key,),
                            {setter_params[1].arg: value})
                    return
                for destination in node.targets:
                    if isinstance(destination, ast.Name):
                        value = known_value(node.value, local_values, receiver)
                        if value is unknown:
                            local_values.pop(destination.id, None)
                        else:
                            local_values[destination.id] = value
                    elif (return_effects and isinstance(destination, ast.Attribute)
                            and isinstance(destination.value, ast.Name)
                            and destination.value.id == receiver):
                        value = known_value(node.value, local_values, receiver)
                        if value is unknown:
                            receiver_values.pop(destination.attr, None)
                        else:
                            receiver_values[destination.attr] = value
                visit(node.value, node, own_store)
                for destination in node.targets:
                    visit(destination, node)
                return
            if isinstance(node, ast.If):
                if return_effects:
                    condition = known_condition(node.test, local_values, receiver,
                                               owner, method)
                    if condition is not unknown:
                        for statement in node.body if condition else node.orelse:
                            visit(statement, node)
                        return
            if isinstance(node, ast.Try):
                if (not return_effects or len(node.body) != 1
                        or not isinstance(node.body[0], ast.Assign)
                        or len(node.body[0].targets) != 1
                        or not isinstance(node.body[0].targets[0], ast.Attribute)
                        or not isinstance(node.body[0].targets[0].value, ast.Name)
                        or node.body[0].targets[0].value.id != receiver
                        or not isinstance(node.body[0].value, ast.Constant)
                        or node.body[0].value.value is not None
                        or node.orelse or node.finalbody or len(node.handlers) != 1):
                    raise _OpenReceiver()
                handler = node.handlers[0]
                if (not isinstance(handler.type, ast.Name) or handler.type.id != 'AttributeError'
                        or analyzer._builtin_name_status(owner, method, 'AttributeError')
                            != 'confirmed_builtin'
                        or len(handler.body) != 1 or not isinstance(handler.body[0], ast.Pass)):
                    raise _OpenReceiver()
                visit(node.body[0], node)
                return
            if isinstance(node, ast.Call):
                if (return_effects and isinstance(node.func, ast.Name) and node.func.id == 'type'
                        and len(node.args) == 1 and not node.keywords
                        and isinstance(node.args[0], ast.Name) and node.args[0].id == receiver
                        and analyzer._builtin_name_status(owner, method, 'type')
                            == 'confirmed_builtin'):
                    return
                selected = None
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == receiver:
                        selected = method_target(node.func.attr)
                elif (isinstance(node.func, ast.Attribute)
                      and isinstance(node.func.value, ast.Call)
                      and isinstance(node.func.value.func, ast.Name)
                      and node.func.value.func.id == 'super'):
                    invocation = node.func.value
                    if (analyzer._builtin_name_status(owner, method, 'super') != 'confirmed_builtin'
                            or invocation.keywords or len(invocation.args) not in (0, 2)):
                        raise _OpenReceiver()
                    enclosing = next((item for item, _ in hierarchy
                                      if item.module == owner.module
                                      and item.qualname == owner.qualname.rpartition('.')[0]), None)
                    if enclosing is None:
                        raise _OpenReceiver()
                    if invocation.args:
                        first, second = invocation.args
                        head = ast.unparse(first).partition('.')[0]
                        if (not isinstance(first, (ast.Name, ast.Attribute))
                                or head in function_scope_facts(method).bound
                                or not analyzer._stable_import_name(owner.module + '.' + head)):
                            raise _OpenReceiver()
                        selected_class = analyzer._resolve_class(owner, ast.unparse(first))
                        if (not selected_class or selected_class[0] != enclosing
                                or not isinstance(second, ast.Name) or second.id != receiver):
                            raise _OpenReceiver()
                    selected = method_target(node.func.attr, after=enclosing)
                if selected is None:
                    if isinstance(node.func, ast.Name) and node.func.id in (
                            'exec', 'eval', 'globals', 'locals', 'vars', '__import__'):
                        raise _OpenReceiver()
                    visit(node.func, node)
                else:
                    calls.add(selected[0].qualname.rsplit('.', 1)[-1])
                    values = {}
                    function_args = selected[1].args
                    positional = function_args.posonlyargs + function_args.args
                    extra_args = node.args[len(positional) - 1:]
                    if (not extra_args and function_args.vararg is not None):
                        values[function_args.vararg.arg] = ()
                    for parameter, argument in zip(positional[1:], node.args):
                        if isinstance(argument, ast.Starred):
                            break
                        value = known_value(argument, local_values, receiver)
                        if value is not unknown:
                            values[parameter.arg] = value
                    explicit_kwargs = {}
                    complete_kwargs = True
                    for keyword in node.keywords:
                        if keyword.arg is None:
                            complete_kwargs = False
                            break
                        value = known_value(keyword.value, local_values, receiver)
                        parameter_names = {argument.arg for argument in positional}
                        parameter_names.update(argument.arg for argument in function_args.kwonlyargs)
                        if keyword.arg in parameter_names:
                            if value is not unknown:
                                values[keyword.arg] = value
                        elif value is not unknown:
                            explicit_kwargs[keyword.arg] = value
                        else:
                            complete_kwargs = False
                    if function_args.kwarg is not None and complete_kwargs:
                        values[function_args.kwarg.arg] = explicit_kwargs
                    inspect(selected, active + (definition_key,), values)
                for argument in node.args + [keyword.value for keyword in node.keywords]:
                    if captured_read(argument):
                        raise _OpenReceiver()
                    visit(argument, node)
                return
            if isinstance(node, ast.Attribute):
                if (isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name)
                        and node.value.id == receiver):
                    reads.add(node.attr)
                if node.attr in forbidden:
                    raise _OpenReceiver()
                if (isinstance(node.ctx, ast.Load) and node.attr in captures
                        and (not return_effects or node.attr in namespace)
                        and isinstance(node.value, ast.Name) and node.value.id == receiver):
                    raise _OpenReceiver()
                if (isinstance(node.ctx, ast.Load) and node.attr in namespace
                        and isinstance(node.value, ast.Name) and node.value.id == receiver):
                    # An arbitrary class member read may invoke a descriptor or
                    # expose a bound method. Direct checked calls are handled above.
                    if not (return_effects and (plain_class_constant(node.attr)
                                                or plain_receiver_property(node.attr))):
                        raise _OpenReceiver()
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    if not isinstance(node.value, ast.Name) or node.value.id != receiver:
                        if receiver_read(node):
                            raise _OpenReceiver()
                    else:
                        writes.append((owner, node.attr, node, parent))
                if isinstance(node.value, ast.Name) and node.value.id == receiver:
                    return
            if (return_effects and isinstance(node, ast.Name) and node.id == receiver
                    and isinstance(parent, ast.Compare) and len(parent.ops) == 1
                    and isinstance(parent.ops[0], (ast.Is, ast.IsNot))
                    and len(parent.comparators) == 1
                    and (parent.left is node or parent.comparators[0] is node)):
                return
            if isinstance(node, ast.Name) and node.id == receiver:
                raise _OpenReceiver()
            for child in ast.iter_child_nodes(node):
                visit(child, node)

        for statement in method.body:
            visit(statement)

    try:
        inspect(target)
    except (RecursionError, _OpenReceiver):
        return None if return_effects else []
    if any(attribute in calls for _, attribute, _, _ in writes):
        return None if return_effects else []
    if any(attribute in namespace for _, attribute, _, _ in writes):
        return None if return_effects else []
    if lookup_name is not None and any(attribute == lookup_name for _, attribute, _, _ in writes):
        return None if return_effects else []
    if any(path not in analyzer.hashes for path in decorator_dependencies):
        return None if return_effects else []
    if return_effects:
        return {'status': 'source_bound',
            'writes': sorted({attribute for _, attribute, _, _ in writes}),
            'checked_methods': [asdict(owner) for owner, _ in checked.values()],
            'calls': sorted(calls),
            'assumptions': sorted(set(binding['assumptions']) | decorator_assumptions),
            'source_hashes': {path: analyzer.hashes[path] for path in sorted(
                {owner.file_path for owner, _ in checked.values()}
                | set(binding['source_hashes']) | decorator_dependencies)}}
    paths = ({owner.file_path for owner, _ in checked.values()}
             | set(binding['source_hashes']) | decorator_dependencies)
    capture = initializer.args.kwarg.arg if initializer.args.kwarg else None
    capture_uses = [node for node in ast.walk(initializer)
                    if isinstance(node, ast.Name) and node.id == capture]
    result = []
    for owner, attribute, destination, statement in writes:
        if (owner != ref or attribute in namespace or attribute.startswith('__')
                or not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(destination.ctx, ast.Store)
                or sum(name == attribute for _, name, _, _ in writes) != 1):
            continue
        result.append({'kind': 'retained_instance_attribute_store', 'status': 'source_bound',
            'basis': 'source_snapshot', 'function': asdict(ref),
            'receiver_class': binding['receiver_class'],
            'receiver': initializer.args.posonlyargs[0].arg if initializer.args.posonlyargs
                        else initializer.args.args[0].arg,
            'attribute': attribute, 'store_protocol': 'ordinary_instance_dict',
            'capture_mapping_parameter': (
                capture if capture and len(capture_uses) == 1
                and statement.value is capture_uses[0] and attribute not in reads else None),
            'retention_scope': 'normal_constructor_return_after_store',
            'runtime_store_confirmed': False,
            'store_evidence': asdict(SourceSpan.from_ast(ref.file_path, statement)),
            'checked_methods': [asdict(owner) for owner, _ in checked.values()],
            'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)},
            'assumptions': sorted(set(binding['assumptions']) | decorator_assumptions
                                  | {'no_external_frame_introspection'})})
    return result
