## @package pcresolve.mapping_return_transfer
#  Conditional source facts for fresh mappings returned after a capture update.
#  为捕获更新后返回的新建映射收集条件式源码事实。

import ast
from dataclasses import asdict


## Build a source span record for one transfer operation.
## 为一次传递操作构造源码范围记录。
#
#  @param ref Source function identity carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Read unique literal mapping fields from a dictionary expression.
## 从字典表达式中读取唯一的字面量映射字段。
#
#  @param node Candidate dictionary expression or constructor call.
#  @param builtin_dict Whether the dict constructor is confirmed builtin.
#  @return Field-name to value-node mapping, or None for dynamic/duplicate keys.
def _fields(node, builtin_dict):
    if isinstance(node, ast.Dict):
        if any(not isinstance(key, ast.Constant) or type(key.value) is not str
               for key in node.keys):
            return None
        names = [key.value for key in node.keys]
        return dict(zip(names, node.values)) if len(set(names)) == len(names) else None
    if (builtin_dict and isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'dict' and not node.args
            and all(keyword.arg is not None for keyword in node.keywords)):
        fields = {keyword.arg: keyword.value for keyword in node.keywords}
        return fields if len(fields) == len(node.keywords) else None
    return None


## Extract a name and constant-key path from nested subscripts.
## 从嵌套下标表达式提取名称和常量键路径。
#
#  @param node Expression to inspect.
#  @return Root name and ordered key path, or a pair of None values.
def _path(node):
    path = []
    while isinstance(node, ast.Subscript):
        if not isinstance(node.slice, ast.Constant) or type(node.slice.value) not in (str, int):
            return None, None
        path.insert(0, node.slice.value)
        node = node.value
    return (node.id, path) if isinstance(node, ast.Name) else (None, None)


## Describe capture updates retained in a fresh returned mapping on normal completion.
## 描述正常完成时保留在新建返回映射中的捕获更新。
#
#  @param analyzer Fixed source analyzer, including lexical builtin binding facts.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Bounded conditional transfers; normal completion is never inferred.
def transfers(analyzer, ref, node):
    if not node.args.kwarg or isinstance(node, ast.AsyncFunctionDef):
        return []

    # Reject generators, awaits, oversized bodies, and anything but one final direct return.
    # 拒绝生成器、await、超大函数体，以及除唯一末尾直接返回之外的结构。
    nodes = list(ast.walk(node))
    if len(nodes) > 4000 or any(isinstance(item, (ast.Yield, ast.YieldFrom, ast.Await))
                               for item in nodes):
        return []
    returns = [item for item in nodes if isinstance(item, ast.Return)]
    if (len(returns) != 1 or node.body[-1] is not returns[0]
            or not isinstance(returns[0].value, ast.Name)):
        return []
    returned = returns[0]
    root = returned.value.id
    parameter = node.args.kwarg.arg
    reflection = {'eval', 'exec', 'locals', 'globals', 'vars', 'dir', 'getattr',
                  'currentframe', '_getframe', 'stack', 'getouterframes',
                  '__builtins__', '__globals__', '__code__', '*'}
    if any(isinstance(item, ast.Name) and item.id in reflection
           or isinstance(item, ast.Attribute) and item.attr in reflection
           or isinstance(item, ast.alias) and item.name in reflection for item in nodes):
        return []
    uses = [item for item in nodes if isinstance(item, ast.Name) and item.id == parameter]
    if len(uses) != 1 or not isinstance(uses[0].ctx, ast.Load):
        return []
    parents = {child: parent for parent in nodes for child in ast.iter_child_nodes(parent)}
    call = parents.get(uses[0])
    if (not isinstance(call, ast.Call) or call.args != uses or call.keywords
            or not isinstance(call.func, ast.Attribute) or call.func.attr != 'update'
            or not isinstance(parents.get(call), ast.Expr) or parents[call] not in node.body):
        return []

    # Require the sole capture update to target the same returned root and a short string path.
    # 要求唯一捕获更新目标与返回根相同，且路径为较短的字符串键序列。
    receiver = call.func.value
    base, path = _path(receiver)
    if base != root or len(path) > 4 or any(type(key) is not str for key in path):
        return []
    bindings = {}
    for statement in node.body:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            bindings.setdefault(statement.targets[0].id, []).append(statement)
    if len(bindings.get(root, [])) != 1:
        return []
    created = bindings[root][0]
    if created.lineno >= call.lineno:
        return []
    builtin_dict = analyzer._builtin_name_status(ref, node, 'dict') == 'confirmed_builtin'
    aliases = {}

    ## Resolve one fresh literal mapping expression before a source position.
    ## 在指定源码位置之前解析一个新建的字面量映射表达式。
    #
    #  @param expression Candidate mapping expression or local name.
    #  @param before Line number that the binding must precede.
    #  @return Unique literal field mapping, or None for stale/ambiguous bindings.
    def fresh(expression, before):
        if isinstance(expression, ast.Name):
            candidates = bindings.get(expression.id, [])
            if len(candidates) != 1 or candidates[0].lineno >= before:
                return None
            binding = candidates[0]
            if expression.id in aliases:
                return None
            aliases[expression.id] = (binding.targets[0], expression)
            expression = binding.value
        return _fields(expression, builtin_dict)

    # Follow only literal fields along the receiver path; unknown values stop the proof.
    # 仅沿接收者路径追踪字面量字段；遇到未知值即停止证明。
    fields = fresh(created.value, created.lineno)
    for key in path:
        if fields is None or key not in fields:
            return []
        expression = fields[key]
        fields = fresh(expression, created.lineno)
    if fields is None:
        return []
    protected = {root} | set(aliases)

    # Reject reflective, rebinding, or additional alias uses that could change mapping identity.
    # 拒绝可能改变映射身份的反射、重绑定或额外别名用法。
    for item in nodes:
        if (isinstance(item, ast.alias) and (item.asname or item.name.split('.')[0]) in protected
                or isinstance(item, ast.ExceptHandler) and item.name in protected
                or isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and item is not node and item.name in protected
                or isinstance(item, (ast.Global, ast.Nonlocal))
                and protected.intersection(item.names)):
            return []
    for name, allowed in aliases.items():
        actual = [item for item in nodes if isinstance(item, ast.Name) and item.id == name]
        if len(actual) != 2 or set(actual) != set(allowed):
            return []
    excluded = set()

    # Collect sibling keys already read after the update so transfer remains conditional.
    # 收集更新后已读取的同级键，使传递结果继续保持条件性。
    for item in nodes:
        if not isinstance(item, ast.Name) or item.id != root:
            continue
        if item is created.targets[0] or item is returned.value:
            continue
        if not isinstance(item.ctx, ast.Load) or item.lineno < call.lineno:
            return []
        outer = item
        while isinstance(parents.get(outer), ast.Subscript) and parents[outer].value is outer:
            outer = parents[outer]
        if outer is receiver:
            continue
        _, access = _path(outer)
        if access is None or not access:
            return []
        if access[:len(path)] == path:
            if len(access) <= len(path) or type(access[len(path)]) is not str:
                return []
            excluded.add(access[len(path)])
        elif path[:len(access)] == access:
            return []
    return [{'kind': 'normal_return_mapping_transfer', 'status': 'conditional',
             'function': asdict(ref), 'parameter': parameter, 'return_root': root,
             'return_path': path, 'excluded_keys': sorted(excluded),
             'update_evidence': _span(ref, call), 'return_evidence': _span(ref, returned),
             'source_hash': analyzer.hashes.get(ref.file_path),
             'normal_completion_proven': False,
             'assumptions': ['standard_builtin_dict', 'no_external_frame_introspection']}]
