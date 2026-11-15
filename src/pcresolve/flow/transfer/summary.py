## @package pcresolve.flow.transfer.summary
#  Query-local flow state assembled from focused transfer components.

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
import sys


class _Summary(CallExpressionMixin, ValuesMixin, ClassEffectsMixin, CallEvidenceMixin, ExpressionsMixin, ContainersMixin, EffectsMixin, ContextManagersMixin, StatementsMixin):
    def __init__(self, analyzer, result, ref, node, remaining, receiver_class=None,
                 incoming=None):
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
        self.incoming = incoming or {}


# Proof and context managers recursively construct the composed query summary.
for _module_name in (
        'summary_values', 'summary_class_effects', 'summary_call_evidence',
        'summary_expressions', 'summary_containers', 'summary_effects',
        'summary_context_managers', 'summary_statements'):
    setattr(sys.modules[__package__ + '.' + _module_name], '_Summary', _Summary)
