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
