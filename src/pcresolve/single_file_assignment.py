## @package pcresolve.single_file_assignment
#  Collect assignment and container-binding facts during single-file analysis.
#
#  The mixin operates on SingleFileAnalyzer visitor state so lexical binding
#  timing, target positions, and container invalidation remain unchanged.

import ast

from .ownership_contracts import (
    _has_result_owner_contract, _match_result_item_owner,
)
from .scope import SCOPE_MODULE
from .sources import (
    CallResult, ContainerItem, DerivedResult, InstanceMethod, UnknownSource,
    make_source_set, normalize_source,
)


## Trace an expression used as a builtin result candidate.
#
#  Literal values are Python-owned.  Other expressions retain their full
#  source IR so cross-file resolution can preserve every possible owner.
#  @param node Candidate AST expression.
#  @param trace_fn Callable to trace an AST expression.
#  @return Source value or UnknownSource.
def _builtin_value_source(node, trace_fn):
    if isinstance(node, ast.Constant):
        return "python"
    source = trace_fn(node)
    if source is not None:
        return source
    return UnknownSource("builtin value")


## Collect assignment facts using SingleFileAnalyzer state.
class SingleFileAssignmentMixin:
    ## Shared assignment pipeline: pending targets, trace RHS, visit, call_assign_funcs.
    #
    #  @param node The Assign or AnnAssign AST node.
    #  @param target_names Flat list of target name strings.
    #  @param field_target_names Instance-field targets used for bounded
    #  expression-owner propagation.
    #  @return The traced RHS source (right-hand value).
    def _visit_assignment(self, node, target_names,
                          field_target_names=None):
        imported_call = self._imported_call_result_source(node.value)
        pending_targets = list(target_names)
        pending_targets.extend(field_target_names or [])
        if pending_targets and isinstance(node.value, ast.Call):
            self._pending_call_targets_by_node[
                id(node.value)] = pending_targets
        right = self._assignment_right_source(node.value)
        right = self._method_result_assignment_source(node.value, right)
        right = self._conversion_assignment_source(node.value, right)
        right = self._operator_assignment_source(node.value, right)
        right = self._local_method_assignment_source(node.value, right)
        self.generic_visit(node)
        self._update_assigned_call_sources(target_names, imported_call)
        self._update_call_assignment_funcs(node.value, target_names)
        return right

    ## Trace the right-hand source, including positional result contracts.
    def _assignment_right_source(self, value):
        result_item_owner = None
        if (isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Call)):
            result_item_owner = self._resolve_call_result_item_owner(
                value.value)
        return (result_item_owner
                or self._parameter_dependency_source(value)
                or self.trace_source(value))

    ## Wrap an imported method result that has an explicit owner contract.
    def _method_result_assignment_source(self, value, right):
        normalized = normalize_source(right)
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Attribute)
                or not isinstance(normalized, InstanceMethod)
                or not isinstance(
                    normalize_source(normalized.receiver), CallResult)
                or normalized.receiver.result_source is not None
                or not _has_result_owner_contract(normalized.method)):
            return right
        return CallResult(
            normalized,
            display_name=ast.unparse(value.func),
            call_lineno=value.lineno,
            call_col_offset=value.col_offset,
            result_source=DerivedResult(
                "method_result", (normalized,), value.func.attr),
        )

    ## Apply a proven conversion-result owner to the assignment source.
    def _conversion_assignment_source(self, value, right):
        conversion = self._resolve_conversion_target(value)
        if not conversion:
            return right
        normalized = normalize_source(right)
        if isinstance(normalized, CallResult):
            return CallResult(
                normalized.callee,
                display_name=normalized.display_name,
                call_lineno=normalized.call_lineno,
                call_col_offset=normalized.call_col_offset,
                result_source=conversion,
            )
        return conversion

    ## Preserve converged same-scope operator ownership evidence.
    def _operator_assignment_source(self, value, right):
        if not isinstance(value, (ast.BinOp, ast.UnaryOp)):
            return right
        expression_top = self._expr_receiver_top(value)
        normalized = normalize_source(right)
        has_parameter = self._source_contains_parameter(normalized)
        if (not has_parameter
                and expression_top not in (
                    None, "", "local", "python", "unknown")):
            if (normalized in (None, "", "local", "unknown")
                    or isinstance(normalized, (
                        UnknownSource, DerivedResult))):
                return expression_top
            return right
        if has_parameter:
            return right
        external_tops = {
            top for top in self._operator_operand_tops(value)
            if top not in (None, "", "local", "python", "unknown")
        }
        if len(external_tops) > 1:
            return UnknownSource("conflicting operator result owners")
        return right

    ## Wrap a local method call with its local return identity.
    def _local_method_assignment_source(self, value, right):
        normalized = normalize_source(right)
        local_receiver = (
            self._returned_local_class_name(normalized.receiver)
            if isinstance(normalized, InstanceMethod) else None)
        if (not isinstance(value, ast.Call)
                or local_receiver is None
                or normalized.method not in self.class_methods[local_receiver]):
            return right
        return CallResult(
            right,
            display_name=ast.unparse(value.func),
            call_lineno=value.lineno,
            call_col_offset=value.col_offset,
            result_source=right,
        )

    ## Replace flow-sensitive assigned-call metadata after RHS visitation.
    def _update_assigned_call_sources(self, target_names, imported_call):
        for name in target_names:
            key = (id(self.current_scope()), name)
            if imported_call is None:
                self._assigned_call_sources.pop(key, None)
            else:
                self._assigned_call_sources[key] = imported_call

    ## Record the dotted callee assigned to each target name.
    def _update_call_assignment_funcs(self, value, target_names):
        while isinstance(value, ast.Attribute):
            value = value.value
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Attribute)):
            return
        func_full = self._attribute_name(value.func)
        if not func_full:
            return
        for name in target_names:
            self.call_assign_funcs[name] = func_full

    ## Visit an Assign node and record symbol bindings.
    #
    #  Handles dict/list/tuple/set container tracking, and traces the
    #  right-hand side to bind target symbols.
    #  @param node The Assign AST node.
    def visit_Assign(self, node):
        mapping_value = self._mapping_facts.value(node.value)
        container_kind, item_kind = self._expression_container_shape(
            node.value)
        item_fields = self._expression_container_item_fields(node.value)
        container_kind = container_kind or None
        item_kind = item_kind or None
        self._invalidate_assignment_container_facts(node)
        self._record_literal_assignment(node)
        self._record_dict_assignment(node)
        self._record_sequence_assignment(node)
        self._record_set_assignment(node)
        self._record_comprehension_assignment(node)
        self._record_constructor_container_assignment(node)
        self._sync_assignment_container_kinds(
            node, container_kind, item_kind)
        targets, field_targets = self._assign_statement_target_names(node)
        right = self._visit_assignment(node, targets, field_targets)
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                self._invalidate_attribute_tuple_item_sources(target)
        self._record_local_constructor_fields(node, targets)
        self._record_external_method_override(node)
        right, callable_keys = self._lambda_assignment_source(
            node, targets, right)
        if right:
            self._bind_traced_assignment_targets(
                node, right, callable_keys, container_kind,
                item_kind, item_fields)
        else:
            self._bind_local_assignment_targets(
                node, callable_keys, container_kind,
                item_kind, item_fields)
        subscript_value_kind = container_kind
        if (subscript_value_kind is None
                and isinstance(node.value, ast.Name)):
            subscript_value_kind = self._lookup_container_kind(
                node.value.id)
        for target in node.targets:
            self._record_subscript_item_kind(
                target, subscript_value_kind)
            self._bind_mapping_value(target, mapping_value)
        self._record_iterable_binding_source(node)
        self._collect_argparse_assignment(node)

    ## Invalidate module-level comprehension and append facts on rebind.
    def _invalidate_assignment_container_facts(self, node):
        if self.current_scope().kind != SCOPE_MODULE:
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            is_self_assignment = (
                isinstance(node.value, ast.Name)
                and node.value.id == target.id)
            if is_self_assignment:
                continue
            self.homogeneous_container_items.pop(target.id, None)
            self.homogeneous_container_tuple_items.pop(target.id, None)
            binding = self.current_scope().lookup(
                target.id, skip_parent_classes=True)
            if binding is None:
                continue
            binding_key = self._binding_key(binding)
            self._iterated_append_tuple_sources.pop(binding_key, None)
            self._iterated_append_tuple_conflicts.discard(binding_key)

    ## Record scalar literals used by static key resolution.
    def _record_literal_assignment(self, node):
        if (not isinstance(node.value, ast.Constant)
                or not isinstance(node.value.value, (str, int))):
            return
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._literal_values[target.id] = node.value.value

    ## Record dictionary key/value and homogeneous-value facts.
    def _record_dict_assignment(self, node):
        if not isinstance(node.value, ast.Dict):
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            container_name = target.id
            self.container_kinds[container_name] = "dict"
            value_sources = []
            for key_node, value_node in zip(
                    node.value.keys, node.value.values):
                if not isinstance(key_node, ast.Constant):
                    continue
                key_value = key_node.value
                value_source = (
                    "python" if isinstance(value_node, ast.Constant)
                    else self._value_source(value_node))
                if value_source:
                    self.container_items[
                        (container_name, key_value)] = value_source
                    value_sources.append(normalize_source(value_source))
            owners = {
                self._structured_source_owner_top(source)
                for source in value_sources
            }
            owners.discard(None)
            if (value_sources
                    and len(value_sources) == len(node.value.values)
                    and len(owners) == 1):
                self.homogeneous_container_value_sources[
                    container_name] = make_source_set(
                        value_sources, origin="dict_values")
            else:
                self.homogeneous_container_value_sources.pop(
                    container_name, None)

    ## Record literal list/tuple item sources and lengths.
    def _record_sequence_assignment(self, node):
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            container_name = target.id
            self.container_lengths[container_name] = len(node.value.elts)
            self.container_kinds[container_name] = (
                "list" if isinstance(node.value, ast.List) else "tuple")
            for index, element in enumerate(node.value.elts):
                value_source = _builtin_value_source(
                    element, self.get_base)
                if value_source:
                    self.container_items[
                        (container_name, index)] = value_source

    ## Record literal set element sources.
    def _record_set_assignment(self, node):
        if not isinstance(node.value, ast.Set):
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            self.container_kinds[target.id] = "set"
            bases = set()
            for element in node.value.elts:
                base = _builtin_value_source(element, self.get_base)
                if base:
                    bases.add(base)
            if bases:
                self.container_set_sources[target.id] = bases

    ## Record container kinds and item sources for comprehensions.
    def _record_comprehension_assignment(self, node):
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if isinstance(node.value, ast.ListComp):
                self.container_kinds[target.id] = "list"
                if self.current_scope().kind == SCOPE_MODULE:
                    tuple_sources = self._expression_tuple_item_sources(
                        node.value)
                    if tuple_sources is not None:
                        self.homogeneous_container_tuple_items[
                            target.id] = tuple_sources
                    else:
                        self.homogeneous_container_tuple_items.pop(
                            target.id, None)
                    item_source = self.trace_source(node.value.elt)
                    if item_source is not None:
                        self.homogeneous_container_items[
                            target.id] = item_source
                else:
                    self.homogeneous_container_tuple_items.pop(
                        target.id, None)
            elif isinstance(node.value, ast.SetComp):
                self.container_kinds[target.id] = "set"
            elif isinstance(node.value, ast.DictComp):
                self.container_kinds[target.id] = "dict"
            elif (isinstance(node.value, ast.Constant)
                  and isinstance(node.value.value, str)):
                self.container_kinds[target.id] = "str"

    ## Record builtin constructor and defaultdict item kinds.
    def _record_constructor_container_assignment(self, node):
        if (not isinstance(node.value, ast.Call)
                or not isinstance(node.value.func, ast.Name)):
            return
        func_id = node.value.func.id
        if func_id in ("list", "dict", "set", "tuple", "str"):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = func_id
        if func_id != "defaultdict" or not node.value.args:
            return
        factory = node.value.args[0]
        if (not isinstance(factory, ast.Name)
                or factory.id not in (
                    "list", "dict", "set", "tuple", "str")):
            return
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.container_item_kinds[target.id] = factory.id

    ## Synchronize legacy container maps with the inferred assignment shape.
    def _sync_assignment_container_kinds(
            self, node, container_kind, item_kind):
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if container_kind:
                self.container_kinds[target.id] = container_kind
            else:
                self.container_kinds.pop(target.id, None)
            if item_kind:
                self.container_item_kinds[target.id] = item_kind
            else:
                self.container_item_kinds.pop(target.id, None)

    ## Collect simple and instance-field assignment target names.
    def _assign_statement_target_names(self, node):
        targets = []
        field_targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                targets.extend(
                    element.id for element in target.elts
                    if isinstance(element, ast.Name))
            elif isinstance(target, ast.Attribute):
                name = self._attribute_name(target)
                if name and name.startswith("self."):
                    field_targets.append(name)
        return targets, field_targets

    ## Register a local lambda summary and return its assignment source.
    def _lambda_assignment_source(self, node, targets, right):
        callable_keys = {}
        if not isinstance(node.value, ast.Lambda):
            return right, callable_keys
        lambda_result = right or UnknownSource("lambda result")
        lambda_key = self._local_lambda_key(node.value)
        for name in targets:
            callable_keys[name] = lambda_key
        self.return_sources[lambda_key] = lambda_result
        return "local", callable_keys

    ## Bind every target to the traced right-hand source.
    def _bind_traced_assignment_targets(
            self, node, right, callable_keys, container_kind,
            item_kind, item_fields):
        normalized = normalize_source(right)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._bind_traced_name_target(
                    target, right, normalized, callable_keys,
                    container_kind, item_kind, item_fields)
            elif isinstance(target, ast.Attribute):
                self._bind_traced_attribute_target(
                    node, target, right, normalized,
                    container_kind, item_kind, item_fields)
            elif isinstance(target, (ast.Tuple, ast.List)):
                self._bind_unpacked_assignment_target(
                    node, target, right, normalized)

    ## Bind one simple name while preserving self-assignment semantics.
    def _bind_traced_name_target(
            self, target, right, normalized, callable_keys,
            container_kind, item_kind, item_fields):
        if (isinstance(normalized, InstanceMethod)
                and normalized.receiver == target.id):
            return
        if (isinstance(normalized, CallResult)
                and (normalized.callee == target.id
                     or (isinstance(normalized.callee, str)
                         and normalized.callee.startswith(target.id + ".")))):
            return
        if isinstance(right, str) and right == target.id:
            return
        self._bind_target_name(
            target.id, right, target,
            container_kind=container_kind or "",
            container_item_kind=item_kind or "",
            callable_key=callable_keys.get(target.id, ""),
            container_item_fields=item_fields)

    ## Bind one attribute target with imported-result preservation.
    def _bind_traced_attribute_target(
            self, node, target, right, normalized,
            container_kind, item_kind, item_fields):
        name = self._attribute_name(target)
        attr_name = name if name and name.startswith("self.") else (
            self._instance_attribute_target_name(name))
        if not attr_name:
            return
        if isinstance(normalized, InstanceMethod):
            preserve_imported_result = (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and self._is_import_backed_receiver_expression(
                    node.value.func.value)
                and self._resolve_func_top(node.value.func)[0]
                == self._structured_source_owner_top(normalized.receiver))
            if not preserve_imported_result:
                return
        attr_source = right
        if isinstance(node.value, ast.Name) and right == "local":
            attr_source = node.value.id
        self._bind_target_name(
            attr_name, attr_source, target,
            container_kind=container_kind or "",
            container_item_kind=item_kind or "",
            container_item_fields=item_fields)

    ## Bind positional elements of one tuple/list assignment target.
    def _bind_unpacked_assignment_target(
            self, node, target, right, normalized):
        unpacked_owner = None
        if isinstance(node.value, ast.Call):
            func_top, func_name = self._resolve_func_top(node.value.func)
            unpacked_owner = _match_result_item_owner(func_top, func_name)
        for index, element in enumerate(target.elts):
            if not isinstance(element, ast.Name):
                continue
            if (isinstance(node.value, (ast.Tuple, ast.List))
                    and index < len(node.value.elts)):
                dependency = self._parameter_dependency_source(
                    node.value.elts[index])
                if dependency is not None:
                    self._bind_target_name(
                        element.id, dependency, element)
                    continue
            if unpacked_owner is not None:
                self._bind_target_name(
                    element.id, unpacked_owner, element)
                continue
            if (isinstance(node.value, ast.Call)
                    and isinstance(normalized, CallResult)):
                self._bind_target_name(element.id, right, element)
                self._assigned_call_sources[
                    (id(self.current_scope()), element.id)
                ] = ContainerItem(normalized, index)
                continue
            if isinstance(node.value, ast.Name):
                dependency = self._parameter_dependency_source(node.value)
                self._bind_target_name(
                    element.id,
                    ContainerItem(dependency or node.value.id, index),
                    element)
                continue
            if isinstance(normalized, InstanceMethod):
                if isinstance(normalized.receiver, str):
                    receiver_top = self.symbols.get_top(normalized.receiver)
                    if receiver_top:
                        result_owner = _match_result_item_owner(
                            receiver_top, normalized.method)
                        if result_owner:
                            self._bind_target_name(
                                element.id, result_owner, element)
                            continue
                    self._bind_target_name(
                        element.id, normalized.receiver, element)
                continue
            self._bind_target_name(element.id, right, element)

    ## Bind unresolved assignment targets to the conservative local source.
    def _bind_local_assignment_targets(
            self, node, callable_keys, container_kind,
            item_kind, item_fields):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._bind_target_name(
                    target.id, "local", target,
                    container_kind=container_kind or "",
                    container_item_kind=item_kind or "",
                    callable_key=callable_keys.get(target.id, ""),
                    container_item_fields=item_fields)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    if isinstance(element, ast.Name):
                        self._bind_target_name(
                            element.id, "local", element)
            elif isinstance(target, ast.Attribute):
                name = self._attribute_name(target)
                if name and name.startswith("self."):
                    self._bind_target_name(
                        name, "local", target,
                        container_kind=container_kind or "",
                        container_item_kind=item_kind or "",
                        container_item_fields=item_fields)
