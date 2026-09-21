## @package pcresolve.single_file_control_flow
#  Loop, branch, comprehension, and generator visitors for ownership analysis.

import ast
from dataclasses import replace

from .call_graph import IterationBinding
from .ownership_contracts import (
    _match_iterator_element_owner, _match_iterator_element_shape,
)
from .scope import Binding, SCOPE_COMPREHENSION, SCOPE_MODULE, merge_snapshots
from .sources import (
    CallResult, ContainerIter, DerivedResult, InstanceMethod, PythonShape,
    SourceSet, UnknownSource, make_source_set, normalize_source, source_display,
)


## Control-flow fact collection mixed into SingleFileAnalyzer.
class SingleFileControlFlowMixin:
    ## Seed Python shapes that can flow from one loop iteration to the next.
    #
    #  This is a bounded lexical fixed-point for builtin value shapes only.
    #  Every assignment to a candidate name inside the loop must independently
    #  prove the same PythonShape, and any conflicting preheader binding blocks
    #  the seed. Import-backed owners and unresolved values are never inferred.
    #  @param statements Statements in one loop body.
    #  @param excluded_names Loop-target names that are rebound by iteration.
    def _seed_loop_carried_python_shapes(self, statements,
                                         excluded_names=None):
        evidence = {}
        self._collect_loop_shape_assignments(statements, evidence)
        excluded = set(excluded_names or [])
        for name, observations in evidence.items():
            if name in excluded or not observations:
                continue
            if any(shape is None for shape, _ in observations):
                continue
            first_shape = observations[0][0]
            if any(shape != first_shape for shape, _ in observations[1:]):
                continue
            binding = self.current_scope().lookup(
                name, skip_parent_classes=True)
            if binding is not None:
                if (binding.container_kind != first_shape.kind
                        or binding.container_item_kind
                        != first_shape.item_kind):
                    continue
                continue
            source_node = observations[0][1]
            self._bind_target_name(
                name, first_shape, source_node,
                container_kind=first_shape.kind,
                container_item_kind=first_shape.item_kind)

    ## Collect same-loop assignment shapes without revisiting call nodes.
    #
    #  Nested lexical scopes are excluded. Control-flow bodies remain part of
    #  the loop backedge, but one unknown assignment invalidates convergence.
    #  @param statements Statements to scan.
    #  @param evidence Mutable name -> [(PythonShape or None, node)] mapping.
    def _collect_loop_shape_assignments(self, statements, evidence):
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                evidence.setdefault(statement.name, []).append(
                    (None, statement))
                header_nodes = list(statement.decorator_list)
                if isinstance(statement, (ast.FunctionDef,
                                          ast.AsyncFunctionDef)):
                    header_nodes.extend(statement.args.defaults)
                    header_nodes.extend(
                        item for item in statement.args.kw_defaults
                        if item is not None)
                else:
                    header_nodes.extend(statement.bases)
                    header_nodes.extend(item.value
                                        for item in statement.keywords)
                for header_node in header_nodes:
                    self._collect_loop_named_expr_bindings(
                        header_node, evidence)
                continue
            self._collect_loop_named_expr_bindings(statement, evidence)
            if isinstance(statement, ast.Assign):
                shape = self._expression_python_shape(statement.value)
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        evidence.setdefault(target.id, []).append(
                            (shape, statement))
                    else:
                        for name in self._assignment_target_names(target):
                            evidence.setdefault(name, []).append(
                                (None, statement))
                continue
            if isinstance(statement, ast.AnnAssign):
                if isinstance(statement.target, ast.Name):
                    shape = (
                        self._expression_python_shape(statement.value)
                        if statement.value is not None else None)
                    evidence.setdefault(statement.target.id, []).append(
                        (shape, statement))
                else:
                    for name in self._assignment_target_names(
                            statement.target):
                        evidence.setdefault(name, []).append(
                            (None, statement))
                continue
            if isinstance(statement, ast.AugAssign):
                target = statement.target
                if isinstance(target, ast.Name):
                    evidence.setdefault(target.id, []).append(
                        (None, statement))
                continue

            if isinstance(statement, (ast.For, ast.AsyncFor)):
                for name in self._assignment_target_names(statement.target):
                    evidence.setdefault(name, []).append((None, statement))
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                for item in statement.items:
                    if item.optional_vars is None:
                        continue
                    for name in self._assignment_target_names(
                            item.optional_vars):
                        evidence.setdefault(name, []).append(
                            (None, statement))
            elif isinstance(statement, ast.Try):
                for handler in statement.handlers:
                    if handler.name:
                        evidence.setdefault(handler.name, []).append(
                            (None, handler))
            elif isinstance(statement, ast.Delete):
                for target in statement.targets:
                    for name in self._assignment_target_names(target):
                        evidence.setdefault(name, []).append(
                            (None, statement))
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    name = alias.asname or alias.name.split(".", 1)[0]
                    evidence.setdefault(name, []).append((None, statement))
            elif isinstance(statement, ast.ImportFrom):
                for alias in statement.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    evidence.setdefault(name, []).append((None, statement))

            child_blocks = []
            if isinstance(statement, ast.If):
                child_blocks.extend((statement.body, statement.orelse))
            elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                child_blocks.extend((statement.body, statement.orelse))
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                child_blocks.append(statement.body)
            elif isinstance(statement, ast.Try):
                child_blocks.extend((statement.body, statement.orelse,
                                     statement.finalbody))
                child_blocks.extend(handler.body
                                    for handler in statement.handlers)
            for child_block in child_blocks:
                self._collect_loop_shape_assignments(child_block, evidence)

    ## Return lexical names bound by an assignment target.
    #  Attribute and subscript writes mutate objects but do not rebind their
    #  receiver names. Tuple, list, and starred targets are traversed.
    #  @param target Assignment-target AST node.
    #  @return Set of rebound lexical names.
    def _assignment_target_names(self, target):
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, ast.Starred):
            return self._assignment_target_names(target.value)
        if isinstance(target, (ast.Tuple, ast.List)):
            names = set()
            for item in target.elts:
                names.update(self._assignment_target_names(item))
            return names
        return set()

    ## Record assignment expressions as unknown loop-local rebindings.
    #  Named expressions may occur inside tests, call arguments, or container
    #  expressions. Their value shape is deliberately not inferred here.
    #  Nested lexical scopes do not share ordinary target bindings with the
    #  surrounding loop. Comprehension targets are ignored automatically, but
    #  assignment expressions inside comprehensions still bind outside them.
    #  @param node AST subtree to inspect.
    #  @param evidence Mutable loop-shape evidence mapping.
    def _collect_loop_named_expr_bindings(self, node, evidence):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Lambda)):
            return
        if isinstance(node, ast.NamedExpr):
            for name in self._assignment_target_names(node.target):
                evidence.setdefault(name, []).append((None, node))
        for child in ast.iter_child_nodes(node):
            self._collect_loop_named_expr_bindings(child, evidence)

    ## Visit a For node and bind the loop variable to the iterator source.
    #  @param node The For AST node.
    def visit_For(self, node):
        target_names = self._assignment_target_names(node.target)
        self._seed_loop_carried_python_shapes(node.body, target_names)
        yields = self._resolve_iterator_yields(node.iter, node.target)
        if isinstance(node.iter, ast.Name):
            binding = self.current_scope().lookup(
                node.iter.id, skip_parent_classes=True)
            # Deferred bodies cannot snapshot an enclosing mutable mapping.
            if binding is not None and binding.container_kind == "dict":
                key_kind = (self._mapping_facts.key_kind(node.iter)
                            if self.current_scope().bindings.get(
                                node.iter.id) is binding else None)
                if key_kind:
                    yields = [(node.target, PythonShape(key_kind), key_kind)]
                else:
                    yields = [(node.target, UnknownSource("unresolved dictionary key"))]
        if yields is not None:
            for item in yields:
                target_elt, source = item[:2]
                container_kind = item[2] if len(item) > 2 else ""
                container_item_kind = item[3] if len(item) > 3 else ""
                self._target_to_source(
                    target_elt, source, "iteration",
                    container_kind=container_kind,
                    container_item_kind=container_item_kind)
        else:
            source = self._iter_source(node.iter)
            item_kind = ""
            if isinstance(node.iter, ast.Name):
                item_kind = (
                    self._lookup_container_kind(node.iter.id, item=True)
                    or "")
            if not item_kind:
                shape = self._expression_python_shape(node.iter)
                item_kind = shape.item_kind if shape is not None else ""
            item_fields = self._expression_container_item_fields(node.iter)
            if item_fields and not item_kind:
                item_kind = "dict"
            if source is None and item_kind:
                source = PythonShape(item_kind)
            self._target_to_source(
                node.target, source, "iteration",
                container_kind=item_kind,
                container_item_fields=item_fields)
        self._record_iteration_binding(node)
        self.generic_visit(node)

    ## Visit a While node with bounded loop-carried Python shape evidence.
    #  @param node The While AST node.
    def visit_While(self, node):
        self._seed_loop_carried_python_shapes(node.body)
        self.generic_visit(node)

    ## Record a generator-loop fact for bounded cross-file propagation.
    #  @param node For-loop AST node.
    def _record_iteration_binding(self, node):
        if (not isinstance(node.iter, ast.Call)
                or not isinstance(node.target, ast.Name)
                or not self._caller_stack):
            return
        callee_name, _ = self._get_call_parts(node.iter)
        self.module_cg.iteration_bindings.append(IterationBinding(
            caller=self._caller_stack[-1],
            callee_name=callee_name,
            callee_source=self.trace_source(node.iter.func),
            target_names=[node.target.id],
            call_lineno=node.iter.lineno,
            call_col_offset=node.iter.col_offset,
        ))

    ## Resolve per-element ownership for one loop iterator expression.
    #  @param iter_node Iterator AST node.
    #  @param target Loop target AST node.
    #  @return Per-target source tuples, or None for the general fallback.
    def _resolve_iterator_yields(self, iter_node, target):
        if not isinstance(iter_node, ast.Call):
            return self._non_call_iterator_yields(iter_node, target)

        func_name = (
            iter_node.func.id if isinstance(iter_node.func, ast.Name)
            else None)
        result = self._os_walk_iterator_yields(
            iter_node, target, func_name)
        if result is not None:
            return result
        if isinstance(target, ast.Name):
            result = self._contract_iterator_yields(iter_node, target)
            if result is not None:
                return result
        if func_name is None:
            return None
        if isinstance(target, ast.Name):
            summary = self.module_cg.functions.get(func_name)
            if summary is not None and summary.yields is not None:
                return [(target, summary.yields)]
        return self._builtin_iterator_yields(iter_node, target, func_name)

    ## Resolve tuple fields yielded by a named or attribute container.
    #  @param iter_node Non-call iterator expression.
    #  @param target Loop target AST node.
    #  @return Positional source tuples or None.
    def _non_call_iterator_yields(self, iter_node, target):
        if not isinstance(target, (ast.Tuple, ast.List)):
            return None
        field_sources = None
        if isinstance(iter_node, ast.Name):
            field_sources = self._lookup_tuple_item_sources(iter_node.id)
        elif isinstance(iter_node, ast.Attribute):
            field_sources = self._lookup_attribute_tuple_item_sources(iter_node)
        if (field_sources is None
                or len(field_sources) != len(target.elts)):
            return None
        return list(zip(target.elts, field_sources))

    ## Resolve the fixed tuple contracts of os.walk and os.fwalk.
    #  @param iter_node Iterator Call AST node.
    #  @param target Loop target AST node.
    #  @param func_name Bare callee name when available.
    #  @return Positional Python-shape tuples or None.
    def _os_walk_iterator_yields(self, iter_node, target, func_name):
        owner, name = None, None
        if isinstance(iter_node.func, ast.Attribute):
            owner, name = self._resolve_func_top(iter_node.func)
            if owner is None and isinstance(iter_node.func.value, ast.Name):
                root = iter_node.func.value.id
                if root in self.import_aliases:
                    owner = self.symbols.get_top(root)
                    name = iter_node.func.attr
        elif func_name in self.import_from_symbols:
            imported = self.import_from_symbols[func_name]
            if imported in ("os.walk", "os.fwalk"):
                owner, name = imported.split(".", 1)
        if owner != "os" or name not in ("walk", "fwalk"):
            return None
        expected_arity = 3 if name == "walk" else 4
        if (not isinstance(target, (ast.Tuple, ast.List))
                or len(target.elts) != expected_arity):
            return None
        result = [
            (target.elts[0], "python", "str", ""),
            (target.elts[1], "python", "list", "str"),
            (target.elts[2], "python", "list", "str"),
        ]
        if expected_arity == 4:
            result.append((target.elts[3], "python", "", ""))
        return result

    ## Resolve explicit iterator contracts and iterator result evidence.
    #  @param iter_node Iterator Call AST node.
    #  @param target Name loop target.
    #  @return One target source tuple or None.
    def _contract_iterator_yields(self, iter_node, target):
        func_top, resolved_name = self._resolve_func_top(iter_node.func)
        element_owner = _match_iterator_element_owner(
            func_top, resolved_name)
        if element_owner is not None:
            element_shape = _match_iterator_element_shape(
                func_top, resolved_name)
            element_source = CallResult(
                InstanceMethod(func_top, resolved_name),
                call_lineno=iter_node.lineno,
                call_col_offset=iter_node.col_offset,
                result_source=element_shape or element_owner,
            )
            if element_shape is not None:
                return [(
                    target, element_source,
                    element_shape.kind, element_shape.item_kind)]
            return [(target, element_source)]
        traced = normalize_source(self.trace_source(iter_node))
        if isinstance(traced, CallResult):
            result_source = normalize_source(traced.result_source)
            if (isinstance(result_source, DerivedResult)
                    and result_source.kind == "iterator"
                    and result_source.sources):
                return [(target, result_source.sources[0])]
        return None

    ## Resolve builtin enumerate and zip positional yield behavior.
    #  @param iter_node Iterator Call AST node.
    #  @param target Loop target AST node.
    #  @param func_name Bare builtin name.
    #  @return Per-target source tuples or None.
    def _builtin_iterator_yields(self, iter_node, target, func_name):
        if func_name == "enumerate" and iter_node.args:
            container = iter_node.args[0]
            container_source = self._iterator_container_source(container)
            if isinstance(target, ast.Tuple) and len(target.elts) == 2:
                item_kind = ""
                if isinstance(container, ast.Name):
                    item_kind = (
                        self._lookup_container_kind(container.id, item=True)
                        or "")
                if item_kind:
                    return [(target.elts[0], "python"),
                            (target.elts[1], "python", item_kind, "")]
                item_source = (
                    ContainerIter(container_source)
                    if container_source else None)
                return [(target.elts[0], "python"),
                        (target.elts[1], item_source)]
            return [(target, "python")]

        if (func_name == "zip" and iter_node.args
                and isinstance(target, ast.Tuple)
                and len(target.elts) == len(iter_node.args)):
            result = []
            for element, argument in zip(target.elts, iter_node.args):
                source = self._iterator_container_source(argument)
                result.append((
                    element, ContainerIter(source) if source else None))
            return result
        return None
    ## Return the container identity for iterator yield resolution.
    #
    #  Preserves AST Name identity for container_items lookup;
    #  falls back to trace_source for complex expressions.
    #  @param node The container AST node.
    #  @return Name string or traced source.
    def _iterator_container_source(self, node):
        if isinstance(node, ast.Name):
            return node.id
        return self.trace_source(node)

    ## Visit an AsyncFor node and bind the loop variable to the iterator source.
    #  @param node The AsyncFor AST node.
    def visit_AsyncFor(self, node):
        target_names = self._assignment_target_names(node.target)
        self._seed_loop_carried_python_shapes(node.body, target_names)
        source = self._iter_source(node.iter)
        self._target_to_source(node.target, source, "iteration")
        self.generic_visit(node)

    ## Record one value yielded by the current generator function.
    #  @param node Yield AST node.
    def visit_Yield(self, node):
        if self._func_stack and self._caller_stack:
            if node.value is None:
                source = UnknownSource("bare yield")
            else:
                source = self._call_edge_argument_source(node.value)
                source = self._source_with_module(source)
                if source is None:
                    source = UnknownSource("unresolved yield")
            qualname = self._caller_stack[-1].qualname
            self.call_graph_yield_sources.setdefault(
                qualname, []).append(source)
        self.generic_visit(node)

    ## Record values forwarded by a yield-from expression.
    #  @param node YieldFrom AST node.
    def visit_YieldFrom(self, node):
        if self._func_stack and self._caller_stack:
            source = None
            if isinstance(node.value, ast.Call):
                callee_name = (
                    node.value.func.id
                    if isinstance(node.value.func, ast.Name) else None)
                if callee_name:
                    summary = self.module_cg.functions.get(callee_name)
                    if summary is not None:
                        source = summary.yields
            if source is None:
                source = self._call_edge_iterable_source(node.value)
            source = self._source_with_module(source)
            if source is None:
                source = UnknownSource("unresolved yield from")
            qualname = self._caller_stack[-1].qualname
            self.call_graph_yield_sources.setdefault(
                qualname, []).append(source)
        self.generic_visit(node)

    ## Visit an If node with lexical branch merging.
    #
    #  Snapshots the current scope before the if, visits each branch
    #  independently, then merges the resulting bindings. Module scope
    #  merges every changed binding. Function scope merges only names
    #  assigned directly by this branch; nested branches merge themselves.
    #  TYPE_CHECKING guards are skipped at all levels.
    #  @param node The If AST node.
    def visit_If(self, node):
        self.visit(node.test)
        receiver_guard = self._resolve_receiver_owner_guard(node.test)

        if self._is_type_checking_guard(node):
            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)
            return

        if self.current_scope().kind != SCOPE_MODULE:
            self._visit_function_if(node, receiver_guard)
            return

        scope_base = self.current_scope().snapshot()
        symbols_base = self.symbols.snapshot()

        self._visit_guarded_nodes(node.body, receiver_guard, node.test)
        scope_left = self.current_scope().snapshot()

        self.current_scope().restore(scope_base)
        self.symbols.restore(symbols_base)

        if node.orelse:
            for stmt in node.orelse:
                self.visit(stmt)
            scope_right = self.current_scope().snapshot()
        else:
            scope_right = scope_base

        merged = merge_snapshots(scope_base, scope_left, scope_right)
        for name, value in list(merged.items()):
            if not isinstance(value, Binding):
                merged[name] = Binding(
                    name=name, source=value,
                    scope_kind=self.current_scope().kind,
                )
        self.current_scope().restore(merged)
        for name, binding in merged.items():
            if isinstance(binding, Binding):
                self.symbols.add(name, binding.source)

    ## Visit a function-level if while merging only direct RHS evidence.
    #
    #  Calls inside each branch retain the established sequential visitor
    #  behavior. After both branches are visited, incompatible direct
    #  assignments are replaced by a function_branch SourceSet.
    #  @param node The function-level If node.
    #  @param receiver_guard Optional receiver narrowing evidence.
    def _visit_function_if(self, node, receiver_guard):
        scope_base = self.current_scope().snapshot()
        left_sources = self._direct_branch_assignment_sources(node.body)
        right_sources = self._direct_branch_assignment_sources(node.orelse)

        self._visit_guarded_nodes(node.body, receiver_guard, node.test)
        names = set(left_sources) | set(right_sources)
        # Restore only the independent mapping facts before the other branch.
        # The established ownership visitor retains its existing merge policy.
        for name in names:
            current = self.current_scope().bindings.get(name)
            if current is not None:
                self.current_scope().bindings[name] = replace(
                    current, mapping_value=getattr(
                        scope_base.get(name), "mapping_value", None))
        for statement in node.orelse:
            self.visit(statement)

        # No mapping join is claimed after a conditional rebind. Captured
        # calls inside each branch still have their branch-local evidence.
        for name in names:
            current = self.current_scope().bindings.get(name)
            if current is not None:
                self.current_scope().bindings[name] = replace(
                    current, mapping_value=None)
        for name in names:
            base_binding = scope_base.get(name)
            left_source = left_sources.get(
                name,
                base_binding.source if isinstance(base_binding, Binding)
                else None)
            right_source = right_sources.get(
                name,
                base_binding.source if isinstance(base_binding, Binding)
                else None)
            if left_source is None or right_source is None:
                continue
            left_binding = Binding(name, left_source)
            right_binding = Binding(name, right_source)
            if not self._branch_sources_require_merge(
                    left_binding, right_binding,
                    allow_local_callable=name.startswith("self.")):
                continue
            current = self.current_scope().lookup(name)
            if current is None:
                continue
            merged_source = make_source_set(
                (left_source, right_source), origin="function_branch")
            self.current_scope().bindings[name] = Binding(
                name=name,
                source=merged_source,
                scope_kind=current.scope_kind,
                lineno=current.lineno,
                col_offset=current.col_offset,
                assignment_index=current.assignment_index,
                version=current.version + 1,
                container_kind=current.container_kind,
                container_item_kind=current.container_item_kind,
                callable_key=current.callable_key,
                binding_kind=current.binding_kind,
            )
            if name.startswith("self.") and self._class_stack:
                self.instance_attrs[
                    (self._class_stack[-1], name)
                ] = merged_source

    ## Collect direct assignment RHS sources from branch statements.
    #
    #  Nested control-flow nodes are intentionally excluded because their
    #  own visitors merge their assignments.
    #  @param statements Statements belonging to the current branch.
    #  @return Mapping of assigned local name to RHS source.
    def _direct_branch_assignment_sources(self, statements):
        sources = {}

        def add_target(target, source):
            if isinstance(target, ast.Name):
                sources[target.id] = source
            elif isinstance(target, ast.Attribute):
                name = self._attribute_name(target)
                if name and name.startswith("self."):
                    sources[name] = source
            elif isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    add_target(element, source)

        for statement in statements:
            if isinstance(statement, ast.Assign):
                if isinstance(statement.value, ast.Subscript):
                    source = UnknownSource("branch_subscript")
                elif isinstance(statement.value, (
                        ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict)):
                    source = (self._expression_python_shape(statement.value)
                              or UnknownSource("branch_rhs"))
                else:
                    source = (
                        self.trace_source(statement.value)
                        or UnknownSource(
                            "branch_ifexp"
                            if isinstance(statement.value, ast.IfExp)
                            else "branch_rhs"))
                if (isinstance(statement.value, ast.Name)
                        and statement.value.id in self.import_from_symbols):
                    source = self.import_from_symbols[statement.value.id]
                for target in statement.targets:
                    add_target(target, source)
            elif isinstance(statement, ast.AnnAssign):
                if isinstance(statement.value, (
                        ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict)):
                    source = self._expression_python_shape(statement.value)
                else:
                    source = (
                        self.trace_source(statement.value)
                        if statement.value is not None else "local")
                if source is None:
                    source = UnknownSource("branch_rhs")
                add_target(statement.target, source)
            elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                for alias in statement.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if isinstance(statement, ast.ImportFrom):
                        sources[name] = statement.module or alias.name
                    else:
                        sources[name] = alias.name
        return sources

    ## Decide whether two branch bindings prove different owner identities.
    #
    #  Local function results deliberately share one coarse identity because
    #  their return ownership requires inter-procedural analysis. Explicit
    #  local constructors remain distinct from that coarse bucket.
    #  @param left_binding Binding produced by the true branch.
    #  @param right_binding Binding produced by the false branch.
    #  @param allow_local_callable Whether exact local callable alternatives
    #  are meaningful for this binding. This is limited to instance fields
    #  because ordinary local names already have established flow behavior.
    #  @return True when the bindings must remain a SourceSet.
    def _branch_sources_require_merge(self, left_binding, right_binding,
                                      allow_local_callable=False):
        if not (isinstance(left_binding, Binding)
                and isinstance(right_binding, Binding)):
            return False
        left_identity = self._branch_source_identity(left_binding.source)
        right_identity = self._branch_source_identity(right_binding.source)
        if left_identity == right_identity:
            return False
        left_kind = left_identity[0]
        right_kind = right_identity[0]
        if left_kind == "library" and right_kind == "library":
            return True
        if (allow_local_callable
                and (left_kind == "local_callable"
                     or right_kind == "local_callable")):
            return True
        kinds = {left_kind, right_kind}
        if "PythonShape" in kinds and kinds.issubset({
                "PythonShape", "UnknownSource", "local_result", "result",
                "InstanceMethod", "function_branch"}):
            return True
        # An unresolved assignment branch cannot be discarded merely
        # because the other branch is a function/method result.
        if "UnknownSource" in kinds and kinds.intersection(
                ("local_result", "result", "InstanceMethod")):
            return True
        if "function_branch" in kinds:
            return True
        if "local_class" in kinds and (
                "library" in kinds
                or ("UnknownSource" in kinds
                    and (
                        left_identity == (
                            "UnknownSource", "branch_ifexp")
                        or right_identity == (
                            "UnknownSource", "branch_ifexp")))):
            return True
        return False

    ## Return a coarse, evidence-backed identity for branch comparison.
    #  @param source Source value from a branch binding.
    #  @return Hashable identity tuple.
    def _branch_source_identity(self, source):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            return (
                source.origin or "set",
                tuple(sorted(
                    repr(self._branch_source_identity(item))
                    for item in source.sources)),
            )
        if isinstance(source, CallResult):
            result_source = normalize_source(source.result_source)
            if isinstance(result_source, str) and result_source:
                return ("result", result_source.split(".")[0])
            callee = source.callee
            if isinstance(callee, str):
                first = callee.split(".")[0]
                imported = self._imported_top_for_branch(first)
                if imported:
                    return ("library", imported)
                if callee in self.class_methods or first in self.class_methods:
                    return ("local_class", callee)
            return ("local_result",)
        if isinstance(source, str):
            if source in self.import_from_symbols.values():
                return ("local_callable", source)
            first = source.split(".")[0]
            imported = self._imported_top_for_branch(first)
            if imported:
                return ("library", imported)
            if source in self.class_methods or first in self.class_methods:
                return ("local_class", source)
            return (source if source in ("python", "unknown") else "local",)
        return (type(source).__name__, source_display(source))

    ## Resolve a single-file import name to its top-level library.
    #  @param name Root symbol used by a branch source.
    #  @return Top-level import name or an empty string.
    def _imported_top_for_branch(self, name):
        imported = self.import_from_symbols.get(name)
        if imported:
            return imported.split(".")[0]
        if name in self.import_aliases:
            direct = self.symbols.direct.get(name, name)
            if isinstance(direct, str):
                return direct.split(".")[0]
            return name.split(".")[0]
        return ""

    ## Visit a conditional expression with true-branch receiver narrowing.
    #
    #  @param node The IfExp AST node.
    def visit_IfExp(self, node):
        self.visit(node.test)
        receiver_guard = self._resolve_receiver_owner_guard(node.test)
        self._visit_guarded_nodes((node.body,), receiver_guard)
        self.visit(node.orelse)

    ## Check whether an If node guards on TYPE_CHECKING.
    #  @param node The If AST node.
    #  @return True if the test is a bare TYPE_CHECKING reference.
    def _is_type_checking_guard(self, node):
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            return True
        if isinstance(node.test, ast.Attribute):
            if node.test.attr == "TYPE_CHECKING":
                return True
        return False

    ## Visit a Try node with conservative lexical branch merging.
    #
    #  At module level, each except handler and the else clause are treated
    #  as independent branches merged conservatively.  At function level,
    #  falls back to generic_visit (deferred to Phase 6 CFG).
    #  @param node The Try AST node.
    def visit_Try(self, node):
        if self.current_scope().kind != SCOPE_MODULE:
            self.generic_visit(node)
            return

        scope_base = self.current_scope().snapshot()
        symbols_base = self.symbols.snapshot()

        for stmt in node.body:
            self.visit(stmt)
        scope_try = self.current_scope().snapshot()
        symbols_try = self.symbols.snapshot()

        all_branches = [scope_try]
        for handler in node.handlers:
            self.current_scope().restore(scope_base)
            self.symbols.restore(symbols_base)
            if handler.type:
                self.visit(handler.type)
            if handler.name:
                self._bind_target_name(handler.name, "local", handler, "variable")
            for stmt in handler.body:
                self.visit(stmt)
            all_branches.append(self.current_scope().snapshot())

        if node.orelse:
            self.current_scope().restore(scope_try)
            self.symbols.restore(symbols_try)
            for stmt in node.orelse:
                self.visit(stmt)
            all_branches.append(self.current_scope().snapshot())

        merged = scope_base
        for branch in all_branches:
            merged = merge_snapshots(scope_base, merged, branch)
        for name, value in list(merged.items()):
            if not isinstance(value, Binding):
                merged[name] = Binding(
                    name=name, source=value,
                    scope_kind=self.current_scope().kind,
                )
        self.current_scope().restore(merged)

        for name, binding in merged.items():
            if isinstance(binding, Binding):
                self.symbols.add(name, binding.source)

        for stmt in node.finalbody:
            self.visit(stmt)

    ## Common handler for all comprehension node types.
    #  @param node A ListComp, SetComp, DictComp, or GeneratorExp AST node.
    def _visit_comprehension(self, node):
        self.push_scope(SCOPE_COMPREHENSION, "<comprehension>")
        for gen in node.generators:
            target_names = [
                item.id for item in ast.walk(gen.target)
                if isinstance(item, ast.Name)
            ]
            self.comprehension_targets.update(target_names)
            source = self._iter_source(gen.iter)
            self._target_to_source(gen.target, source)
        self.generic_visit(node)
        self.pop_scope()

    ## Visit a ListComp node and bind loop variables to the iterator source.
    #  @param node The ListComp AST node.
    def visit_ListComp(self, node):
        self._visit_comprehension(node)

    ## Visit a DictComp node and bind loop variables to the iterator source.
    #  @param node The DictComp AST node.
    def visit_DictComp(self, node):
        self._visit_comprehension(node)

    ## Visit a SetComp node and bind loop variables to the iterator source.
    #  @param node The SetComp AST node.
    def visit_SetComp(self, node):
        self._visit_comprehension(node)

    ## Visit a GeneratorExp node and bind loop variables to the iterator source.
    #  @param node The GeneratorExp AST node.
    def visit_GeneratorExp(self, node):
        self._visit_comprehension(node)

    ## Visit a Global node and mark names for module-scope routing.
    #  @param node The Global AST node.
    def visit_Global(self, node):
        for name in node.names:
            self._global_names.add(name)
        self.generic_visit(node)

    ## Visit a Nonlocal node. First edition: no-crash only.
    #  @param node The Nonlocal AST node.
    def visit_Nonlocal(self, node):
        self.generic_visit(node)
