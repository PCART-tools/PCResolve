## @package pcresolve._class_literal_loops
#  Bounded syntax specialization of fresh literal factory-table iteration.
#  对新建字面量工厂表迭代执行有界语法特化，不运行用户代码。

import ast
import copy

from .scope_facts import statement_scope_facts

_UNKNOWN = object()


## Decode a serialized factory value into an isolated Python literal.
## 将序列化工厂值还原为隔离的 Python 字面量。
#
#  @param record Serialized value record from the factory premise.
#  @return Decoded literal value or the unknown sentinel.
def _decode(record):
    ## Recursively decode nested dictionary and list records.
    ## 递归解码嵌套字典与列表记录。
    #
    #  @param value Serialized nested value.
    #  @return Decoded nested literal or the original scalar value.
    def nested(value):
        if isinstance(value, dict) and value.get('kind') == 'dict':
            return {key: nested(item) for key, item in value['items']}
        if isinstance(value, list):
            return [nested(item) for item in value]
        return value
    return nested(record) if record.get('kind') == 'dict' else nested(record.get('value', _UNKNOWN))


## Evaluate a restricted AST expression using known immutable literals.
## 使用已知不可变字面量计算受限 AST 表达式。
#
#  @param node Expression node to evaluate.
#  @param env Known local values at this program point.
#  @return Literal result or the unknown sentinel.
def _value(node, env):
    if isinstance(node, ast.Name):
        return env.get(node.id, _UNKNOWN)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _value(node.left, env), _value(node.right, env)
        return left + right if type(left) is type(right) is str and len(left) + len(right) <= 2000 else _UNKNOWN
    if node is None or any(isinstance(item, ast.Call) for item in ast.walk(node)):
        return _UNKNOWN
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, RecursionError):
        return _UNKNOWN


## Check that an expression cannot expose or mutate tracked mutable values.
## 检查表达式是否不会暴露或修改已跟踪的可变值。
#
#  @param node AST node whose subtree is inspected.
#  @param env Current literal environment.
#  @return True when no tracked mutable name is referenced.
def _safe(node, env):
    mutable = {name for name, value in env.items() if type(value) in (dict, list, tuple)}
    return not any(isinstance(item, ast.Name) and item.id in mutable for item in ast.walk(node))


## Update known values after a simple assignment statement.
## 在简单赋值语句之后更新已知值。
#
#  @param statement Assignment statement to apply.
#  @param env Mutable environment of known local values.
#  @return None; unsupported bindings are removed from the environment.
def _assigned(statement, env):
    value = _value(getattr(statement, 'value', None), env)
    for name in statement_scope_facts([statement]).bound:
        env.pop(name, None)
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            if isinstance(target, ast.Name):
                env[target.id] = value
    elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        env[statement.target.id] = value


## Expand one reached finite table loop without executing class/helper operations.
## 展开已到达的有限表循环，不执行类方法或辅助函数。
#
#  @param analyzer Fixed source snapshot and optional analysis budget.
#  @param target Source function pair after partial class-argument binding.
#  @param factory Source partial-factory premise with freshly constructed literal data.
#  @param max_nodes Maximum generated AST nodes; inspection is bounded to four times this.
#  @return Specialized AST and source premise, or None for uncertain data/iteration.
def specialize(analyzer, target, factory, max_nodes=2000):
    ref, function = target
    if any(isinstance(node, (ast.Global, ast.Nonlocal)) for node in ast.walk(function)):
        return None
    env = {item['parameter']: _decode(item['value']) for item in factory.get('arguments', [])}
    if (factory.get('kind') != 'source_partial_class_decorator'
            or factory.get('source_hashes') != analyzer.hashes or max_nodes < 1):
        return None
    remaining, iterations, witnesses = [4 * max_nodes], [0], []

    ## Account for inspected syntax and stop when either analysis budget is spent.
    ## 累计检查的语法节点，并在任一分析预算耗尽时停止。
    #
    #  @param node AST subtree whose nodes are charged.
    #  @return None; raises ValueError when the local node budget is exceeded.
    def charge(node):
        for _ in ast.walk(node):
            remaining[0] -= 1
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if remaining[0] < 0:
                raise ValueError()

    ## Preserve a real loop binding while substituting each known loop item.
    ## 为每个已知循环项保留真实循环变量绑定。
    #
    #  @param target_node Loop target pattern to bind.
    #  @param value Literal iteration value.
    #  @param local Mutable local literal environment.
    #  @param source Original loop node used for source locations.
    #  @return Assignment nodes that preserve closure-cell behavior.
    def bind(target_node, value, local, source):
        if isinstance(target_node, ast.Name):
            local[target_node.id] = value
        elif (isinstance(target_node, (ast.Tuple, ast.List)) and type(value) in (tuple, list)
                and len(target_node.elts) == len(value)):
            assignments = []
            for child, element in zip(target_node.elts, value):
                assignments.extend(bind(child, element, local, source))
            return assignments
        else:
            raise ValueError()
        # Bind real iteration variables instead of replacing uses with constants:
        # deferred function bodies must retain Python's closure-cell behavior.
        # 保留真实迭代变量绑定，确保延迟执行的函数体仍使用 Python 闭包单元。
        assignment = ast.Assign(targets=[copy.deepcopy(target_node)],
                                value=ast.parse(repr(value), mode='eval').body)
        ast.copy_location(assignment, source)
        for node in ast.walk(assignment):
            if isinstance(node, (ast.expr, ast.stmt)):
                ast.copy_location(node, source)
        charge(assignment)
        return [assignment]

    ## Materialize a supported literal iterable without invoking runtime code.
    ## 在不调用运行时代码的前提下展开受支持的字面量迭代对象。
    #
    #  @param loop For statement whose iterator is inspected.
    #  @param local Current literal environment.
    #  @return Finite iteration values, or None for unsupported iterators.
    def sequence(loop, local):
        node = loop.iter
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'items' and isinstance(node.func.value, ast.Name)
                and not node.args and not node.keywords):
            value = local.get(node.func.value.id, _UNKNOWN)
            return list(value.items()) if type(value) is dict else None
        value = _value(node, local)
        return list(value) if type(value) in (list, tuple) else None

    ## Specialize a bounded statement block while tracking literal bindings.
    ## 跟踪字面量绑定并特化有界语句块。
    #
    #  @param body Ordered statements to specialize.
    #  @param local Mutable literal environment for this path.
    #  @param depth Current nested-block depth.
    #  @return Specialized statements; unsupported control flow raises ValueError.
    def block(body, local, depth=0):
        if depth > 32:
            raise ValueError()
        output = []
        for statement in body:
            charge(statement)
            if isinstance(statement, (ast.Break, ast.Continue)):
                raise ValueError()
            if isinstance(statement, ast.For):
                # A loop must have a fully known, finite iterator before expansion.
                # 只有迭代值完全已知且有限时才展开循环。
                values = sequence(statement, local)
                if values is None or len(values) > 64:
                    raise ValueError()
                if any(isinstance(node, (ast.Break, ast.Continue))
                       for part in statement.body for node in ast.walk(part)):
                    raise ValueError()
                # The iterator and list-valued elements cannot be rebound,
                # mutated or exposed while their iteration is specialized.
                protected = {name for name, value in local.items()
                             if type(value) in (dict, list, tuple)}
                if any(isinstance(node, ast.Name) and node.id in protected
                       and isinstance(node.ctx, (ast.Store, ast.Del))
                       for part in statement.body for node in ast.walk(part)):
                    raise ValueError()
                witnesses.append({'file_path': ref.file_path, 'lineno': statement.lineno,
                    'col_offset': statement.col_offset, 'end_lineno': statement.end_lineno,
                    'end_col_offset': statement.end_col_offset})
                for value in values:
                    iterations[0] += 1
                    output.extend(bind(statement.target, value, local, statement))
                    output.extend(block(statement.body, local, depth + 1))
                output.extend(block(statement.orelse, local, depth + 1))
            elif isinstance(statement, ast.If):
                # Keep the branch syntax and merge only facts agreed on by both paths.
                # 保留分支语法，仅合并两条路径都一致的事实。
                if not _safe(statement.test, local):
                    raise ValueError()
                left, right = dict(local), dict(local)
                branch = copy.copy(statement)
                branch.body = block(statement.body, left, depth + 1)
                branch.orelse = block(statement.orelse, right, depth + 1)
                output.append(branch)
                local.clear()
                local.update({name: value for name, value in left.items()
                              if value is not _UNKNOWN and name in right
                              and right[name] is not _UNKNOWN and right[name] == value})
            else:
                # Retain ordinary statements unchanged only when they cannot hide loops.
                # 普通语句仅在不会隐藏循环时原样保留。
                if not _safe(statement, local) or any(isinstance(node, ast.For)
                        for node in ast.walk(statement)
                        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))):
                    raise ValueError()
                output.append(copy.deepcopy(statement))
                _assigned(statement, local)
        return output

    output = []
    try:
        for index, statement in enumerate(function.body):
            if isinstance(statement, ast.For):
                output.extend(block([statement], env))
                output.extend(copy.deepcopy(function.body[index + 1:]))
                break
            if not _safe(statement, env):
                return None
            charge(statement)
            output.append(copy.deepcopy(statement))
            _assigned(statement, env)
        else:
            return None
    except (ValueError, TypeError, SyntaxError, RecursionError):
        return None
    specialized = copy.copy(function)
    specialized.body = output
    generated = sum(1 for _ in ast.walk(specialized))
    if generated > max_nodes:
        return None
    return specialized, {'kind': 'source_literal_loop_expansion',
        'status': 'source_specialized', 'iterations': iterations[0],
        'generated_nodes': generated, 'inspected_nodes': 4 * max_nodes - remaining[0],
        'runtime_iterators_executed': False, 'effects': 'original_body_unproved',
        'evidence': witnesses, 'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold', 'fresh_factory_literal_inputs',
                        'builtin_literal_iteration', 'no_external_frame_introspection']}
