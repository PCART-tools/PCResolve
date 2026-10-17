## @package pcresolve.mapping_attribute_transfer
#  Source obligations for retaining a keyword capture in constructor state.

import ast
from dataclasses import asdict


## Describe a direct constructor capture store, without asserting its execution.
#  @param analyzer Fixed source analyzer providing the source snapshot hash.
#  @param ref Source function identity.
#  @param node Source function AST.
#  @return Bounded obligations requiring independent store and retention evidence.
def transfers(analyzer, ref, node):
    positional = node.args.posonlyargs + node.args.args
    if (not node.args.kwarg or not positional or node.name != '__init__'
            or isinstance(node, ast.AsyncFunctionDef)):
        return []
    nodes = list(ast.walk(node))
    if len(nodes) > 4000 or any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Await)) for n in nodes):
        return []
    name = node.args.kwarg.arg
    uses = [n for n in nodes if isinstance(n, ast.Name) and n.id == name]
    if len(uses) != 1 or not isinstance(uses[0].ctx, ast.Load):
        return []
    stores = [statement for statement in node.body
              if isinstance(statement, ast.Assign) and statement.value is uses[0]
              and len(statement.targets) == 1]
    if len(stores) != 1:
        return []
    store = stores[0]
    target = store.targets[0]
    receiver = positional[0].arg
    if (not isinstance(target, ast.Attribute) or not isinstance(target.value, ast.Name)
            or target.value.id != receiver):
        return []
    return [{'kind': 'mapping_attribute_transfer', 'status': 'requires_observation',
             'function': asdict(ref), 'parameter': name, 'receiver': receiver,
             'attribute': target.attr,
             'store_evidence': {'file_path': ref.file_path, 'lineno': store.lineno,
                                'col_offset': store.col_offset, 'end_lineno': store.end_lineno,
                                'end_col_offset': store.end_col_offset},
             'source_hash': analyzer.hashes.get(ref.file_path),
             'store_completed': False, 'returned_instance_retention_proven': False}]
