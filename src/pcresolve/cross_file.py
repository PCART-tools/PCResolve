## @package pcresolve.cross_file
#  Provide cross-file project-level API call chain analysis.
#
#  The ProjectAnalyzer class orchestrates scanning a project, parsing every
#  .py file, building per-file symbol tables, resolving symbols across files,
#  and collecting all API calls with their top-level library origins.

import ast
import os
import builtins
from .module_mapper import ModuleMapper

## Python 2 builtins not present in Python 3's builtins module.
_PY2_BUILTINS = frozenset({
    "apply", "basestring", "buffer", "cmp", "coerce", "execfile",
    "file", "intern", "long", "raw_input", "reduce", "reload",
    "StandardError", "unichr", "unicode", "xrange",
})


## Check if a name is a Python builtin (including Python 2 builtins).
def _is_builtin(name):
    return isinstance(name, str) and (hasattr(builtins, name) or name in _PY2_BUILTINS)
from .diagnostics import Diagnostic, FILE_READ_ERROR, SYNTAX_ERROR, ENCODING_ERROR
from .ir import (SymbolProvenance, REASON_DIRECT_IMPORT, REASON_TRANSITIVE_IMPORT,
                    REASON_LOCAL_DEFINITION, REASON_BUILTIN,
                    REASON_PARAMETER_PROPAGATION, REASON_RETURN_PROPAGATION,
                    REASON_FLOW_MERGE, REASON_UNRESOLVED)
from .single_file import SingleFileAnalyzer
from .sources import (ContainerItem, ContainerIter, InstanceMethod, CallResult,
                       SourceSet, is_structured_source, normalize_source,
                       source_display)
from .types import ProjectAnalysis, FileAnalysis, ApiCall, LibraryUsage


## Remove consecutive duplicate items from a list while preserving order.
#  @param chain Input list.
#  @return List with no consecutive duplicates.
def _dedup_consecutive(chain):
    result = []
    for item in chain:
        if not result or item != result[-1]:
            result.append(item)
    return result


## Check whether a library name string is suitable for library_usage.
#  @param name Candidate library name.
#  @return True if not a dataclass repr or structured source display.
def _is_legal_library_name(name):
    if not isinstance(name, str):
        return False
    if name.startswith("InstanceMethod("):
        return False
    if name.startswith("ContainerItem("):
        return False
    if name.startswith("ContainerIter("):
        return False
    if name.startswith("CallResult("):
        return False
    if name.startswith("UnknownSource("):
        return False
    return True


## Check whether a symbol is an imported external origin in this tracer.
#  @param tracer Single-file analyzer.
#  @param symbol Candidate external origin.
#  @return True if symbol matches an import source or its top-level package.
def _is_import_origin(tracer, symbol):
    if tracer is None or not isinstance(symbol, str):
        return False
    for value in tracer.symbols.direct.values():
        if isinstance(value, SourceSet):
            for src in value.sources:
                if isinstance(src, str) and (src == symbol or src.startswith(symbol + ".")):
                    return True
        elif isinstance(value, str):
            if value == symbol or value.startswith(symbol + "."):
                return True
    return False


## Normalize a file path to a relative POSIX path for library usage reporting.
#  @param file_path Absolute file path.
#  @param project_root Root directory to make relative.
#  @return Relative POSIX path, or empty string.
def _normalize_path_for_usage(file_path, project_root):
    if not file_path:
        return ""
    try:
        rel = os.path.relpath(file_path, project_root)
    except ValueError:
        rel = file_path
    result = rel.replace(os.sep, "/")
    if os.altsep:
        result = result.replace(os.altsep, "/")
    return result


## Cross-file project analyzer that traces all API calls to their origins.
#
#  Steps:
#  1. Scan the project for all .py/.pyi files and map them to module names.
#  2. Parse each file and run SingleFileAnalyzer to build per-file symbol data.
#  3. Resolve cross-file symbol references across the project.
#  4. Classify every API call with its top-level library source.
class ProjectAnalyzer:
    ## Initialize the analyzer for a given project root.
    #  @param project_root Absolute path to the project root directory.
    #  @param scope_model "v1" (legacy) or "v2" (lexical scopes).
    def __init__(self, project_root, scope_model="v1"):
        self.project_root = project_root
        self.scope_model = scope_model
        self.module_mapper = ModuleMapper(project_root)
        self.global_symbols = {}
        self.symbol_chains = {}
        self.all_calls = {}

    ## Run the full analysis: scan, parse, resolve, and collect.
    #  @return ProjectAnalysis with all results.
    def analyze(self):
        self.module_mapper.scan_project()
        all_modules = self.module_mapper.get_all_modules()
        module_tracers = {}
        diagnostics = []

        for module in all_modules:
            file_path = self.module_mapper.get_file_path(module)
            if not file_path or not os.path.exists(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except UnicodeDecodeError as e:
                diagnostics.append(Diagnostic(
                    code=ENCODING_ERROR,
                    message="Cannot decode file: %s" % e,
                    severity="error",
                    file_path=file_path,
                    module_name=module,
                ))
                continue
            except OSError as e:
                diagnostics.append(Diagnostic(
                    code=FILE_READ_ERROR,
                    message="Cannot read file: %s" % e,
                    severity="error",
                    file_path=file_path,
                    module_name=module,
                ))
                continue
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
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
                scope_model=self.scope_model,
                file_path=file_path,
            )
            tracer.visit(tree)
            module_tracers[module] = tracer

        self.resolve_cross_file_symbols(module_tracers)
        self.get_calls(module_tracers)

        all_provenance = self._build_symbol_provenance(module_tracers)

        files = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            files.append(FileAnalysis(
                file_path=file_path,
                module_name=module,
                symbols=self.global_symbols.get(module, {}),
                chains=self.symbol_chains.get(module, {}),
                symbol_provenance=[p for p in all_provenance if p.file_path == file_path],
                api_calls=[
                    ApiCall(
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
                    )
                    for c in self.all_calls.get(module, [])
                ],
            ))

        all_api_calls = []
        for module, calls in self.all_calls.items():
            for c in calls:
                all_api_calls.append(ApiCall(
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
                ))

        library_usage = self._build_library_usage(all_api_calls, all_provenance)

        stats = {
            "total_modules": len(all_modules),
            "parsed_modules": len(module_tracers),
            "skipped_modules": len(diagnostics),
            "scope_model": self.scope_model,
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

    ## Build SymbolProvenance records from each tracer's symbol_refs.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of SymbolProvenance records.
    def _build_symbol_provenance(self, module_tracers):
        result = []
        for module, tracer in module_tracers.items():
            file_path = self.module_mapper.get_file_path(module)
            for ref in tracer.symbol_refs:
                try:
                    chain = self.trace_symbol(module, ref.symbol, module_tracers,
                                               set(), _direct_source=ref.source)
                except RecursionError:
                    chain = [source_display(ref.source)]
                chain = _dedup_consecutive(chain)
                top = self.extract_final_source(chain) if chain else ""
                tops = [top] if top else []
                reason, confidence, alts = self._classify_symbol_reason(
                    ref, top, tracer, module, module_tracers)
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
                    reason=reason,
                    confidence=confidence,
                    alternatives=alts,
                )
                result.append(prov)
        return result

    ## Build a library usage index from calls and provenance.
    #  @param all_api_calls List of ApiCall records.
    #  @param all_provenance List of SymbolProvenance records.
    #  @return Dict of library_name -> LibraryUsage.
    def _build_library_usage(self, all_api_calls, all_provenance):
        usage = {}
        root = self.project_root
        for call in all_api_calls:
            top = call.top_library
            if top in ("local", "python", "unknown", ""):
                continue
            if not _is_legal_library_name(top):
                continue
            if top not in usage:
                usage[top] = LibraryUsage(library=top)
            u = usage[top]
            u.api_call_count += 1
            u.has_evidence = True
            conf = getattr(call, 'confidence', 1.0) or 1.0
            u.min_confidence = min(u.min_confidence or 1.0, conf)
            u.max_confidence = max(u.max_confidence, conf)
            fp = _normalize_path_for_usage(call.file_path, root)
            if fp and fp not in u.files:
                u.files.append(fp)

        for prov in all_provenance:
            top = prov.top_library
            if top in ("local", "python", "unknown", ""):
                continue
            if not _is_legal_library_name(top):
                continue
            if top not in usage:
                usage[top] = LibraryUsage(library=top)
            u = usage[top]
            u.symbol_count += 1
            u.has_evidence = True
            conf = getattr(prov, 'confidence', 1.0) or 1.0
            u.min_confidence = min(u.min_confidence or 1.0, conf)
            u.max_confidence = max(u.max_confidence, conf)
            if prov.kind == "import":
                if prov.symbol not in u.imports:
                    u.imports.append(prov.symbol)
            kind = prov.kind if prov.kind else "unknown"
            u.kind_counts[kind] = u.kind_counts.get(kind, 0) + 1
            fp = _normalize_path_for_usage(prov.file_path, root)
            if fp and fp not in u.files:
                u.files.append(fp)

        for u in usage.values():
            u.files.sort()
            u.imports.sort()
        return {k: u for k, u in sorted(usage.items())}

    ## Check whether a module name belongs to the current project.
    #  @param module_name Dotted module name.
    #  @return True if the module is a local project module.
    def is_local(self, module_name):
        return module_name in self.module_mapper.get_all_modules()

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
                if call_detail.get('top') == 'local':
                    if isinstance(base, str) or is_structured_source(base):
                        top_source = self._base_top_source(module, base, tracer, module_tracers)
                        if top_source and top_source != 'local':
                            record = dict(call_detail)
                            record['top'] = top_source
                            record['reason'] = self._classify_reason(base, top_source, tracer)
                            record['alternatives'] = self._extract_alternatives(
                                base, module, module_tracers)
                            record['confidence'] = self._classify_confidence(
                                record['reason'], record['alternatives'])
                            self.all_calls[module].append(record)
                            continue
                    record = dict(call_detail)
                    record['top'] = 'local'
                    record['reason'] = REASON_LOCAL_DEFINITION
                    record['confidence'] = 1.0
                    record['alternatives'] = []
                    self.all_calls[module].append(record)
                    continue
                top_source = self._base_top_source(module, base, tracer, module_tracers)
                record = dict(call_detail)
                record['top'] = top_source
                record['reason'] = self._classify_reason(base, top_source, tracer)
                record['alternatives'] = self._extract_alternatives(
                    base, module, module_tracers)
                record['confidence'] = self._classify_confidence(
                    record['reason'], record['alternatives'])
                self.all_calls[module].append(record)

        for module, tracer in module_tracers.items():
            for c in self.all_calls.get(module, []):
                c['resolved_func'] = self._resolve_func_name(c, module, tracer)

        self._call_searched_global = None

    ## Resolve the top-level source of a base symbol, preferring call_assign_funcs.
    #  @param module The current module.
    #  @param base The base symbol string.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name.
    def _base_top_source(self, module, base, tracer, module_tracers):
        if is_structured_source(base):
            structured = self._resolve_structured_source(module, base, module_tracers)
            if structured is not None:
                _, src_module, src_symbol = structured
                return self._top_source(src_module, src_symbol, module_tracers)
            return str(base)
        if isinstance(base, str) and '.' in base:
            prefix = base.split('.')[0]
            if prefix in self.global_symbols.get(module, {}):
                return self.global_symbols[module][prefix]
            return self._top_source(module, base, module_tracers)
        # Simple string base: check call_assign_funcs first to avoid cross-scope pollution
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

    ## Determine the classification reason for a resolved API call.
    #  @param base The call's base symbol or source.
    #  @param top The resolved top-level library.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @return Reason constant string.
    def _classify_reason(self, base, top, tracer):
        if top == "local":
            return REASON_LOCAL_DEFINITION
        if top == "python":
            return REASON_BUILTIN
        if top == "unknown" or not top:
            return REASON_UNRESOLVED
        base_norm = normalize_source(base)
        if isinstance(base_norm, SourceSet):
            return REASON_FLOW_MERGE
        if isinstance(base_norm, CallResult):
            return REASON_RETURN_PROPAGATION
        if isinstance(base, str):
            if base in getattr(tracer, 'import_from_symbols', {}):
                return REASON_DIRECT_IMPORT
            sd = tracer.symbols.direct.get(base)
            if isinstance(sd, str) and sd not in ("local", "python"):
                return REASON_DIRECT_IMPORT
        return REASON_TRANSITIVE_IMPORT

    ## Determine confidence for a classification result.
    #  @param reason Classification reason.
    #  @param alternatives List of alternative top libraries.
    #  @return Confidence score (0.0-1.0).
    def _classify_confidence(self, reason, alternatives=None):
        if reason == REASON_UNRESOLVED:
            return 0.0
        if reason in (REASON_DIRECT_IMPORT, REASON_LOCAL_DEFINITION, REASON_BUILTIN):
            return 1.0
        if reason in (REASON_PARAMETER_PROPAGATION, REASON_RETURN_PROPAGATION):
            return 0.9
        if reason == REASON_FLOW_MERGE:
            alt_count = len(alternatives) if alternatives else 0
            if alt_count > 1:
                return max(1.0 / alt_count, 0.2)
            return 0.85
        return 0.9

    ## Extract alternatives from a SourceSet base.
    #  @param base The call's base.
    #  @param module Current module name.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of alternative top library strings.
    def _extract_alternatives(self, base, module, tracers):
        base_norm = normalize_source(base)
        if not isinstance(base_norm, SourceSet):
            return []
        alts = []
        for src in base_norm.sources:
            if isinstance(src, str):
                top = self._top_source(module, src, tracers)
                if top and top not in ("local", "python", "unknown", "", None):
                    if top not in alts:
                        alts.append(top)
            elif isinstance(src, CallResult):
                top = self._top_source(module, src.callee, tracers)
                if top and top not in ("local", "python", "unknown", "", None):
                    if top not in alts:
                        alts.append(top)
        return alts

    ## Determine reason/confidence/alternatives for a symbol provenance record.
    #  @param ref The SymbolRef being traced.
    #  @param top The resolved top library.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param module The module name.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Tuple of (reason, confidence, alternatives).
    def _classify_symbol_reason(self, ref, top, tracer, module, tracers):
        if top == "local":
            return (REASON_LOCAL_DEFINITION, 1.0, [])
        if top == "python":
            return (REASON_BUILTIN, 1.0, [])
        if top == "unknown" or not top:
            return (REASON_UNRESOLVED, 0.0, [])
        if ref.kind == "import":
            return (REASON_DIRECT_IMPORT, 1.0, [])
        if ref.kind == "parameter":
            return (REASON_PARAMETER_PROPAGATION, 0.9, [])
        source_norm = normalize_source(ref.source)
        if isinstance(source_norm, SourceSet):
            alts = self._extract_alternatives(ref.source, module, tracers)
            conf = self._classify_confidence(REASON_FLOW_MERGE, alts)
            return (REASON_FLOW_MERGE, conf, alts)
        if isinstance(source_norm, CallResult):
            return (REASON_RETURN_PROPAGATION, 0.9, [])
        return (REASON_TRANSITIVE_IMPORT, 0.9, [])

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
        parts = func_name.split('.')
        first = parts[0]

        if _visited is None:
            _visited = set()
        if first in _visited:
            return func_name
        _visited.add(first)

        replacement = None
        ifs = tracer.import_from_symbols.get(first)
        if ifs:
            ifs_top = ifs.split('.')[0]
            if not self.is_local(ifs_top):
                replacement = ifs
        else:
            caf = tracer.call_assign_funcs.get(first)
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
        return replacement + '.' + '.'.join(parts[1:])

    ## Resolve cross-file symbol references across all modules.
    #
    #  For each symbol in each module, trace its source through imports
    #  and assignments to find the final origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def resolve_cross_file_symbols(self, module_tracers):
        self._call_searched_global = set()
        for module, tracer in module_tracers.items():
            self.global_symbols[module] = {}
            self.symbol_chains[module] = {}
            for symbol, direct_source in tracer.symbols.direct.items():
                chain = self.trace_symbol(module, symbol, module_tracers, set())
                if chain:
                    chain = _dedup_consecutive(chain)
                    self.global_symbols[module][symbol] = self.extract_final_source(chain)
                    self.symbol_chains[module][symbol] = chain
        self._call_searched_global = None

    ## Normalize a container index to its positive equivalent.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param key_idx Raw index (may be negative).
    #  @return Adjusted index.
    def _container_index(self, tracer, container_name, key_idx):
        if not isinstance(key_idx, int):
            return key_idx
        if key_idx >= 0:
            return key_idx
        n = tracer.container_lengths.get(container_name)
        if n is not None:
            return key_idx + n
        return key_idx

    ## Resolve a container item access to its source symbol.
    #
    #  Looks up the item in the current module's container_items, and falls
    #  back to cross-file import if not found locally.
    #  @param module The module where the access occurs.
    #  @param container_name Name of the container variable.
    #  @param key_idx The index/key being accessed.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_container_item(self, module, container_name, key_idx, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        container_idx = self._container_index(tracer, container_name, key_idx)
        item_key = (container_name, container_idx)
        if item_key in tracer.container_items:
            return (module, tracer.container_items[item_key])
        container_direct = tracer.symbols.direct.get(container_name)
        if self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            container_idx_src = self._container_index(src_tracer, container_name, key_idx)
            src_key = (container_name, container_idx_src)
            if src_key in src_tracer.container_items:
                return (src_module, src_tracer.container_items[src_key])
        return None

    ## Add a candidate to the list if not already visited.
    #  @param module The current module.
    #  @param src The source symbol.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param candidates List to append to.
    #  @param visited Set of already-visited origins.
    def _container_candidate(self, module, src, tracers, candidates, visited):
        if not src:
            return
        top_src = self._top_source(module, src, tracers)
        if top_src and top_src not in visited:
            visited.add(top_src)
            candidates.append(top_src)

    ## Collect all candidates for a container's iteration source.
    #  @param module The current module.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of candidate source symbols.
    def _collect_container_candidates(self, module, tracer, container_name, tracers):
        candidates = []
        visited = set()
        for (cont_name, idx), src in tracer.container_items.items():
            if cont_name == container_name:
                self._container_candidate(module, src, tracers, candidates, visited)
        for src in sorted(tracer.container_set_sources.get(container_name, set())):
            self._container_candidate(module, src, tracers, candidates, visited)
        return candidates

    ## Resolve an iteration over a container to its source(s).
    #  @param module The current module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, candidates_list) tuple, or None.
    def _resolve_container_iter(self, module, container_name, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        local_candidates = self._collect_container_candidates(module, tracer, container_name, tracers)
        if local_candidates:
            return (module, local_candidates)
        container_direct = tracer.symbols.direct.get(container_name)
        if isinstance(container_direct, str) and self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            src_candidates = self._collect_container_candidates(src_module, src_tracer, container_name, tracers)
            if src_candidates:
                return (src_module, src_candidates)
        return None

    ## Resolve a method call through class inheritance and cross-file imports.
    #
    #  Searches the class's method list, then recursively checks parent classes,
    #  following imports to other modules as needed.
    #  @param module The current module.
    #  @param class_symbol The class name.
    #  @param method_name The method being called.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, class, method) keys.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_method_symbol(self, module, class_symbol, method_name, tracers, visited):
        tracer = tracers.get(module)
        if not tracer:
            return None
        key = (module, class_symbol, method_name)
        if key in visited:
            return None
        visited.add(key)
        methods = tracer.class_methods.get(class_symbol, [])
        if method_name in methods:
            return (module, method_name)
        for base_symbol in tracer.class_bases.get(class_symbol, []):
            if base_symbol in tracer.class_methods:
                resolved = self._resolve_method_symbol(module, base_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            base_direct = normalize_source(tracer.symbols.direct.get(base_symbol))
            if isinstance(base_direct, CallResult):
                base_direct = base_direct.callee
                if base_direct == base_symbol:
                    base_direct = tracer.import_from_symbols.get(base_symbol, base_direct)
            if isinstance(base_direct, str):
                if self.is_local(base_direct):
                    src_module = base_direct
                    resolved = self._resolve_method_symbol(src_module, base_symbol, method_name, tracers, visited)
                    if resolved:
                        return resolved
                else:
                    return (module, base_symbol)
        class_direct = normalize_source(tracer.symbols.direct.get(class_symbol))
        if isinstance(class_direct, CallResult):
            class_direct = class_direct.callee
            if class_direct == class_symbol:
                class_direct = tracer.import_from_symbols.get(class_symbol, class_direct)
        if isinstance(class_direct, str):
            if self.is_local(class_direct):
                src_module = class_direct
                resolved = self._resolve_method_symbol(src_module, class_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            else:
                if class_direct == "local":
                    rs = tracer.return_sources.get(class_symbol)
                    if rs is not None and isinstance(rs, tuple) and len(rs) == 3 and rs[0] == "call_result":
                        return (module, rs[1])
                return (module, class_symbol)
        return None

    ## Trace a function or constructor parameter through collected call sites.
    #  @param module Module containing the parameter.
    #  @param param_name Parameter name to resolve.
    #  @param display_symbol Symbol to use at the start of the returned chain.
    #  @param tracer Single-file analyzer for module.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of visited trace keys.
    #  @return Chain from display_symbol to argument origin, or None.
    def _trace_parameter_source(self, module, param_name, display_symbol, tracer, tracers, visited):
        for func_name, params in tracer.function_params.items():
            try:
                param_idx = params.index(param_name)
            except ValueError:
                continue
            for call_site in tracer.call_sites.get(func_name, []):
                if param_idx >= len(call_site["args"]):
                    continue
                arg_src = call_site["args"][param_idx]
                if isinstance(arg_src, str):
                    sub_chain = self.trace_symbol(
                        call_site["module"], arg_src, tracers, visited
                    )
                elif arg_src is not None:
                    sub_chain = self.trace_symbol(
                        call_site["module"], param_name, tracers, set(),
                        _direct_source=arg_src,
                    )
                else:
                    sub_chain = None
                if sub_chain:
                    if sub_chain[0] == display_symbol:
                        return sub_chain
                    return [display_symbol] + sub_chain
        return None

    ## Resolve a structured (tuple) source to its concrete origin.
    #
    #  Handles the four structured tuple kinds:
    #  - "container_item" for subscript access
    #  - "instance_method" for method calls
    #  - "container_iter" for iteration over containers
    #  - "call_result" for function call return values
    #  @param module The current module.
    #  @param direct_source The structured tuple (kind, arg1, arg2).
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (display_name, src_module, src_symbol) tuple, or None.
    def _resolve_structured_source(self, module, direct_source, tracers):
        direct_source = normalize_source(direct_source)
        if isinstance(direct_source, SourceSet):
            for src in direct_source.sources:
                if isinstance(src, str):
                    top = self._top_source(module, src, tracers)
                    if top and top not in ("local", "python", "unknown", ""):
                        return (source_display(direct_source), module, src)
                else:
                    resolved = self._resolve_structured_source(module, src, tracers)
                    if resolved is not None:
                        _, src_module, src_symbol = resolved
                        top = self._top_source(src_module, src_symbol, tracers)
                        if top and top not in ("local", "python", "unknown", ""):
                            return resolved
            for src in direct_source.sources:
                if isinstance(src, str):
                    return (source_display(direct_source), module, src)
                resolved = self._resolve_structured_source(module, src, tracers)
                if resolved is not None:
                    return resolved
            return None
        callee_display = None
        if isinstance(direct_source, ContainerItem):
            kind, a, b = "container_item", direct_source.container, direct_source.index
        elif isinstance(direct_source, ContainerIter):
            kind, a, b = "container_iter", direct_source.container, "*"
        elif isinstance(direct_source, InstanceMethod):
            kind, a, b = "instance_method", direct_source.receiver, direct_source.method
        elif isinstance(direct_source, CallResult):
            kind, a, b = "call_result", direct_source.callee, None
            callee_display = direct_source.display_name or direct_source.callee
        elif isinstance(direct_source, tuple) and len(direct_source) == 3:
            kind, a, b = direct_source
        else:
            return None

        if kind == "container_item":
            resolved = self._resolve_container_item(module, a, b, tracers)
            if resolved:
                src_module, src_symbol = resolved
                return (f"{a}[{b}]", src_module, src_symbol)
            return (f"{a}[{b}]", module, a)

        if kind == "instance_method":
            tracer = tracers.get(module)
            if not tracer:
                return None
            if a in tracer.import_from_symbols:
                class_symbol = a
            else:
                class_symbol = tracer.symbols.direct.get(a)
                if isinstance(class_symbol, tuple) and len(class_symbol) == 3 and class_symbol[0] == "call_result":
                    class_symbol = class_symbol[1]
                if a in tracer.class_methods and class_symbol == "local":
                    class_symbol = a
            if not class_symbol:
                receiver_chain = self.trace_symbol(
                    module, a, tracers, set(), _direct_source="local")
                receiver_top = self.extract_final_source(receiver_chain)
                if receiver_top:
                    return (f"{a}.{b}", module, receiver_top)
                return None
            resolved = self._resolve_method_symbol(module, class_symbol, b, tracers, set())
            if not resolved:
                if class_symbol != a and isinstance(a, str) and a in tracer.symbols.direct:
                    resolved = self._resolve_method_symbol(module, a, b, tracers, set())
                if not resolved:
                    class_direct = tracer.symbols.direct.get(class_symbol)
                    if isinstance(class_direct, str) and self.is_local(class_direct):
                        return (f"{a}.{b}", module, "local")
                    return None
            src_module, src_symbol = resolved
            return (f"{a}.{b}", src_module, src_symbol)

        if kind == "container_iter":
            resolved = self._resolve_container_iter(module, a, tracers)
            if not resolved:
                return None
            src_module, candidates = resolved
            if len(candidates) == 1:
                src_symbol = candidates[0]
            else:
                src_symbol = "[" + ",".join(candidates) + "]"
            return (f"{a}[*]", src_module, src_symbol)

        if kind == "call_result":
            callee = a
            if isinstance(callee, SourceSet):
                for src in callee.sources:
                    if isinstance(src, str):
                        top = self._top_source(module, src, tracers)
                        if top and top not in ("local", "python", "unknown", ""):
                            return (f"{callee_display or callee}()", module, src)
                for src in callee.sources:
                    if isinstance(src, str):
                        return (f"{callee_display or callee}()", module, src)
            gs = getattr(self, '_call_searched_global', None)
            if gs is not None:
                if (module, callee) in gs:
                    return (f"{callee_display or callee}()", module, callee)
                gs.add((module, callee))
            callee_chain = self.trace_symbol(module, callee, tracers, set())
            def_module = module
            for item in reversed(callee_chain):
                if isinstance(item, str) and self.is_local(item):
                    def_module = item
                    break
            cur_module = def_module
            cur_symbol = callee
            seen = {(cur_module, cur_symbol)}
            while True:
                tr = tracers.get(cur_module)
                rs = tr.return_sources.get(cur_symbol) if tr else None
                rs = normalize_source(rs)
                if isinstance(rs, SourceSet):
                    for src in rs.sources:
                        if isinstance(src, str):
                            return (f"{callee_display or callee}()", cur_module, src)
                        if isinstance(src, CallResult):
                            return (f"{callee_display or callee}()", cur_module, src.callee)
                if rs is None:
                    return (f"{callee_display or callee}()", cur_module, cur_symbol)
                if isinstance(rs, str):
                    return (f"{callee_display or callee}()", cur_module, rs)
                rs = normalize_source(rs)
                if isinstance(rs, CallResult):
                    next_chain = self.trace_symbol(cur_module, rs.callee, tracers, set())
                    cur_symbol = rs.callee
                    for item in reversed(next_chain):
                        if isinstance(item, str) and self.is_local(item):
                            cur_module = item
                            break
                    if (cur_module, cur_symbol) in seen:
                        return (f"{callee_display or callee}()", cur_module, cur_symbol)
                    seen.add((cur_module, cur_symbol))
                    continue
                break
            return (f"{callee_display or callee}()", cur_module, cur_symbol)

        return None

    ## Recursively trace a symbol through cross-file imports to its origin.
    #
    #  Follows direct sources across module boundaries, handling
    #  structured sources (container items, instance methods, container iters,
    #  call results) at each step.
    #  @param module The current module being traced from.
    #  @param symbol The symbol to trace.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, symbol) pairs.
    #  @return Ordered chain list from symbol to origin.
    def trace_symbol(self, module, symbol, tracers, visited, _direct_source=None):
        if (module, symbol) in visited:
            return []
        visited.add((module, symbol))
        tracer = tracers.get(module)
        if not tracer:
            return []
        direct_source = _direct_source if _direct_source is not None else tracer.symbols.direct.get(symbol)
        if not direct_source:
            if isinstance(symbol, str) and '.' in symbol:
                prefix = symbol.split('.')[0]
                if prefix in tracer.symbols.direct:
                    sub_chain = self.trace_symbol(module, prefix, tracers, visited)
                    if sub_chain:
                        return [symbol] + sub_chain
            if tracer.wildcard_modules:
                tops = []
                local_found = False
                for wm in tracer.wildcard_modules:
                    actual_wm = wm
                    if wm not in tracers:
                        for m in tracers:
                            if m == wm or m.endswith('.' + wm):
                                actual_wm = m
                                break
                    if self.is_local(actual_wm):
                        local_found = True
                    else:
                        top = wm.split('.')[0]
                        if top not in tops:
                            tops.append(top)
                if tops:
                    if len(tops) == 1:
                        return [symbol, tops[0]]
                    else:
                        return [symbol, "[" + ",".join(tops) + "]"]
                if local_found:
                    for wm in tracer.wildcard_modules:
                        actual_wm = wm
                        if wm not in tracers:
                            for m in tracers:
                                if m == wm or m.endswith('.' + wm):
                                    actual_wm = m
                                    break
                        if self.is_local(actual_wm):
                            src_tracer = tracers.get(actual_wm)
                            if src_tracer and symbol in src_tracer.symbols.direct:
                                sub_chain = self.trace_symbol(actual_wm, symbol, tracers, visited)
                                if sub_chain:
                                    return [symbol] + sub_chain
                    return [symbol, "local"]
            if symbol == "self" or (isinstance(symbol, str) and symbol.startswith("self.")):
                return [symbol, "local"]
            if isinstance(symbol, str) and _is_builtin(symbol):
                return [symbol, "python"]
            return [symbol]

        if direct_source == "local":
            param_chain = self._trace_parameter_source(
                module, symbol, symbol, tracer, tracers, visited)
            if param_chain:
                return param_chain

        if isinstance(direct_source, str) and direct_source != symbol:
            param_chain = self._trace_parameter_source(
                module, direct_source, symbol, tracer, tracers, visited)
            if param_chain:
                return param_chain

        structured = self._resolve_structured_source(module, direct_source, tracers)
        if structured is not None:
            display_name, src_module, src_symbol = structured
            sub_chain = self.trace_symbol(src_module, src_symbol, tracers, visited)
            if sub_chain and sub_chain != [src_symbol]:
                return [symbol, display_name] + sub_chain
            src_tracer = tracers.get(src_module)
            if (
                sub_chain == [src_symbol]
                and isinstance(src_symbol, str)
                and src_tracer is not None
                and _is_import_origin(src_tracer, src_symbol)
            ):
                return [symbol, display_name, src_symbol]
            if isinstance(src_symbol, str) and ('.' in src_symbol or '[' in src_symbol or src_symbol == 'local' or _is_builtin(src_symbol)):
                if '.' in src_symbol:
                    first = src_symbol.split('.')[0]
                    full_first = self.module_mapper.resolve_module_name(first, src_module)
                    if self.is_local(full_first):
                        return [symbol, display_name, src_module]
                return [symbol, display_name, src_symbol]
            return [symbol, display_name, src_module]

        if isinstance(direct_source, tuple):
            return [symbol, str(direct_source)]

        if isinstance(direct_source, str):
            full_source = self.module_mapper.resolve_module_name(direct_source, module)
        else:
            full_source = direct_source

        if self.is_local(full_source):
            sub_chain = self.trace_symbol(full_source, symbol, tracers, visited)
            if sub_chain and sub_chain != [symbol]:
                return [symbol, full_source] + sub_chain
            else:
                return [symbol, full_source]
        elif isinstance(full_source, str) and full_source in tracer.symbols.direct:
            sub_chain = self.trace_symbol(module, full_source, tracers, visited)
            if sub_chain:
                return [symbol] + sub_chain
            else:
                return [symbol, full_source]
        else:
            return [symbol, full_source]

    ## Extract the top-level name from a dotted name string.
    #  @param name Possibly dotted name.
    #  @return The first component before a dot.
    def _top_name(self, name):
        if isinstance(name, str) and "." in name:
            return name.split(".")[0]
        return name

    ## Resolve a symbol to its top-level source library.
    #
    #  Traces through the chain and returns the top-level name, or "python"
    #  for builtins.
    #  @param src_module The module where the symbol is referenced.
    #  @param symbol The symbol to resolve.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name (e.g. "requests", "python").
    def _top_source(self, src_module, symbol, tracers):
        if not symbol:
            return None
        if isinstance(symbol, str) and _is_builtin(symbol):
            return "python"
        chain = self.trace_symbol(src_module, symbol, tracers, set())
        if chain:
            return self.extract_final_source(chain)
        src_tracer = tracers.get(src_module)
        if src_tracer:
            top = src_tracer.symbols.get_top(symbol)
            if top:
                return self._top_name(top)
        return self._top_name(symbol)

    ## Extract the ultimate source from a resolution chain.
    #
    #  Walks the chain in reverse; the first non-local, non-builtin element
    #  is the top-level library.
    #  @param chain The resolution chain list.
    #  @return Final source string.
    def extract_final_source(self, chain):
        if not chain:
            return ""
        found_local_module = False
        for item in reversed(chain):
            if isinstance(item, str) and _is_builtin(item):
                return "python"
            if isinstance(item, str) and not self.is_local(item):
                if found_local_module:
                    return "local"
                result = self._top_name(item)
                if result == "self":
                    return "local"
                return result
            if isinstance(item, str) and self.is_local(item):
                found_local_module = True
        return "local"


## Analyze an entire project and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Absolute path to the project root directory.
#  @return ProjectAnalysis with all per-file and cross-file results.
## Analyze an entire project and return structured results.
#
#  Convenience function: creates a ProjectAnalyzer, runs analysis, and
#  returns a ProjectAnalysis object.
#  @param project_root Absolute path to the project root directory.
#  @param scope_model "v1" (legacy, default) or "v2" (lexical scopes).
#  @return ProjectAnalysis with all per-file and cross-file results.
def analyze_project(project_root, scope_model="v1"):
    analyzer = ProjectAnalyzer(project_root, scope_model=scope_model)
    return analyzer.analyze()
