## @package pcresolve.cross_file
#  Provide cross-file project-level API call chain analysis.
#
#  The ProjectAnalyzer class orchestrates scanning a project, parsing every
#  .py file, building per-file symbol tables, resolving symbols across files,
#  and collecting all API calls with their top-level library origins.

import os
from .module_mapper import ModuleMapper
from .call_result_resolution import CallResultResolutionMixin
from .instance_method_resolution import InstanceMethodResolutionMixin
from .container_resolution import ContainerResolutionMixin
from .project_call_classification import ProjectCallClassificationMixin
from .project_call_context import ProjectCallContextMixin
from .project_local_classes import ProjectLocalClassesMixin
from .project_method_ownership import ProjectMethodOwnershipMixin
from .project_result_binding import ProjectResultBindingMixin
from .project_source_tracing import ProjectSourceTracingMixin
from .diagnostics import Diagnostic, FILE_READ_ERROR, SYNTAX_ERROR, ENCODING_ERROR
from .ir import SymbolProvenance
from .single_file import SingleFileAnalyzer
from .sources import (
    CallResult, ParameterSource, SourceSet, normalize_source, source_display,
)
from .source_snapshot import SourceStore, OWNERSHIP_SOURCE
from .ownership_model import OwnershipRun, ProjectSnapshot
from .classification import ClassificationPipeline
from .decorator_provenance import build_decorator_index, lookup_decorated_by
from .library_usage import build_library_usage
from .source_resolution import SourceSetResolver
from .types import ProjectAnalysis, FileAnalysis, ApiCall


## Remove consecutive duplicate items from a list while preserving order.
#  @param chain Input list.
#  @return List with no consecutive duplicates.
def _dedup_consecutive(chain):
    result = []
    for item in chain:
        if not result or item != result[-1]:
            result.append(item)
    return result


## Check whether a symbol is an imported external origin in this tracer.
#  @param tracer Single-file analyzer.
#  @param symbol Candidate external origin.
#  @return True if symbol matches an import source or its top-level package.
def _is_import_origin(tracer, symbol):
    if tracer is None or not isinstance(symbol, str):
        return False
    def _matches(value):
        if not isinstance(value, str):
            return False
        return (value == symbol
                or value.startswith(symbol + ".")
                or symbol.startswith(value + "."))
    for value in tracer.symbols.direct.values():
        if isinstance(value, SourceSet):
            for src in value.sources:
                if _matches(src):
                    return True
        elif _matches(value):
            return True
    # Function-local imports live in lexical scopes instead of the module-level
    # compatibility table. SymbolRef is the durable project
    # fact available after the visitor has left that scope.
    for ref in getattr(tracer, "symbol_refs", []):
        if ref.kind == "import" and _matches(normalize_source(ref.source)):
            return True
    return False


## Build an ApiCall from a get_calls() record dict.
#  @param c Call record dict.
#  @param deco_by Decorator evidence index.
#  @return ApiCall object.
def _make_api_call(c, deco_by):
    """Build an ApiCall from a get_calls() record dict."""
    return ApiCall(
        expression=c['api'],
        top_library=c['top'],
        base_symbol=source_display(c.get('base', '')),
        chain=c.get('chain', []),
        file_path=c.get('file_path', ''),
        lineno=c.get('lineno', 0),
        col_offset=c.get('col_offset', 0),
        end_lineno=c.get('end_lineno', 0),
        end_col_offset=c.get('end_col_offset', 0),
        func_name=c.get('func_name', ''),
        parameters=c.get('parameters', ''),
        resolved_func=c.get('resolved_func', ''),
        resolved_chain=[c.get('func_name', ''), c.get('resolved_func', ''), c.get('top', '')],
        reason=c.get('reason', ''),
        confidence=c.get('confidence', 1.0),
        alternatives=c.get('alternatives', []),
        decorated_by=lookup_decorated_by(
            c.get('file_path', ''),
            c.get('func_name', ''),
            c.get('scope_name', ''), deco_by),
    )


## Cross-file project analyzer that traces all API calls to their origins.
#
#  Steps:
#  1. Scan the project for all .py/.pyi files and map them to module names.
#  2. Parse each file and run SingleFileAnalyzer to build per-file symbol data.
#  3. Resolve cross-file symbol references across the project.
#  4. Classify every API call with its top-level library source.
class ProjectAnalyzer(CallResultResolutionMixin, InstanceMethodResolutionMixin,
                      ContainerResolutionMixin,
                      ProjectCallClassificationMixin,
                      ProjectCallContextMixin, ProjectLocalClassesMixin,
                      ProjectMethodOwnershipMixin, ProjectResultBindingMixin,
                      ProjectSourceTracingMixin):
    # ── pipeline ───────────────────────────────────────────────────────

    ## Initialize the analyzer for a project directory or one Python source file.
    #  @param project_root Path to the project directory or a .py/.pyi file.
    def __init__(self, project_root):
        self.module_mapper = ModuleMapper(project_root)
        self.project_root = (self.module_mapper.project_root
                             if os.path.isfile(project_root) else project_root)
        self._source_store = SourceStore()
        self._ownership_run = None
        self.global_symbols = {}
        self.symbol_chains = {}
        self.all_calls = {}
        self._python_shape_in_progress = set()
        self._callable_field_in_progress = set()
        self._constructor_only_fields = None
        self._source_resolver = SourceSetResolver(
            top_source_cb=self._top_source,
            cg_return_cb=self._lookup_cg_return_source,
            known_local_cb=self._is_known_local_symbol,
            resolve_structured_cb=self._resolve_structured_source,
            dedupe_cb=self._dedupe_list,
            is_import_origin_cb=_is_import_origin)
        self._pipeline = ClassificationPipeline(
            origin_candidates_cb=self._origin_candidates,
            is_direct_import_cb=self._is_direct_import_base,
            dedupe_cb=self._dedupe_list)

    ## Check whether a symbol has import-backed ownership evidence.
    #  @param tracer Single-file analyzer containing import facts.
    #  @param symbol Candidate symbol or top-level library name.
    #  @return True when the symbol matches an import origin.
    def _has_import_origin(self, tracer, symbol):
        return _is_import_origin(tracer, symbol)

    ## Run the full analysis: scan, parse, resolve, and collect.
    #  @return ProjectAnalysis with all results.
    def analyze(self):
        self.module_mapper.scan_project()
        all_modules = tuple(self.module_mapper.get_all_modules())
        paths = [self.module_mapper.get_file_path(module) for module in all_modules]
        sources = self._source_store.snapshot(
            [path for path in paths if path and os.path.exists(path)], OWNERSHIP_SOURCE)
        run = OwnershipRun(ProjectSnapshot(all_modules, sources))
        self._ownership_run = run
        # Compatibility aliases remain while resolver methods migrate to the
        # explicit run model in later behavior-preserving slices.
        self._source_snapshot = run.snapshot.sources
        self.project_cg = run.program.call_graph
        module_tracers = run.program.module_tracers
        diagnostics = run.diagnostics
        self.global_symbols = run.global_symbols
        self.symbol_chains = run.symbol_chains
        self.all_calls = run.all_calls
        self._python_shape_in_progress = run.python_shape_in_progress
        self._callable_field_in_progress = run.callable_field_in_progress
        self._constructor_only_fields = run.constructor_only_fields

        for module in all_modules:
            file_path = self.module_mapper.get_file_path(module)
            document = self._source_snapshot.documents.get(file_path)
            if document is None:
                continue
            e = document.error
            if isinstance(e, UnicodeDecodeError):
                diagnostics.append(Diagnostic(
                    code=ENCODING_ERROR,
                    message="Cannot decode file: %s" % e,
                    severity="error",
                    file_path=file_path,
                    module_name=module,
                ))
                continue
            if isinstance(e, OSError):
                diagnostics.append(Diagnostic(
                    code=FILE_READ_ERROR,
                    message="Cannot read file: %s" % e,
                    severity="error",
                    file_path=file_path,
                    module_name=module,
                ))
                continue
            if isinstance(e, SyntaxError):
                diagnostics.append(Diagnostic(
                    code=SYNTAX_ERROR,
                    message=str(e),
                    severity="error",
                    file_path=file_path,
                    lineno=getattr(e, 'lineno', 0),
                    col_offset=getattr(e, 'offset', 0) if getattr(e, 'offset', 0) else 0,
                    end_lineno=getattr(e, 'end_lineno', 0) or 0,
                    end_col_offset=getattr(e, 'end_offset', 0) if getattr(e, 'end_offset', 0) else 0,
                    module_name=module,
                ))
                continue
            tracer = SingleFileAnalyzer(
                module_name=module,
                is_package=self.module_mapper.is_package(module),
                file_path=file_path,
            )
            tracer.visit(document.tree)
            run.program.add_module(module, tracer)

        self._bind_bounded_local_call_results(module_tracers)
        self._bind_bounded_callback_map_results(module_tracers)
        self._bind_bounded_local_iteration_results(module_tracers)
        self._bind_proven_result_method_results(module_tracers)
        self.resolve_cross_file_symbols(module_tracers)
        self.get_calls(module_tracers)

        all_provenance = self._build_symbol_provenance(module_tracers)
        deco_by = self._build_decorator_index(all_provenance)

        files = self._build_file_analysis(module_tracers, all_provenance, deco_by)
        all_api_calls = self._build_all_api_calls(deco_by)
        library_usage = self._build_library_usage(all_api_calls, all_provenance)

        stats = {
            "total_modules": len(all_modules),
            "parsed_modules": len(module_tracers),
            "skipped_modules": len(diagnostics),
        }

        return ProjectAnalysis(
            project_root=self.project_root,
            files=files,
            all_api_calls=all_api_calls,
            diagnostics=diagnostics,
            stats=stats,
            all_symbol_provenance=all_provenance,
            library_usage=library_usage,
        )

    # ── provenance helpers ───────────────────────────────────────────────

    ## Check whether a top name is backed by any import evidence across tracers.
    def _is_prov_import_backed(self, name, tracers):
        if not isinstance(name, str) or '.' in name:
            return bool('.' in name) if isinstance(name, str) else False
        for tr in tracers.values():
            if _is_import_origin(tr, name):
                return True
            if name in getattr(tr, 'import_aliases', set()):
                return True
        return False

    # ── output construction ──────────────────────────────────────────────

    ## Build per-file analysis results.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param all_provenance List of SymbolProvenance records.
    #  @param deco_by Decorator evidence index.
    #  @return List of FileAnalysis records.
    def _build_file_analysis(self, module_tracers, all_provenance, deco_by):
        files = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            files.append(FileAnalysis(
                file_path=file_path,
                module_name=module,
                symbols=self.global_symbols.get(module, {}),
                chains=self.symbol_chains.get(module, {}),
                symbol_provenance=[p for p in all_provenance
                                   if p.file_path == file_path],
                api_calls=[_make_api_call(c, deco_by)
                           for c in self.all_calls.get(module, [])],
            ))
        return files

    ## Build the flat project-level API call list.
    #  @param deco_by Decorator evidence index.
    #  @return List of ApiCall records.
    def _build_all_api_calls(self, deco_by):
        return [_make_api_call(c, deco_by)
                for module, calls in self.all_calls.items()
                for c in calls]

    ## Build a decorator evidence index from provenance records.
    #  @param all_provenance List of SymbolProvenance records.
    #  @return Dict keyed by (file_path, scope, symbol) → [library, ...].
    def _build_decorator_index(self, all_provenance):
        return build_decorator_index(all_provenance)

    ## Build SymbolProvenance records from each tracer's symbol_refs.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of SymbolProvenance records.
    def _build_symbol_provenance(self, module_tracers):
        result = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            for ref in tracer.symbol_refs:
                direct_source = ref.source
                if ref.kind == "parameter" and ref.scope_name:
                    direct_source = ParameterSource(
                        ref.scope_name, ref.symbol)
                try:
                    chain = self.trace_symbol(module, ref.symbol, module_tracers,
                                               set(),
                                               _direct_source=direct_source)
                except RecursionError:
                    chain = [source_display(ref.source)]
                chain = _dedup_consecutive(chain)
                top = self.extract_final_source(chain) if chain else ""
                if top and top not in ("local", "python", "unknown", ""):
                    if '.' not in top and not self._is_prov_import_backed(top, module_tracers):
                        ## 1.0.5 P2: explicit result_source confirms library
                        #  identity even without import statement evidence.
                        rs = getattr(ref.source, 'result_source', None)
                        if (isinstance(ref.source, CallResult)
                                and isinstance(rs, str)
                                and rs not in ("local", "python", "unknown", "")
                                and rs.split(".")[0] == top):
                            pass
                        else:
                            top = "local"
                tops = [top] if top else []
                cr = self.classify_source(
                    ref.source, top, module, tracer, module_tracers,
                    expand_origins=False, symbol=ref.symbol, kind=ref.kind)
                prov = SymbolProvenance(
                    symbol=ref.symbol,
                    kind=ref.kind,
                    top_libraries=tops,
                    top_library=tops[0] if tops else "unknown",
                    chain=chain,
                    scope_name=ref.scope_name,
                    file_path=file_path or "",
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    reason=cr.reason,
                    confidence=cr.confidence,
                    alternatives=cr.alternatives,
                )
                result.append(prov)
        return result

    # ── library usage ────────────────────────────────────────────────────

    ## Build a library usage index from calls and provenance.
    #
    #  Delegates to library_usage.build_library_usage() (Phase 9-lite PR1).
    #  @param all_api_calls List of ApiCall records.
    #  @param all_provenance List of SymbolProvenance records.
    #  @return Dict of library_name -> LibraryUsage.
    def _build_library_usage(self, all_api_calls, all_provenance):
        return build_library_usage(
            self.project_root, all_api_calls, all_provenance)

    ## Check whether a module name belongs to the current project.
    #  @param module_name Dotted module name.
    #  @return True if the module is a local project module.
    def is_local(self, module_name):
        return module_name in self.module_mapper.get_all_modules()

## Analyze a project directory or one Python source file and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Path to the project directory or a .py/.pyi file.
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root):
    analyzer = ProjectAnalyzer(project_root)
    return analyzer.analyze()
