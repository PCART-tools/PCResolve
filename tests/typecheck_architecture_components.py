## @package tests.typecheck_architecture_components
#  Strict probes exercise the actual internal state and factory contracts.

import ast

from pcresolve.flow.contracts import ChildSummaryFactory, RecursiveSummaryPort
from pcresolve.flow.model.results import FlowAnalysis, FunctionRef
from pcresolve.flow.transfer.call_expression_state import _CallExpressionState
from pcresolve.flow.transfer.summary import _Summary
from pcresolve.ownership.call_graph import ModuleCallGraph
from pcresolve.ownership.source_fact_cache import SingleFileFacts
from pcresolve.ownership.symbol_table import SymbolTable


def call_state(visitor: object, node: ast.Call, env: dict[str, object],
               location: tuple[int, ...]) -> _CallExpressionState:
    return _CallExpressionState(visitor, node, env, location)


def child_factory(summary: _Summary) -> ChildSummaryFactory:
    return summary._make_child_summary


def child_summary(summary: _Summary, result: FlowAnalysis, ref: FunctionRef,
                  node: ast.AST, remaining: int) -> RecursiveSummaryPort:
    factory = child_factory(summary)
    return factory(result, ref, node, remaining)


def cached_graph(facts: SingleFileFacts) -> ModuleCallGraph:
    return facts.visitor.module_cg


def cached_symbols(facts: SingleFileFacts) -> SymbolTable:
    return facts.visitor.symbols
