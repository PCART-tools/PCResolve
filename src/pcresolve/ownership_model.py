## @package pcresolve.ownership_model
#  Explicit internal state for one ownership analysis run.

from dataclasses import dataclass, field
from functools import wraps

from .call_graph import ProjectCallGraph
from .source_snapshot import SourceSnapshot


## Work budget shared by mutually recursive ownership proof queries.
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
#  @param fallback Factory producing the query's conservative unknown result.
#  @return Decorator sharing one budget across nested ownership queries.
def bounded_ownership_query(fallback):
    def decorate(query):
        @wraps(query)
        def bounded(self, *args, **kwargs):
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
                return fallback() if budget.exhausted else result
            finally:
                budget.depth -= 1
        return bounded
    return decorate


## Immutable project inputs observed by one ownership analysis run.
@dataclass(frozen=True)
class ProjectSnapshot:
    ## Ordered module names selected by the ownership adapter.
    modules: tuple
    ## Exact decoded source and AST versions used for those modules.
    sources: SourceSnapshot


## Mutable program facts assembled during one ownership analysis run.
@dataclass
class ProgramIndex:
    ## Per-module single-file analyzers, preserving discovery order.
    module_tracers: dict = field(default_factory=dict)
    ## Project call graph backed by the tracers' module summaries.
    call_graph: ProjectCallGraph = field(default_factory=ProjectCallGraph)

    ## Register one completed single-file analysis and its call-graph facts.
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
@dataclass
class OwnershipRun:
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
