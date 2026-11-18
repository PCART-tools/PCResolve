## @package pcresolve.ownership.ir
#  Represent internal tracing facts.
#
#
#  Internal analysis IR for call sites and trace results.
#  调用点和追踪结果使用的内部分析中间表示。



from dataclasses import dataclass, field
from pcresolve.facts.program_facts import SourceSpan
from pcresolve.ownership.fact_versions import FactStructure

## Classification reason constants.
REASON_DIRECT_IMPORT = "DIRECT_IMPORT"
REASON_TRANSITIVE_IMPORT = "TRANSITIVE_IMPORT"
REASON_LOCAL_DEFINITION = "LOCAL_DEFINITION"
REASON_BUILTIN = "BUILTIN"
REASON_PARAMETER_PROPAGATION = "PARAMETER_PROPAGATION"
REASON_RETURN_PROPAGATION = "RETURN_PROPAGATION"
REASON_FLOW_MERGE = "FLOW_MERGE"
REASON_UNRESOLVED = "UNRESOLVED"


## Unified classification result for a call or symbol.
## 调用或符号的统一分类结果。
#
#  Bundles the library, reason, confidence, and alternatives into a single
#  result so that callers do not recompute top/alternatives/confidence
#  independently.
@dataclass
class ClassificationResult:
    ## Top-level library name, e.g. "requests", "local", "python", "unknown".
    library: str = ""
    ## Classification reason constant.
    reason: str = ""
    ## Confidence score (0.0-1.0).
    confidence: float = 1.0
    ## Alternative top libraries when multiple sources exist.
    alternatives: list = field(default_factory=list)
    ## Whether this result should appear in library_usage.
    is_usage_library: bool = False


## Raw facts about a call expression collected from AST.
## 从 AST 收集的调用表达式原始事实。
@dataclass
class CallSite:
    ## Full call expression.
    expression: str
    ## Function expression without arguments.
    func_name: str
    ## Argument text.
    parameters: str
    ## Base symbol or source.
    base: object
    ## Module name.
    module_name: str = ""
    ## File path.
    file_path: str = ""
    ## Line number.
    lineno: int = 0
    ## Column offset.
    col_offset: int = 0
    ## End line number.
    end_lineno: int = 0
    ## End column offset.
    end_col_offset: int = 0
    ## Scope qualname at the call site.
    scope_name: str = ""
    ## Argument sources (list of source values).
    arg_sources: list = field(default_factory=list)

    ## Shared internal identity without adding serialized fields to this adapter.
    ## 共享内部标识，不为此适配器增加序列化字段。
    #
    #  @return Complete source span of the call expression.
    @property
    def source_span(self):
        return SourceSpan(self.file_path, self.lineno, self.col_offset,
                          self.end_lineno, self.end_col_offset)


## A symbol definition or reference whose origin should be tracked.
## 需要追踪来源的符号定义或引用。
@dataclass
class SymbolRef(FactStructure):
    ## Notify fact consumers when the source or category changes.
    ## 来源或类别变化时通知事实使用方。
    #
    #  @param name Attribute name being assigned.
    #  @param value New attribute value.
    #  @return None
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        # Other metadata does not invalidate source-dependent facts.
        # 其他元数据不会使依赖来源的事实失效。
        if name in ('source', 'kind'):
            self._notify()

    ## Display name, such as "df", "self.session", or "models[0]".
    symbol: str
    ## Source object currently bound to this symbol.
    source: object
    ## Symbol category: import, variable, parameter, attribute, return,
    #  container_item, iteration.
    kind: str = ""
    ## Module name.
    module_name: str = ""
    ## File path.
    file_path: str = ""
    ## Scope name or qualname.
    scope_name: str = ""
    ## Line number.
    lineno: int = 0
    ## Column offset.
    col_offset: int = 0


## Final provenance record for one symbol.
## 单个符号的最终来源记录。
@dataclass
class SymbolProvenance:
    ## Display symbol name.
    symbol: str
    ## Symbol category.
    kind: str = ""
    ## Top-level related libraries or origins.
    top_libraries: list = field(default_factory=list)
    ## Main compatibility top value, usually first top library.
    top_library: str = ""
    ## Ordered trace chain.
    chain: list = field(default_factory=list)
    ## Scope name or qualname.
    scope_name: str = ""
    ## File path.
    file_path: str = ""
    ## Line number.
    lineno: int = 0
    ## Column offset.
    col_offset: int = 0
    ## Classification/provenance reason.
    reason: str = ""
    ## Confidence score.
    confidence: float = 1.0
    ## Alternative top libraries or trace candidates.
    alternatives: list = field(default_factory=list)
    ## Diagnostics related to this symbol.
    diagnostics: list = field(default_factory=list)


## Result of tracing one symbol or call site.
## 追踪单个符号或调用点的结果。
@dataclass
class TraceResult:
    ## Original source.
    source: object
    ## Ordered display chain.
    chain: list = field(default_factory=list)
    ## Possible top-level libraries or origins.
    tops: list = field(default_factory=list)
    ## Whether trace was complete.
    complete: bool = True
    ## Diagnostic objects or strings.
    diagnostics: list = field(default_factory=list)
