## @package pcresolve.flow.proofs.namespaces.source._source_dependencies
#  Track source proof dependencies.
#
#
#  Versioned support for explicit source-protocol proofs, outside primary flow.
#  为显式源码协议证明维护版本化支持依赖，不扩展主数据流范围。



from pcresolve.frontend.source_snapshot import FLOW_SOURCE, SourceStore


## Register only independently proved dependency versions for an opted-in query.
## 为显式启用的查询仅注册已独立证明的依赖版本。
#
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

    # Validate every extension before publishing any of them to the registry.
    # 更新注册表前先验证全部扩展依赖，避免保留部分更新。
    for path, digest in external.items():
        previous = analyzer._supporting_source_hashes.get(path)
        if previous is not None and previous != digest:
            raise ValueError('Source protocol sources changed during analysis')
    analyzer._supporting_source_hashes.update(external)
    return True


## Verify supporting versions independently of primary snapshot membership.
## 独立于主快照成员关系校验支持依赖的版本。
#
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
## 附加支持依赖版本，不将其视为主数据流输入。
#
#  @param analyzer Query-local dependency registry.
#  @param result Completed primary analysis or expansion.
#  @return None.
def publish(analyzer, result):
    hashes = analyzer._supporting_source_hashes
    if hashes:
        validate(hashes, analyzer._analysis_budget)
        result.inputs['supporting_source_sha256'] = dict(sorted(hashes.items()))
