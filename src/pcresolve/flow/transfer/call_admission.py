# Budget decisions made before call-transfer state is constructed.

from collections import namedtuple


CallAdmission = namedtuple(
    'CallAdmission', ('charge_class', 'charge_summary', 'boundary'))


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


def apply_summary_admission(admission, remaining,
                            evaluated,
                            location):
    # Charge an admitted call and record its location in the current query.
    if admission.charge_summary:
        evaluated.add(location)
        return remaining - 1
    return remaining
