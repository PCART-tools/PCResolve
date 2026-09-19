## @package pcresolve.single_file
#  Provide single-file AST-based API call tracing.
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved primary owners and supporting provenance.

import ast
from dataclasses import replace
from .single_file_method_resolution import SingleFileMethodResolutionMixin
from .single_file_call_collection import (
    SingleFileCallCollectionMixin, _is_unshadowed_builtin_call,
)
from .single_file_assignment import (
    SingleFileAssignmentMixin, _builtin_value_source,
)
from .single_file_source_resolution import (
    SingleFileSourceResolutionMixin, _BUILTIN_PYTHON_OWNED_RESULT,
    _iterable_element_source, _uniform_python_shape,
)
from .single_file_control_flow import SingleFileControlFlowMixin
from .single_file_definitions import SingleFileDefinitionMixin
from .mapping_facts import MappingFacts, bound_names as mapping_bound_names
from .symbol_table import SymbolTable
from .ir import CallSite, SymbolRef
from .import_facts import import_facts, resolve_relative_module
from .scope import (Scope, SCOPE_MODULE, SCOPE_CLASS,
                       SCOPE_COMPREHENSION)
from .sources import (ContainerItem, ContainerIter, TupleSource, InstanceMethod,
                       ParameterSource, InstanceAttribute, PythonShape,
                       SuperMethod, CallResult,
                       DerivedResult, UnknownSource,
                       SourceSet, is_structured_source, normalize_source,
                       source_display, make_source_set)
from .call_graph import FunctionId, CallEdge, ModuleCallGraph
from .ownership_contracts import (
    _CONVERSION_METHOD_TARGETS, _CONVERSION_ATTRIBUTE_TARGETS,
    _TYPE_GUARD_OWNER_CONTRACTS, _CALLBACK_PARAMETER_OWNER_CONTRACTS,
    _BUILTIN_METHOD_RESULT_ITEM_KINDS, _RECEIVER_PRESERVE_UFUNCS,
    _COMPARE_RESULT_METHODS, _match_result_owner,
    _has_result_owner_contract, _match_attribute_result_owner,
    _match_attribute_python_shape, _match_result_python_shape,
    _is_verified_result_owner, _match_result_item_owner,
)
from .builtin_ownership import (
    _BUILTIN_CONTAINER_METHODS, _is_builtin, _builtin_shape_type,
    _has_builtin_shape_method, _builtin_method_return_shape,
)

## Check if a Call node is a defaultdict(list) call with a statically
#  known default factory (list/dict/set/tuple/str).
def _is_defaultdict_itemkind(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False
    if node.func.id != "defaultdict" or len(node.args) < 1:
        return False
    factory = node.args[0]
    return isinstance(factory, ast.Name) and factory.id in ("list", "dict", "set", "tuple", "str")


## Return the concrete Python container kind produced by an expression.
#  @param node Assignment right-hand side AST node.
#  @return Container kind string or None.
def _container_kind(node):
    if isinstance(node, (ast.List, ast.ListComp)):
        return "list"
    if isinstance(node, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(node, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(node, ast.Tuple):
        return "tuple"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "str"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("list", "dict", "set", "tuple", "str"):
            return node.func.id
        if node.func.id == "defaultdict":
            return "dict"
    return None


## Return the concrete kind produced by subscripting a container expression.
#  Dict literals qualify only when every value has the same known kind.
#  @param node Assignment right-hand side AST node.
#  @return Item kind string or None.
def _container_item_kind(node):
    if isinstance(node, ast.Dict) and node.values:
        kinds = [_container_kind(value) for value in node.values]
        if kinds[0] is not None and all(kind == kinds[0] for kind in kinds):
            return kinds[0]
    if _is_defaultdict_itemkind(node):
        return node.args[0].id
    return None
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
                         SingleFileCallCollectionMixin,
                         SingleFileAssignmentMixin,
                         SingleFileControlFlowMixin,
                         SingleFileDefinitionMixin, ast.NodeVisitor):
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

    ## Return assignment metadata for a name in the active lexical scope.
    #  A found binding with no metadata is authoritative and prevents a
    #  same-name binding from another scope leaking through legacy maps.
    #  @param name Receiver variable name.
    #  @param item Whether to request the subscript item kind.
    #  @return Container kind string or None.
    def _lookup_container_kind(self, name, item=False):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            attr = "container_item_kind" if item else "container_kind"
            return getattr(binding, attr, "") or None
        # Compatibility maps are file-wide and can contain a same-name local
        # from a previously visited function. Only module code may use their
        # fallback; nested scopes require a lexical Binding as evidence.
        if self.current_scope().kind != SCOPE_MODULE:
            return None
        if item:
            return self.container_item_kinds.get(name)
        return self.container_kinds.get(name)

    ## Return field shapes for elements of a statically known container.
    #  @param node Container expression or bound name.
    #  @return Mapping of literal field names to shape tuples.
    def _expression_container_item_fields(self, node):
        if isinstance(node, (ast.List, ast.Tuple)):
            field_sets = []
            for element in node.elts:
                fields = self._literal_dict_field_shapes(element)
                if not fields:
                    return {}
                field_sets.append(fields)
            if field_sets and all(fields == field_sets[0]
                                  for fields in field_sets):
                return dict(field_sets[0])
            return {}
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            return dict(getattr(binding, "container_item_fields", {}) or {})
        if isinstance(node, ast.Attribute):
            name = self._attribute_name(node)
            if name and name.startswith("self.") and self._class_stack:
                return dict(self.instance_attr_item_fields.get(
                    (self._class_stack[-1], name), {}) or {})
        return {}

    ## Return positional sources for a homogeneous tuple/list comprehension.
    #
    #  The fact is intentionally limited to a comprehension whose element is
    #  a tuple or list and whose every field has an explicit source. It lets
    #  ``for value, label in pairs`` preserve the source of ``value`` without
    #  inferring ownership from the loop variable or method name.
    #  @param node Candidate list comprehension.
    #  @return Tuple of field sources, or None when incomplete.
    def _expression_tuple_item_sources(self, node):
        if not isinstance(node, ast.ListComp):
            return None
        element = node.elt
        if not isinstance(element, (ast.Tuple, ast.List)):
            return None
        sources = []
        for field in element.elts:
            source = self.trace_source(field)
            if source is None:
                source = self.get_base(field)
            if source is None:
                return None
            sources.append(normalize_source(source))
        return tuple(sources)

    ## Return module-level tuple-field facts for an active container binding.
    #  @param name Container name.
    #  @return Tuple of sources, or None when unavailable or shadowed.
    def _lookup_tuple_item_sources(self, name):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None and binding.scope_kind != SCOPE_MODULE:
            return None
        return self.homogeneous_container_tuple_items.get(name)

    ## Return the lexical identity of an attribute-backed container.
    #
    #  The root binding's monotonic assignment index keeps same-spelled local
    #  objects in separate functions isolated without relying on reusable
    #  Python object ids. Attribute facts are shared across functions only
    #  when their root resolves to the same enclosing binding.
    #  @param node Attribute expression naming the container.
    #  @return Tuple of root binding identity and attribute path, or None.
    def _attribute_container_key(self, node):
        chain = self._attribute_chain_list(node)
        if not chain or len(chain) < 2:
            return None
        binding = self.current_scope().lookup(
            chain[0], skip_parent_classes=True)
        if binding is None:
            return None
        return (binding.assignment_index, tuple(chain[1:]))

    ## Return tuple-field facts recorded for an attribute-backed list.
    #  @param node Attribute expression naming the list.
    #  @return TupleSource fields, or None when unresolved or conflicting.
    def _lookup_attribute_tuple_item_sources(self, node):
        key = self._attribute_container_key(node)
        if key is None or key in self._attribute_append_tuple_conflicts:
            return None
        source = self._attribute_append_tuple_sources.get(key)
        return source.items if isinstance(source, TupleSource) else None

    ## Invalidate tuple-field facts when an attribute container is rebound.
    #  @param node Attribute assignment target naming the container.
    def _invalidate_attribute_tuple_item_sources(self, node):
        key = self._attribute_container_key(node)
        if key is None:
            return
        self._attribute_append_tuple_sources.pop(key, None)
        self._attribute_append_tuple_conflicts.discard(key)

    ## Check whether two tuple item facts have the same positional owners.
    #  Call locations and expression spellings are not ownership differences.
    #  Unresolved positions never converge.
    #  @param left Existing TupleSource fact.
    #  @param right Newly observed TupleSource fact.
    #  @return True when every field has one matching resolved owner.
    def _tuple_item_owners_match(self, left, right):
        if (not isinstance(left, TupleSource)
                or not isinstance(right, TupleSource)
                or len(left.items) != len(right.items)):
            return False
        for left_item, right_item in zip(left.items, right.items):
            left_owner = self._structured_source_owner_top(left_item)
            right_owner = self._structured_source_owner_top(right_item)
            if (left_owner in (None, "unknown", "")
                    or left_owner != right_owner):
                return False
        return True

    ## Infer field shapes from a literal dictionary element.
    #  @param node Candidate dictionary AST node.
    #  @return Mapping of literal string keys to shape tuples.
    def _literal_dict_field_shapes(self, node):
        if not isinstance(node, ast.Dict):
            return {}
        fields = {}
        for key_node, value_node in zip(node.keys, node.values):
            if (not isinstance(key_node, ast.Constant)
                    or not isinstance(key_node.value, str)):
                continue
            kind, item_kind = self._expression_container_shape(value_node)
            if not kind:
                continue
            fields[key_node.value] = (kind, item_kind)
        return fields

    ## Return the shape of a literal-key field on a known element.
    #  @param node Subscript AST node.
    #  @return (container kind, item kind), or empty strings.
    def _expression_subscript_field_shape(self, node):
        if not isinstance(node, ast.Subscript):
            return ("", "")
        key = self._get_slice(node.slice)
        if not isinstance(key, str):
            return ("", "")
        fields = self._expression_container_item_fields(node.value)
        shape = fields.get(key)
        if shape is None:
            return ("", "")
        return shape

    ## Resolve a structured source to one uniform owner within the file.
    #
    #  This follows existing provenance only. It does not infer ownership from
    #  an attribute or method name, and mixed SourceSet owners stay unresolved.
    #  @param source Source value to inspect.
    #  @param seen Recursion guard for cyclic structured sources.
    #  @return Uniform owner string or None.
    def _structured_source_owner_top(self, source, seen=None):
        source = normalize_source(source)
        visited = set(seen or set())
        key = (type(source).__name__, source_display(source))
        if key in visited:
            return None
        visited.add(key)

        if isinstance(source, str):
            if source in ("local", "python", "unknown", ""):
                return source or None
            return self.symbols.get_top(source) or source
        if isinstance(source, PythonShape):
            return "python"
        if isinstance(source, UnknownSource):
            return "unknown"
        if isinstance(source, CallResult):
            if source.result_source is not None:
                return self._structured_source_owner_top(
                    source.result_source, visited)
            return self._structured_source_owner_top(
                source.callee, visited)
        if isinstance(source, InstanceMethod):
            return self._structured_source_owner_top(
                source.receiver, visited)
        if isinstance(source, ContainerIter):
            return self._structured_source_owner_top(
                source.container, visited)
        if isinstance(source, ContainerItem):
            return self._structured_source_owner_top(
                source.container, visited)
        if isinstance(source, SourceSet):
            owners = {
                self._structured_source_owner_top(item, set(visited))
                for item in source.sources
            }
            owners.discard(None)
            if len(owners) == 1:
                return next(iter(owners))
        return None

    ## Infer a Python-provided container shape from local expression evidence.
    #
    #  This follows only language-level facts: literals, lexical bindings,
    #  slicing, homogeneous items, and builtin methods on an independently
    #  known receiver kind. It never infers a receiver kind from a method name.
    #  @param node Value expression.
    #  @return Tuple of (container_kind, container_item_kind), or ("", "").
    def _expression_container_shape(self, node):
        direct_kind = _container_kind(node)
        if direct_kind is not None:
            return (direct_kind, _container_item_kind(node) or "")
        if (isinstance(node, ast.Constant)
                and type(node.value) in (bool, int, float, complex, bytes)):
            return (type(node.value).__name__, "")

        if isinstance(node, ast.JoinedStr):
            return ("str", "")

        if isinstance(node, ast.Name):
            return (
                self._lookup_container_kind(node.id) or "",
                self._lookup_container_kind(node.id, item=True) or "",
            )

        if isinstance(node, ast.Attribute):
            name = self._attribute_name(node)
            if name and name.startswith("self.") and self._class_stack:
                key = (self._class_stack[-1], name)
                return (
                    self.instance_attr_kinds.get(key, ""),
                    self.instance_attr_item_kinds.get(key, ""),
                )
            if name:
                binding = self.current_scope().lookup(
                    name, skip_parent_classes=True)
                if binding is not None:
                    return (
                        getattr(binding, "container_kind", "") or "",
                        getattr(binding, "container_item_kind", "") or "",
                    )
                parts = name.split(".", 1)
                if len(parts) == 2:
                    for scope_key in self._local_instance_field_scope_keys(
                            parts[0]):
                        field_shape = self._local_instance_field_shapes.get(
                            (scope_key, parts[0], parts[1]))
                        if field_shape is not None:
                            return field_shape
            receiver_top = self._expr_receiver_top(node.value)
            if receiver_top is None:
                receiver_top = self._structured_source_owner_top(
                    self.trace_source(node.value))
            shape = _match_attribute_python_shape(
                receiver_top, node.attr)
            if shape is not None:
                return (shape.kind, shape.item_kind)
            return ("", "")

        if isinstance(node, ast.Subscript):
            field_kind = self._expression_subscript_field_shape(node)
            if field_kind[0]:
                return field_kind
            value_kind, item_kind = self._expression_container_shape(
                node.value)
            if isinstance(node.slice, ast.Slice):
                if value_kind in ("list", "tuple", "str"):
                    return (value_kind, item_kind)
                return ("", "")
            if item_kind:
                return (item_kind, "")
            if value_kind == "str":
                return ("str", "")
            return ("", "")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            left = self._expression_container_shape(node.left)
            if left[0] == "str":
                return ("str", "")
            return ("", "")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._expression_container_shape(node.left)
            right = self._expression_container_shape(node.right)
            if (left[0] in ("list", "tuple", "str")
                    and left == right):
                return left
            return ("", "")

        if isinstance(node, ast.IfExp):
            body = self._expression_container_shape(node.body)
            orelse = self._expression_container_shape(node.orelse)
            return body if body[0] and body == orelse else ("", "")

        if isinstance(node, ast.Call):
            call_key = self.get_base(node, call_lookup=True)
            if isinstance(call_key, str):
                local_shape = _uniform_python_shape(
                    self.return_sources.get(call_key))
                if local_shape is not None:
                    return (local_shape.kind, local_shape.item_kind)
            func_top, func_name = self._resolve_func_top(node.func)
            if (func_top is None
                    and isinstance(node.func, ast.Attribute)):
                func_top = self._expr_receiver_top(node.func.value)
                func_name = node.func.attr
            if (func_top is None
                    and isinstance(node.func, ast.Attribute)):
                method_source = normalize_source(
                    self._resolve_methods(node))
                if isinstance(method_source, InstanceMethod):
                    receiver = normalize_source(method_source.receiver)
                    if isinstance(receiver, str):
                        func_top = (
                            self.symbols.get_top(receiver) or receiver)
                    elif isinstance(receiver, CallResult):
                        result_source = normalize_source(
                            receiver.result_source)
                        if isinstance(result_source, str):
                            func_top = result_source
                        elif isinstance(receiver.callee, str):
                            func_top = (
                                self.symbols.get_top(receiver.callee)
                                or receiver.callee)
                    func_name = method_source.method
            shape = _match_result_python_shape(func_top, func_name)
            if shape is not None:
                return (shape.kind, shape.item_kind)

        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)):
            receiver_kind, receiver_item_kind = (
                self._expression_container_shape(node.func.value))
            method = node.func.attr
            if (receiver_kind == "dict"
                    and method == "get"
                    and receiver_item_kind):
                return (receiver_item_kind, "")
            shape = _builtin_method_return_shape(
                PythonShape(receiver_kind, receiver_item_kind), method)
            if shape is not None:
                return (shape.kind, shape.item_kind)

        return ("", "")

    ## Preserve a concrete Python value shape for local call arguments.
    #
    #  Container shapes reuse lexical flow facts. Scalar literals are carried
    #  by their builtin type so downstream method resolution can validate the
    #  protocol instead of treating every Python value as interchangeable.
    #  @param node Value expression.
    #  @return PythonShape or None.
    def _expression_python_shape(self, node):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and node.elts:
            item_shapes = [
                self._expression_python_shape(item) for item in node.elts
            ]
            if (any(item is None for item in item_shapes)
                    or any(item.kind != item_shapes[0].kind
                           for item in item_shapes[1:])):
                return None
            return PythonShape(
                _container_kind(node) or "", item_shapes[0].kind)
        kind, item_kind = self._expression_container_shape(node)
        if kind:
            return PythonShape(kind, item_kind)
        if isinstance(node, ast.Constant):
            value = node.value
            if value is None:
                return PythonShape("NoneType")
            value_type = type(value)
            if value_type in (bytes, bool, int, float, complex):
                return PythonShape(value_type.__name__)
        return None

    ## Return the container kind relevant to a method call receiver.
    #  @param node The ast.Call node.
    #  @return Container or subscript-item kind string, or None.
    def _call_receiver_container_kind(self, node):
        if not isinstance(node, ast.Call):
            return None
        if not isinstance(node.func, ast.Attribute):
            return None
        receiver = node.func.value
        literal_kind = _container_kind(receiver)
        if literal_kind is not None:
            return literal_kind
        if isinstance(receiver, ast.Name):
            return self._lookup_container_kind(receiver.id)
        if isinstance(receiver, ast.Attribute) and self._class_stack:
            name = self._attribute_name(receiver)
            if name and name.startswith("self."):
                return self.instance_attr_kinds.get(
                    (self._class_stack[-1], name))
            if isinstance(receiver.value, ast.Name):
                root = receiver.value.id
                class_name = self._class_stack[-1]
                active_receiver = (
                    self._class_receiver_stack[-1]
                    if self._class_receiver_stack else "")
                if root == class_name or (
                        active_receiver and root == active_receiver):
                    return self.class_attr_kinds.get(
                        (class_name, receiver.attr))
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Name)):
            return self._lookup_container_kind(receiver.value.id, item=True)
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Attribute)
                and self._class_stack):
            name = self._attribute_name(receiver.value)
            if name and name.startswith("self."):
                return self.instance_attr_item_kinds.get(
                    (self._class_stack[-1], name))
        if (isinstance(receiver, ast.Subscript)
                and isinstance(receiver.value, ast.Call)):
            producer = receiver.value
            producer_kind = self._call_receiver_container_kind(producer)
            producer_method = (
                producer.func.attr
                if isinstance(producer.func, ast.Attribute) else "")
            item_kind = _BUILTIN_METHOD_RESULT_ITEM_KINDS.get(
                (producer_kind, producer_method))
            if item_kind is not None:
                return item_kind
            producer_owner = self.get_base(producer, call_lookup=True)
            if producer_owner == "python":
                return _BUILTIN_METHOD_RESULT_ITEM_KINDS.get(
                    ("str", producer_method))
        receiver_kind, _ = self._expression_container_shape(receiver)
        if receiver_kind:
            return receiver_kind
        return None

    ## Record the concrete kind assigned through a dictionary subscript.
    #
    #  The evidence is accepted only for a receiver already known to be a
    #  Python dict. All writes must converge to one concrete item kind.
    #  Conflicting or unresolved writes invalidate the fact for that binding.
    #  @param target Assignment target AST node.
    #  @param value_kind Concrete kind of the assigned value, or None.
    def _record_subscript_item_kind(self, target, value_kind):
        if (not isinstance(target, ast.Subscript)
                or not isinstance(target.value, ast.Name)):
            return
        container_name = target.value.id
        binding = self.current_scope().lookup(
            container_name, skip_parent_classes=True)
        if binding is None or binding.container_kind != "dict":
            return

        conflict_key = self._binding_key(binding)
        if conflict_key in self._container_item_kind_conflicts:
            return
        current = binding.container_item_kind or ""
        if not value_kind or (current and current != value_kind):
            binding.container_item_kind = ""
            self.container_item_kinds.pop(container_name, None)
            self._container_item_kind_conflicts.add(conflict_key)
            return
        binding.container_item_kind = value_kind
        self.container_item_kinds[container_name] = value_kind

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

    ## Preserve whether an assignment value has unresolved parameter origin.
    #  @param node Assignment value expression.
    #  @return ParameterSource, DerivedResult, UnknownSource, "local", or
    #  None.
    def _parameter_dependency_source(self, node, expression_context=False):
        if isinstance(node, ast.Name):
            if not self._caller_stack:
                return None
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is None:
                return None
            existing = normalize_source(binding.source)
            if isinstance(existing, (ParameterSource, UnknownSource)):
                return existing
            if isinstance(existing, DerivedResult):
                return existing
            if (expression_context
                    and isinstance(existing, ContainerItem)):
                return UnknownSource(
                    "unresolved container-item expression")
            if (expression_context
                    and isinstance(existing, CallResult)
                    and existing.result_source is None):
                callee = existing.callee
                callee_root = (
                    callee.split(".", 1)[0]
                    if isinstance(callee, str) else "")
                imported = (
                    callee_root in self.import_aliases
                    or callee_root in self.import_from_symbols
                    or (callee_root in self.symbols.direct
                        and self.symbols.direct.get(callee_root)
                        not in (None, "local", "python", "unknown")))
                if not imported:
                    return None
                # A call result without an explicit result-owner contract
                # cannot be safely used as the operand owner of a later
                # expression. Preserve uncertainty instead of allowing the
                # assignment fallback to relabel the value as local.
                return UnknownSource("unresolved call-result expression")
            if binding.binding_kind != "parameter":
                return None
            return ParameterSource(
                self._caller_stack[-1].qualname, node.id)

        if isinstance(node, ast.Attribute):
            if (expression_context
                    and isinstance(node.value, ast.Name)
                    and node.value.id in ("self", "cls")):
                attr_name = self._attribute_name(node)
                existing_attr = None
                if self._class_stack and attr_name:
                    existing_attr = self.instance_attrs.get(
                        (self._class_stack[-1], attr_name))
                existing_attr = normalize_source(existing_attr)
                if existing_attr is not None:
                    if isinstance(existing_attr, (ParameterSource,
                                                   UnknownSource,
                                                   DerivedResult)):
                        return existing_attr
                    return None
                scope_name = (
                    self._caller_stack[-1].qualname
                    if self._caller_stack else "")
                if not self._class_stack:
                    return "local"
                return InstanceAttribute(
                    self._class_stack[-1], attr_name, scope_name)
            dependency = self._parameter_dependency_source(
                node.value, expression_context=expression_context)
            if isinstance(dependency, ParameterSource):
                return ParameterSource(
                    dependency.scope,
                    dependency.name,
                    derived=dependency.derived,
                    attributes=dependency.attributes + (node.attr,),
                    derived_operation=dependency.derived_operation,
                )
            if isinstance(dependency, UnknownSource):
                return dependency
            return None

        if isinstance(node, ast.Subscript):
            dependency = self._parameter_dependency_source(
                node.value, expression_context=expression_context)
            if isinstance(dependency, ParameterSource):
                return ParameterSource(
                    dependency.scope,
                    dependency.name,
                    derived=True,
                    attributes=dependency.attributes,
                    derived_operation=(
                        "slice" if isinstance(node.slice, ast.Slice)
                        else "item"),
                )
            if isinstance(dependency, UnknownSource):
                return dependency
            return None

        if isinstance(node, ast.UnaryOp):
            dependency = self._parameter_dependency_source(
                node.operand, expression_context=expression_context)
            if dependency is not None:
                return UnknownSource("unresolved parameter-derived expression")
            return None

        if isinstance(node, ast.BinOp):
            left = self._parameter_dependency_source(
                node.left, expression_context=True)
            right = self._parameter_dependency_source(
                node.right, expression_context=True)
            if left is not None or right is not None:
                if left is None:
                    traced_left = self.trace_source(node.left)
                    if traced_left != "local":
                        left = traced_left
                if right is None:
                    traced_right = self.trace_source(node.right)
                    if traced_right != "local":
                        right = traced_right
                operands = tuple(
                    source for source in (left, right)
                    if source is not None)
                return DerivedResult(
                    "expression", operands,
                    type(node.op).__name__)
            return None

        if isinstance(node, ast.Compare):
            operands = []
            has_dependency = False
            for operand in [node.left] + list(node.comparators):
                dependency = self._parameter_dependency_source(
                    operand, expression_context=True)
                if dependency is not None:
                    has_dependency = True
                    operands.append(dependency)
                    continue
                traced = self.trace_source(operand)
                if traced != "local" and traced is not None:
                    operands.append(traced)
            if has_dependency:
                return DerivedResult(
                    "expression", tuple(operands), "Compare")
            return None

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            dependency = self._parameter_dependency_source(node.func.value)
            if dependency is not None:
                method_source = self._resolve_methods(node)
                if method_source is None:
                    return UnknownSource("unresolved parameter method result")
                return CallResult(
                    method_source,
                    display_name=ast.unparse(node.func),
                    call_lineno=node.lineno,
                    call_col_offset=node.col_offset,
                    result_source=DerivedResult(
                        "method_result",
                        (method_source,),
                        node.func.attr,
                    ),
                )
        return None

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

    ## --- Method resolution ---

    ## Resolve a method inherited from a statically known builtin base class.
    #
    #  Follows local base classes in declared MRO order.  A local override wins;
    #  an external or otherwise unknown base stops inference so a later builtin
    #  base cannot be claimed speculatively.
    #  @param class_name Local class whose bases should be inspected.
    #  @param method_name Method looked up on the instance.
    #  @param seen Local classes already visited during recursive lookup.
    #  @return Builtin type name, "local", or None when unresolved.
    def _inherited_builtin_method_owner(self, class_name, method_name,
                                        seen=None):
        if seen is None:
            seen = set()
        if class_name in seen:
            return None
        seen = set(seen)
        seen.add(class_name)

        for base in self.class_bases.get(class_name, []):
            if base in self.class_methods:
                if method_name in self.class_methods.get(base, []):
                    return "local"
                inherited = self._inherited_builtin_method_owner(
                    base, method_name, seen)
                if inherited is not None:
                    return inherited
                continue

            direct = normalize_source(self.symbols.direct.get(base))
            if direct == "local":
                return None

            imported = self.import_from_symbols.get(base, "")
            resolved_base = imported or base
            builtin_name = resolved_base.rsplit(".", 1)[-1]
            builtin_origin = (
                resolved_base == builtin_name
                or resolved_base.startswith("builtins."))
            if (builtin_origin
                    and method_name in _BUILTIN_CONTAINER_METHODS.get(
                        builtin_name, frozenset())):
                return builtin_name
            if builtin_name == "object" and builtin_origin:
                continue

            # An earlier unknown/external base may provide the descriptor.
            return None
        return None


    ## Resolve the owner of a comparison-result method call.
    #
    #  For (np.diag(W) == np.zeros(...)).any(), both sides of the
    #  comparison are numpy expressions, so the result is a boolean
    #  ndarray and .any() belongs to numpy.
    #
    #  Only returns an owner when ALL operands resolve to the same
    #  library AND the method is in _COMPARE_RESULT_METHODS for that
    #  library.  Returns None otherwise — no fallback to the first
    #  operand (which would overclaim ownership for mixed libraries).
    #  @param compare_node The ast.Compare node.
    #  @param method_name The method being called on the result.
    #  @return InstanceMethod or None.
    def _resolve_compare_result_top(self, compare_node, method_name):
        # Collect the top library of every operand.
        operands = [compare_node.left] + list(compare_node.comparators)
        tops = []
        for op in operands:
            base = self.get_base(op)
            if isinstance(base, str):
                top = self.symbols.get_top(base)
                if top and top not in ("local", "python", "unknown", ""):
                    tops.append(top)
                    continue
            # Could not resolve this operand — conservative bail-out.
            return None

        if not tops:
            return None

        first = tops[0]
        # All operands must have the same owner.
        if any(t != first for t in tops[1:]):
            return None

        # Only allow methods known to exist on compare-result objects.
        allowed = _COMPARE_RESULT_METHODS.get(first)
        if allowed is None or method_name not in allowed:
            return None

        return InstanceMethod(first, method_name)

    ## Flatten an attribute chain (e.g. a.b.c) into a list ["a", "b", "c"].
    #  @param node The starting Attribute node.
    #  @return List of name parts from root to leaf, or None.
    def _attribute_chain_list(self, node):
        parts = []
        remain = node
        while isinstance(remain, ast.Attribute):
            parts.append(remain.attr)
            remain = remain.value
        if isinstance(remain, ast.Name):
            parts.append(remain.id)
            return list(reversed(parts))
        return None

    ## Reconstruct a dotted attribute name from an AST node.
    #  @param node The Attribute or Name node.
    #  @return Dotted name string (e.g. "os.path.join"), or None.
    def _attribute_name(self, node):
        chain = self._attribute_chain_list(node)
        if chain:
            return ".".join(chain)
        return None

    ## Check whether an expression is rooted at an imported module symbol.
    #
    #  This is deliberately syntactic.  A variable whose value came from an
    #  external call is not treated as the module that produced that value.
    #  @param node Receiver expression below an Attribute node.
    #  @return True only for an import alias or import-from root.
    def _is_import_backed_receiver_expression(self, node):
        if isinstance(node, ast.Name):
            root = node.id
        elif isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            root = chain[0] if chain else None
        else:
            root = None
        if not root:
            return False
        if (root not in self.import_aliases
                and root not in self.import_from_symbols):
            return False
        top = self._receiver_top(root)
        return top not in (None, "", "local", "python", "unknown")

    ## Resolve an explicitly evidenced external receiver expression.
    #
    #  Accepted roots are import symbols and instance fields already bound to
    #  an external source. A local variable is intentionally excluded even
    #  when its current source came from an external call, because that call's
    #  return object has no generic static owner contract.
    #  @param node Receiver expression.
    #  @return External owner top or None.
    def _explicit_external_receiver_top(self, node):
        if self._is_import_backed_receiver_expression(node):
            if isinstance(node, ast.Name):
                root = node.id
            else:
                chain = self._attribute_chain_list(node)
                root = chain[0] if chain else None
            return self._receiver_top(root) if root else None

        if isinstance(node, ast.Attribute) and self._class_stack:
            chain = self._attribute_chain_list(node) or []
            if chain and chain[0] == "self":
                class_name = self._class_stack[-1]
                for end in range(len(chain), 1, -1):
                    field_name = ".".join(chain[:end])
                    source = normalize_source(self.instance_attrs.get(
                        (class_name, field_name)))
                    owner = self._structured_source_owner_top(source)
                    if owner not in (None, "", "local", "python", "unknown"):
                        return owner

        if isinstance(node, ast.Subscript):
            return self._explicit_external_receiver_top(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            receiver = node.func.value
            if self._is_import_backed_receiver_expression(receiver):
                return None
            return self._explicit_external_receiver_top(receiver)
        if isinstance(node, ast.Attribute):
            return self._explicit_external_receiver_top(node.value)
        return None

    ## Check whether an expression is rooted at a local instance field.
    #  @param node Receiver expression.
    #  @return True for self.field and its subscripted forms.
    def _is_instance_field_expression(self, node):
        if isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            return bool(chain and chain[0] == "self")
        if isinstance(node, ast.Subscript):
            return self._is_instance_field_expression(node.value)
        return False

    ## Find the root receiver of a call expression.
    #
    #  Unwinds chained calls and attributes to find the base object.
    #  @param receiver_node The receiver AST node.
    #  @return Base symbol name, or None.
    ## Resolve an Attribute receiver through scope binding.
    #
    #  When the root of the attribute chain (e.g. "v" in "v.armW.mean")
    #  has a scope binding with a library source, propagate it instead
    #  of returning the raw dotted name.
    #  @param receiver_node The Attribute AST node.
    #  @param receiver_name The full dotted name (e.g. "v.armW").
    #  @return Resolved source or the original receiver_name.
    def _resolve_attribute_receiver_chain(self, receiver_node, receiver_name):
        if receiver_name in self.symbols.direct:
            return receiver_name
        chain = self._attribute_chain_list(receiver_node)
        if chain:
            root_src = self._lookup_name_source(chain[0])
            if root_src and root_src != chain[0]:
                return root_src
        return receiver_name

    def _resolve_call_receiver(self, receiver_node):
        if isinstance(receiver_node, ast.Name):
            return self._lookup_name_source(receiver_node.id)
        if isinstance(receiver_node, ast.Attribute):
            receiver_name = self._attribute_name(receiver_node)
            if receiver_name is not None:
                return self._resolve_attribute_receiver_chain(
                    receiver_node, receiver_name)
            return self._resolve_call_receiver(receiver_node.value)
        if isinstance(receiver_node, ast.Call):
            inner_receiver = self.get_base(receiver_node, call_lookup=True)
            if inner_receiver is not None:
                return inner_receiver
            return self.get_base(receiver_node.func, call_lookup=False)
        if isinstance(receiver_node, ast.BinOp):
            left = self.get_base(receiver_node.left, call_lookup=True)
            if left is not None:
                return left
            return self.get_base(receiver_node.right, call_lookup=True)
        if isinstance(receiver_node, ast.Subscript):
            return self._resolve_call_receiver(receiver_node.value)
        return None

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

    ## --- Base extraction ---

    ## Extract the root/base name from an expression node.
    #
    #  For simple names returns the name. For attributes returns the chain root.
    #  For calls with call_lookup=True, resolves the call receiver.
    #  @param node The AST expression node.
    #  @param call_lookup If True, resolve call receivers instead of just func base.
    #  @return Root symbol name, or None.
    def get_base(self, node, call_lookup=False):
        if isinstance(node, ast.Name):
            return self._lookup_name_source(node.id)
        elif isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            if chain:
                name = '.'.join(chain)
                if name in self.symbols.direct:
                    return name
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    attr_source = self.instance_attrs.get((cn, name))
                    if attr_source is not None:
                        if isinstance(attr_source, str):
                            if attr_source in self.symbols.direct or '.' in attr_source:
                                return attr_source
                        else:
                            return attr_source
                root = chain[0]
                return self._lookup_name_source(root)
            return self.get_base(node.value, call_lookup=call_lookup)
        elif isinstance(node, ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0], call_lookup=call_lookup)
            if call_lookup:
                func = node.func
                if isinstance(func, ast.Attribute):
                    return self._resolve_call_receiver(func.value)
                if isinstance(func, ast.Call):
                    return self._resolve_call_receiver(func)
                if isinstance(func, ast.Name):
                    return self._lookup_name_source(func.id)
                return None
            return self.get_base(node.func, call_lookup=False)
        elif isinstance(node, ast.BinOp):
            left = self.get_base(node.left, call_lookup=call_lookup)
            if left is not None:
                return left
            return self.get_base(node.right, call_lookup=call_lookup)
        elif isinstance(node, ast.Lambda):
            return self.get_base(node.body, call_lookup=call_lookup)
        elif isinstance(node, ast.Subscript):
            return self.get_base(node.value, call_lookup=call_lookup)
        return None

    ## --- Visit handlers ---


    ## Resolve a receiver name to its top library using lexical scope.
    def _receiver_top(self, name):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            src = normalize_source(binding.source)
            if isinstance(src, str):
                if src in ("local", "python", "unknown", ""):
                    return src or None
                source_top = self.symbols.get_top(src)
                return source_top or src
            if isinstance(src, InstanceMethod):
                receiver = normalize_source(src.receiver)
                if isinstance(receiver, str):
                    receiver_top = self.symbols.get_top(receiver)
                    return receiver_top or receiver
                return None
            if isinstance(src, CallResult):
                result_owner = normalize_source(src.result_source)
                if isinstance(result_owner, str):
                    owner_top = self.symbols.get_top(result_owner)
                    return owner_top or result_owner
                if isinstance(result_owner, UnknownSource):
                    return "unknown"
                if not isinstance(src.callee, str):
                    return None
                callee_top = self.symbols.get_top(src.callee)
                root = src.callee.split(".", 1)[0]
                root_binding = self.current_scope().lookup(
                    root, skip_parent_classes=True)
                if ("." in src.callee and root_binding is not None
                        and root_binding.binding_kind == "import"
                        and isinstance(root_binding.source, str)):
                    callee_top = root_binding.source.split(".", 1)[0]
                if callee_top and callee_top not in ("local", name):
                    return callee_top
                # Follow return_sources through local functions.
                rs = self.return_sources.get(src.callee)
                if rs is not None:
                    rs = normalize_source(rs)
                    sources = rs.sources if isinstance(rs, SourceSet) else [rs]
                    for source in sources:
                        source = normalize_source(source)
                        if (isinstance(source, CallResult)
                                and isinstance(source.callee, str)):
                            callee_top = self.symbols.get_top(source.callee)
                            if (callee_top
                                    and callee_top not in ("local", name)):
                                return callee_top
                return callee_top
            # A lexical binding is authoritative. Do not consult a same-name
            # module binding when its structured source is unresolved here.
            return None
        top = self.symbols.get_top(name)
        return top

    ## Resolve the ownership top of an expression node.
    #  Recursively handles ast.Call arguments so that
    #  np.log(price.dropna()).diff() preserves the inner call's
    #  receiver owner (pandas).
    #  Respects conversion boundaries: data.to_numpy() returns
    #  numpy even though the receiver is pandas.
    def _expr_receiver_top(self, expr):
        if isinstance(expr, ast.Name):
            return self._receiver_top(expr.id)
        if isinstance(expr, ast.Constant):
            return "python"
        if isinstance(expr, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return "python"
        if isinstance(expr, ast.UnaryOp):
            return self._expr_receiver_top(expr.operand)
        if isinstance(expr, ast.BinOp):
            left_top = self._expr_receiver_top(expr.left)
            right_top = self._expr_receiver_top(expr.right)
            if left_top == right_top:
                return left_top
            external = [
                top for top in (left_top, right_top)
                if top not in (None, "", "local", "python", "unknown")]
            other = [
                top for top in (left_top, right_top)
                if top not in external]
            if (len(set(external)) == 1
                    and all(top == "python" for top in other)):
                return external[0]
            return None
        if isinstance(expr, ast.Subscript):
            return self._expr_receiver_top(expr.value)
        if isinstance(expr, ast.Attribute):
            receiver = expr.value
            name = self._attribute_name(expr)
            if (name and name.startswith("self.")
                    and self._class_stack):
                field_source = normalize_source(self.instance_attrs.get(
                    (self._class_stack[-1], name)))
                field_top = self._structured_source_owner_top(field_source)
                if field_top not in (None, "", "local", "python", "unknown"):
                    return field_top
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top:
                    return _CONVERSION_ATTRIBUTE_TARGETS.get(
                        (receiver_top, expr.attr))
            return None
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            receiver_top = self._expr_receiver_top(expr.func.value)
            if (receiver_top
                    and receiver_top not in (
                        "local", "python", "unknown", "")):
                # Check conversion boundary first:
                # data.to_numpy() return is numpy, not pandas.
                conv = _CONVERSION_METHOD_TARGETS.get(
                    (receiver_top, expr.func.attr))
                if conv:
                    return conv
                return receiver_top
        return None

    ## Identify one imported attribute path by its lexical root binding.
    #  @param node Attribute expression.
    #  @return Binding key and attribute path, or None for non-import roots.
    def _import_attribute_key(self, node):
        if not isinstance(node, ast.Attribute):
            return None
        chain = self._attribute_chain_list(node)
        if not chain:
            return None
        binding = self.current_scope().lookup(
            chain[0], skip_parent_classes=True)
        if binding is None or binding.binding_kind != "import":
            return None
        return (self._binding_key(binding), tuple(chain[1:]))

    ## Record runtime attributes of imported objects used via subscripting.
    #
    #  A subscript proves only that the attribute supports the subscription
    #  protocol. It does not prove that the attribute value is owned by the
    #  library that owns the outer object. Later method calls on the same
    #  attribute therefore remain unknown unless independent shape evidence
    #  exists.
    #  @param node Subscript expression.
    def visit_Subscript(self, node):
        key = self._import_attribute_key(node.value)
        if key is not None:
            self._subscripted_import_attribute_receivers.add(key)
        self.generic_visit(node)

    ## Check whether a return expression is fully bounded by project sources.
    #  @param source Structured return-expression source.
    #  @return True when exact call-edge substitution is safe.
    def _is_bounded_return_expression(self, source):
        source = normalize_source(source)
        if isinstance(source, (ParameterSource, InstanceAttribute,
                               PythonShape)):
            return True
        if isinstance(source, str):
            return source == "python"
        if isinstance(source, DerivedResult):
            return (
                source.kind == "expression"
                and bool(source.sources)
                and all(self._is_bounded_return_expression(item)
                        for item in source.sources)
            )
        if isinstance(source, CallResult):
            return (
                source.result_source is not None
                and self._is_bounded_return_expression(
                    source.result_source)
            )
        return False

    ## Check whether a structured source still depends on a parameter.
    #
    #  Parameter expressions must be resolved from project call edges.  A
    #  same-scope expression owner must not overwrite that richer evidence.
    #  @param source Source value to inspect.
    #  @return True when any nested source is parameter-backed.
    def _source_contains_parameter(self, source):
        source = normalize_source(source)
        if isinstance(source, ParameterSource):
            return True
        if isinstance(source, (DerivedResult, SourceSet)):
            return any(self._source_contains_parameter(item)
                       for item in source.sources)
        if isinstance(source, CallResult):
            return self._source_contains_parameter(source.result_source)
        if isinstance(source, InstanceMethod):
            return self._source_contains_parameter(source.receiver)
        return False

    ## Collect immediate ownership evidence from an operator expression.
    #
    #  The caller uses these candidates only to distinguish strict
    #  same-owner convergence from conflicting import-backed operands.
    #  @param expr BinOp or UnaryOp expression.
    #  @return List of operand owner strings.
    def _operator_operand_tops(self, expr):
        if isinstance(expr, ast.BinOp):
            return [
                self._expr_receiver_top(expr.left),
                self._expr_receiver_top(expr.right),
            ]
        if isinstance(expr, ast.UnaryOp):
            return [self._expr_receiver_top(expr.operand)]
        return []

    ## Resolve (top_library, function_name) for a function expression.
    #  Handles both bare names (cdist) and dotted names (np.log).
    def _resolve_func_top(self, func_node):
        if isinstance(func_node, ast.Name):
            name = func_node.id
            top = self._receiver_top(name)
            imported_name = self.import_from_symbols.get(name, "")
            func_name = (
                imported_name.rsplit(".", 1)[-1]
                if imported_name else name)
            if (top and top not in ("local", "python", "unknown", "")
                    and (top != name
                         or name in self.import_aliases
                         or name in self.import_from_symbols)):
                return (top, func_name)
        if isinstance(func_node, ast.Attribute):
            full_name = self._attribute_name(func_node)
            prefix = ""
            if full_name:
                imported_prefixes = sorted(
                    (
                        name for name in self.import_aliases
                        if (full_name == name
                            or full_name.startswith(name + "."))
                    ),
                    key=len,
                    reverse=True,
                )
                if imported_prefixes:
                    prefix = imported_prefixes[0]
                else:
                    prefix = full_name.split(".", 1)[0]
            prefix_top = self._receiver_top(prefix)
            if (prefix_top
                    and prefix_top not in ("local", "python", "unknown", "")
                    and (prefix_top != prefix
                         or prefix in self.import_aliases
                         or prefix in self.import_from_symbols)):
                return (prefix_top, func_node.attr)
        return (None, None)

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

    ## Resolve a verified owner for an item selected from a call result.
    #
    #  Direct import calls use _resolve_func_top().  Receiver calls additionally
    #  use _resolve_methods(), which can recover owners stored on instance
    #  attributes such as self.model = GPRegression(...).
    #  @param call_node The call whose result is indexed or destructured.
    #  @return Verified item owner string, or None.
    def _resolve_call_result_item_owner(self, call_node):
        func_top, func_name = self._resolve_func_top(call_node.func)
        owner = _match_result_item_owner(func_top, func_name)
        if owner is not None:
            return owner
        method_source = normalize_source(self._resolve_methods(call_node))
        if isinstance(method_source, InstanceMethod):
            receiver = normalize_source(method_source.receiver)
            if isinstance(receiver, str):
                receiver_top = self.symbols.get_top(receiver) or receiver
                if receiver_top not in (
                        None, "", "local", "python", "unknown"):
                    return _match_result_item_owner(
                        receiver_top, method_source.method)
        if (not isinstance(call_node.func, ast.Attribute)
                or not isinstance(call_node.func.value, ast.Attribute)
                or not self._class_stack):
            return None
        receiver_name = self._attribute_name(call_node.func.value)
        if not receiver_name or not receiver_name.startswith("self."):
            return None
        attr_source = normalize_source(self.instance_attrs.get(
            (self._class_stack[-1], receiver_name)))
        if isinstance(attr_source, CallResult):
            attr_source = normalize_source(
                attr_source.result_source or attr_source.callee)
        if not isinstance(attr_source, str):
            return None
        attr_top = self.symbols.get_top(attr_source) or attr_source
        if attr_top in (None, "", "local", "python", "unknown"):
            return None
        return _match_result_item_owner(attr_top, call_node.func.attr)

    ## Resolve the result owner of a protocol-dispatched NumPy ufunc.
    #
    #  Pandas and NumPy inputs retain their owner.  Python literals and
    #  containers produce NumPy results.  An unresolved or other import-backed
    #  receiver remains unknown because array protocols may override dispatch.
    #  @param call_node Ufunc call expression.
    #  @param func_top Resolved callable owner.
    #  @param func_name Resolved function name.
    #  @return Owner string, structured deferred source, UnknownSource, or
    #  None when not applicable.
    def _receiver_preserving_result_owner(self, call_node, func_top,
                                          func_name):
        if (func_top != "numpy"
                or func_name not in _RECEIVER_PRESERVE_UFUNCS
                or not call_node.args):
            return None
        arg_tops = []
        deferred_sources = []
        for argument in call_node.args:
            arg_top = self._expr_receiver_top(argument)
            if (_container_kind(argument) is not None
                    or isinstance(argument, ast.Constant)):
                arg_top = "python"
            if arg_top in (None, "", "local", "unknown"):
                dependency = self._parameter_dependency_source(
                    argument, expression_context=True)
                dependency = normalize_source(dependency)
                if dependency is None or isinstance(
                        dependency, UnknownSource):
                    return UnknownSource(
                        "receiver-preserving ufunc result")
                deferred_sources.append(dependency)
            else:
                deferred_sources.append(arg_top)
            arg_tops.append(arg_top)

        if any(top in (None, "", "local", "unknown")
               for top in arg_tops):
            return DerivedResult(
                "receiver_preserving_ufunc",
                tuple(deferred_sources),
                func_name,
            )

        external = set(top for top in arg_tops if top != "python")
        if not external:
            return "numpy"
        if len(external) == 1:
            owner = next(iter(external))
            if owner in ("pandas", "numpy"):
                return owner
        return UnknownSource("receiver-preserving ufunc result")

    ## Check whether a call expression is a known library-to-library conversion.
    #
    #  Unwraps trailing attribute chains (e.g. data.to_numpy().T) to find
    #  the inner conversion call, then looks up (source_library, method).
    #  @param value_node The RHS expression node.
    #  @return The conversion target library name, or None.
    def _resolve_conversion_target(self, value_node):
        # Unwrap trailing attribute chain: data.to_numpy().T → data.to_numpy()
        call_node = value_node
        while isinstance(call_node, ast.Attribute) and isinstance(call_node.value, (ast.Call, ast.Attribute)):
            call_node = call_node.value

        if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Attribute):
            # Method call: data.to_numpy() → conversion if method in table.
            method = call_node.func.attr
            receiver = call_node.func.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    conv = _CONVERSION_METHOD_TARGETS.get((receiver_top, method))
                    if conv:
                        return conv
            # Not a known conversion method — fall through to check
            # function-call return types (e.g. np.log, cdist).

        if isinstance(call_node, ast.Attribute):
            # Bare attribute read: data.values → conversion if attr in table.
            # Bare method references (data.to_numpy without call) are NOT
            # conversions — saving a method object does not change the result type.
            attr_name = call_node.attr
            receiver = call_node.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    return _CONVERSION_ATTRIBUTE_TARGETS.get((receiver_top, attr_name))
            return None

        # 1.0.5 P1: function-call return type.  cdist(...) → numpy,
        # receiver-preserving ufunc np.log(pd.Series) → pandas.
        if isinstance(call_node, ast.Call):
            func_top, func_name = self._resolve_func_top(call_node.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                # Check explicit result-owner map (cdist → numpy).
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    call_node, func_top, func_name)
                if preserved is not None:
                    return preserved
        return None

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

        result_item_owner = None
        if (isinstance(node.value, ast.Subscript)
                and isinstance(node.value.value, ast.Call)):
            result_item_owner = self._resolve_call_result_item_owner(
                node.value.value)
        right = (result_item_owner
                 or self._parameter_dependency_source(node.value)
                 or self.trace_source(node.value))
        right_norm = normalize_source(right)
        if (isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(right_norm, InstanceMethod)
                and isinstance(
                    normalize_source(right_norm.receiver), CallResult)
                and right_norm.receiver.result_source is None
                and _has_result_owner_contract(right_norm.method)):
            right = CallResult(
                right_norm,
                display_name=ast.unparse(node.value.func),
                call_lineno=node.value.lineno,
                call_col_offset=node.value.col_offset,
                result_source=DerivedResult(
                    "method_result",
                    (right_norm,),
                    node.value.func.attr,
                ),
            )
        # 1.0.5 P1: if the RHS is a known conversion call
        # (e.g. data.to_numpy()), override the bound source
        # so subsequent calls on the target use the post-conversion
        # library.  Also handles data.to_numpy().T chains.
        conversion = self._resolve_conversion_target(node.value)
        if conversion:
            right_norm = normalize_source(right)
            if isinstance(right_norm, CallResult):
                right = CallResult(
                    right_norm.callee,
                    display_name=right_norm.display_name,
                    call_lineno=right_norm.call_lineno,
                    call_col_offset=right_norm.call_col_offset,
                    result_source=conversion,
                )
            else:
                right = conversion
        # Preserve an owner proven by same-scope operator operands.  This
        # covers both instance fields and ordinary locals, but never replaces
        # parameter-backed dataflow: parameters are resolved from exact
        # project call edges in the cross-file pass.
        if isinstance(node.value, (ast.BinOp, ast.UnaryOp)):
            expression_top = self._expr_receiver_top(node.value)
            right_norm = normalize_source(right)
            has_parameter = self._source_contains_parameter(right_norm)
            if (not has_parameter
                    and expression_top not in (
                        None, "", "local", "python", "unknown")):
                if (right_norm in (
                        None, "", "local", "unknown")
                        or isinstance(
                            right_norm, (UnknownSource, DerivedResult))):
                    right = expression_top
            elif not has_parameter:
                external_tops = {
                    top for top in self._operator_operand_tops(node.value)
                    if top not in (
                        None, "", "local", "python", "unknown")
                }
                if len(external_tops) > 1:
                    right = UnknownSource(
                        "conflicting operator result owners")
        # 1.0.5 P0: visit RHS before binding targets
        right_norm = normalize_source(right)
        local_receiver = (self._returned_local_class_name(right_norm.receiver)
                          if isinstance(right_norm, InstanceMethod) else None)
        if (isinstance(node.value, ast.Call) and local_receiver is not None
                and right_norm.method in self.class_methods[local_receiver]):
            right = CallResult(
                right, display_name=ast.unparse(node.value.func),
                call_lineno=node.value.lineno,
                call_col_offset=node.value.col_offset,
                result_source=right)
        self.generic_visit(node)
        # Assignment-call metadata is flow-sensitive too.  Keep the previous
        # binding visible while nested RHS calls collect their argument
        # sources, then invalidate or replace it before binding the LHS.
        for name in target_names:
            key = (id(self.current_scope()), name)
            if imported_call is None:
                self._assigned_call_sources.pop(key, None)
            else:
                self._assigned_call_sources[key] = imported_call
        # 1.0.5 P0: call_assign_funcs after generic_visit
        value_node = node.value
        # Unwrap trailing attributes for call_assign_funcs:
        # data = data.to_numpy().T  →  extract data.to_numpy
        while isinstance(value_node, ast.Attribute):
            value_node = value_node.value
        if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Attribute):
            func_full = self._attribute_name(value_node.func)
            if func_full:
                for name in target_names:
                    self.call_assign_funcs[name] = func_full
        return right

    ## Resolve a class identity through already defined local return summaries.
    #  @param source Receiver value, not the name of the producing method.
    #  @param seen Local return-summary cycle guard.
    #  @return Local class name or None without uniform constructor evidence.
    def _returned_local_class_name(self, source, seen=None):
        source = normalize_source(source)
        seen = set(seen or ())
        if isinstance(source, SourceSet):
            names = [self._returned_local_class_name(item, seen)
                     for item in source.sources]
            return (names[0] if names and names[0] is not None
                    and all(name == names[0] for name in names) else None)
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            callee = source.callee
            if callee in self.class_methods:
                return callee
            if callee not in seen:
                seen.add(callee)
                return self._returned_local_class_name(
                    self.return_sources.get(callee), seen)
        if isinstance(source, str) and source in self.class_methods:
            return source
        return None

    ## Visit an AnnAssign node (x: T = expr) with RHS-before-target ordering.
    #
    #  Same contract as visit_Assign: visit the RHS value before binding
    #  the target symbol so nested RHS calls use the pre-assignment state.
    #  @param node The AnnAssign AST node.
    def visit_AnnAssign(self, node):
        if node.value is None:
            return
        mapping_value = self._mapping_facts.value(node.value)
        assignment_container_kind, assignment_item_kind = (
            self._expression_container_shape(node.value))
        assignment_item_fields = self._expression_container_item_fields(
            node.value)
        assignment_container_kind = assignment_container_kind or None
        assignment_item_kind = assignment_item_kind or None
        targets = []
        if isinstance(node.target, ast.Name):
            targets.append(node.target.id)
        elif isinstance(node.target, ast.Attribute):
            name = self._attribute_name(node.target)
            if name and name.startswith("self."):
                targets.append(name)
        elif isinstance(node.target, (ast.Tuple, ast.List)):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    targets.append(elt.id)
        field_targets = [
            name for name in targets if name.startswith("self.")]
        right = self._visit_assignment(node, targets, field_targets)
        if isinstance(node.target, ast.Attribute):
            self._invalidate_attribute_tuple_item_sources(node.target)
        self._record_local_constructor_fields(node, targets)
        callable_keys = {}
        if isinstance(node.value, ast.Lambda):
            lambda_result = right or UnknownSource("lambda result")
            lambda_key = self._local_lambda_key(node.value)
            for name in targets:
                callable_keys[name] = lambda_key
            self.return_sources[lambda_key] = lambda_result
            right = "local"

        if right:
            right_norm = normalize_source(right)
            if isinstance(node.target, ast.Name):
                if isinstance(right, str) and right == node.target.id:
                    pass  # skip self-assign
                else:
                    self._bind_target_name(
                        node.target.id, right, node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        callable_key=callable_keys.get(node.target.id, ""),
                        container_item_fields=assignment_item_fields)
            elif isinstance(node.target, ast.Attribute):
                name = self._attribute_name(node.target)
                attr_name = name if name and name.startswith("self.") else (
                    self._instance_attribute_target_name(name))
                if attr_name:
                    self._bind_target_name(
                        attr_name, right, node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        container_item_fields=assignment_item_fields)
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        self._bind_target_name(elt.id, right, elt)
        else:
            if isinstance(node.target, ast.Name):
                self._bind_target_name(
                    node.target.id, 'local', node.target,
                    container_kind=assignment_container_kind or "",
                    container_item_kind=assignment_item_kind or "",
                    callable_key=callable_keys.get(node.target.id, ""),
                    container_item_fields=assignment_item_fields)
            elif isinstance(node.target, ast.Attribute):
                name = self._attribute_name(node.target)
                if name and name.startswith("self."):
                    self._bind_target_name(
                        name, 'local', node.target,
                        container_kind=assignment_container_kind or "",
                        container_item_kind=assignment_item_kind or "",
                        container_item_fields=assignment_item_fields)
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        self._bind_target_name(elt.id, 'local', elt)

        self._bind_mapping_value(node.target, mapping_value)

    ## Reject identities affected by augmented assignment or deletion.
    #  @param node AugAssign AST node.
    def visit_AugAssign(self, node):
        self._mapping_facts.escape(node.target)
        self._mapping_facts.escape(node.value)
        self.generic_visit(node)
        self._bind_mapping_value(node.target, None)

    ## Invalidate mapping aliases when a binding or item is deleted.
    #  @param node Delete AST node.
    def visit_Delete(self, node):
        for target in node.targets:
            self._mapping_facts.escape(target)
            self._bind_mapping_value(target, None)
        self.generic_visit(node)

    ## Do not reuse mapping identities across an unsupported walrus rebind.
    #  @param node NamedExpr AST node.
    def visit_NamedExpr(self, node):
        self.generic_visit(node)
        self._bind_mapping_value(node.target, None)

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

    ## Record fields of a literal element appended to a known list.
    #  @param node Append call AST node.
    def _record_container_append_shape(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr != "append"
                or len(node.args) != 1):
            return
        receiver = node.func.value
        receiver_kind, _ = self._expression_container_shape(receiver)
        if receiver_kind != "list":
            return

        ## Preserve a homogeneous owner fact for later iteration.  This is
        # based on the appended value's traced source, not on append itself.
        # Any unresolved or conflicting append invalidates the fact.
        def record_item_source(binding, item_source):
            if binding is None or binding.container_kind != "list":
                return
            key = self._binding_key(binding)
            current = self._iterated_append_sources.get(key)
            current_norm = normalize_source(current)
            current_owner = (
                self._structured_source_owner_top(current_norm)
                if current_norm is not None else None)
            item_owner = self._structured_source_owner_top(item_source)
            if isinstance(current_norm, UnknownSource):
                current_display = current_norm.display
                if current_display == "empty iterable":
                    current_owner = None
            if item_owner is None:
                self._iterated_append_sources[key] = UnknownSource(
                    "unresolved appended item")
            elif current_owner is None or current_owner == item_owner:
                self._iterated_append_sources[key] = item_owner
            else:
                self._iterated_append_sources[key] = UnknownSource(
                    "conflicting iterable items")

        def tuple_item_source(value):
            """Return exact field evidence for one appended tuple/list."""
            if not isinstance(value, (ast.Tuple, ast.List)):
                return None
            items = []
            for field in value.elts:
                shape = self._expression_python_shape(field)
                if shape is not None:
                    items.append(shape)
                    continue
                source = normalize_source(
                    self._call_edge_argument_source(field))
                if source is None or isinstance(source, UnknownSource):
                    return None
                items.append(source)
            return TupleSource(tuple(items))

        item_source = normalize_source(self.trace_source(node.args[0]))
        if isinstance(receiver, ast.Name):
            binding = self.current_scope().lookup(
                receiver.id, skip_parent_classes=True)
            record_item_source(binding, item_source)
            tuple_source = tuple_item_source(node.args[0])
            if binding is not None:
                key = self._binding_key(binding)
                if key in self._iterated_append_tuple_conflicts:
                    pass
                elif tuple_source is None:
                    self._iterated_append_tuple_sources.pop(key, None)
                    self._iterated_append_tuple_conflicts.add(key)
                else:
                    previous = self._iterated_append_tuple_sources.get(key)
                    if previous is None or previous == tuple_source:
                        self._iterated_append_tuple_sources[key] = tuple_source
                    else:
                        self._iterated_append_tuple_sources.pop(key, None)
                        self._iterated_append_tuple_conflicts.add(key)
        elif isinstance(receiver, ast.Attribute):
            key = self._attribute_container_key(receiver)
            tuple_source = tuple_item_source(node.args[0])
            if key is not None:
                if key in self._attribute_append_tuple_conflicts:
                    pass
                elif tuple_source is None:
                    self._attribute_append_tuple_sources.pop(key, None)
                    self._attribute_append_tuple_conflicts.add(key)
                else:
                    previous = self._attribute_append_tuple_sources.get(key)
                    if (previous is None
                            or previous == tuple_source
                            or self._tuple_item_owners_match(
                                previous, tuple_source)):
                        self._attribute_append_tuple_sources[key] = tuple_source
                    else:
                        self._attribute_append_tuple_sources.pop(key, None)
                        self._attribute_append_tuple_conflicts.add(key)

        ## Preserve a homogeneous item shape only when the appended value is
        # independently proven by syntax or an existing result contract.  An
        # unknown or conflicting append invalidates the binding fact so later
        # iteration cannot infer a receiver type from an incomplete list.
        item_shape = self._expression_python_shape(node.args[0])
        item_kind = (
            item_shape.kind
            if isinstance(item_shape, PythonShape) and item_shape.kind
            else "")

        def record_item_kind(binding, container_name):
            if binding is None or binding.container_kind != "list":
                return
            conflict_key = self._binding_key(binding)
            if conflict_key in self._container_item_kind_conflicts:
                return
            current = binding.container_item_kind or ""
            if not item_kind or (current and current != item_kind):
                binding.container_item_kind = ""
                self.container_item_kinds.pop(container_name, None)
                self._container_item_kind_conflicts.add(conflict_key)
                return
            binding.container_item_kind = item_kind
            self.container_item_kinds[container_name] = item_kind

        if isinstance(receiver, ast.Name):
            record_item_kind(
                self.current_scope().lookup(
                    receiver.id, skip_parent_classes=True),
                receiver.id)

        fields = self._literal_dict_field_shapes(node.args[0])
        if not fields:
            if isinstance(receiver, ast.Attribute):
                name = self._attribute_name(receiver)
                if name and name.startswith("self.") and self._class_stack:
                    key = (self._class_stack[-1], name)
                    if item_kind:
                        self.instance_attr_item_kinds[key] = item_kind
                    else:
                        self.instance_attr_item_kinds.pop(key, None)
            return
        if isinstance(receiver, ast.Name):
            binding = self.current_scope().lookup(
                receiver.id, skip_parent_classes=True)
            if binding is not None and binding.container_kind == "list":
                binding.container_item_fields = dict(fields)
            return
        if isinstance(receiver, ast.Attribute):
            name = self._attribute_name(receiver)
            if name and name.startswith("self.") and self._class_stack:
                self.instance_attr_item_fields[(
                    self._class_stack[-1], name)] = dict(fields)

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

    ## Build a positional source summary for a tuple return expression.
    #
    #  The tuple itself has no single owner. Preserve each element source so
    #  a cross-file call edge can bind ``left, right = make_pair()`` by
    #  position without promoting one element's owner to the whole tuple.
    #  @param value Tuple AST node.
    #  @return DerivedResult with one source per tuple element, or None when
    #  any element cannot be traced.
    def _tuple_return_source(self, value):
        if not isinstance(value, ast.Tuple):
            return None
        elements = []
        for element in value.elts:
            source = self.trace_source(element)
            if source is None:
                return None
            elements.append(normalize_source(source))
        return DerivedResult("tuple", tuple(elements))

    ## Check whether a statement sequence definitely cannot fall through.
    #  @param statements Function or branch statements.
    #  @return True for a proven return/raise on every path.
    def _block_exits(self, statements):
        for statement in statements:
            if isinstance(statement, (ast.Return, ast.Raise)):
                return True
            if (isinstance(statement, ast.If)
                    and self._block_exits(statement.body)
                    and self._block_exits(statement.orelse)):
                return True
        return False

    ## Preserve arithmetic return operands at their evaluation point.
    #  @param node Return expression or one of its operands.
    #  @return Structured value source, including unsupported operands.
    def _return_expression_source(self, node):
        if isinstance(node, ast.BinOp):
            return DerivedResult("expression", (
                self._return_expression_source(node.left),
                self._return_expression_source(node.right)),
                type(node.op).__name__)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return PythonShape("bool")
            return DerivedResult("expression", (
                self._return_expression_source(node.operand),),
                type(node.op).__name__)
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is None:
                return UnknownSource("unbound return operand")
        shape = self._expression_python_shape(node)
        if shape is not None:
            if shape.kind == "NoneType":
                return UnknownSource("non-arithmetic None operand")
            return shape
        dependency = self._parameter_dependency_source(
            node, expression_context=True)
        return (dependency or self._call_edge_argument_source(node)
                or UnknownSource("unresolved return operand"))

    ## Visit a Return node and record return-value flow for the function.
    #  @param node The Return AST node.
    def visit_Return(self, node):
        if node.value is not None:
            self._mapping_facts.escape(node.value)
        if self._caller_stack:
            return_key = self._caller_stack[-1].qualname
            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                elements = [
                    self._expression_python_shape(element)
                    or self._call_edge_argument_source(element)
                    or UnknownSource("unresolved returned element")
                    for element in node.value.elts
                ]
            else:
                returned = None
                if node.value is not None:
                    returned = (self._expression_python_shape(node.value)
                                or self._call_edge_argument_source(node.value))
                elements = [ContainerIter(returned) if returned is not None
                            else UnknownSource("unresolved returned iterable")]
            self.return_element_sources.setdefault(return_key, []).extend(
                elements)
        cg_source = None
        if self._func_stack and node.value is not None:
            func_name = self._func_stack[-1]
            source = None
            if isinstance(node.value, (ast.BinOp, ast.UnaryOp)):
                source = self._return_expression_source(node.value)
            elif (isinstance(node.value, ast.Call)
                  and isinstance(node.value.func, ast.Attribute)):
                source = self._parameter_dependency_source(
                    node.value, expression_context=True)
            tuple_source = self._tuple_return_source(node.value)
            result_kind = _container_kind(node.value)
            # A tuple owns only the aggregate object.  Its unpacked items may
            # have unrelated owners, so do not promote the function's entire
            # return contract to Python from a tuple literal alone.
            if tuple_source is not None:
                source = tuple_source
            elif source is not None:
                pass
            elif result_kind is not None and result_kind != "tuple":
                source = "python"
            elif (isinstance(node.value, ast.Name)
                  and self._lookup_container_kind(node.value.id) is not None):
                source = "python"
            else:
                source = self.trace_source(node.value)
            if source:
                if isinstance(source, str) and source in self.symbols.direct:
                    s = self.symbols.direct[source]
                    new_src = s if s else source
                else:
                    new_src = source
                if (source == "local" and isinstance(node.value, ast.Name)
                        and node.value.id in self.function_params.get(func_name, [])):
                    new_src = node.value.id
                ## Write qualified key for class methods; bare key only
                ## for non-class functions to prevent cross-class pollution.
                if self._class_stack:
                    qkey = self._class_stack[-1] + "." + func_name
                    return_key = qkey
                else:
                    return_key = func_name
                cg_source = tuple_source or new_src
                if tuple_source is not None:
                    old_cg = self.call_graph_return_sources.get(return_key)
                    self.call_graph_return_sources[return_key] = (
                        make_source_set(
                            [old_cg, new_src] if old_cg else [new_src],
                            origin="return"))
                else:
                    old_legacy = self.return_sources.get(return_key)
                    self.return_sources[return_key] = make_source_set(
                        [old_legacy, new_src]
                        if old_legacy else [new_src],
                        origin="return")
                    # Preserve a mixed tuple/non-tuple contract when a
                    # function has both return shapes across branches.
                    if return_key in self.call_graph_return_sources:
                        old_cg = self.call_graph_return_sources[return_key]
                        self.call_graph_return_sources[return_key] = (
                            make_source_set(
                                [old_cg, new_src], origin="return"))
                self._add_symbol_ref(
                    func_name + ".return", source, "return", node)
        if self._caller_stack:
            # Protocol resolution needs every return alternative, including
            # scalar/None branches that have no legacy symbol provenance.
            if node.value is None:
                cg_source = PythonShape("NoneType")
            else:
                shape = self._call_edge_protocol_source(node.value)
                if isinstance(node.value, ast.Tuple):
                    cg_source = DerivedResult("tuple", tuple(
                        self._call_edge_protocol_source(element)
                        or self._call_edge_argument_source(element)
                        or UnknownSource("unresolved returned tuple item")
                        for element in node.value.elts))
                elif shape is not None:
                    cg_source = shape
                elif isinstance(node.value, (ast.Name, ast.Subscript)):
                    cg_source = self._call_edge_argument_source(node.value)
                elif cg_source is None:
                    cg_source = shape
            cg_source = cg_source or UnknownSource("unresolved return branch")
            return_key = self._caller_stack[-1].qualname
            old_cg = self.call_graph_return_values.get(return_key)
            self.call_graph_return_values[return_key] = make_source_set(
                [old_cg, cg_source] if old_cg else [cg_source], origin="return")
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
