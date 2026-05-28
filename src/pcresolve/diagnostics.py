## @package pcresolve.diagnostics
#  Structured diagnostics emitted during analysis.

from dataclasses import dataclass


## Diagnostic severity constants.
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

## Diagnostic code constants.
FILE_READ_ERROR = "FILE_READ_ERROR"
SYNTAX_ERROR = "SYNTAX_ERROR"
ENCODING_ERROR = "ENCODING_ERROR"
UNSUPPORTED_NODE = "UNSUPPORTED_NODE"
RECURSION_LIMIT = "RECURSION_LIMIT"
TRACE_CYCLE = "TRACE_CYCLE"


## A structured diagnostic produced while scanning, parsing, or tracing.
@dataclass
class Diagnostic:
    ## Stable diagnostic code.
    code: str
    ## Human-readable message.
    message: str
    ## Severity string: info, warning, or error.
    severity: str = SEVERITY_WARNING
    ## File path related to the diagnostic.
    file_path: str = ""
    ## Optional line number.
    lineno: int = 0
    ## Optional column offset.
    col_offset: int = 0
    ## Optional end line number.
    end_lineno: int = 0
    ## Optional end column offset.
    end_col_offset: int = 0
    ## Optional module name.
    module_name: str = ""
