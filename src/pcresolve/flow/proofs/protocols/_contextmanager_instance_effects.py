"""Bounded effects for source context managers that temporarily set receiver data attributes."""

## @package pcresolve._contextmanager_instance_effects
#  Bounded effects for source context managers that temporarily set receiver data attributes.
#  有界分析临时设置并恢复接收者实例属性的源码上下文管理器效果。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.protocols._contextmanager_namespace import _namespace as contextmanager_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.scope_facts import statement_scope_facts


_BUILTINS = {'object', 'getattr', 'setattr', 'delattr', 'isinstance', 'type', 'property'}
_SPAN = ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')


## Build a dotted name from a simple name or attribute expression.
## 从简单名称或属性表达式构造点分名称。
#
#  @param node AST expression to convert.
#  @return Dotted name, or None for unsupported expression shapes.
def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return head + '.' + node.attr if head else None
    return None


## Resolve a call target under the caller's stable import bindings.
## 根据调用方稳定的导入绑定解析调用目标。
#
#  @param analyzer Source analyzer with imports and definition index.
#  @param caller Source definition containing the call.
#  @param call Call expression to resolve.
#  @return Unique source function pair, or None when unresolved.
def _target(analyzer, caller, call):
    dotted = _dotted(call.func)
    if not dotted:
        return None
    head, dot, tail = dotted.partition('.')
    imported = analyzer.imports.get(caller.module, {}).get(head)
    qualified = (imported + (dot + tail if dot else '') if imported
                 else caller.module + '.' + dotted)
    return analyzer._definition_index.resolve_qualified(
        [qualified], analyzer.imports, kind='function',
        qualified_guard=analyzer._stable_import_name)


## Confirm use of the standard contextlib.contextmanager protocol.
## 确认装饰器使用标准 contextlib.contextmanager 协议。
#
#  @param analyzer Source analyzer providing stable import and namespace facts.
#  @param ref Source definition reference for the decorated function.
#  @param node Function AST node to inspect.
#  @return True only when the standard decorator and namespace are stable.
def _standard_contextmanager(analyzer, ref, node):
    if len(node.decorator_list) != 1:
        return False
    decorator = _dotted(node.decorator_list[0])
    if not decorator:
        return False
    head, dot, tail = decorator.partition('.')
    imported = analyzer.imports.get(ref.module, {}).get(head)
    canonical = imported + (dot + tail if dot else '') if imported else decorator
    if canonical != 'contextlib.contextmanager':
        return False
    try:
        return (analyzer._stable_import_name(ref.module + '.' + head)
                and contextmanager_namespace(analyzer, require_nonobserving=False))
    except _ClassEffectLimit:
        return False


## Match an AST name against an expected identifier.
## 判断 AST 名称是否匹配预期标识符。
#
#  @param node AST node to compare.
#  @param value Expected identifier.
#  @return True when node is the expected name.
def _is_name(node, value):
    return isinstance(node, ast.Name) and node.id == value


## Match a positional call to a named builtin with expected name arguments.
## 匹配名称指定的内建函数及其预期位置参数。
#
#  @param node AST expression to check.
#  @param name Expected callee identifier.
#  @param arguments Expected argument identifiers in order.
#  @return True when the complete call shape matches.
def _is_call(node, name, arguments):
    return (isinstance(node, ast.Call) and _is_name(node.func, name)
            and len(node.args) == len(arguments) and not node.keywords
            and all(_is_name(actual, expected) for actual, expected in
                    zip(node.args, arguments)))


## Match a no-argument items() call on the expected mapping name.
## 匹配对预期映射名称进行的无参 items() 调用。
#
#  @param node AST expression to check.
#  @param mapping Expected mapping identifier.
#  @return True when node has the required mapping-items shape.
def _mapping_items(node, mapping):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and _is_name(node.func.value, mapping) and node.func.attr == 'items'
            and not node.args and not node.keywords)


## Recognize a finite mapping-driven set/yield/finally-restore protocol.
## 识别由有限映射驱动的设置、让出与 finally 恢复协议。
#
#  @param node Context-manager function AST node.
#  @param receiver Receiver parameter identifier.
#  @param capture Keyword-capture parameter identifier.
#  @return True only when the function matches the supported protocol shape.
def _temporary_set_restore_shape(node, receiver, capture):
    body = [item for item in node.body if not (isinstance(item, ast.Expr)
        and isinstance(item.value, ast.Constant) and type(item.value.value) is str)]
    tries = [item for item in body if isinstance(item, ast.Try)]
    if len(tries) != 1:
        return False
    block = tries[0]
    if block is not body[-1] or block.handlers or block.orelse or len(block.body) != 2:
        return False
    set_loop, yield_statement = block.body
    if (not isinstance(set_loop, ast.For) or set_loop.orelse
            or not isinstance(set_loop.target, (ast.Tuple, ast.List))
            or len(set_loop.target.elts) != 2
            or not all(isinstance(item, ast.Name) for item in set_loop.target.elts)
            or not _mapping_items(set_loop.iter, capture)
            or len(set_loop.body) != 1 or not isinstance(set_loop.body[0], ast.Expr)):
        return False
    attribute, value = (item.id for item in set_loop.target.elts)
    if not _is_call(set_loop.body[0].value, 'setattr', [receiver, attribute, value]):
        return False
    if (not isinstance(yield_statement, ast.Expr)
            or not isinstance(yield_statement.value, ast.Yield)
            or yield_statement.value.value is not None
            or len(block.finalbody) != 1 or not isinstance(block.finalbody[0], ast.For)):
        return False
    restore = block.finalbody[0]
    if (restore.orelse or not isinstance(restore.target, (ast.Tuple, ast.List))
            or len(restore.target.elts) != 2
            or not all(isinstance(item, ast.Name) for item in restore.target.elts)
            or not _mapping_items(restore.iter, 'origs') or len(restore.body) != 1
            or not isinstance(restore.body[0], ast.If)):
        return False
    restore_key, original = (item.id for item in restore.target.elts)
    guard = restore.body[0]
    if (not isinstance(guard.test, ast.Compare) or len(guard.test.ops) != 1
            or not isinstance(guard.test.ops[0], ast.Is) or len(guard.test.comparators) != 1
            or not _is_name(guard.test.left, original)
            or not isinstance(guard.test.comparators[0], ast.Name)
            or not isinstance(guard.body, list) or len(guard.body) != 1
            or not isinstance(guard.body[0], ast.Expr)
            or not _is_call(guard.body[0].value, 'delattr', [receiver, restore_key])
            or len(guard.orelse) != 1 or not isinstance(guard.orelse[0], ast.Expr)
            or not _is_call(guard.orelse[0].value, 'setattr',
                            [receiver, restore_key, original])):
        return False

    # Before entering the try block, every supplied key is saved. For keys
    # statically absent from both the class layout and receiver dictionary,
    # this exact guard selects the first arm and stores the sentinel.
    # 进入 try 前保存每个输入键；静态确认不存在的键会通过此守卫保存哨兵值。
    initializer = next((item for item in body if isinstance(item, ast.Assign)
                        and len(item.targets) == 1 and _is_name(item.targets[0], 'origs')
                        and isinstance(item.value, ast.Dict)
                        and not item.value.keys and not item.value.values), None)
    loops = [item for item in body if isinstance(item, ast.For)
             and _is_name(item.iter, capture)]
    if (initializer is None or len(loops) != 1 or body.index(loops[0]) > body.index(block)
            or not isinstance(loops[0].target, ast.Name)
            or loops[0].target.id != attribute or loops[0].orelse
            or len(loops[0].body) != 2 or not isinstance(loops[0].body[0], ast.Assign)
            or len(loops[0].body[0].targets) != 1
            or not _is_name(loops[0].body[0].targets[0], original)
            or not _is_call(loops[0].body[0].value, 'getattr',
                            [receiver, attribute, 'sentinel'])
            or not isinstance(loops[0].body[1], ast.If)):
        return False
    sentinel = next((item for item in body if isinstance(item, ast.Assign)
                     and len(item.targets) == 1 and _is_name(item.targets[0], 'sentinel')
                     and _is_call(item.value, 'object', [])), None)
    if sentinel is None:
        return False
    save_guard = loops[0].body[1]
    test = save_guard.test
    if (not isinstance(test, ast.BoolOp) or not isinstance(test.op, ast.Or)
            or len(test.values) != 2
            or not isinstance(test.values[0], ast.Compare)
            or len(test.values[0].ops) != 1
            or not isinstance(test.values[0].ops[0], ast.In)
            or not _is_name(test.values[0].left, attribute)
            or len(test.values[0].comparators) != 1
            or not isinstance(test.values[0].comparators[0], ast.Attribute)
            or test.values[0].comparators[0].attr != '__dict__'
            or not _is_name(test.values[0].comparators[0].value, receiver)
            or not isinstance(test.values[1], ast.Compare)
            or len(test.values[1].ops) != 1 or not isinstance(test.values[1].ops[0], ast.Is)
            or not _is_name(test.values[1].left, original)
            or len(test.values[1].comparators) != 1
            or not _is_name(test.values[1].comparators[0], 'sentinel')):
        return False
    ## Match an assignment that stores a selected value in the originals map.
    ## 匹配将指定值写入 originals 映射的赋值语句。
    #
    #  @param statement Candidate AST statement.
    #  @param value Expected source identifier.
    #  @return True when the assignment has the required exact shape.
    def save_assignment(statement, value):
        return (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Subscript)
                and _is_name(statement.targets[0].value, 'origs')
                and _is_name(statement.targets[0].slice, attribute)
                and _is_name(statement.value, value))

    if (len(save_guard.body) != 1 or not save_assignment(save_guard.body[0], original)
            or len(save_guard.orelse) != 2 or not isinstance(save_guard.orelse[0], ast.Assign)
            or len(save_guard.orelse[0].targets) != 1
            or not _is_name(save_guard.orelse[0].targets[0], 'cls_orig')):
        return False
    class_getattr = save_guard.orelse[0].value
    if (not isinstance(class_getattr, ast.Call) or not _is_name(class_getattr.func, 'getattr')
            or len(class_getattr.args) != 2 or class_getattr.keywords
            or not isinstance(class_getattr.args[0], ast.Call)
            or not _is_name(class_getattr.args[0].func, 'type')
            or len(class_getattr.args[0].args) != 1 or class_getattr.args[0].keywords
            or not _is_name(class_getattr.args[0].args[0], receiver)
            or not _is_name(class_getattr.args[1], attribute)):
        return False
    property_guard = save_guard.orelse[1]
    if (not isinstance(property_guard, ast.If)
            or not isinstance(property_guard.test, ast.Call)
            or not _is_name(property_guard.test.func, 'isinstance')
            or len(property_guard.test.args) != 2 or property_guard.test.keywords
            or not _is_name(property_guard.test.args[0], 'cls_orig')
            or not _is_name(property_guard.test.args[1], 'property')
            or len(property_guard.body) != 1
            or not save_assignment(property_guard.body[0], original)
            or len(property_guard.orelse) != 1
            or not save_assignment(property_guard.orelse[0], 'sentinel')):
        return False
    return True


## Prove that a finite context manager only saves, sets, and restores receiver attributes.
## 证明有限上下文管理器仅保存、设置并恢复接收者实例属性。
#
#  @param summary Active effect summary with source and evidence access.
#  @param expression Context-manager call expression to inspect.
#  @param env Abstract values available at the call site.
#  @return Bounded temporary-attribute effect, or None when proof is incomplete.
def temporary_receiver_attributes(summary, expression, env):
    if (not isinstance(expression, ast.Call) or len(expression.args) != 1
            or not isinstance(expression.args[0], ast.Name) or not expression.keywords
            or any(item.arg is None or not isinstance(item.value, ast.Constant)
                   for item in expression.keywords)
            or len({item.arg for item in expression.keywords}) != len(expression.keywords)):
        return None
    receiver_name = expression.args[0].id
    receiver_values = env.get(receiver_name, [])
    origins = [value.get('fresh_receiver_origin') for value in receiver_values]
    if (not origins or not origins[0]
            or any(origin != origins[0] for origin in origins)
            or any(value.get('value_incomplete') or value.get('relation') != 'direct'
                   or value.get('instance_type') != origins[0]['allocation']['receiver_class']
                   for value in receiver_values)):
        return None
    origin = origins[0]
    if (origin.get('current_function') != asdict(summary.ref)
            or origin.get('parameter') != receiver_name
            or origin['allocation'].get('source_hashes') != summary.analyzer.hashes):
        return None
    selected = _target(summary.analyzer, summary.ref, expression)
    if selected is None:
        return None
    ref, function = selected
    if (not isinstance(function, ast.FunctionDef) or function.args.kwarg is None
            or function.args.vararg or function.args.kwonlyargs or function.args.defaults
            or len(function.args.posonlyargs + function.args.args) != 1
            or function.decorator_list == []
            or not _standard_contextmanager(summary.analyzer, ref, function)):
        return None
    receiver_parameter = (function.args.posonlyargs + function.args.args)[0].arg
    keyword_parameter = function.args.kwarg.arg
    keyword_names = {item.arg for item in expression.keywords}
    if not _temporary_set_restore_shape(function, receiver_parameter, keyword_parameter):
        return None

    hierarchy = summary.analyzer._class_mro(
        origin['allocation']['receiver_class']['module'],
        origin['allocation']['receiver_class']['qualname'])
    if not hierarchy:
        return None
    class_names = set().union(*(statement_scope_facts(cls.body).bound for _, cls in hierarchy))
    # A temporary write to a class attribute could invoke a descriptor. When
    # the key is absent from the closed class namespace, an existing own value
    # is an ordinary instance-dictionary entry and the manager's validated
    # save/restore protocol is bounded for either presence state.
    if keyword_names & class_names:
        return None

    body_nodes = list(ast.walk(function))
    if any(isinstance(node, (ast.AsyncFunctionDef, ast.Lambda, ast.YieldFrom,
                             ast.Await, ast.Global, ast.Nonlocal))
           for node in body_nodes):
        return None
    yields = [node for node in body_nodes if isinstance(node, ast.Yield)]
    tries = [node for node in body_nodes if isinstance(node, ast.Try)]
    if (len(yields) != 1 or len(tries) != 1 or not tries[0].finalbody
            or not any(child is yields[0] for statement in tries[0].body
                       for child in ast.walk(statement))):
        return None

    loops = []
    local_dicts = set()
    key_names = set()
    for node in body_nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (isinstance(target, ast.Name) and isinstance(node.value, ast.Dict)
                    and not node.value.keys and not node.value.values):
                local_dicts.add(target.id)
            if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                    and target.value.id in local_dicts and isinstance(target.slice, ast.Name)):
                key_names.add(target.slice.id)
        if isinstance(node, ast.For):
            iterator = node.iter
            owner = (iterator.func.value.id if isinstance(iterator, ast.Call)
                     and isinstance(iterator.func, ast.Attribute)
                     and iterator.func.attr == 'items' and isinstance(iterator.func.value, ast.Name)
                     and not iterator.args and not iterator.keywords else
                     iterator.id if isinstance(iterator, ast.Name) else None)
            if owner not in {keyword_parameter} | local_dicts:
                return None
            first = node.target.elts[0] if isinstance(node.target, (ast.Tuple, ast.List)) \
                and node.target.elts else node.target
            if not isinstance(first, ast.Name):
                return None
            key_names.add(first.id)
            loops.append(node)
    if not loops or not keyword_names:
        return None

    mutation_count = 0
    for call in (node for node in body_nodes if isinstance(node, ast.Call)):
        if isinstance(call.func, ast.Name) and call.func.id in _BUILTINS:
            if summary.analyzer._builtin_name_status(
                    ref, function, call.func.id) != 'confirmed_builtin':
                return None
            if call.func.id in ('setattr', 'delattr'):
                mutation_count += 1
                if (len(call.args) != (3 if call.func.id == 'setattr' else 2)
                        or call.keywords or not isinstance(call.args[0], ast.Name)
                        or call.args[0].id != receiver_parameter
                        or not isinstance(call.args[1], ast.Name)
                        or call.args[1].id not in key_names):
                    return None
        elif (isinstance(call.func, ast.Attribute) and call.func.attr == 'items'
                and isinstance(call.func.value, ast.Name) and not call.args and not call.keywords
                and call.func.value.id in {keyword_parameter} | local_dicts):
            continue
        else:
            return None
    if mutation_count < 2:
        return None

    if any(isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
           for node in body_nodes):
        return None
    if any(isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del))
           and (not isinstance(node.value, ast.Name) or node.value.id not in local_dicts)
           for node in body_nodes):
        return None
    return {
        'kind': 'bounded_temporary_receiver_attributes',
        'manager': asdict(ref),
        'receiver_parameter': receiver_name,
        'receiver_class': origin['allocation']['receiver_class'],
        'receiver_origin': origin,
        'prior_own_attributes': list(origin.get('own_attributes', ())),
        'attributes': sorted(keyword_names),
        'evidence': {
            'function': {'file_path': ref.file_path, 'lineno': function.lineno,
                         'end_lineno': function.end_lineno},
            'decorator': {'file_path': ref.file_path,
                          'lineno': function.decorator_list[0].lineno,
                          'end_lineno': function.decorator_list[0].end_lineno},
            'invocation': summary.evidence(expression),
            'yield': summary.evidence_at(ref, yields[0]),
        },
        'source_hashes': dict(sorted(summary.analyzer.hashes.items())),
        'restored_on_all_exits': True,
        'body_exception_behavior': 'propagates_if_cleanup_completes',
        'runtime_protocol_confirmed': False,
        'assumptions': ['standard_library_contextmanager_protocol',
                        'source_snapshot_bindings_hold',
                        'no_external_monkeypatch_or_import_hook',
                        'builtin_instance_data_attribute_operations'],
    }
