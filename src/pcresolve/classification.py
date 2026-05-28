## @package pcresolve.classification
#  Classification reason and confidence helpers.
#
#  Pure functions extracted from cross_file.ProjectAnalyzer
#  so that reason/confidence rules live in one place.

from .ir import (REASON_DIRECT_IMPORT, REASON_LOCAL_DEFINITION,
                 REASON_BUILTIN, REASON_PARAMETER_PROPAGATION,
                 REASON_RETURN_PROPAGATION, REASON_FLOW_MERGE,
                 REASON_UNRESOLVED)


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
