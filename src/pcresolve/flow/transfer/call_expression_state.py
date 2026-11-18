## @package pcresolve.flow.transfer.call_expression_state
#  Hold state for one call transfer.
#
#
#  Explicit internal state shared by the ordered call-transfer phases.
#  有序调用转移阶段共享的显式内部状态。



# A candidate identifies both the source-level function and its syntax.


## Per-call mutable facts shared by the ordered call-transfer phases.
## 有序调用转移阶段共享的单次调用可变事实。
## Intermediate fields are initialized by the phase that first establishes them.
## 中间字段由首次建立该事实的阶段初始化。
class _CallExpressionState:
    # Slots declare allowed shared fields; later phases establish their own values.
    __slots__ = (
        'node',
        'env',
        'allocation_candidates',
        'allocation_class',
        'binding',
        'bound_receiver',
        'bounded_targets',
        'builtin_status',
        'callable_incomplete',
        'callable_instance_fact',
        'callable_sources',
        'callee_classes',
        'canonical',
        'construction_candidates',
        'construction_safe',
        'constructor_class',
        'dispatch_kind',
        'name',
        'owner',
        'protocol',
        'receiver_sources',
        'receiver_values',
        'returned_field_receiver',
        'target',
        'descriptor_kind',
        'call',
        'call_id',
    )

    def __init__(self, node, env):
        self.node = node
        self.env = env
