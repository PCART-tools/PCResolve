## @package pcresolve.single_file_binding_resolution
#  Bind decorated targets, assignment targets, iterators, and finite guards.
#
#  The mixin shares SingleFileAnalyzer lexical state so binding time and AST
#  traversal order remain unchanged.

import ast

from .builtin_ownership import _is_builtin
from .ownership_contracts import _TYPE_GUARD_OWNER_CONTRACTS
from .scope import SCOPE_MODULE
from .single_file_call_collection import _is_unshadowed_builtin_call
from .sources import (
    CallResult, ContainerIter, ParameterSource, PythonShape, UnknownSource,
    make_source_set, normalize_source,
)


## Resolve flow-sensitive bindings using SingleFileAnalyzer state.
class SingleFileBindingResolutionMixin:

    ## --- Decorator binding ---

    ## Record decorator evidence without overwriting the target's primary binding.
    #
    #  Each decorator expression is traced and recorded as a separate
    #  provenance record (kind="decorated_by"), while the decorated
    #  function/class keeps its "local" primary identity.
    #  @param target_name Name of the decorated function/class.
    #  @param decorator_nodes List of decorator AST nodes.
    def _bind_decorated_target(self, target_name, decorator_nodes):
        if not decorator_nodes:
            return
        for deco in reversed(decorator_nodes):
            deco_source = self.trace_source(deco)
            if not deco_source or (isinstance(deco_source, str) and _is_builtin(deco_source)):
                continue
            if deco_source == "local" and isinstance(deco, ast.Name):
                fn = deco.id
                rs = self.return_sources.get(fn)
                if rs is not None and not (isinstance(rs, str) and rs == "local"):
                    deco_source = rs
                else:
                    deco_source = fn
            self._add_symbol_ref(
                target_name, deco_source, "decorated_by", deco)

    ## --- Assignment helpers ---

    ## Record a project-local callable assigned onto an imported class.
    #
    #  The fact identifies a possible monkey patch. It does not prove that an
    #  arbitrary receiver from the same library has the patched runtime class;
    #  cross-file classification therefore uses it only to remove false
    #  certainty from a library owner.
    #  @param node Assignment node.
    def _record_external_method_override(self, node):
        local_callable = False
        if isinstance(node.value, ast.Lambda):
            local_callable = True
        elif isinstance(node.value, ast.Name):
            binding = self.current_scope().lookup(
                node.value.id, skip_parent_classes=True)
            local_callable = (
                binding is not None
                and (
                    bool(binding.callable_key)
                    or binding.source == "local"
                )
            )
        if not local_callable:
            return

        wildcard_tops = {
            module.split(".")[0] for module in self.wildcard_modules
            if isinstance(module, str) and module
        }
        scope_name = (
            self.current_scope().name
            if self.current_scope().kind != SCOPE_MODULE else "")
        for target in node.targets:
            if (not isinstance(target, ast.Attribute)
                    or not isinstance(target.value, ast.Name)):
                continue
            class_symbol = target.value.id
            qualified = self.import_from_symbols.get(class_symbol)
            if qualified:
                owner = qualified.split(".")[0]
            else:
                direct = normalize_source(
                    self.symbols.direct.get(class_symbol))
                if (isinstance(direct, str)
                        and direct not in (
                            "", "local", "python", "unknown")):
                    owner = direct.split(".")[0]
                elif len(wildcard_tops) == 1:
                    owner = next(iter(wildcard_tops))
                else:
                    continue
            key = (owner, target.attr)
            self.external_method_overrides.setdefault(key, []).append(
                (scope_name, node.lineno, class_symbol))

    ## Bind assignment targets to a source value.
    #
    #  Handles simple names, self.attr, and tuple/list unpacking.
    #  @param target The assignment target AST node.
    #  @param source The source symbol or structured tuple.
    def _target_to_source(self, target, source, kind="variable",
                          container_kind="", container_item_kind="",
                          container_item_fields=None):
        if not source:
            return
        if isinstance(target, ast.Name):
            self._bind_target_name(
                target.id, source, target, kind,
                container_kind=container_kind,
                container_item_kind=container_item_kind,
                container_item_fields=container_item_fields)
            return
        if isinstance(target, ast.Attribute):
            name = self._attribute_name(target)
            attr_name = name if name and name.startswith("self.") else (
                self._instance_attribute_target_name(name))
            if attr_name:
                self._bind_target_name(attr_name, source, target, "attribute")
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._target_to_source(
                    elt, source, kind,
                    container_kind=container_kind,
                    container_item_kind=container_item_kind,
                    container_item_fields=container_item_fields)

    ## Trace the source of a for-loop iterator.
    #  @param iter_node The iterator AST node.
    #  @return Source symbol, structured tuple, or None.
    def _iter_source(self, iter_node):
        if isinstance(iter_node, ast.Name):
            container_name = iter_node.id
            binding = self.current_scope().lookup(
                container_name, skip_parent_classes=True)
            item_source = (
                self._iterated_append_sources.get(
                    self._binding_key(binding))
                if binding is not None else None)
            if item_source is not None:
                return item_source
            item_source = self.homogeneous_container_items.get(
                container_name)
            if item_source is not None:
                if binding is None or binding.scope_kind == SCOPE_MODULE:
                    return item_source
            has_items = False
            for k in self.container_items.keys():
                if k[0] == container_name:
                    has_items = True
                    break
            has_set = container_name in self.container_set_sources
            if ((has_items or has_set) and binding is not None
                    and binding.container_kind in ("dict", "list", "tuple", "set")):
                return ContainerIter(container_name)
        parameter_source = self._parameter_dependency_source(iter_node)
        if parameter_source is not None:
            return ContainerIter(parameter_source)
        source = self.trace_source(iter_node)
        source_norm = normalize_source(source)
        if (isinstance(source_norm, CallResult)
                and isinstance(source_norm.callee, str)
                and source_norm.callee in self.return_element_sources):
            return ContainerIter(source_norm)
        if (isinstance(source_norm, CallResult)
                and isinstance(
                    normalize_source(source_norm.callee), ContainerIter)
                and source_norm.result_source is None):
            return UnknownSource("unresolved iterator element")
        if isinstance(normalize_source(source), ParameterSource):
            return ContainerIter(source)
        if source:
            return source
        return self.get_base(iter_node)

    ## Resolve a true-branch receiver-owner guard.
    #
    #  @param test_node Conditional expression.
    #  @return (receiver_name, owner) or None.
    def _resolve_receiver_owner_guard(self, test_node):
        if (not isinstance(test_node, ast.Call)
                or not test_node.args
                or not isinstance(test_node.args[0], ast.Name)):
            return None
        if (_is_unshadowed_builtin_call(self, test_node)
                and isinstance(test_node.func, ast.Name)
                and test_node.func.id == "isinstance"
                and len(test_node.args) == 2
                and isinstance(test_node.args[1], ast.Name)
                and test_node.args[1].id in (
                    "list", "dict", "set", "tuple", "str")):
            return (
                test_node.args[0].id,
                PythonShape(test_node.args[1].id),
            )
        if len(test_node.args) != 1:
            return None
        func_top, func_name = self._resolve_func_top(test_node.func)
        for (lib_prefix, name), contract in (
                _TYPE_GUARD_OWNER_CONTRACTS.items()):
            if (name == func_name
                    and func_top is not None
                    and (func_top == lib_prefix
                         or func_top.startswith(lib_prefix + "."))):
                return (test_node.args[0].id, contract[0])
        return None

    ## Visit nodes under an optional receiver-owner guard.
    #
    #  @param nodes Iterable of AST nodes.
    #  @param guard Optional (receiver_name, owner) pair.
    #  @param test Optional branch condition for finite-name narrowing.
    def _visit_guarded_nodes(self, nodes, guard, test=None):
        finite = self._finite_name_guard(test, nodes)
        if finite is not None:
            self._finite_name_guards.append(finite)
        if guard is not None:
            self._receiver_owner_guards.append({guard[0]: guard[1]})
        try:
            for child in nodes:
                self.visit(child)
        finally:
            if guard is not None:
                self._receiver_owner_guards.pop()
            if finite is not None:
                self._finite_name_guards.pop()

    ## Read a finite string-name guard without evaluating project code.
    #  @param test Branch condition.
    #  @param nodes Guarded statements.
    #  @return Expression key and allowed strings, or None.
    def _finite_name_guard(self, test, nodes):
        if (not isinstance(test, ast.Compare) or len(test.ops) != 1
                or not isinstance(test.ops[0], ast.In)
                or not isinstance(test.left, (ast.Name, ast.Attribute))
                or not isinstance(test.comparators[0], (ast.List, ast.Tuple, ast.Set))):
            return None
        choices = test.comparators[0].elts
        if (not choices or len(choices) > 32 or any(
                not isinstance(item, ast.Constant) or not isinstance(item.value, str)
                for item in choices)):
            return None
        root = test.left
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        if isinstance(test.left, ast.Name):
            shape = self._expression_python_shape(test.left)
            if shape is None or shape.kind != "str":
                return None
        if (isinstance(test.left, ast.Attribute)
                and self._expression_python_shape(test.left) is None):
            field = self.current_scope().lookup(
                self._attribute_name(test.left), skip_parent_classes=True)
            if field is None or field.binding_kind != 'attribute' or field.source != 'python':
                return None
        mutated_roots = set()

        def escaped_roots(value):
            if isinstance(value, ast.Name):
                return {value.id}
            if isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
                return set().union(*(escaped_roots(child)
                                     for child in ast.iter_child_nodes(value)))
            return set()

        for statement in nodes:
            for child in ast.walk(statement):
                if (isinstance(child, ast.Name) and child.id == root.id
                        and isinstance(child.ctx, (ast.Store, ast.Del))):
                    return None
                if isinstance(child, ast.Attribute) and isinstance(child.ctx, (ast.Store, ast.Del)):
                    base = child.value
                    while isinstance(base, ast.Attribute):
                        base = base.value
                    if isinstance(base, ast.Name):
                        mutated_roots.add(base.id)
                if isinstance(child, (ast.Assign, ast.AnnAssign)):
                    mutated_roots.update(escaped_roots(child.value))
                if isinstance(child, ast.Call):
                    for arg in list(child.args) + [kw.value for kw in child.keywords]:
                        mutated_roots.update(escaped_roots(arg))
                    if isinstance(child.func, ast.Attribute):
                        base = child.func.value
                        while isinstance(base, ast.Attribute):
                            base = base.value
                        if isinstance(base, ast.Name) and base.id == root.id:
                            return None
                if isinstance(child, ast.Call) and any(
                        isinstance(arg, ast.Name) and arg.id == root.id
                        for arg in list(child.args) + [kw.value for kw in child.keywords]
                        ):
                    if not (_is_unshadowed_builtin_call(self, child)
                            and child.func.id == 'eval'):
                        return None
        if root.id in mutated_roots:
            return None
        return (ast.dump(test.left, include_attributes=False),
                tuple(item.value for item in choices), id(self.current_scope()),
                mutated_roots)

    ## Resolve only finite qualified-name eval expressions as value identities.
    #  @param node Call expression.
    #  @return SourceSet of possible names, or None for open evaluation.
    def _finite_eval_names(self, node):
        if (not self._finite_name_guards or len(node.args) != 1 or node.keywords
                or not _is_unshadowed_builtin_call(self, node)
                or node.func.id != 'eval' or not isinstance(node.args[0], ast.JoinedStr)):
            return None
        candidates = ['']
        mutated_roots = set()
        for part in node.args[0].values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                values = (part.value,)
            elif (isinstance(part, ast.FormattedValue) and part.conversion == -1
                  and part.format_spec is None):
                key = ast.dump(part.value, include_attributes=False)
                guard = next((guard for guard in reversed(self._finite_name_guards)
                              if guard[0] == key and guard[2] == id(self.current_scope())), None)
                values = guard[1] if guard is not None else None
                if values is None:
                    return None
                mutated_roots.update(guard[3])
            else:
                return None
            candidates = [prefix + value for prefix in candidates for value in values]
            if len(candidates) > 32:
                return None
        sources = []
        for candidate in candidates:
            try:
                expression = ast.parse(candidate, mode='eval').body
            except SyntaxError:
                return None
            if not isinstance(expression, ast.Attribute):
                return None
            parts = self._attribute_chain_list(expression)
            if not parts or parts[0] not in self.import_aliases:
                return None
            if parts[0] in mutated_roots:
                return None
            if not self._finite_namespace_is_stable(parts[0]):
                return None
            binding = self.current_scope().lookup(parts[0], skip_parent_classes=True)
            if binding is None or binding.binding_kind != 'import':
                return None
            sources.append('.'.join(parts))
        return make_source_set(sources, origin='finite_name_selection')

    ## Reject namespace writes or escapes before narrowing an eval result.
    #  @param name Imported module binding name.
    #  @return True only for read-only attribute access in this module.
    def _finite_namespace_is_stable(self, name):
        if name in self._finite_namespace_stability:
            return self._finite_namespace_stability[name]
        tree = self._module_tree
        if tree is None:
            return False
        parents = {id(child): node for node in ast.walk(tree)
                   for child in ast.iter_child_nodes(node)}
        stable = True
        for node in ast.walk(tree):
            if not isinstance(node, ast.Name) or node.id != name:
                continue
            parent = parents.get(id(node))
            if (not isinstance(node.ctx, ast.Load)
                    or not isinstance(parent, ast.Attribute)
                    or parent.value is not node):
                stable = False
                break
            while isinstance(parent, ast.Attribute):
                if not isinstance(parent.ctx, ast.Load):
                    stable = False
                    break
                node = parent
                parent = parents.get(id(node))
            if isinstance(parent, ast.Call) and parent.func is node:
                stable = False
            if not stable:
                break
        self._finite_namespace_stability[name] = stable
        return stable
