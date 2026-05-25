## @package pcresolve.types
#  Shared data types for API call chain tracing results.
#

from dataclasses import dataclass, field


## Single API call record.
#
#  Captures an API call expression and its resolved top-level origin library.
@dataclass
class ApiCall:
    ## The full call expression, e.g. "requests.get(url, headers=h)".
    expression: str
    ## The top-level library or origin: "requests", "python", "local", etc.
    top_library: str
    ## The root symbol from which the call was traced.
    base_symbol: str
    ## The resolution chain from call site to origin.
    chain: list
    ## Absolute path to the source file containing this call.
    file_path: str = ""
    ## Line number of the call (1-based).
    lineno: int = 0
    ## Column offset of the call (0-based).
    col_offset: int = 0
    ## End line number of the call.
    end_lineno: int = 0
    ## End column offset of the call.
    end_col_offset: int = 0
    ## The function expression part (without arguments), e.g. "pl.DataFrame".
    func_name: str = ""
    ## The arguments string, e.g. "x, y=1".
    parameters: str = ""
    ## The symbol-resolved function path, stripped of concrete arguments.
    resolved_func: str = ""
    ## Concise 3-level resolution chain: [func_name, resolved_func, top_library].
    resolved_chain: list = field(default_factory=list)


## Trace chain for a single symbol.
#
#  Records how a symbol resolves through aliases/assignments to its ultimate source.
@dataclass
class SymbolChain:
    ## The symbol being traced.
    symbol: str
    ## Ordered chain of symbols from source to origin.
    chain: list
    ## The top-level library or origin name.
    top: str


## Result of analyzing a single Python source file.
@dataclass
class FileAnalysis:
    ## Absolute path to the source file.
    file_path: str
    ## Dotted module name derived from the file path.
    module_name: str
    ## Mapping of symbol -> top-level source.
    symbols: dict
    ## Mapping of symbol -> resolution chain.
    chains: dict
    ## All API calls found in this file.
    api_calls: list
    ## Diagnostics for this file (parse errors, etc.).
    diagnostics: list = field(default_factory=list)


## Result of analyzing an entire project.
@dataclass
class ProjectAnalysis:
    ## The project root directory that was scanned.
    project_root: str
    ## List of per-file analysis results.
    files: list
    ## Flat list of all API calls across all files.
    all_api_calls: list
    ## Schema version for the output format.
    schema_version: str = "1.0"
    ## Diagnostics collected during analysis.
    diagnostics: list = field(default_factory=list)
    ## Summary statistics about the analysis run.
    stats: dict = field(default_factory=dict)
