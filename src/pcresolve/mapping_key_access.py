## @package pcresolve.mapping_key_access
#  Bounded source footprints for nonescaping keyword-capture dictionaries.

import ast
from dataclasses import asdict


## Describe all accesses to a keyword capture when each is local to a fixed key.
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
        if (isinstance(item, ast.Name) and item.id in reflection
                or isinstance(item, ast.Attribute) and item.attr in reflection
                or isinstance(item, ast.alias) and item.name in reflection | {'*'}):
            return []
        if not isinstance(item, ast.Name) or item.id != name:
            continue
        # Captures, rebinding, aliases and non-key-local writes are excluded.
        current = parents.get(item)
        while current is not None and current is not node:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                    ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                                    ast.GeneratorExp)):
                return []
            current = parents.get(current)
        if not isinstance(item.ctx, ast.Load):
            return []
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
    return [{'kind': 'mapping_key_access', 'status': 'key_local', 'parameter': name,
             'function': asdict(ref), 'protocol': 'keyword_capture',
             'keys': sorted({item['key'] for item in accesses}), 'accesses': accesses,
             'source_hash': analyzer.hashes.get(ref.file_path), 'control_flow_proven': False,
             'assumptions': ['no_external_frame_introspection']}]
