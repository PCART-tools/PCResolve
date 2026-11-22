## @package pcresolve.flow.transfer.environment
#  Merge value-flow environments.
#
#
#  Joins branch bindings and result sources conservatively when paths differ.
#  在分支路径不同时保守合并变量绑定与结果来源。



## Deduplicate values while keeping their first occurrence order.
## 对值去重并保留首次出现的顺序。
#
#  @param values Values whose duplicate entries are dropped.
#  @return Unique values in their original order.
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


## Preserve the branch on which an incoming local source survives a join.
## 保留分支合并时原局部来源仍然有效的分支条件。
#
#  @param incoming Bindings before evaluating the two suites.
#  @param left Normal exit environments from the true branch.
#  @param right Normal exit environments from the false branch.
#  @param test Source evidence for the branch test.
#  @return None
def guard_surviving_sources(incoming, left, right, test):
    if not left or not right:
        return
    names = set(incoming)
    names.update(name for state in left + right for name in state)
    for name in names:
        if not name.isidentifier():
            continue
        left_values = [value for state in left for value in state.get(name, [])]
        right_values = [value for state in right for value in state.get(name, [])]
        # Compare every local value, not only values of one selected shape.
        # A parameter, literal and call result can occupy the same name on the
        # two branches; the branch-specific alternative must keep its guard.
        # 比较每个局部值，而不只比较某一类形状。参数、字面量和调用结果可能
        # 占据两个分支中的同一个名字；分支特有的候选必须保留自己的条件。
        tracked_kinds = ('parameter', 'literal', 'call_result', 'capture')
        left_sources = [value for value in left_values
                        if value.get('kind') in tracked_kinds]
        right_sources = [value for value in right_values
                         if value.get('kind') in tracked_kinds]
        for states, own_sources, other_sources, branch in (
                (left, left_sources, right_values, True),
                (right, right_sources, left_values, False)):
            # The same value can survive under different guards on either branch.
            # 同一个值可以在两个分支上以不同条件存活。
            exclusive = [value for value in own_sources if value not in other_sources]
            if not exclusive:
                continue
            guard = {'test': test, 'branch': branch}
            for state in states:
                updated = []
                for value in state.get(name, []):
                    if (value in exclusive
                            and guard not in value.get('conditions', [])):
                        value = dict(value, conditions=value.get('conditions', []) + [guard])
                    updated.append(value)
                state[name] = updated


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
                          'class', 'call_result', 'container', 'callable', 'literal', 'parameter')
                      or value.get('class_type') or value.get('callable_type') else value
                      for value in values]
        merged[key] = values
    return merged
