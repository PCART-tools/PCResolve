## @package pcresolve.ast_facts
#  Read-only syntax indexes scoped to a source generation.

import ast
from dataclasses import dataclass


## Ordered nodes and lookup buckets for one immutable AST root.
@dataclass(frozen=True)
class AstFacts:
    nodes: tuple
    calls: dict
    assignments: tuple
    classes: tuple
    parents: dict


## Lazy syntax facts retained only by one analysis generation.
class AstFactIndex:
    ## Initialize an empty per-run cache and optional cooperative budget.
    def __init__(self):
        self._facts = {}
        self.budget = None

    ## Index a tree once in the existing breadth-first order.
    #  @param tree Read-only AST node.
    #  @return Facts for that exact node identity.
    def get(self, tree):
        if tree not in self._facts:
            nodes = tuple(ast.walk(tree))
            calls, assignments, classes, parents = {}, [], [], {}
            for node in nodes:
                if self.budget is not None:
                    self.budget.checkpoint()
                if isinstance(node, ast.Call):
                    calls.setdefault((node.lineno, node.col_offset), []).append(node)
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    assignments.append(node)
                if isinstance(node, ast.ClassDef):
                    classes.append(node)
                for child in ast.iter_child_nodes(node):
                    parents[id(child)] = node
            self._facts[tree] = AstFacts(nodes, calls, tuple(assignments),
                                         tuple(classes), parents)
        return self._facts[tree]


## Collect constructor fields without repeated ancestor walks.
#  @param tracers Module analyzers with immutable source trees.
#  @param budget Optional cooperative resource checks during syntax traversal.
#  @return Fields written only through self in direct class initializers.
def constructor_only_fields(tracers, budget=None):
    fields, blocked = set(), set()
    for tracer in tracers.values():
        if tracer._module_tree is None:
            continue
        stack = [(tracer._module_tree, None, None, False)]
        while stack:
            if budget is not None:
                budget.checkpoint()
            node, parent, function, class_method = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function, class_method = node, isinstance(parent, ast.ClassDef)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                fields.add(node.attr)
                if (not isinstance(node.ctx, ast.Store)
                        or not isinstance(node.value, ast.Name) or node.value.id != 'self'
                        or function is None or function.name != '__init__' or not class_method):
                    blocked.add(node.attr)
            stack.extend((child, node, function, class_method)
                         for child in ast.iter_child_nodes(node))
    return fields - blocked
