## @package pcresolve.ownership_model
#  Explicit internal state for one ownership analysis run.
#  单次归属分析运行使用的显式内部状态。

from dataclasses import dataclass, field
from functools import wraps

from .call_graph import ProjectCallGraph
from .source_snapshot import SourceSnapshot
from .ast_facts import AstFactIndex


## Work budget shared by mutually recursive ownership proof queries.
## 相互递归的归属证明查询共享的工作预算。
@dataclass
class OwnershipProofBudget:
    ## Maximum query entries in one independent proof.
    max_queries: int = 4096
    ## Maximum nested query entries, independent of Python's stack limit.
    max_depth: int = 32
    ## Current nesting depth.
    depth: int = 0
    ## Query entries consumed by the active proof.
    queries: int = 0
    ## Whether any part of the active proof exceeded its limits.
    exhausted: bool = False


## Bound cross-resolver work and discard proofs with incomplete candidates.
## 限制跨解析器工作量，并丢弃候选不完整的证明。
#
#  @param fallback Factory producing the query's conservative unknown result.
#  @return Decorator sharing one budget across nested ownership queries.
def bounded_ownership_query(fallback):
    ## Wrap a query with the shared proof budget.
    ## 使用共享证明预算包装查询。
    #
    #  @param query Ownership query to wrap.
    #  @return Budget-aware query.
    def decorate(query):
        ## Enforce budget limits across nested calls to the query.
        ## 在嵌套查询中执行共享预算限制。
        #
        #  @param args Positional arguments forwarded to the query.
        #  @param kwargs Keyword arguments forwarded to the query.
        #  @return Query result or conservative fallback after exhaustion.
        @wraps(query)
        def bounded(self, *args, **kwargs):
            resources = getattr(self, '_analysis_budget', None)
            if resources is not None:
                resources.checkpoint()
            budget = self._ownership_proof_budget
            if budget.depth == 0:
                budget.queries = 0
                budget.exhausted = False
            if (budget.exhausted or budget.queries >= budget.max_queries
                    or budget.depth >= budget.max_depth):
                budget.exhausted = True
                return fallback()
            budget.depth += 1
            budget.queries += 1
            try:
                result = query(self, *args, **kwargs)
                # A cutoff in a nested candidate must invalidate the outer
                # proof too; a surviving subset cannot establish convergence.
                # 嵌套候选触及限制时，剩余子集无法证明整体收敛。
                return fallback() if budget.exhausted else result
            finally:
                budget.depth -= 1
        return bounded
    return decorate


## Immutable project inputs observed by one ownership analysis run.
## 单次归属分析运行观察到的不可变项目输入。
@dataclass(frozen=True)
class ProjectSnapshot:
    ## Ordered module names selected by the ownership adapter.
    modules: tuple
    ## Exact decoded source and AST versions used for those modules.
    sources: SourceSnapshot


## Mutable program facts assembled during one ownership analysis run.
## 单次归属分析运行中组装的可变程序事实。
@dataclass
class ProgramIndex:
    ## Per-module single-file analyzers, preserving discovery order.
    module_tracers: dict = field(default_factory=dict)
    ## Project call graph backed by the tracers' module summaries.
    call_graph: ProjectCallGraph = field(default_factory=ProjectCallGraph)

    ## Register one completed single-file analysis and its call-graph facts.
    ## 注册一个已完成的单文件分析及其调用关系事实。
    #
    #  @param module Dotted module name.
    #  @param tracer Completed SingleFileAnalyzer for the module.
    #  @return None.
    def add_module(self, module, tracer):
        self.module_tracers[module] = tracer
        graph = tracer.module_cg
        if (graph.functions or graph.classes or graph.edges
                or graph.iteration_bindings):
            self.call_graph.modules[module] = graph


## Mutable orchestration state owned by one ProjectAnalyzer.analyze() call.
## 单次 ProjectAnalyzer.analyze() 调用拥有的可变编排状态。
@dataclass
class OwnershipRun:
    ## Read-only AST lookup facts owned by this source generation.
    ast_facts: AstFactIndex = field(default_factory=AstFactIndex, init=False)
    ## Completed readonly proofs; recursive failures are never memoized.
    readonly_proofs: set = field(default_factory=set, init=False)
    ## Number of unmodified files whose pristine visitor facts were reused.
    source_facts_reused: int = field(default=0, init=False)
    ## Fixed module and source inputs for the run.
    snapshot: ProjectSnapshot
    ## Tracers and project-wide indexes built from the snapshot.
    program: ProgramIndex = field(default_factory=ProgramIndex)
    ## Diagnostics emitted while consuming the snapshot.
    diagnostics: list = field(default_factory=list)
    ## Cross-file symbol lookup table built during resolution.
    global_symbols: dict = field(default_factory=dict)
    ## Explanation chains corresponding to global symbol resolutions.
    symbol_chains: dict = field(default_factory=dict)
    ## Classified call records grouped by module.
    all_calls: dict = field(default_factory=dict)
    ## Active Python-shape queries used to stop recursive resolution cycles.
    python_shape_in_progress: set = field(default_factory=set)
    ## Active callable-field queries used to stop recursive resolution cycles.
    callable_field_in_progress: set = field(default_factory=set)
    ## Active call-edge target queries, including receiver provenance lookup.
    edge_target_in_progress: set = field(default_factory=set)
    ## Fresh cross-resolver proof limits for this analysis generation.
    proof_budget: OwnershipProofBudget = field(default_factory=OwnershipProofBudget)
    ## Lazily computed fields whose writes are confined to constructors.
    constructor_only_fields: object = None
