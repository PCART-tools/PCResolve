## @package pcresolve.cross_file
#  Provide cross-file project-level API call chain analysis.
#
#  The ProjectAnalyzer class orchestrates scanning a project, parsing every
#  .py file, building per-file symbol tables, resolving symbols across files,
#  and collecting all API calls with their top-level library origins.

import ast
import os
from .module_mapper import ModuleMapper
from .call_result_resolution import CallResultResolutionMixin
from .instance_method_resolution import InstanceMethodResolutionMixin
from .container_resolution import ContainerResolutionMixin
from .project_call_context import ProjectCallContextMixin
from .project_method_ownership import ProjectMethodOwnershipMixin
from .project_result_binding import ProjectResultBindingMixin
from .project_source_tracing import ProjectSourceTracingMixin
from .diagnostics import Diagnostic, FILE_READ_ERROR, SYNTAX_ERROR, ENCODING_ERROR
from .ir import (SymbolProvenance, ClassificationResult,
                    REASON_DIRECT_IMPORT)
from .single_file import SingleFileAnalyzer
from .builtin_ownership import (
    _BUILTIN_CONTAINER_METHODS, _is_builtin, _builtin_method_return_shape,
)
from .ownership_contracts import (
    _match_result_owner,
    _is_verified_result_owner, _match_result_python_shape,
)
from .sources import (ContainerItem, ContainerIter, InstanceMethod,
                       ParameterSource, PythonShape,
                       SuperMethod, CallResult,
                       DerivedResult, UnknownSource,
                       SourceSet, is_structured_source, normalize_source,
                       source_display)
from .call_graph import ProjectCallGraph
from .source_snapshot import SourceStore, OWNERSHIP_SOURCE
from .ownership_model import OwnershipRun, ProjectSnapshot
from .classification import classify_confidence, ClassificationPipeline
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
                      ContainerResolutionMixin, ProjectCallContextMixin,
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

    ## Downgrade an import-backed method owner after a visible monkey patch.
    #
    #  A patch on one imported class does not prove that every receiver from
    #  that library has the patched class. When the receiver has already been
    #  reduced to the library owner, the only sound primary is unknown.
    #  @param call_detail Single-file call record.
    #  @param tracer Analyzer for the current module.
    #  @param top_source Resolved import-backed owner.
    #  @return top_source or "unknown".
    def _apply_external_override_ambiguity(
            self, call_detail, tracer, top_source):
        if top_source in ("", None, "local", "python", "unknown"):
            return top_source
        func_name = call_detail.get("func_name", "")
        if "." not in func_name:
            return top_source
        method_name = func_name.rsplit(".", 1)[-1]
        patches = getattr(
            tracer, "external_method_overrides", {}).get(
                (top_source, method_name), [])
        if not patches:
            return top_source
        call_scope = call_detail.get("scope_name", "")
        call_line = call_detail.get("lineno", 0)
        for patch_scope, patch_line, _ in patches:
            visible = (
                patch_scope == ""
                or (
                    patch_scope == call_scope
                    and patch_line <= call_line
                )
            )
            if visible:
                return "unknown"
        return top_source

    ## Promote a chained local-call receiver to structured result evidence.
    #
    #  Single-file collection intentionally keeps ``make_value().method``
    #  conservative because the return object is resolved only after the
    #  project call graph is available.  Once the exact local edge is known,
    #  represent the receiver as a CallResult so the existing return-summary
    #  resolver can follow it.  This is limited to an unambiguous project
    #  call edge and never infers an external library from the method name.
    #  @param module Current caller module.
    #  @param call_detail Raw single-file call record.
    #  @param module_tracers All module analyzers.
    #  @return InstanceMethod receiver, or None when the edge is unresolved.
    def _promote_chained_local_call_receiver(
            self, module, call_detail, module_tracers):
        base = normalize_source(call_detail.get("base"))
        func_name = call_detail.get("func_name", "")
        if not isinstance(base, str) or not isinstance(func_name, str):
            return None
        marker = "()."
        if func_name.startswith(base + marker):
            inner_name, _, suffix = func_name.partition(marker)
        else:
            # The legacy base may be a resolved class name while func_name
            # retains the source receiver spelling.  Recover the inner call
            # from the recorded expression instead of requiring those two
            # representations to share a prefix.
            try:
                expression = ast.parse(
                    call_detail.get("api", ""), mode="eval").body
            except (SyntaxError, ValueError, TypeError):
                return None
            if (not isinstance(expression, ast.Call)
                    or not isinstance(expression.func, ast.Attribute)
                    or not isinstance(expression.func.value, ast.Call)):
                return None
            inner_name = ast.unparse(expression.func.value.func)
            suffix = expression.func.attr
        if not inner_name or not suffix:
            return None
        edges = [
            edge for edge in self.project_cg.modules.get(
                module, ProjectCallGraph()).edges
            if edge.caller.qualname == (
                call_detail.get("scope_name", "") or "<module>")
            and edge.call_lineno == call_detail.get("lineno", 0)
            and edge.call_col_offset == call_detail.get("col_offset", 0)
            and edge.callee_name == inner_name
        ]
        if len(edges) != 1:
            return None
        targets = self._local_edge_targets(edges[0], module, module_tracers)
        if len(targets) != 1:
            return None
        target = targets[0]
        result = CallResult(
            target.module + "." + target.qualname,
            display_name=inner_name,
            call_lineno=edges[0].call_lineno,
            call_col_offset=edges[0].call_col_offset,
            source_module=module,
        )
        return InstanceMethod(result, suffix.rsplit(".", 1)[-1])

    ## Collect all API calls across all modules and resolve their top-level origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def get_calls(self, module_tracers):
        self._call_searched_global = set()
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            for c in tracer.api_calls:
                c['file_path'] = file_path or ''

            self.all_calls[module] = []
            for call_detail in tracer.api_calls:
                base = call_detail.get('base')
                promoted_receiver = self._promote_chained_local_call_receiver(
                    module, call_detail, module_tracers)
                if (promoted_receiver is not None
                        and not isinstance(base, UnknownSource)):
                    base = promoted_receiver
                # A comprehension variable is an element of the receiver
                # container, not the owner of that container.  When a local
                # function returns a tuple and no positional binding reaches
                # the comprehension, keep the element unresolved instead of
                # promoting the homogeneous container owner.
                base_receiver = (
                    base.receiver
                    if isinstance(base, InstanceMethod) else base)
                if (call_detail.get('scope_name') == '<comprehension>'
                        and call_detail.get('func_name', '').split('.', 1)[0]
                        in getattr(tracer, 'comprehension_targets', set())
                        and isinstance(base_receiver, CallResult)
                        and base_receiver.result_source is None
                        and self._is_unbound_tuple_call_result(
                            module, base_receiver, module_tracers)):
                    base = UnknownSource("unresolved tuple element")
                    call_detail = dict(call_detail)
                    call_detail['top'] = 'unknown'
                if (call_detail.get('top') == 'unknown'
                        or isinstance(base, UnknownSource)):
                    # Preserve unknown top — the single-file phase
                    # already determined the owner cannot be resolved.
                    record = dict(call_detail)
                    record['top'] = 'unknown'
                    cr = self.classify_source(
                        base, 'unknown', module, tracer, module_tracers)
                    record['reason'] = cr.reason
                    record['confidence'] = cr.confidence
                    record['alternatives'] = cr.alternatives
                    self.all_calls[module].append(record)
                    continue
                if call_detail.get('top') == 'local':
                    if isinstance(base, str) or is_structured_source(base):
                        top_source = self._base_top_source(module, base, tracer, module_tracers)
                        if top_source and top_source != 'local':
                            top_source = self._apply_external_override_ambiguity(
                                call_detail, tracer, top_source)
                            record = dict(call_detail)
                            record['top'] = top_source
                            cr = self.classify_source(
                                base, top_source, module, tracer, module_tracers)
                            record['reason'] = cr.reason
                            record['alternatives'] = cr.alternatives
                            record['confidence'] = cr.confidence
                            self.all_calls[module].append(record)
                            continue
                    # 1.0.5 P0: container methods on local/builtin receivers
                    # must not inherit argument provenance as top_library.
                    # Argument provenance belongs in SymbolProvenance, not
                    # ApiCall.top_library.
                    record = dict(call_detail)
                    record['top'] = 'local'
                    cr = self.classify_source(
                        base, 'local', module, tracer, module_tracers)
                    record['reason'] = cr.reason
                    record['confidence'] = cr.confidence
                    record['alternatives'] = cr.alternatives
                    self.all_calls[module].append(record)
                    continue
                # 1.0.5 P1: preserve python top from single-file phase
                # for calls with call-site recorded container kind or a
                # lexically verified, unshadowed builtin callable.
                call_kind = call_detail.get("receiver_container_kind")
                direct_builtin = (
                    call_detail.get("top") == "python"
                    and call_detail.get("direct_name_callee") == base
                    and _is_builtin(base)
                )
                if ((call_kind is not None
                     and call_detail.get("top") == "python")
                        or direct_builtin):
                    record = dict(call_detail)
                    record['top'] = "python"
                else:
                    top_source = self._base_top_source(module, base, tracer, module_tracers)
                    top_source = self._apply_external_override_ambiguity(
                        call_detail, tracer, top_source)
                    record = dict(call_detail)
                    record['top'] = top_source
                cr = self.classify_source(
                    base, record['top'], module, tracer, module_tracers)
                record['reason'] = cr.reason
                record['alternatives'] = cr.alternatives
                record['confidence'] = cr.confidence
                self.all_calls[module].append(record)

        for module, tracer in module_tracers.items():
            for c in self.all_calls.get(module, []):
                c['resolved_func'] = self._resolve_func_name(c, module, tracer)

        self._call_searched_global = None

    ## Check whether a call result used in a comprehension is an unbound
    #  project-local tuple result.
    #  @param module Caller module.
    #  @param source CallResult used as the comprehension receiver.
    #  @param tracers Per-module analyzers.
    #  @return True when the tuple item position is not statically known.
    def _is_unbound_tuple_call_result(self, module, source, tracers):
        context = self._bounded_call_context(
            module, source.call_lineno, source.call_col_offset,
            tracers)
        if context is None:
            return False
        module_cg = self.project_cg.modules.get(context.target.module)
        summary = (
            module_cg.functions.get(context.target.qualname)
            if module_cg is not None else None)
        return summary is not None and self._is_tuple_return_source(
            summary.returns)

    ## Resolve the top-level source of a base symbol, preferring call_assign_funcs.
    #  @param module The current module.
    #  @param base The base symbol string.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name.
    def _base_top_source(self, module, base, tracer, module_tracers):
        if is_structured_source(base):
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, str)
                    and _is_verified_result_owner(base.receiver)):
                return base.receiver
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, CallResult)):
                result_owner = normalize_source(
                    base.receiver.result_source)
                if isinstance(result_owner, str) and result_owner:
                    return result_owner
                candidates = self._bounded_call_result_method_candidates(
                    module, base.receiver, base.method, module_tracers,
                    None, set(), None)
                candidate = self._bounded_candidates_top(candidates or [])
                if _is_verified_result_owner(candidate):
                    # A resolved owner is not a lexical symbol. Looking it
                    # up again can redirect it through a local star import.
                    return candidate
            structured = self._resolve_structured_source(module, base, module_tracers)
            if structured is not None:
                ## Explicit result_source carries an owner, not a symbol to
                # resolve again in module scope.  InstanceMethod receivers
                # cover assignments from function-local import chains.
                result = base
                if (isinstance(base, InstanceMethod)
                        and isinstance(base.receiver, CallResult)):
                    result = base.receiver
                if isinstance(result, CallResult):
                    rs = getattr(result, 'result_source', None)
                    if (isinstance(rs, str)
                            and rs not in ("local", "python", "unknown", "")):
                        return rs
                _, src_module, src_symbol = structured
                if src_symbol in ("local", "python", "unknown"):
                    return src_symbol
                if _is_verified_result_owner(src_symbol):
                    return src_symbol
                if (isinstance(base, InstanceMethod)
                        and base.parameter_scope
                        and isinstance(src_symbol, str)
                        and src_symbol):
                    return src_symbol
                top = self._top_source(src_module, src_symbol, module_tracers)
                # 1.0.5 P1: builtin container method on a receiver
                # whose container kind is known from tracer-final state.
                # This fallback only sees module-level legacy maps.
                # Function-local receiver kinds are captured at the call
                # site and preserved before this path is reached.
                if (top == "local"
                        and isinstance(base, InstanceMethod)
                        and base.receiver not in tracer.class_methods
                        and base.receiver in tracer.symbols.direct):
                    kind = getattr(tracer, "container_item_kinds", {}).get(base.receiver)
                    if kind is None:
                        kind = getattr(tracer, "container_kinds", {}).get(base.receiver)
                    if (kind is not None
                            and base.method in _BUILTIN_CONTAINER_METHODS.get(kind, frozenset())):
                        return "python"
                return top
            return "local"
        if isinstance(base, str) and '.' in base:
            prefix = base.split('.')[0]
            if prefix in self.global_symbols.get(module, {}):
                return self.global_symbols[module][prefix]
            return self._top_source(module, base, module_tracers)
        if isinstance(base, str):
            caf = tracer.call_assign_funcs.get(base)
            if caf:
                caf_first = caf.split('.')[0]
                top = self._top_source(module, caf_first, module_tracers)
                if top and top != 'local':
                    return top
        if base in self.global_symbols.get(module, {}):
            return self.global_symbols[module][base]
        return self._top_source(module, base, module_tracers)

    ## Check whether a symbol is a known local definition in this tracer.
    #  @param tracer Single-file analyzer.
    #  @param symbol Candidate symbol name.
    #  @return True if the symbol is a local function/method/class/param.
    def _is_known_local_symbol(self, tracer, symbol):
        if not isinstance(symbol, str):
            return False
        first = symbol.split(".")[0]
        if first in ("self", "cls"):
            return True
        if first in getattr(tracer, "local", set()):
            return True
        if first in getattr(tracer, "defined_functions", set()):
            return True
        if first in getattr(tracer, "class_methods", {}):
            return True
        for methods in getattr(tracer, "class_methods", {}).values():
            if first in methods:
                return True
        direct = normalize_source(tracer.symbols.direct.get(first))
        if direct == "local":
            return True
        return False

    ## Check whether a string base represents a direct import.
    #  @param tracer Single-file analyzer.
    #  @param base Candidate base name.
    #  @return True if base is an import alias or from-import symbol.
    def _is_direct_import_base(self, tracer, base):
        if not isinstance(base, str):
            return False
        first = base.split(".")[0]
        if first in getattr(tracer, "import_aliases", set()):
            return True
        if first in getattr(tracer, "import_from_symbols", {}):
            return True
        direct = normalize_source(tracer.symbols.direct.get(first))
        if isinstance(direct, str) and direct not in ("local", "python", "unknown"):
            return True
        return False

    ## Check whether a SymbolProvenance import is a direct external import.
    #
    #  True when the import source is a non-local module and the resolved
    #  top matches the source's top-level name.  Local re-exports
    #  (local_lib -> requests) are not direct external imports.
    #  @param base The import source value (e.g. "functools").
    #  @param top The resolved top library.
    #  @param module The module where the import occurs.
    #  @return True if this is a direct external import.
    def _is_direct_external_import(self, base, top, module):
        if not isinstance(base, str) or not top:
            return False
        first = base.split(".")[0]
        if self.is_local(first):
            return False
        if top == first:
            return True
        return False

    ## Converge argument candidates under the receiver-preserving ufunc rule.
    #  @param candidate_groups One candidate-owner list per ufunc argument.
    #  @return Result owner or "unknown".
    def _receiver_preserving_ufunc_owner(self, candidate_groups):
        owners = []
        for candidates in candidate_groups:
            unique = self._dedupe_list(
                candidate for candidate in candidates
                if candidate not in (None, ""))
            if len(unique) != 1:
                return "unknown"
            owners.append(unique[0])
        if any(owner in ("local", "unknown") for owner in owners):
            return "unknown"
        external = self._dedupe_list(
            owner for owner in owners if owner != "python")
        if not external:
            return "numpy"
        if len(external) == 1 and external[0] in ("numpy", "pandas"):
            return external[0]
        return "unknown"

    ## Converge exact operands for a local arithmetic return expression.
    #  @param candidate_groups One candidate-owner list per expression operand.
    #  @return Result owner or "unknown".
    def _bounded_expression_owner(self, candidate_groups):
        owners = []
        for candidates in candidate_groups:
            unique = self._dedupe_list(
                candidate for candidate in candidates
                if candidate not in (None, ""))
            if len(unique) != 1 or unique[0] == "unknown":
                return "unknown"
            owners.append(unique[0])
        external = self._dedupe_list(
            owner for owner in owners
            if owner not in ("local", "python"))
        if len(external) == 1 and all(
                owner in (external[0], "python") for owner in owners):
            return external[0]
        if owners and all(owner == "python" for owner in owners):
            return "python"
        if owners and all(owner == "local" for owner in owners):
            return "local"
        return "unknown"

    ## Collect all origin candidates from a source value.
    #  @param module Current module name.
    #  @param source Source value to expand.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param include_local Whether to include "local" in results.
    #  @return List of candidate top strings.
    def _origin_candidates(self, module, source, tracers, include_local=True,
                           _seen=None):
        if _seen is None:
            _seen = set()
        source = normalize_source(source)
        key = (module, type(source).__name__, source_display(source))
        if key in _seen:
            return ["unknown"]
        seen = set(_seen)
        seen.add(key)

        if isinstance(source, SourceSet):
            out = []
            for item in source.sources:
                out.extend(self._origin_candidates(
                    module, item, tracers, include_local,
                    _seen=set(seen)))
            return self._dedupe_list(out)
        if isinstance(source, PythonShape):
            return ["python"]
        if isinstance(source, DerivedResult):
            if source.kind == "iterator":
                return ["unknown"]
            if source.kind == "receiver_preserving_ufunc":
                candidate_groups = [
                    self._argument_owner_candidates(module, item, tracers)
                    for item in source.sources
                ]
                return [self._receiver_preserving_ufunc_owner(
                    candidate_groups)]
            if source.kind == "method_result":
                if len(source.sources) != 1:
                    return ["unknown"]
                method_source = normalize_source(source.sources[0])
                if not isinstance(method_source, InstanceMethod):
                    return ["unknown"]
                resolved = self._resolve_structured_source(
                    module, method_source, tracers, _seen=set(seen))
                if resolved is None:
                    return ["unknown"]
                _, receiver_module, receiver_symbol = resolved
                receiver_top = self._top_source(
                    receiver_module, receiver_symbol, tracers,
                    _seen=set(seen))
                if receiver_top == "python":
                    return ["python"]
                result_owner = _match_result_owner(
                    receiver_top, method_source.method)
                return [result_owner or "unknown"]
            if source.kind == "expression":
                # An expression receiver is owner evidence only when every
                # operand resolves to the same concrete owner.  A parameter
                # expression with unresolved or mixed operands must remain
                # unknown rather than falling through to local.  Explicit
                # local evidence is retained when no external owner is
                # present, which preserves local protocol receivers such as
                # ``(self.value * mask).sum()``.
                operand_candidates = []
                numeric_scalars = True
                saw_local = False
                saw_unresolved = False
                for item in source.sources:
                    shape = self._returned_python_shape(module, item, tracers)
                    candidates = (["python"] if shape is not None else
                                  self._argument_owner_candidates(
                                      module, item, tracers))
                    saw_local = saw_local or "local" in candidates
                    saw_unresolved = (
                        saw_unresolved or "unknown" in candidates)
                    concrete = self._dedupe_list([
                        candidate for candidate in candidates
                        if candidate not in (None, "", "unknown", "local")
                    ])
                    if len(concrete) != 1:
                        if concrete:
                            return ["unknown"]
                        saw_unresolved = True
                        continue
                    if concrete[0] == "python":
                        numeric_scalars = numeric_scalars and (
                            shape is not None and shape.kind in (
                                "bool", "int", "float", "complex"))
                    operand_candidates.append(concrete[0])
                external = set(operand_candidates) - {"python"}
                if (len(external) == 1 and "python" in operand_candidates
                        and numeric_scalars and not saw_unresolved
                        and not saw_local and source.attribute in (
                            "Add", "Sub", "Mult", "Div", "FloorDiv", "Mod",
                            "Pow", "Compare")):
                    return [next(iter(external))]
                if (operand_candidates and not saw_unresolved
                        and not saw_local and all(
                        owner == operand_candidates[0]
                        for owner in operand_candidates)):
                    return [operand_candidates[0]]
                if not operand_candidates and saw_local:
                    return ["local"]
                return ["unknown"]
            out = []
            for item in source.sources:
                out.extend(self._origin_candidates(
                    module, item, tracers, include_local,
                    _seen=set(seen)))
            return self._dedupe_list(out) or ["unknown"]
        if isinstance(source, UnknownSource):
            return ["unknown"]
        if isinstance(source, ContainerItem):
            container = normalize_source(source.container)
            if (isinstance(container, CallResult)
                    and isinstance(source.index, int)):
                source_origin_module = container.source_module or module
                candidates = self._bounded_call_result_item_candidates(
                    source_origin_module, container, source.index, tracers,
                    _seen=seen)
                if candidates is not None:
                    return candidates
                # No project-local tuple contract exists. Preserve the
                # established aggregate call-result fallback for external
                # calls instead of treating the positional marker as a
                # project container lookup.
                return self._origin_candidates(
                    source_origin_module, container, tracers, include_local,
                    _seen=set(seen))
        if isinstance(source, ContainerIter):
            resolved = self._resolve_container_iter(
                module, source.container, tracers)
            if resolved is None:
                return ["unknown"]
            _, candidates = resolved
            return self._dedupe_list(candidates) or ["unknown"]
        if (isinstance(source, InstanceMethod)
                and isinstance(
                    normalize_source(source.receiver), CallResult)):
            return self._origin_candidates(
                module, normalize_source(source.receiver), tracers,
                include_local, _seen=set(seen))
        if isinstance(source, CallResult):
            source_origin_module = source.source_module or module
            if source.result_source is not None:
                if (isinstance(source.result_source, str)
                        and source.result_source not in (
                            "", "local", "python", "unknown")):
                    return [source.result_source]
                return self._origin_candidates(
                    source_origin_module, source.result_source, tracers,
                    include_local,
                    _seen=set(seen))
            bounded = self._bounded_call_result_candidates(
                module, source, tracers, _seen=set(seen))
            if bounded is not None:
                return bounded
            if self._local_class_from_source(module, source) is not None:
                return ["local"]
            callee = source.callee
            tracer = tracers.get(module)
            rs = tracer.return_sources.get(callee) if tracer else None
            if rs is not None:
                candidates = self._origin_candidates(
                    module, rs, tracers, include_local,
                    _seen=set(seen))
                clean = [c for c in candidates
                         if c not in ("", None, "unknown")]
                if clean:
                    return clean
                cr_lineno = getattr(source, 'call_lineno', 0) or 0
                cr_col = getattr(source, 'call_col_offset', 0) or 0
                if cr_lineno:
                    rs_norm = normalize_source(rs)
                    if isinstance(rs_norm, SourceSet):
                        for s in rs_norm.sources:
                            if isinstance(s, str):
                                arg = self._resolve_param_to_arg(
                                    module, callee, s, tracers,
                                    call_lineno=cr_lineno, call_col_offset=cr_col)
                                if arg is not None:
                                    more = self._origin_candidates(
                                        module, arg, tracers, include_local,
                                        _seen=set(seen))
                                    for m in more:
                                        if m not in candidates:
                                            candidates.append(m)
                    else:
                        arg = self._resolve_param_to_arg(
                            module, callee, rs, tracers,
                            call_lineno=cr_lineno, call_col_offset=cr_col)
                        if arg is not None:
                            more = self._origin_candidates(
                                module, arg, tracers, include_local,
                                _seen=set(seen))
                            for m in more:
                                if m not in candidates:
                                    candidates.append(m)
                return candidates
            top = self._top_source(
                source_origin_module, callee, tracers, _seen=set(seen))
            return [top] if top else []
        if is_structured_source(source):
            resolved = self._resolve_structured_source(
                module, source, tracers, _seen=set(seen))
            if resolved is not None:
                _, src_module, src_symbol = resolved
                return self._origin_candidates(
                    src_module, src_symbol, tracers, include_local,
                    _seen=set(seen))
            return ["unknown"]
        if isinstance(source, str):
            top = self._top_source(
                module, source, tracers, _seen=set(seen))
            return [top] if top else []
        return ["unknown"]

    ## Deduplicate a list preserving order.
    #  @param items List of strings.
    #  @return Deduplicated list.
    @staticmethod
    def _dedupe_list(items):
        seen = set()
        out = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    ## Determine the classification reason for a resolved API call.
    #  @param base The call's base symbol or source.
    #  @param top The resolved top-level library.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @return Reason constant string.
    # ── classification helpers ───────────────────────────────────────────

    ## Determine confidence for a classification result.
    #
    #  Delegates to the standalone classify_confidence() in
    #  classification.py so the confidence rules live in one place.
    #  @param reason Classification reason.
    #  @param alternatives List of alternative top libraries.
    #  @return Confidence score (0.0-1.0).
    def _classify_confidence(self, reason, alternatives=None):
        return classify_confidence(reason, alternatives)

    ## Unified classification entry point for a resolved top library.
    #
    #  Delegates to ClassificationPipeline.classify() (Phase 8B).
    #  Kept as a thin wrapper so callers in get_calls() and
    #  _build_symbol_provenance() do not need to change.
    #  @param base The call's base symbol or source.
    #  @param top The resolved top-level library.
    #  @param module Current module name.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return ClassificationResult with library/reason/confidence/alternatives.
    def classify_source(self, base, top, module, tracer, module_tracers,
                        expand_origins=True, symbol=None, kind=""):
        if kind == "import" and self._is_direct_external_import(base, top, module):
            # Override: direct external imports always use DIRECT_IMPORT reason.
            result = self._pipeline.classify(
                base, top, module, tracer, module_tracers,
                expand_origins=expand_origins)
            return ClassificationResult(
                library=result.library,
                reason=REASON_DIRECT_IMPORT,
                confidence=classify_confidence(REASON_DIRECT_IMPORT),
                alternatives=result.alternatives,
                is_usage_library=result.is_usage_library)
        return self._pipeline.classify(
            base, top, module, tracer, module_tracers,
            expand_origins=expand_origins)

    ## Resolve the first segment of func_name to its fully qualified path.
    #  @param call_dict Dict with 'func_name' and other call data.
    #  @param module The module where the call occurs.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param _visited Set of already-visited first names (cycle detection).
    #  @return Resolved function path string.
    def _resolve_func_name(self, call_dict, module, tracer, _visited=None):
        func_name = call_dict.get('func_name', '')
        if not func_name:
            return func_name
        base = normalize_source(call_dict.get('base'))
        if isinstance(base, SuperMethod):
            base_path = call_dict.get('super_base_path')
            decorator_module = call_dict.get('super_decorator_module')
            decorator_parts = decorator_module.split('.') if decorator_module else []
            local_decorator = any(
                self.is_local('.'.join(decorator_parts[:length]))
                for length in range(1, len(decorator_parts) + 1)
            )
            if (isinstance(base_path, str) and base_path
                    and not self.is_local(base_path.split('.')[0])
                    and not local_decorator):
                # Public import provenance is a display hint, not the
                # method's runtime defining class or an importability claim.
                return base_path + '.' + base.method
            return func_name
        parts = func_name.split('.')
        first = parts[0]

        if _visited is None:
            _visited = set()
        if first in _visited:
            return func_name
        _visited.add(first)

        replacement = None
        if "call_import_source" in call_dict:
            ifs = call_dict["call_import_source"]
        else:
            ifs = tracer.import_from_symbols.get(first)
        if ifs:
            ifs_top = ifs.split('.')[0]
            if not self.is_local(ifs_top):
                replacement = ifs
        else:
            # 1.0.5 P0: prefer call-site snapshot (key present)
            # over final tracer map so RHS sub-calls see
            # pre-assignment state.  A snapshot of None means
            # "not in call_assign_funcs at call time", which
            # must not be replaced by a later assignment.
            if 'call_assign_func' in call_dict:
                caf = call_dict['call_assign_func']
            else:
                caf = tracer.call_assign_funcs.get(first)
            # Bare-name factories are represented directly by the call-result
            # source rather than call_assign_funcs (which records dotted
            # callees).  Use that exact source only when it identifies one
            # callee; SourceSet and other structured callees are intentionally
            # left unresolved instead of selecting one candidate.
            if not caf:
                call_base = normalize_source(call_dict.get('base'))
                if isinstance(call_base, CallResult):
                    factory_callee = normalize_source(call_base.callee)
                    if isinstance(factory_callee, str):
                        if (call_base.display_name
                                and '.' in call_base.display_name):
                            caf = call_base.display_name
                        else:
                            caf = factory_callee
            if caf and not caf.startswith(first + '.'):
                resolved_callee = self._resolve_func_name({'func_name': caf}, module, tracer, _visited)
                if resolved_callee and not resolved_callee.startswith('self.'):
                    replacement = resolved_callee

            if replacement is None:
                sd = tracer.symbols.direct.get(first)
                if isinstance(sd, str):
                    if sd == 'local' or sd == 'self' or sd.startswith('self.'):
                        return func_name
                    # If sd is a simple local name, try to resolve it further
                    if '.' not in sd:
                        gs_sd = self.global_symbols.get(module, {}).get(sd)
                        if gs_sd and gs_sd != 'local' and gs_sd != 'python':
                            replacement = gs_sd
                        else:
                            replacement = sd
                    else:
                        replacement = sd

            if replacement is None:
                gs = self.global_symbols.get(module, {}).get(first)
                if isinstance(gs, str):
                    if gs == 'local' or gs == 'python':
                        return func_name
                    replacement = gs
                elif gs is not None:
                    return func_name

        if replacement is None:
            return func_name

        # If the replacement's root is a local symbol, don't use it
        rep_first = replacement.split('.')[0]
        if rep_first == 'self' or (rep_first and rep_first != first):
            rep_gs = self.global_symbols.get(module, {}).get(rep_first)
            if rep_gs == 'local':
                return func_name

        if len(parts) == 1:
            return replacement

        # 1.0.5 P1: if the call's base has a class.method form (e.g.
        # InstanceMethod("Session","get")), resolve the class through
        # import_from_symbols for a more precise resolved_func
        # (e.g. requests.Session.get instead of requests.get).
        base_raw = call_dict.get('base', '')
        base_norm = normalize_source(base_raw)
        if isinstance(base_norm, InstanceMethod):
            receiver = base_norm.receiver
            if isinstance(receiver, str) and receiver in tracer.import_from_symbols:
                ifs = tracer.import_from_symbols[receiver]
                if not self.is_local(ifs.split('.')[0]):
                    return ifs + '.' + base_norm.method

        return replacement + '.' + '.'.join(parts[1:])

    ## Find one instance-field binding on a local class or its local bases.
    #  @param module Defining module of the candidate class.
    #  @param class_name Candidate class name.
    #  @param attribute Normalized ``self.<field>`` path.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Inheritance recursion guard.
    #  @return List of (module, source) bindings.
    def _local_class_attribute_bindings(
            self, module, class_name, attribute, tracers, visited=None):
        identity = (module, class_name)
        seen = set(visited or set())
        if identity in seen:
            return []
        seen.add(identity)
        module_cg = self.project_cg.modules.get(module)
        class_summary = (
            module_cg.classes.get(class_name)
            if module_cg is not None else None)
        if class_summary is None:
            return []
        if attribute in class_summary.attrs:
            return [(module, class_summary.attrs[attribute])]

        bindings = []
        tracer = tracers.get(module)
        if tracer is None:
            return []
        for base_symbol in tracer.class_bases.get(class_name, []):
            base_identity = self._resolve_local_class_identity(
                module, base_symbol, tracers)
            if base_identity is None:
                continue
            bindings.extend(self._local_class_attribute_bindings(
                base_identity[0], base_identity[1], attribute, tracers,
                seen))
        return self._dedupe_list(bindings)

    ## Identify a project-local class constructor source.
    #  @param module Module containing the source.
    #  @param source Source to inspect.
    #  @return (module, class name) or None.
    def _local_class_from_source(self, module, source):
        source = normalize_source(source)
        if isinstance(source, CallResult):
            source = normalize_source(source.callee)
        if not isinstance(source, str):
            return None
        cg = getattr(self, "project_cg", None)
        if cg is None:
            return None
        if module in cg.modules and source in cg.modules[module].classes:
            return (module, source)
        parts = source.split(".")
        for index in range(len(parts) - 1, 0, -1):
            candidate_module = ".".join(parts[:index])
            candidate_class = ".".join(parts[index:])
            module_cg = cg.modules.get(candidate_module)
            if module_cg and candidate_class in module_cg.classes:
                return (candidate_module, candidate_class)
        return None

    ## Resolve a local class returned by a local class or static method.
    #
    #  This follows only an explicit return summary. It does not infer a
    #  class from a method name or from a variable spelling. Every return
    #  branch must resolve to a project-local class; multiple classes remain
    #  ambiguous and are resolved conservatively by the caller.
    #  @param module Module containing the call result.
    #  @param source CallResult representing a method call.
    #  @param tracers Dict of module name to analyzer.
    #  @return List of unique local class identities.
    def _local_class_from_method_result(self, module, source, tracers):
        source = normalize_source(source)
        if not isinstance(source, CallResult):
            return []
        callee = source.callee
        if not isinstance(callee, str) or "." not in callee:
            return []
        caller_tracer = tracers.get(module)
        identities = []
        for candidate_module, module_cg in self.project_cg.modules.items():
            for class_name, class_summary in module_cg.classes.items():
                for method_name, method_summary in class_summary.methods.items():
                    qualified_class = candidate_module + "." + class_name
                    qualified_method = qualified_class + "." + method_name
                    spellings = {qualified_method}
                    if candidate_module == module:
                        spellings.add(class_name + "." + method_name)
                    if caller_tracer is not None:
                        parts = callee.split(".")
                        prefix = parts[0]
                        imported = caller_tracer.import_from_symbols.get(
                            prefix)
                        if (isinstance(imported, str)
                                and imported + "." + method_name
                                == qualified_method):
                            spellings.add(callee)
                        direct = normalize_source(
                            caller_tracer.symbols.direct.get(prefix))
                        if (isinstance(direct, str)
                                and direct == candidate_module
                                and len(parts) == 3
                                and parts[1] == class_name
                                and parts[2] == method_name):
                            spellings.add(callee)
                    if callee not in spellings:
                        continue
                    returns = normalize_source(method_summary.returns)
                    if returns is None:
                        continue
                    return_sources = (
                        list(returns.sources)
                        if isinstance(returns, SourceSet)
                        else [returns]
                    )
                    returned_classes = []
                    for returned in return_sources:
                        returned = normalize_source(returned)
                        if returned == "self":
                            returned_classes.append(
                                (candidate_module, class_name))
                            continue
                        if isinstance(returned, CallResult):
                            returned = returned.callee
                        identity = self._local_class_from_source(
                            candidate_module, returned)
                        if identity is None:
                            returned_classes = []
                            break
                        returned_classes.append(identity)
                    if returned_classes:
                        identities.extend(self._dedupe_list(returned_classes))
        return self._dedupe_list(identities)

    ## Resolve local classes returned by a project-local function.
    #
    #  The function must have an explicit return summary whose every branch
    #  resolves to one project-local constructor.  This deliberately does not
    #  infer a class from a function name, argument type, or method spelling.
    #  @param module Module containing the call site.
    #  @param callee Callee spelling from a CallResult.
    #  @param tracers Dict of module name to analyzer.
    #  @return List of unique local class identities.
    def _local_classes_from_function_result(self, module, callee, tracers):
        if not isinstance(callee, str):
            return []
        candidates = []
        caller_tracer = tracers.get(module)
        if caller_tracer is not None:
            imported = caller_tracer.import_from_symbols.get(callee)
            if isinstance(imported, str):
                candidates.append((module, imported))

        parts = callee.split(".")
        for index in range(len(parts), 0, -1):
            candidate_module = ".".join(parts[:index])
            if candidate_module in tracers:
                candidates.append((
                    candidate_module, ".".join(parts[index:])))
                break
        candidates.append((module, callee))

        identities = []
        seen = set()
        for target_module, qualname in candidates:
            key = (target_module, qualname)
            if key in seen or not qualname:
                continue
            seen.add(key)
            tracer = tracers.get(target_module)
            if tracer is None:
                continue
            returns = tracer.return_sources.get(qualname)
            if returns is None and target_module == module:
                returns = tracer.return_sources.get(parts[-1])
            if returns is None:
                continue
            normalized = normalize_source(returns)
            returned_sources = (
                list(normalized.sources)
                if isinstance(normalized, SourceSet)
                else [normalized]
            )
            branch_identities = []
            for returned in returned_sources:
                returned = normalize_source(returned)
                if isinstance(returned, CallResult):
                    returned = returned.callee
                identity = self._local_class_from_source(
                    target_module, returned)
                if identity is None:
                    branch_identities = []
                    break
                branch_identities.append(identity)
            if branch_identities:
                identities.extend(branch_identities)
        return self._dedupe_list(identities)

    ## Check whether a local class owns a method through local inheritance.
    #  @param module Defining module of the class.
    #  @param class_name Local class name.
    #  @param method_name Method name.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard.
    #  @return True when the method is locally defined or locally inherited.
    def _local_class_defines_method(self, module, class_name, method_name,
                                    tracers, visited=None):
        key = (module, class_name, method_name)
        seen = set(visited or set())
        if key in seen:
            return False
        seen.add(key)
        module_cg = self.project_cg.modules.get(module)
        if module_cg is None:
            return False
        class_summary = module_cg.classes.get(class_name)
        if class_summary is None:
            return False
        if method_name in class_summary.methods:
            return True
        tracer = tracers.get(module)
        if tracer is None:
            return False
        for base_symbol in class_summary.bases:
            base_identity = self._resolve_local_class_identity(
                module, base_symbol, tracers)
            if base_identity and self._local_class_defines_method(
                    base_identity[0], base_identity[1], method_name,
                    tracers, seen):
                return True
        return False

    ## Resolve a project-local class through imports and package re-exports.
    #
    #  @param module Module where the class symbol is referenced.
    #  @param source Class symbol or constructor source.
    #  @param tracers Dict of module name to analyzer.
    #  @return (defining module, class name) or None.
    def _resolve_local_class_identity(self, module, source, tracers):
        direct = self._local_class_from_source(module, source)
        if direct is not None:
            return direct
        source = normalize_source(source)
        if isinstance(source, CallResult):
            source = normalize_source(source.callee)
        if not isinstance(source, str):
            return None
        chain = self.trace_symbol(module, source, tracers, set())
        cg = getattr(self, "project_cg", None)
        if cg is None:
            return None
        for index in range(len(chain) - 1, 0, -1):
            class_name = chain[index]
            class_module = chain[index - 1]
            if not isinstance(class_name, str):
                continue
            module_cg = cg.modules.get(class_module)
            if module_cg and class_name in module_cg.classes:
                return (class_module, class_name)
        return None

    ## Return whether one project-local class derives from another.
    #
    #  @param candidate_module Defining module of the candidate subclass.
    #  @param candidate_class Candidate subclass name.
    #  @param base_module Defining module of the required base class.
    #  @param base_class Required base class name.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard for cyclic or malformed hierarchies.
    #  @return True for identity or transitive local inheritance.
    def _local_class_is_or_derives(
            self, candidate_module, candidate_class,
            base_module, base_class, tracers, visited=None):
        candidate = (candidate_module, candidate_class)
        required = (base_module, base_class)
        if candidate == required:
            return True
        seen = set(visited or set())
        if candidate in seen:
            return False
        seen.add(candidate)
        tracer = tracers.get(candidate_module)
        if tracer is None:
            return False
        for base_symbol in tracer.class_bases.get(candidate_class, []):
            identity = self._resolve_local_class_identity(
                candidate_module, base_symbol, tracers)
            if identity is None:
                continue
            if self._local_class_is_or_derives(
                    identity[0], identity[1],
                    base_module, base_class, tracers, seen):
                return True
        return False

    ## Collect project-local runtime class candidates for a receiver source.
    #
    #  Explicit constructors and statically tracked container elements provide
    #  class-level dispatch evidence. An empty result means the source cannot
    #  constrain dispatch, not that the receiver is non-local.
    #  @param module Module where the source is evaluated.
    #  @param source Receiver source.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard.
    #  @return List of (defining module, class name) tuples.
    def _local_class_candidates(
            self, module, source, tracers, visited=None):
        source = normalize_source(source)
        key = (module, type(source).__name__, source_display(source))
        seen = set(visited or set())
        if key in seen:
            return []
        seen.add(key)

        if isinstance(source, CallResult):
            method_classes = self._local_class_from_method_result(
                module, source, tracers)
            if method_classes:
                return method_classes
            function_classes = self._local_classes_from_function_result(
                module, source.callee, tracers)
            if function_classes:
                return function_classes
            callable_classes = self._local_callable_class_candidates(
                module, source, tracers.get(module), tracers, seen)
            if callable_classes:
                return callable_classes
            identity = self._local_class_from_source(
                module, source.callee)
            return [identity] if identity is not None else []
        identity = self._resolve_local_class_identity(
            module, source, tracers)
        if identity is not None:
            return [identity]
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._local_class_candidates(
                    module, item, tracers, set(seen)))
            return self._dedupe_list(candidates)
        if isinstance(source, ContainerItem):
            resolved = self._resolve_container_item(
                module, source.container, source.index, tracers)
            if resolved is None:
                return []
            return self._local_class_candidates(
                resolved[0], resolved[1], tracers, seen)
        if isinstance(source, ContainerIter):
            container = normalize_source(source.container)
            if not isinstance(container, str):
                return self._local_class_candidates(
                    module, container, tracers, seen)
            tracer = tracers.get(module)
            if tracer is None:
                return []
            candidates = []
            for (container_name, _), item_source in (
                    tracer.container_items.items()):
                if container_name == container:
                    candidates.extend(self._local_class_candidates(
                        module, item_source, tracers, set(seen)))
            for item_source in tracer.container_set_sources.get(
                    container, set()):
                candidates.extend(self._local_class_candidates(
                    module, item_source, tracers, set(seen)))
            return self._dedupe_list(candidates)
        return []

    ## Resolve a constructor-injected callable field of a parameter object.
    #  @param module Module containing the field call.
    #  @param source Parameter-backed field-call source.
    #  @param tracers All project analyzers.
    #  @param seen Callable-source recursion guard.
    #  @return Complete local callable class candidates, or an empty list.
    def _parameter_callable_field_classes(self, module, source, tracers, seen):
        key = (module, source.parameter_scope, source.parameter_name, source.method)
        if key in self._callable_field_in_progress:
            return []
        tracer = tracers.get(module)
        params = (tracer.function_params.get(source.parameter_scope, [])
                  if tracer is not None else [])
        if source.parameter_name not in params:
            return []
        # A write outside an initializer invalidates constructor-only evidence.
        run = self._ownership_run
        if run.constructor_only_fields is None:
            fields, blocked = set(), set()
            for candidate in tracers.values():
                tree = candidate._module_tree
                if tree is None:
                    continue
                parents = {id(child): node for node in ast.walk(tree)
                           for child in ast.iter_child_nodes(node)}
                for node in ast.walk(tree):
                    if (not isinstance(node, ast.Attribute)
                            or not isinstance(node.ctx, (ast.Store, ast.Del))):
                        continue
                    parent = parents.get(id(node))
                    while parent is not None and not isinstance(
                            parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parent = parents.get(id(parent))
                    fields.add(node.attr)
                    if (not isinstance(node.ctx, ast.Store)
                            or not isinstance(node.value, ast.Name)
                            or node.value.id != 'self'
                            or parent is None or parent.name != '__init__'
                            or not isinstance(parents.get(id(parent)), ast.ClassDef)):
                        blocked.add(node.attr)
            run.constructor_only_fields = fields - blocked
            self._constructor_only_fields = run.constructor_only_fields
        if source.method not in run.constructor_only_fields:
            return []
        self._callable_field_in_progress.add(key)
        try:
            arguments = self._parameter_call_arguments(
                module, source.parameter_scope, source.parameter_name,
                params.index(source.parameter_name), tracer, tracers)
            if self._callable_field_receiver_escapes(module, source, arguments, tracers):
                return []
            classes = []
            for origin, receiver in arguments:
                identity = self._resolve_local_class_identity(origin, receiver, tracers)
                if identity is None or not isinstance(receiver, CallResult):
                    return []
                bindings = self._local_class_attribute_bindings(
                    identity[0], identity[1], 'self.' + source.method, tracers)
                if not bindings:
                    return []
                contexts = self._bounded_call_contexts(
                    origin, receiver.call_lineno, receiver.call_col_offset, tracers,
                    callee_name=receiver.display_name)
                for binding_module, binding in bindings:
                    binding = normalize_source(binding)
                    if isinstance(binding, ParameterSource):
                        matching = [context for context in contexts
                                    if context.target.module == binding_module
                                    and context.target.qualname == binding.scope]
                        if (len(matching) != 1 or binding.derived
                                or binding.attributes
                                or not binding.scope.endswith('.__init__')):
                            return []
                        binding = self._bounded_argument_source(matching[0], binding.name)
                        binding_module = matching[0].caller_module
                    values = (binding.sources if isinstance(binding, SourceSet)
                              else (binding,))
                    for value in values:
                        candidates = self._local_callable_class_candidates(
                            binding_module, value, tracers.get(binding_module), tracers,
                            visited=seen)
                        if not candidates:
                            return []
                        classes.extend(candidates)
            return self._dedupe_list(classes)
        finally:
            self._callable_field_in_progress.remove(key)

    ## Reject object escapes that could overwrite an injected callable field.
    #  @param module Field-call module.
    #  @param source Parameter-backed field-call source.
    #  @param arguments Concrete receiver constructor sources.
    #  @param tracers Project analyzers.
    #  @return True when a receiver is passed elsewhere or aliased ambiguously.
    def _callable_field_receiver_escapes(self, module, source, arguments, tracers):
        names = {(module, source.parameter_scope): {source.parameter_name}}
        identities = []
        for origin, receiver in arguments:
            if not isinstance(receiver, CallResult):
                return True
            identity = self._resolve_local_class_identity(origin, receiver, tracers)
            if identity is None:
                return True
            if not self._constructor_field_method_is_readonly(
                    identity, '__init__', source.method, tracers):
                return True
            identities.append(identity)
            cg = self.project_cg.modules.get(origin)
            for edge in cg.edges if cg is not None else ():
                if (edge.call_lineno == receiver.call_lineno
                        and edge.call_col_offset == receiver.call_col_offset):
                    names.setdefault((origin, edge.caller.qualname), set()).update(
                        edge.assigned_to)

        def carries_name(node, tracked):
            if isinstance(node, ast.Name):
                return node.id in tracked
            if isinstance(node, ast.Attribute):
                return False
            return any(carries_name(child, tracked)
                       for child in ast.iter_child_nodes(node))

        for (origin, scope), tracked in names.items():
            tree = tracers[origin]._module_tree
            calls = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    calls.setdefault((node.lineno, node.col_offset), []).append(node)
            # Alias assignments may hide an escape inside a container argument.
            # Keep this constructor-only path conservative until aliases carry
            # object mutation facts of their own.
            for node in ast.walk(tree):
                if (isinstance(node, (ast.Assign, ast.AnnAssign))
                        and node.value is not None
                        and carries_name(node.value, tracked)
                        and isinstance(node.value, (ast.Name, ast.List, ast.Tuple, ast.Dict))):
                    return True
            for edge in self.project_cg.modules[origin].edges:
                if edge.caller.qualname != scope:
                    continue
                candidates = calls.get((edge.call_lineno, edge.call_col_offset), [])
                if len(candidates) > 1:
                    candidates = [node for node in candidates
                                  if ast.unparse(node.func) == edge.callee_name]
                if len(candidates) != 1:
                    return True
                call = candidates[0]
                receiver = call.func
                attributes = []
                while isinstance(receiver, ast.Attribute):
                    attributes.append(receiver.attr)
                    receiver = receiver.value
                if (isinstance(receiver, ast.Name) and receiver.id in tracked
                        and isinstance(call.func, ast.Attribute)
                        and not (isinstance(call.func.value, ast.Name)
                                 and call.func.attr == source.method)):
                    checked_method = call.func.attr
                    if len(attributes) > 1:
                        if attributes[-1] not in self._constructor_only_fields:
                            return True
                        checked_method = '__init__'
                    if not all(self._constructor_field_method_is_readonly(
                            identity, checked_method, source.method, tracers)
                            for identity in identities):
                        return True
                if not any(carries_name(arg, tracked)
                        for arg in list(call.args) + [kw.value for kw in call.keywords]):
                    continue
                if self._edge_targets_local_function(
                        edge, origin, module, source.parameter_scope,
                        tracers[origin], tracers):
                    continue
                return True
        return False

    ## Check a local method for escapes of its constructor-only field owner.
    #  @param identity Project-local class identity.
    #  @param method Method invoked on the object.
    #  @param field Constructor-injected callable field.
    #  @param tracers Project analyzers.
    #  @param seen Local method recursion guard.
    #  @return True only for inspectable non-escaping instance method bodies.
    def _constructor_field_method_is_readonly(
            self, identity, method, field, tracers, seen=None):
        key = (identity, method)
        seen = set(seen or ())
        if key in seen:
            return False
        seen.add(key)
        tree = tracers[identity[0]]._module_tree
        classes = [node for node in ast.walk(tree)
                   if isinstance(node, ast.ClassDef) and node.name == identity[1]]
        if len(classes) != 1:
            return False
        methods = [node for node in classes[0].body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name in (method, '__init__')]
        method_names = {node.name for node in classes[0].body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if not any(node.name == method for node in methods):
            return False
        for function in methods:
            args = list(function.args.posonlyargs) + list(function.args.args)
            if not args or function.decorator_list:
                return False
            receiver = args[0].arg
            parents = {id(child): node for node in ast.walk(function)
                       for child in ast.iter_child_nodes(node)}
            for node in ast.walk(function):
                if (isinstance(node, ast.Name) and node.id == receiver
                        and isinstance(node.ctx, ast.Load)
                        and not isinstance(parents.get(id(node)), ast.Attribute)):
                    return False
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == receiver and node.attr in method_names):
                    parent = parents.get(id(node))
                    if not (isinstance(parent, ast.Call) and parent.func is node):
                        return False
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == receiver
                        and node.func.attr != field
                        and not (node.func.attr in self._constructor_only_fields
                                 and node.func.attr not in method_names)
                        and not self._constructor_field_method_is_readonly(
                            identity, node.func.attr, field, tracers, seen)):
                    return False
        return True

    ## Resolve local classes represented by callable-object constructor calls.
    #
    #  A call such as ``f(value)`` stores the constructor's defining module in
    #  CallEdge.callee while retaining the imported class spelling in
    #  CallEdge.callee_name.  CallResult sources carry the same spelling in
    #  display_name.  Reconstruct the class only from that existing evidence
    #  and the caller's import bindings.
    #  @param module Module containing the callable-object call.
    #  @param source Callable source or SourceSet of callable sources.
    #  @param tracer Analyzer for the caller module.
    #  @param tracers All project analyzers.
    #  @param visited Recursion guard.
    #  @param display_name Optional call-edge spelling for the source.
    #  @return List of local class identities.
    def _local_callable_class_candidates(
            self, module, source, tracer, tracers, visited=None,
            display_name=None):
        source = normalize_source(source)
        seen = set(visited or set())
        key = (type(source).__name__, source_display(source))
        if key in seen:
            return []
        seen.add(key)

        if (isinstance(source, InstanceMethod) and source.parameter_scope
                and source.receiver == source.parameter_name):
            return self._parameter_callable_field_classes(
                module, source, tracers, seen)

        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._local_callable_class_candidates(
                    module, item, tracer, tracers, set(seen)))
            return self._dedupe_list(candidates)

        direct = self._local_class_from_source(module, source)
        if direct is not None:
            return [direct]
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            call_method = ".__call__"
            if source.callee.endswith(call_method):
                direct = self._local_class_from_source(
                    module, source.callee[:-len(call_method)])
                if direct is not None:
                    return [direct]
        if tracer is None:
            return []

        display = display_name
        if display is None and isinstance(source, CallResult):
            display = source.display_name
        if (not display
                and isinstance(source, CallResult)
                and isinstance(source.callee, str)):
            for imported in getattr(
                    tracer, "import_from_symbols", {}).values():
                if (isinstance(imported, str)
                        and (imported == source.callee
                             or imported.startswith(source.callee + "."))):
                    identity = self._local_class_from_source(
                        module, imported)
                    if identity is not None:
                        return [identity]
        if not isinstance(display, str) or not display:
            return []
        if "." in display:
            alias, class_name = display.rsplit(".", 1)
            bound_module = tracer.import_from_symbols.get(alias)
            if bound_module is None:
                bound_module = tracer.symbols.direct.get(alias)
        else:
            class_name = display
            bound_module = tracer.import_from_symbols.get(display)
            if bound_module is None:
                bound_module = tracer.symbols.direct.get(display)
        bound_module = normalize_source(bound_module)
        if isinstance(bound_module, CallResult):
            bound_module = bound_module.callee
        if isinstance(bound_module, str):
            imported_symbol = tracer.import_from_symbols.get(bound_module)
            if imported_symbol is not None:
                bound_module = imported_symbol
            if bound_module.endswith(".__call__"):
                bound_module = bound_module[:-len(".__call__")]
        if not isinstance(bound_module, str):
            return []
        candidate_source = (
            bound_module if "." not in display
            else bound_module + "." + class_name)
        identity = self._local_class_from_source(module, candidate_source)
        return [identity] if identity is not None else []

    ## Return whether an edge receiver may have one required local class.
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the edge.
    #  @param required Pair of required (module, class).
    #  @param tracers Dict of module name to analyzer.
    #  @return False only when concrete local class evidence excludes it.
    def _edge_receiver_may_have_class(
            self, edge, caller_module, required, tracers):
        candidates = self._local_class_candidates(
            caller_module, edge.receiver_source, tracers)
        if not candidates:
            return True
        return any(
            self._local_class_is_or_derives(
                candidate[0], candidate[1],
                required[0], required[1], tracers)
            for candidate in candidates
        )

## Analyze a project directory or one Python source file and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Path to the project directory or a .py/.pyi file.
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root):
    analyzer = ProjectAnalyzer(project_root)
    return analyzer.analyze()
