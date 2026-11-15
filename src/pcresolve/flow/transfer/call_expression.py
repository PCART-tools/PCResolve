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
from pcresolve.flow.proofs.callables._fresh_receiver import (method_binding as fresh_method_binding,
    super_method_binding as fresh_super_method_binding, incoming_origin as fresh_incoming_origin)
from pcresolve.flow.proofs.callables._fresh_receiver import recover_lookup_receiver as fresh_lookup_receiver
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified as namespace_unmodified
from pcresolve.flow.transfer._summary_support import _call_key, _call_span, _unique
from pcresolve.flow.transfer.call_expression_state import _CallExpressionState


class CallExpressionMixin:
    ## Evaluate a call using the summary's bounded source and flow context.
    ## 使用摘要的有界源码与数据流上下文分析调用。
    def call_expression(self, node, env):
        location = _call_span(node)
        if location not in self.evaluated_calls and self.analyzer._class_return_stack:
            if self.analyzer._fact_calls <= 0:
                self.result.boundaries.append({'function': asdict(self.ref),
                    'reason': 'class_return_budget', 'evidence': self.evidence(node)})
                return []
            self.analyzer._fact_calls -= 1
        if location not in self.evaluated_calls and self.remaining <= 0:
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'budget_exceeded', 'evidence': self.evidence(node)})
            return []
        if location not in self.evaluated_calls:
            self.remaining -= 1
            self.evaluated_calls.add(location)
        state = _CallExpressionState(self=self, node=node, env=env, location=location)
        if self._resolve_callee_and_construction(state):
            return state.return_value
        if self._resolve_receiver_dispatch(state):
            return state.return_value
        if self._resolve_callable_binding(state):
            return state.return_value
        if self._create_flow_call_record(state):
            return state.return_value
        if self._complete_call_target_metadata(state):
            return state.return_value
        if self._bind_call_parameters(state):
            return state.return_value
        if self._map_call_arguments(state):
            return state.return_value
        if self._analyze_call_effects(state):
            return state.return_value
        if self._resolve_container_and_protocol_results(state):
            return state.return_value
        if self._resolve_return_sources(state):
            return state.return_value
        return state.return_value

    ## Resolve the callee, binding and construction candidates.
    ## 解析被调对象、绑定关系和构造候选。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _resolve_callee_and_construction(self, state):
        state.name = ast.unparse(state.node.func)
        state.binding = state.env.get(state.name.split('.')[0])
        state.builtin_status = (state.self.analyzer._builtin_name_status(state.self.ref, state.self.node, state.name, state.env)
                          if isinstance(state.node.func, ast.Name) and hasattr(builtins, state.name) else None)
        state.callable_sources = (state.self.expression(state.node.func, state.env)
                            if isinstance(state.node.func, ast.Subscript) else state.binding or [])
        state.protocol = getattr(state.node, '_flow_implicit_protocol', {})
        state.target = (getattr(state.node, '_flow_protocol_target', None) if state.protocol else
                  state.self.analyzer._resolve(state.self.ref, state.name) if state.binding is None else None)
        state.global_rebound = False
        state.global_declarations = []
        state.nominal_target = state.target
        if state.target and not state.protocol and '.' not in state.target[0].qualname:
            state.global_declarations = state.self.analyzer._module_global_declarations(state.target[0])
            state.global_rebound = bool(state.global_declarations)
            if state.global_rebound:
                state.target = None
        state.canonical = state.self.ref.module + '.' + state.name
        state.constructor_class = None
        state.allocation_class = None
        state.allocation_values = []
        state.allocation_candidates = []
        state.construction_safe = False
        state.callable_instance_fact = None
        state.callable_instance_cause = None
        state.bounded_targets = []
        state.callable_incomplete = state.global_rebound
        state.receiver_values = (state.self.expression(state.node.func.value, state.env)
                            if isinstance(state.node.func, ast.Attribute) else [])
        state.receiver_sources = state.self.materialize(state.receiver_values, state.env)
        state.returned_field_receiver = bool(state.receiver_values) and all(
            value.get('receiver_type_evidence') for value in state.receiver_values)
        state.bound_receiver = bool(state.protocol and state.target)
        state.dispatch_kind = 'receiver_type_evidence' if state.bound_receiver else None
        state.field_evidence = None
        state.owner = state.self.ref.qualname.rpartition('.')[0]
        state.function_names = state.self.analyzer._definition_index.scopes(state.self.ref.module)
        state.callee_classes = state.self.class_values(state.binding, env=state.env) if state.binding and isinstance(state.node.func, ast.Name) else []
        state.construction_candidates = []
        if state.binding and isinstance(state.node.func, ast.Name) and not state.callee_classes:
            state.classes = state.self.class_values(state.binding, allow_incomplete=True, env=state.env)
            if state.classes and all(value.get('attribute_provenance') for value in state.classes):
                state.construction_candidates = [value for value in state.classes
                    if state.self.analyzer._ordinary_construction(FunctionRef(**value['class_type']))]
                if len(state.construction_candidates) != len(state.classes):
                    state.construction_candidates = [dict(value, value_incomplete=True)
                                               for value in state.construction_candidates]
                state.allocation_candidates = state.construction_candidates
                state.allocation_values = state.construction_candidates
        if state.target is None:
            if state.callee_classes:
                state.identities = {(value['module'], value['source'])
                              for value in state.callee_classes}
                state.class_target = None
                if len(state.identities) == 1:
                    state.module, state.qualname = next(iter(state.identities))
                    state.matches = state.self.analyzer._definition_index.find(
                        state.module, state.qualname, kind='class')
                    state.class_target = state.matches[0] if len(state.matches) == 1 else None
            elif state.binding is None:
                state.class_target = state.self.analyzer._resolve_class(state.self.ref, state.name)
                state.alias = state.name.split('.')[0]
                if (state.alias in state.self.analyzer.imports.get(state.self.ref.module, {})
                        and not state.self.analyzer._stable_import_name(
                            state.self.ref.module + '.' + state.alias)):
                    state.class_target = None
                if state.class_target and not state.self.analyzer._stable_import_name(
                        state.class_target[0].module + '.' + state.class_target[0].qualname):
                    state.class_target = None
            elif all(value.get('kind') == 'import' for value in state.binding):
                state.callee_classes = state.self.class_values([dict(value,
                    source=value['source'] + ('.' + state.name.split('.', 1)[1]
                        if '.' in state.name else '')) for value in state.binding])
                state.class_target = None
                state.identities = {(value['module'], value['source']) for value in state.callee_classes}
                if len(state.identities) == 1:
                    state.module, state.qualname = next(iter(state.identities))
                    state.matches = state.self.analyzer._definition_index.find(state.module, state.qualname, kind='class')
                    state.class_target = state.matches[0] if len(state.matches) == 1 else None
            else:
                state.class_target = None
            if state.class_target is not None:
                state.constructor = state.self.analyzer._constructor_target(state.class_target)
                state.constructor_class = state.class_target[0]
                state.construction_safe = state.self.analyzer._ordinary_construction(state.constructor_class)
                if state.constructor is not None:
                    state.target = state.constructor
                    state.bound_receiver = True
                    state.dispatch_kind = 'constructor'
                else:
                    state.dispatch_kind = 'constructor_unavailable'
                state.canonical = (state.constructor_class.module + '.' +
                             state.constructor_class.qualname)
        return False

    ## Resolve receiver-based, inherited, super and field dispatch.
    ## 解析基于接收者的继承、super 与字段分派。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _resolve_receiver_dispatch(self, state):
        state.receiver_types = {tuple((value.get('class_type') or {}).get(key, '')
                          for key in ('module', 'qualname')) for value in state.receiver_values}
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and state.receiver_values and all(value.get('class_type')
                                            and not value.get('value_incomplete')
                                            and value.get('relation') == 'direct'
                                            and not value.get('projection')
                                            and not value.get('output_path')
                                            for value in state.receiver_values)
                and len(state.receiver_types) == 1):
            state.module, state.class_name = next(iter(state.receiver_types))
            state.matches = state.self.analyzer._definition_index.find(state.module, state.class_name + '.' + state.node.func.attr)
            state.candidate = state.matches[0] if len(state.matches) == 1 else state.self.analyzer._inherited_method(
                state.module, state.class_name, state.node.func.attr)
            if state.candidate is not None:
                state.target = state.candidate
                state.bound_receiver = False
                state.dispatch_kind = 'class_receiver_candidate'
        if (state.target is None and isinstance(state.node.func, ast.Attribute) and isinstance(state.node.func.value, ast.Name)
                and state.owner and state.owner not in state.function_names
                and (state.self.node.args.posonlyargs or state.self.node.args.args)
                # Incoming instance facts take precedence over the method's
                # lexical owner, including incomplete/empty candidates.
                and not any('instance_type' in value or 'instance_candidates' in value
                            for value in state.receiver_values + state.receiver_sources)
                and state.receiver_sources and all(v['kind'] == 'parameter' and v['relation'] == 'direct'
                    and not v.get('value_incomplete')
                    and v['source'] == (state.self.node.args.posonlyargs + state.self.node.args.args)[0].arg
                    for v in state.receiver_sources)):
            state.matches = state.self.analyzer._definition_index.find(state.self.ref.module, state.owner + '.' + state.node.func.attr)
            if not state.matches:
                state.inherited = state.self.analyzer._inherited_method(state.self.ref.module, state.owner, state.node.func.attr)
                state.matches = [state.inherited] if state.inherited else []
            if len(state.matches) == 1:
                state.target = state.matches[0]
                state.bound_receiver = True
                state.dispatch_kind = 'instance_method'
        if (isinstance(state.node.func, ast.Attribute) and isinstance(state.node.func.value, ast.Attribute)
                and isinstance(state.node.func.value.value, ast.Name)
                and not getattr(state.self.node, 'decorator_list', [])):
            state.args = state.self.node.args.posonlyargs + state.self.node.args.args
            state.bases = state.env.get(state.node.func.value.value.id, [])
            if state.args and state.bases and all(v['kind'] == 'parameter' and v['source'] == state.args[0].arg
                                     and v['relation'] == 'direct' for v in state.bases):
                state.candidate = state.self.analyzer._field_candidate(state.self.ref, state.node.func.value.attr, state.node.func.attr)
                if state.candidate:
                    state.target, state.field_evidence = state.candidate
                    state.bound_receiver = True
                    state.dispatch_kind = 'field_method'
        state.is_zero_super = (isinstance(state.node.func, ast.Attribute)
                         and isinstance(state.node.func.value, ast.Call)
                         and isinstance(state.node.func.value.func, ast.Name)
                         and state.node.func.value.func.id == 'super'
                         and not state.node.func.value.args and not state.node.func.value.keywords)
        state.is_explicit_super = (isinstance(state.node.func, ast.Attribute)
            and isinstance(state.node.func.value, ast.Call)
            and isinstance(state.node.func.value.func, ast.Name)
            and state.node.func.value.func.id == 'super'
            and len(state.node.func.value.args) == 2
            and not state.node.func.value.keywords
            and isinstance(state.node.func.value.args[0], ast.Name)
            and isinstance(state.node.func.value.args[1], ast.Name)
            and state.node.func.value.args[0].id == state.owner.rpartition('.')[2])
        state.current_descriptor = state.self.analyzer._descriptor_kind(
            (state.self.ref, state.self.node))
        state.builtin_super = ('super' not in state.env
            and 'super' not in state.self.analyzer.imports.get(state.self.ref.module, {})
            and 'super' not in state.self.analyzer.module_bindings.get(state.self.ref.module, set())
            and state.self.analyzer._resolve(state.self.ref, 'super') is None
            and state.self.analyzer._resolve_class(state.self.ref, 'super') is None)
        state.current_class_known = (not state.is_explicit_super or (
            state.node.func.value.args[0].id not in state.env
            and state.self.analyzer._class_symbol(state.self.ref.module + '.' + state.owner)
            is not None))
        if ((state.is_zero_super or state.is_explicit_super) and state.owner and state.builtin_super
                and state.current_class_known):
            state.inherited = state.self.analyzer._inherited_method(
                state.self.ref.module, state.owner, state.node.func.attr,
                skip_current_members=True)
            state.args = state.self.node.args.posonlyargs + state.self.node.args.args
            state.receiver_name = (state.node.func.value.args[1].id
                             if state.is_explicit_super else state.args[0].arg if state.args else '')
            if (state.inherited and state.args and state.receiver_name == state.args[0].arg
                    and state.env.get(state.receiver_name)):
                state.target = state.inherited
                state.bound_receiver = state.node.func.attr != '__new__'
                state.dispatch_kind = ('super_new' if state.node.func.attr == '__new__'
                                 else 'super_method')
                state.receiver_values = state.env.get(state.receiver_name, [])
                state.receiver_sources = state.self.materialize(state.receiver_values, state.env)
            if (state.inherited is None and state.node.func.attr == '__new__'
                    and len(state.node.args) == 1 and not state.node.keywords):
                state.receiver = state.self.class_values(state.env.get(state.receiver_name, []), env=state.env)
                state.types = _unique([value.get('class_type') for value in state.receiver])
                if (state.receiver and all(state.types) and len(state.types) == 1
                        and not any(value.get('value_incomplete') for value in state.receiver)):
                    state.class_ref = FunctionRef(**state.types[0])
                    state.hierarchy = state.self.analyzer._class_mro(state.class_ref.module, state.class_ref.qualname)
                    state.owner_index = next((index for index, (ref, _) in enumerate(state.hierarchy or ())
                        if ref.module == state.self.ref.module and ref.qualname == state.owner), None)
                    state.writes, state.truncated = state.self.analyzer._class_binding_writes()
                    state.changed = state.truncated or any(attribute in ('__new__', '__class__', '__bases__', '*')
                        and any(written == ref for ref, _ in state.hierarchy or ())
                        for written, attribute, _, _, _ in state.writes)
                    if state.owner_index is not None and not state.changed and not any(
                            '__new__' in statement_scope_facts(cls.body).bound
                            or cls.keywords or cls.decorator_list
                            for ref, cls in state.hierarchy[state.owner_index + 1:]):
                        state.classes = state.self.class_values(state.self.expression(state.node.args[0], state.env),
                                                    allow_incomplete=True, env=state.env)
                        if state.classes:
                            if (len({(value['module'], value['source']) for value in state.classes}) == 1
                                    and not any(value.get('value_incomplete') for value in state.classes)):
                                state.allocation_class = FunctionRef(**state.classes[0]['class_type'])
                            state.allocation_values = state.classes
                            state.allocation_candidates = state.classes
                            state.dispatch_kind = 'builtin_allocation'
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and isinstance(state.node.func.value, ast.Name)
                and state.node.func.value.id == 'object' and state.node.func.attr == '__new__'
                and len(state.node.args) == 1 and not state.node.keywords
                and 'object' not in state.env
                and 'object' not in state.self.analyzer.imports.get(state.self.ref.module, {})
                and 'object' not in state.self.analyzer.module_bindings.get(state.self.ref.module, set())
                and state.self.analyzer._resolve(state.self.ref, 'object') is None
                and state.self.analyzer._resolve_class(state.self.ref, 'object') is None):
            state.classes = state.self.class_values(state.self.expression(state.node.args[0], state.env), allow_incomplete=True, env=state.env)
            if state.classes and len({(value['module'], value['source']) for value in state.classes}) == 1:
                if not any(value.get('value_incomplete') for value in state.classes):
                    state.allocation_class = FunctionRef(**state.classes[0]['class_type'])
                state.allocation_values = state.classes
                state.allocation_candidates = state.classes
                state.dispatch_kind = 'builtin_allocation'
            elif state.classes:
                state.allocation_candidates = state.classes
                state.allocation_values = state.classes
                state.dispatch_kind = 'builtin_allocation'
        state.possible_allocations = state.allocation_candidates
        state.allocation_candidates = [value for value in state.possible_allocations
            if (state.self.analyzer._ordinary_construction if state.construction_candidates
                else state.self.analyzer._explicit_object_allocation)(FunctionRef(**value['class_type']))]
        if len(state.allocation_candidates) != len(state.possible_allocations):
            state.allocation_candidates = [dict(value, value_incomplete=True) for value in state.allocation_candidates]
        return False

    ## Resolve callable-instance and fresh-receiver bindings.
    ## 解析可调用实例与新鲜接收者绑定。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _resolve_callable_binding(self, state):
        if state.allocation_class and not state.self.analyzer._explicit_object_allocation(state.allocation_class):
            state.allocation_class = None
        if not state.allocation_candidates and state.allocation_class is None and state.dispatch_kind == 'builtin_allocation':
            state.dispatch_kind = None
        state.receiver_values = fresh_lookup_receiver(state.self, state.node, state.receiver_values)
        if (state.target is None and isinstance(state.node.func, ast.Attribute)
                and state.receiver_values and all((value.get('instance_type') and (
                                                not value.get('value_incomplete')
                                                or value.get('fresh_receiver_origin'))
                                            or value.get('instance_candidates'))
                                            and value.get('relation') == 'direct'
                                            and not value.get('projection')
                                            and not value.get('output_path')
                                            for value in state.receiver_values)):
            state.instance_types = {
                (identity['module'], identity['qualname'])
                for value in state.receiver_values
                for identity in ([value['instance_type']] if value.get('instance_type')
                                 else value.get('instance_candidates', []))}
            state.candidates = []
            state.complete_candidates = True
            for state.module, state.class_name in sorted(state.instance_types):
                state.candidate = state.self.analyzer._instance_method_candidate(
                    state.module, state.class_name, state.node.func.attr)
                if state.self.class_lookup_affected(state.receiver_values,
                        (state.node.func.attr, '__class__', '__bases__')):
                    state.candidate = None
                if state.candidate is None:
                    state.complete_candidates = False
                elif state.candidate not in state.candidates:
                    state.candidates.append(state.candidate)
            state.receiver_complete = all(not value.get('value_incomplete') for value in state.receiver_values)
            if state.complete_candidates and len(state.candidates) == 1:
                state.candidate = state.candidates[0]
                state.fresh_binding = (fresh_method_binding(
                    state.self, state.node, state.candidate, state.receiver_values) if not state.receiver_complete else None)
                if state.receiver_complete or state.fresh_binding is not None:
                    state.target = state.candidate
                    state.bound_receiver = True
                    state.dispatch_kind = ('returned_field_candidate'
                                     if state.returned_field_receiver else
                                     'receiver_type_evidence')
                    if state.fresh_binding is not None:
                        state.fresh_instance_method_bindings = [state.fresh_binding]
            elif state.candidates and (state.complete_candidates or any(
                    value.get('instance_candidates') for value in state.receiver_values)):
                state.bounded_targets = state.candidates
                state.dispatch_kind = ('bounded_alternatives' if state.receiver_complete
                                 and state.complete_candidates else 'receiver_unresolved')
        if state.target is None and state.binding and all(v['kind'] == 'import' for v in state.binding):
            state.imported = {v['source'] for v in state.binding}
            if len(state.imported) == 1:
                state.canonical = next(iter(state.imported)) + ('.' + state.name.split('.', 1)[1] if '.' in state.name else '')
                state.target = (state.self.analyzer._resolve_import_binding(state.canonical)
                          if not any(value.get('conditions')
                                     or value.get('import_modified')
                                     or value.get('import_incomplete')
                                     for value in state.binding) else None)
        elif state.binding is None:
            state.alias, state.dot, state.rest = state.name.partition('.')
            state.imported = state.self.analyzer.imports.get(state.self.ref.module, {}).get(state.alias)
            if state.imported:
                state.canonical = state.imported + (state.dot + state.rest if state.dot else '')
        if state.callable_sources and isinstance(state.node.func, (ast.Name, ast.Subscript)):
            state.candidates, state.complete = state.self.callable_targets(state.callable_sources)
            state.callable_incomplete = bool(state.candidates) and not state.complete
            if isinstance(state.node.func, ast.Subscript) and not isinstance(state.node.func.slice, ast.Constant):
                state.complete = False
            if state.complete and len(state.candidates) == 1:
                state.target = state.candidates[0]
                state.dispatch_kind = ('literal_dispatch' if isinstance(state.node.func, ast.Subscript)
                                 else 'incoming_callable' if any(
                                     value.get('callable_type') for value in state.callable_sources)
                                 else None)
            elif state.candidates:
                state.target = None
                state.bounded_targets = state.candidates
        if state.target is None:
            state.target, state.callable_instance_fact, state.callable_instance_cause = (
                state.self.analyzer._module_callable_instance(
                    state.self.ref, state.name, state.binding))
            if state.target is not None:
                state.bound_receiver = True
                state.dispatch_kind = 'callable_instance_candidate'
                state.assignment_evidence = state.self.evidence_at(
                    state.callable_instance_fact['module_ref'],
                    state.callable_instance_fact['assignment'])
                state.receiver_sources = [{
                    'kind': 'module_callable_instance',
                    'source': state.callable_instance_fact['qualified_name'],
                    'instance_type': asdict(
                        state.callable_instance_fact['class_ref']),
                    'relation': 'direct',
                    'evidence': [state.assignment_evidence, state.self.evidence(state.node)],
                    'conditions': list(state.self.conditions)}]
        state.decorated_target_candidate = False
        if (isinstance(state.node.func, ast.Attribute) and (
                any(value.get('class_type') and value.get('value_incomplete')
                    for value in state.receiver_values)
                or state.self.class_lookup_affected(state.receiver_values,
                    (state.node.func.attr, '__class__', '__bases__'))
                or state.node.func.attr.startswith('__') and not state.node.func.attr.endswith('__')
                and any(effect.get('attributes') for value in state.receiver_values
                        for effect in value.get('class_lookup_mutations', [])))):
            if (state.target and state.dispatch_kind == 'super_new' and state.receiver_values
                    and all(value.get('source_class_origin', {}).get('basis') == 'source_symbol'
                            for value in state.receiver_values)
                    and not state.self.class_lookup_affected(state.receiver_values,
                        (state.node.func.attr, '__class__', '__bases__'))
                    and any(value.get('cause') == 'unmodeled_call' for key, values in state.env.items()
                            if key.startswith('$class_origin_invalid:') for value in values)
                    and not any(value.get('cause') == 'write' for key, values in state.env.items()
                                if key.startswith('$class_origin_invalid:') for value in values)):
                state.self.result.boundaries.append({'reason': 'source_lookup_candidate',
                    'call_id': _call_key(state.self.ref.file_path, state.node),
                    'target': asdict(state.target[0]), 'evidence': state.self.evidence(state.node)})
            state.target, state.bounded_targets, state.bound_receiver, state.dispatch_kind = None, [], False, None
        state.identity_decorator = None
        state.wrapper_forwarding_candidate = False
        state.descriptor_kind = state.self.analyzer._descriptor_kind(state.target) if state.target else None
        if state.target and getattr(state.target[1], 'decorator_list', []) and state.descriptor_kind is None:
            state.identity_decorator = state.self.analyzer._identity_decorator(state.target)
            state.decoration_facts = state.self.analyzer._binding_decoration_facts(state.target)
            state.body_preserved = (len(state.decoration_facts) == 1
                and state.decoration_facts[0]['body_binding_status'] == 'preserved')
            if state.identity_decorator is not None or state.body_preserved:
                state.decorated_target_candidate = state.body_preserved and state.identity_decorator is None
            elif (factory_wrapper(state.self.analyzer, state.target) or {}).get('forwarding') is not None:
                # Preserve only the nominal original body. This wrapper's
                # path condition requires concrete invocation arguments;
                # generic ownership/value-flow consumers retain a boundary.
                state.wrapper_forwarding_candidate = True
                state.decorated_target_candidate = True
            elif state.dispatch_kind in (
                    'constructor', 'instance_method', 'field_method',
                    'receiver_type_evidence', 'returned_field_candidate',
                    'super_method', 'super_new'):
                state.decorated_target_candidate = True
            else:
                state.replacement = state.self.analyzer._decorated_target(state.target)
                if state.replacement:
                    state.target = state.replacement
                    state.dispatch_kind = 'decorator_replacement'
                else:
                    state.target = None
        elif state.descriptor_kind == 'staticmethod':
            state.dispatch_kind = 'constructor' if state.constructor_class is not None else 'staticmethod'
        elif state.descriptor_kind == 'classmethod':
            state.bound_receiver = True
            state.dispatch_kind = 'constructor' if state.constructor_class is not None else 'classmethod'
        return False

    ## Create the call record and capture its initial identity and evidence.
    ## 创建调用记录并记录初始身份与证据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _create_flow_call_record(self, state):
        state.call_id = _call_key(state.self.ref.file_path, state.node)
        if state.target and (not namespace_unmodified(state.self.analyzer, state.self.ref.module + '.' + state.name)
                or not namespace_unmodified(state.self.analyzer,
                    state.target[0].module + '.' + state.target[0].qualname)):
            state.self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_source_namespace_binding', 'boundary_kind': 'uncertainty',
                'target': asdict(state.target[0]), 'evidence': state.self.evidence(state.node)})
        state.constructor_values = (state.self.expression(state.node.func, state.env)
            if state.constructor_class is not None and state.target
            and state.dispatch_kind == 'constructor' else [])
        state.call = FlowCall(state.call_id, state.self.ref, state.name, state.node.lineno, state.node.col_offset,
                        state.node.end_lineno, state.node.end_col_offset, state.target[0] if state.target else None)
        state.call.instance_method_bindings = state.fresh_instance_method_bindings
        state.call.implicit_protocol = copy.deepcopy(state.protocol)
        if state.global_rebound:
            state.self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'module_callable_binding_unconfirmed',
                'boundary_kind': 'uncertainty', 'nominal_target': asdict(state.nominal_target[0]),
                'declarations': [state.self.evidence_at(state.nominal_target[0], declaration)
                                 for declaration in state.global_declarations],
                'evidence': state.self.evidence(state.node)})
        if getattr(state.self.analyzer, '_conditional_source_state', False):
            state.contexts = [context for value in state.receiver_sources
                        for context in value.get('instance_candidate_contexts', [])] or state.receiver_sources
            state.common = (state.contexts[0].get('conditions', []) if state.contexts else [])
            state.call.conditions = _unique(copy.deepcopy(state.self.conditions) + [condition for condition in state.common
                if all(condition in value.get('conditions', []) for value in state.contexts)])
            state.parameters = state.self.node.args.posonlyargs + state.self.node.args.args
            state.ambient = state.env.get(state.parameters[0].arg, []) if state.parameters else []
            if state.ambient:
                state.call.conditions = _unique(state.call.conditions + [condition
                    for condition in state.ambient[0].get('conditions', [])
                    if all(condition in value.get('conditions', []) for value in state.ambient)
                    and condition.get('kind') == 'source_state_preserved'])
            for state.context in state.contexts:
                state.identity = state.context.get('instance_type')
                state.candidate = (state.self.analyzer._instance_method_candidate(state.identity['module'],
                    state.identity['qualname'], state.node.func.attr) if state.identity and isinstance(state.node.func, ast.Attribute)
                    else None)
                if state.candidate and state.candidate in state.bounded_targets:
                    state.call.candidate_paths.append({'target': asdict(state.candidate[0]), 'call_id': state.call.id,
                        'receiver_class': copy.deepcopy(state.identity),
                        'conditions': copy.deepcopy(state.context.get('conditions', []))})
        state.call.callable_sources = copy.deepcopy(state.callable_sources)
        if state.callable_incomplete:
            state.self.add_boundary('callable_identity_incomplete', state.node, state.env,
                state.callable_sources, call_id=state.call_id)
        if (isinstance(state.node.func, ast.Subscript) and state.callable_sources
                and not isinstance(state.node.func.slice, ast.Constant)):
            state.self.add_boundary('literal_dispatch_key_unknown', state.node, state.env,
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
        state.class_binding = state.self.class_method_binding(state.node, state.target, state.receiver_values)
        if state.class_binding:
            state.call.class_method_bindings = [state.class_binding]
            if state.class_binding['status'] != 'source_bound':
                state.self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'class_method_binding_unconfirmed', 'boundary_kind': 'uncertainty',
                    'issues': copy.deepcopy(state.class_binding['issues']), 'evidence': state.self.evidence(state.node)})
        if (state.target and state.receiver_sources and (state.descriptor_kind == 'classmethod'
                or any(value.get('class_type') for value in state.receiver_sources))):
            state.self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_class_receiver_override_possible',
                'boundary_kind': 'assumption' if state.class_binding and state.class_binding['status'] == 'source_bound' else 'uncertainty',
                'binding_status': state.class_binding['status'] if state.class_binding else 'unconfirmed',
                'assumptions': copy.deepcopy(state.class_binding['assumptions']) if state.class_binding else [],
                'evidence': state.self.evidence(state.node)})
        if state.identity_decorator is not None:
            state.call.decorator_identity_evidence = [{
                'decorator': asdict(state.identity_decorator['decorator']),
                'parameter': state.identity_decorator['parameter'],
                'returns': [state.self.evidence_at(
                    state.identity_decorator['decorator'], returned)
                    for returned in state.identity_decorator['returns']]}]
            if (state.identity_decorator['effects_unmodeled'] and not (state.body_preserved
                    and state.decoration_facts[0].get('kind') == 'source_fresh_function_decoration')):
                state.self.result.boundaries.append({
                    'call_id': state.call_id, 'callee_name': state.name,
                    'reason': 'identity_decorator_effects_unmodeled',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': state.self.evidence_at(
                        state.identity_decorator['decorator'],
                        state.identity_decorator['definition'])})
        if state.wrapper_forwarding_candidate:
            state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'identity_decorator_effects_unmodeled',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence_at(state.target[0], state.target[1])})
        if state.callable_instance_fact is not None:
            state.call.callable_instance_evidence = state.self.module_callable_evidence(
                state.callable_instance_fact, state.node)
            state.call.callable_instance_evidence['binding'] = source_binding(
                state.self, state.callable_instance_fact, state.target)
        if state.returned_field_receiver:
            state.call.receiver_type_evidence = _unique([
                dict(fact, receiver_call=state.self.evidence(state.node))
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
            state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'function': asdict(state.self.ref), 'reason': 'builtin_name_unconfirmed',
                'builtin_name_status': state.builtin_status, 'affected_scope': 'unknown',
                'affected_values': [], 'conditions': list(state.self.conditions),
                'evidence': state.self.evidence(state.node)})
        return False

    ## Finalize target status and attach bounded call metadata.
    ## 确定目标状态并附加有界调用元数据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _complete_call_target_metadata(self, state):
        if state.dispatch_kind == 'receiver_unresolved' and state.bounded_targets:
            state.call.target_status = 'receiver_unresolved'
            state.self.add_boundary('class_attribute_state_unknown', state.node, state.env,
                state.receiver_values, call_id=state.call_id)
        if state.callable_incomplete:
            state.call.target_status = 'definition_unavailable'
        if state.constructor_class is not None and not state.construction_safe:
            state.self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'dynamic_construction', 'evidence': state.self.evidence(state.node)})
            if (state.self.analyzer._class_binding_write_cache is not None
                    and state.self.analyzer._class_binding_write_cache[1]):
                state.self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'constructor_binding_budget', 'evidence': state.self.evidence(state.node)})
            if state.target and state.target[1].name == '__new__':
                state.self.result.boundaries.append({'call_id': state.call_id,
                    'reason': 'constructor_initialization_unmodeled',
                    'phase': '__init__', 'evidence': state.self.evidence(state.node)})
        if state.allocation_class is not None or state.allocation_candidates and not state.construction_candidates:
            state.self.result.boundaries.append({'call_id': state.call_id,
                'reason': 'builtin_allocator_source_unavailable',
                'evidence': state.self.evidence(state.node)})
        if state.field_evidence:
            state.call.target_status = 'constructor_field_candidate'
            state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'constructor_field_assumption', 'evidence': state.self.evidence(state.field_evidence)})
        if state.callable_instance_cause is not None:
            state.self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'module_callable_instance_unresolved',
                'cause': state.callable_instance_cause,
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence(state.node)})
        if state.callable_instance_fact is not None:
            state.callable_binding = state.call.callable_instance_evidence['binding']
            state.self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_callable_instance_override_possible',
                'boundary_kind': 'assumption' if state.callable_binding['status'] == 'source_bound' else 'uncertainty',
                'binding_status': state.callable_binding['status'],
                'assumptions': copy.deepcopy(state.callable_binding['assumptions']),
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence(state.node)})
        if (state.target and state.dispatch_kind in (
                'super_method', 'super_new', 'instance_method')
                and getattr(state.self.node, 'decorator_list', [])
                and state.current_descriptor not in ('classmethod', 'staticmethod')):
            state.self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'decorated_caller_semantics',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence(state.self.node)})
            state.facts = state.self.analyzer._binding_decoration_facts((state.self.ref, state.self.node))
            if len(state.facts) == 1 and state.facts[0]['body_binding_status'] == 'preserved':
                state.self.result.boundaries[-1].update(boundary_kind='assumption',
                    body_binding_status='preserved', function=asdict(state.self.ref),
                    assumptions=copy.deepcopy(state.facts[0]['assumptions']))
        if state.target and state.decorated_target_candidate:
            state.self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'decorated_target_candidate',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence_at(state.target[0], state.target[1])})
            state.facts = state.self.analyzer._binding_decoration_facts(state.target)
            if len(state.facts) == 1 and state.facts[0]['body_binding_status'] == 'preserved':
                state.self.result.boundaries[-1].update(boundary_kind='assumption',
                    body_binding_status='preserved', function=asdict(state.target[0]),
                    assumptions=copy.deepcopy(state.facts[0]['assumptions']))
        if state.target and state.owner and state.dispatch_kind in (
                'instance_method', 'super_method', 'super_new'):
            state.hierarchy = state.self.analyzer._class_mro(state.self.ref.module, state.owner)
            state.decorated_class = next(((ref, cls) for ref, cls in (state.hierarchy or ())
                                    if cls.decorator_list), None)
            if state.decorated_class is not None:
                state.self.result.boundaries.append({
                    'call_id': state.call_id, 'callee_name': state.name,
                    'reason': 'decorated_class_candidate',
                    'affected_scope': 'unknown', 'affected_values': [],
                    'evidence': state.self.evidence_at(*state.decorated_class)})
        state.string_arity = {'split': (0, 2), 'rsplit': (0, 2),
                        'strip': (0, 1), 'lstrip': (0, 1), 'rstrip': (0, 1),
                        'startswith': (1, 3), 'endswith': (1, 3),
                        'partition': (1, 1), 'rpartition': (1, 1)}
        state.method = state.node.func.attr if isinstance(state.node.func, ast.Attribute) else ''
        state.limits = state.string_arity.get(state.method)
        state.string_protocol = (state.target is None and isinstance(state.node.func, ast.Attribute)
                           and isinstance(state.node.func.value, ast.Name)
                           and state.limits is not None and state.limits[0] <= len(state.node.args) <= state.limits[1]
                           and not state.node.keywords
                           and not any(isinstance(argument, ast.Starred)
                                       for argument in state.node.args)
                           and state.receiver_sources
                           and all(v.get('python_shape') == 'str'
                                   for v in state.receiver_sources))
        if state.string_protocol:
            state.call.target_status = 'python_protocol'
            state.call.argument_sources.append({'argument': {'receiver': True}, 'parameter': '$receiver',
                                          'sources': state.receiver_sources})
            if state.method in ('partition', 'rpartition'):
                state.call.return_dependencies = [
                    {'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                     'output_path': [index],
                     'evidence': [{'provenance':
                        'Guarded or trusted str partition result dependency'}],
                     'conditions': list(state.self.conditions)} for index in range(3)]
            else:
                state.call.return_dependencies = [{
                    'kind': 'parameter', 'source': '$receiver', 'relation': 'derived',
                    'evidence': [{'provenance':
                        'Guarded str receiver dependency; builtin method implementation assumed'}],
                    'conditions': list(state.self.conditions)}]
                state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                                               'reason': 'string_subclass_override_possible'})
            if state.method in ('partition', 'rpartition'):
                state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                                               'reason': 'string_subclass_override_possible'})
        state.literal_join = (state.target is None and isinstance(state.node.func, ast.Attribute)
                        and isinstance(state.node.func.value, ast.Constant) and isinstance(state.node.func.value.value, str)
                        and state.node.func.attr == 'join' and len(state.node.args) == 1 and not state.node.keywords
                        and not isinstance(state.node.args[0], ast.Starred))
        if state.target and state.dispatch_kind == 'super_method':
            # The dedicated proof revalidates the exact builtin super()
            # receiver, MRO target and fresh-origin lineage itself. Do not
            # gate that proof on the generic receiver-binding flag: other
            # uncertainty in argument expansion can clear that flag even
            # when the super lookup remains statically exact.
            state.fresh = fresh_super_method_binding(state.self, state.node, state.target, state.receiver_values)
            if state.fresh is not None:
                state.call.instance_method_bindings = [state.fresh]
        if state.target and state.bound_receiver and state.dispatch_kind in (
                'instance_method', 'field_method', 'receiver_type_evidence',
                'returned_field_candidate'):
            state.fresh = fresh_method_binding(state.self, state.node, state.target, state.receiver_values)
            if state.fresh is not None:
                state.call.instance_method_bindings = [state.fresh]
            state.self.result.boundaries.append({'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_method_override_possible',
                **({'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                    'assumptions': copy.deepcopy(state.fresh['assumptions'])} if state.fresh is not None else {})})
        if state.returned_field_receiver and (state.target or state.bounded_targets):
            state.self.result.boundaries.append({
                'call_id': state.call_id, 'callee_name': state.name,
                'reason': 'dynamic_accessor_override_possible',
                'affected_scope': 'unknown', 'affected_values': [],
                'evidence': state.self.evidence(state.node)})
        return False

    ## Bind call arguments to formal parameters and callable contracts.
    ## 将调用实参与形参及可调用契约绑定。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _bind_call_parameters(self, state):
        state.capture_values = {}
        state.params = state.target[1].args if state.target else None
        state.contract = state.self.analyzer.return_summaries.get(state.canonical) if state.target is None else None
        if (state.contract is None and state.target is None and state.name == 'isinstance'
                and state.builtin_status == 'confirmed_builtin' and len(state.node.args) == 2
                and not state.node.keywords and isinstance(state.node.args[0], ast.Name)
                and isinstance(state.node.args[1], ast.Name) and state.node.args[1].id == 'str'
                and state.self.analyzer._builtin_name_status(state.self.ref, state.self.node, 'str', state.env)
                    == 'confirmed_builtin'):
            state.functions, state.closed = state.self.callable_targets(state.env.get(state.node.args[0].id, []))
            if (state.functions and state.closed and all(not function.decorator_list
                    and '.' not in ref.qualname for ref, function in state.functions)):
                state.contract = {'parameters': ['object', 'classinfo'], 'returns': [],
                    'provenance': 'Closed source function object is not a builtin str'}
                state.call.target_status = 'python_protocol'
                state.call.implicit_protocol = {'kind': 'source_function_isinstance',
                    'type': 'str', 'result': False, 'evidence': state.self.evidence(state.node)}
        if (state.contract is None and state.target is None and state.builtin_status == 'confirmed_builtin'
                and state.name in ('str', 'repr', 'bool', 'len', 'list', 'tuple', 'set', 'callable')
                and state.canonical == state.self.ref.module + '.' + state.name
                and len(state.node.args) == 1 and not state.node.keywords
                and not isinstance(state.node.args[0], ast.Starred)):
            state.contract = {'parameters': ['object'], 'returns': [
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
                    'source_hash': state.self.analyzer.hashes[state.self.ref.file_path],
                    'evidence': state.self.evidence(state.node)}
            elif state.name == 'bool':
                state.call.implicit_protocol = {'kind': 'builtin_scalar_truth', 'builtin': 'bool',
                    'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                    'precondition': {'argument': {'position': 0},
                        'exact_types': ['NoneType', 'bool', 'int', 'float', 'str', 'bytes']},
                    'completion': 'normal_return_if_precondition',
                    'effects': 'none_if_precondition', 'call_id': state.call.id,
                    'source_hash': state.self.analyzer.hashes[state.self.ref.file_path],
                    'evidence': state.self.evidence(state.node)}
            elif state.name == 'len':
                state.call.implicit_protocol = {'kind': 'builtin_container_length', 'builtin': 'len',
                    'status': 'requires_exact_input', 'runtime_input_confirmed': False,
                    'precondition': {'argument': {'position': 0},
                        'exact_types': ['dict', 'list', 'tuple', 'str', 'bytes',
                                        'set', 'frozenset']},
                    'completion': 'normal_return_if_precondition',
                    'effects': 'none_if_precondition', 'call_id': state.call.id,
                    'source_hash': state.self.analyzer.hashes[state.self.ref.file_path],
                    'evidence': state.self.evidence(state.node)}
        if (state.contract is None and state.target is None and state.builtin_status == 'confirmed_builtin' and state.name == 'next'
                and state.canonical == state.self.ref.module + '.next'
                and len(state.node.args) == 1 and not state.node.keywords
                and not isinstance(state.node.args[0], ast.Starred)):
            state.contract = {'parameters': ['iterator'], 'returns': [
                {'parameter': 'iterator', 'projection': ['*'], 'relation': 'direct'}],
                'provenance': 'Python next returns an element produced by its iterator'}
            state.call.target_status = 'python_protocol'
        if state.contract and (state.binding is None or all(v['kind'] == 'import' for v in state.binding)):
            state.params = ast.arguments(posonlyargs=[], args=[ast.arg(arg=n) for n in state.contract['parameters']],
                                   vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
            state.call.return_dependencies = [
                {'kind': 'parameter', 'source': d['parameter'], 'relation': d['relation'],
                 'projection': d.get('projection', []),
                 'evidence': [{'provenance': state.contract['provenance'], 'callable': state.canonical}], 'conditions': []}
                for d in state.contract.get('returns', [])]
        state.positional = state.params.posonlyargs + state.params.args if state.params else []
        state.instance_parameter = None
        if state.bound_receiver and state.target and state.positional:
            if state.dispatch_kind != 'constructor':
                state.call.argument_sources.append({
                    'argument': {'receiver': True},
                    'parameter': state.positional[0].arg,
                    'sources': state.receiver_sources})
                if (state.descriptor_kind is None and not state.target[1].decorator_list
                        and state.receiver_sources and all(value.get('instance_type')
                            for value in state.receiver_sources)):
                    state.instance_parameter = state.positional[0].arg
                    state.call.parameter_bindings.append({'argument': {'receiver': True},
                        'parameter': state.instance_parameter, 'status': 'exact',
                        'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'})
            state.positional = state.positional[1:]
        state.records = state.self.bind_call_arguments(state.node, state.params, state.positional, state.call) if state.params else [
            {'argument': {'position': i}, 'node': arg.value if isinstance(arg, ast.Starred) else arg,
             'parameter': None, 'target_path': [], 'status': 'unresolved',
              'binding_kind': 'dynamic_starred' if isinstance(arg, ast.Starred) else 'explicit',
              'destination_kind': 'unresolved'}
            for i, arg in enumerate(state.node.args)] + [
            {'argument': {'keyword': kw.arg}, 'node': kw.value, 'parameter': None,
              'target_path': [], 'status': 'unresolved', 'binding_kind': 'explicit',
              'destination_kind': 'unresolved'}
            for kw in state.node.keywords]
        if not state.params:
            state.call.binding_status = 'unavailable'
        state.invalid_binding = bool(state.params) and any(
            record['status'] == 'unresolved'
            and record['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
            for record in state.records)
        state.invalid_binding = state.invalid_binding or any(
            record['status'] in ('missing', 'duplicate') for record in state.records)
        state.actual_values = {}
        return False

    ## Build per-argument binding records and propagate argument facts.
    ## 构建逐实参绑定记录并传播实参事实。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _map_call_arguments(self, state):
        state.protocol_values = {}
        for state.record in state.records:
            state.slot, state.arg = state.record['argument'], state.record['node']
            state.parameter, state.target_path = state.record['parameter'], state.record['target_path']
            state.binding_record = {'argument': state.slot, 'parameter': state.parameter,
                              'status': state.record['status'],
                              'destination_kind': state.record.get('destination_kind', 'unresolved')}
            if state.target_path:
                state.binding_record['target_path'] = state.target_path
            if state.record['binding_kind'] != 'explicit':
                state.binding_record['binding_kind'] = state.record['binding_kind']
            state.call.parameter_bindings.append(state.binding_record)
            if state.arg is None:
                continue
            state.raw_values = state.self.expression(state.arg, state.env)
            if isinstance(state.slot, dict) and 'position' in state.slot:
                state.protocol_values[state.slot['position']] = state.raw_values
            state.raw_values = [dict(value, value_incomplete=True)
                if ((value.get('callable_type') or {}).get('module', value.get('module')),
                    (value.get('callable_type') or {}).get('qualname', value.get('source')))
                    in state.self.modified_return_callables else value for value in state.raw_values]
            state.actual_values[state.parameter] = _unique(state.actual_values.get(state.parameter, []) + state.raw_values)
            state.values = state.self.marked(state.self.materialize(state.raw_values, state.env), state.arg)
            state.argument_record = {'argument': state.slot, 'parameter': state.parameter, 'sources': state.values}
            state.container = state.self.exact_container(state.raw_values, ('dict', 'list', 'tuple'), state.env)
            if state.container is not None and not state.target_path and not any(
                    isinstance(child, ast.Call) for argument in state.node.args
                    + [keyword.value for keyword in state.node.keywords] for child in ast.walk(argument)):
                state.argument_record['container_binding'] = {'status': 'exact',
                    'shape': state.container['container_shape'],
                    'source': state.container['source'],
                    'contents_unknown': bool(state.env.get(state.container['source'] + '$state')),
                    'evidence': [state.self.evidence(state.arg)], 'conditions': copy.deepcopy(state.self.conditions)}
            elif state.raw_values and not state.target_path and all(
                    value.get('kind') == 'parameter' and value.get('relation') == 'direct'
                    and value.get('container_binding', {}).get('status') == 'exact'
                    and not any(value.get(flag) for flag in ('projection', 'output_path', 'value_incomplete'))
                    for value in state.raw_values):
                state.incoming_bindings = [value['container_binding'] for value in state.raw_values]
                if all(value == state.incoming_bindings[0] for value in state.incoming_bindings):
                    state.forwarded = copy.deepcopy(state.incoming_bindings[0])
                    state.aliases = {name for name, facts in state.self.incoming.items() if any(
                        fact.get('container_binding', {}).get('source') == state.forwarded['source']
                        for fact in facts)}
                    if any(value.get('source') in state.aliases for previous in state.self.calls
                            for value in previous.receiver_sources + [value for item in previous.argument_sources
                                for value in item.get('sources', [])]):
                        state.forwarded['contents_unknown'] = True
                    state.argument_record['container_binding'] = state.forwarded
            state.literal = state.self.literal_fact(state.arg, state.env)
            if state.literal is not None:
                state.argument_record.update(literal=state.literal, value_evidence=[state.self.evidence(state.arg)])
            if state.target_path:
                state.argument_record['target_path'] = state.target_path
            state.call.argument_sources.append(state.argument_record)
            for state.value in state.values:
                state.call.argument_flows.append(dict(state.value, target_parameter=state.parameter,
                                                target_path=state.target_path, argument=state.slot,
                                                status='flow_found'))
                if state.value['kind'] == 'parameter':
                    state.call.parameter_flows.append(dict(state.value, source_parameter=state.value['source'],
                                                     target_parameter=state.parameter,
                                                     target_path=state.target_path,
                                                     argument=state.slot, status='flow_found'))
        state.fresh_super = (state.call.instance_method_bindings[0]
            if len(state.call.instance_method_bindings) == 1
            and state.call.instance_method_bindings[0].get('kind') == 'fresh_source_super_method'
            and state.call.instance_method_bindings[0].get('status') == 'source_bound'
            else None)
        state.receiver_parameters = (state.target[1].args.posonlyargs + state.target[1].args.args
            if state.target is not None else [])
        if (state.fresh_super is not None and state.receiver_parameters
                and state.fresh_super.get('call_id') == state.call.id
                and state.fresh_super.get('target') == asdict(state.target[0])
                and state.call.receiver_sources and all(
                    value.get('fresh_receiver_origin') == state.fresh_super.get('origin')
                    and value.get('relation') == 'direct'
                    and value.get('source') == state.fresh_super.get('origin', {}).get('parameter')
                    and not any(value.get(flag) for flag in (
                        'projection', 'output_path', 'attribute_provenance',
                        'import_modified', 'import_incomplete', 'value_incomplete'))
                    for value in state.call.receiver_sources)
                and not any(binding.get('argument') == {'receiver': True}
                    and binding.get('parameter') == state.receiver_parameters[0].arg
                    for binding in state.call.parameter_bindings)):
            state.call.parameter_bindings.append({'argument': {'receiver': True},
                'parameter': state.receiver_parameters[0].arg, 'status': 'exact',
                'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter',
                'basis': 'source_bound_super_method_wrapper'})
        if state.literal_join:
            state.call.target_status = 'python_protocol'
            state.call.argument_sources[0]['parameter'] = 'iterable'
            state.call.parameter_bindings[0].update(parameter='iterable', status='exact')
            for state.value in state.call.argument_flows + state.call.parameter_flows:
                state.value['target_parameter'] = 'iterable'
            state.call.return_dependencies = [{'kind': 'parameter', 'source': 'iterable', 'projection': ['*'],
                'relation': 'derived', 'evidence': [{'provenance': 'Python str.join iterable elements'}],
                'conditions': list(state.self.conditions)}]
        if state.params:
            state.supplied = {b['parameter'] for b in state.call.parameter_bindings if b['status'] == 'exact'}
            state.defaults = list(zip(state.positional[len(state.positional) - len(state.params.defaults):], state.params.defaults))
            state.defaults += [(a, d) for a, d in zip(state.params.kwonlyargs, state.params.kw_defaults) if d is not None]
            for state.param, state.default in state.defaults:
                state.unknown_keywords = any(keyword.arg is None and not isinstance(keyword.value, ast.Dict)
                                       for keyword in state.node.keywords)
                state.unknown_positions = any(isinstance(argument, ast.Starred)
                                        and not isinstance(argument.value, (ast.Tuple, ast.List))
                                        for argument in state.node.args)
                state.possibly_expanded = state.unknown_keywords or (state.unknown_positions and state.param in state.positional)
                if state.param.arg not in state.supplied and not state.possibly_expanded:
                    state.call.parameter_bindings.append({'argument': None, 'parameter': state.param.arg,
                                                    'binding_kind': 'default', 'status': 'exact',
                                                    'source_text': ast.unparse(state.default)})
                    if state.binding and all(v['kind'] == 'callable' for v in state.binding):
                        state.call.argument_sources.append({'argument': None, 'parameter': state.param.arg,
                            'sources': _unique([v for b in state.binding for v in b.get('defaults', {}).get(state.param.arg, [])])})
        return False

    ## Collect source-backed effects and receiver mutations.
    ## 收集有源码依据的效果与接收者变更。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _analyze_call_effects(self, state):
        if (state.constructor_class is not None and state.target
                and state.call.target_status == 'constructor'):
            state.fact = constructor_source_binding(state.self, state.node, state.constructor_class, state.target,
                state.constructor_values, state.self.class_origin_invalid(asdict(state.constructor_class), state.env)
                or state.self.class_lookup_affected([{'class_lookup_mutations':
                    state.self.class_lookup_effects(asdict(state.constructor_class), state.env)}],
                    ('__new__', '__init__', '__class__', '__bases__')))
            state.call.constructor_bindings = [state.fact]
            if state.fact['status'] == 'source_bound':
                state.parameter = state.fact['implicit_binding']['parameter']
                state.slot = copy.deepcopy(state.fact['implicit_binding']['argument'])
                state.sources = ([{'kind': 'constructor_instance', 'source': state.call.id,
                    'instance_type': asdict(state.constructor_class), 'relation': 'direct',
                    'evidence': [state.self.evidence(state.node)],
                    'conditions': copy.deepcopy(state.self.conditions)}]
                    if state.fact['phase'] == '__init__' else copy.deepcopy(state.constructor_values))
                if state.fact['phase'] == '__new__':
                    for state.value in state.sources:
                        state.value.setdefault('source_class_origin', {
                            'basis': 'source_symbol', 'class': asdict(state.constructor_class),
                            'evidence': copy.deepcopy(state.value.get('evidence', [])), 'call_context': []})
                state.call.argument_sources.insert(0, {'argument': state.slot, 'parameter': state.parameter,
                                                'sources': state.sources})
                state.call.parameter_bindings.insert(0, {'argument': state.slot, 'parameter': state.parameter,
                    'status': 'exact', 'binding_kind': 'implicit_receiver',
                    'destination_kind': 'parameter'})
                if state.self.implicit_keyword_conflict(state.call, state.parameter, state.slot,
                        {arg.arg for arg in state.target[1].args.posonlyargs}):
                    state.invalid_binding = True
                state.actual_values[state.parameter] = state.sources
                for state.value in state.sources:
                    state.call.argument_flows.append(dict(state.value, target_parameter=state.parameter,
                        argument=state.slot, status='flow_found'))
                state.self.result.boundaries.append({'call_id': state.call.id,
                    'reason': 'source_constructor_' + state.fact['phase'].strip('_') + '_binding',
                    'boundary_kind': 'assumption', 'binding_status': 'source_bound',
                    'execution_scope': state.fact['execution_scope'],
                    'assumptions': copy.deepcopy(state.fact['assumptions']),
                    'evidence': state.self.evidence(state.node)})
            else:
                state.self.result.boundaries.append({'call_id': state.call.id,
                    'reason': 'constructor_binding_unconfirmed',
                    'issues': copy.deepcopy(state.fact['issues']), 'evidence': state.self.evidence(state.node)})
                state.conditional = conditional_constructor_signature(state.self, state.node, state.fact, state.call.id)
                if state.conditional is not None and state.call.binding_status != 'invalid':
                    state.conditional.update(call_id=state.call.id, call_evidence=state.self.evidence(state.node))
                    state.call.conditional_source_bindings = [state.conditional]
                    state.call.conditions = copy.deepcopy(state.conditional['conditions'])
                    state.self.result.boundaries.append({'call_id': state.call.id,
                        'reason': 'conditional_constructor_signature',
                        'boundary_kind': 'required_condition',
                        'condition': copy.deepcopy(state.conditional['conditions'][-1])})
        if state.instance_parameter is not None:
            if state.self.implicit_keyword_conflict(state.call, state.instance_parameter, {'receiver': True},
                    {arg.arg for arg in state.target[1].args.posonlyargs}):
                state.invalid_binding = True
            state.invalid_receivers = {(value.get('source'), repr(value.get('instance_type')))
                for values in state.env.values() for value in values
                if value.get('instance_type') and value.get('value_incomplete')}
            for state.argument in state.call.argument_sources:
                if state.argument.get('argument') == {'receiver': True}:
                    state.argument['sources'] = [dict(value, value_incomplete=True)
                        if (value.get('source'), repr(value.get('instance_type')))
                            in state.invalid_receivers else value for value in state.argument['sources']]
                    state.actual_values[state.instance_parameter] = state.argument['sources']
        if (state.descriptor_kind == 'classmethod' and state.target and any(
                fact.get('status') == 'source_bound' for fact in state.call.class_method_bindings)):
            state.parameters = state.target[1].args.posonlyargs + state.target[1].args.args
            if state.parameters and state.self.implicit_keyword_conflict(state.call, state.parameters[0].arg,
                    {'receiver': True}, {arg.arg for arg in state.target[1].args.posonlyargs}):
                state.invalid_binding = True
        for state.argument in state.call.argument_sources:
            state.updated = []
            for state.value in state.argument.get('sources', []):
                if state.value.get('class_type'):
                    state.mutations = state.self.class_lookup_effects(state.value['class_type'], state.env)
                    if state.mutations:
                        state.value = dict(state.value, class_lookup_mutations=_unique(
                            state.value.get('class_lookup_mutations', []) + copy.deepcopy(state.mutations)))
                    if state.self.class_origin_invalid(state.value['class_type'], state.env):
                        state.value = dict(state.value, value_incomplete=True)
                state.updated.append(state.value)
            state.argument['sources'] = state.updated
        state.effects_complete = False
        if state.target:
            # Closure cells are read at invocation, after all argument expressions.
            for state.capture in state.self.analyzer._captures(*state.target):
                state.capture_values[state.capture] = copy.deepcopy(state.env.get(state.capture, []))
                state.record = {'capture': state.capture, 'sources': state.capture_values[state.capture],
                    'current_sources': copy.deepcopy(state.self.materialize(state.capture_values[state.capture], state.env))}
                state.container = state.self.exact_container(state.capture_values[state.capture], ('dict', 'list', 'tuple'), state.env)
                if state.container is not None:
                    state.record['container_binding'] = {'status': 'exact',
                        'shape': state.container['container_shape'], 'source': state.container['source'],
                        'contents_unknown': bool(state.env.get(state.container['source'] + '$state')),
                        'evidence': [state.self.evidence(state.node)], 'conditions': copy.deepcopy(state.self.conditions)}
                state.call.capture_bindings.append(state.record)
        state.selected_target = (state.self.analyzer._selected_definition(state.target,
            state.self.analyzer._incoming_facts(state.target, state.call)) if state.target else None)
        if state.target:
            state.call.conditional_returns = state.self.analyzer._guarded_object_returns(state.target)
            for state.fact in state.call.conditional_returns:
                state.values = state.self.container_values(state.actual_values.get(state.fact['parameter'], []))
                if (state.call.binding_status == 'complete' and state.values and all(
                        value.get('kind') == 'container'
                        and value.get('container_shape') in ('dict', 'list', 'tuple')
                        and value.get('relation') == 'direct' and not value.get('value_incomplete')
                        and not value.get('projection') and not value.get('output_path')
                        and value['source'] in state.env for value in state.values)
                        and len({value['source'] for value in state.values}) == 1):
                    state.fact.update(container_shape=state.values[0]['container_shape'],
                        object_source=state.values[0]['source'],
                        binding=copy.deepcopy(next(binding for binding in state.call.parameter_bindings
                            if binding.get('parameter') == state.fact['parameter'])),
                        input_evidence=_unique([evidence for value in state.values
                            for evidence in value.get('evidence', [])]))
        state.self.invalidate_attributes(state.env)
        if state.target and not state.invalid_binding and not getattr(state.node, '_flow_skip_effects', False):
            state.effects_complete = state.self.apply_effects(
                state.selected_target, state.actual_values, state.capture_values, state.call, state.env, state.node)
            state.scope = state.self.analyzer._scope_facts(state.selected_target[1])
            state.unmodeled = (state.scope.nonlocals & state.scope.bound) - {
                effect['target'] for effect in state.call.effects
                if effect.get('kind') == 'nonlocal_write' and effect.get('status') == 'exact'}
            if state.unmodeled:
                state.affected = [value for name in state.unmodeled for value in state.capture_values.get(name, [])]
                state.self.add_boundary('capture_binding_write_unmodeled', state.node, state.env, state.affected,
                                  call_id=state.call.id)
                for state.name in state.unmodeled:
                    state.self.unknown_container_contents(state.capture_values.get(state.name, []), state.env)
                    state.env[state.name] = [dict(value, value_incomplete=True)
                                 for value in state.env.get(state.name, [])]
                state.effects_complete = False
        state.container_result = state.self.container_call(state.node, state.receiver_values, state.call, state.env, state.protocol_values)
        return False

    ## Resolve container, protocol and bounded-target result facts.
    ## 解析容器、协议及有界目标的结果事实。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _resolve_container_and_protocol_results(self, state):
        if state.container_result is None and isinstance(state.node.func, ast.Attribute) and state.node.func.attr == 'copy':
            state.incoming_receiver = state.self.incoming_copy_receiver(state.node, state.receiver_values, state.call, state.env)
            if state.incoming_receiver is not None:
                state.container_result = state.self.container_call(state.node, state.incoming_receiver, state.call, state.env, state.protocol_values)
        if state.target is None and state.container_result is None:
            state.self.inherited_setdefault(state.node, state.receiver_values, state.call, state.env)
        if state.target is None and state.container_result is None and isinstance(state.node.func, ast.Name):
            state.container_result = state.self.container_constructor(state.node, state.call, state.env, state.protocol_values)
        if (state.target is None and not state.bounded_targets
                and state.call.target_status not in ('python_protocol', 'local_container_protocol',
                                              'builtin_allocation')):
            for state.values in state.actual_values.values():
                state.self.invalidate_literals(state.values, state.env)
                state.candidates, state._ = state.self.callable_targets(state.values)
                state.self.modified_return_callables.update(
                    (candidate[0].module, candidate[0].qualname) for candidate in state.candidates)
                for state.reference in state.self.container_values(state.values):
                    if state.reference.get('kind') == 'container':
                        state.source = state.reference['source']
                        state.env[state.source] = [dict(value, value_incomplete=True)
                            if value.get('kind') == 'callable' or value.get('callable_type')
                            else value for value in state.env.get(state.source, [])]
                state.self.unknown_container_contents(state.values, state.env)
            state.self.unknown_container_contents(state.receiver_values, state.env)
        state.source_super = (state.name == 'super' and state.builtin_status == 'confirmed_builtin'
            and len(state.node.args) == 2 and not state.node.keywords
            and not any(isinstance(argument, ast.Starred) for argument in state.node.args)
            and all(known and not any(value.get('value_incomplete') for value in known)
                    for known in (state.self.class_values(values, env=state.env)
                                  for values in state.actual_values.values())))
        state.preserved_classes = (state.self.class_attribute_effect(
            state.selected_target, state.call, state.capture_values, state.env, state.node)
            if state.selected_target and not state.invalid_binding
            and not getattr(state.node, '_flow_skip_effects', False) else [])
        if not state.effects_complete and not state.source_super and state.call.target_status not in (
                'python_protocol', 'local_container_protocol', 'builtin_allocation'):
            state.self.invalidate_instance_receivers(
                [value for values in state.actual_values.values() for value in values]
                + state.receiver_values
                + [value for values in state.capture_values.values() for value in values], state.env)
            state.self.invalidate_class_origins(
                [value for value in [value for values in state.actual_values.values() for value in values]
                + state.receiver_values
                + [value for values in state.capture_values.values() for value in values]
                 if value.get('class_type') not in state.preserved_classes], state.env, state.call)
        state.self.calls.append(state.call)
        if state.invalid_binding:
            state.return_value =  []
            return True
        if (getattr(state.self.analyzer, '_conditional_source_state', False) and state.call.target is not None
                and state.call.target_status in ('super_new', 'super_method', 'classmethod')):
            state.required = [condition for condition in state.call.conditions
                        if condition.get('kind') == 'source_state_preserved']
            if state.required:
                state.call.conditional_source_bindings = [{'kind': 'conditional_source_lookup',
                    'status': 'required', 'target': asdict(state.call.target), 'call_id': state.call.id,
                    'call_evidence': state.self.evidence(state.node), 'conditions': copy.deepcopy(state.call.conditions),
                    'receiver_classes': _unique([value['class_type'] for value in state.receiver_sources
                        if value.get('class_type')]), 'runtime_target_confirmed': False,
                    'source_hashes': dict(state.self.analyzer.hashes), 'feasibility': 'not_proven'}]
        if state.container_result is not None:
            state.return_value =  state.container_result
            return True
        return False

    ## Assemble the call result sources and their evidence.
    ## 组装调用结果来源及其证据。
    #
    #  @param state Mutable state shared by the ordered call-analysis phases.
    #  @return True only when this phase completes the call with an early result.
    def _resolve_return_sources(self, state):
        state.result_value = {'kind': 'call_result', 'source': state.call_id,
                        'relation': 'direct',
                        'evidence': [state.self.evidence(state.node)],
                        'conditions': list(state.self.conditions)}
        if any(effect.get('kind') == 'mapping_remainder' and effect.get('return_path')
               for effect in state.call.effects):
            state.return_value =  state.call.result_sources
            return True
        state.returned_object = state.self.returned_container(
            state.selected_target, state.call, state.actual_values, state.env, state.node, state.effects_complete)
        if state.returned_object is not None:
            state.result_value['container_object'] = state.returned_object
            state.result_value['object_only'] = True
            state.result_value['conditions'] = _unique(state.result_value['conditions'] +
                state.returned_object.get('conditions', []))
            state.result_value['evidence'] = _unique(state.result_value['evidence'] +
                state.returned_object.pop('evidence'))
            state.call.result_sources = [state.result_value]
            state.return_value =  [state.result_value]
            return True
        if state.effects_complete and state.call.result_sources:
            state.return_value =  [state.result_value] + state.call.result_sources
            return True
        if state.constructor_class is not None and state.construction_safe:
            state.result_value['instance_type'] = asdict(state.constructor_class)
            state.mutations = state.self.class_lookup_effects(asdict(state.constructor_class), state.env)
            if state.mutations:
                state.result_value['class_lookup_mutations'] = copy.deepcopy(state.mutations)
            state.result_value['evidence'] = _unique(state.result_value['evidence'] + [
                evidence for value in state.callee_classes
                for evidence in value.get('evidence', [])])
            state.call.result_sources = [state.result_value]
        elif state.allocation_class is not None:
            state.result_value['instance_type'] = asdict(state.allocation_class)
            state.result_value['evidence'] = _unique(state.result_value['evidence'] + [
                evidence for value in state.allocation_values
                for evidence in value.get('evidence', [])])
            state.call.result_sources = [state.result_value]
            state.result_value['attribute_provenance'] = _unique([
                fact for value in state.allocation_values for fact in value.get('attribute_provenance', [])])
            state.result_value['conditions'] = _unique(state.result_value['conditions'] + [
                condition for value in state.allocation_values for condition in value.get('conditions', [])])
        elif state.allocation_candidates:
            state.result_value.update(instance_candidates=_unique([
                value['class_type'] for value in state.allocation_candidates]),
                value_incomplete=any(value.get('value_incomplete') for value in state.allocation_candidates),
                attribute_provenance=_unique([fact for value in state.allocation_candidates
                    for fact in value.get('attribute_provenance', [])]),
                conditions=_unique(state.result_value['conditions'] + [condition
                    for value in state.allocation_candidates for condition in value.get('conditions', [])]),
                evidence=_unique(state.result_value['evidence'] + [evidence
                    for value in state.allocation_candidates for evidence in value.get('evidence', [])]))
            state.call.result_sources = [state.result_value]
            if getattr(state.self.analyzer, '_conditional_source_state', False):
                state.result_value['instance_candidate_contexts'] = [
                    {'instance_type': copy.deepcopy(value['class_type']),
                     'conditions': copy.deepcopy(value.get('conditions', []))}
                    for value in state.allocation_candidates]
        elif (state.target and state.dispatch_kind == 'instance_method'
              and isinstance(state.node.func, ast.Attribute)
              and isinstance(state.node.func.value, ast.Name)
              and state.call.binding_status == 'complete'):
            state.field_types = state.self.analyzer._returned_field_instances(state.target)
            if state.field_types:
                state.values = []
                for state.item in state.field_types:
                    state.fact = {'field': state.item['field'],
                            'instance_type': state.item['instance_type'],
                            'assignment': state.self.evidence_at(
                                state.item['assignment_ref'], state.item['assignment_node']),
                            'returns': [state.self.evidence_at(state.item['return_ref'], path)
                                        for path in state.item['return_nodes']],
                            'accessor_call': state.self.evidence(state.node)}
                    state.call.receiver_type_evidence.append(state.fact)
                    state.values.append(dict(state.result_value,
                        instance_type=state.item['instance_type'],
                        receiver_type_evidence=[state.fact],
                        evidence=state.result_value['evidence'] +
                                 [state.fact['assignment']] + state.fact['returns']))
                state.return_value =  state.values
                return True
        state.return_value =  [state.result_value]
        return True
        return False
