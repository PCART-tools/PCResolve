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


## Compose the transfer phases that build and query one function summary.
## 组合构建和查询单个函数摘要所使用的各转移阶段。
class _Summary(CallExpressionMixin, ValuesMixin, ClassEffectsMixin, CallEvidenceMixin, ExpressionsMixin, ContainersMixin, EffectsMixin, ContextManagersMixin, StatementsMixin):

    ## Initialize one summary from explicit analysis inputs.
    ## 使用显式的分析输入初始化单个摘要。
    #
    #  @param analyzer Flow analyzer providing texts, indexes and proof caches.
    #  @param result Analysis result receiving calls, returns and boundaries.
    #  @param ref Function identity represented by this summary.
    #  @param node Function syntax node whose body is evaluated.
    #  @param remaining Remaining budget for nested call analysis.
    #  @param receiver_class Optional class context for receiver-bound evaluation.
    #  @param incoming Optional incoming dependency facts keyed by parameter name.
    #  @return None
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
        # Source lines and span evidence depend only on the immutable source
        # generation; sharing them across summaries keeps one record per span
        # instead of one per summary that touches it.
        # 源码行与跨度证据只依赖不可变源码代次；跨摘要共享后每个跨度只保留一条记录。
        self.source_lines = self.analyzer._source_lines(ref.file_path)
        self.evidence_cache = self.analyzer._source_evidence_cache
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
