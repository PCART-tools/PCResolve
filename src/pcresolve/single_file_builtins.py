## @package pcresolve.single_file_builtins
#  Builtin-call predicates shared by single-file ownership adapters.

import ast

from .builtin_ownership import _is_builtin


## Check whether a builtin name is not shadowed by a local definition.
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
    binding = tracer.current_scope().lookup(
        name, skip_parent_classes=True)
    if binding is not None:
        return False
    return True
