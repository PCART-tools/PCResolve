## @package pcresolve.ir
#  Internal analysis IR for call sites and trace results.

from dataclasses import dataclass, field


## Raw facts about a call expression collected from AST.
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


## A symbol definition or reference whose origin should be tracked.
@dataclass
class SymbolRef:
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
