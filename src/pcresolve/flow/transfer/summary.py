## @package pcresolve.flow.transfer.summary
#  Query-local flow state assembled from focused transfer components.
#
#
#  Composes the transfer mixins for one function summary and creates child
#  summaries using explicit input and result state.
#  组合单个函数摘要使用的转移组件，并通过显式输入和结果状态创建子摘要。



import copy


from pcresolve.flow.transfer.call_expression import CallExpressionMixin
from pcresolve.flow.transfer.summary_values import ValuesMixin
from pcresolve.flow.transfer.summary_class_effects import ClassEffectsMixin
from pcresolve.flow.transfer.summary_call_evidence import CallEvidenceMixin
from pcresolve.flow.transfer.summary_expressions import ExpressionsMixin
from pcresolve.flow.transfer.summary_containers import ContainersMixin
from pcresolve.flow.transfer.summary_effects import EffectsMixin
from pcresolve.flow.transfer.summary_context_managers import ContextManagersMixin
from pcresolve.flow.transfer.summary_statements import StatementsMixin


class _Summary(CallExpressionMixin, ValuesMixin, ClassEffectsMixin, CallEvidenceMixin, ExpressionsMixin, ContainersMixin, EffectsMixin, ContextManagersMixin, StatementsMixin):

    def __init__(self, analyzer, result,
                 ref, node, remaining,
                 receiver_class = None,
                 incoming = None
                 ):
        self.analyzer, self.result, self.ref, self.node = analyzer, result, ref, node
        self.calls = []
        self.returns = []
        self.conditions = copy.deepcopy(getattr(node, '_flow_conditions', []))
        self.remaining = remaining
        self.evaluated_calls = set()
        self.loops = []
        self.yields = []
        self.source_lines = [line.encode('utf-8') for line in
                             self.analyzer.texts[ref.file_path].split('\n')]
        self.evidence_cache = {}
        self.mapping_effects = []
        self.cached_local_imports = []
        self.receiver_class = receiver_class
        self.normal_returns = []
        self.incomplete_return = False
        self.exit_kinds = set()
        self.context_managers = []
        self.context_execution = False
        self.context_cleanup_order = [0]
        self.outcomes = []
        self.modified_return_callables = set()
        self.incoming = dict(incoming or {})

    ## Create a child with fresh query state and the same source index.
    ## 使用相同源码索引创建拥有新查询状态的子摘要。
    #
    #  @param result Child analysis result receiving calls and boundaries.
    #  @param ref Function identity represented by the child summary.
    #  @param node Source function node evaluated by the child.
    #  @param remaining Remaining call-analysis budget.
    #  @param receiver_class Optional receiver class context.
    #  @param incoming Optional incoming value facts for the child.
    #  @return Fresh summary instance. Callers may explicitly share selected state.
    def _make_child_summary(self, result, ref,
                            node, remaining,
                            receiver_class = None,
                            incoming = None
                            ):
        return _Summary(self.analyzer, result, ref, node, remaining,
                        receiver_class=receiver_class, incoming=incoming)
