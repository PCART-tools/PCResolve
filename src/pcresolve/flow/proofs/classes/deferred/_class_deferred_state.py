## @package pcresolve.flow.proofs.classes._class_deferred_state
#  Conservative joins for declaration-time helper bindings and literals.
#  延迟声明辅助函数绑定与字面量事实的保守分支合并。


## Merge only facts that agree across both bounded control-flow branches.
## 仅保留两个有界控制流分支均一致的事实。
#
#  @param state Binding state to update in place.
#  @param values Known literal-string state to update in place.
#  @param left Bindings after the first branch.
#  @param right Bindings after the second branch.
#  @param left_values Literal strings after the first branch.
#  @param right_values Literal strings after the second branch.
#  @return None; updates the supplied path state at the join point.
def merge_deferred_branch_state(state, values, left, right, left_values, right_values):
    merged = {}
    for name in set(left) | set(right):
        if name not in left or name not in right or left[name][:2] != right[name][:2]:
            merged[name] = ('uncertain', None)
        else:
            merged[name] = (left[name] if left[name] == right[name]
                            else (*left[name][:2], None))
    state.clear()
    state.update(merged)
    values.clear()
    values.update({name: value for name, value in left_values.items()
                   if right_values.get(name) == value})
