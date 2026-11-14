## @package pcresolve.flow.proofs.protocols.capture_rejection_guard
#  Conditional source obligations for rejecting a nonempty captured dictionary.
#  拒绝非空捕获字典的条件性源码证据要求。

import ast
from dataclasses import asdict


## Record source coordinates for one guard or raise node.
## 记录守卫或抛出节点的源码坐标。
#
#  @param ref Source function identity.
#  @param node AST node with source positions.
#  @return Source location dictionary.
def _span(ref, node):
    return dict(file_path=ref.file_path, lineno=node.lineno, col_offset=node.col_offset,
                end_lineno=node.end_lineno, end_col_offset=node.end_col_offset)


## Describe direct rejection guards without asserting runtime reachability or type.
## 描述直接拒绝守卫，不断言运行时可达性或类型。
#
#  @param analyzer Fixed source analyzer, providing lexical builtin facts and hashes.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Bounded obligations requiring an original-call uncaught exception trace.
def checks(analyzer, ref, node):
    if not isinstance(node, ast.FunctionDef):
        return []
    parameters = {a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
    parameters.update(a.arg for a in (node.args.vararg, node.args.kwarg) if a)
    pending = [node]
    facts = []
    count = 0
    while pending:
        branch = pending.pop()
        count += 1
        if count > 4000:
            return []
        if branch is not node and isinstance(branch, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue

        # Inspect this function only; nested definitions execute in other scopes.
        # 仅检查当前函数；嵌套定义在其他作用域中执行。
        pending.extend(ast.iter_child_nodes(branch))
        if not isinstance(branch, ast.If) or len(branch.body) != 1:
            continue
        presence = branch.test
        while isinstance(presence, ast.BoolOp) and isinstance(presence.op, ast.And):
            presence = presence.values[-1]
        if not isinstance(presence, ast.Name) or presence.id not in parameters:
            continue
        raised = branch.body[0]
        if (not isinstance(raised, ast.Raise) or raised.cause is not None
                or not isinstance(raised.exc, ast.Call) or raised.exc.keywords
                or not isinstance(raised.exc.func, ast.Name)
                or raised.exc.func.id not in {'ValueError', 'TypeError'}
                or len(raised.exc.args) > 1 or any(
                    not isinstance(a, ast.Constant) or type(a.value) is not str
                    for a in raised.exc.args)
                or analyzer._builtin_name_status(ref, node, raised.exc.func.id)
                != 'confirmed_builtin'):
            continue

        # Source syntax alone does not establish an uncaught runtime exception.
        # 仅凭源码语法不能证明运行时出现未捕获异常。
        facts.append({'kind': 'capture_truth_rejection', 'status': 'requires_observation',
                      'function': asdict(ref), 'parameter': presence.id,
                      'exception': raised.exc.func.id, 'guard_evidence': _span(ref, branch.test),
                      'presence_evidence': _span(ref, presence),
                      'raise_evidence': _span(ref, raised),
                      'source_hash': analyzer.hashes.get(ref.file_path),
                      'guard_completed': False, 'runtime_rejection_confirmed': False})
    return facts
