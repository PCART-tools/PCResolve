## @package pcresolve.flow.transfer.call_expression_state
#  Explicit internal state shared by the ordered call-transfer phases.
#  有序调用转移阶段共享的显式内部状态。

import ast
from dataclasses import dataclass, field


## Per-call mutable facts shared by the ordered call-transfer phases.
## 有序调用转移阶段共享的单次调用可变事实。
## Intermediate fields are initialized by the phase that first establishes them.
## 中间字段由首次建立该事实的阶段初始化。
@dataclass(eq=False, repr=False)
class _CallExpressionState:
    self: object
    node: ast.Call
    env: dict[str, object]
    location: tuple[int, ...]
    return_value: object = None
    fresh_instance_method_bindings: list[object] = field(default_factory=list)

    # Callee binding and construction candidates.
    alias: object = field(init=False, repr=False)
    allocation_candidates: object = field(init=False, repr=False)
    allocation_class: object = field(init=False, repr=False)
    allocation_values: object = field(init=False, repr=False)
    binding: object = field(init=False, repr=False)
    bound_receiver: object = field(init=False, repr=False)
    bounded_targets: object = field(init=False, repr=False)
    builtin_status: object = field(init=False, repr=False)
    callable_incomplete: object = field(init=False, repr=False)
    callable_instance_cause: object = field(init=False, repr=False)
    callable_instance_fact: object = field(init=False, repr=False)
    callable_sources: object = field(init=False, repr=False)
    callee_classes: object = field(init=False, repr=False)
    canonical: object = field(init=False, repr=False)
    class_target: object = field(init=False, repr=False)
    classes: object = field(init=False, repr=False)
    construction_candidates: object = field(init=False, repr=False)
    construction_safe: object = field(init=False, repr=False)
    constructor: object = field(init=False, repr=False)
    constructor_class: object = field(init=False, repr=False)
    dispatch_kind: object = field(init=False, repr=False)
    field_evidence: object = field(init=False, repr=False)
    function_names: object = field(init=False, repr=False)
    global_declarations: object = field(init=False, repr=False)
    global_rebound: object = field(init=False, repr=False)
    identities: object = field(init=False, repr=False)
    matches: object = field(init=False, repr=False)
    module: object = field(init=False, repr=False)
    name: object = field(init=False, repr=False)
    nominal_target: object = field(init=False, repr=False)
    owner: object = field(init=False, repr=False)
    protocol: object = field(init=False, repr=False)
    qualname: object = field(init=False, repr=False)
    receiver_sources: object = field(init=False, repr=False)
    receiver_values: object = field(init=False, repr=False)
    returned_field_receiver: object = field(init=False, repr=False)
    target: object = field(init=False, repr=False)

    # Receiver, inheritance and super dispatch.
    args: object = field(init=False, repr=False)
    bases: object = field(init=False, repr=False)
    builtin_super: object = field(init=False, repr=False)
    candidate: object = field(init=False, repr=False)
    changed: object = field(init=False, repr=False)
    class_name: object = field(init=False, repr=False)
    class_ref: object = field(init=False, repr=False)
    current_class_known: object = field(init=False, repr=False)
    current_descriptor: object = field(init=False, repr=False)
    hierarchy: object = field(init=False, repr=False)
    inherited: object = field(init=False, repr=False)
    is_explicit_super: object = field(init=False, repr=False)
    is_zero_super: object = field(init=False, repr=False)
    owner_index: object = field(init=False, repr=False)
    possible_allocations: object = field(init=False, repr=False)
    receiver: object = field(init=False, repr=False)
    receiver_name: object = field(init=False, repr=False)
    receiver_types: object = field(init=False, repr=False)
    truncated: object = field(init=False, repr=False)
    types: object = field(init=False, repr=False)
    writes: object = field(init=False, repr=False)

    # Fresh receiver and callable binding.
    assignment_evidence: object = field(init=False, repr=False)
    body_preserved: object = field(init=False, repr=False)
    candidates: object = field(init=False, repr=False)
    complete: object = field(init=False, repr=False)
    complete_candidates: object = field(init=False, repr=False)
    decorated_target_candidate: object = field(init=False, repr=False)
    decoration_facts: object = field(init=False, repr=False)
    descriptor_kind: object = field(init=False, repr=False)
    dot: object = field(init=False, repr=False)
    fresh_binding: object = field(init=False, repr=False)
    identity_decorator: object = field(init=False, repr=False)
    imported: object = field(init=False, repr=False)
    instance_types: object = field(init=False, repr=False)
    receiver_complete: object = field(init=False, repr=False)
    replacement: object = field(init=False, repr=False)
    rest: object = field(init=False, repr=False)
    wrapper_forwarding_candidate: object = field(init=False, repr=False)

    # Call identity and record construction.
    ambient: object = field(init=False, repr=False)
    call: object = field(init=False, repr=False)
    call_id: object = field(init=False, repr=False)
    class_binding: object = field(init=False, repr=False)
    common: object = field(init=False, repr=False)
    constructor_values: object = field(init=False, repr=False)
    context: object = field(init=False, repr=False)
    contexts: object = field(init=False, repr=False)
    identity: object = field(init=False, repr=False)
    parameters: object = field(init=False, repr=False)

    # Target status and call metadata.
    callable_binding: object = field(init=False, repr=False)
    decorated_class: object = field(init=False, repr=False)
    facts: object = field(init=False, repr=False)
    fresh: object = field(init=False, repr=False)
    limits: object = field(init=False, repr=False)
    literal_join: object = field(init=False, repr=False)
    method: object = field(init=False, repr=False)
    string_arity: object = field(init=False, repr=False)
    string_protocol: object = field(init=False, repr=False)

    # Formal parameters and call binding.
    actual_values: object = field(init=False, repr=False)
    capture_values: object = field(init=False, repr=False)
    closed: object = field(init=False, repr=False)
    contract: object = field(init=False, repr=False)
    functions: object = field(init=False, repr=False)
    instance_parameter: object = field(init=False, repr=False)
    invalid_binding: object = field(init=False, repr=False)
    params: object = field(init=False, repr=False)
    positional: object = field(init=False, repr=False)
    records: object = field(init=False, repr=False)

    # Per-argument binding and propagation.
    aliases: object = field(init=False, repr=False)
    arg: object = field(init=False, repr=False)
    argument_record: object = field(init=False, repr=False)
    binding_record: object = field(init=False, repr=False)
    container: object = field(init=False, repr=False)
    default: object = field(init=False, repr=False)
    defaults: object = field(init=False, repr=False)
    forwarded: object = field(init=False, repr=False)
    fresh_super: object = field(init=False, repr=False)
    incoming_bindings: object = field(init=False, repr=False)
    literal: object = field(init=False, repr=False)
    param: object = field(init=False, repr=False)
    parameter: object = field(init=False, repr=False)
    possibly_expanded: object = field(init=False, repr=False)
    protocol_values: object = field(init=False, repr=False)
    raw_values: object = field(init=False, repr=False)
    receiver_parameters: object = field(init=False, repr=False)
    record: object = field(init=False, repr=False)
    slot: object = field(init=False, repr=False)
    supplied: object = field(init=False, repr=False)
    target_path: object = field(init=False, repr=False)
    unknown_keywords: object = field(init=False, repr=False)
    unknown_positions: object = field(init=False, repr=False)
    value: object = field(init=False, repr=False)
    values: object = field(init=False, repr=False)

    # Source-backed effects and mutations.
    affected: object = field(init=False, repr=False)
    argument: object = field(init=False, repr=False)
    capture: object = field(init=False, repr=False)
    conditional: object = field(init=False, repr=False)
    container_result: object = field(init=False, repr=False)
    effects_complete: object = field(init=False, repr=False)
    fact: object = field(init=False, repr=False)
    invalid_receivers: object = field(init=False, repr=False)
    mutations: object = field(init=False, repr=False)
    scope: object = field(init=False, repr=False)
    selected_target: object = field(init=False, repr=False)
    sources: object = field(init=False, repr=False)
    unmodeled: object = field(init=False, repr=False)
    updated: object = field(init=False, repr=False)

    # Container and protocol result resolution.
    _: object = field(init=False, repr=False)
    incoming_receiver: object = field(init=False, repr=False)
    preserved_classes: object = field(init=False, repr=False)
    reference: object = field(init=False, repr=False)
    required: object = field(init=False, repr=False)
    source: object = field(init=False, repr=False)
    source_super: object = field(init=False, repr=False)

    # Return-source construction.
    field_types: object = field(init=False, repr=False)
    item: object = field(init=False, repr=False)
    result_value: object = field(init=False, repr=False)
    returned_object: object = field(init=False, repr=False)
