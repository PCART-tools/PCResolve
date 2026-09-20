## @package pcresolve.single_file
#  Provide single-file AST-based API call tracing.
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved primary owners and supporting provenance.

import ast
from dataclasses import replace
from .single_file_method_resolution import SingleFileMethodResolutionMixin
from .single_file_parameter_dependency import (
    SingleFileParameterDependencyMixin,
)
from .single_file_receiver_resolution import (
    SingleFileReceiverResolutionMixin,
)
from .single_file_returns import SingleFileReturnMixin
from .single_file_call_collection import (
    SingleFileCallCollectionMixin, _is_unshadowed_builtin_call,
)
from .single_file_assignment import (
    SingleFileAssignmentMixin, _builtin_value_source,
)
from .single_file_source_resolution import (
    SingleFileSourceResolutionMixin, _BUILTIN_PYTHON_OWNED_RESULT,
    _iterable_element_source,
)
from .single_file_control_flow import SingleFileControlFlowMixin
from .single_file_definitions import SingleFileDefinitionMixin
from .single_file_container_shapes import (
    SingleFileContainerShapeMixin, _container_kind,
)
from .mapping_facts import MappingFacts, bound_names as mapping_bound_names
from .symbol_table import SymbolTable
from .ir import CallSite, SymbolRef
from .import_facts import import_facts, resolve_relative_module
from .scope import (Scope, SCOPE_MODULE, SCOPE_CLASS,
                       SCOPE_COMPREHENSION)
from .sources import (ContainerItem, ContainerIter, TupleSource, InstanceMethod,
                       ParameterSource, PythonShape, CallResult,
                       UnknownSource, SourceSet, normalize_source,
                       source_display, make_source_set)
from .call_graph import FunctionId, ModuleCallGraph
from .ownership_contracts import (
    _TYPE_GUARD_OWNER_CONTRACTS, _CALLBACK_PARAMETER_OWNER_CONTRACTS,
    _match_result_owner,
)
from .builtin_ownership import (
    _is_builtin, _builtin_shape_type,
)

from .types import FileAnalysis, ApiCall

## AST visitor that traces all symbols and API calls in a single Python file.
#
#
#  Walks the AST to:
#  - Record import mappings and their aliases
#  - Track assignments, function/class definitions, decorators
#  - Resolve with/for return-value flows
#  - Handle container indexing, class inheritance, method resolution
#  - Detect and classify all API call expressions
class SingleFileAnalyzer(SingleFileSourceResolutionMixin,
                         SingleFileMethodResolutionMixin,
                         SingleFileParameterDependencyMixin,
                         SingleFileReceiverResolutionMixin,
                         SingleFileReturnMixin,
                         SingleFileCallCollectionMixin,
                         SingleFileAssignmentMixin,
                         SingleFileControlFlowMixin,
                         SingleFileDefinitionMixin,
                         SingleFileContainerShapeMixin, ast.NodeVisitor):
    ## Initialize the analyzer with empty state.
    #  @param module_name Optional dotted module name for resolving relative imports.
    #  @param is_package Whether the file is a package __init__.py.
    def __init__(self, module_name=None, is_package=False, file_path=""):
        self.module_name = module_name
        self.is_package = is_package
        self._file_path = file_path
        self.return_sources = {}
        # Literal return containers own their aggregate, not their elements.
        self.return_element_sources = {}
        # Positional tuple return summaries are consumed only by the project
        # call graph. Keep them out of return_sources, whose legacy resolver
        # expects one whole-result source.
        self.call_graph_return_sources = {}
        self.call_graph_return_values = {}
        self.call_graph_yield_sources = {}
        self.symbols = SymbolTable(self.return_sources)
        self.api_calls = []
        self.comprehension_targets = set()
        self.attr_accesses = []
        self.local = set()
        self._func_stack = []
        self._class_stack = []
        self._super_base_path_stack = []
        self._seen_api_call_ids = set()
        self._receiver_owner_guards = []
        self.defined_functions = set()
        self.function_params = {}
        self.parameter_sources = {}
        self._assigned_call_sources = {}
        self.container_items = {}
        self.homogeneous_container_items = {}
        self.homogeneous_container_value_sources = {}
        # Positional sources for homogeneous tuple/list-comprehension items.
        # Keys are module-level container names; values are source tuples.
        self.homogeneous_container_tuple_items = {}
        self.container_lengths = {}
        self.container_kinds = {}  # 1.0.5 P1: name -> "list"|"dict"|"set"|"tuple"|"str"
        self.container_item_kinds = {}  # 1.0.5 P1+: name -> "list"|"dict"|... for defaultdict(list) etc.
        self.container_set_sources = {}
        self.class_methods = {}
        self.class_bases = {}
        self.instance_attrs = {}
        self.instance_attr_kinds = {}
        self.instance_attr_item_kinds = {}
        self.instance_attr_item_fields = {}
        self._constructor_kwargs_contracts = {}
        self._local_instance_field_sources = {}
        self._local_instance_field_shapes = {}
        self._local_instance_field_shadowed = {}
        self.class_attr_kinds = {}
        self._class_receiver_stack = []
        self._container_item_kind_conflicts = set()
        self.import_from_symbols = {}
        self.wildcard_modules = []
        self.import_aliases = set()
        self._import_binding_sources = {}
        self.call_sites = {}
        self.call_assign_funcs = {}
        self._assignment_counter = 0
        self._global_names = set()
        self.call_site_objects = []
        self.symbol_refs = []
        self.module_scope = Scope(SCOPE_MODULE, self.module_name or "<module>")
        self.scope_stack = [self.module_scope]
        ## Call-graph facts (Phase 7B-full PR1: read-only collection).
        self.module_cg = ModuleCallGraph(module=module_name or "")
        ## Stack of FunctionId for tracking the current caller context.
        self._caller_stack = [FunctionId(module_name or "", "<module>")]
        ## Map from RHS top-level expression node id -> list of target names.
        ## Only the outermost RHS call (not nested inner calls) consumes targets.
        self._literal_values = {}
        self._pending_call_targets_by_node = {}
        self._argparse_parsers = {}
        self._argparse_destination_shapes = {}
        self._iterable_binding_sources = {}
        self._iterated_append_sources = {}
        self._iterated_append_tuple_sources = {}
        self._iterated_append_tuple_conflicts = set()
        self._attribute_append_tuple_sources = {}
        self._attribute_append_tuple_conflicts = set()
        self._subscripted_import_attribute_receivers = set()
        self.external_method_overrides = {}
        self._mapping_facts = MappingFacts(
            self._mapping_binding,
            lambda node: FunctionId(
                self.module_name or "", self._local_lambda_key(node)),
            lambda name: self.current_scope().lookup(
                name, skip_parent_classes=True),
            self._expression_python_shape)
        self._mapping_edges = []
        self._mapping_local_names = {}
        self._mapping_blocked_names = set()
        self._finite_name_guards = []
        self._finite_namespace_stability = {}
        self._module_tree = None

    ## Visit with mapping joins disabled for loop/exception-assigned names.
    #  Existing owner and protocol analysis remains unchanged.
    #  @param node AST node.
    def visit(self, node):
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try)):
            return super().visit(node)
        names = mapping_bound_names([node])
        scope = self.current_scope()
        previous = self._mapping_blocked_names
        self._mapping_blocked_names = previous | {
            (id(scope), name) for name in names}
        for name in names:
            binding = scope.lookup(name, skip_parent_classes=True)
            self._mapping_facts.invalidate(
                getattr(binding, "mapping_value", None), rebind=True)
        try:
            return super().visit(node)
        finally:
            self._mapping_blocked_names = previous

    ## Complete mapping call evidence after all possible mutations are seen.
    #  @param node Module AST node.
    def visit_Module(self, node):
        self._module_tree = node
        self.generic_visit(node)
        for edge, value in self._mapping_edges:
            edge.mapping_targets, edge.mapping_targets_complete = value.targets()

    ## Look up mapping facts without importing a deferred closure's bindings.
    #  @param name Lexical name.
    #  @return Current or module Binding, otherwise None.
    def _mapping_binding(self, name):
        scope = self.current_scope()
        if (id(scope), name) in self._mapping_blocked_names:
            return None
        if (name in self._mapping_local_names.get(id(scope), set())
                and name not in scope.bindings):
            return None
        binding = self.current_scope().lookup(name, skip_parent_classes=True)
        if (binding is not None
                and binding.scope_kind != SCOPE_MODULE
                and self.current_scope().bindings.get(name) is not binding):
            return None
        return binding

    ## Store mapping facts separately from the assigned object's owner.
    #  @param target Assignment target.
    #  @param value Captured mapping value.
    def _bind_mapping_value(self, target, value):
        if isinstance(target, ast.Name):
            binding = self.current_scope().bindings.get(target.id)
            if binding is not None:
                blocked = ((id(self.current_scope()), target.id)
                           in self._mapping_blocked_names)
                binding.mapping_value = None if blocked else value
        elif isinstance(target, ast.Subscript):
            self._mapping_facts.write(target)
            self._mapping_facts.invalidate(value)
        elif isinstance(target, ast.Attribute):
            self._mapping_facts.escape(target.value)
            self._mapping_facts.invalidate(value)

    ## Return the current innermost scope.
    def current_scope(self):
        return self.scope_stack[-1]

    ## Push a new scope onto the stack.
    #  @param kind Scope kind constant.
    #  @param name Human-readable scope name.
    #  @return The new Scope.
    def push_scope(self, kind, name):
        parent = self.current_scope()
        scope = Scope(kind, name, parent)
        self.scope_stack.append(scope)
        return scope

    ## Pop the current scope from the stack.
    #  @return The popped Scope.
    def pop_scope(self):
        return self.scope_stack.pop()

    ## Return the stable analyzer-local identity of a lexical binding.
    #  @param binding Binding created by this analyzer.
    #  @return Monotonic assignment index unique within the analyzed file.
    def _binding_key(self, binding):
        return binding.assignment_index

    ## Bind a name in the current lexical scope and compatibility symbol table.
    #
    #  Only module-scope and explicit global bindings enter self.symbols.
    #  @param name Symbol name.
    #  @param source Source value.
    #  @param node Optional AST node for position info.
    #  @param kind Optional symbol kind for provenance ("variable", "parameter", "attribute").
    def _bind_target_name(self, name, source, node=None, kind="variable",
                          container_kind="", container_item_kind="",
                          callable_key="", container_item_fields=None):
        if self.current_scope().kind == SCOPE_MODULE or name in self._global_names:
            old = self.current_scope().lookup(name, skip_parent_classes=True)
            self._mapping_facts.invalidate(
                getattr(old, "mapping_value", None), rebind=True)
        self._assignment_counter += 1
        lineno = getattr(node, "lineno", 0) if node is not None else 0
        col = getattr(node, "col_offset", 0) if node is not None else 0
        self.current_scope().bind(
            name, source, lineno, col, self._assignment_counter,
            container_kind=container_kind,
            container_item_kind=container_item_kind,
            callable_key=callable_key,
            binding_kind=kind,
            container_item_fields=container_item_fields)
        if (name in self._global_names
                or self.current_scope().kind == SCOPE_MODULE):
            self.symbols.add(name, source)
        if name.startswith("self.") and self._class_stack:
            attr_key = (self._class_stack[-1], name)
            self.instance_attrs[attr_key] = source
            if container_kind:
                self.instance_attr_kinds[attr_key] = container_kind
            else:
                self.instance_attr_kinds.pop(attr_key, None)
            if container_item_kind:
                self.instance_attr_item_kinds[attr_key] = container_item_kind
            else:
                self.instance_attr_item_kinds.pop(attr_key, None)
            if container_item_fields:
                self.instance_attr_item_fields[attr_key] = dict(
                    container_item_fields)
            else:
                self.instance_attr_item_fields.pop(attr_key, None)
        if (self.current_scope().kind == SCOPE_CLASS
                and self._class_stack and "." not in name):
            attr_key = (self._class_stack[-1], name)
            if container_kind:
                self.class_attr_kinds[attr_key] = container_kind
            else:
                self.class_attr_kinds.pop(attr_key, None)
        if kind:
            self._add_symbol_ref(name, source, kind, node)

    ## Normalize a class-qualified instance field target.
    #
    #  A local singleton may initialize an instance field through a class
    #  holder, for example ``MySQL.__instance.connection = pymysql.connect``.
    #  The later method body still observes that field as ``self.connection``.
    #  Preserve only this syntactic binding relationship; do not infer an
    #  external return type from the field name or method name.
    #  @param name Dotted assignment target.
    #  @return ``self.<field>`` or None when the target is unrelated.
    def _instance_attribute_target_name(self, name):
        if not self._class_stack or not isinstance(name, str):
            return None
        class_name = self._class_stack[-1]
        prefixes = (class_name + ".", "cls.")
        prefix = next(
            (candidate for candidate in prefixes
             if name.startswith(candidate)), None)
        if prefix is None:
            return None
        if prefix == "cls.":
            binding = self.current_scope().lookup(
                "cls", skip_parent_classes=True)
            if (binding is None
                    or binding.binding_kind != "parameter"):
                return None
        parts = name[len(prefix):].split(".")
        if parts and parts[0] == "__instance":
            parts = parts[1:]
        if not parts:
            return None
        return "self." + ".".join(parts)

    ## Look up a name in the lexical scope chain or return the name as-is.
    #
    #  Unified helper so that trace_source, get_base, and _resolve_call_receiver
    #  all use the same scope-aware resolution.
    #  @param name The raw AST name string.
    #  @return Scope binding source, or the name itself when not found.
    def _lookup_name_source(self, name):
        binding = self.current_scope().lookup(name, skip_parent_classes=True)
        if binding is not None:
            if binding.source == "local":
                return binding.source
            if (binding.binding_kind == "import"
                    and binding.scope_kind != SCOPE_MODULE):
                return binding.source
            if (name in self.import_aliases
                    and isinstance(binding.source, str)
                    and '.' not in binding.source):
                return name
            return binding.source
        return name

    ## Build a scope-qualified key for a locally assigned callable.
    #  @param name Assignment target name.
    #  @return Stable key used in return_sources.
    def _local_callable_key(self, name):
        parts = list(self._class_stack) + list(self._func_stack) + [name]
        return ".".join(parts)

    ## Build a stable scope-qualified key for an inline lambda callable.
    #  @param node Lambda expression.
    #  @return Source-location-qualified callable key.
    def _local_lambda_key(self, node):
        name = "<lambda>@%d:%d" % (node.lineno, node.col_offset)
        return self._local_callable_key(name)

    ## Preserve a local callable's identity when stored as a value.
    #  @param node Value expression.
    #  @return Qualified callable key or ordinary traced source.
    def _value_source(self, node):
        if (isinstance(node, (ast.Constant, ast.JoinedStr))
                or _container_kind(node) is not None):
            return "python"
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is not None and binding.callable_key:
                return binding.callable_key
        if isinstance(node, ast.Lambda):
            return self._local_lambda_key(node)
        return self.trace_source(node) or self.get_base(node)

    ## Preserve a lexical local callable's identity on a call edge.
    #
    #  Nested functions and lambdas need their qualified binding key so
    #  call contexts cannot merge unrelated same-named local definitions.
    #  @param node Call target expression.
    #  @return Local callable key or the ordinary traced source.
    def _call_edge_callee_source(self, node):
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and binding.callable_key
                    and binding.callable_key != node.id):
                return binding.callable_key
        return self.trace_source(node)

    ## Return argparse destination fields tracked for a parser binding.
    #
    #  @param parser_name Parser variable name.
    #  @return Mutable destination-name set, or None.
    def _argparse_destinations(self, parser_name):
        scope = self.current_scope()
        while scope is not None:
            destinations = self._argparse_parsers.get(
                (id(scope), parser_name))
            if destinations is not None:
                return destinations
            scope = scope.parent
        return None

    ## Return Python shapes tracked for an argparse parser binding.
    #
    #  @param parser_name Parser variable name.
    #  @return Destination-to-PythonShape mapping, or None.
    def _argparse_destination_shape_map(self, parser_name):
        scope = self.current_scope()
        while scope is not None:
            shapes = self._argparse_destination_shapes.get(
                (id(scope), parser_name))
            if shapes is not None:
                return shapes
            scope = scope.parent
        return None

    ## Record an argparse add_argument() destination with Python value shape.
    #
    #  Custom type/action callables are intentionally excluded because their
    #  return object may be project-local or import-backed.
    #  @param node Candidate add_argument() call.
    def _collect_argparse_destination(self, node):
        if (not isinstance(node.func, ast.Attribute)
                or node.func.attr != "add_argument"
                or not isinstance(node.func.value, ast.Name)):
            return
        destinations = self._argparse_destinations(node.func.value.id)
        if destinations is None:
            return
        shapes = self._argparse_destination_shape_map(node.func.value.id)

        keywords = {
            keyword.arg: keyword.value for keyword in node.keywords
            if keyword.arg is not None
        }
        type_node = keywords.get("type")
        if (type_node is not None
                and (not isinstance(type_node, ast.Name)
                     or not _is_builtin(type_node.id))):
            return
        action_node = keywords.get("action")
        if (action_node is not None
                and (not isinstance(action_node, ast.Constant)
                     or not isinstance(action_node.value, str))):
            return

        destination = None
        dest_node = keywords.get("dest")
        if (isinstance(dest_node, ast.Constant)
                and isinstance(dest_node.value, str)):
            destination = dest_node.value
        else:
            option_strings = [
                arg.value for arg in node.args
                if (isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str))
            ]
            long_options = [
                option for option in option_strings
                if option.startswith("--")
            ]
            if long_options:
                destination = long_options[0][2:].replace("-", "_")
            elif option_strings and not option_strings[0].startswith("-"):
                destination = option_strings[0].replace("-", "_")
        if destination:
            destinations.add(destination)
            if shapes is not None:
                shape = self._expression_python_shape(
                    keywords.get("default"))
                if shape is None and isinstance(type_node, ast.Name):
                    if _is_builtin(type_node.id):
                        shape = PythonShape(type_node.id)
                if (shape is None
                        and isinstance(action_node, ast.Constant)
                        and action_node.value in (
                            "store_true", "store_false")):
                    shape = PythonShape("bool")
                if shape is None:
                    shapes.pop(destination, None)
                else:
                    existing = shapes.get(destination)
                    if existing is None or existing == shape:
                        shapes[destination] = shape
                    else:
                        shapes.pop(destination, None)

    ## Record ArgumentParser construction or parse_args Namespace attributes.
    #
    #  @param node Assignment being visited.
    def _collect_argparse_assignment(self, node):
        if (not isinstance(node.value, ast.Call)
                or not isinstance(node.value.func, ast.Attribute)):
            return
        targets = [
            target.id for target in node.targets
            if isinstance(target, ast.Name)
        ]
        if not targets:
            return

        # ArgumentGroup.add_argument() populates the same Namespace as its
        # owning ArgumentParser.  Preserve that destination set when a group
        # is assigned to a local name, so grouped options receive the same
        # Python value-shape evidence as parser-level options.
        if (node.value.func.attr == "add_argument_group"
                and isinstance(node.value.func.value, ast.Name)):
            destinations = self._argparse_destinations(
                node.value.func.value.id)
            shapes = self._argparse_destination_shape_map(
                node.value.func.value.id)
            if destinations is not None:
                for target in targets:
                    self._argparse_parsers[
                        (id(self.current_scope()), target)] = destinations
                    if shapes is not None:
                        self._argparse_destination_shapes[
                            (id(self.current_scope()), target)] = shapes
                return

        func_top, func_name = self._resolve_func_top(node.value.func)
        if func_top == "argparse" and func_name == "ArgumentParser":
            for target in targets:
                self._argparse_parsers[
                    (id(self.current_scope()), target)] = set()
                self._argparse_destination_shapes[
                    (id(self.current_scope()), target)] = {}
            return

        if (node.value.func.attr not in ("parse_args",)
                or not isinstance(node.value.func.value, ast.Name)):
            return
        destinations = self._argparse_destinations(
            node.value.func.value.id)
        if destinations is None:
            return
        shapes = self._argparse_destination_shape_map(
            node.value.func.value.id)
        for target in targets:
            for destination in destinations:
                shape = shapes.get(destination) if shapes is not None else None
                self._bind_target_name(
                    target + "." + destination,
                    "python",
                    node,
                    "attribute",
                    container_kind=(shape.kind if shape is not None
                                    and shape.kind in (
                                        "list", "dict", "set", "tuple",
                                        "str") else ""),
                    container_item_kind=(shape.item_kind if shape is not None
                                         else ""),
                )

    ## Preserve a direct import-from callable for argument-flow evidence.
    #
    #  This metadata is intentionally separate from the ordinary symbol
    #  binding so public provenance and legacy call classification keep their
    #  established representation.
    #
    #  @param node Candidate call expression.
    #  @return Qualified CallResult or None.
    def _imported_call_result_source(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)):
            return None
        qualified = self.import_from_symbols.get(node.func.id)
        if not qualified:
            return None
        traced = normalize_source(self.trace_source(node))
        return CallResult(
            qualified,
            display_name=node.func.id,
            call_lineno=node.lineno,
            call_col_offset=node.col_offset,
            result_source=(traced.result_source
                           if isinstance(traced, CallResult) else None),
        )

    ## Preserve parameter forwarding in call-edge argument facts.
    #  @param node Argument expression.
    #  @return ParameterSource or ordinary argument source.
    def _call_edge_argument_source(self, node):
        if isinstance(node, ast.Subscript):
            dependency = self._parameter_dependency_source(node.value)
            if isinstance(dependency, ParameterSource):
                if isinstance(node.slice, ast.Slice):
                    return ParameterSource(
                        dependency.scope,
                        dependency.name,
                        derived=True,
                        attributes=dependency.attributes,
                        derived_operation="slice",
                    )
                index = self._get_slice(node.slice)
                return ContainerItem(
                    dependency, index if index is not None else "*")
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.List,
                             ast.Tuple, ast.Set, ast.Dict)):
            python_shape = self._expression_python_shape(node)
            if python_shape is not None:
                return python_shape
        if isinstance(node, ast.Name) and self._caller_stack:
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and isinstance(binding.source, SourceSet)
                    and binding.source.origin == "function_branch"):
                return binding.source
            if (self.current_scope().kind == SCOPE_COMPREHENSION
                    and node.id in self.comprehension_targets
                    and binding is not None
                    and (normalize_source(binding.source) == "local"
                         or (isinstance(
                             normalize_source(binding.source), CallResult)
                             and normalize_source(
                                 binding.source).result_source is None))):
                return UnknownSource("unresolved iterator element")
            if (binding is not None
                    and binding.binding_kind == "parameter"):
                return ParameterSource(
                    self._caller_stack[-1].qualname, node.id)
            assigned_call = self._assigned_call_sources.get(
                (id(self.current_scope()), node.id))
            if assigned_call is not None:
                return assigned_call
        imported_call = self._imported_call_result_source(node)
        if imported_call is not None:
            return imported_call
        return self._value_source(node)

    ## Preserve the exact producing call for a receiver-protocol argument.
    #  @param node Argument or return expression.
    #  @return Concrete Python shape, exact CallResult, or None.
    def _call_edge_protocol_source(self, node):
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and isinstance(binding.source, SourceSet)
                    and binding.source.origin == "function_branch"):
                return binding.source
        if isinstance(node, ast.Call):
            if (_is_unshadowed_builtin_call(self, node)
                    and node.func.id in _BUILTIN_PYTHON_OWNED_RESULT
                    and node.func.id != "super"
                    and _builtin_shape_type(node.func.id) is not None):
                return PythonShape(node.func.id)
            source = self._call_edge_argument_source(node)
            shape = self._expression_python_shape(node)
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Subscript)):
                receiver = self._call_edge_argument_source(node.func.value)
                if (isinstance(receiver, ContainerItem)
                        and isinstance(receiver.container, ParameterSource)):
                    return CallResult(
                        source, display_name=ast.unparse(node.func),
                        call_lineno=node.lineno, call_col_offset=node.col_offset,
                        result_source=InstanceMethod(receiver, node.func.attr))
            chained = (isinstance(node.func, ast.Attribute)
                       and isinstance(node.func.value, ast.Call))
            if isinstance(source, CallResult) and not chained:
                if shape is not None:
                    return replace(source, result_source=shape)
                return source
            return CallResult(
                (source.callee if isinstance(source, CallResult) else source)
                or UnknownSource("unresolved return callable"),
                display_name=ast.unparse(node.func),
                call_lineno=node.lineno,
                call_col_offset=node.col_offset,
                result_source=shape or source)
        return self._expression_python_shape(node)

    ## Preserve exact fields of a callback argument tuple.
    #  @param node Candidate tuple/list expression.
    #  @return TupleSource with UnknownSource fields when needed, or None for
    #  a non-tuple expression.
    def _call_edge_tuple_source(self, node):
        if not isinstance(node, (ast.Tuple, ast.List)):
            return None
        fields = []
        for field in node.elts:
            source = normalize_source(self._call_edge_argument_source(field))
            fields.append(source or UnknownSource("unresolved callback argument"))
        return TupleSource(tuple(fields))

    ## Attach the defining module to a declaration-time call source.
    #  Default expressions are evaluated while visiting a function definition,
    #  outside the function call graph. The module fact keeps alias resolution
    #  available when that default is later propagated to a receiver.
    #  @param source Candidate argument source.
    #  @return Source with module metadata when it is a CallResult.
    def _default_argument_source(self, source):
        return self._source_with_module(source)

    ## Attach this analyzer's module to a call result when absent.
    #  @param source Candidate source value.
    #  @return Source with module metadata when applicable.
    def _source_with_module(self, source):
        source = normalize_source(source)
        if not isinstance(source, CallResult) or source.source_module:
            return source
        return CallResult(
            source.callee,
            display_name=source.display_name,
            call_lineno=source.call_lineno,
            call_col_offset=source.call_col_offset,
            source_module=self.module_name or "",
            result_source=source.result_source,
        )

    ## Return a project-local callback identity carried by one argument.
    #  @param node Call argument AST node.
    #  @return Local function or qualified self-method name, otherwise None.
    def _call_edge_callback_name(self, node):
        if isinstance(node, ast.Name):
            if (node.id in self.defined_functions
                    or node.id in self.class_methods):
                return node.id
            return None
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in ("self", "cls")
                and self._class_stack
                and node.attr in self.class_methods.get(
                    self._class_stack[-1], [])):
            return self._class_stack[-1] + "." + node.attr
        return None

    ## Preserve element ownership for a call argument used as an iterable.
    #
    #  This fact is separate from ordinary argument ownership. A Python list
    #  may yield project-local or import-backed objects, so treating the list
    #  owner as the element owner would contaminate receiver classification.
    #  @param node Argument expression.
    #  @return Element source or None when the iterable is not explicit.
    def _call_edge_iterable_source(self, node):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if not node.elts:
                return UnknownSource("empty iterable")
            return _iterable_element_source(node, self.trace_source)
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is not None:
                tuple_sources = self._iterated_append_tuple_sources.get(
                    self._binding_key(binding))
                if tuple_sources is not None:
                    return tuple_sources
                source = self._iterable_binding_sources.get(
                    self._binding_key(binding))
                if source is not None:
                    return source
                dependency = self._parameter_dependency_source(node)
                if dependency is not None:
                    return ContainerIter(dependency)
        return None

    ## Attach an explicit iterable's element source to its lexical binding.
    #
    #  Binding identity prevents a same-name container in another function
    #  from changing an already collected call edge.
    #  @param node Assignment node whose targets have already been bound.
    def _record_iterable_binding_source(self, node):
        if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            return
        if not node.value.elts:
            item_source = UnknownSource("empty iterable")
        else:
            item_source = _iterable_element_source(
                node.value, self.trace_source)
        if item_source is None:
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            binding = self.current_scope().bindings.get(target.id)
            if binding is not None:
                self._iterable_binding_sources[
                    self._binding_key(binding)] = item_source

    ## Resolve the result object of a builtin container method.
    #
    #  The method callable is Python-owned, but selection methods return a
    #  value from the receiver. Preserve that item source instead of
    #  contaminating the result object with the callable's owner.
    #  @param node Method call.
    #  @param receiver_kind Independently known builtin container kind.
    #  @param method_name Called method name.
    #  @return Result source, "python", or None.
    def _builtin_method_result_source(
            self, node, receiver_kind, method_name):
        if (receiver_kind == "dict"
                and method_name == "get"
                and node.args):
            receiver = node.func.value
            if isinstance(receiver, ast.Name):
                container = receiver.id
            else:
                container = self.trace_source(receiver)
            key_node = node.args[0]
            if isinstance(key_node, ast.Constant):
                key = key_node.value
            else:
                key = "*"
            selected = ContainerItem(container, key)
            if len(node.args) >= 2:
                default = _builtin_value_source(
                    node.args[1], self.trace_source)
                return make_source_set(
                    (selected, default), origin="dict_lookup")
            return selected
        return "python"

    ## Record a SymbolRef for provenance tracking.
    #  @param symbol Display name.
    #  @param source Source value.
    #  @param kind Symbol category.
    #  @param node Optional AST node for position.
    def _add_symbol_ref(self, symbol, source, kind, node=None):
        scope_name = ""
        cs = self.current_scope()
        if cs.kind != SCOPE_MODULE:
            scope_name = cs.name
        self.symbol_refs.append(SymbolRef(
            symbol=symbol,
            source=source,
            kind=kind,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            scope_name=scope_name,
            lineno=getattr(node, "lineno", 0) if node is not None else 0,
            col_offset=getattr(node, "col_offset", 0) if node is not None else 0,
        ))

    ## --- Import visitors ---

    ## Visit an Import node and record alias-to-module mappings.
    #  @param node The Import AST node.
    def visit_Import(self, node):
        for fact in import_facts(node):
            symbol = fact.full_binding
            self.import_aliases.add(symbol)
            self._bind_target_name(symbol, fact.name, node, "import")
            binding = self.current_scope().bindings.get(symbol)
            if binding is not None:
                self._import_binding_sources[
                    self._binding_key(binding)] = fact.name
        self.generic_visit(node)

    ## Visit an ImportFrom node and record alias-to-module mappings.
    #  @param node The ImportFrom AST node.
    def visit_ImportFrom(self, node):
        for fact in import_facts(node):
            symbol = fact.python_binding
            if fact.wildcard:
                if fact.module:
                    if fact.level > 0 and self.module_name:
                        resolved = resolve_relative_module(
                            self.module_name, self.is_package,
                            fact.module, fact.level)
                        self.wildcard_modules.append(resolved)
                    else:
                        self.wildcard_modules.append(fact.module)
                continue
            if fact.level > 0 and self.module_name:
                resolved = resolve_relative_module(
                    self.module_name, self.is_package, fact.module, fact.level)
                self._bind_target_name(symbol, resolved, node, "import")
                qualified = (
                    (resolved + '.' + fact.name) if resolved else fact.name)
                self.import_from_symbols[symbol] = qualified
            else:
                self.import_aliases.add(symbol)
                self._bind_target_name(symbol, fact.module or None, node, "import")
                qualified = (
                    (fact.module + '.' + fact.name)
                    if fact.module else fact.name)
                self.import_from_symbols[symbol] = qualified
            binding = self.current_scope().bindings.get(symbol)
            if binding is not None:
                self._import_binding_sources[
                    self._binding_key(binding)] = qualified
        self.generic_visit(node)


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

    ## --- API call detection ---

    ## Resolve the base of an API call for origin tracking.
    #
    #  Tries getattr(), import_module(), method resolution, and
    #  call-lookup receiver resolution in order.
    #  @param node The Call AST node.
    #  @return Base symbol, structured tuple, or None.
    def _resolve_call_base_for_api(self, node):
        # P0 (1.0.5): bare getattr() builtin calls must be classified as
        # python, not traced through the argument's provenance.  Only
        # trace through obj.getattr("name") style calls where getattr is
        # accessed as an attribute on a receiver object.
        if self._is_getattr_call(node) and not isinstance(node.func,
                                                          ast.Name):
            if self._literal_str(node.args[1]) is not None:
                g = self.trace_source(node.args[0])
                if g is not None:
                    return g
        if self._is_import_module_call(node):
            im = self._resolve_import_module_trace(node)
            if im is not None:
                return im
        base = self._resolve_methods(node)
        if base is not None:
            return base
        # 1.0.5 P1+: defaultdict(list) item kind — d[k].append(v) where
        # d = defaultdict(list) has item kind "list".
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Subscript):
                sub = node.func.value
                if isinstance(sub.value, ast.Name):
                    item_kind = self._lookup_container_kind(
                        sub.value.id, item=True)
                    if item_kind is not None:
                        return InstanceMethod(sub.value.id, node.func.attr)
        ## For chained calls (A().B()), resolve via the inner call's
        ## return source so the outer call traces to the correct library.
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            inner_source = self.trace_source(node.func.value)
            if isinstance(inner_source, str):
                rs = self.return_sources.get(inner_source)
                if rs is not None:
                    return rs
            if isinstance(inner_source, CallResult):
                if inner_source.result_source is not None:
                    return inner_source.result_source
                rs = self.return_sources.get(inner_source.callee)
                if rs is not None:
                    return rs
            if isinstance(inner_source, InstanceMethod):
                if inner_source.parameter_scope:
                    return InstanceMethod(
                        inner_source,
                        node.func.attr,
                        parameter_scope=inner_source.parameter_scope,
                        parameter_name=inner_source.parameter_name,
                    )
            if isinstance(inner_source, SourceSet):
                return inner_source
            # 1.0.5 P1: library-function return types for chained
            # calls (cdist(...).argmin(), np.log(s).diff()).
            inner_call = node.func.value
            func_top, func_name = self._resolve_func_top(inner_call.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    inner_call, func_top, func_name)
                if preserved is not None:
                    return preserved
        call_lookup_base = self.get_base(node, call_lookup=True)
        if call_lookup_base is not None:
            return call_lookup_base
        return self.get_base(node.func)

    ## Collect all prefix calls in a chained call expression.
    #
    #  For a.b().c().d(), returns [a.b(), c(), d()] in call order.
    #  @param node The outermost Call AST node.
    #  @return List of Call nodes from outermost to innermost chain, reversed.
    def _chained_prefix_calls(self, node):
        if not isinstance(node, ast.Call):
            return []
        out = []
        cur = node
        while isinstance(cur, ast.Call):
            out.append(cur)
            f = cur.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call):
                cur = f.value
            else:
                break
        out.reverse()
        return out


    ## Collect a CallSite from the raw call data.
    #  @param expression Full call expression.
    #  @param func_name Function part.
    #  @param parameters Arguments string.
    #  @param base Base symbol or source.
    #  @param loc Dict with lineno/col_offset/end_lineno/end_col_offset.
    def _collect_call_site(self, expression, func_name, parameters,
                           base, loc):
        scope_name = ""
        cs = self.current_scope()
        if cs.kind != SCOPE_MODULE:
            scope_name = cs.name
        self.call_site_objects.append(CallSite(
            expression=expression,
            func_name=func_name,
            parameters=parameters,
            base=base,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            lineno=loc.get('lineno', 0),
            col_offset=loc.get('col_offset', 0),
            end_lineno=loc.get('end_lineno', 0),
            end_col_offset=loc.get('end_col_offset', 0),
            scope_name=scope_name,
        ))

    ## Record verified owner evidence supplied to callback parameters.
    #
    #  @param node The call expression accepting a callback.
    def _collect_callback_parameter_sources(self, node):
        func_top, func_name = self._resolve_func_top(node.func)
        if not func_top or not func_name:
            return
        for (owner, name, callback_index, parameter_index), contract in (
                _CALLBACK_PARAMETER_OWNER_CONTRACTS.items()):
            if (name != func_name
                    or not (func_top == owner
                            or func_top.startswith(owner + "."))
                    or callback_index >= len(node.args)):
                continue
            callback = node.args[callback_index]
            callback_key = self._value_source(callback)
            if not isinstance(callback_key, str):
                continue
            bare_key = callback_key.rsplit(".", 1)[-1]
            params = (self.function_params.get(callback_key)
                      or self.function_params.get(bare_key, []))
            if parameter_index >= len(params):
                continue
            parameter = params[parameter_index]
            self.parameter_sources.setdefault(
                (callback_key, parameter), []).append(contract[0])

    ## Return (func_str, args_str) tuple for a Call node.
    #  @param node The Call AST node.
    #  @return Tuple of (function expression, arguments string).
    def _get_call_parts(self, node):
        func_str = ast.unparse(node.func)
        parts = [ast.unparse(a) for a in node.args]
        if node.keywords:
            for kw in node.keywords:
                if kw.arg:
                    parts.append(f"{kw.arg}={ast.unparse(kw.value)}")
                else:
                    parts.append(f"**{ast.unparse(kw.value)}")
        args_str = ", ".join(parts)
        return func_str, args_str

    ## Reconstruct a call expression as a string.
    #  @param node The Call AST node.
    #  @return String representation like "func(arg1, arg2, kw=val)".
    def get_call(self, node):
        func_str, args_str = self._get_call_parts(node)
        return f"{func_str}({args_str})"

    ## Visit a Call node and record API calls from its chained prefix calls.
    #  @param node The Call AST node.
    def visit_Call(self, node):
        self._mapping_facts.call(node)
        self._collect_argparse_destination(node)
        self._collect_callback_parameter_sources(node)
        self._record_container_append_shape(node)
        for sub in self._chained_prefix_calls(node):
            self._one_api_call(sub)
        if isinstance(node.func, ast.Name) and node.func.id in self.defined_functions:
            arg_sources = []
            protocol_arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
                protocol_arg_sources.append(
                    self._call_edge_protocol_source(arg))
            self.call_sites.setdefault(node.func.id, []).append({
                "module": self.module_name,
                "args": arg_sources,
                "protocol_args": protocol_arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
            })
        elif isinstance(node.func, ast.Name) and node.func.id in self.class_methods:
            arg_sources = []
            protocol_arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
                protocol_arg_sources.append(
                    self._call_edge_protocol_source(arg))
            self.call_sites.setdefault(node.func.id + ".__init__", []).append({
                "module": self.module_name,
                "args": arg_sources,
                "protocol_args": protocol_arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
            })
        self.generic_visit(node)

    ## Visit an Attribute access node and record the top-level origin.
    #  @param node The Attribute AST node.
    def visit_Attribute(self, node):
        attr_string = ast.unparse(node)
        name = self._attribute_name(node)
        if name and name in self.symbols.direct:
            base = name
        else:
            base = self.get_base(node)
        if base:
            top = self.symbols.get_top(base)
            if top:
                self.attr_accesses.append({
                    'attr': attr_string,
                    'top': top,
                    'chain': self.symbols.get_chain(base)
                })
        self.generic_visit(node)

    ## Visit a With node and bind context-variable aliases.
    #  @param node The With AST node.
    def visit_With(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)

    ## Visit an AsyncWith node and bind context-variable aliases.
    #  @param node The AsyncWith AST node.
    def visit_AsyncWith(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)

## Analyze a single Python source string and return structured results.
#
#  Convenience function that parses source code and runs a full analysis
#  pass, returning a FileAnalysis object.
#  @param source Python source code as a string.
#  @param file_path Optional file path for the FileAnalysis record.
#  @return FileAnalysis with symbols, chains, and API calls.
## Analyze a single source string and return per-file results.
#  @param source Python source code string.
#  @param file_path Optional file path for reporting.
#  @return FileAnalysis object.
def analyze_source(source, file_path="<string>"):
    tree = ast.parse(source)
    tracer = SingleFileAnalyzer(file_path=file_path)
    tracer.visit(tree)
    return FileAnalysis(
        file_path=file_path,
        module_name="",
        symbols=dict(tracer.symbols.direct),
        chains=dict(tracer.symbols.chains),
        api_calls=[
            ApiCall(
                expression=c['api'],
                top_library=c['top'],
                base_symbol=source_display(c.get('base', '')),
                chain=c.get('chain', []),
                file_path=file_path,
                lineno=c.get('lineno', 0),
                col_offset=c.get('col_offset', 0),
                end_lineno=c.get('end_lineno', 0),
                end_col_offset=c.get('end_col_offset', 0),
                func_name=c.get('func_name', ''),
                parameters=c.get('parameters', ''),
                resolved_func=c.get('func_name', ''),
                resolved_chain=[c.get('func_name', ''), c.get('func_name', ''), c.get('top', '')],
            )
            for c in tracer.api_calls
        ],
    )
