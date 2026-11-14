## @package pcresolve.ownership.classification
#  Classification reason, confidence helpers, and the
#  priority-ordered ClassificationPipeline.
#  提供分类原因、置信度辅助函数和按优先级执行的 ClassificationPipeline。
#
#  Pure functions and the pipeline are extracted from
#  cross_file.ProjectAnalyzer so that reason/confidence
#  rules live in one place (Phase 8B).

from pcresolve.ownership.ir import (ClassificationResult,
                 REASON_DIRECT_IMPORT, REASON_LOCAL_DEFINITION,
                 REASON_BUILTIN, REASON_PARAMETER_PROPAGATION,
                 REASON_RETURN_PROPAGATION, REASON_FLOW_MERGE,
                 REASON_UNRESOLVED, REASON_TRANSITIVE_IMPORT)
from pcresolve.ownership.sources import (InstanceMethod, SourceSet, CallResult, normalize_source)


## Determine confidence for a classification result.
## 根据分类结果确定置信度。
#
#  @param reason       Classification reason constant.
#  @param alternatives List of alternative top-library strings.
#  @return Confidence score (0.0-1.0).
def classify_confidence(reason, alternatives=None):
    if reason == REASON_UNRESOLVED:
        return 0.0
    if reason in (REASON_DIRECT_IMPORT, REASON_LOCAL_DEFINITION, REASON_BUILTIN):
        return 1.0
    if reason in (REASON_PARAMETER_PROPAGATION, REASON_RETURN_PROPAGATION):
        return 0.9
    if reason == REASON_FLOW_MERGE:
        clean = [a for a in (alternatives or [])
                 if a not in ("", None, "unknown")]
        alt_count = len(clean)
        if alt_count > 1:
            return max(1.0 / alt_count, 0.2)
        return 0.85
    return 0.9


## Priority-ordered classification pipeline (Phase 8B).
## 按优先级执行分类规则的流水线（Phase 8B）。
#
#  Wraps top-library determination and reason/confidence
#  assignment into a single priority-ordered rule chain.
#  Callbacks are injected so this module does not import
#  ProjectAnalyzer.
#
#  Rule priority (highest first):
#   1. LOCAL_DEFINITION    — local function, method, or class
#   2. BUILTIN             — Python-provided builtin API
#   3. UNRESOLVED          — unknown or empty top
#   4. DIRECT_IMPORT       — import alias or from-import
#   5. FLOW_MERGE          — SourceSet base (multi-source)
#   6. RETURN_PROPAGATION  — CallResult base
#   7. PARAMETER_PROPAGATION / TRANSITIVE_IMPORT — default
class ClassificationPipeline:
    ## Configure callbacks used for ownership and origin resolution.
    ## 配置归属判定和来源解析所需的回调。
    #
    #  @param origin_candidates_cb Callback returning origin candidates.
    #  @param is_direct_import_cb Callback checking direct import ownership.
    #  @param dedupe_cb Callback preserving unique candidate order.
    #
    #  @return None; the injected callbacks are stored for later classification.
    def __init__(self, origin_candidates_cb, is_direct_import_cb, dedupe_cb):
        self._origin_candidates = origin_candidates_cb
        self._is_direct_import = is_direct_import_cb
        self._dedupe = dedupe_cb

    ## Classify a resolved (base, top) pair.
    ## 对已解析的 (base, top) 对进行分类。
    #
    #  @param base        Call base symbol or source.
    #  @param top         Resolved top library.
    #  @param module      Current module name.
    #  @param tracer      SingleFileAnalyzer for the module.
    #  @param tracers     Dict module_name -> SingleFileAnalyzer.
    #  @param expand_origins  Whether to extract alternatives.
    #  @return ClassificationResult.
    def classify(self, base, top, module, tracer, tracers,
                 expand_origins=True):
        # Rules 1-3: early-exit categories.
        # 规则 1-3：本地、内建和未知类别在此提前返回。
        if top == "local":
            alternatives = []
            if expand_origins and isinstance(normalize_source(base), SourceSet):
                alternatives = self._extract_alternatives(
                    base, module, tracers)
            return ClassificationResult(
                library="local",
                reason=REASON_FLOW_MERGE if alternatives else REASON_LOCAL_DEFINITION,
                confidence=0.5 if alternatives else 1.0,
                alternatives=alternatives,
                is_usage_library=False)

        if top == "python":
            return ClassificationResult(
                library="python", reason=REASON_BUILTIN,
                confidence=1.0, alternatives=[], is_usage_library=False)

        if top == "unknown" or not top:
            alternatives = []
            if expand_origins:
                alternatives = self._extract_alternatives(
                    base, module, tracers)
            reason = REASON_FLOW_MERGE if alternatives else REASON_UNRESOLVED
            return ClassificationResult(
                library="unknown", reason=reason,
                confidence=classify_confidence(reason, alternatives),
                alternatives=alternatives, is_usage_library=False)

        # Rules 4-7: import-backed library owner categories.
        # 规则 4-7：对有导入依据的库所有者进一步判定原因和来源候选。
        reason = self._determine_reason(
            base, top, tracer, module, tracers, expand_origins)

        if expand_origins:
            alternatives = self._extract_alternatives(
                base, module, tracers)
        else:
            alternatives = []

        confidence = classify_confidence(reason, alternatives)
        is_lib = top not in ("", "local", "python", "unknown")

        return ClassificationResult(
            library=top, reason=reason, confidence=confidence,
            alternatives=alternatives, is_usage_library=is_lib)

    # ── reason determination (priority-ordered) ─────────────────────────

    ## Select the highest-priority reason supported by the resolved evidence.
    ## 根据已解析证据选择优先级最高的分类原因。
    #
    #  @param base Call base symbol or normalized source.
    #  @param top Resolved top-level owner label.
    #  @param tracer Analyzer for the call's module.
    #  @param module Module containing the call site.
    #  @param tracers Analyzers for all indexed modules.
    #  @param expand_origins Whether to inspect merged origin candidates.
    #  @return Classification reason constant.
    def _determine_reason(self, base, top, tracer, module, tracers,
                          expand_origins):
        # Rule 4: DIRECT_IMPORT
        if self._is_direct_import(tracer, base):
            return REASON_DIRECT_IMPORT

        # Rule 5: FLOW_MERGE — SourceSet base
        base_norm = normalize_source(base)
        if isinstance(base_norm, SourceSet):
            return REASON_FLOW_MERGE

        # Rule 6: RETURN_PROPAGATION — CallResult base
        result_base = base_norm
        if (isinstance(base_norm, InstanceMethod)
                and isinstance(
                    normalize_source(base_norm.receiver), CallResult)):
            result_base = normalize_source(base_norm.receiver)
        if isinstance(result_base, CallResult):
            if expand_origins:
                origins = self._origin_candidates(
                    module, result_base, tracers, include_local=False)
                unique = [o for o in self._dedupe(origins)
                          if o not in ("", None, "unknown")]
                if len(unique) > 1:
                    return REASON_FLOW_MERGE
            return REASON_RETURN_PROPAGATION

        # Rule 7: default — TRANSITIVE_IMPORT or PARAMETER_PROPAGATION
        # 规则 7：缺少更高优先级证据时回退到传递导入原因。
        return REASON_TRANSITIVE_IMPORT

    # ── helpers ────────────────────────────────────────────────────────

    ## Extract unique non-empty library alternatives from a source expression.
    ## 从来源表达式中提取唯一且非空的库候选。
    #
    #  @param base Call base symbol or source record.
    #  @param module Module containing the call site.
    #  @param tracers Analyzers for all indexed modules.
    #  @return Normalized alternative library labels.
    def _extract_alternatives(self, base, module, tracers):
        origins = self._origin_candidates(module, base, tracers,
                                          include_local=True)
        alts = [x for x in self._dedupe(origins)
                if x not in ("", None, "unknown")]
        return _normalize_merged_labels(alts)


## Split merged container labels such as "[requests,numpy]" into library names.
## 将 "[requests,numpy]" 这样的合并容器标签拆分为独立库名。
#
#  @param alts Candidate labels, including possibly merged container spellings.
#  @return Unique library labels with local and unknown sentinels removed.
def _normalize_merged_labels(alts):
    out = []
    for a in alts:
        if isinstance(a, str) and a.startswith("[") and a.endswith("]"):
            parts = [p.strip() for p in a[1:-1].split(",") if p.strip()]
            for p in parts:
                if p and p not in ("local", "python", "unknown", "") and p not in out:
                    out.append(p)
        else:
            if a and a not in ("local", "python", "unknown", "") and a not in out:
                out.append(a)
    return out
