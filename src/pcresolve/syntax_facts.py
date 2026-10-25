## @package pcresolve.syntax_facts
#  Source-only AST structure, independent of namespace and value-flow judgments.

import ast
from collections import deque
from dataclasses import dataclass
from types import MappingProxyType

from .import_facts import import_facts


## A requested syntax walk exceeded its caller's node allowance.
class SyntaxLimit(Exception):
    pass


## Immutable structure in statement order, with breadth-first order per statement.
@dataclass(frozen=True)
class BodySyntax:
    nodes: tuple
    parents: object
    imports: tuple


## Capture source structure without evaluating names or selecting analysis policy.
#  @param body Ordered top-level statements from an immutable source document.
#  @param limit Maximum nodes, including repeated singleton context/operator nodes.
#  @return Read-only nodes, last-parent lookup and ordered import syntax facts.
def body_syntax(body, limit):
    nodes, parents, imports = [], {}, []
    for statement in body:
        pending = deque([statement])
        while pending:
            node = pending.popleft()
            if len(nodes) >= limit:
                raise SyntaxLimit()
            nodes.append(node)
            for child in ast.iter_child_nodes(node):
                parents[child] = node
                pending.append(child)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(import_facts(node))
    return BodySyntax(tuple(nodes), MappingProxyType(parents), tuple(imports))
