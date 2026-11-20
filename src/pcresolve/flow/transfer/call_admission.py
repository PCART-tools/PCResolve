## @package pcresolve.flow.transfer.call_admission
#  Decide whether a call may enter value-flow transfer.
#
#
#  Computes budget charges and cutoff boundaries before per-call state exists.
#  A separate operation records admitted call locations in the current query.
#  在建立单次调用状态前确定预算扣减及截断边界；独立操作记录本次查询中已接纳的调用位置。



from collections import namedtuple


CallAdmission = namedtuple(
    'CallAdmission', ('charge_class', 'charge_summary', 'boundary'))


## Decide budget charges and the first exhausted budget for one call.
## 确定单次调用的预算扣减以及首个耗尽的预算。
#
#  @param already_evaluated Whether the call was already evaluated in this query.
#  @param in_class_return Whether analysis is currently inside a class return.
#  @param class_remaining Remaining class-return budget before this call.
#  @param summary_remaining Remaining summary budget before this call.
#  @return Admission with charge flags and an optional cutoff boundary.
def decide_call_admission(*, already_evaluated, in_class_return,
                          class_remaining, summary_remaining):
    # Determine charges and the first exhausted budget in execution order.
    if already_evaluated:
        return CallAdmission(False, False, None)
    if in_class_return and class_remaining <= 0:
        return CallAdmission(False, False, 'class_return_budget')
    charge_class = in_class_return
    if summary_remaining <= 0:
        return CallAdmission(charge_class, False, 'budget_exceeded')
    return CallAdmission(charge_class, True, None)


## Charge an admitted call and record its location in the current query.
## 对已接纳的调用扣减预算并记录其在本次查询中的位置。
#
#  @param admission Admission computed for the call.
#  @param remaining Summary budget before the call is charged.
#  @param evaluated Set of call locations already evaluated in this query.
#  @param location Call location recorded when the summary is charged.
#  @return Remaining summary budget after the call.
def apply_summary_admission(admission, remaining,
                            evaluated,
                            location):
    # Charge an admitted call and record its location in the current query.
    if admission.charge_summary:
        evaluated.add(location)
        return remaining - 1
    return remaining
