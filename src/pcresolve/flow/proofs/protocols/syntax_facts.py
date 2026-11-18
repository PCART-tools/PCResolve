## @package pcresolve.flow.proofs.protocols.syntax_facts
#  Inspect source-only syntax structure.
#
#
#  Source-only AST structure, independent of namespace and value-flow judgments.
#  仅描述源码 AST 结构，不依赖命名空间或数据流判断。



import ast
from collections import deque
from dataclasses import dataclass
from types import MappingProxyType

from pcresolve.facts.import_facts import import_facts


## A requested syntax walk exceeded its caller's node allowance.
## 请求的语法遍历超过调用方允许的节点数量。
class SyntaxLimit(Exception):
    pass


## Immutable structure in statement order, with breadth-first order per statement.
## 按语句顺序排列、每条语句内部广度优先的不可变结构。
@dataclass(frozen=True)
class BodySyntax:
    nodes: tuple
    parents: object
    imports: tuple


## Capture source structure without evaluating names or selecting analysis policy.
## 捕获源码结构，不求值名称或选择分析策略。
#
#  @param body Ordered top-level statements from an immutable source document.
#  @param limit Maximum nodes, including repeated singleton context/operator nodes.
#  @return Read-only nodes, last-parent lookup and ordered import syntax facts.
def body_syntax(body, limit):
    nodes, parents, imports = [], {}, []
    for statement in body:
        pending = deque([statement])
        while pending:
            node = pending.popleft()
            # Count repeated AST singleton nodes as visits, not unique identities.
            # 重复出现的 AST 单例节点按访问次数计数，而非按身份去重。
            if len(nodes) >= limit:
                raise SyntaxLimit()
            nodes.append(node)
            for child in ast.iter_child_nodes(node):
                parents[child] = node
                pending.append(child)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(import_facts(node))
    return BodySyntax(tuple(nodes), MappingProxyType(parents), tuple(imports))
