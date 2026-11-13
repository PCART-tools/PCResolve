## @package pcresolve.mapping_key_access
#  Bounded source footprints for nonescaping keyword-capture dictionaries.
#  未逃逸关键字捕获字典的有界源码访问记录。

import ast
from dataclasses import asdict


## Describe all accesses to a keyword capture when each is local to a fixed key.
## 当关键字捕获的所有访问均局限于固定键时描述这些访问。
#
#  @param analyzer Fixed source analyzer providing the source snapshot hash.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Neutral access footprints, never execution or compatibility verdicts.
def footprints(analyzer, ref, node):
    if node.args.kwarg is None:
        return []
    name = node.args.kwarg.arg
    nodes = list(ast.walk(node))
    if len(nodes) > 4000:
        return []
    parents = {child: parent for parent in nodes for child in ast.iter_child_nodes(parent)}
    accesses = []
    reflection = {'eval', 'exec', 'locals', 'globals', 'vars', 'dir', 'getattr',
                  'currentframe', '_getframe', 'stack', 'getouterframes',
                  '__builtins__', '__globals__', '__code__'}
    for item in nodes:
        # Reject referenced reflection capabilities as well as direct calls.
        # Alias invocation must not bypass a namespace escape boundary.
        # 同时拒绝反射能力的引用，防止别名调用绕过命名空间逃逸边界。
        if (isinstance(item, ast.Name) and item.id in reflection
                or isinstance(item, ast.Attribute) and item.attr in reflection
                or isinstance(item, ast.alias) and item.name in reflection | {'*'}):
            return []
        if not isinstance(item, ast.Name) or item.id != name:
            continue
        # Captures, rebinding, aliases and non-key-local writes are excluded.
        # 排除捕获、重新绑定、别名及非固定键的写入。
        current = parents.get(item)
        while current is not None and current is not node:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                    ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                                    ast.GeneratorExp)):
                return []
            current = parents.get(current)
        if not isinstance(item.ctx, ast.Load):
            return []

        # Every use must match a supported operation with a literal string key.
        # 每次使用都必须匹配受支持操作及字符串字面量键。
        parent = parents.get(item)
        operation, key = None, None
        if isinstance(parent, ast.Subscript) and parent.value is item:
            if isinstance(parent.ctx, ast.Load):
                operation, key = 'getitem', parent.slice
        elif (isinstance(parent, ast.Compare) and len(parent.ops) == 1
              and len(parent.comparators) == 1 and parent.comparators[0] is item
              and isinstance(parent.ops[0], (ast.In, ast.NotIn))):
            operation, key = 'contains', parent.left
        elif (isinstance(parent, ast.Attribute) and parent.value is item
              and parent.attr in {'get', 'pop'}):
            call = parents.get(parent)
            if (isinstance(call, ast.Call) and call.func is parent and not call.keywords
                    and len(call.args) in (1, 2)
                    and not any(isinstance(arg, ast.Starred) for arg in call.args)):
                operation, key = parent.attr, call.args[0]
        if operation is None or not isinstance(key, ast.Constant) or type(key.value) is not str:
            return []
        accesses.append({'operation': operation, 'key': key.value,
                         'evidence': {'file_path': ref.file_path, 'lineno': parent.lineno,
                                      'col_offset': parent.col_offset,
                                      'end_lineno': parent.end_lineno,
                                      'end_col_offset': parent.end_col_offset}})
    if not accesses:
        return []

    # This is source evidence only; control flow and execution remain unproven.
    # 这里只提供源码证据，控制流和实际执行仍未获证明。
    return [{'kind': 'mapping_key_access', 'status': 'key_local', 'parameter': name,
             'function': asdict(ref), 'protocol': 'keyword_capture',
             'keys': sorted({item['key'] for item in accesses}), 'accesses': accesses,
             'source_hash': analyzer.hashes.get(ref.file_path), 'control_flow_proven': False,
             'assumptions': ['no_external_frame_introspection']}]
