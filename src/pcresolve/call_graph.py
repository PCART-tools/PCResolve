## @package pcresolve.call_graph
#  Lightweight call-graph facts for Phase 7B-full return-object tracking.
#
#  PR1 (this module): read-only fact collection — FunctionSummary,
#  ClassSummary, and CallEdge data structures plus collection helpers in
#  SingleFileAnalyzer.  PR2+ will consume these facts for classification.

from dataclasses import dataclass, field


## Unique identifier for a function or method within the project.
#
#  Uses (module, qualname) rather than file path so that the same logical
#  function can be referenced across analysis passes.
@dataclass(frozen=True)
class FunctionId:
    ## Dotted module name.
    module: str
    ## Qualified name within the module, e.g. "ClassName.method" or "func".
    qualname: str


## Per-function summary collected during single-file analysis.
#
#  Captured after visiting the function body so that return_sources and
#  local assignments reflect the full function.
@dataclass
class FunctionSummary:
    ## Unique identifier.
    id: FunctionId
    ## Ordered parameter names (excluding "self").
    params: list = field(default_factory=list)
    ## Return source(s) — SourceSet or single value from return_sources.
    returns: object = None
    ## Assignments to local variables within the function body.
    #  Maps local variable name to its traced source.
    local_assignments: dict = field(default_factory=dict)


## Per-class summary collected during single-file analysis.
@dataclass
class ClassSummary:
    ## Unique identifier for the class.
    id: FunctionId
    ## Base class symbols (names or dotted paths).
    bases: list = field(default_factory=list)
    ## Method summaries keyed by method name.
    methods: dict = field(default_factory=dict)
    ## self.attr bindings collected from __init__ and class body.
    #  Maps "self.attr" -> source.
    attrs: dict = field(default_factory=dict)


## A single call edge in the intra-project call graph.
@dataclass
class CallEdge:
    ## Who is calling (the enclosing function/method/module).
    caller: FunctionId
    ## What is being called — FunctionId for local, str for external.
    callee: object
    ## Source of the receiver (for obj.method() calls).
    receiver_source: object = None
    ## Argument sources keyed by parameter name (best-effort).
    arg_sources: dict = field(default_factory=dict)
    ## Variable name(s) that receive the call result.
    assigned_to: list = field(default_factory=list)
    ## Source location.
    call_lineno: int = 0
    ## Source column.
    call_col_offset: int = 0


## Full call-graph facts for a module.
@dataclass
class ModuleCallGraph:
    ## Module name.
    module: str
    ## Function summaries keyed by qualname.
    functions: dict = field(default_factory=dict)
    ## Class summaries keyed by class name.
    classes: dict = field(default_factory=dict)
    ## Call edges within this module.
    edges: list = field(default_factory=list)


## Full call-graph facts for a project.
@dataclass
class ProjectCallGraph:
    ## Per-module call-graph facts.
    modules: dict = field(default_factory=dict)
