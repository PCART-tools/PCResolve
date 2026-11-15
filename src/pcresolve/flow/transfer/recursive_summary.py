## @package pcresolve.flow.transfer.recursive_summary
#  Typed construction and execution adapters for recursive summaries.

import ast
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from pcresolve.flow.contracts import ChildSummaryFactory, RecursiveSummaryPort
from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef


@dataclass(frozen=True)
class ChildExpressionExecution:
    values: Sequence[Mapping[str, object]]
    heap_updates: Mapping[str, object]
    remaining: int


@dataclass(frozen=True)
class ChildBlockExecution:
    outcomes: Sequence[object]
    calls: Sequence[FlowCall]
    mapping_effects: Sequence[object]
    boundaries: Sequence[object]
    remaining: int


def create_child_summary(factory: ChildSummaryFactory, result: FlowAnalysis,
                         ref: FunctionRef, node: ast.AST, remaining: int,
                         receiver_class: Optional[FunctionRef] = None,
                         incoming: Optional[Mapping[str, Sequence[Mapping[str, object]]]] = None
                         ) -> RecursiveSummaryPort:
    return factory(result, ref, node, remaining, receiver_class, incoming)


def evaluate_child_expression(child: RecursiveSummaryPort, node: ast.AST,
                              env: Mapping[str, object]) -> ChildExpressionExecution:
    values = child.expression(node, env)
    heap_updates = {key: value for key, value in env.items()
                    if key.startswith('$heap:')}
    return ChildExpressionExecution(values, heap_updates, child.remaining)


def execute_child_block(child: RecursiveSummaryPort,
                        statements: Sequence[ast.stmt],
                        env: Mapping[str, object]) -> ChildBlockExecution:
    outcomes = child.block(statements, env)
    return ChildBlockExecution(outcomes, tuple(child.calls),
                               tuple(child.mapping_effects),
                               tuple(child.result.boundaries), child.remaining)
