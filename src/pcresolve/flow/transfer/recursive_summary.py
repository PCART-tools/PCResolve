## @package pcresolve.flow.transfer.recursive_summary
#  Typed construction and execution adapters for recursive summaries.

from collections import namedtuple


ChildExpressionExecution = namedtuple(
    'ChildExpressionExecution', ('values', 'heap_updates', 'remaining'))


ChildBlockExecution = namedtuple(
    'ChildBlockExecution', ('outcomes', 'calls', 'mapping_effects', 'boundaries', 'remaining'))


def create_child_summary(factory, result,
                         ref, node, remaining,
                         receiver_class = None,
                         incoming = None
                         ):
    return factory(result, ref, node, remaining, receiver_class, incoming)


def evaluate_child_expression(child, node,
                              env):
    values = child.expression(node, env)
    heap_updates = {key: value for key, value in env.items()
                    if key.startswith('$heap:')}
    return ChildExpressionExecution(values, heap_updates, child.remaining)


def propagate_child_expression(parent,
                               env,
                               execution
                               ):
    env.update(execution.heap_updates)
    parent.remaining = execution.remaining
    return execution.values


def execute_child_block(child,
                        statements,
                        env):
    outcomes = child.block(statements, env)
    return ChildBlockExecution(outcomes, tuple(child.calls),
                               tuple(child.mapping_effects),
                               tuple(child.result.boundaries), child.remaining)


def merge_child_block(parent,
                      execution):
    parent.remaining = min(parent.remaining, execution.remaining)
    parent.calls.extend(execution.calls)
    parent.mapping_effects.extend(execution.mapping_effects)
    parent.result.boundaries.extend(execution.boundaries)
