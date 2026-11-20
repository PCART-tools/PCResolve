## @package pcresolve.flow.transfer.recursive_summary
#  Construct and execute recursive flow summaries.
#
#
#  Passes inputs to a child-summary factory and returns execution results with
#  the remaining budget and effects needed by the caller.
#  将输入交给子摘要工厂，并向调用方返回执行结果、剩余预算及相关效果。



from collections import namedtuple


ChildExpressionExecution = namedtuple(
    'ChildExpressionExecution', ('values', 'heap_updates', 'remaining'))


ChildBlockExecution = namedtuple(
    'ChildBlockExecution', ('outcomes', 'calls', 'mapping_effects', 'boundaries', 'remaining'))


## Create a child summary by delegating to a caller-supplied factory.
## 通过调用方提供的工厂创建子摘要。
#
#  @param factory Callable that constructs the child from the given inputs.
#  @param result Child analysis result receiving generated facts.
#  @param ref Function identity represented by the child summary.
#  @param node Source function node evaluated by the child.
#  @param remaining Remaining call-analysis budget for the child.
#  @param receiver_class Optional receiver class context for the child.
#  @param incoming Optional incoming value facts for the child.
#  @return Newly created child summary.
def create_child_summary(factory, result,
                         ref, node, remaining,
                         receiver_class = None,
                         incoming = None
                         ):
    return factory(result, ref, node, remaining, receiver_class, incoming)


## Evaluate a child expression and capture its heap updates and budget.
## 求值子表达式，并记录其堆更新和剩余预算。
#
#  @param child Child summary that evaluates the expression.
#  @param node Expression node to evaluate.
#  @param env Environment the child reads and updates.
#  @return Execution record with values, heap updates and remaining budget.
def evaluate_child_expression(child, node,
                              env):
    values = child.expression(node, env)
    heap_updates = {key: value for key, value in env.items()
                    if key.startswith('$heap:')}
    return ChildExpressionExecution(values, heap_updates, child.remaining)


## Apply a child expression execution to the parent summary.
## 将子表达式执行结果应用到父摘要。
#
#  @param parent Parent summary receiving heap updates and the budget.
#  @param env Environment updated with the child's heap facts.
#  @param execution Child execution record to propagate.
#  @return Values produced by the child expression.
def propagate_child_expression(parent,
                               env,
                               execution
                               ):
    env.update(execution.heap_updates)
    parent.remaining = execution.remaining
    return execution.values


## Execute a child statement block and snapshot its call and effect facts.
## 执行子语句块，并快照其调用和效果事实。
#
#  @param child Child summary that executes the block.
#  @param statements Statement nodes forming the block.
#  @param env Environment the child reads and updates.
#  @return Execution record with outcomes, calls, effects and boundaries.
def execute_child_block(child,
                        statements,
                        env):
    outcomes = child.block(statements, env)
    return ChildBlockExecution(outcomes, tuple(child.calls),
                               tuple(child.mapping_effects),
                               tuple(child.result.boundaries), child.remaining)


## Merge a child block execution into the parent summary.
## 将子语句块执行结果合并到父摘要。
#
#  @param parent Parent summary receiving the merged facts.
#  @param execution Child block execution record to merge.
#  @return None
def merge_child_block(parent,
                      execution):
    parent.remaining = min(parent.remaining, execution.remaining)
    parent.calls.extend(execution.calls)
    parent.mapping_effects.extend(execution.mapping_effects)
    parent.result.boundaries.extend(execution.boundaries)
