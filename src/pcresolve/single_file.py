## @package pcresolve.single_file
#  Provide single-file AST-based API call tracing.
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved primary owners and supporting provenance.

import ast
from .single_file_method_resolution import SingleFileMethodResolutionMixin
from .single_file_binding_resolution import (
    SingleFileBindingResolutionMixin,
)
from .single_file_parameter_dependency import (
    SingleFileParameterDependencyMixin,
)
from .single_file_receiver_resolution import (
    SingleFileReceiverResolutionMixin,
)
from .single_file_argparse import SingleFileArgparseMixin
from .single_file_returns import SingleFileReturnMixin
from .single_file_call_collection import SingleFileCallCollectionMixin
from .single_file_assignment import SingleFileAssignmentMixin
from .single_file_source_resolution import SingleFileSourceResolutionMixin
from .single_file_control_flow import SingleFileControlFlowMixin
from .single_file_definitions import SingleFileDefinitionMixin
from .single_file_container_shapes import (
    SingleFileContainerShapeMixin, _container_kind,
)
from .mapping_facts import MappingFacts, bound_names as mapping_bound_names
from .symbol_table import SymbolTable
from .import_facts import import_facts, resolve_relative_module
from .scope import Scope, SCOPE_MODULE, SCOPE_CLASS
from .sources import source_display
from .call_graph import FunctionId, ModuleCallGraph

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
                         SingleFileBindingResolutionMixin,
                         SingleFileParameterDependencyMixin,
                         SingleFileReceiverResolutionMixin,
                         SingleFileArgparseMixin,
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
