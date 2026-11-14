## @package pcresolve.ownership.source_resolution
#  SourceSet primary convergence resolver.
#
#  Extracted from cross_file.ProjectAnalyzer to keep
#  _resolve_structured_source() and _top_source() from
#  tangling with SourceSet-resolution internals.
#
#  The class receives callbacks for the bits that still live
#  on ProjectAnalyzer so we avoid a circular import.
#  收敛来源集合的首要库候选；通过注入回调避免循环导入。

from pcresolve.ownership.sources import (normalize_source, CallResult, PythonShape,
                               is_structured_source)


## Resolves a SourceSet to a primary top-library candidate.
## 将来源集合解析为首要顶层库候选。
#
#  Uses origin-aware rules:
#  - "return": accepts local + single import-backed library convergence.
#  - "dict_lookup": strict — no local, no unknown, single import-backed.
#  - default (no origin): same strict rules as dict_lookup.
#
#  Callbacks are injected so this module does not import ProjectAnalyzer.
class SourceSetResolver:
    ## Initialize callbacks used to resolve and classify source candidates.
    ## 初始化解析和分类来源候选所需的回调。
    #
    #  @param top_source_cb Resolve a symbol to a top-level source.
    #  @param cg_return_cb Look up a callee's collected return source.
    #  @param known_local_cb Test whether a symbol is known to be local.
    #  @param resolve_structured_cb Resolve a structured source to its target.
    #  @param dedupe_cb Deduplicate candidates while preserving consumer policy.
    #  @param is_import_origin_cb Optional test for import-backed origin.
    #  @return None
    def __init__(self, top_source_cb, cg_return_cb, known_local_cb,
                 resolve_structured_cb, dedupe_cb,
                 is_import_origin_cb=None):
        self._top_source = top_source_cb
        self._lookup_cg_return_source = cg_return_cb
        self._is_known_local = known_local_cb
        self._resolve_structured_source = resolve_structured_cb
        self._dedupe_list = dedupe_cb
        self._is_import_origin = is_import_origin_cb

    # ── public API ──────────────────────────────────────────────────────

    ## Resolve a SourceSet to a primary top library, or None.
    ## 将来源集合解析为首要顶层库；无法收敛时返回 None。
    #
    #  @param module   Current module name.
    #  @param sourceset SourceSet to resolve.
    #  @param tracers  Dict module_name -> SingleFileAnalyzer.
    #  @param _seen    Internal cycle-detection set.
    #  @return Top library string or None.
    def resolve_primary(self, module, sourceset, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        tops, has_local, has_unknown = self._collect_tops(
            module, sourceset, tracers, _seen=_seen)
        origin = getattr(sourceset, "origin", "")

        if origin == "dict_lookup":
            if len(tops) == 1 and not has_local and not has_unknown:
                return tops[0]
            return None

        if origin == "return":
            if len(tops) == 1 and not has_unknown:
                return tops[0]
            return None

        # Default convergence rejects local and unknown alternatives.
        # 默认收敛规则拒绝包含本地或未知来源的候选集合。
        if len(tops) == 1 and not has_local and not has_unknown:
            return tops[0]
        return None

    # ── internal helpers ────────────────────────────────────────────────

    ## Collect import-backed-library top candidates and local/unknown flags
    ## 收集来源集合中的顶层库候选以及本地、未知标记。
    #  from every source inside a SourceSet.
    #
    #  @param module Current module name.
    #  @param sourceset Source alternatives to inspect.
    #  @param tracers Module analyzers used for lookup.
    #  @param _seen Shared cycle-detection set.
    #  @return Deduplicated top candidates and local/unknown flags.
    def _collect_tops(self, module, sourceset, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        tops = []
        has_local = False
        has_unknown = False
        for src in sourceset.sources:
            top = self._to_top_candidate(module, src, tracers, _seen=_seen)
            if top in ("", None, "unknown"):
                has_unknown = True
            elif top == "local":
                has_local = True
            elif top == "python":
                tops.append("python")
            else:
                tops.append(top)
        return self._dedupe_list(tops), has_local, has_unknown

    ## Resolve a single source to its top-library candidate.
    ## 将单个来源解析为顶层库候选。
    #
    #  CallResult resolution is restricted to import-backed callees
    #  to avoid recursive SourceSet loops: a local symbol whose
    #  direct binding is itself a SourceSet would re-enter
    #  convergence resolution and overflow the stack.
    #
    #  @param module Current module name.
    #  @param source Source value to resolve.
    #  @param tracers Module analyzers used for lookup.
    #  @param _seen Shared cycle-detection set.
    #  @return Top candidate or None when unresolved or cyclic.
    def _to_top_candidate(self, module, source, tracers, _seen=None):
        if _seen is None:
            _seen = set()
        source = normalize_source(source)
        if isinstance(source, PythonShape):
            return "python"
        if isinstance(source, str):
            key = (module, "str", source)
            if key in _seen:
                return None
            _seen.add(key)
            cg = self._lookup_cg_return_source(module, source)
            if cg:
                return self._top_source(
                    module, cg, tracers, _seen=_seen) or cg
            return self._top_source(
                module, source, tracers, _seen=_seen)
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            source_module = source.source_module or module
            key = (source_module, "cr", source.callee)
            if key in _seen:
                return None
            _seen.add(key)
            if source.result_source is not None:
                resolved = self._resolve_structured_source(
                    source_module, source, tracers, _seen=_seen)
                if resolved:
                    _, src_module, src_symbol = resolved
                    return self._top_source(
                        src_module, src_symbol, tracers, _seen=_seen)
            cg = self._lookup_cg_return_source(source_module, source.callee)
            if cg:
                return self._top_source(
                    source_module, cg, tracers, _seen=_seen) or cg
            tracer = tracers.get(source_module)
            if tracer:
                first = source.callee.split(".")[0]
                if (first in getattr(tracer, "import_aliases", set()) or
                        first in getattr(tracer, "import_from_symbols", {})):
                    return self._top_source(
                        source_module, source.callee, tracers, _seen=_seen)
                if self._is_known_local(tracer, source.callee):
                    return "local"
                # Dotted call results can retain a qualified import target
                # even when the first component is not itself an alias.
                # Accept this only when the tracer independently records
                # import-backed evidence for the complete symbol.
                # 只有完整符号具备独立导入来源证据时才接受限定调用结果。
                if (self._is_import_origin is not None
                        and self._is_import_origin(
                            tracer, source.callee)):
                    return self._top_source(
                        source_module, source.callee, tracers, _seen=_seen)
            return None
        if is_structured_source(source):
            resolved = self._resolve_structured_source(
                module, source, tracers, _seen=_seen)
            if resolved:
                _, src_module, src_symbol = resolved
                return self._top_source(
                    src_module, src_symbol, tracers, _seen=_seen)
        return None
