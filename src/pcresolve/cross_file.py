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
from .project_local_classes import ProjectLocalClassesMixin
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
                      ProjectLocalClassesMixin, ProjectMethodOwnershipMixin,
                      ProjectResultBindingMixin, ProjectSourceTracingMixin):
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

## Analyze a project directory or one Python source file and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Path to the project directory or a .py/.pyi file.
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root):
    analyzer = ProjectAnalyzer(project_root)
    return analyzer.analyze()
