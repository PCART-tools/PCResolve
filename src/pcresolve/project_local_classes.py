## @package pcresolve.project_local_classes
#  Local class identity, inheritance, and callable-instance evidence.

import ast

from .sources import (
    CallResult, ContainerItem, ContainerIter, InstanceMethod,
    ParameterSource, SourceSet, normalize_source, source_display,
)


## Project local-class reasoning mixed into ProjectAnalyzer.
class ProjectLocalClassesMixin:
    ## Find one instance-field binding on a local class or its local bases.
    #  @param module Defining module of the candidate class.
    #  @param class_name Candidate class name.
    #  @param attribute Normalized ``self.<field>`` path.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Inheritance recursion guard.
    #  @return List of (module, source) bindings.
    def _local_class_attribute_bindings(
            self, module, class_name, attribute, tracers, visited=None):
        identity = (module, class_name)
        seen = set(visited or set())
        if identity in seen:
            return []
        seen.add(identity)
        module_cg = self.project_cg.modules.get(module)
        class_summary = (
            module_cg.classes.get(class_name)
            if module_cg is not None else None)
        if class_summary is None:
            return []
        if attribute in class_summary.attrs:
            return [(module, class_summary.attrs[attribute])]

        bindings = []
        tracer = tracers.get(module)
        if tracer is None:
            return []
        for base_symbol in tracer.class_bases.get(class_name, []):
            base_identity = self._resolve_local_class_identity(
                module, base_symbol, tracers)
            if base_identity is None:
                continue
            bindings.extend(self._local_class_attribute_bindings(
                base_identity[0], base_identity[1], attribute, tracers,
                seen))
        return self._dedupe_list(bindings)

    ## Identify a project-local class constructor source.
    #  @param module Module containing the source.
    #  @param source Source to inspect.
    #  @return (module, class name) or None.
    def _local_class_from_source(self, module, source):
        source = normalize_source(source)
        if isinstance(source, CallResult):
            source = normalize_source(source.callee)
        if not isinstance(source, str):
            return None
        cg = getattr(self, "project_cg", None)
        if cg is None:
            return None
        if module in cg.modules and source in cg.modules[module].classes:
            return (module, source)
        parts = source.split(".")
        for index in range(len(parts) - 1, 0, -1):
            candidate_module = ".".join(parts[:index])
            candidate_class = ".".join(parts[index:])
            module_cg = cg.modules.get(candidate_module)
            if module_cg and candidate_class in module_cg.classes:
                return (candidate_module, candidate_class)
        return None

    ## Resolve a local class returned by a local class or static method.
    #
    #  This follows only an explicit return summary. It does not infer a
    #  class from a method name or from a variable spelling. Every return
    #  branch must resolve to a project-local class; multiple classes remain
    #  ambiguous and are resolved conservatively by the caller.
    #  @param module Module containing the call result.
    #  @param source CallResult representing a method call.
    #  @param tracers Dict of module name to analyzer.
    #  @return List of unique local class identities.
    def _local_class_from_method_result(self, module, source, tracers):
        source = normalize_source(source)
        if not isinstance(source, CallResult):
            return []
        callee = source.callee
        if not isinstance(callee, str) or "." not in callee:
            return []
        caller_tracer = tracers.get(module)
        identities = []
        for candidate_module, module_cg in self.project_cg.modules.items():
            for class_name, class_summary in module_cg.classes.items():
                for method_name, method_summary in class_summary.methods.items():
                    qualified_class = candidate_module + "." + class_name
                    qualified_method = qualified_class + "." + method_name
                    spellings = {qualified_method}
                    if candidate_module == module:
                        spellings.add(class_name + "." + method_name)
                    if caller_tracer is not None:
                        parts = callee.split(".")
                        prefix = parts[0]
                        imported = caller_tracer.import_from_symbols.get(
                            prefix)
                        if (isinstance(imported, str)
                                and imported + "." + method_name
                                == qualified_method):
                            spellings.add(callee)
                        direct = normalize_source(
                            caller_tracer.symbols.direct.get(prefix))
                        if (isinstance(direct, str)
                                and direct == candidate_module
                                and len(parts) == 3
                                and parts[1] == class_name
                                and parts[2] == method_name):
                            spellings.add(callee)
                    if callee not in spellings:
                        continue
                    returns = normalize_source(method_summary.returns)
                    if returns is None:
                        continue
                    return_sources = (
                        list(returns.sources)
                        if isinstance(returns, SourceSet)
                        else [returns]
                    )
                    returned_classes = []
                    for returned in return_sources:
                        returned = normalize_source(returned)
                        if returned == "self":
                            returned_classes.append(
                                (candidate_module, class_name))
                            continue
                        if isinstance(returned, CallResult):
                            returned = returned.callee
                        identity = self._local_class_from_source(
                            candidate_module, returned)
                        if identity is None:
                            returned_classes = []
                            break
                        returned_classes.append(identity)
                    if returned_classes:
                        identities.extend(self._dedupe_list(returned_classes))
        return self._dedupe_list(identities)

    ## Resolve local classes returned by a project-local function.
    #
    #  The function must have an explicit return summary whose every branch
    #  resolves to one project-local constructor.  This deliberately does not
    #  infer a class from a function name, argument type, or method spelling.
    #  @param module Module containing the call site.
    #  @param callee Callee spelling from a CallResult.
    #  @param tracers Dict of module name to analyzer.
    #  @return List of unique local class identities.
    def _local_classes_from_function_result(self, module, callee, tracers):
        if not isinstance(callee, str):
            return []
        candidates = []
        caller_tracer = tracers.get(module)
        if caller_tracer is not None:
            imported = caller_tracer.import_from_symbols.get(callee)
            if isinstance(imported, str):
                candidates.append((module, imported))

        parts = callee.split(".")
        for index in range(len(parts), 0, -1):
            candidate_module = ".".join(parts[:index])
            if candidate_module in tracers:
                candidates.append((
                    candidate_module, ".".join(parts[index:])))
                break
        candidates.append((module, callee))

        identities = []
        seen = set()
        for target_module, qualname in candidates:
            key = (target_module, qualname)
            if key in seen or not qualname:
                continue
            seen.add(key)
            tracer = tracers.get(target_module)
            if tracer is None:
                continue
            returns = tracer.return_sources.get(qualname)
            if returns is None and target_module == module:
                returns = tracer.return_sources.get(parts[-1])
            if returns is None:
                continue
            normalized = normalize_source(returns)
            returned_sources = (
                list(normalized.sources)
                if isinstance(normalized, SourceSet)
                else [normalized]
            )
            branch_identities = []
            for returned in returned_sources:
                returned = normalize_source(returned)
                if isinstance(returned, CallResult):
                    returned = returned.callee
                identity = self._local_class_from_source(
                    target_module, returned)
                if identity is None:
                    branch_identities = []
                    break
                branch_identities.append(identity)
            if branch_identities:
                identities.extend(branch_identities)
        return self._dedupe_list(identities)

    ## Check whether a local class owns a method through local inheritance.
    #  @param module Defining module of the class.
    #  @param class_name Local class name.
    #  @param method_name Method name.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard.
    #  @return True when the method is locally defined or locally inherited.
    def _local_class_defines_method(self, module, class_name, method_name,
                                    tracers, visited=None):
        key = (module, class_name, method_name)
        seen = set(visited or set())
        if key in seen:
            return False
        seen.add(key)
        module_cg = self.project_cg.modules.get(module)
        if module_cg is None:
            return False
        class_summary = module_cg.classes.get(class_name)
        if class_summary is None:
            return False
        if method_name in class_summary.methods:
            return True
        tracer = tracers.get(module)
        if tracer is None:
            return False
        for base_symbol in class_summary.bases:
            base_identity = self._resolve_local_class_identity(
                module, base_symbol, tracers)
            if base_identity and self._local_class_defines_method(
                    base_identity[0], base_identity[1], method_name,
                    tracers, seen):
                return True
        return False

    ## Resolve a project-local class through imports and package re-exports.
    #
    #  @param module Module where the class symbol is referenced.
    #  @param source Class symbol or constructor source.
    #  @param tracers Dict of module name to analyzer.
    #  @return (defining module, class name) or None.
    def _resolve_local_class_identity(self, module, source, tracers):
        direct = self._local_class_from_source(module, source)
        if direct is not None:
            return direct
        source = normalize_source(source)
        if isinstance(source, CallResult):
            source = normalize_source(source.callee)
        if not isinstance(source, str):
            return None
        chain = self.trace_symbol(module, source, tracers, set())
        cg = getattr(self, "project_cg", None)
        if cg is None:
            return None
        for index in range(len(chain) - 1, 0, -1):
            class_name = chain[index]
            class_module = chain[index - 1]
            if not isinstance(class_name, str):
                continue
            module_cg = cg.modules.get(class_module)
            if module_cg and class_name in module_cg.classes:
                return (class_module, class_name)
        return None

    ## Return whether one project-local class derives from another.
    #
    #  @param candidate_module Defining module of the candidate subclass.
    #  @param candidate_class Candidate subclass name.
    #  @param base_module Defining module of the required base class.
    #  @param base_class Required base class name.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard for cyclic or malformed hierarchies.
    #  @return True for identity or transitive local inheritance.
    def _local_class_is_or_derives(
            self, candidate_module, candidate_class,
            base_module, base_class, tracers, visited=None):
        candidate = (candidate_module, candidate_class)
        required = (base_module, base_class)
        if candidate == required:
            return True
        seen = set(visited or set())
        if candidate in seen:
            return False
        seen.add(candidate)
        tracer = tracers.get(candidate_module)
        if tracer is None:
            return False
        for base_symbol in tracer.class_bases.get(candidate_class, []):
            identity = self._resolve_local_class_identity(
                candidate_module, base_symbol, tracers)
            if identity is None:
                continue
            if self._local_class_is_or_derives(
                    identity[0], identity[1],
                    base_module, base_class, tracers, seen):
                return True
        return False

    ## Collect project-local runtime class candidates for a receiver source.
    #
    #  Explicit constructors and statically tracked container elements provide
    #  class-level dispatch evidence. An empty result means the source cannot
    #  constrain dispatch, not that the receiver is non-local.
    #  @param module Module where the source is evaluated.
    #  @param source Receiver source.
    #  @param tracers Dict of module name to analyzer.
    #  @param visited Recursion guard.
    #  @return List of (defining module, class name) tuples.
    def _local_class_candidates(
            self, module, source, tracers, visited=None):
        source = normalize_source(source)
        key = (module, type(source).__name__, source_display(source))
        seen = set(visited or set())
        if key in seen:
            return []
        seen.add(key)

        if isinstance(source, CallResult):
            method_classes = self._local_class_from_method_result(
                module, source, tracers)
            if method_classes:
                return method_classes
            function_classes = self._local_classes_from_function_result(
                module, source.callee, tracers)
            if function_classes:
                return function_classes
            callable_classes = self._local_callable_class_candidates(
                module, source, tracers.get(module), tracers, seen)
            if callable_classes:
                return callable_classes
            identity = self._local_class_from_source(
                module, source.callee)
            return [identity] if identity is not None else []
        identity = self._resolve_local_class_identity(
            module, source, tracers)
        if identity is not None:
            return [identity]
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._local_class_candidates(
                    module, item, tracers, set(seen)))
            return self._dedupe_list(candidates)
        if isinstance(source, ContainerItem):
            resolved = self._resolve_container_item(
                module, source.container, source.index, tracers)
            if resolved is None:
                return []
            return self._local_class_candidates(
                resolved[0], resolved[1], tracers, seen)
        if isinstance(source, ContainerIter):
            container = normalize_source(source.container)
            if not isinstance(container, str):
                return self._local_class_candidates(
                    module, container, tracers, seen)
            tracer = tracers.get(module)
            if tracer is None:
                return []
            candidates = []
            for (container_name, _), item_source in (
                    tracer.container_items.items()):
                if container_name == container:
                    candidates.extend(self._local_class_candidates(
                        module, item_source, tracers, set(seen)))
            for item_source in tracer.container_set_sources.get(
                    container, set()):
                candidates.extend(self._local_class_candidates(
                    module, item_source, tracers, set(seen)))
            return self._dedupe_list(candidates)
        return []

    ## Resolve a constructor-injected callable field of a parameter object.
    #  @param module Module containing the field call.
    #  @param source Parameter-backed field-call source.
    #  @param tracers All project analyzers.
    #  @param seen Callable-source recursion guard.
    #  @return Complete local callable class candidates, or an empty list.
    def _parameter_callable_field_classes(self, module, source, tracers, seen):
        key = (module, source.parameter_scope, source.parameter_name, source.method)
        if key in self._callable_field_in_progress:
            return []
        tracer = tracers.get(module)
        params = (tracer.function_params.get(source.parameter_scope, [])
                  if tracer is not None else [])
        if source.parameter_name not in params:
            return []
        # A write outside an initializer invalidates constructor-only evidence.
        run = self._ownership_run
        if run.constructor_only_fields is None:
            fields, blocked = set(), set()
            for candidate in tracers.values():
                tree = candidate._module_tree
                if tree is None:
                    continue
                parents = {id(child): node for node in ast.walk(tree)
                           for child in ast.iter_child_nodes(node)}
                for node in ast.walk(tree):
                    if (not isinstance(node, ast.Attribute)
                            or not isinstance(node.ctx, (ast.Store, ast.Del))):
                        continue
                    parent = parents.get(id(node))
                    while parent is not None and not isinstance(
                            parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parent = parents.get(id(parent))
                    fields.add(node.attr)
                    if (not isinstance(node.ctx, ast.Store)
                            or not isinstance(node.value, ast.Name)
                            or node.value.id != 'self'
                            or parent is None or parent.name != '__init__'
                            or not isinstance(parents.get(id(parent)), ast.ClassDef)):
                        blocked.add(node.attr)
            run.constructor_only_fields = fields - blocked
            self._constructor_only_fields = run.constructor_only_fields
        if source.method not in run.constructor_only_fields:
            return []
        self._callable_field_in_progress.add(key)
        try:
            arguments = self._parameter_call_arguments(
                module, source.parameter_scope, source.parameter_name,
                params.index(source.parameter_name), tracer, tracers)
            if self._callable_field_receiver_escapes(module, source, arguments, tracers):
                return []
            classes = []
            for origin, receiver in arguments:
                identity = self._resolve_local_class_identity(origin, receiver, tracers)
                if identity is None or not isinstance(receiver, CallResult):
                    return []
                bindings = self._local_class_attribute_bindings(
                    identity[0], identity[1], 'self.' + source.method, tracers)
                if not bindings:
                    return []
                contexts = self._bounded_call_contexts(
                    origin, receiver.call_lineno, receiver.call_col_offset, tracers,
                    callee_name=receiver.display_name)
                for binding_module, binding in bindings:
                    binding = normalize_source(binding)
                    if isinstance(binding, ParameterSource):
                        matching = [context for context in contexts
                                    if context.target.module == binding_module
                                    and context.target.qualname == binding.scope]
                        if (len(matching) != 1 or binding.derived
                                or binding.attributes
                                or not binding.scope.endswith('.__init__')):
                            return []
                        binding = self._bounded_argument_source(matching[0], binding.name)
                        binding_module = matching[0].caller_module
                    values = (binding.sources if isinstance(binding, SourceSet)
                              else (binding,))
                    for value in values:
                        candidates = self._local_callable_class_candidates(
                            binding_module, value, tracers.get(binding_module), tracers,
                            visited=seen)
                        if not candidates:
                            return []
                        classes.extend(candidates)
            return self._dedupe_list(classes)
        finally:
            self._callable_field_in_progress.remove(key)

    ## Reject object escapes that could overwrite an injected callable field.
    #  @param module Field-call module.
    #  @param source Parameter-backed field-call source.
    #  @param arguments Concrete receiver constructor sources.
    #  @param tracers Project analyzers.
    #  @return True when a receiver is passed elsewhere or aliased ambiguously.
    def _callable_field_receiver_escapes(self, module, source, arguments, tracers):
        names = {(module, source.parameter_scope): {source.parameter_name}}
        identities = []
        for origin, receiver in arguments:
            if not isinstance(receiver, CallResult):
                return True
            identity = self._resolve_local_class_identity(origin, receiver, tracers)
            if identity is None:
                return True
            if not self._constructor_field_method_is_readonly(
                    identity, '__init__', source.method, tracers):
                return True
            identities.append(identity)
            cg = self.project_cg.modules.get(origin)
            for edge in cg.edges if cg is not None else ():
                if (edge.call_lineno == receiver.call_lineno
                        and edge.call_col_offset == receiver.call_col_offset):
                    names.setdefault((origin, edge.caller.qualname), set()).update(
                        edge.assigned_to)

        def carries_name(node, tracked):
            if isinstance(node, ast.Name):
                return node.id in tracked
            if isinstance(node, ast.Attribute):
                return False
            return any(carries_name(child, tracked)
                       for child in ast.iter_child_nodes(node))

        for (origin, scope), tracked in names.items():
            tree = tracers[origin]._module_tree
            calls = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    calls.setdefault((node.lineno, node.col_offset), []).append(node)
            # Alias assignments may hide an escape inside a container argument.
            # Keep this constructor-only path conservative until aliases carry
            # object mutation facts of their own.
            for node in ast.walk(tree):
                if (isinstance(node, (ast.Assign, ast.AnnAssign))
                        and node.value is not None
                        and carries_name(node.value, tracked)
                        and isinstance(node.value, (ast.Name, ast.List, ast.Tuple, ast.Dict))):
                    return True
            for edge in self.project_cg.modules[origin].edges:
                if edge.caller.qualname != scope:
                    continue
                candidates = calls.get((edge.call_lineno, edge.call_col_offset), [])
                if len(candidates) > 1:
                    candidates = [node for node in candidates
                                  if ast.unparse(node.func) == edge.callee_name]
                if len(candidates) != 1:
                    return True
                call = candidates[0]
                receiver = call.func
                attributes = []
                while isinstance(receiver, ast.Attribute):
                    attributes.append(receiver.attr)
                    receiver = receiver.value
                if (isinstance(receiver, ast.Name) and receiver.id in tracked
                        and isinstance(call.func, ast.Attribute)
                        and not (isinstance(call.func.value, ast.Name)
                                 and call.func.attr == source.method)):
                    checked_method = call.func.attr
                    if len(attributes) > 1:
                        if attributes[-1] not in self._constructor_only_fields:
                            return True
                        checked_method = '__init__'
                    if not all(self._constructor_field_method_is_readonly(
                            identity, checked_method, source.method, tracers)
                            for identity in identities):
                        return True
                if not any(carries_name(arg, tracked)
                        for arg in list(call.args) + [kw.value for kw in call.keywords]):
                    continue
                if self._edge_targets_local_function(
                        edge, origin, module, source.parameter_scope,
                        tracers[origin], tracers):
                    continue
                return True
        return False

    ## Check a local method for escapes of its constructor-only field owner.
    #  @param identity Project-local class identity.
    #  @param method Method invoked on the object.
    #  @param field Constructor-injected callable field.
    #  @param tracers Project analyzers.
    #  @param seen Local method recursion guard.
    #  @return True only for inspectable non-escaping instance method bodies.
    def _constructor_field_method_is_readonly(
            self, identity, method, field, tracers, seen=None):
        key = (identity, method)
        seen = set(seen or ())
        if key in seen:
            return False
        seen.add(key)
        tree = tracers[identity[0]]._module_tree
        classes = [node for node in ast.walk(tree)
                   if isinstance(node, ast.ClassDef) and node.name == identity[1]]
        if len(classes) != 1:
            return False
        methods = [node for node in classes[0].body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name in (method, '__init__')]
        method_names = {node.name for node in classes[0].body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if not any(node.name == method for node in methods):
            return False
        for function in methods:
            args = list(function.args.posonlyargs) + list(function.args.args)
            if not args or function.decorator_list:
                return False
            receiver = args[0].arg
            parents = {id(child): node for node in ast.walk(function)
                       for child in ast.iter_child_nodes(node)}
            for node in ast.walk(function):
                if (isinstance(node, ast.Name) and node.id == receiver
                        and isinstance(node.ctx, ast.Load)
                        and not isinstance(parents.get(id(node)), ast.Attribute)):
                    return False
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == receiver and node.attr in method_names):
                    parent = parents.get(id(node))
                    if not (isinstance(parent, ast.Call) and parent.func is node):
                        return False
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == receiver
                        and node.func.attr != field
                        and not (node.func.attr in self._constructor_only_fields
                                 and node.func.attr not in method_names)
                        and not self._constructor_field_method_is_readonly(
                            identity, node.func.attr, field, tracers, seen)):
                    return False
        return True

    ## Resolve local classes represented by callable-object constructor calls.
    #
    #  A call such as ``f(value)`` stores the constructor's defining module in
    #  CallEdge.callee while retaining the imported class spelling in
    #  CallEdge.callee_name.  CallResult sources carry the same spelling in
    #  display_name.  Reconstruct the class only from that existing evidence
    #  and the caller's import bindings.
    #  @param module Module containing the callable-object call.
    #  @param source Callable source or SourceSet of callable sources.
    #  @param tracer Analyzer for the caller module.
    #  @param tracers All project analyzers.
    #  @param visited Recursion guard.
    #  @param display_name Optional call-edge spelling for the source.
    #  @return List of local class identities.
    def _local_callable_class_candidates(
            self, module, source, tracer, tracers, visited=None,
            display_name=None):
        source = normalize_source(source)
        seen = set(visited or set())
        key = (type(source).__name__, source_display(source))
        if key in seen:
            return []
        seen.add(key)

        if (isinstance(source, InstanceMethod) and source.parameter_scope
                and source.receiver == source.parameter_name):
            return self._parameter_callable_field_classes(
                module, source, tracers, seen)

        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._local_callable_class_candidates(
                    module, item, tracer, tracers, set(seen)))
            return self._dedupe_list(candidates)

        direct = self._local_class_from_source(module, source)
        if direct is not None:
            return [direct]
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            call_method = ".__call__"
            if source.callee.endswith(call_method):
                direct = self._local_class_from_source(
                    module, source.callee[:-len(call_method)])
                if direct is not None:
                    return [direct]
        if tracer is None:
            return []

        display = display_name
        if display is None and isinstance(source, CallResult):
            display = source.display_name
        if (not display
                and isinstance(source, CallResult)
                and isinstance(source.callee, str)):
            for imported in getattr(
                    tracer, "import_from_symbols", {}).values():
                if (isinstance(imported, str)
                        and (imported == source.callee
                             or imported.startswith(source.callee + "."))):
                    identity = self._local_class_from_source(
                        module, imported)
                    if identity is not None:
                        return [identity]
        if not isinstance(display, str) or not display:
            return []
        if "." in display:
            alias, class_name = display.rsplit(".", 1)
            bound_module = tracer.import_from_symbols.get(alias)
            if bound_module is None:
                bound_module = tracer.symbols.direct.get(alias)
        else:
            class_name = display
            bound_module = tracer.import_from_symbols.get(display)
            if bound_module is None:
                bound_module = tracer.symbols.direct.get(display)
        bound_module = normalize_source(bound_module)
        if isinstance(bound_module, CallResult):
            bound_module = bound_module.callee
        if isinstance(bound_module, str):
            imported_symbol = tracer.import_from_symbols.get(bound_module)
            if imported_symbol is not None:
                bound_module = imported_symbol
            if bound_module.endswith(".__call__"):
                bound_module = bound_module[:-len(".__call__")]
        if not isinstance(bound_module, str):
            return []
        candidate_source = (
            bound_module if "." not in display
            else bound_module + "." + class_name)
        identity = self._local_class_from_source(module, candidate_source)
        return [identity] if identity is not None else []

    ## Return whether an edge receiver may have one required local class.
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the edge.
    #  @param required Pair of required (module, class).
    #  @param tracers Dict of module name to analyzer.
    #  @return False only when concrete local class evidence excludes it.
    def _edge_receiver_may_have_class(
            self, edge, caller_module, required, tracers):
        candidates = self._local_class_candidates(
            caller_module, edge.receiver_source, tracers)
        if not candidates:
            return True
        return any(
            self._local_class_is_or_derives(
                candidate[0], candidate[1],
                required[0], required[1], tracers)
            for candidate in candidates
        )
