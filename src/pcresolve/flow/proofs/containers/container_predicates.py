## @package pcresolve.flow.proofs.containers.container_predicates
#  Source obligations for observed builtin-container predicate evaluation.
#  对内置容器谓词求值进行观察所需的源码证据条件。

import ast
from dataclasses import asdict


## Iterate the root syntax without entering nested named or lambda scopes.
## 遍历根节点语法，不进入嵌套具名作用域或 lambda。
#
#  @param root AST root to traverse.
#  @return Iterator of nodes in depth-first order.
def _nodes(root):
    pending = [root]
    while pending:
        node = pending.pop()
        if node is not root and isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


## Capture a node's source coordinates for an indexed function.
## 获取索引函数中节点的源码坐标。
#
#  @param ref Source function identity.
#  @param node AST node with source positions.
#  @return Source location dictionary.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Describe predicates that require independent execution and container-type evidence.
## 描述需要独立执行证据和容器类型证据的谓词。
#
#  @param analyzer Fixed source analyzer providing hashes and lexical builtin facts.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Bounded source obligations; no runtime consumption or type assertion.
def checks(analyzer, ref, node):
    parameters = {argument.arg for argument in node.args.posonlyargs + node.args.args
                  + node.args.kwonlyargs}
    parameters.update(argument.arg for argument in (node.args.vararg, node.args.kwarg) if argument)
    result = []
    for count, branch in enumerate(_nodes(node)):
        if count >= 4000:
            return []
        if not isinstance(branch, ast.If):
            continue
        predicate = branch.test
        # Only the first Boolean operand is necessarily evaluated on entry.
        # 进入布尔表达式时，只有第一个操作数一定会被求值。
        while isinstance(predicate, ast.BoolOp):
            predicate = predicate.values[0]
        selected = predicate
        negated = False
        while isinstance(predicate, ast.UnaryOp) and isinstance(predicate.op, ast.Not):
            negated = not negated
            predicate = predicate.operand
        detail = {}
        if isinstance(predicate, ast.Name) and predicate.id in parameters:
            operation, parameter = 'truth', predicate.id
        elif (isinstance(predicate, ast.Compare) and len(predicate.ops) == 1
              and isinstance(predicate.ops[0], (ast.In, ast.NotIn))
              and isinstance(predicate.comparators[0], ast.Name)
              and predicate.comparators[0].id in parameters):
            key = predicate.left
            if isinstance(key, ast.Name):
                detail['key'] = {'kind': 'name', 'name': key.id}
            elif isinstance(key, ast.Constant) and type(key.value) is str:
                detail['key'] = {'kind': 'literal', 'value': key.value}
            else:
                continue
            operation, parameter = 'contains', predicate.comparators[0].id
            detail['operator'] = 'in' if isinstance(predicate.ops[0], ast.In) else 'not_in'
        elif (isinstance(predicate, ast.Compare) and len(predicate.ops) == 1
              and isinstance(predicate.ops[0], (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE))
              and isinstance(predicate.left, ast.Call)
              and isinstance(predicate.left.func, ast.Name) and predicate.left.func.id == 'len'
              and len(predicate.left.args) == 1 and not predicate.left.keywords
              and isinstance(predicate.left.args[0], ast.Name)
              and predicate.left.args[0].id in parameters
              and isinstance(predicate.comparators[0], ast.Constant)
              and type(predicate.comparators[0].value) is int
              and analyzer._builtin_name_status(ref, node, 'len') == 'confirmed_builtin'):
            operation, parameter = 'length', predicate.left.args[0].id
            detail.update(operator=type(predicate.ops[0]).__name__,
                          constant=predicate.comparators[0].value)
        else:
            continue

        # A syntactic match does not prove execution or the runtime receiver type.
        # 语法匹配不能证明实际执行或运行时接收者类型。
        result.append({'kind': 'container_predicate', 'status': 'requires_observation',
                       'function': asdict(ref), 'parameter': parameter, 'operation': operation,
                       'negated': negated, 'detail': detail,
                       'predicate_evidence': _span(ref, selected),
                       'guard_evidence': _span(ref, branch.test),
                       'source_hash': analyzer.hashes.get(ref.file_path),
                       'predicate_completed': False, 'container_type_proven': False})
    return result
