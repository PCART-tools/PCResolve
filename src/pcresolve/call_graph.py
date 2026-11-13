## @package pcresolve.call_graph
#  Internal function, class, call-edge and iteration facts used by ownership analysis.
#  归属分析使用的内部函数、类、调用边和迭代事实。

from dataclasses import dataclass, field
from .program_facts import FunctionSignature
from .call_resolution import CallContext
from .fact_versions import FactStructure, VersionedDict, VersionedList


## Unique identifier for a function or method within the project.
## 项目中函数或方法的逻辑标识。
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
## 单文件分析期间收集的函数摘要。
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
    ## Positional-only and positional-or-keyword parameters in declaration order.
    positional_params: list = field(default_factory=list)
    ## Keyword-only parameters in declaration order.
    keyword_only_params: list = field(default_factory=list)
    ## Name of the variadic positional parameter, if any.
    vararg: str = ""
    ## Name of the variadic keyword parameter, if any.
    kwarg: str = ""
    ## Sources of declaration-time defaults keyed by parameter name.
    #  Defaults are evaluated in the enclosing lexical scope and are used
    #  only when a call edge omits the corresponding parameter.
    defaults: dict = field(default_factory=dict)
    ## Source(s) yielded by a generator function.
    #  None means the function has no statically collected yield contract.
    yields: object = None
    ## Concrete return alternatives for receiver-protocol queries. Unlike
    #  symbol provenance, these include scalar, None, and unresolved branches.
    return_values: object = None
    ## Preserved syntax metadata, independent of ownership source payloads.
    positional_only_params: list = field(default_factory=list, repr=False)
    ## Definition location, independent of the logical ownership key.
    definition_span: object = field(default=None, repr=False, compare=False)

    ## Adapt collected source facts without caching mutable declaration defaults.
    ## 将已收集来源事实转换为签名，不缓存可变的声明默认值。
    #
    #  @return Shared signature, preserving the legacy positional fallback.
    @property
    def signature(self):
        positional = self.positional_params or [
            name for name in self.params if name not in (self.vararg, self.kwarg)]
        positional_only = tuple(name for name in positional if name in self.positional_only_params)
        return FunctionSignature(positional_only,
                                 tuple(name for name in positional if name not in positional_only),
                                 tuple(self.keyword_only_params), self.vararg, self.kwarg,
                                 tuple(self.defaults.items()))


## Per-class summary collected during single-file analysis.
## 单文件分析期间收集的类摘要。
@dataclass
class ClassSummary(FactStructure):
    _versioned_fields = {'methods': VersionedDict}
    ## Unique identifier for the class.
    id: FunctionId
    ## Base class symbols (names or dotted paths).
    bases: list = field(default_factory=list)
    ## Method summaries keyed by method name.
    methods: dict = field(default_factory=dict)
    ## self.attr bindings collected from __init__ and class body.
    #  Maps "self.attr" -> source.
    attrs: dict = field(default_factory=dict)
    ## Definition location; not part of public ownership output.
    definition_span: object = field(default=None, repr=False, compare=False)


## A single call edge in the intra-project call graph.
## 项目内部调用关系中的一条调用边。
@dataclass
class CallEdge:
    ## Who is calling (the enclosing function/method/module).
    caller: FunctionId
    ## What is being called — FunctionId for local, str for external.
    callee: object
    ## Syntactic callable name at the call site.
    #
    #  Preserves names such as create_body or module.create_body even when
    #  source tracing reduces the callee to local. Used for bounded project
    #  parameter propagation, not exposed as a public call graph.
    callee_name: str = ""
    ## Structured callable source before ownership classification.
    callee_source: object = None
    ## Possible exact targets selected from a literal mapping. None means
    #  this edge has no mapping evidence; an empty tuple rejects stale lookup.
    mapping_targets: object = None
    ## Whether every selected alternative is an exact local callable.
    mapping_targets_complete: bool = False
    ## Source of the receiver (for obj.method() calls).
    receiver_source: object = None
    ## Argument sources keyed by parameter name (best-effort).
    arg_sources: dict = field(default_factory=dict)
    ## Sources of starred positional expansions keyed by their lower-bound
    #  positional index.  The index is exact only when no later positional
    #  expansion makes the binding ambiguous.
    star_arg_sources: dict = field(default_factory=dict)
    ## Sources of starred keyword expansions, retained in source order.
    star_kwarg_sources: list = field(default_factory=list)
    ## Direct project-local callback arguments, keyed by positional index.
    #  Consumed only by bounded callback contracts such as
    #  multiprocessing.Pool.map(callback, iterable).
    callback_args: dict = field(default_factory=dict)
    ## Explicit callback invocations with keyword-bound argument tuples.
    #  Each item has callback and args fields.  This preserves source-level
    #  Process(target=..., args=(...)) bindings without claiming dispatch for
    #  arbitrary callback-taking libraries.
    callback_bindings: list = field(default_factory=list)
    ## Independently proven Python value shapes for protocol validation.
    #
    #  Kept separate from arg_sources so richer protocol evidence cannot
    #  affect local call-target or return-value resolution.
    protocol_arg_sources: dict = field(default_factory=dict)
    ## Independently preserved iterable element sources.
    #
    #  Kept separate from arg_sources because the owner of a container
    #  object is not the owner of each value yielded from that container.
    iterable_arg_sources: dict = field(default_factory=dict)
    ## Variable name(s) that receive the call result.
    assigned_to: list = field(default_factory=list)
    ## Source location.
    call_lineno: int = 0
    ## Source column.
    call_col_offset: int = 0
    ## Complete syntactic identity; not part of ownership's public output.
    source_span: object = field(default=None, repr=False, compare=False)


## A loop target bound from a call expression that produces an iterator.
## 由返回迭代器的调用表达式绑定的循环目标。
@dataclass
class IterationBinding:
    ## Enclosing caller function or module.
    caller: FunctionId
    ## Callable spelling used by the iterator expression.
    callee_name: str = ""
    ## Structured callable source at the iterator expression.
    callee_source: object = None
    ## Simple target names bound by the loop.
    target_names: list = field(default_factory=list)
    ## Source location of the iterator call.
    call_lineno: int = 0
    ## Source column of the iterator call.
    call_col_offset: int = 0


## Full call-graph facts for a module.
## 单个模块收集到的调用关系事实。
@dataclass
class ModuleCallGraph(FactStructure):
    _versioned_fields = {'functions': VersionedDict, 'classes': VersionedDict,
                         'edges': VersionedList}
    ## Module name.
    module: str
    ## Function summaries keyed by qualname.
    functions: dict = field(default_factory=dict)
    ## Class summaries keyed by class name.
    classes: dict = field(default_factory=dict)
    ## Call edges within this module.
    edges: list = field(default_factory=list)
    ## Generator-loop bindings collected in this module.
    iteration_bindings: list = field(default_factory=list)


## Full call-graph facts for a project.
## 项目中各模块收集到的调用关系事实。
@dataclass
class ProjectCallGraph(FactStructure):
    _versioned_fields = {'modules': VersionedDict}
    ## Per-module call-graph facts.
    modules: dict = field(default_factory=dict)
