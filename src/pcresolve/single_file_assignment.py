## @package pcresolve.single_file_assignment
#  Collect assignment and container-binding facts during single-file analysis.
#
#  The mixin operates on SingleFileAnalyzer visitor state so lexical binding
#  timing, target positions, and container invalidation remain unchanged.

import ast

from .ownership_contracts import _match_result_item_owner
from .scope import SCOPE_MODULE
from .sources import (
    CallResult, ContainerItem, InstanceMethod, UnknownSource,
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
    ## Visit an Assign node and record symbol bindings.
    #
    #  Handles dict/list/tuple/set container tracking, and traces the
    #  right-hand side to bind target symbols.
    #  @param node The Assign AST node.
    def visit_Assign(self, node):
        mapping_value = self._mapping_facts.value(node.value)
        assignment_container_kind, assignment_item_kind = (
            self._expression_container_shape(node.value))
        assignment_item_fields = self._expression_container_item_fields(
            node.value)
        assignment_container_kind = assignment_container_kind or None
        assignment_item_kind = assignment_item_kind or None

        # Homogeneous comprehension evidence is flow-sensitive at module
        # scope. Any real rebind invalidates the previous element source.
        if self.current_scope().kind == SCOPE_MODULE:
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                is_self_assignment = (
                    isinstance(node.value, ast.Name)
                    and node.value.id == target.id
                )
                if not is_self_assignment:
                    self.homogeneous_container_items.pop(
                        target.id, None)
                    self.homogeneous_container_tuple_items.pop(
                        target.id, None)
                    binding = self.current_scope().lookup(
                        target.id, skip_parent_classes=True)
                    if binding is not None:
                        binding_key = self._binding_key(binding)
                        self._iterated_append_tuple_sources.pop(
                            binding_key, None)
                        self._iterated_append_tuple_conflicts.discard(
                            binding_key)

        ## Track literal assignments for static key resolution (PR7).
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (str, int)):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._literal_values[target.id] = node.value.value

        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    self.container_kinds[container_name] = "dict"
                    value_sources = []
                    for key_node, value_node in zip(node.value.keys, node.value.values):
                        if isinstance(key_node, ast.Constant):
                            key_value = key_node.value
                            if isinstance(value_node, ast.Constant):
                                value_source = "python"
                            else:
                                value_source = self._value_source(value_node)
                            if value_source:
                                self.container_items[(container_name, key_value)] = value_source
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

        if isinstance(node.value, (ast.List, ast.Tuple)):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    n = len(node.value.elts)
                    self.container_lengths[container_name] = n
                    self.container_kinds[container_name] = (
                        "list" if isinstance(node.value, ast.List) else "tuple")
                    for i, elt in enumerate(node.value.elts):
                        value_source = _builtin_value_source(
                            elt, self.get_base)
                        if value_source:
                            self.container_items[(container_name, i)] = value_source

        if isinstance(node.value, ast.Set):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    container_name = target.id
                    self.container_kinds[container_name] = "set"
                    bases = set()
                    for elt in node.value.elts:
                        base = _builtin_value_source(elt, self.get_base)
                        if base:
                            bases.add(base)
                    if bases:
                        self.container_set_sources[container_name] = bases

        # 1.0.5 P1: track container kinds for comprehensions and constructors.
        if isinstance(node.value, ast.ListComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
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
                    else:
                        self.homogeneous_container_tuple_items.pop(
                            target.id, None)
                    if self.current_scope().kind == SCOPE_MODULE:
                        item_source = self.trace_source(node.value.elt)
                        if item_source is not None:
                            self.homogeneous_container_items[
                                target.id] = item_source
        if isinstance(node.value, ast.SetComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "set"
        if isinstance(node.value, ast.DictComp):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "dict"
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.container_kinds[target.id] = "str"
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            func_id = node.value.func.id
            if func_id in ("list", "dict", "set", "tuple", "str"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.container_kinds[target.id] = func_id
            # 1.0.5 P1+: track defaultdict(list) / defaultdict(dict) etc.
            # so d[k].append(v) can be classified from the item kind.
            if func_id == "defaultdict" and len(node.value.args) >= 1:
                factory = node.value.args[0]
                if isinstance(factory, ast.Name):
                    factory_name = factory.id
                    if factory_name in ("list", "dict", "set", "tuple", "str"):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                self.container_item_kinds[target.id] = factory_name

        # Keep compatibility maps flow-sensitive. Lexical Binding metadata is
        # authoritative, while these maps support older module-level paths.
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if assignment_container_kind:
                self.container_kinds[
                    target.id] = assignment_container_kind
            else:
                self.container_kinds.pop(target.id, None)
            if assignment_item_kind:
                self.container_item_kinds[
                    target.id] = assignment_item_kind
            else:
                self.container_item_kinds.pop(target.id, None)

        ## Collect assignment target names and delegate to shared pipeline.
        targets = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        targets.append(elt.id)
        field_targets = []
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                name = self._attribute_name(target)
                if name and name.startswith("self."):
                    field_targets.append(name)
        right = self._visit_assignment(node, targets, field_targets)
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                self._invalidate_attribute_tuple_item_sources(target)
        self._record_local_constructor_fields(node, targets)
        self._record_external_method_override(node)
        callable_keys = {}
        if isinstance(node.value, ast.Lambda):
            lambda_result = right or UnknownSource("lambda result")
            lambda_key = self._local_lambda_key(node.value)
            for name in targets:
                callable_keys[name] = lambda_key
            self.return_sources[lambda_key] = lambda_result
            # The lambda expression defines a project-local callable. Its
            # body source describes only the object returned by that call.
            right = "local"
        if right:
            right_norm = normalize_source(right)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if (
                        isinstance(right_norm, InstanceMethod)
                        and right_norm.receiver == target.id
                    ):
                        continue
                    if (
                        isinstance(right_norm, CallResult)
                        and (
                            right_norm.callee == target.id
                            or (isinstance(right_norm.callee, str)
                                and right_norm.callee.startswith(
                                    target.id + ".")))
                    ):
                        continue
                    ## skip self-assign: df = df[...] where right resolves to "df"
                    if isinstance(right, str) and right == target.id:
                        continue
                    self._bind_target_name(
                        target.id, right, target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(target.id, ""),
                        container_item_fields=assignment_item_fields)
                elif isinstance(target, ast.Attribute):
                    name = self._attribute_name(target)
                    attr_name = name if name and name.startswith("self.") else (
                        self._instance_attribute_target_name(name))
                    if attr_name:
                        if isinstance(right_norm, InstanceMethod):
                            preserve_imported_result = (
                                isinstance(node.value, ast.Call)
                                and isinstance(node.value.func, ast.Attribute)
                                and self._is_import_backed_receiver_expression(
                                    node.value.func.value)
                                and self._resolve_func_top(
                                    node.value.func)[0]
                                == self._structured_source_owner_top(
                                    right_norm.receiver))
                            if not preserve_imported_result:
                                continue
                        attr_source = right
                        if (isinstance(node.value, ast.Name)
                                and right == "local"):
                            attr_source = node.value.id
                        self._bind_target_name(
                            attr_name, attr_source, target,
                            container_kind=assignment_container_kind or "",
                            container_item_kind=assignment_item_kind or "",
                            container_item_fields=assignment_item_fields)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    unpacked_owner = None
                    if isinstance(node.value, ast.Call):
                        func_top, func_name = self._resolve_func_top(
                            node.value.func)
                        unpacked_owner = _match_result_item_owner(
                            func_top, func_name)
                    for index, elt in enumerate(target.elts):
                        if isinstance(elt, ast.Name):
                            if (isinstance(node.value, (ast.Tuple, ast.List))
                                    and index < len(node.value.elts)):
                                dependency = self._parameter_dependency_source(
                                    node.value.elts[index])
                                if dependency is not None:
                                    self._bind_target_name(
                                        elt.id, dependency, elt)
                                    continue
                            if unpacked_owner is not None:
                                self._bind_target_name(
                                    elt.id, unpacked_owner, elt)
                                continue
                            if (isinstance(node.value, ast.Call)
                                    and isinstance(right_norm, CallResult)):
                                # Keep the selected position when a local
                                # tuple-return call is forwarded as an
                                # argument before project summaries exist.
                                selected_source = ContainerItem(
                                    right_norm, index)
                                self._bind_target_name(
                                    elt.id, right, elt)
                                self._assigned_call_sources[
                                    (id(self.current_scope()), elt.id)
                                ] = selected_source
                                continue
                            # Preserve positional provenance when unpacking a
                            # named value.  Flattening every element to the
                            # traced top (often "local" for a parameter)
                            # allows a module-level symbol with the same name
                            # to leak back in during cross-file resolution.
                            if isinstance(node.value, ast.Name):
                                dependency = self._parameter_dependency_source(
                                    node.value)
                                self._bind_target_name(
                                    elt.id,
                                    ContainerItem(
                                        dependency or node.value.id, index),
                                    elt)
                                continue
                            if isinstance(right_norm, InstanceMethod):
                                if isinstance(right_norm.receiver, str):
                                    # 1.0.5 P1: consult result-owner map
                                    # before binding.  linalg.svd(arr)
                                    # returns numpy arrays even though
                                    # linalg is scipy.
                                    rcvr_top = self.symbols.get_top(
                                        right_norm.receiver)
                                    if rcvr_top:
                                        ret = _match_result_item_owner(
                                            rcvr_top, right_norm.method)
                                        if ret:
                                            self._bind_target_name(
                                                elt.id, ret, elt)
                                            continue
                                    self._bind_target_name(
                                        elt.id, right_norm.receiver, elt)
                                continue
                            self._bind_target_name(elt.id, right, elt)
        else:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._bind_target_name(
                        target.id, 'local', target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(target.id, ""),
                        container_item_fields=assignment_item_fields)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            self._bind_target_name(elt.id, 'local', elt)
                elif isinstance(target, ast.Attribute):
                    name = self._attribute_name(target)
                    if name and name.startswith("self."):
                        self._bind_target_name(
                            name, 'local', target,
                            container_kind=assignment_container_kind or "",
                            container_item_kind=assignment_item_kind or "",
                            container_item_fields=assignment_item_fields)
        subscript_value_kind = assignment_container_kind
        if (subscript_value_kind is None
                and isinstance(node.value, ast.Name)):
            subscript_value_kind = self._lookup_container_kind(
                node.value.id)
        for target in node.targets:
            self._record_subscript_item_kind(
                target, subscript_value_kind)
            self._bind_mapping_value(target, mapping_value)
        self._record_iterable_binding_source(node)
        # 1.0.5 P0: generic_visit already called above, before target binding.
        self._collect_argparse_assignment(node)
