## @package pcresolve.flow.contracts
#  Narrow typed contracts shared by flow execution components.
#  数据流执行组件之间的窄类型契约。

import ast
from typing import Mapping, Optional, Protocol, Sequence, Set, Tuple

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef


## Cooperative resource boundary checked by flow execution components.
## 数据流执行组件检查的协作式资源边界。
class AnalysisBudgetPort(Protocol):
    ## Check whether the active analysis has crossed a resource limit.
    ## 检查当前分析是否达到资源上限。
    #
    #  @param force Perform a checkpoint even when no work was charged.
    #  @return None; raises at an exceeded limit.
    def checkpoint(self, force: bool = False) -> None:
        ...


## Callable contract for context-bound fresh-decoration proofs.
## 绑定到执行上下文的新鲜装饰证明回调契约。
class FreshDecorationProvider(Protocol):
    ## Compute a bounded fresh-decoration fact for an exact source function.
    ## 为精确源码函数计算有界的新鲜装饰事实。
    #
    #  @param ref Source function identity.
    #  @param node Function syntax carrying the selected decorator.
    #  @param limit Maximum proof work.
    #  @return Evidence record, or None when it cannot be established.
    def __call__(self, ref: FunctionRef, node: ast.AST, limit: int
                 ) -> Optional[Mapping[str, object]]:
        ...


## Invoke a fresh-decoration provider through the typed component boundary.
## 通过带类型的组件边界调用新鲜装饰证明。
#
#  @param provider Query-local proof provider.
#  @param ref Exact source function identity.
#  @param node Function syntax carrying the selected decorator.
#  @param limit Maximum proof work.
#  @return Evidence record or None when unproven.
def fresh_decoration_fact(provider: FreshDecorationProvider, ref: FunctionRef,
                          node: ast.AST, limit: int
                          ) -> Optional[Mapping[str, object]]:
    return provider(ref, node, limit)


## Read-only source index consumed by proof and transfer components.
## 证明与传播组件使用的只读源码索引。
class SourceIndexPort(Protocol):
    files: Set[str]
    hashes: Mapping[str, str]
    definitions: Sequence[Tuple[FunctionRef, ast.AST]]

    ## Find definitions by module and qualified name.
    ## 按模块和限定名查找定义。
    #
    #  @param module Source module name.
    #  @param qualname Definition qualified name.
    #  @param kind Optional syntax kind filter.
    #  @return Matching source definitions.
    def find(self, module: str, qualname: str, kind: Optional[str] = None
             ) -> Sequence[Tuple[FunctionRef, ast.AST]]:
        ...


## Analyzer data required to construct a query-local flow summary.
## 构造查询级数据流摘要所需的分析器数据。
class SummaryAnalyzerPort(SourceIndexPort, Protocol):
    texts: Mapping[str, str]


## Query-local state visible to value-flow transfer components.
## 数据流传播组件可见的查询级状态。
class FlowSummaryPort(Protocol):
    analyzer: SourceIndexPort
    result: FlowAnalysis
    ref: FunctionRef
    node: ast.AST
    remaining: int

    ## Record a conservative boundary at the current source location.
    ## 在当前源码位置记录保守分析边界。
    #
    #  @param reason Stable boundary reason.
    #  @param node Source syntax responsible for the boundary.
    #  @param env Current abstract environment.
    #  @return None.
    def add_boundary(self, reason: str, node: ast.AST,
                     env: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
        ...


## Minimal recursive summary surface used by child-summary call sites.
## 子摘要递归调用点所需的最小摘要接口。
class RecursiveSummaryPort(Protocol):
    analyzer: SummaryAnalyzerPort
    result: FlowAnalysis
    ref: FunctionRef
    node: ast.AST
    remaining: int
    calls: list[FlowCall]
    mapping_effects: list[object]
    conditions: list[object]
    context_execution: bool
    ## Shared with nested context-exit children to preserve query-wide order.
    context_cleanup_order: list[int]

    @property
    def incoming(self) -> Mapping[str, Sequence[Mapping[str, object]]]:
        ...

    def expression(self, node: ast.AST,
                   env: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
        ...

    def block(self, statements: Sequence[ast.stmt],
              env: Mapping[str, object]) -> Sequence[object]:
        ...


## Construct a child summary with isolated query-local state.
## 使用隔离的查询级状态创建子摘要。
class ChildSummaryFactory(Protocol):
    def __call__(self, result: FlowAnalysis, ref: FunctionRef, node: ast.AST,
                 remaining: int, receiver_class: Optional[FunctionRef] = None,
                 incoming: Optional[Mapping[str, Sequence[Mapping[str, object]]]] = None
                 ) -> RecursiveSummaryPort:
        ...
