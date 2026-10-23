## @package pcresolve._source_dependencies
#  Versioned support for explicit source-protocol proofs, outside primary flow.

from .source_snapshot import FLOW_SOURCE, SourceStore


## Register only independently proved dependency versions for an opted-in query.
#  @param analyzer Primary flow adapter; its source files and naming scope stay fixed.
#  @param hashes Complete source-protocol premise, including ambient primary files.
#  @return False for an unapproved extension; conflicting versions raise ValueError.
def register(analyzer, hashes):
    external = {}
    for path, digest in hashes.items():
        if path in analyzer.hashes:
            if analyzer.hashes[path] != digest:
                raise ValueError('Source protocol sources changed during analysis')
        else:
            external[path] = digest
    if external and not analyzer.support_source_protocols:
        return False
    for path, digest in external.items():
        previous = analyzer._supporting_source_hashes.get(path)
        if previous is not None and previous != digest:
            raise ValueError('Source protocol sources changed during analysis')
    analyzer._supporting_source_hashes.update(external)
    return True


## Verify supporting versions independently of primary snapshot membership.
#  @param hashes Dependency versions from a completed protocol proof.
#  @param budget Optional shared source-reading budget.
#  @return None; stale/missing dependency versions raise ValueError.
def validate(hashes, budget=None):
    if not hashes:
        return
    snapshot = SourceStore().snapshot(hashes, FLOW_SOURCE, budget=budget)
    if any(snapshot.documents[path].sha256 != digest
           for path, digest in hashes.items()):
        raise ValueError('Source protocol sources changed; call analyze again')


## Attach supporting versions without claiming that they are primary flow inputs.
#  @param analyzer Query-local dependency registry.
#  @param result Completed primary analysis or expansion.
#  @return None.
def publish(analyzer, result):
    hashes = analyzer._supporting_source_hashes
    if hashes:
        validate(hashes, analyzer._analysis_budget)
        result.inputs['supporting_source_sha256'] = dict(sorted(hashes.items()))
