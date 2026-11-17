## @package pcresolve.flow.transfer.call_expression
#  Transfer of explicit call expressions for flow summaries.
#  数据流摘要中的显式调用表达式传播。

import ast
import builtins
import copy
from dataclasses import asdict

from pcresolve.flow.model.results import FlowCall, FunctionRef
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.callables.dispatch.conditional_constructor import signature_reference as conditional_constructor_signature
from pcresolve.flow.proofs.callables._constructor_binding import source_binding as constructor_source_binding
from pcresolve.flow.proofs.callables._callable_instance_binding import source_binding
from pcresolve.flow.proofs.callables._function_factory import factory_wrapper
from pcresolve.flow.proofs.callables._fresh_receiver import method_binding as fresh_method_binding, super_method_binding as fresh_super_method_binding
from pcresolve.flow.proofs.callables._fresh_receiver import recover_lookup_receiver as fresh_lookup_receiver
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified as namespace_unmodified
from pcresolve.flow.transfer._summary_support import _call_key, _unique
from pcresolve.flow.transfer.call_entry import (
    CallEntryMixin, CalleeResolution, ReceiverDispatchResult, CallDecorationResult,
    CallableBindingResult,
)
from pcresolve.flow.transfer.call_binding_state import (
    CallArgumentsBinding, CallArgumentValues, CallEffectsResult, has_invalid_binding, record_argument_binding,
    record_actual_values, record_protocol_values, unavailable_call_binding, unbound_default_arguments,
)


class CallExpressionMixin(CallEntryMixin):
    # Query-local state provided by the composed summary, not by each phase.

    ## Resolve the callee, binding and construction candidates.
    ## 解析被调对象、绑定关系和构造候选。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return Facts consumed by receiver dispatch and call-record construction.
    def _resolve_callee_and_construction(self, state):
        state.name = ast.unparse(state.node.func)
        state.binding = state.env.get(state.name.split('.')[0])
        state.builtin_status = (self.analyzer._builtin_name_status(self.ref, self.node, state.name, state.env)
                          if isinstance(state.node.func, ast.Name) and hasattr(builtins, state.name) else None)
        state.callable_sources = (self.expression(state.node.func, state.env)
                            if isinstance(state.node.func, ast.Subscript) else state.binding or [])
        state.protocol = getattr(state.node, '_flow_implicit_protocol', {})
        state.target = (getattr(state.node, '_flow_protocol_target', None) if state.protocol else
                  self.analyzer._resolve(self.ref, state.name) if state.binding is None else None)
        global_rebound = False
        global_declarations = []
        nominal_target = state.target
        if state.target and not state.protocol and '.' not in state.target[0].qualname:
            global_declarations = self.analyzer._module_global_declarations(state.target[0])
            global_rebound = bool(global_declarations)
            if global_rebound:
                state.target = None
        state.canonical = self.ref.module + '.' + state.name
        state.constructor_class = None
        state.allocation_class = None
        allocation_values = []
        state.allocation_candidates = []
        state.construction_safe = False
        state.callable_instance_fact = None
        state.bounded_targets = []
        state.callable_incomplete = global_rebound
        state.receiver_values = (self.expression(state.node.func.value, state.env)
                            if isinstance(state.node.func, ast.Attribute) else [])
        state.receiver_sources = self.materialize(state.receiver_values, state.env)
        state.returned_field_receiver = bool(state.receiver_values) and all(
            value.get('receiver_type_evidence') for value in state.receiver_values)
        state.bound_receiver = bool(state.protocol and state.target)
        state.dispatch_kind = 'receiver_type_evidence' if state.bound_receiver else None
        state.owner = self.ref.qualname.rpartition('.')[0]
        function_names = self.analyzer._definition_index.scopes(self.ref.module)
        state.callee_classes = self.class_values(state.binding, env=state.env) if state.binding and isinstance(state.node.func, ast.Name) else []
        state.construction_candidates = []
        if state.binding and isinstance(state.node.func, ast.Name) and not state.callee_classes:
            _phase_classes = self.class_values(state.binding, allow_incomplete=True, env=state.env)
            if _phase_classes and all(value.get('attribute_provenance') for value in _phase_classes):
                state.construction_candidates = [value for value in _phase_classes
                    if self.analyzer._ordinary_construction(FunctionRef(**value['class_type']))]
                if len(state.construction_candidates) != len(_phase_classes):
                    state.construction_candidates = [dict(value, value_incomplete=True)
                                               for value in state.construction_candidates]
                state.allocation_candidates = state.construction_candidates
                allocation_values = state.construction_candidates
        if state.target is None:
            if state.callee_classes:
                _phase_identities = {(value['module'], value['source'])
                              for value in state.callee_classes}
                _phase_class_target = None
                if len(_phase_identities) == 1:
                    _phase_module, _phase_qualname = next(iter(_phase_identities))
                    _phase_matches = self.analyzer._definition_index.find(
                        _phase_module, _phase_qualname, kind='class')
                    _phase_class_target = _phase_matches[0] if len(_phase_matches) == 1 else None
            elif state.binding is None:
                _phase_class_target = self.analyzer._resolve_class(self.ref, state.name)
                _phase_alias = state.name.split('.')[0]
                if (_phase_alias in self.analyzer.imports.get(self.ref.module, {})
                        and not self.analyzer._stable_import_name(
                            self.ref.module + '.' + _phase_alias)):
                    _phase_class_target = None
                if _phase_class_target and not self.analyzer._stable_import_name(
                        _phase_class_target[0].module + '.' + _phase_class_target[0].qualname):
                    _phase_class_target = None
            elif all(value.get('kind') == 'import' for value in state.binding):
                state.callee_classes = self.class_values([dict(value,
                    source=value['source'] + ('.' + state.name.split('.', 1)[1]
                        if '.' in state.name else '')) for value in state.binding])
                _phase_class_target = None
                _phase_identities = {(value['module'], value['source']) for value in state.callee_classes}
                if len(_phase_identities) == 1:
                    _phase_module, _phase_qualname = next(iter(_phase_identities))
                    _phase_matches = self.analyzer._definition_index.find(_phase_module, _phase_qualname, kind='class')
                    _phase_class_target = _phase_matches[0] if len(_phase_matches) == 1 else None
            else:
                _phase_class_target = None
            if _phase_class_target is not None:
                _phase_constructor = self.analyzer._constructor_target(_phase_class_target)
                state.constructor_class = _phase_class_target[0]
                state.construction_safe = self.analyzer._ordinary_construction(state.constructor_class)
                if _phase_constructor is not None:
                    state.target = _phase_constructor
                    state.bound_receiver = True
                    state.dispatch_kind = 'constructor'
                else:
                    state.dispatch_kind = 'constructor_unavailable'
                state.canonical = (state.constructor_class.module + '.' +
                             state.constructor_class.qualname)
        return CalleeResolution(function_names, nominal_target, allocation_values,
                                global_declarations, global_rebound)

    ## Resolve receiver-based, inherited, super and field dispatch.
    ## 解析基于接收者的继承、super 与字段分派。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param callee Facts established by callee resolution.
    #  @return Descriptor and allocation values consumed by later phases.
    def _resolve_receiver_dispatch(self, state, callee):
        allocation_values = callee.allocation_values
        field_evidence = None
        _phase_receiver_types = {tuple((value.get('class_type') or {}).get(key, '')
                          for key in ('module', 'qualname')) for value in state.receiver_values}
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and state.receiver_values and all(value.get('class_type')
                                            and not value.get('value_incomplete')
                                            and value.get('relation') == 'direct'
                                            and not value.get('projection')
                                            and not value.get('output_path')
                                            for value in state.receiver_values)
                and len(_phase_receiver_types) == 1):
            _phase_module, _phase_class_name = next(iter(_phase_receiver_types))
            _phase_matches = self.analyzer._definition_index.find(_phase_module, _phase_class_name + '.' + state.node.func.attr)
            _phase_candidate = _phase_matches[0] if len(_phase_matches) == 1 else self.analyzer._inherited_method(
                _phase_module, _phase_class_name, state.node.func.attr)
            if _phase_candidate is not None:
                state.target = _phase_candidate
                state.bound_receiver = False
                state.dispatch_kind = 'class_receiver_candidate'
        if (state.target is None and isinstance(state.node.func, ast.Attribute) and isinstance(state.node.func.value, ast.Name)
                and state.owner and state.owner not in callee.function_names
                and (self.node.args.posonlyargs or self.node.args.args)
                # Incoming instance facts take precedence over the method's
                # lexical owner, including incomplete/empty candidates.
                and not any('instance_type' in value or 'instance_candidates' in value
                            for value in state.receiver_values + state.receiver_sources)
                and state.receiver_sources and all(v['kind'] == 'parameter' and v['relation'] == 'direct'
                    and not v.get('value_incomplete')
                    and v['source'] == (self.node.args.posonlyargs + self.node.args.args)[0].arg
                    for v in state.receiver_sources)):
            _phase_matches = self.analyzer._definition_index.find(self.ref.module, state.owner + '.' + state.node.func.attr)
            if not _phase_matches:
                _phase_inherited = self.analyzer._inherited_method(self.ref.module, state.owner, state.node.func.attr)
                _phase_matches = [_phase_inherited] if _phase_inherited else []
            if len(_phase_matches) == 1:
                state.target = _phase_matches[0]
                state.bound_receiver = True
                state.dispatch_kind = 'instance_method'
        if (isinstance(state.node.func, ast.Attribute) and isinstance(state.node.func.value, ast.Attribute)
                and isinstance(state.node.func.value.value, ast.Name)
                and not getattr(self.node, 'decorator_list', [])):
            _phase_args = self.node.args.posonlyargs + self.node.args.args
            _phase_bases = state.env.get(state.node.func.value.value.id, [])
            if _phase_args and _phase_bases and all(v['kind'] == 'parameter' and v['source'] == _phase_args[0].arg
                                     and v['relation'] == 'direct' for v in _phase_bases):
                _phase_candidate = self.analyzer._field_candidate(self.ref, state.node.func.value.attr, state.node.func.attr)
                if _phase_candidate:
                    state.target, field_evidence = _phase_candidate
                    state.bound_receiver = True
                    state.dispatch_kind = 'field_method'
        _phase_is_zero_super = (isinstance(state.node.func, ast.Attribute)
                         and isinstance(state.node.func.value, ast.Call)
                         and isinstance(state.node.func.value.func, ast.Name)
                         and state.node.func.value.func.id == 'super'
                         and not state.node.func.value.args and not state.node.func.value.keywords)
        _phase_is_explicit_super = (isinstance(state.node.func, ast.Attribute)
            and isinstance(state.node.func.value, ast.Call)
            and isinstance(state.node.func.value.func, ast.Name)
            and state.node.func.value.func.id == 'super'
            and len(state.node.func.value.args) == 2
            and not state.node.func.value.keywords
            and isinstance(state.node.func.value.args[0], ast.Name)
            and isinstance(state.node.func.value.args[1], ast.Name)
            and state.node.func.value.args[0].id == state.owner.rpartition('.')[2])
        current_descriptor = self.analyzer._descriptor_kind(
            (self.ref, self.node))
        _phase_builtin_super = ('super' not in state.env
            and 'super' not in self.analyzer.imports.get(self.ref.module, {})
            and 'super' not in self.analyzer.module_bindings.get(self.ref.module, set())
            and self.analyzer._resolve(self.ref, 'super') is None
            and self.analyzer._resolve_class(self.ref, 'super') is None)
        _phase_current_class_known = (not _phase_is_explicit_super or (
            state.node.func.value.args[0].id not in state.env
            and self.analyzer._class_symbol(self.ref.module + '.' + state.owner)
            is not None))
        if ((_phase_is_zero_super or _phase_is_explicit_super) and state.owner and _phase_builtin_super
                and _phase_current_class_known):
            _phase_inherited = self.analyzer._inherited_method(
                self.ref.module, state.owner, state.node.func.attr,
                skip_current_members=True)
            _phase_args = self.node.args.posonlyargs + self.node.args.args
            _phase_receiver_name = (state.node.func.value.args[1].id
                             if _phase_is_explicit_super else _phase_args[0].arg if _phase_args else '')
            if (_phase_inherited and _phase_args and _phase_receiver_name == _phase_args[0].arg
                    and state.env.get(_phase_receiver_name)):
                state.target = _phase_inherited
                state.bound_receiver = state.node.func.attr != '__new__'
                state.dispatch_kind = ('super_new' if state.node.func.attr == '__new__'
                                 else 'super_method')
                state.receiver_values = state.env.get(_phase_receiver_name, [])
                state.receiver_sources = self.materialize(state.receiver_values, state.env)
            if (_phase_inherited is None and state.node.func.attr == '__new__'
                    and len(state.node.args) == 1 and not state.node.keywords):
                _phase_receiver = self.class_values(state.env.get(_phase_receiver_name, []), env=state.env)
                _phase_types = _unique([value.get('class_type') for value in _phase_receiver])
                if (_phase_receiver and all(_phase_types) and len(_phase_types) == 1
                        and not any(value.get('value_incomplete') for value in _phase_receiver)):
                    _phase_class_ref = FunctionRef(**_phase_types[0])
                    _phase_hierarchy = self.analyzer._class_mro(_phase_class_ref.module, _phase_class_ref.qualname)
                    _phase_owner_index = next((index for index, (ref, _) in enumerate(_phase_hierarchy or ())
                        if ref.module == self.ref.module and ref.qualname == state.owner), None)
                    _phase_writes, _phase_truncated = self.analyzer._class_binding_writes()
                    _phase_changed = _phase_truncated or any(attribute in ('__new__', '__class__', '__bases__', '*')
                        and any(written == ref for ref, _ in _phase_hierarchy or ())
                        for written, attribute, _, _, _ in _phase_writes)
                    if _phase_owner_index is not None and not _phase_changed and not any(
                            '__new__' in statement_scope_facts(cls.body).bound
                            or cls.keywords or cls.decorator_list
                            for ref, cls in _phase_hierarchy[_phase_owner_index + 1:]):
                        _phase_classes = self.class_values(self.expression(state.node.args[0], state.env),
                                                    allow_incomplete=True, env=state.env)
                        if _phase_classes:
                            if (len({(value['module'], value['source']) for value in _phase_classes}) == 1
                                    and not any(value.get('value_incomplete') for value in _phase_classes)):
                                state.allocation_class = FunctionRef(**_phase_classes[0]['class_type'])
                            allocation_values = _phase_classes
                            state.allocation_candidates = _phase_classes
                            state.dispatch_kind = 'builtin_allocation'
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and isinstance(state.node.func.value, ast.Name)
                and state.node.func.value.id == 'object' and state.node.func.attr == '__new__'
                and len(state.node.args) == 1 and not state.node.keywords
                and 'object' not in state.env
                and 'object' not in self.analyzer.imports.get(self.ref.module, {})
                and 'object' not in self.analyzer.module_bindings.get(self.ref.module, set())
                and self.analyzer._resolve(self.ref, 'object') is None
                and self.analyzer._resolve_class(self.ref, 'object') is None):
            _phase_classes = self.class_values(self.expression(state.node.args[0], state.env), allow_incomplete=True, env=state.env)
            if _phase_classes and len({(value['module'], value['source']) for value in _phase_classes}) == 1:
                if not any(value.get('value_incomplete') for value in _phase_classes):
                    state.allocation_class = FunctionRef(**_phase_classes[0]['class_type'])
                allocation_values = _phase_classes
                state.allocation_candidates = _phase_classes
                state.dispatch_kind = 'builtin_allocation'
            elif _phase_classes:
                state.allocation_candidates = _phase_classes
                allocation_values = _phase_classes
                state.dispatch_kind = 'builtin_allocation'
        _phase_possible_allocations = state.allocation_candidates
        state.allocation_candidates = [value for value in _phase_possible_allocations
            if (self.analyzer._ordinary_construction if state.construction_candidates
                else self.analyzer._explicit_object_allocation)(FunctionRef(**value['class_type']))]
        if len(state.allocation_candidates) != len(_phase_possible_allocations):
            state.allocation_candidates = [dict(value, value_incomplete=True) for value in state.allocation_candidates]
        return ReceiverDispatchResult(current_descriptor, allocation_values, field_evidence)

    ## Resolve callable-instance and fresh-receiver bindings.
    ## 解析可调用实例与新鲜接收者绑定。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return Fresh instance-method binding evidence for call-record construction.
    def _resolve_callable_binding(self, state):
        fresh_instance_method_bindings = []
        callable_instance_cause = None
        if state.allocation_class and not self.analyzer._explicit_object_allocation(state.allocation_class):
            state.allocation_class = None
        if not state.allocation_candidates and state.allocation_class is None and state.dispatch_kind == 'builtin_allocation':
            state.dispatch_kind = None
        state.receiver_values = fresh_lookup_receiver(self, state.node, state.receiver_values)
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and state.receiver_values and all((value.get('instance_type') and (
                                                not value.get('value_incomplete')
                                                or value.get('fresh_receiver_origin'))
                                            or value.get('instance_candidates'))
                                            and value.get('relation') == 'direct'
                                            and not value.get('projection')
                                            and not value.get('output_path')
                                            for value in state.receiver_values)):
            _phase_instance_types = {
                (identity['module'], identity['qualname'])
                for value in state.receiver_values
                for identity in ([value['instance_type']] if value.get('instance_type')
                                 else value.get('instance_candidates', []))}
            _phase_candidates = []
            _phase_complete_candidates = True
            for _phase_module, _phase_class_name in sorted(_phase_instance_types):
                _phase_candidate = self.analyzer._instance_method_candidate(
                    _phase_module, _phase_class_name, state.node.func.attr)
                if self.class_lookup_affected(state.receiver_values,
                        (state.node.func.attr, '__class__', '__bases__')):
                    _phase_candidate = None
                if _phase_candidate is None:
                    _phase_complete_candidates = False
                elif _phase_candidate not in _phase_candidates:
                    _phase_candidates.append(_phase_candidate)
            _phase_receiver_complete = all(not value.get('value_incomplete') for value in state.receiver_values)
            if _phase_complete_candidates and len(_phase_candidates) == 1:
                _phase_candidate = _phase_candidates[0]
                _phase_fresh_binding = (fresh_method_binding(
                    self, state.node, _phase_candidate, state.receiver_values) if not _phase_receiver_complete else None)
                if _phase_receiver_complete or _phase_fresh_binding is not None:
                    state.target = _phase_candidate
                    state.bound_receiver = True
                    state.dispatch_kind = ('returned_field_candidate'
                                     if state.returned_field_receiver else
                                     'receiver_type_evidence')
                    if _phase_fresh_binding is not None:
                        fresh_instance_method_bindings = [_phase_fresh_binding]
            elif _phase_candidates and (_phase_complete_candidates or any(
                    value.get('instance_candidates') for value in state.receiver_values)):
                state.bounded_targets = _phase_candidates
                state.dispatch_kind = ('bounded_alternatives' if _phase_receiver_complete
                                 and _phase_complete_candidates else 'receiver_unresolved')
        if state.target is None and state.binding and all(v['kind'] == 'import' for v in state.binding):
            _phase_imported = {v['source'] for v in state.binding}
            if len(_phase_imported) == 1:
                state.canonical = next(iter(_phase_imported)) + ('.' + state.name.split('.', 1)[1] if '.' in state.name else '')
                state.target = (self.analyzer._resolve_import_binding(state.canonical)
                          if not any(value.get('conditions')
                                     or value.get('import_modified')
                                     or value.get('import_incomplete')
                                     for value in state.binding) else None)
        elif state.binding is None:
            _phase_alias, _phase_dot, _phase_rest = state.name.partition('.')
            _phase_imported = self.analyzer.imports.get(self.ref.module, {}).get(_phase_alias)
            if _phase_imported:
                state.canonical = _phase_imported + (_phase_dot + _phase_rest if _phase_dot else '')
        if state.callable_sources and isinstance(state.node.func, (ast.Name, ast.Subscript)):
            _phase_candidates, _phase_complete = self.callable_targets(state.callable_sources)
            state.callable_incomplete = bool(_phase_candidates) and not _phase_complete
            if isinstance(state.node.func, ast.Subscript) and not isinstance(state.node.func.slice, ast.Constant):
                _phase_complete = False
            if _phase_complete and len(_phase_candidates) == 1:
                state.target = _phase_candidates[0]
                state.dispatch_kind = ('literal_dispatch' if isinstance(state.node.func, ast.Subscript)
                                 else 'incoming_callable' if any(
                                     value.get('callable_type') for value in state.callable_sources)
                                 else None)
            elif _phase_candidates:
                state.target = None
                state.bounded_targets = _phase_candidates
        if state.target is None:
            state.target, state.callable_instance_fact, callable_instance_cause = (
                self.analyzer._module_callable_instance(
                    self.ref, state.name, state.binding))
            if state.target is not None:
                state.bound_receiver = True
                state.dispatch_kind = 'callable_instance_candidate'
                _phase_assignment_evidence = self.evidence_at(
                    state.callable_instance_fact['module_ref'],
                    state.callable_instance_fact['assignment'])
                state.receiver_sources = [{
                    'kind': 'module_callable_instance',
                    'source': state.callable_instance_fact['qualified_name'],
                    'instance_type': asdict(
                        state.callable_instance_fact['class_ref']),
                    'relation': 'direct',
                    'evidence': [_phase_assignment_evidence, self.evidence(state.node)],
                    'conditions': list(self.conditions)}]
        decorated_target_candidate = False
        identity_decorator = None
        wrapper_forwarding_candidate = False
        decoration_facts = []
        body_preserved = False
        if (isinstance(state.node.func, ast.Attribute) and (
                any(value.get('class_type') and value.get('value_incomplete')
                    for value in state.receiver_values)
                or self.class_lookup_affected(state.receiver_values,
                    (state.node.func.attr, '__class__', '__bases__'))
                or state.node.func.attr.startswith('__') and not state.node.func.attr.endswith('__')
                and any(effect.get('attributes') for value in state.receiver_values
                        for effect in value.get('class_lookup_mutations', [])))):
            if (state.target and state.dispatch_kind == 'super_new' and state.receiver_values
                    and all(value.get('source_class_origin', {}).get('basis') == 'source_symbol'
                            for value in state.receiver_values)
                    and not self.class_lookup_affected(state.receiver_values,
                        (state.node.func.attr, '__class__', '__bases__'))
                    and any(value.get('cause') == 'unmodeled_call' for key, values in state.env.items()
                            if key.startswith('$class_origin_invalid:') for value in values)
                    and not any(value.get('cause') == 'write' for key, values in state.env.items()
                                if key.startswith('$class_origin_invalid:') for value in values)):
                self.result.boundaries.append({'reason': 'source_lookup_candidate',
                    'call_id': _call_key(self.ref.file_path, state.node),
                    'target': asdict(state.target[0]), 'evidence': self.evidence(state.node)})
            state.target, state.bounded_targets, state.bound_receiver, state.dispatch_kind = None, [], False, None
        state.descriptor_kind = self.analyzer._descriptor_kind(state.target) if state.target else None
        if state.target and getattr(state.target[1], 'decorator_list', []) and state.descriptor_kind is None:
            identity_decorator = self.analyzer._identity_decorator(state.target)
            decoration_facts = self.analyzer._binding_decoration_facts(state.target)
            body_preserved = (len(decoration_facts) == 1
                and decoration_facts[0]['body_binding_status'] == 'preserved')
            if identity_decorator is not None or body_preserved:
                decorated_target_candidate = body_preserved and identity_decorator is None
            elif (factory_wrapper(self.analyzer, state.target) or {}).get('forwarding') is not None:
                # Preserve only the nominal original body. This wrapper's
                # path condition requires concrete invocation arguments;
                # generic ownership/value-flow consumers retain a boundary.
                wrapper_forwarding_candidate = True
                decorated_target_candidate = True
            elif state.dispatch_kind in (
                    'constructor', 'instance_method', 'field_method',
                    'receiver_type_evidence', 'returned_field_candidate',
                    'super_method', 'super_new'):
                decorated_target_candidate = True
            else:
                _phase_replacement = self.analyzer._decorated_target(state.target)
                if _phase_replacement:
                    state.target = _phase_replacement
                    state.dispatch_kind = 'decorator_replacement'
                else:
                    state.target = None
        elif state.descriptor_kind == 'staticmethod':
            state.dispatch_kind = 'constructor' if state.constructor_class is not None else 'staticmethod'
        elif state.descriptor_kind == 'classmethod':
            state.bound_receiver = True
            state.dispatch_kind = 'constructor' if state.constructor_class is not None else 'classmethod'
        decoration = CallDecorationResult(
            identity_decorator, wrapper_forwarding_candidate,
            decorated_target_candidate, body_preserved, decoration_facts)
        return CallableBindingResult(
            fresh_instance_method_bindings, callable_instance_cause, decoration)

    ## Create the call record and capture its initial identity and evidence.
    ## 创建调用记录并记录初始身份与证据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param fresh_instance_method_bindings Facts returned by callable binding.
    #  @return Constructor values consumed by the effects phase.
    def _create_flow_call_record(self, state, fresh_instance_method_bindings,
                                 nominal_target, decoration, global_declarations,
                                 global_rebound):
        state.call_id = _call_key(self.ref.file_path, state.node)
        if state.target and (not namespace_unmodified(self.analyzer, self.ref.module + '.' + state.name)
                or not namespace_unmodified(self.analyzer,
                    state.target[0].module + '.' + state.target[0].qualname)):
            self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_source_namespace_binding', 'boundary_kind': 'uncertainty',
                'target': asdict(state.target[0]), 'evidence': self.evidence(state.node)})
        constructor_values = (self.expression(state.node.func, state.env)
            if state.constructor_class is not None and state.target
            and state.dispatch_kind == 'constructor' else [])
        state.call = FlowCall(state.call_id, self.ref, state.name, state.node.lineno, state.node.col_offset,
                        state.node.end_lineno, state.node.end_col_offset, state.target[0] if state.target else None)
        state.call.instance_method_bindings = fresh_instance_method_bindings
        state.call.implicit_protocol = copy.deepcopy(state.protocol)
        if global_rebound:
            self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'module_callable_binding_unconfirmed',
                'boundary_kind': 'uncertainty', 'nominal_target': asdict(nominal_target[0]),
                'declarations': [self.evidence_at(nominal_target[0], declaration)
                                 for declaration in global_declarations],
                'evidence': self.evidence(state.node)})
        if getattr(self.analyzer, '_conditional_source_state', False):
            _phase_contexts = [context for value in state.receiver_sources
                        for context in value.get('instance_candidate_contexts', [])] or state.receiver_sources
            _phase_common = (_phase_contexts[0].get('conditions', []) if _phase_contexts else [])
            state.call.conditions = _unique(copy.deepcopy(self.conditions) + [condition for condition in _phase_common
                if all(condition in value.get('conditions', []) for value in _phase_contexts)])
            _phase_parameters = self.node.args.posonlyargs + self.node.args.args
            _phase_ambient = state.env.get(_phase_parameters[0].arg, []) if _phase_parameters else []
            if _phase_ambient:
                state.call.conditions = _unique(state.call.conditions + [condition
                    for condition in _phase_ambient[0].get('conditions', [])
                    if all(condition in value.get('conditions', []) for value in _phase_ambient)
                    and condition.get('kind') == 'source_state_preserved'])
            for _phase_context in _phase_contexts:
                _phase_identity = _phase_context.get('instance_type')
                _phase_candidate = (self.analyzer._instance_method_candidate(_phase_identity['module'],
                    _phase_identity['qualname'], state.node.func.attr) if _phase_identity and isinstance(state.node.func, ast.Attribute)
                    else None)
                if _phase_candidate and _phase_candidate in state.bounded_targets:
                    state.call.candidate_paths.append({'target': asdict(_phase_candidate[0]), 'call_id': state.call.id,
                        'receiver_class': copy.deepcopy(_phase_identity),
                        'conditions': copy.deepcopy(_phase_context.get('conditions', []))})
        state.call.callable_sources = copy.deepcopy(state.callable_sources)
        if state.callable_incomplete:
            self.add_boundary('callable_identity_incomplete', state.node, state.env,
                state.callable_sources, call_id=state.call_id)
        if (isinstance(state.node.func, ast.Subscript) and state.callable_sources
                and not isinstance(state.node.func.slice, ast.Constant)):
            self.add_boundary('literal_dispatch_key_unknown', state.node, state.env,
                              state.callable_sources, call_id=state.call_id)
        if state.target:
            state.call.target_candidates = [asdict(state.target[0])]
        elif state.bounded_targets:
            state.call.target_candidates = [asdict(candidate[0])
                                      for candidate in state.bounded_targets]
        state.call.receiver_sources = state.receiver_sources
        state.call.receiver_type_evidence.extend({'kind': 'context_manager_enter_return',
            'instance_type': copy.deepcopy(value.get('instance_type')),
            'return_binding': copy.deepcopy(value['context_manager_return']),
            'evidence': copy.deepcopy(value.get('evidence', [])),
            'conditions': copy.deepcopy(value.get('conditions', [])),
            'basis': 'source_snapshot', 'runtime_target_confirmed': False}
            for value in state.receiver_values if value.get('context_manager_return'))
        _phase_class_binding = self.class_method_binding(state.node, state.target, state.receiver_values)
        if _phase_class_binding:
            state.call.class_method_bindings = [_phase_class_binding]
            if _phase_class_binding['status'] != 'source_bound':
                self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'class_method_binding_unconfirmed', 'boundary_kind': 'uncertainty',
                    'issues': copy.deepcopy(_phase_class_binding['issues']), 'evidence': self.evidence(state.node)})
        if (state.target and state.receiver_sources and (state.descriptor_kind == 'classmethod'
                or any(value.get('class_type') for value in state.receiver_sources))):
            self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_class_receiver_override_possible',
                'boundary_kind': 'assumption' if _phase_class_binding and _phase_class_binding['status'] == 'source_bound' else 'uncertainty',
                'binding_status': _phase_class_binding['status'] if _phase_class_binding else 'unconfirmed',
                'assumptions': copy.deepcopy(_phase_class_binding['assumptions']) if _phase_class_binding else [],
                'evidence': self.evidence(state.node)})
        if decoration.identity_decorator is not None:
            state.call.decorator_identity_evidence = [{
                'decorator': asdict(decoration.identity_decorator['decorator']),
                'parameter': decoration.identity_decorator['parameter'],
                'returns': [self.evidence_at(
                    decoration.identity_decorator['decorator'], returned)
                    for returned in decoration.identity_decorator['returns']]}]
            if (decoration.identity_decorator['effects_unmodeled'] and not (decoration.body_preserved
                    and decoration.decoration_facts[0].get('kind') == 'source_fresh_function_decoration')):
                self.result.boundaries.append({
                    'call_id': state.call_id, 'callee_name': state.name,
                    'reason': 'identity_decorator_effects_unmodeled',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence_at(
                        decoration.identity_decorator['decorator'],
                        decoration.identity_decorator['definition'])})
        if decoration.wrapper_forwarding_candidate:
            self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'identity_decorator_effects_unmodeled',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence_at(state.target[0], state.target[1])})
        if state.callable_instance_fact is not None:
            state.call.callable_instance_evidence = self.module_callable_evidence(
                state.callable_instance_fact, state.node)
            state.call.callable_instance_evidence['binding'] = source_binding(
                self, state.callable_instance_fact, state.target)
        if state.returned_field_receiver:
            state.call.receiver_type_evidence = _unique([
                dict(fact, receiver_call=self.evidence(state.node))
                for value in state.receiver_values
                for fact in value['receiver_type_evidence']])
        state.call.target_status = ('bounded_alternatives' if state.bounded_targets else
                              'constructor_unavailable' if state.construction_candidates else
                              'builtin_allocation' if state.allocation_class or state.allocation_candidates else
                              state.dispatch_kind if state.target and state.dispatch_kind else
                              'constructor_unavailable' if state.constructor_class else
                              'lexical_method_candidate' if state.target and state.bound_receiver else
                              'resolved' if state.target else 'receiver_unresolved' if isinstance(state.node.func, ast.Attribute)
                              else 'builtin_boundary' if state.builtin_status == 'confirmed_builtin'
                              else 'definition_unavailable')
        if (state.target is None and state.builtin_status in ('source_binding', 'unconfirmed')
                and state.name in ('dict', 'list', 'tuple', 'set', 'str', 'repr', 'bool', 'len', 'next')):
            self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'function': asdict(self.ref), 'reason': 'builtin_name_unconfirmed',
                'builtin_name_status': state.builtin_status, 'affected_scope': 'unknown',
                'affected_values': [], 'conditions': list(self.conditions),
                'evidence': self.evidence(state.node)})
        return constructor_values

    ## Finalize target status and attach bounded call metadata.
    ## 确定目标状态并附加有界调用元数据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return Whether the call is a literal string join, consumed by argument mapping.
    def _complete_call_target_metadata(self, state, current_descriptor,
                                       callable_instance_cause, decoration,
                                       field_evidence):
        if state.dispatch_kind == 'receiver_unresolved' and state.bounded_targets:
            state.call.target_status = 'receiver_unresolved'
            self.add_boundary('class_attribute_state_unknown', state.node, state.env,
                state.receiver_values, call_id=state.call_id)
        if state.callable_incomplete:
            state.call.target_status = 'definition_unavailable'
        if state.constructor_class is not None and not state.construction_safe:
            self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_construction', 'evidence': self.evidence(state.node)})
            if (self.analyzer._class_binding_write_cache is not None
                    and self.analyzer._class_binding_write_cache[1]):
                self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'constructor_binding_budget', 'evidence': self.evidence(state.node)})
            if state.target and state.target[1].name == '__new__':
                self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'constructor_initialization_unmodeled',
                    'phase': '__init__', 'evidence': self.evidence(state.node)})
        if state.allocation_class is not None or state.allocation_candidates and not state.construction_candidates:
            self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'builtin_allocator_source_unavailable',
                'evidence': self.evidence(state.node)})
        if field_evidence:
            state.call.target_status = 'constructor_field_candidate'
            self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'constructor_field_assumption', 'evidence': self.evidence(field_evidence)})
        if callable_instance_cause is not None:
            self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'module_callable_instance_unresolved',
                'cause': callable_instance_cause,
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence(state.node)})
        if state.callable_instance_fact is not None:
            _phase_callable_binding = state.call.callable_instance_evidence['binding']
            self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_callable_instance_override_possible',
                'boundary_kind': 'assumption' if _phase_callable_binding['status'] == 'source_bound' else 'uncertainty',
                'binding_status': _phase_callable_binding['status'],
                'assumptions': copy.deepcopy(_phase_callable_binding['assumptions']),
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence(state.node)})
        if (state.target and state.dispatch_kind in (
                'super_method', 'super_new', 'instance_method')
                and getattr(self.node, 'decorator_list', [])
                and current_descriptor not in ('classmethod', 'staticmethod')):
            self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'decorated_caller_semantics',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence(self.node)})
            _phase_facts = self.analyzer._binding_decoration_facts((self.ref, self.node))
            if len(_phase_facts) == 1 and _phase_facts[0]['body_binding_status'] == 'preserved':
                self.result.boundaries[-1].update(boundary_kind='assumption',
                    body_binding_status='preserved', function=asdict(self.ref),
                    assumptions=copy.deepcopy(_phase_facts[0]['assumptions']))
        if state.target and decoration.decorated_target_candidate:
            self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'decorated_target_candidate',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence_at(state.target[0], state.target[1])})
            _phase_facts = self.analyzer._binding_decoration_facts(state.target)
            if len(_phase_facts) == 1 and _phase_facts[0]['body_binding_status'] == 'preserved':
                self.result.boundaries[-1].update(boundary_kind='assumption',
                    body_binding_status='preserved', function=asdict(state.target[0]),
                    assumptions=copy.deepcopy(_phase_facts[0]['assumptions']))
        if state.target and state.owner and state.dispatch_kind in (
                'instance_method', 'super_method', 'super_new'):
            _phase_hierarchy = self.analyzer._class_mro(self.ref.module, state.owner)
            _phase_decorated_class = next(((ref, cls) for ref, cls in (_phase_hierarchy or ())
                                    if cls.decorator_list), None)
            if _phase_decorated_class is not None:
                self.result.boundaries.append({
                    'call_id': state.call_id, 'callee_name': state.name,
                    'reason': 'decorated_class_candidate',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': self.evidence_at(*_phase_decorated_class)})
        _phase_string_arity = {'split': (0, 2), 'rsplit': (0, 2),
                        'strip': (0, 1), 'lstrip': (0, 1), 'rstrip': (0, 1),
                        'startswith': (1, 3), 'endswith': (1, 3),
                        'partition': (1, 1), 'rpartition': (1, 1)}
        _phase_method = state.node.func.attr if isinstance(state.node.func, ast.Attribute) else ''
        _phase_limits = _phase_string_arity.get(_phase_method)
        _phase_string_protocol = (state.target is None and isinstance(state.node.func, ast.Attribute)
                           and isinstance(state.node.func.value, ast.Name)
                           and _phase_limits is not None and _phase_limits[0] <= len(state.node.args) <= _phase_limits[1]
                           and not state.node.keywords
                           and not any(isinstance(argument, ast.Starred)
                                       for argument in state.node.args)
                           and state.receiver_sources
                           and all(v.get('python_shape') == 'str'
                                   for v in state.receiver_sources))
        if _phase_string_protocol:
            state.call.target_status = 'python_protocol'
            state.call.argument_sources.append({'argument': {'receiver': True}, 'parameter': '$receiver',
                                          'sources': state.receiver_sources})
            if _phase_method in ('partition', 'rpartition'):
                state.call.return_dependencies = [
                    {'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                     'output_path': [index],
                     'evidence': [{'provenance':
                        'Guarded or trusted str partition result dependency'}],
                     'conditions': list(self.conditions)} for index in range(3)]
            else:
                state.call.return_dependencies = [{
                    'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                    'evidence': [{'provenance':
                        'Guarded str receiver dependency; builtin method implementation assumed'}],
                    'conditions': list(self.conditions)}]
                self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                                               'reason': 'string_subclass_override_possible'})
            if _phase_method in ('partition', 'rpartition'):
                self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                                               'reason': 'string_subclass_override_possible'})
        literal_join = (state.target is None and isinstance(state.node.func, ast.Attribute)
                        and isinstance(state.node.func.value, ast.Constant) and isinstance(state.node.func.value.value, str)
                        and state.node.func.attr == 'join' and len(state.node.args) == 1 and not state.node.keywords
                        and not isinstance(state.node.args[0], ast.Starred))
        if state.target and state.dispatch_kind == 'super_method':
            # The dedicated proof revalidates the exact builtin super()
            # receiver, MRO target and fresh-origin lineage itself. Do not
            # gate that proof on the generic receiver-binding flag: other
            # uncertainty in argument expansion can clear that flag even
            # when the super lookup remains statically exact.
            _phase_fresh = fresh_super_method_binding(self, state.node, state.target, state.receiver_values)
            if _phase_fresh is not None:
                state.call.instance_method_bindings = [_phase_fresh]
        if state.target and state.bound_receiver and state.dispatch_kind in (
                'instance_method', 'field_method', 'receiver_type_evidence',
                'returned_field_candidate'):
            _phase_fresh = fresh_method_binding(self, state.node, state.target, state.receiver_values)
            if _phase_fresh is not None:
                state.call.instance_method_bindings = [_phase_fresh]
            self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_method_override_possible',
                **({'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                    'assumptions': copy.deepcopy(_phase_fresh['assumptions'])} if _phase_fresh is not None else {})})
        if state.returned_field_receiver and (state.target or state.bounded_targets):
            self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_accessor_override_possible',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': self.evidence(state.node)})
        return literal_join

    ## Bind call arguments to formal parameters and callable contracts.
    ## 将调用实参与形参及可调用契约绑定。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return Signature, positional parameters and records for argument mapping.
    def _bind_call_parameters(self, state):
        _phase_params = state.target[1].args if state.target else None
        _phase_contract = self.analyzer.return_summaries.get(state.canonical) if state.target is None else None
        if (_phase_contract is None and state.target is None and state.name == 'isinstance'
                and state.builtin_status == 'confirmed_builtin' and len(state.node.args) == 2
                and not state.node.keywords and isinstance(state.node.args[0], ast.Name)
                and isinstance(state.node.args[1], ast.Name) and state.node.args[1].id == 'str'
                and self.analyzer._builtin_name_status(self.ref, self.node, 'str', state.env)
                    == 'confirmed_builtin'):
            _phase_functions, _phase_closed = self.callable_targets(state.env.get(state.node.args[0].id, []))
            if (_phase_functions and _phase_closed and all(not function.decorator_list
                    and '.' not in ref.qualname for ref, function in _phase_functions)):
                _phase_contract = {'parameters': ['object', 'classinfo'], 'returns': [],
                    'provenance': 'Closed source function object is not a builtin str'}
                state.call.target_status = 'python_protocol'
                state.call.implicit_protocol = {'kind': 'source_function_isinstance',
                    'type': 'str', 'result': False, 'evidence': self.evidence(state.node)}
        if (_phase_contract is None and state.target is None and state.builtin_status == 'confirmed_builtin'
                and state.name in ('str', 'repr', 'bool', 'len', 'list', 'tuple', 'set', 'callable')
                and state.canonical == self.ref.module + '.' + state.name
                and len(state.node.args) == 1 and not state.node.keywords
                and not isinstance(state.node.args[0], ast.Starred)):
            _phase_contract = {'parameters': ['object'], 'returns': [
                {'parameter': 'object', 'relation': 'derived'}],
                'provenance': 'Python builtin result dependency (not owner preservation)'}
            state.call.target_status = 'python_protocol'
            if state.name == 'callable':
                state.call.implicit_protocol = {'kind': 'builtin_exact_callability',
                    'builtin': 'callable', 'status': 'requires_exact_input',
                    'runtime_input_confirmed': False,
                    'precondition': {'argument': {'position': 0}, 'exact_types': [
                        'NoneType', 'bool', 'int', 'float', 'str', 'bytes',
                        'dict', 'list', 'tuple', 'set', 'frozenset']},
                    'result': False, 'dependency': 'input_object_type_only',
                    'completion': 'normal_return_if_precondition',
                    'effects': 'none_if_precondition', 'call_id': state.call.id,
                    'source_hash': self.analyzer.hashes[self.ref.file_path],
                    'evidence': self.evidence(state.node)}
            elif state.name == 'bool':
                state.call.implicit_protocol = {'kind': 'builtin_scalar_truth', 'builtin': 'bool',
                    'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                    'precondition': {'argument': {'position': 0},
                        'exact_types': ['NoneType', 'bool', 'int', 'float', 'str', 'bytes']},
                    'completion': 'normal_return_if_precondition',
                    'effects': 'none_if_precondition', 'call_id': state.call.id,
                    'source_hash': self.analyzer.hashes[self.ref.file_path],
                    'evidence': self.evidence(state.node)}
            elif state.name == 'len':
                state.call.implicit_protocol = {'kind': 'builtin_container_length', 'builtin': 'len',
                    'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                    'precondition': {'argument': {'position': 0},
                        'exact_types': ['dict', 'list', 'tuple', 'str', 'bytes',
                                        'set', 'frozenset']},
                    'completion': 'normal_return_if_precondition',
                    'effects': 'none_if_precondition', 'call_id': state.call.id,
                    'source_hash': self.analyzer.hashes[self.ref.file_path],
                    'evidence': self.evidence(state.node)}
        if (_phase_contract is None and state.target is None and state.builtin_status == 'confirmed_builtin' and state.name == 'next'
                and state.canonical == self.ref.module + '.next'
                and len(state.node.args) == 1 and not state.node.keywords
                and not isinstance(state.node.args[0], ast.Starred)):
            _phase_contract = {'parameters': ['iterator'], 'returns': [
                {'parameter': 'iterator', 'projection': ['*'], 'relation': 'direct'}],
                'provenance': 'Python next returns an element produced by its iterator'}
            state.call.target_status = 'python_protocol'
        if _phase_contract and (state.binding is None or all(v['kind'] == 'import' for v in state.binding)):
            _phase_params = ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in _phase_contract['parameters']],
                                   vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
            state.call.return_dependencies = [
                {'kind': 'parameter', 'source': d['parameter'], 'relation': d['relation'],
                 'projection': d.get('projection', []),
                 'evidence': [{'provenance': _phase_contract['provenance'], 'callable': state.canonical}], 'conditions': []}
                for d in _phase_contract.get('returns', [])]
        _phase_positional = _phase_params.posonlyargs + _phase_params.args if _phase_params else []
        _phase_instance_parameter = None
        if state.bound_receiver and state.target and _phase_positional:
            if state.dispatch_kind != 'constructor':
                state.call.argument_sources.append({
                    'argument': {'receiver': True},
                    'parameter': _phase_positional[0].arg,
                    'sources': state.receiver_sources})
                if (state.descriptor_kind is None and not state.target[1].decorator_list
                        and state.receiver_sources and all(value.get('instance_type')
                            for value in state.receiver_sources)):
                    _phase_instance_parameter = _phase_positional[0].arg
                    state.call.parameter_bindings.append({'argument': {'receiver': True},
                        'parameter': _phase_instance_parameter, 'status': 'exact',
                        'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'})
            _phase_positional = _phase_positional[1:]
        _phase_records = (self.bind_call_arguments(state.node, _phase_params, _phase_positional, state.call)
                          if _phase_params else unavailable_call_binding(state.node, state.call))
        _phase_invalid_binding = has_invalid_binding(bool(_phase_params), _phase_records)
        return CallArgumentsBinding(_phase_params, _phase_positional, _phase_records,
                                    _phase_instance_parameter, _phase_invalid_binding)

    ## Build per-argument binding records and propagate argument facts.
    ## 构建逐实参绑定记录并传播实参事实。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param binding Results established by the preceding binding phase.
    #  @param literal_join Metadata result established by target completion.
    #  @return Per-call argument values for effect and result phases.
    def _map_call_arguments(self, state, binding,
                            literal_join):
        arguments = CallArgumentValues()
        for _phase_record in binding.records:
            _phase_slot, _phase_arg = _phase_record['argument'], _phase_record['node']
            _phase_parameter, _phase_target_path = _phase_record['parameter'], _phase_record['target_path']
            record_argument_binding(state.call, _phase_record)
            if _phase_arg is None:
                continue
            _phase_raw_values = self.expression(_phase_arg, state.env)
            record_protocol_values(arguments, _phase_record, _phase_raw_values)
            _phase_raw_values = [dict(value, value_incomplete=True)
                if ((value.get('callable_type') or {}).get('module', value.get('module')),
                    (value.get('callable_type') or {}).get('qualname', value.get('source')))
                    in self.modified_return_callables else value for value in _phase_raw_values]
            record_actual_values(arguments, _phase_record, _phase_raw_values)
            _phase_values = self.marked(self.materialize(_phase_raw_values, state.env), _phase_arg)
            _phase_argument_record = {'argument': _phase_slot, 'parameter': _phase_parameter, 'sources': _phase_values}
            _phase_container = self.exact_container(_phase_raw_values, ('dict', 'list', 'tuple'), state.env)
            if _phase_container is not None and not _phase_target_path and not any(
                    isinstance(child, ast.Call) for argument in state.node.args
                    + [keyword.value for keyword in state.node.keywords] for child in ast.walk(argument)):
                _phase_argument_record['container_binding'] = {'status': 'exact',
                    'shape': _phase_container['container_shape'],
                    'source': _phase_container['source'],
                    'contents_unknown': bool(state.env.get(_phase_container['source'] + '$state')),
                    'evidence': [self.evidence(_phase_arg)], 'conditions': copy.deepcopy(self.conditions)}
            elif _phase_raw_values and not _phase_target_path and all(
                    value.get('kind') == 'parameter' and value.get('relation') == 'direct'
                    and value.get('container_binding', {}).get('status') == 'exact'
                    and not any(value.get(flag) for flag in ('projection', 'output_path', 'value_incomplete'))
                    for value in _phase_raw_values):
                _phase_incoming_bindings = [value['container_binding'] for value in _phase_raw_values]
                if all(value == _phase_incoming_bindings[0] for value in _phase_incoming_bindings):
                    _phase_forwarded = copy.deepcopy(_phase_incoming_bindings[0])
                    _phase_aliases = {name for name, facts in self.incoming.items() if any(
                        fact.get('container_binding', {}).get('source') == _phase_forwarded['source']
                        for fact in facts)}
                    if any(value.get('source') in _phase_aliases for previous in self.calls
                            for value in previous.receiver_sources + [value for item in previous.argument_sources
                                for value in item.get('sources', [])]):
                        _phase_forwarded['contents_unknown'] = True
                    _phase_argument_record['container_binding'] = _phase_forwarded
            _phase_literal = self.literal_fact(_phase_arg, state.env)
            if _phase_literal is not None:
                _phase_argument_record.update(literal=_phase_literal, value_evidence=[self.evidence(_phase_arg)])
            if _phase_target_path:
                _phase_argument_record['target_path'] = _phase_target_path
            state.call.argument_sources.append(_phase_argument_record)
            for _phase_value in _phase_values:
                state.call.argument_flows.append(dict(_phase_value, target_parameter=_phase_parameter,
                                                target_path=_phase_target_path, argument=_phase_slot,
                                                status='flow_found'))
                if _phase_value['kind'] == 'parameter':
                    state.call.parameter_flows.append(dict(_phase_value, source_parameter=_phase_value['source'],
                                                     target_parameter=_phase_parameter,
                                                     target_path=_phase_target_path,
                                                     argument=_phase_slot, status='flow_found'))
        _phase_fresh_super = (state.call.instance_method_bindings[0]
            if len(state.call.instance_method_bindings) == 1
            and state.call.instance_method_bindings[0].get('kind') == 'fresh_source_super_method'
            and state.call.instance_method_bindings[0].get('status') == 'source_bound'
            else None)
        _phase_receiver_parameters = (state.target[1].args.posonlyargs + state.target[1].args.args
            if state.target is not None else [])
        if (_phase_fresh_super is not None and _phase_receiver_parameters
                and _phase_fresh_super.get('call_id') == state.call.id
                and _phase_fresh_super.get('target') == asdict(state.target[0])
                and state.call.receiver_sources and all(
                    value.get('fresh_receiver_origin') == _phase_fresh_super.get('origin')
                    and value.get('relation') == 'direct'
                    and value.get('source') == _phase_fresh_super.get('origin', {}).get('parameter')
                    and not any(value.get(flag) for flag in (
                        'projection', 'output_path', 'attribute_provenance',
                        'import_modified', 'import_incomplete', 'value_incomplete'))
                    for value in state.call.receiver_sources)
                and not any(binding.get('argument') == {'receiver': True}
                    and binding.get('parameter') == _phase_receiver_parameters[0].arg
                    for binding in state.call.parameter_bindings)):
            state.call.parameter_bindings.append({'argument': {'receiver': True},
                'parameter': _phase_receiver_parameters[0].arg, 'status': 'exact',
                'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter',
                'basis': 'source_bound_super_method_wrapper'})
        if literal_join:
            state.call.target_status = 'python_protocol'
            state.call.argument_sources[0]['parameter'] = 'iterable'
            state.call.parameter_bindings[0].update(parameter='iterable', status='exact')
            for _phase_value in state.call.argument_flows + state.call.parameter_flows:
                _phase_value['target_parameter'] = 'iterable'
            state.call.return_dependencies = [{'kind': 'parameter', 'source': 'iterable', 'projection': ['*'],
                'relation': 'derived', 'evidence': [{'provenance': 'Python str.join iterable elements'}],
                'conditions': list(self.conditions)}]
        for _phase_param, _phase_default in unbound_default_arguments(
                state.node, binding, state.call.parameter_bindings):
            state.call.parameter_bindings.append({'argument': None, 'parameter': _phase_param.arg,
                                            'binding_kind': 'default', 'status': 'exact',
                                            'source_text': ast.unparse(_phase_default)})
            if state.binding and all(v['kind'] == 'callable' for v in state.binding):
                state.call.argument_sources.append({'argument': None, 'parameter': _phase_param.arg,
                    'sources': _unique([v for b in state.binding for v in b.get('defaults', {}).get(_phase_param.arg, [])])})
        return arguments

    ## Collect source-backed effects and receiver mutations.
    ## 收集有源码依据的效果与接收者变更。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param binding Binding result containing the implicit receiver parameter, if any.
    #  @param arguments Mutable values established by the argument mapping phase.
    #  @param constructor_values Values established with the call record.
    #  @return Binding validity and container result after applying effects.
    def _analyze_call_effects(self, state,
                              binding, arguments, constructor_values):
        _phase_invalid_binding = binding.invalid
        effective_name = state.name
        _phase_capture_values = {}
        if (state.constructor_class is not None and state.target
                and state.call.target_status == 'constructor'):
            _phase_fact = constructor_source_binding(self, state.node, state.constructor_class, state.target,
                constructor_values, self.class_origin_invalid(asdict(state.constructor_class), state.env)
                or self.class_lookup_affected([{'class_lookup_mutations':
                    self.class_lookup_effects(asdict(state.constructor_class), state.env)}],
                    ('__new__', '__init__', '__class__', '__bases__')))
            state.call.constructor_bindings = [_phase_fact]
            if _phase_fact['status'] == 'source_bound':
                _phase_parameter = _phase_fact['implicit_binding']['parameter']
                _phase_slot = copy.deepcopy(_phase_fact['implicit_binding']['argument'])
                _phase_sources = ([{'kind': 'constructor_instance', 'source': state.call.id,
                    'instance_type': asdict(state.constructor_class), 'relation': 'direct',
                    'evidence': [self.evidence(state.node)],
                    'conditions': copy.deepcopy(self.conditions)}]
                    if _phase_fact['phase'] == '__init__' else copy.deepcopy(constructor_values))
                if _phase_fact['phase'] == '__new__':
                    for _phase_value in _phase_sources:
                        _phase_value.setdefault('source_class_origin', {
                            'basis': 'source_symbol', 'class': asdict(state.constructor_class),
                            'evidence': copy.deepcopy(_phase_value.get('evidence', [])), 'call_context': []})
                state.call.argument_sources.insert(0, {'argument': _phase_slot, 'parameter': _phase_parameter,
                                                'sources': _phase_sources})
                state.call.parameter_bindings.insert(0, {'argument': _phase_slot, 'parameter': _phase_parameter,
                    'status': 'exact', 'binding_kind': 'implicit_receiver',
                    'destination_kind': 'parameter'})
                if self.implicit_keyword_conflict(state.call, _phase_parameter, _phase_slot,
                        {arg.arg for arg in state.target[1].args.posonlyargs}):
                    _phase_invalid_binding = True
                arguments.actual_values[_phase_parameter] = _phase_sources
                for _phase_value in _phase_sources:
                    state.call.argument_flows.append(dict(_phase_value, target_parameter=_phase_parameter,
                        argument=_phase_slot, status='flow_found'))
                self.result.boundaries.append({'call_id': state.call.id,
                    'reason': 'source_constructor_' + _phase_fact['phase'].strip('_') + '_binding',
                    'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                    'execution_scope': _phase_fact['execution_scope'],
                    'assumptions': copy.deepcopy(_phase_fact['assumptions']),
                    'evidence': self.evidence(state.node)})
            else:
                self.result.boundaries.append({'call_id': state.call.id,
                    'reason': 'constructor_binding_unconfirmed',
                    'issues': copy.deepcopy(_phase_fact['issues']), 'evidence': self.evidence(state.node)})
                _phase_conditional = conditional_constructor_signature(self, state.node, _phase_fact, state.call.id)
                if _phase_conditional is not None and state.call.binding_status != 'invalid':
                    _phase_conditional.update(call_id=state.call.id, call_evidence=self.evidence(state.node))
                    state.call.conditional_source_bindings = [_phase_conditional]
                    state.call.conditions = copy.deepcopy(_phase_conditional['conditions'])
                    self.result.boundaries.append({'call_id': state.call.id,
                        'reason': 'conditional_constructor_signature',
                        'boundary_kind': 'required_condition',
                        'condition': copy.deepcopy(_phase_conditional['conditions'][-1])})
        if binding.instance_parameter is not None:
            if self.implicit_keyword_conflict(state.call, binding.instance_parameter, {'receiver': True},
                    {arg.arg for arg in state.target[1].args.posonlyargs}):
                _phase_invalid_binding = True
            _phase_invalid_receivers = {(value.get('source'), repr(value.get('instance_type')))
                for values in state.env.values() for value in values
                if value.get('instance_type') and value.get('value_incomplete')}
            for _phase_argument in state.call.argument_sources:
                if _phase_argument.get('argument') == {'receiver': True}:
                    _phase_argument['sources'] = [dict(value, value_incomplete=True)
                        if (value.get('source'), repr(value.get('instance_type')))
                            in _phase_invalid_receivers else value for value in _phase_argument['sources']]
                    arguments.actual_values[binding.instance_parameter] = _phase_argument['sources']
        if (state.descriptor_kind == 'classmethod' and state.target and any(
                fact.get('status') == 'source_bound' for fact in state.call.class_method_bindings)):
            _phase_parameters = state.target[1].args.posonlyargs + state.target[1].args.args
            if _phase_parameters and self.implicit_keyword_conflict(state.call, _phase_parameters[0].arg,
                    {'receiver': True}, {arg.arg for arg in state.target[1].args.posonlyargs}):
                _phase_invalid_binding = True
        for _phase_argument in state.call.argument_sources:
            _phase_updated = []
            for _phase_value in _phase_argument.get('sources', []):
                if _phase_value.get('class_type'):
                    _phase_mutations = self.class_lookup_effects(_phase_value['class_type'], state.env)
                    if _phase_mutations:
                        _phase_value = dict(_phase_value, class_lookup_mutations=_unique(
                            _phase_value.get('class_lookup_mutations', []) + copy.deepcopy(_phase_mutations)))
                    if self.class_origin_invalid(_phase_value['class_type'], state.env):
                        _phase_value = dict(_phase_value, value_incomplete=True)
                _phase_updated.append(_phase_value)
            _phase_argument['sources'] = _phase_updated
        _phase_effects_complete = False
        if state.target:
            # Closure cells are read at invocation, after all argument expressions.
            for _phase_capture in self.analyzer._captures(*state.target):
                _phase_capture_values[_phase_capture] = copy.deepcopy(state.env.get(_phase_capture, []))
                _phase_record = {'capture': _phase_capture, 'sources': _phase_capture_values[_phase_capture],
                    'current_sources': copy.deepcopy(self.materialize(_phase_capture_values[_phase_capture], state.env))}
                _phase_container = self.exact_container(_phase_capture_values[_phase_capture], ('dict', 'list', 'tuple'), state.env)
                if _phase_container is not None:
                    _phase_record['container_binding'] = {'status': 'exact',
                        'shape': _phase_container['container_shape'], 'source': _phase_container['source'],
                        'contents_unknown': bool(state.env.get(_phase_container['source'] + '$state')),
                        'evidence': [self.evidence(state.node)], 'conditions': copy.deepcopy(self.conditions)}
                state.call.capture_bindings.append(_phase_record)
        _phase_selected_target = (self.analyzer._selected_definition(state.target,
            self.analyzer._incoming_facts(state.target, state.call)) if state.target else None)
        if state.target:
            state.call.conditional_returns = self.analyzer._guarded_object_returns(state.target)
            for _phase_fact in state.call.conditional_returns:
                _phase_values = self.container_values(arguments.actual_values.get(_phase_fact['parameter'], []))
                if (state.call.binding_status == 'complete' and _phase_values and all(
                        value.get('kind') == 'container'
                        and value.get('container_shape') in ('dict', 'list', 'tuple')
                        and value.get('relation') == 'direct' and not value.get('value_incomplete')
                        and not value.get('projection') and not value.get('output_path')
                        and value['source'] in state.env for value in _phase_values)
                        and len({value['source'] for value in _phase_values}) == 1):
                    _phase_fact.update(container_shape=_phase_values[0]['container_shape'],
                        object_source=_phase_values[0]['source'],
                        binding=copy.deepcopy(next(binding for binding in state.call.parameter_bindings
                            if binding.get('parameter') == _phase_fact['parameter'])),
                        input_evidence=_unique([evidence for value in _phase_values
                            for evidence in value.get('evidence', [])]))
        self.invalidate_attributes(state.env)
        if state.target and not _phase_invalid_binding and not getattr(state.node, '_flow_skip_effects', False):
            _phase_effects_complete = self.apply_effects(
                _phase_selected_target, arguments.actual_values, _phase_capture_values, state.call, state.env, state.node)
            _phase_scope = self.analyzer._scope_facts(_phase_selected_target[1])
            _phase_unmodeled = (_phase_scope.nonlocals & _phase_scope.bound) - {
                effect['target'] for effect in state.call.effects
                if effect.get('kind') == 'nonlocal_write' and effect.get('status') == 'exact'}
            if _phase_unmodeled:
                _phase_affected = [value for name in _phase_unmodeled for value in _phase_capture_values.get(name, [])]
                self.add_boundary('capture_binding_write_unmodeled', state.node, state.env, _phase_affected,
                                  call_id=state.call.id)
                for _phase_name in _phase_unmodeled:
                    # Preserve the prior downstream name semantics while keeping
                    # the original syntactic call name available to other phases.
                    effective_name = _phase_name
                    self.unknown_container_contents(_phase_capture_values.get(_phase_name, []), state.env)
                    state.env[_phase_name] = [dict(value, value_incomplete=True)
                                 for value in state.env.get(_phase_name, [])]
                _phase_effects_complete = False
        return CallEffectsResult(_phase_invalid_binding, self.container_call(
            state.node, state.receiver_values, state.call, state.env, arguments.protocol_values),
            _phase_effects_complete, _phase_selected_target, _phase_capture_values,
            arguments, effective_name)

    ## Resolve container, protocol and bounded-target result facts.
    ## 解析容器、协议及有界目标的结果事实。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param effects Result produced by the effects phase.
    #  @return Result facts, or None when return-source resolution must continue.
    def _resolve_container_and_protocol_results(
            self, state, effects
            ):
        container_result = effects.container_result
        if container_result is None and isinstance(state.node.func, ast.Attribute) and state.node.func.attr == 'copy':
            _phase_incoming_receiver = self.incoming_copy_receiver(state.node, state.receiver_values, state.call, state.env)
            if _phase_incoming_receiver is not None:
                container_result = self.container_call(state.node, _phase_incoming_receiver, state.call, state.env, effects.arguments.protocol_values)
        if state.target is None and container_result is None:
            self.inherited_setdefault(state.node, state.receiver_values, state.call, state.env)
        if state.target is None and container_result is None and isinstance(state.node.func, ast.Name):
            container_result = self.container_constructor(state.node, state.call, state.env, effects.arguments.protocol_values)
        if (state.target is None and not state.bounded_targets
                and state.call.target_status not in ('python_protocol', 'local_container_protocol',
                                              'builtin_allocation')):
            for _phase_values in effects.arguments.actual_values.values():
                self.invalidate_literals(_phase_values, state.env)
                _phase_candidates, _phase__ = self.callable_targets(_phase_values)
                self.modified_return_callables.update(
                    (candidate[0].module, candidate[0].qualname) for candidate in _phase_candidates)
                for _phase_reference in self.container_values(_phase_values):
                    if _phase_reference.get('kind') == 'container':
                        _phase_source = _phase_reference['source']
                        state.env[_phase_source] = [dict(value, value_incomplete=True)
                            if value.get('kind') == 'callable' or value.get('callable_type')
                            else value for value in state.env.get(_phase_source, [])]
                self.unknown_container_contents(_phase_values, state.env)
            self.unknown_container_contents(state.receiver_values, state.env)
        _phase_source_super = (effects.effective_name == 'super' and state.builtin_status == 'confirmed_builtin'
            and len(state.node.args) == 2 and not state.node.keywords
            and not any(isinstance(argument, ast.Starred) for argument in state.node.args)
            and all(known and not any(value.get('value_incomplete') for value in known)
                    for known in (self.class_values(values, env=state.env)
                                  for values in effects.arguments.actual_values.values())))
        _phase_preserved_classes = (self.class_attribute_effect(
            effects.selected_target, state.call, effects.capture_values, state.env, state.node)
            if effects.selected_target and not effects.invalid_binding
            and not getattr(state.node, '_flow_skip_effects', False) else [])
        if not effects.effects_complete and not _phase_source_super and state.call.target_status not in (
                'python_protocol', 'local_container_protocol', 'builtin_allocation'):
            self.invalidate_instance_receivers(
                [value for values in effects.arguments.actual_values.values() for value in values]
                + state.receiver_values
                + [value for values in effects.capture_values.values() for value in values], state.env)
            self.invalidate_class_origins(
                [value for value in [value for values in effects.arguments.actual_values.values() for value in values]
                + state.receiver_values
                + [value for values in effects.capture_values.values() for value in values]
                 if value.get('class_type') not in _phase_preserved_classes], state.env, state.call)
        self.calls.append(state.call)
        if effects.invalid_binding:
            return []
        if (getattr(self.analyzer, '_conditional_source_state', False) and state.call.target is not None
                and state.call.target_status in ('super_new', 'super_method', 'classmethod')):
            _phase_required = [condition for condition in state.call.conditions
                        if condition.get('kind') == 'source_state_preserved']
            if _phase_required:
                state.call.conditional_source_bindings = [{'kind': 'conditional_source_lookup',
                    'status': 'required', 'target': asdict(state.call.target), 'call_id': state.call.id,
                    'call_evidence': self.evidence(state.node), 'conditions': copy.deepcopy(state.call.conditions),
                    'receiver_classes': _unique([value['class_type'] for value in state.receiver_sources
                        if value.get('class_type')]), 'runtime_target_confirmed': False,
                    'source_hashes': dict(self.analyzer.hashes), 'feasibility': 'not_proven'}]
        if container_result is not None:
            return container_result
        return None

    ## Assemble the call result sources and their evidence.
    ## 组装调用结果来源及其证据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @param effects Result produced by the effects phase.
    #  @return Resolved call-result facts, possibly empty.
    def _resolve_return_sources(self, state, effects,
                                allocation_values):
        _phase_result_value = {'kind': 'call_result', 'source': state.call_id,
                        'relation': 'direct',
                        'evidence': [self.evidence(state.node)],
                        'conditions': list(self.conditions)}
        if any(effect.get('kind') == 'mapping_remainder' and effect.get('return_path')
               for effect in state.call.effects):
            return state.call.result_sources
        _phase_returned_object = self.returned_container(
            effects.selected_target, state.call, effects.arguments.actual_values, state.env, state.node, effects.effects_complete)
        if _phase_returned_object is not None:
            _phase_result_value['container_object'] = _phase_returned_object
            _phase_result_value['object_only'] = True
            _phase_result_value['conditions'] = _unique(_phase_result_value['conditions'] +
                _phase_returned_object.get('conditions', []))
            _phase_result_value['evidence'] = _unique(_phase_result_value['evidence'] +
                _phase_returned_object.pop('evidence'))
            state.call.result_sources = [_phase_result_value]
            return [_phase_result_value]
        if effects.effects_complete and state.call.result_sources:
            return [_phase_result_value] + state.call.result_sources
        if state.constructor_class is not None and state.construction_safe:
            _phase_result_value['instance_type'] = asdict(state.constructor_class)
            _phase_mutations = self.class_lookup_effects(asdict(state.constructor_class), state.env)
            if _phase_mutations:
                _phase_result_value['class_lookup_mutations'] = copy.deepcopy(_phase_mutations)
            _phase_result_value['evidence'] = _unique(_phase_result_value['evidence'] + [
                evidence for value in state.callee_classes
                for evidence in value.get('evidence', [])])
            state.call.result_sources = [_phase_result_value]
        elif state.allocation_class is not None:
            _phase_result_value['instance_type'] = asdict(state.allocation_class)
            _phase_result_value['evidence'] = _unique(_phase_result_value['evidence'] + [
                evidence for value in allocation_values
                for evidence in value.get('evidence', [])])
            state.call.result_sources = [_phase_result_value]
            _phase_result_value['attribute_provenance'] = _unique([
                fact for value in allocation_values for fact in value.get('attribute_provenance', [])])
            _phase_result_value['conditions'] = _unique(_phase_result_value['conditions'] + [
                condition for value in allocation_values for condition in value.get('conditions', [])])
        elif state.allocation_candidates:
            _phase_result_value.update(instance_candidates=_unique([
                value['class_type'] for value in state.allocation_candidates]),
                value_incomplete=any(value.get('value_incomplete') for value in state.allocation_candidates),
                attribute_provenance=_unique([fact for value in state.allocation_candidates
                    for fact in value.get('attribute_provenance', [])]),
                conditions=_unique(_phase_result_value['conditions'] + [condition
                    for value in state.allocation_candidates for condition in value.get('conditions', [])]),
                evidence=_unique(_phase_result_value['evidence'] + [evidence
                    for value in state.allocation_candidates for evidence in value.get('evidence', [])]))
            state.call.result_sources = [_phase_result_value]
            if getattr(self.analyzer, '_conditional_source_state', False):
                _phase_result_value['instance_candidate_contexts'] = [
                    {'instance_type': copy.deepcopy(value['class_type']),
                     'conditions': copy.deepcopy(value.get('conditions', []))}
                    for value in state.allocation_candidates]
        elif (state.target and state.dispatch_kind == 'instance_method'
              and isinstance(state.node.func, ast.Attribute)
              and isinstance(state.node.func.value, ast.Name)
              and state.call.binding_status == 'complete'):
            _phase_field_types = self.analyzer._returned_field_instances(state.target)
            if _phase_field_types:
                _phase_values = []
                for _phase_item in _phase_field_types:
                    _phase_fact = {'field': _phase_item['field'],
                            'instance_type': _phase_item['instance_type'],
                            'assignment': self.evidence_at(
                                _phase_item['assignment_ref'], _phase_item['assignment_node']),
                            'returns': [self.evidence_at(_phase_item['return_ref'], path)
                                        for path in _phase_item['return_nodes']],
                            'accessor_call': self.evidence(state.node)}
                    state.call.receiver_type_evidence.append(_phase_fact)
                    _phase_values.append(dict(_phase_result_value,
                        instance_type=_phase_item['instance_type'],
                        receiver_type_evidence=[_phase_fact],
                        evidence=_phase_result_value['evidence'] +
                                 [_phase_fact['assignment']] + _phase_fact['returns']))
                return _phase_values
        return [_phase_result_value]
