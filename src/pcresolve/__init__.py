## @package pcresolve
#  Static analysis tool for tracing Python API calls to their origin library.
#
#  Usage:
#    import pcresolve
#    result = pcresolve.analyze_project("/path/to/project")
#    for call in result.all_api_calls:
#        print(f"{call.expression} -> {call.top_library}")

from .scanner import FileScanner, scan_directory
from .module_mapper import ModuleMapper
from .symbol_table import SymbolTable
from .single_file import SingleFileAnalyzer, analyze_source
from .cross_file import ProjectAnalyzer, analyze_project
from .types import ApiCall, SymbolChain, FileAnalysis, ProjectAnalysis

__all__ = [
    "analyze_project",
    "analyze_source",
    "scan_directory",
    "ProjectAnalyzer",
    "SingleFileAnalyzer",
    "ModuleMapper",
    "SymbolTable",
    "FileScanner",
    "ApiCall",
    "SymbolChain",
    "FileAnalysis",
    "ProjectAnalysis",
]
