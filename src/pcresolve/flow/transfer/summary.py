## @package pcresolve.flow.transfer.summary
#  Query-local flow state assembled from focused transfer components.

import ast
import copy
from typing import Mapping, Optional, Sequence

from pcresolve.flow.transfer._summary_support import *
from pcresolve.flow.transfer.call_expression import CallExpressionMixin
from pcresolve.flow.transfer.summary_values import ValuesMixin
from pcresolve.flow.transfer.summary_class_effects import ClassEffectsMixin
from pcresolve.flow.transfer.summary_call_evidence import CallEvidenceMixin
from pcresolve.flow.transfer.summary_expressions import ExpressionsMixin
from pcresolve.flow.transfer.summary_containers import ContainersMixin
from pcresolve.flow.transfer.summary_effects import EffectsMixin
from pcresolve.flow.transfer.summary_context_managers import ContextManagersMixin
from pcresolve.flow.transfer.summary_statements import StatementsMixin
from pcresolve.flow.contracts import RecursiveSummaryPort, SummaryAnalyzerPort
from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef


class _Summary(CallExpressionMixin, ValuesMixin, ClassEffectsMixin, CallEvidenceMixin, ExpressionsMixin, ContainersMixin, EffectsMixin, ContextManagersMixin, StatementsMixin):
    def __init__(self, analyzer: SummaryAnalyzerPort, result: FlowAnalysis,
                 ref: FunctionRef, node: ast.AST, remaining: int,
                 receiver_class: Optional[FunctionRef] = None,
                 incoming: Optional[Mapping[str, Sequence[Mapping[str, object]]]] = None
                 ) -> None:
        self.analyzer, self.result, self.ref, self.node = analyzer, result, ref, node
        self.calls: list[FlowCall] = []
        self.returns: list[object] = []
        self.conditions: list[object] = copy.deepcopy(getattr(node, '_flow_conditions', []))
        self.remaining = remaining
        self.evaluated_calls: set[tuple[int, ...]] = set()
        self.loops: list[object] = []
        self.yields: list[object] = []
        self.source_lines: list[bytes] = [line.encode('utf-8') for line in
                             self.analyzer.texts[ref.file_path].split('\n')]
        self.evidence_cache: dict[object, object] = {}
        self.mapping_effects: list[object] = []
        self.cached_local_imports: list[object] = []
        self.receiver_class: Optional[FunctionRef] = receiver_class
        self.normal_returns: list[object] = []
        self.incomplete_return = False
        self.exit_kinds: set[str] = set()
        self.context_managers: list[object] = []
        self.context_execution = False
        self.context_cleanup_order: list[int] = [0]
        self.outcomes: list[object] = []
        self.modified_return_callables: set[tuple[str, str]] = set()
        self.incoming: dict[str, Sequence[Mapping[str, object]]] = dict(incoming or {})

    ## Create an isolated child using the same composed transfer behavior.
    ## 使用相同的组合转移行为创建隔离的子摘要。
    #
    #  @param result Child analysis result receiving calls and boundaries.
    #  @param ref Function identity represented by the child summary.
    #  @param node Source function node evaluated by the child.
    #  @param remaining Remaining call-analysis budget.
    #  @param receiver_class Optional receiver class context.
    #  @param incoming Optional incoming value facts for the child.
    #  @return Fresh summary instance with independent query-local state.
    def _make_child_summary(self, result: FlowAnalysis, ref: FunctionRef,
                            node: ast.AST, remaining: int,
                            receiver_class: Optional[FunctionRef] = None,
                            incoming: Optional[Mapping[str, Sequence[Mapping[str, object]]]] = None
                            ) -> RecursiveSummaryPort:
        return _Summary(self.analyzer, result, ref, node, remaining,
                        receiver_class=receiver_class, incoming=incoming)
