## @package pcresolve.single_file_builtins
#  Builtin-call predicates shared by single-file ownership adapters.
#  单文件归属适配器共享的内置调用判断。

import ast

from .builtin_ownership import _is_builtin


## Check whether a builtin name is not shadowed by a local definition.
## 判断内置名称是否未被本地定义遮蔽。
#
#  @param tracer SingleFileAnalyzer-compatible visitor state.
#  @param node The ast.Call node.
#  @return True if the call is to an unshadowed builtin.
def _is_unshadowed_builtin_call(tracer, node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False
    name = node.func.id
    if not _is_builtin(name):
        return False
    if name in tracer.defined_functions:
        return False
    if name in tracer.import_from_symbols:
        return False
    if name in tracer.local:
        return False

    # Lexical bindings can shadow the builtin even without a module-level entry.
    # 即使模块级记录中没有该名称，词法绑定也可能遮蔽内置名称。
    binding = tracer.current_scope().lookup(
        name, skip_parent_classes=True)
    if binding is not None:
        return False
    return True
