## @package pcresolve.ownership.analyzer
#  Orchestrate project ownership analysis.
#
#
#  Provide cross-file project-level API call chain analysis.
#  提供跨文件的项目级 API 调用链分析。
#
#  The ProjectAnalyzer class orchestrates scanning a project, parsing every
#  .py file, building per-file symbol tables, resolving symbols across files,
#  and collecting all API calls with their top-level library origins.



import os
from pcresolve.runtime.limits import AnalysisBudget
from pcresolve.ownership.source_fact_cache import (
    SourceFactCacheEntry, capture_source_facts, clone_source_facts, find_source_fact_entry,
)
from pcresolve.frontend.module_mapper import ModuleMapper
from pcresolve.ownership.resolve.call_result_resolution import CallResultResolutionMixin
from pcresolve.ownership.resolve.instance_method_resolution import InstanceMethodResolutionMixin
from pcresolve.ownership.resolve.container_resolution import ContainerResolutionMixin
from pcresolve.ownership.resolve.project_call_classification import ProjectCallClassificationMixin
from pcresolve.ownership.resolve.project_call_context import ProjectCallContextMixin
from pcresolve.ownership.resolve.project_local_classes import ProjectLocalClassesMixin
from pcresolve.ownership.resolve.project_method_ownership import ProjectMethodOwnershipMixin
from pcresolve.ownership.resolve.project_result_binding import ProjectResultBindingMixin
from pcresolve.ownership.resolve.project_source_tracing import ProjectSourceTracingMixin
from pcresolve.ownership.diagnostics import Diagnostic, FILE_READ_ERROR, SYNTAX_ERROR, ENCODING_ERROR
from pcresolve.ownership.ir import SymbolProvenance
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer
from pcresolve.ownership.sources import (
    CallResult, ParameterSource, SourceSet, normalize_source, source_display,
)
from pcresolve.frontend.source_snapshot import SourceStore, OWNERSHIP_SOURCE
from pcresolve.ownership.ownership_model import OwnershipProofBudget, OwnershipRun, ProjectSnapshot
from pcresolve.ownership.classification import ClassificationPipeline
from pcresolve.ownership.decorator_provenance import build_decorator_index, lookup_decorated_by
from pcresolve.ownership.library_usage import build_library_usage
from pcresolve.ownership.source_resolution import SourceSetResolver
from pcresolve.ownership.types import ProjectAnalysis, FileAnalysis, ApiCall


## Remove consecutive duplicate items from a list while preserving order.
## 保留顺序并移除列表中的连续重复项。
#
#  @param chain Input list.
#  @return List with no consecutive duplicates.
def _dedup_consecutive(chain):
    result = []
    for item in chain:
        if not result or item != result[-1]:
            result.append(item)
    return result


## Check whether a symbol is an imported external origin in this tracer.
## 检查符号是否具有当前分析器中的外部导入来源证据。
#
#  @param tracer Single-file analyzer.
#  @param symbol Candidate external origin.
#  @return True if symbol matches an import source or its top-level package.
def _is_import_origin(tracer, symbol):
    if tracer is None or not isinstance(symbol, str):
        return False
    if not getattr(tracer, '_ownership_import_unstable', False):
        direct = tracer.symbols.direct
        refs = getattr(tracer, 'symbol_refs', ())
        generation = (direct.version, tracer.version)
        cached = getattr(tracer, '_import_origin_index', None)
        if (cached is None or cached[0] is not direct or cached[1] is not refs
                or cached[2] != generation):
            values = set()
            for value in direct.values():
                sources = value.sources if isinstance(value, SourceSet) else (value,)
                values.update(item for item in sources if isinstance(item, str))
            for ref in refs:
                if ref.kind == 'import':
                    value = normalize_source(ref.source)
                    if isinstance(value, str):
                        values.add(value)
            prefixes = set(values)
            for value in values:
                prefixes.update(value[:i] for i, char in enumerate(value) if char == '.')
            cached = tracer._import_origin_index = direct, refs, generation, values, prefixes
        _, _, _, values, prefixes = cached
        return (symbol in prefixes or any(symbol[:i] in values
                for i, char in enumerate(symbol) if char == '.'))
    ## Compare one known import source with the candidate origin spelling.
    ## 将已知导入来源与候选归属拼写进行比较。
    #
    #  @param value Known imported source spelling.
    #  @return True when either spelling is a dotted prefix of the other.
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
## 根据 get_calls() 记录字典构造 ApiCall。
#
#  @param c Call record dict.
#  @param deco_by Decorator evidence index.
#  @return ApiCall object.
def _make_api_call(c, deco_by):
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
## 跨文件项目分析器，负责追踪所有 API 调用的来源。
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
    ## 为项目目录或单个 Python 源文件初始化分析器。
    #
    #  @param project_root Path to the project directory or a .py/.pyi file.
    #  @param analysis_limits Optional cooperative whole-analysis limits.
    #  @param reuse_source_facts Opt-in pristine per-file visitor fact cache.
    #  @return None; project state and the cross-file resolution pipeline are initialized.
    def __init__(self, project_root, analysis_limits=None, reuse_source_facts=False):
        self.reuse_source_facts = reuse_source_facts
        self._source_fact_cache = {}
        self.analysis_limits = analysis_limits
        self.module_mapper = ModuleMapper(project_root)
        self.project_root = (self.module_mapper.project_root
                             if os.path.isfile(project_root) else project_root)
        self._source_store = SourceStore()
        self._ownership_run = None
        self._initial_method_result_index = None
        self.global_symbols = {}
        self.symbol_chains = {}
        self.all_calls = {}
        self._python_shape_in_progress = set()
        self._callable_field_in_progress = set()
        self._edge_target_in_progress = set()
        self._ownership_proof_budget = OwnershipProofBudget()
        self._initial_constructor_only_fields = None
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

    ## Return constructor-only field names for the active run.
    ## 返回当前运行使用的仅构造函数字段名。
    #
    #  @return Field-name set of the run, or the pre-run compatibility value.
    @property
    def _constructor_only_fields(self):
        # Compatibility view of the active run's lazy constructor evidence.
        if self._ownership_run is None:
            return self._initial_constructor_only_fields
        return self._ownership_run.constructor_only_fields

    ## Replace constructor-only field names for the active run.
    ## 替换当前运行使用的仅构造函数字段名。
    #
    #  @param value New constructor-only field-name set.
    #  @return None
    @_constructor_only_fields.setter
    def _constructor_only_fields(self, value):
        if self._ownership_run is None:
            self._initial_constructor_only_fields = value
        else:
            self._ownership_run.constructor_only_fields = value

    ## Return the cross-file symbol table of the active run.
    ## 返回当前运行使用的跨文件符号表。
    #
    #  @return Global symbol table of the active run, or the pre-run value.
    @property
    def global_symbols(self):
        if self._ownership_run is None:
            return self._initial_global_symbols
        return self._ownership_run.global_symbols

    ## Replace the cross-file symbol table of the active run.
    ## 替换当前运行使用的跨文件符号表。
    #
    #  @param value New symbol table keyed by module name.
    #  @return None
    @global_symbols.setter
    def global_symbols(self, value):
        if self._ownership_run is None:
            self._initial_global_symbols = value
        else:
            self._ownership_run.global_symbols = value

    ## Return symbol explanation chains of the active run.
    ## 返回当前运行使用的符号解释链。
    #
    #  @return Explanation chains keyed by module, or the pre-run value.
    @property
    def symbol_chains(self):
        if self._ownership_run is None:
            return self._initial_symbol_chains
        return self._ownership_run.symbol_chains

    ## Replace symbol explanation chains of the active run.
    ## 替换当前运行使用的符号解释链。
    #
    #  @param value New explanation chains keyed by module name.
    #  @return None
    @symbol_chains.setter
    def symbol_chains(self, value):
        if self._ownership_run is None:
            self._initial_symbol_chains = value
        else:
            self._ownership_run.symbol_chains = value

    ## Return classified call records of the active run.
    ## 返回当前运行使用的已分类调用记录。
    #
    #  @return Call records grouped by module, or the pre-run value.
    @property
    def all_calls(self):
        if self._ownership_run is None:
            return self._initial_all_calls
        return self._ownership_run.all_calls

    ## Replace classified call records of the active run.
    ## 替换当前运行使用的已分类调用记录。
    #
    #  @param value New call records grouped by module name.
    #  @return None
    @all_calls.setter
    def all_calls(self, value):
        if self._ownership_run is None:
            self._initial_all_calls = value
        else:
            self._ownership_run.all_calls = value

    ## Return the project call graph of the active run.
    ## 返回当前运行使用的项目调用图。
    #
    #  @return Project call graph of the active run, or the pre-run value.
    @property
    def project_cg(self):
        if self._ownership_run is None:
            return self._initial_project_cg
        return self._ownership_run.program.call_graph

    ## Replace the project call graph of the active run.
    ## 替换当前运行使用的项目调用图。
    #
    #  @param value New project call graph.
    #  @return None
    @project_cg.setter
    def project_cg(self, value):
        if self._ownership_run is None:
            self._initial_project_cg = value
        else:
            self._ownership_run.program.call_graph = value

    ## Return the read-only source snapshot captured by the active run.
    ## 返回当前运行捕获的只读源码快照。
    #
    #  Reading it before analysis starts raises AttributeError.
    #
    #  @return SourceSnapshot holding the run's parsed source documents.
    @property
    def _source_snapshot(self):
        if self._ownership_run is None:
            raise AttributeError('source snapshot is not available before analysis')
        return self._ownership_run.snapshot.sources

    ## Return active Python-shape queries of the active run.
    ## 返回当前运行中活跃的 Python 形状查询。
    #
    #  @return Query keys used to stop recursive shape resolution, or the pre-run value.
    @property
    def _python_shape_in_progress(self):
        if self._ownership_run is None:
            return self._initial_python_shape_in_progress
        return self._ownership_run.python_shape_in_progress

    ## Replace active Python-shape queries of the active run.
    ## 替换当前运行中活跃的 Python 形状查询。
    #
    #  @param value New set of active shape query keys.
    #  @return None
    @_python_shape_in_progress.setter
    def _python_shape_in_progress(self, value):
        if self._ownership_run is None:
            self._initial_python_shape_in_progress = value
        else:
            self._ownership_run.python_shape_in_progress = value

    ## Return active callable-field queries of the active run.
    ## 返回当前运行中活跃的可调用字段查询。
    #
    #  @return Query keys used to stop recursive field resolution, or the pre-run value.
    @property
    def _callable_field_in_progress(self):
        if self._ownership_run is None:
            return self._initial_callable_field_in_progress
        return self._ownership_run.callable_field_in_progress

    ## Replace active callable-field queries of the active run.
    ## 替换当前运行中活跃的可调用字段查询。
    #
    #  @param value New set of active callable-field query keys.
    #  @return None
    @_callable_field_in_progress.setter
    def _callable_field_in_progress(self, value):
        if self._ownership_run is None:
            self._initial_callable_field_in_progress = value
        else:
            self._ownership_run.callable_field_in_progress = value

    ## Return active call-edge target queries of the active run.
    ## 返回当前运行中活跃的调用边目标查询。
    #
    #  @return Query keys used to stop recursive target resolution, or the pre-run value.
    @property
    def _edge_target_in_progress(self):
        if self._ownership_run is None:
            return self._initial_edge_target_in_progress
        return self._ownership_run.edge_target_in_progress

    ## Replace active call-edge target queries of the active run.
    ## 替换当前运行中活跃的调用边目标查询。
    #
    #  @param value New set of active edge-target query keys.
    #  @return None
    @_edge_target_in_progress.setter
    def _edge_target_in_progress(self, value):
        if self._ownership_run is None:
            self._initial_edge_target_in_progress = value
        else:
            self._ownership_run.edge_target_in_progress = value

    ## Return the proof budget of the active run.
    ## 返回当前运行使用的证明预算。
    #
    #  @return Proof budget of the active run, or the pre-run budget.
    @property
    def _ownership_proof_budget(self):
        if self._ownership_run is None:
            return self._initial_ownership_proof_budget
        return self._ownership_run.proof_budget

    ## Replace the proof budget of the active run.
    ## 替换当前运行使用的证明预算。
    #
    #  @param value New proof budget shared by nested ownership queries.
    #  @return None
    @_ownership_proof_budget.setter
    def _ownership_proof_budget(self, value):
        if self._ownership_run is None:
            self._initial_ownership_proof_budget = value
        else:
            self._ownership_run.proof_budget = value

    ## Return the cooperative analysis budget of the active run.
    ## 返回当前运行使用的协作式分析预算。
    #
    #  @return Analysis budget of the run, or None when no budget is active.
    @property
    def _analysis_budget(self):
        # Compatibility view of the active run's cooperative analysis budget.
        if self._ownership_run is None:
            return None
        return self._ownership_run.analysis_budget

    ## Drop pre-run compatibility aliases once a new analysis run starts.
    ## 在新的分析运行开始后清除运行前的兼容别名。
    #
    #  @return None
    def _clear_pre_run_compat_state(self):
        # Pre-run aliases support direct resolver use, but are not inputs to a run.
        for name in (
                '_initial_global_symbols', '_initial_symbol_chains', '_initial_all_calls',
                '_initial_project_cg', '_initial_constructor_only_fields',
                '_initial_python_shape_in_progress', '_initial_callable_field_in_progress',
                '_initial_edge_target_in_progress', '_initial_ownership_proof_budget',
                '_initial_definition_index', '_initial_edge_index', '_initial_callable_index'):
            self.__dict__.pop(name, None)
        # Kept as None for compatibility with existing internal inspection.
        self._initial_method_result_index = None

    ## Check whether a symbol has import-backed ownership evidence.
    ## 检查符号是否有导入支撑的归属证据。
    #
    #  @param tracer Single-file analyzer containing import facts.
    #  @param symbol Candidate symbol or top-level library name.
    #  @return True when the symbol matches an import origin.
    def _has_import_origin(self, tracer, symbol):
        return _is_import_origin(tracer, symbol)

    ## Run the full analysis: scan, parse, resolve, and collect.
    ## 执行完整分析流程：扫描、解析、解析跨文件符号并收集结果。
    #
    #  @return ProjectAnalysis with all results.
    def analyze(self):
        budget = (AnalysisBudget(self.analysis_limits)
                  if self.analysis_limits is not None else None)
        if budget is not None:
            budget.checkpoint(force=True)

        # Capture the file set once so every subsequent phase sees one project snapshot.
        # 一次性固定文件集合，使后续所有阶段都使用同一个项目快照。
        self.module_mapper.scan_project()
        all_modules = tuple(self.module_mapper.get_all_modules())
        paths = [self.module_mapper.get_file_path(module) for module in all_modules]
        source_paths = [path for path in paths if path and os.path.exists(path)]
        sources = (self._source_store.snapshot(source_paths, OWNERSHIP_SOURCE, budget=budget)
                   if budget is not None else self._source_store.snapshot(source_paths, OWNERSHIP_SOURCE))
        run = OwnershipRun(ProjectSnapshot(all_modules, sources), analysis_budget=budget)
        run.ast_facts.budget = budget
        self._ownership_run = run
        self._clear_pre_run_compat_state()

        # Resolver properties forward to this run so existing internal call
        # sites share the same per-run storage rather than keeping duplicates.
        module_tracers = run.program.module_tracers
        diagnostics = run.diagnostics

        next_source_facts = {}
        for module in all_modules:
            if budget is not None:
                budget.checkpoint(force=True)
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
            package = self.module_mapper.is_package(module)

            # Reuse detached visitor facts only when both snapshot identity and module context match.
            # 仅当快照对象和模块上下文均匹配时，才复用分离保存的访问器事实。
            cached = (find_source_fact_entry(self._source_fact_cache, file_path,
                                             document, module, package)
                      if self.reuse_source_facts else None)
            if cached is not None:
                tracer = clone_source_facts(cached.facts, document, budget)
                run.source_facts_reused += 1
                next_source_facts[file_path] = cached
            else:
                tracer = SingleFileAnalyzer(module_name=module, is_package=package,
                    file_path=file_path, analysis_budget=budget)
                tracer.visit(document.tree)
                if self.reuse_source_facts:
                    pristine = capture_source_facts(tracer, document, budget)
                    next_source_facts[file_path] = SourceFactCacheEntry(
                        document, module, package, pristine)
            run.program.add_module(module, tracer)

        # Temporarily guard imports while bounded local call results are propagated.
        # 传播有界本地调用结果时，暂时启用导入稳定性保护。
        for tracer in module_tracers.values():
            tracer._ownership_import_unstable = True
        try:
            self._bind_bounded_local_call_results(module_tracers)
            self._bind_bounded_callback_map_results(module_tracers)
            self._bind_bounded_local_iteration_results(module_tracers)
            self._bind_proven_result_method_results(module_tracers)
        finally:
            for tracer in module_tracers.values():
                tracer._ownership_import_unstable = False
        self.resolve_cross_file_symbols(module_tracers)
        self.get_calls(module_tracers)

        # Construct provenance before decorator and library-usage views consume it.
        # 先构造来源链，再供装饰器和库使用视图消费。
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
        if budget is not None:
            budget.checkpoint(force=True)

        result = ProjectAnalysis(
            project_root=self.project_root,
            files=files,
            all_api_calls=all_api_calls,
            diagnostics=diagnostics,
            stats=stats,
            all_symbol_provenance=all_provenance,
            library_usage=library_usage,
        )
        # Publish only after the full analysis succeeds.  A failed run keeps
        # the previous pristine cache, which is still guarded by source identity.
        self._source_fact_cache = next_source_facts
        return result

    # ── provenance helpers ───────────────────────────────────────────────

    ## Check whether a top name is backed by any import evidence across tracers.
    ## 检查顶层名称是否在任一分析器中有导入证据。
    ## Check the provenance fallback's top-level owner against all module imports.
    ## 对所有模块的导入证据检查来源回退使用的顶层所有者。
    #
    #  @param name Candidate top-level owner spelling.
    #  @param tracers Per-module analyzers with import and alias facts.
    #  @return True when import evidence supports the candidate owner.
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
    ## 构造逐文件分析结果。
    #
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param all_provenance List of SymbolProvenance records.
    #  @param deco_by Decorator evidence index.
    #  @return List of FileAnalysis records.
    def _build_file_analysis(self, module_tracers, all_provenance, deco_by):
        files = []
        by_file = {}
        for provenance in all_provenance:
            by_file.setdefault(provenance.file_path, []).append(provenance)
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            files.append(FileAnalysis(
                file_path=file_path,
                module_name=module,
                symbols=self.global_symbols.get(module, {}),
                chains=self.symbol_chains.get(module, {}),
                symbol_provenance=list(by_file.get(file_path, ())),
                api_calls=[_make_api_call(c, deco_by)
                           for c in self.all_calls.get(module, [])],
            ))
        return files

    ## Build the flat project-level API call list.
    ## 构造扁平的项目级 API 调用列表。
    #
    #  @param deco_by Decorator evidence index.
    #  @return List of ApiCall records.
    def _build_all_api_calls(self, deco_by):
        return [_make_api_call(c, deco_by)
                for module, calls in self.all_calls.items()
                for c in calls]

    ## Build a decorator evidence index from provenance records.
    ## 根据来源记录构造装饰器证据索引。
    #
    #  @param all_provenance List of SymbolProvenance records.
    #  @return Dict keyed by (file_path, scope, symbol) → [library, ...].
    def _build_decorator_index(self, all_provenance):
        return build_decorator_index(all_provenance)

    ## Build SymbolProvenance records from each tracer's symbol_refs.
    ## 根据各分析器的 symbol_refs 构造 SymbolProvenance 记录。
    #
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of SymbolProvenance records.
    def _build_symbol_provenance(self, module_tracers):
        result = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            for ref in tracer.symbol_refs:
                if self._analysis_budget is not None:
                    self._analysis_budget.checkpoint()
                direct_source = ref.source
                if ref.kind == "parameter" and ref.scope_name:
                    direct_source = ParameterSource(
                        ref.scope_name, ref.symbol)
                try:
                    chain = self.trace_symbol(module, ref.symbol, module_tracers,
                                               set(),
                                               _direct_source=direct_source)
                except RecursionError:
                    # Preserve the direct source when recursive provenance exceeds Python's stack.
                    # 递归来源追踪耗尽 Python 调用栈时，保留直接来源作为保守结果。
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
    ## 根据调用和来源记录构造库使用索引。
    #
    #  Delegates to library_usage.build_library_usage() (Phase 9-lite PR1).
    #
    #  @param all_api_calls List of ApiCall records.
    #  @param all_provenance List of SymbolProvenance records.
    #  @return Dict of library_name -> LibraryUsage.
    def _build_library_usage(self, all_api_calls, all_provenance):
        return build_library_usage(
            self.project_root, all_api_calls, all_provenance)

    ## Check whether a module name belongs to the current project.
    ## 检查模块名是否属于当前项目。
    #
    #  @param module_name Dotted module name.
    #  @return True if the module is a local project module.
    def is_local(self, module_name):
        return isinstance(module_name, str) and module_name in self.module_mapper.module_to_file

## Analyze a project directory or one Python source file and return structured results.
## 分析项目目录或单个 Python 源文件，并返回结构化结果。
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#
#  @param project_root Path to the project directory or a .py/.pyi file.
#  @param analysis_limits Optional cooperative resource limits.
#  @param reuse_source_facts Opt-in detached per-file facts for repeated analysis.
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root, analysis_limits=None, reuse_source_facts=False):
    analyzer = ProjectAnalyzer(project_root, analysis_limits=analysis_limits,
                               reuse_source_facts=reuse_source_facts)
    return analyzer.analyze()
