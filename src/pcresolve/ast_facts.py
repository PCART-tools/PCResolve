## @package pcresolve.ast_facts
#  Read-only syntax indexes scoped to a source generation.
#  局限于单次源码生成版本的只读语法索引。

import ast
from dataclasses import dataclass


## Ordered nodes and lookup buckets for one immutable AST root.
## 单个不可变 AST 根节点的有序节点和查找分组。
@dataclass(frozen=True)
class AstFacts:
    nodes: tuple
    calls: dict
    assignments: tuple
    classes: tuple
    parents: dict


## Lazy syntax facts retained only by one analysis generation.
## 仅由单次分析生成版本持有的惰性语法事实。
class AstFactIndex:
    ## Initialize an empty per-run cache and optional cooperative budget.
    ## 初始化本次运行的空缓存和可选协作式预算。
    #
    #  @return None
    def __init__(self):
        self._facts = {}
        self.budget = None

    ## Index a tree once in the existing breadth-first order.
    ## 按既有广度优先顺序为语法树建立一次索引。
    #
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
            # Publish the index only after traversal and budget checks complete.
            # 仅在遍历和预算检查完成后发布索引。
            self._facts[tree] = AstFacts(nodes, calls, tuple(assignments),
                                         tuple(classes), parents)
        return self._facts[tree]


## Collect constructor fields without repeated ancestor walks.
## 收集构造函数专有字段，避免重复向上遍历祖先节点。
#
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
                # Any other write or deletion disqualifies this field globally.
                # 其他位置的写入或删除会使该字段在全局结果中失去资格。
                if (not isinstance(node.ctx, ast.Store)
                        or not isinstance(node.value, ast.Name) or node.value.id != 'self'
                        or function is None or function.name != '__init__' or not class_method):
                    blocked.add(node.attr)
            stack.extend((child, node, function, class_method)
                         for child in ast.iter_child_nodes(node))
    return fields - blocked
