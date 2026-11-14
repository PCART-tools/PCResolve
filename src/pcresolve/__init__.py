## @package pcresolve
#  Project-level Python static analysis for API ownership and library usage
#  provenance.
#  面向项目级 Python API 归属与库使用来源的静态分析。
#
#  Usage:
#    import pcresolve
#    result = pcresolve.analyze_project("/path/to/project")
#    result = pcresolve.analyze_project("/path/to/a.py")  # Select one source.
#    for call in result.all_api_calls:
#        print(f"{call.expression} -> {call.top_library}")

from pcresolve.frontend.scanner import FileScanner, scan_directory
from pcresolve.frontend.module_mapper import ModuleMapper
from pcresolve.ownership.symbol_table import SymbolTable
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer, analyze_source
from pcresolve.ownership.analyzer import ProjectAnalyzer, analyze_project
from pcresolve.ownership.types import ApiCall, SymbolChain, FileAnalysis, ProjectAnalysis
from pcresolve.facts.program_facts import SourceSpan
from pcresolve.runtime.limits import AnalysisLimits, AnalysisLimitExceeded
from importlib import import_module as _import_module
from pcresolve.runtime._legacy_imports import (
    legacy_names_for as _legacy_names_for,
    legacy_target_for as _legacy_target_for,
    register_legacy_imports as _register_legacy_imports,
)

_register_legacy_imports(__name__)
del _register_legacy_imports

_FLOW_EXPORTS = {'FlowAnalyzer', 'FunctionRef', 'FlowAnalysis', 'FlowCall'}


## Resolve an experimental flow export or a requested legacy module lazily.
## 按需解析实验性数据流导出或旧版模块。
#
#  @param name Requested module attribute.
#  @return Public export or legacy module object.
def __getattr__(name):
    if name in _FLOW_EXPORTS:
        module = _import_module('pcresolve.flow')
        value = getattr(module, name)
        globals()[name] = value
        return value
    target = _legacy_target_for(__name__, name)
    if target is not None:
        value = _import_module('.' + target, __name__)
        globals()[name] = value
        return value
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


## List eager, lazy and legacy package attributes for interactive discovery.
## 为交互式发现列出即时、延迟和旧版包属性。
#
#  @return Sorted package attribute names.
def __dir__():
    return sorted(set(globals()) | set(_legacy_names_for(__name__)) | _FLOW_EXPORTS)

__all__ = [
    "AnalysisLimits",
    "AnalysisLimitExceeded",
    "FlowAnalyzer",
    "FunctionRef",
    "FlowAnalysis",
    "FlowCall",
    "SourceSpan",
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
