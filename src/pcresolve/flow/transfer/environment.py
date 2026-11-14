## @package pcresolve.flow.transfer.environment
#  Conservative joins of flow environments and result sources.


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


## Merge result alternatives while retaining incomplete container evidence.
## 合并结果候选，并保留不完整的容器证据。
#
#  @param left First branch sources.
#  @param right Second branch sources.
#  @return Deduplicated merged source records.
def merge_result_sources(left, right):
    incomplete = any(not values or any(
        not value.get('container_object') or value.get('value_incomplete')
        for value in values) for values in (left, right))
    return _unique([dict(value, value_incomplete=True)
                    if incomplete and value.get('container_object') else value
                    for value in left + right])


## Merge branch environments without treating absent bindings as certain.
## 合并分支环境，不将缺失绑定视为确定事实。
#
#  @param environments Branch environment mappings.
#  @return Merged environment with uncertainty markers.
def merge_environments(environments):
    keys = set().union(*(e.keys() for e in environments))
    merged = {}
    for key in keys:
        values = _unique([value for env in environments for value in env.get(key, [])])
        if key.endswith('$keys'):
            values = [dict(value, presence_unconfirmed=True)
                      if not all(any(marker.get('key') == value.get('key')
                          and not marker.get('presence_unconfirmed')
                          for marker in env.get(key, [])) for env in environments)
                      else value for value in values]
        if any(not env.get(key) for env in environments):
            values = [dict(value, import_incomplete=True)
                      if value.get('kind') == 'import' else
                      dict(value, value_incomplete=True) if value.get('kind') in (
                          'class', 'call_result', 'container', 'callable')
                      or value.get('class_type') or value.get('callable_type') else value
                      for value in values]
        merged[key] = values
    return merged
