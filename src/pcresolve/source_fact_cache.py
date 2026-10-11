## @package pcresolve.source_fact_cache
#  Detached ownership visitor facts, captured before any project propagation.

import ast
from copy import deepcopy

from .call_graph import FunctionId


## Copy collected facts without copying ASTs or retaining callbacks to another run.
#  @param tracer Pristine single-file visitor state, never a propagated tracer.
#  @param document Read-only source version owning its AST identities.
#  @param budget Optional current analysis budget.
#  @return Independent visitor facts with callbacks rebound to the copy.
def clone_source_facts(tracer, document, budget=None):
    if budget is not None:
        budget.checkpoint(force=True)
    memo = {}
    for node in ast.walk(document.tree):
        if budget is not None:
            budget.checkpoint()
        memo[id(node)] = node
    previous_budget = tracer._analysis_budget
    if previous_budget is not None:
        memo[id(previous_budget)] = None
    copied = deepcopy(tracer, memo)
    copied._analysis_budget = budget
    facts = copied._mapping_facts
    facts.lookup = copied._mapping_binding
    facts.lambda_identity = lambda node: FunctionId(
        copied.module_name or '', copied._local_lambda_key(node))
    facts.mutable_lookup = lambda name: copied.current_scope().lookup(
        name, skip_parent_classes=True)
    facts.python_shape = copied._expression_python_shape
    if budget is not None:
        budget.checkpoint(force=True)
    return copied
