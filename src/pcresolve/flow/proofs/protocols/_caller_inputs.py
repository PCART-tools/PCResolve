## @package pcresolve.flow.proofs.protocols._caller_inputs
#  Collect bounded caller-input facts.
#
#
#  Bounded caller literals, independent of library policy and runtime execution.
#  与库策略和运行时执行无关的有界调用方字面量事实。



import ast
import math
from dataclasses import asdict

from pcresolve.facts.import_facts import import_facts
from pcresolve.facts.program_facts import SourceSpan
from pcresolve.frontend.source_snapshot import FLOW_SOURCE, SourceStore
from pcresolve.flow.proofs.protocols._stub_iterability import iterable_return_fact


## Copy a literal fact subject to shared item and nesting limits.
## 在共享元素数和嵌套深度限制下复制字面量事实。
#
#  @param value Literal fact to copy.
#  @param remaining Mutable remaining item budget.
#  @param depth Current nesting depth.
#  @return Copied fact or None when a limit is exceeded.
def _copy_literal(value, remaining, depth):
    remaining[0] -= 1
    if remaining[0] < 0 or depth > 16:
        return None
    if value['kind'] == 'scalar':
        return dict(value)
    items = [_copy_literal(item, remaining, depth + 1) for item in value['items']]
    return dict(value, items=items) if all(item is not None for item in items) else None


## Extract a finite literal or previously known literal binding.
## 提取有限字面量或先前已知的字面量绑定。
#
#  @param node Expression AST.
#  @param environment Known name bindings and their evidence.
#  @param remaining Mutable remaining item budget.
#  @param evidence List receiving binding evidence.
#  @param depth Current nesting depth.
#  @return Literal fact or None when unsupported or bounded out.
def _literal(node, environment, remaining, evidence, depth=0):
    remaining[0] -= 1
    if remaining[0] < 0 or depth > 16:
        return None
    if isinstance(node, ast.Name):
        known = environment.get(node.id)
        if known is not None:
            evidence.extend(known[1])
            return _copy_literal(known[0], remaining, depth)
        return None
    if isinstance(node, ast.Constant):
        value = node.value
        if type(value) in (str, int, bool, type(None)):
            return {'kind': 'scalar', 'type': type(value).__name__, 'value': value}
        if type(value) is float and math.isfinite(value):
            return {'kind': 'scalar', 'type': 'float', 'value': value}
        if type(value) is bytes:
            return {'kind': 'scalar', 'type': 'bytes', 'value_hex': value.hex()}
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_literal(child, environment, remaining, evidence, depth + 1)
                  for child in node.elts]
        if all(value is not None for value in values):
            return {'kind': 'list' if isinstance(node, ast.List) else 'tuple', 'items': values}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _literal(node.operand, environment, remaining, evidence, depth + 1)
        if value and value.get('kind') == 'scalar' and value.get('type') in ('int', 'float'):
            if isinstance(node.op, ast.USub):
                value['value'] = -value['value']
            return value
    return None


## Check for expression syntax whose evaluation requires additional proof.
## 检查求值需要额外证明的表达式语法。
#
#  @param node Expression AST.
#  @return True if any unsupported potentially effectful syntax occurs.
def _has_effectful_syntax(node):
    return any(isinstance(child, (ast.Call, ast.Attribute, ast.Subscript,
                                 ast.Await, ast.Yield, ast.YieldFrom,
                                 ast.NamedExpr, ast.BinOp, ast.Compare,
                                 ast.BoolOp, ast.IfExp, ast.Starred,
                                 ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
               for child in ast.walk(node))


## Resolve a name or module attribute chain through known import origins.
## 根据已知导入来源解析名称或模块属性链。
#
#  @param node Callable or alias expression.
#  @param origins Known imported names and their qualified origins.
#  @param module_origins Names proven to refer to imported modules.
#  @return Qualified target or None when not established.
def _target(node, origins, module_origins):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name) or node.id not in origins:
        return None
    if parts and node.id not in module_origins:
        return None
    head = origins[node.id]
    return '.'.join([head] + list(reversed(parts)))


## Recognize an imported-module call whose arguments have bounded syntax.
## 识别实参语法受限的导入模块调用。
#
#  @param node Candidate expression.
#  @param origins Known imported names and their qualified origins.
#  @param module_origins Names proven to refer to imported modules.
#  @return True if the call may be retained as an unknown result.
def _module_call_assignment(node, origins, module_origins):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    head = node.func
    while isinstance(head, ast.Attribute):
        head = head.value
    if (not isinstance(head, ast.Name) or head.id not in module_origins
            or _target(node.func, origins, module_origins) is None
            or any(_has_effectful_syntax(value) for value in node.args)
            or any(keyword.arg is None or _has_effectful_syntax(keyword.value)
                   for keyword in node.keywords)):
        return False
    return True


## Find a module-level call and its enclosing context-manager statements
## 查找模块级调用及其外层上下文管理语句。
#
#  @param document Parsed caller source document.
#  @param call Exact call node selected by its source span.
#  @return Top-level owner, enclosing managers, and direct expression owner.
def _call_scope(document, call):
    parents = {}
    for parent in ast.walk(document):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    direct = next((statement for statement in document.body
                   if getattr(statement, 'value', None) is call), None)
    if direct is not None:
        return direct, (), direct

    current, managers, expression = call, [], None
    while True:
        parent = parents.get(id(current))
        if isinstance(parent, ast.Expr) and parent.value is current:
            expression = parent
            current = parent
            continue
        if isinstance(parent, (ast.With, ast.AsyncWith)) and current in parent.body:
            managers.append(parent)
            current = parent
            continue
        if isinstance(parent, ast.Module) and current in parent.body:
            return current, tuple(reversed(managers)), expression
        return None, None, None


## Read finite literals and bounded return protocols at a module-level call site.
## 在模块级调用点读取有限字面量和有界返回协议。
#
#  @param callsite Full SourceSpan, never a line-only or terminal-name selection.
#  @param store Optional source cache that rereads content for each query.
#  @param max_nodes Finite source-walk bound.
#  @param max_items Finite literal construction bound across the query.
#  @param import_roots Roots used to locate supporting protocol stubs.
#  @return Source literal records or explicit boundaries; no execution/reachability assertion.
def literal_inputs(callsite, store=None, max_nodes=50000, max_items=2000, import_roots=()):
    if (type(max_nodes) is not int or type(max_items) is not int
            or max_nodes <= 0 or max_items <= 0):
        raise ValueError('Caller input budgets must be positive integers')
    result = {'kind': 'source_callsite_inputs', 'status': 'unconfirmed',
        'scope': 'argument_reads_on_normal_module_prefix', 'runtime_values_observed': False,
        'arguments': [], 'boundaries': [], 'source_hashes': {},
        'supporting_source_sha256': {},
        'assumptions': ['source_snapshot_bindings_hold', 'standard_module_global_lookup',
                        'no_external_module_global_mutation']}

    ## Add an explicit boundary and return the incomplete result.
    ## 添加显式边界并返回不完整结果。
    #
    #  @param reason Boundary reason code.
    #  @return Current result with the boundary appended.
    def fail(reason):
        result['boundaries'].append({'reason': reason})
        return result

    fields = ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')
    if (not isinstance(callsite, SourceSpan)
            or not isinstance(callsite.file_path, str) or not callsite.file_path
            or not all(type(getattr(callsite, key)) is int for key in fields)):
        return fail('caller_callsite_span_unconfirmed')
    path = callsite.file_path
    document = (store or SourceStore()).snapshot([path], FLOW_SOURCE).documents[path]
    if document.error is not None:
        return fail('caller_source_unavailable')
    result['source_hashes'][path] = document.sha256
    nodes = []
    for node in ast.walk(document.tree):
        nodes.append(node)
        if len(nodes) > max_nodes:
            return fail('caller_input_budget')
    matches = [n for n in nodes if isinstance(n, ast.Call)
               and all(getattr(n, key) == getattr(callsite, key) for key in fields)]
    if len(matches) != 1:
        return fail('caller_callsite_unconfirmed')
    call = matches[0]
    owner, with_path, expression_owner = _call_scope(document.tree, call)
    if (not isinstance(owner, (ast.Assign, ast.AnnAssign, ast.Expr, ast.With, ast.AsyncWith))
            or with_path is None):
        return fail('caller_callsite_not_module_expression')
    if any(_has_effectful_syntax(argument) for argument in call.args):
        return fail('caller_argument_evaluation_unconfirmed')
    if any(_has_effectful_syntax(keyword.value) for keyword in call.keywords):
        return fail('caller_argument_evaluation_unconfirmed')
    environment, origins, origin_evidence = {}, {}, {}
    module_origins, module_bindings, remaining = set(), set(), [max_items]
    protocols, protocol_evidence = {}, {}

    ## Convert a source node into its complete location dictionary.
    ## 将源码节点转换为完整位置字典。
    #
    #  @param node AST node with source positions.
    #  @return Source span dictionary.
    def span(node):
        return asdict(SourceSpan.from_ast(path, node))

    for statement in document.tree.body:
        if statement is owner:
            break
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            # Imports bind only their declared local names. Keep independent
            # earlier bindings under the existing no-external-module-global-
            # mutation assumption, while a new import may replace its own name.
            for fact in import_facts(statement):
                if fact.wildcard or fact.level:
                    continue
                if fact.python_binding.startswith('__') and fact.python_binding.endswith('__'):
                    return fail('caller_namespace_customization_unconfirmed')
                origins[fact.python_binding] = (
                    fact.name if fact.kind == 'import' and fact.asname
                    else fact.python_binding if fact.kind == 'import'
                    else fact.module + '.' + fact.name)
                origin_evidence[fact.python_binding] = [span(statement)]
                module_bindings.add(fact.python_binding)
                if fact.kind == 'import':
                    module_origins.add(fact.python_binding)
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if (not all(isinstance(target, ast.Name) for target in targets)
                    or any(target.id.startswith('__') and target.id.endswith('__')
                           for target in targets)
                    or statement.value is None
                    or isinstance(statement, ast.AnnAssign)
                    and not isinstance(statement.annotation, (ast.Name, ast.Constant))):
                return fail('caller_prefix_effect_unconfirmed')
            if _has_effectful_syntax(statement.value):
                if not _module_call_assignment(statement.value, origins, module_origins):
                    return fail('caller_prefix_effect_unconfirmed')
                target = _target(statement.value.func, origins, module_origins)
                result['boundaries'].append({
                    'reason': 'caller_prefix_call_effect_unconfirmed',
                    'evidence': span(statement), 'target': target,
                })
                protocol = iterable_return_fact(target, import_roots) if target else None
                # Call results are never executed. A result receives a narrow
                # protocol fact only when every overload in a bounded installed
                # stub returns a declared iterable type.
                # 不执行调用；仅当有界存根的所有重载声明可迭代返回类型时记录协议。
                for target in targets:
                    module_bindings.add(target.id)
                    environment.pop(target.id, None)
                    origins.pop(target.id, None)
                    origin_evidence.pop(target.id, None)
                    module_origins.discard(target.id)
                    protocols.pop(target.id, None)
                    protocol_evidence.pop(target.id, None)
                    if protocol is not None:
                        protocols[target.id] = protocol
                        protocol_evidence[target.id] = [span(statement)]
                        result['supporting_source_sha256'].update(protocol['source_hashes'])
                continue
            evidence = [span(statement)]
            value = _literal(statement.value, environment, remaining, evidence)
            origin = (_target(statement.value, origins, module_origins)
                      if isinstance(statement.value, ast.Name) else None)
            module_alias = (isinstance(statement.value, ast.Name)
                            and statement.value.id in module_origins)
            source_evidence = (list(origin_evidence.get(statement.value.id, []))
                               if isinstance(statement.value, ast.Name) else [])
            protocol = (protocols.get(statement.value.id)
                        if isinstance(statement.value, ast.Name) else None)
            protocol_sources = (list(protocol_evidence.get(statement.value.id, []))
                                if isinstance(statement.value, ast.Name) else [])
            if value is None and not isinstance(statement.value, (ast.Name, ast.Constant)):
                return fail('caller_prefix_value_unconfirmed')
            for target in targets:
                module_bindings.add(target.id)
                environment.pop(target.id, None)
                origins.pop(target.id, None)
                origin_evidence.pop(target.id, None)
                module_origins.discard(target.id)
                protocols.pop(target.id, None)
                protocol_evidence.pop(target.id, None)
                if value is not None:
                    environment[target.id] = value, list(evidence)
                if protocol is not None:
                    protocols[target.id] = protocol
                    protocol_evidence[target.id] = protocol_sources + [span(statement)]
                if origin is not None:
                    origins[target.id] = origin
                    origin_evidence[target.id] = source_evidence + [span(statement)]
                    if module_alias:
                        module_origins.add(target.id)
            continue
        if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)):
            continue
        return fail('caller_prefix_effect_unconfirmed')

    # Preserve manager bindings separately from ordinary module prefix values.
    # 将上下文管理器绑定与普通模块前缀值分开记录。
    context_managers, context_bindings = [], {}
    for depth, manager_node in enumerate(with_path):
        expected_body = (with_path[depth + 1] if depth + 1 < len(with_path)
                         else expression_owner)
        if len(manager_node.body) != 1 or manager_node.body[0] is not expected_body:
            return fail('caller_context_body_unconfirmed')
        for item_index, item in enumerate(manager_node.items):
            expression = item.context_expr
            manager = {
                'source_text': ast.unparse(expression),
                'call_syntax': ast.dump(expression, include_attributes=False),
                'evidence': span(expression),
                'target': (_target(expression.func, origins, module_origins)
                           if isinstance(expression, ast.Call) else None),
                'arguments': [],
                'keywords': [],
            }
            if (isinstance(expression, ast.Call)
                    and isinstance(expression.func, ast.Name)
                    and expression.func.id == 'open'
                    and expression.func.id not in module_bindings):
                manager['target'] = 'builtins.open'
            record = {
                'kind': ('async_context_manager' if isinstance(manager_node, ast.AsyncWith)
                         else 'context_manager'),
                'with_evidence': span(manager_node),
                'item_index': item_index,
                'manager': manager,
                'binding': None,
                'call_evidence': span(call),
                'runtime_value_observed': False,
            }
            if isinstance(expression, ast.Call):
                manager_arguments = [({'position': index}, value)
                                     for index, value in enumerate(expression.args)]
                manager_arguments.extend(({'keyword': keyword.arg}, keyword.value)
                                         for keyword in expression.keywords)
                for slot, value in manager_arguments:
                    evidence = [span(value)]
                    literal = _literal(value, environment, remaining, evidence)
                    argument = {
                        'argument': slot,
                        'evidence': evidence,
                        'status': 'source_literal' if literal is not None else 'unproven',
                    }
                    if literal is not None:
                        argument['value'] = literal
                    if 'position' in slot:
                        manager['arguments'].append(argument)
                    else:
                        manager['keywords'].append(argument)
            if isinstance(item.optional_vars, ast.Name):
                binding = {'name': item.optional_vars.id,
                           'evidence': span(item.optional_vars)}
                record['binding'] = binding
                context_bindings[item.optional_vars.id] = {
                    'manager_index': len(context_managers),
                    'binding_evidence': binding['evidence'],
                }
            context_managers.append(record)

    qualified = _target(call.func, origins, module_origins)
    target_status = 'source_bound'
    if qualified is None:
        # An exact method-expression receiver may be an object returned by an
        # opaque factory. Preserve argument facts without claiming its runtime
        # target; the consumer must match this exact function expression to an
        # independently supplied API identity.
        # 保留精确接收者表达式和实参事实；目标身份须由使用方独立证明。
        if not (isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)):
            return fail('caller_target_binding_unconfirmed')
        qualified = None
        target_status = 'receiver_expression_only'
    head = call.func
    while isinstance(head, ast.Attribute):
        head = head.value
    binding_evidence = ([span(call.func)] if target_status == 'receiver_expression_only'
                        else origin_evidence[head.id])
    result.update(target=qualified, target_status=target_status,
                  target_expression=(ast.dump(call.func, include_attributes=False)
                                     if target_status == 'receiver_expression_only' else None),
                  call_evidence=span(call),
                  call_syntax=ast.dump(call, include_attributes=False),
                  target_binding_evidence=binding_evidence)
    arguments = [({'position': index}, argument) for index, argument in enumerate(call.args)]
    arguments.extend(({'keyword': keyword.arg}, keyword.value) for keyword in call.keywords)
    if any(isinstance(argument, ast.Starred) for argument in call.args) or any(
            keyword.arg is None for keyword in call.keywords):
        return fail('caller_argument_expansion_unconfirmed')
    for slot, argument in arguments:
        evidence = [span(argument)]
        value = _literal(argument, environment, remaining, evidence)
        if value is None and any(not isinstance(child, (
                ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Load))
                for child in ast.walk(argument)):
            result['arguments'] = []
            return fail('caller_argument_evaluation_unconfirmed')
        record = {'argument': slot, 'evidence': evidence,
                  'status': 'source_literal' if value is not None else 'unproven'}
        if value is not None:
            record['value'] = value
        elif isinstance(argument, ast.Name) and argument.id in protocols:
            protocol = protocols[argument.id]
            record.update(status='source_protocol', protocol={
                'kind': 'iterable', 'basis': protocol['basis'],
                'call_target': protocol['target'],
                'supporting_source_sha256': protocol['source_hashes'],
            }, evidence=evidence + protocol_evidence[argument.id])
        result['arguments'].append(record)
    if context_managers:
        result['context_managers'] = context_managers
        result['context_argument_bindings'] = [
            {'argument': slot, 'name': argument.id,
             'manager_index': context_bindings[argument.id]['manager_index'],
             'binding_evidence': context_bindings[argument.id]['binding_evidence'],
             'argument_evidence': span(argument)}
            for slot, argument in arguments
            if isinstance(argument, ast.Name) and argument.id in context_bindings
        ]
    if remaining[0] < 0:
        result['arguments'] = []
        return fail('caller_input_budget')
    result['status'] = 'source_bound'
    return result
