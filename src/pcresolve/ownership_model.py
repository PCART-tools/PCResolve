## @package pcresolve.ownership_model
#  Explicit internal state for one ownership analysis run.

from dataclasses import dataclass, field

from .call_graph import ProjectCallGraph
from .source_snapshot import SourceSnapshot


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
    ## Lazily computed fields whose writes are confined to constructors.
    constructor_only_fields: object = None
