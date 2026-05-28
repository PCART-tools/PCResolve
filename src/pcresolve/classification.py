## @package pcresolve.classification
#  Classification reason, confidence helpers, and the
#  priority-ordered ClassificationPipeline.
#
#  Pure functions and the pipeline are extracted from
#  cross_file.ProjectAnalyzer so that reason/confidence
#  rules live in one place (Phase 8B).

from .ir import (ClassificationResult,
                 REASON_DIRECT_IMPORT, REASON_LOCAL_DEFINITION,
                 REASON_BUILTIN, REASON_PARAMETER_PROPAGATION,
                 REASON_RETURN_PROPAGATION, REASON_FLOW_MERGE,
                 REASON_UNRESOLVED, REASON_TRANSITIVE_IMPORT)
from .sources import (SourceSet, CallResult, normalize_source)


## Determine confidence for a classification result.
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
#
#  Wraps top-library determination and reason/confidence
#  assignment into a single priority-ordered rule chain.
#  Callbacks are injected so this module does not import
#  ProjectAnalyzer.
#
#  Rule priority (highest first):
#   1. LOCAL_DEFINITION    — local function, method, or class
#   2. BUILTIN             — Python builtin / stdlib
#   3. UNRESOLVED          — unknown or empty top
#   4. DIRECT_IMPORT       — import alias or from-import
#   5. FLOW_MERGE          — SourceSet base (multi-source)
#   6. RETURN_PROPAGATION  — CallResult base
#   7. PARAMETER_PROPAGATION / TRANSITIVE_IMPORT — default
class ClassificationPipeline:
    ## @param origin_candidates_cb fn(module, source, tracers, include_local)
    ## @param is_direct_import_cb fn(tracer, base) -> bool
    ## @param dedupe_cb fn(items) -> list
    def __init__(self, origin_candidates_cb, is_direct_import_cb, dedupe_cb):
        self._origin_candidates = origin_candidates_cb
        self._is_direct_import = is_direct_import_cb
        self._dedupe = dedupe_cb

    ## Classify a resolved (base, top) pair.
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
            return ClassificationResult(
                library="unknown", reason=REASON_UNRESOLVED,
                confidence=0.0, alternatives=[], is_usage_library=False)

        # Rules 4-7: third-party categories.
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

    def _determine_reason(self, base, top, tracer, module, tracers,
                          expand_origins):
        """Apply priority-ordered rules to determine the reason."""
        # Rule 4: DIRECT_IMPORT
        if self._is_direct_import(tracer, base):
            return REASON_DIRECT_IMPORT

        # Rule 5: FLOW_MERGE — SourceSet base
        base_norm = normalize_source(base)
        if isinstance(base_norm, SourceSet):
            return REASON_FLOW_MERGE

        # Rule 6: RETURN_PROPAGATION — CallResult base
        if isinstance(base_norm, CallResult):
            if expand_origins:
                origins = self._origin_candidates(
                    module, base_norm, tracers, include_local=False)
                unique = [o for o in self._dedupe(origins)
                          if o not in ("", None, "unknown")]
                if len(unique) > 1:
                    return REASON_FLOW_MERGE
            return REASON_RETURN_PROPAGATION

        # Rule 7: default — TRANSITIVE_IMPORT or PARAMETER_PROPAGATION
        return REASON_TRANSITIVE_IMPORT

    # ── helpers ────────────────────────────────────────────────────────

    def _extract_alternatives(self, base, module, tracers):
        origins = self._origin_candidates(module, base, tracers,
                                          include_local=True)
        alts = [x for x in self._dedupe(origins)
                if x not in ("", None, "unknown")]
        return _normalize_merged_labels(alts)


## Split merged container labels like "[requests,numpy]" into
#  individual library names for alternatives.
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
