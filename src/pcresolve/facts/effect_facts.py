## @package pcresolve.facts.effect_facts
#  Collect shared source effect facts.
#
#
#  Describes supported builtin-container and straight-line function effects without choosing an owner.
#  描述受支持的内置容器及顺序执行函数效果，不决定调用归属。



import ast
from dataclasses import dataclass


## Walk immediate evaluation, including declaration inputs but not deferred bodies.
## 遍历立即求值部分，包括声明输入但不包括延迟执行的函数体。
#
#  @param root Source execution scope to inspect.
#  @return Iterator of AST nodes evaluated within this scope.
def execution_nodes(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        # Defaults, annotations and decorators execute without invoking the body.
        # 默认值、注解和装饰器无需调用函数体即可求值。
        if node is not root and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            children = list(getattr(node, 'decorator_list', [])) + list(node.args.defaults)
            children.extend(value for value in node.args.kw_defaults if value is not None)
            arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
            children.extend(arg.annotation for arg in arguments if arg.annotation is not None)
            if getattr(node, 'returns', None) is not None:
                children.append(node.returns)
        else:
            children = list(ast.iter_child_nodes(node))
        pending.extend(reversed(children))


## Describe syntactic evaluation prerequisites without claiming reachability.
## 描述语法求值前提，不据此断言代码可达。
#
#  @param root Source tree or expression; no source is executed.
#  @return Iterator of (node, prerequisite tuple) pairs. Each prerequisite pairs
#          a phase kind with its source declaration/generator node. Empty means
#          no deferred-body prerequisite, not guaranteed execution or completion.
def evaluation_contexts(root):
    pending = [(root, ())]
    while pending:
        node, requirements = pending.pop()
        yield node, requirements
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            inputs = list(getattr(node, 'decorator_list', [])) + list(node.args.defaults)
            inputs.extend(value for value in node.args.kw_defaults if value is not None)
            arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
            inputs.extend(arg.annotation for arg in arguments if arg.annotation is not None)
            if getattr(node, 'returns', None) is not None:
                inputs.append(node.returns)
            body_requirements = requirements + (('function_invocation', node),)
            if isinstance(node, ast.AsyncFunctionDef):
                phase = 'async_generator_resumption' if contains_yield(node) else 'coroutine_resumption'
                body_requirements += ((phase, node),)
            elif contains_yield(node):
                body_requirements += (('generator_resumption', node),)
            body = [node.body] if isinstance(node, ast.Lambda) else node.body
            children = [(item, requirements) for item in inputs]
            children.extend((item, body_requirements) for item in body)
        elif isinstance(node, ast.GeneratorExp):
            # The first iterable is evaluated immediately; the remaining work is deferred.
            # 首个可迭代表达式立即求值，其余工作延迟到生成器恢复执行。
            deferred = requirements + (('generator_resumption', node),)
            children = [(node.elt, deferred)]
            for index, generator in enumerate(node.generators):
                children.append((generator.iter, requirements if index == 0 else deferred))
                children.append((generator.target, deferred))
                children.extend((condition, deferred) for condition in generator.ifs)
        else:
            children = [(child, requirements) for child in ast.iter_child_nodes(node)]
        pending.extend(reversed(children))


## Match syntax for a finite builtin exception handler that only raises again.
## 匹配只重新抛出有限内置异常的处理器语法。
#
#  @param handler ExceptHandler source node; no source is executed.
#  @return Syntactic translation shape, or None; builtin bindings and data effects
#          still require a caller-specific proof.
def builtin_exception_translation(handler):
    supported = {'KeyError', 'TypeError', 'ValueError', 'AttributeError'}
    if (not isinstance(handler, ast.ExceptHandler) or len(handler.body) != 1
            or not isinstance(handler.body[0], ast.Raise)):
        return None
    caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    if (not 1 <= len(caught) <= 4
            or any(not isinstance(item, ast.Name) or item.id not in supported for item in caught)):
        return None
    raised = handler.body[0]
    if (not isinstance(raised.exc, ast.Call) or not isinstance(raised.exc.func, ast.Name)
            or raised.exc.func.id not in supported or raised.exc.keywords
            or any(not isinstance(arg, (ast.Name, ast.Constant)) for arg in raised.exc.args)):
        return None
    if raised.cause is None:
        cause = 'implicit_context'
    elif isinstance(raised.cause, ast.Constant) and raised.cause.value is None:
        cause = 'suppressed_context'
    elif (handler.name is not None and isinstance(raised.cause, ast.Name)
            and raised.cause.id == handler.name):
        cause = 'caught_exception'
    else:
        return None
    return {'caught_types': [item.id for item in caught], 'exception_name': handler.name,
            'raised_type': raised.exc.func.id, 'cause_kind': cause,
            'argument_names': [arg.id for arg in raised.exc.args if isinstance(arg, ast.Name)]}


## Exact supported behavior of one builtin container method call.
## 一个内置容器方法调用受支持的精确行为。
@dataclass(frozen=True)
class ContainerMethodEffect:
    ## Canonical operation name.
    operation: str
    ## Formal names for positional arguments.
    parameters: tuple
    ## Whether the operation changes the receiver.
    mutates_receiver: bool

    ## Freeze the formal parameter names used by this effect.
    ## 将此效果使用的形参名固定为元组。
    #
    #  @return None
    def __post_init__(self):
        object.__setattr__(self, 'parameters', tuple(self.parameters))


## One exact write in a complete straight-line function summary.
## 完整顺序函数摘要中的一个精确写入效果。
@dataclass(frozen=True)
class FunctionEffect:
    ## Canonical effect kind.
    kind: str
    ## Receiver parameter or nonlocal binding name.
    target: str
    ## Value parameter or capture name, when applicable.
    source: object
    ## AST statement providing source evidence.
    statement: object
    ## Required builtin receiver shape; None for the older protocol summaries.
    receiver_shape: object = None
    ## Constant element path, empty for whole-container effects.
    element_path: tuple = ()
    ## Possible exception before normal completion, when known.
    may_raise: object = None
    ## Finite-key iteration syntax; concrete sequence is supplied by the adapter.
    sequence_loop: object = None
    ## Membership guard protecting an element deletion.
    membership_test: object = None
    ## Instance attribute written by a source-bound method effect.
    attribute: object = None
    ## Source guards that must hold for the effect site.
    conditions: tuple = ()
    ## Original right-hand-side expression for an instance-field write.
    source_expression: object = None
    ## Non-boolean execution contexts such as a try handler or loop.
    contexts: tuple = ()


## Match a builtin container method by receiver shapes and positional arity.
## 根据接收者形态和位置实参数量匹配内置容器方法。
#  Keyword and expansion uncertainty remains an adapter policy.
#
#  @param method Attribute method name.
#  @param receiver_shapes Iterable of proven builtin container kinds.
#  @param positional_count Number of syntactic positional arguments.
#  @return ContainerMethodEffect or None when no exact contract is supported.
def container_method_effect(method, receiver_shapes, positional_count):
    shapes = frozenset(receiver_shapes)
    if method == 'append' and shapes == frozenset(('list',)):
        if positional_count == 1:
            return ContainerMethodEffect('append', ('object',), True)
        return None
    if method == 'clear' and shapes and shapes <= frozenset(
            ('list', 'set', 'dict')):
        if positional_count == 0:
            return ContainerMethodEffect('clear', (), True)
        return None
    if method == 'get' and shapes == frozenset(('dict',)):
        if positional_count in (1, 2):
            return ContainerMethodEffect('get', ('key', 'default'), False)
        return None
    if method == 'copy' and shapes == frozenset(('dict',)):
        if positional_count == 0:
            return ContainerMethodEffect('copy', (), False)
        return None
    if method == 'setdefault' and shapes == frozenset(('dict',)):
        if positional_count in (1, 2):
            return ContainerMethodEffect('mapping_setdefault', ('key', 'default'), True)
        return None
    if method == 'pop' and shapes == frozenset(('list',)):
        if positional_count in (0, 1):
            return ContainerMethodEffect('pop', ('index',), True)
        return None
    if method == 'pop' and shapes == frozenset(('dict',)):
        if positional_count in (1, 2):
            return ContainerMethodEffect('mapping_pop', ('key', 'default'), True)
        return None
    if method == 'update' and shapes == frozenset(('dict',)):
        if positional_count in (0, 1):
            return ContainerMethodEffect('mapping_update', ('other',), True)
        return None
    return None


## Determine whether a body yields without entering nested definitions.
## 判断当前函数体是否 yield，不进入嵌套定义。
#
#  @param node Root function, lambda, or expression AST.
#  @return True when the root execution contains Yield or YieldFrom.
def contains_yield(node):
    found = False

    ## Search this execution body until a yield is found.
    ## 在当前执行体中搜索 yield，找到后停止。
    #
    #  @param item AST node to inspect.
    #  @return None
    def visit(item):
        nonlocal found
        if found:
            return
        if item is not node and isinstance(
                item, (ast.FunctionDef, ast.AsyncFunctionDef,
                       ast.ClassDef, ast.Lambda)):
            return
        if isinstance(item, (ast.Yield, ast.YieldFrom)):
            found = True
            return
        for child in ast.iter_child_nodes(item):
            visit(child)

    visit(node)
    return found


## Extract all effects from a supported straight-line function body.
## 从受支持的顺序函数体中提取全部效果。
#  A partial summary is never returned: unsupported statements and generators
#  produce None so callers do not apply an incomplete set of writes.
#  Ordinary-parameter aliases and constant-string-key pop/delete facts retain
#  receiver shape prerequisites, not an inferred type for generic parameters.
#  Effects describe normal completion; required-key removals may raise KeyError.
#
#  @param node Candidate function definition.
#  @param call_effects Optional adapter proving complete effects of source helper calls.
#  @return FunctionEffect tuple, or None when the whole body is unsupported.
def function_effects(node, call_effects=None):
    if not isinstance(node, ast.FunctionDef) or contains_yield(node):
        return None
    body = [statement for statement in node.body
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str))]
    if any(isinstance(statement, ast.Global) for statement in body):
        return None
    nonlocal_names = {
        name for statement in body if isinstance(statement, ast.Nonlocal)
        for name in statement.names}
    ordinary = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    aliases = {argument.arg: argument.arg for argument in ordinary}

    ## Recognize a constant-key mapping pop and its possible exception.
    ## 识别常量键映射 pop 及其可能抛出的异常。
    #
    #  @param value Candidate call expression.
    #  @param statement Statement supplying evidence.
    #  @return FunctionEffect or None for an unsupported shape.
    def mapping_pop(value, statement):
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Attribute)
                or value.func.attr != 'pop'
                or not isinstance(value.func.value, ast.Name)
                or value.func.value.id not in aliases
                or value.keywords or len(value.args) not in (1, 2)
                or not isinstance(value.args[0], ast.Constant)
                or not isinstance(value.args[0].value, str)
                or (len(value.args) == 2
                    and not isinstance(value.args[1], ast.Constant))):
            return None
        return FunctionEffect('mapping_pop', aliases[value.func.value.id], None,
                              statement, 'dict', (value.args[0].value,),
                              'KeyError' if len(value.args) == 1 else None)

    ## Extract a flat instance-field assignment with a directly traceable value.
    ## 提取右值可直接追踪的单层实例字段赋值。
    #
    #  @param statement Candidate assignment statement.
    #  @param conditions Source guards enclosing the assignment.
    #  @return FunctionEffect or None for unsupported receiver or value syntax.
    def instance_field_write(statement, conditions=()):
        if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(statement.targets[0], ast.Attribute)
                or not isinstance(statement.targets[0].value, ast.Name)
                or statement.targets[0].value.id not in aliases):
            return None
        value = statement.value
        if not ((isinstance(value, ast.Name) and value.id in aliases)
                or isinstance(value, ast.Constant)):
            return None
        source = aliases[value.id] if isinstance(value, ast.Name) else value
        return FunctionEffect('instance_field_write',
            aliases[statement.targets[0].value.id], source, statement,
            attribute=statement.targets[0].attr, conditions=tuple(conditions),
            source_expression=value)

    # Reject the entire summary on an unsupported statement, never a partial write set.
    # 遇到不支持的语句时拒绝整个摘要，避免输出不完整的写入集合。
    effects = []
    for statement in body:
        if isinstance(statement, (ast.Nonlocal, ast.Pass)):
            continue
        field_effect = instance_field_write(statement)
        if field_effect is not None:
            effects.append(field_effect)
            continue
        if (isinstance(statement, ast.If) and not statement.orelse
                and len(statement.body) == 1):
            field_effect = instance_field_write(
                statement.body[0], ((statement.test, True),))
            if field_effect is not None:
                effects.append(field_effect)
                continue
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id not in nonlocal_names
                and isinstance(statement.value, ast.Name)
                and statement.value.id in aliases):
            aliases[statement.targets[0].id] = aliases[statement.value.id]
            continue
        if (isinstance(statement, ast.For) and not statement.orelse
                and isinstance(statement.target, ast.Name)
                and isinstance(statement.iter, ast.Name) and statement.iter.id in aliases
                and statement.target.id not in aliases and len(statement.body) == 1
                and isinstance(statement.body[0], ast.If)):
            branch = statement.body[0]
            test = branch.test
            if (not branch.orelse and len(branch.body) == 1
                    and isinstance(branch.body[0], ast.Delete)
                    and len(branch.body[0].targets) == 1
                    and isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.In) and len(test.comparators) == 1
                    and isinstance(test.left, ast.Name) and test.left.id == statement.target.id
                    and isinstance(test.comparators[0], ast.Name)
                    and test.comparators[0].id in aliases):
                target = branch.body[0].targets[0]
                if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                        and target.value.id == test.comparators[0].id
                        and isinstance(target.slice, ast.Name)
                        and target.slice.id == statement.target.id):
                    effects.append(FunctionEffect('mapping_delete_keys',
                        aliases[target.value.id], aliases[statement.iter.id],
                        branch.body[0], 'dict', (), None, statement, test))
                    continue
        if isinstance(statement, (ast.Expr, ast.Return)):
            effect = mapping_pop(statement.value, statement)
            if effect is not None:
                effects.append(effect)
                if isinstance(statement, ast.Return):
                    return tuple(effects)
                continue
        if isinstance(statement, ast.Delete) and len(statement.targets) == 1:
            target = statement.targets[0]
            if (isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in aliases
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)):
                effects.append(FunctionEffect(
                    'mapping_delete', aliases[target.value.id], None,
                    statement, 'dict', (target.slice.value,), 'KeyError'))
                continue
        if isinstance(statement, ast.Return):
            if (statement.value is None or isinstance(statement.value, ast.Constant)
                    or isinstance(statement.value, ast.Name)
                    and statement.value.id in aliases):
                return tuple(effects)
            return None
        if (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and not statement.value.keywords):
            call = statement.value
            target = aliases.get(call.func.value.id, call.func.value.id)
            if (call.func.attr == 'append' and len(call.args) == 1
                    and isinstance(call.args[0], ast.Name)):
                effects.append(FunctionEffect(
                    'container_append', target, call.args[0].id, statement))
                continue
            if call.func.attr == 'clear' and not call.args:
                effects.append(FunctionEffect(
                    'container_clear', target, None, statement))
                continue
        if (isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id in nonlocal_names
                and isinstance(statement.value, ast.Name)):
            effects.append(FunctionEffect(
                'nonlocal_write', statement.targets[0].id,
                statement.value.id, statement))
            continue
        if (call_effects is not None and isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)):
            nested = call_effects(statement, aliases)
            if nested is not None:
                effects.extend(nested)
                continue
        return None
    return tuple(effects)


## Collect direct receiver-field write sites without claiming completeness.
## 收集直接接收者字段写入位置，但不声称副作用摘要完整。
#
#  @param node Candidate source method.
#  @return Field write sites with syntactic conditions and exception contexts.
def instance_field_write_sites(node):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ()
    parameters = node.args.posonlyargs + node.args.args
    if not parameters:
        return ()
    receiver = parameters[0].arg
    aliases = {receiver}
    sites = []

    ## Decide whether a suite has no normal continuation.
    ## 判断语句组是否不存在正常后续路径。
    #
    #  @param statements Suite to inspect.
    #  @return True when every represented path exits abruptly.
    def terminates(statements):
        if not statements:
            return False
        last = statements[-1]
        if isinstance(last, (ast.Raise, ast.Return, ast.Break, ast.Continue)):
            return True
        if isinstance(last, ast.If):
            return terminates(last.body) and terminates(last.orelse)
        return False

    ## Visit immediate statements while recording enclosing control syntax.
    ## 遍历当前执行体的语句，并记录外围控制语法。
    #
    #  @param statements Statements in one execution suite.
    #  @param conditions Boolean guards enclosing the suite.
    #  @param contexts Non-boolean execution contexts enclosing the suite.
    #  @param receiver_aliases Names already known to alias the receiver.
    #  @return None
    def visit(statements, conditions=(), contexts=(), receiver_aliases=None):
        receiver_aliases = set(receiver_aliases or (receiver,))
        active_conditions = tuple(conditions)
        for statement in statements:
            if isinstance(statement, (ast.Raise, ast.Return, ast.Break, ast.Continue)):
                break
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and isinstance(statement.value, ast.Name)
                    and statement.value.id in receiver_aliases):
                receiver_aliases.add(statement.targets[0].id)
                continue
            target = (statement.targets[0] if isinstance(statement, ast.Assign)
                      and len(statement.targets) == 1 else
                      statement.target if isinstance(statement, ast.AnnAssign) else None)
            if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                    and target.value.id in receiver_aliases):
                sites.append(FunctionEffect('instance_field_write', receiver, None,
                    statement, attribute=target.attr, conditions=active_conditions,
                    source_expression=(statement.value if isinstance(statement, ast.Assign)
                                       else statement.value), contexts=tuple(contexts)))
                continue
            if isinstance(statement, ast.If):
                visit(statement.body, active_conditions + ((statement.test, True),), contexts,
                      receiver_aliases)
                visit(statement.orelse, active_conditions + ((statement.test, False),), contexts,
                      receiver_aliases)
                true_terminates = terminates(statement.body)
                false_terminates = terminates(statement.orelse)
                if true_terminates and false_terminates:
                    break
                if true_terminates != false_terminates:
                    active_conditions += ((statement.test, not true_terminates),)
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                      ast.Lambda)):
                continue
            if isinstance(statement, ast.Try):
                visit(statement.body, active_conditions,
                      contexts + (('try_body', statement),), receiver_aliases)
                for handler in statement.handlers:
                    visit(handler.body, active_conditions,
                          contexts + (('exception_handler', handler),), receiver_aliases)
                visit(statement.orelse, active_conditions,
                      contexts + (('try_else', statement),), receiver_aliases)
                visit(statement.finalbody, active_conditions,
                      contexts + (('finally', statement),), receiver_aliases)
                continue
            if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                visit(statement.body, active_conditions,
                      contexts + (('loop', statement),), receiver_aliases)
                visit(statement.orelse, active_conditions,
                      contexts + (('loop_else', statement),), receiver_aliases)
                continue
    visit(node.body)
    return tuple(sites)


## Extract guarded deletion sites without claiming a complete effect summary.
## 提取受条件保护的删除位置，不声称得到完整效果摘要。
#  Additional statements may throw, mutate or escape; these facts describe
#  conditional source operations only, never normal-return postconditions.
#
#  @param node Source function with ordinary mapping and sequence parameters.
#  @return Symbolic sites; None of them authorizes a strong update by itself.
def finite_key_delete_sites(node):
    if not isinstance(node, ast.FunctionDef) or contains_yield(node):
        return ()
    aliases = {argument.arg: argument.arg for argument in node.args.posonlyargs
               + node.args.args + node.args.kwonlyargs}
    sites = []
    for statement in node.body:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, ast.Name) and statement.value.id in aliases):
            aliases[statement.targets[0].id] = aliases[statement.value.id]
            continue
        if (not isinstance(statement, ast.For) or statement.orelse
                or not isinstance(statement.iter, ast.Name) or statement.iter.id not in aliases
                or not isinstance(statement.target, ast.Name) or statement.target.id in aliases
                or len(statement.body) != 1 or not isinstance(statement.body[0], ast.If)):
            break

        # These sites are conditional evidence, not proof of a normal-return update.
        # 这些位置仅是条件性证据，不能证明正常返回后的更新。
        branch = statement.body[0]
        test = branch.test
        if (branch.orelse or not isinstance(test, ast.Compare) or len(test.ops) != 1
                or not isinstance(test.ops[0], ast.In) or len(test.comparators) != 1
                or not isinstance(test.left, ast.Name) or test.left.id != statement.target.id
                or not isinstance(test.comparators[0], ast.Name)
                or test.comparators[0].id not in aliases):
            break
        receiver, key = test.comparators[0].id, statement.target.id
        if any(isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del))
               and child.id in (receiver, key) for body in branch.body for child in ast.walk(body)):
            break
        for body in branch.body:
            if isinstance(body, ast.Delete) and len(body.targets) == 1:
                target = body.targets[0]
                if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                        and target.value.id == receiver and isinstance(target.slice, ast.Name)
                        and target.slice.id == key):
                    sites.append(FunctionEffect('mapping_delete_keys', aliases[receiver],
                        aliases[statement.iter.id], body, 'dict', (), None, statement, test))
    return tuple(sites)
