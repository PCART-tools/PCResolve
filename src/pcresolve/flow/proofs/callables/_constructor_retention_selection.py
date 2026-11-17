## @package pcresolve.flow.proofs.callables._constructor_retention_selection
#  Conflict checks and witness selection after receiver-effect collection.
#  接收者效果事实收集后的冲突检查与 witness 筛选。

import ast


## Check collected effects against the retained-store proof boundary.
## 根据保留存储证明边界检查已收集的效果事实。
#
#  @param writes Collected receiver writes as owner/name/node/statement tuples.
#  @param calls Collected receiver method calls.
#  @param namespace Attributes governed by class or descriptor protocols.
#  @param lookup_name Attribute excluded by the current lookup proof.
#  @param dependencies Required decorator source paths.
#  @param source_hashes Hashes available for the analyzed source snapshot.
#  @return True when all collected facts stay within the requested proof.
def retention_facts_are_closed(writes, calls, namespace, lookup_name,
                               dependencies, source_hashes):
    if any(attribute in calls for _, attribute, _, _ in writes):
        return False
    if any(attribute in namespace for _, attribute, _, _ in writes):
        return False
    if lookup_name is not None and any(
            attribute == lookup_name for _, attribute, _, _ in writes):
        return False
    return all(path in source_hashes for path in dependencies)


## Select unique ordinary root-initializer stores for witness generation.
## 筛选可生成 witness 的唯一普通根初始化器存储。
#
#  @param writes Collected receiver writes as owner/name/node/statement tuples.
#  @param root_owner Selected root initializer owner.
#  @param namespace Attributes governed by class or descriptor protocols.
#  @return Candidate writes that may be projected into retained-store witnesses.
def select_retained_store_writes(writes, root_owner, namespace):
    candidates = []
    for owner, attribute, destination, statement in writes:
        if (owner != root_owner or attribute in namespace or attribute.startswith('__')
                or not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(destination.ctx, ast.Store)
                or sum(name == attribute for _, name, _, _ in writes) != 1):
            continue
        candidates.append((owner, attribute, destination, statement))
    return candidates
