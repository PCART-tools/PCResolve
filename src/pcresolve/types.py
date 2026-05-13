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


## Result of analyzing an entire project.
@dataclass
class ProjectAnalysis:
    ## The project root directory that was scanned.
    project_root: str
    ## List of per-file analysis results.
    files: list
    ## Flat list of all API calls across all files.
    all_api_calls: list
