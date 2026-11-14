## @package pcresolve.ownership.collect.single_file
#  Provide single-file AST-based API call tracing.
#  提供基于单文件 AST 的 API 调用追踪。
#
#  Contains the SingleFileAnalyzer class which visits every node in a
#  Python file's AST and builds a symbol table + list of API calls with
#  their resolved primary owners and supporting provenance.

import ast
from pcresolve.ownership.collect.single_file_method_resolution import SingleFileMethodResolutionMixin
from pcresolve.ownership.collect.single_file_binding_resolution import (
    SingleFileBindingResolutionMixin,
)
from pcresolve.ownership.collect.single_file_parameter_dependency import (
    SingleFileParameterDependencyMixin,
)
from pcresolve.ownership.collect.single_file_receiver_resolution import (
    SingleFileReceiverResolutionMixin,
)
from pcresolve.ownership.collect.single_file_argparse import SingleFileArgparseMixin
from pcresolve.ownership.collect.single_file_returns import SingleFileReturnMixin
from pcresolve.ownership.collect.single_file_call_collection import SingleFileCallCollectionMixin
from pcresolve.ownership.collect.single_file_assignment import SingleFileAssignmentMixin
from pcresolve.ownership.collect.single_file_source_resolution import SingleFileSourceResolutionMixin
from pcresolve.ownership.collect.single_file_control_flow import SingleFileControlFlowMixin
from pcresolve.ownership.collect.single_file_definitions import SingleFileDefinitionMixin
from pcresolve.ownership.collect.single_file_container_shapes import (
    SingleFileContainerShapeMixin, _container_kind,
)
from pcresolve.ownership.mapping_facts import MappingFacts, bound_names as mapping_bound_names
from pcresolve.ownership.symbol_table import SymbolTable
from pcresolve.facts.import_facts import import_facts, resolve_relative_module
from pcresolve.ownership.scope import Scope, SCOPE_MODULE, SCOPE_CLASS
from pcresolve.ownership.sources import source_display
from pcresolve.ownership.call_graph import FunctionId, ModuleCallGraph
from pcresolve.ownership.fact_versions import FactStructure, VersionedList

from pcresolve.ownership.types import FileAnalysis, ApiCall

## AST visitor that traces all symbols and API calls in a single Python file.
## 追踪单个 Python 文件中所有符号和 API 调用的 AST 访问器。
#
#
#  Walks the AST to:
#  - Record import mappings and their aliases
#  - Track assignments, function/class definitions, decorators
#  - Resolve with/for return-value flows
#  - Handle container indexing, class inheritance, method resolution
#  - Detect and classify all API call expressions
class SingleFileAnalyzer(FactStructure, SingleFileSourceResolutionMixin,
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
    _versioned_fields = {'symbol_refs': VersionedList}
    ## Initialize the analyzer with empty state.
    ## 使用空状态初始化分析器。
    #
    #  @param module_name Optional dotted module name for resolving relative imports.
    #  @param is_package Whether the file is a package __init__.py.
    #  @param file_path Source location metadata.
    #  @param analysis_budget Optional internal cooperative analysis budget.
    #  @return None; per-file facts, lexical scopes, and caches are initialized.
    def __init__(self, module_name=None, is_package=False, file_path="", analysis_budget=None):
        self._analysis_budget = analysis_budget
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
        self._expression_query_cache = None
        self.defined_functions = set()
        self.function_params = {}
        self._parameter_name_index = None
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
    ## 访问循环或异常处理中赋值的名称时，禁用映射事实合并。
    #  Existing owner and protocol analysis remains unchanged.
    #  现有归属与协议分析行为保持不变。
    #
    #  @param node AST node.
    #  @return Visitor result for the node, or None when no visitor handles it.
    def visit(self, node):
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint()
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try)):
            return super().visit(node)
        names = mapping_bound_names([node])
        scope = self.current_scope()
        previous = self._mapping_blocked_names

        # Hide loop and exception bindings from mapping joins while visiting the construct.
        # 访问控制流结构期间，将其绑定从映射事实合并中屏蔽。
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
    ## 收集完所有可能的变更后，补全映射调用证据。
    #
    #  @param node Module AST node.
    #  @return None; module source and mapping-call summaries are finalized.
    def visit_Module(self, node):
        self._module_tree = node
        self.generic_visit(node)
        for edge, value in self._mapping_edges:
            edge.mapping_targets, edge.mapping_targets_complete = value.targets()

    ## Find signatures containing a parameter in original definition order.
    ## 按原始定义顺序查找包含指定参数的函数签名。
    #
    #  @param name Parameter name.
    #  @return Ordered (function name, first positional index) pairs.
    def _parameter_definitions(self, name):
        if self._parameter_name_index is None:
            index = {}
            for function, parameters in self.function_params.items():
                seen = set()
                for position, parameter in enumerate(parameters):
                    if parameter not in seen:
                        index.setdefault(parameter, []).append((function, position))
                        seen.add(parameter)
            self._parameter_name_index = index
        return self._parameter_name_index.get(name, ())

    ## Look up mapping facts without importing a deferred closure's bindings.
    ## 查找映射事实时，不引入延迟闭包中的绑定。
    #
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
    ## 将映射事实与被赋值对象的归属信息分开保存。
    #
    #  @param target Assignment target.
    #  @param value Captured mapping value.
    #  @return None; mapping identity is updated or invalidated according to the target.
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
    ## 返回当前最内层的词法作用域。
    #
    #  @return Current Scope at the top of the scope stack.
    def current_scope(self):
        return self.scope_stack[-1]

    ## Push a new scope onto the stack.
    ## 将新的词法作用域压入作用域栈。
    #
    #  @param kind Scope kind constant.
    #  @param name Human-readable scope name.
    #  @return The new Scope.
    def push_scope(self, kind, name):
        parent = self.current_scope()
        scope = Scope(kind, name, parent)
        self.scope_stack.append(scope)
        return scope

    ## Pop the current scope from the stack.
    ## 从作用域栈中弹出当前作用域。
    #
    #  @return The popped Scope.
    def pop_scope(self):
        return self.scope_stack.pop()

    ## Return the stable analyzer-local identity of a lexical binding.
    ## 返回词法绑定在当前分析器内稳定的身份键。
    #
    #  @param binding Binding created by this analyzer.
    #  @return Monotonic assignment index unique within the analyzed file.
    def _binding_key(self, binding):
        return binding.assignment_index

    ## Bind a name in the current lexical scope and compatibility symbol table.
    ## 在当前词法作用域和兼容符号表中绑定名称。
    #
    #  Only module-scope and explicit global bindings enter self.symbols.
    #
    #  @param name Symbol name.
    #  @param source Source value.
    #  @param node Optional AST node for position info.
    #  @param kind Optional symbol kind for provenance ("variable", "parameter", "attribute").
    #  @param container_kind Optional container shape retained with the binding.
    #  @param container_item_kind Optional element shape retained for containers.
    #  @param callable_key Optional stable identity for a locally bound callable.
    #  @param container_item_fields Optional field facts for structured items.
    #  @return None; lexical, symbol, attribute, and provenance facts are updated.
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
    ## 规范化类限定的实例字段赋值目标。
    #  单例可经类持有对象初始化实例字段；后续方法仍以 self.<field> 访问。
    #  只保留语法绑定关系，不从字段名或方法名推断外部返回类型。
    #
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
    ## 沿词法作用域链查找名称，未找到时返回名称本身。
    #
    #  Unified helper so that trace_source, get_base, and _resolve_call_receiver
    #  all use the same scope-aware resolution.
    #
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
    ## 为本地赋值的可调用对象构造作用域限定键。
    #
    #  @param name Assignment target name.
    #  @return Stable key used in return_sources.
    def _local_callable_key(self, name):
        parts = list(self._class_stack) + list(self._func_stack) + [name]
        return ".".join(parts)

    ## Build a stable scope-qualified key for an inline lambda callable.
    ## 为内联 lambda 构造稳定的作用域限定键。
    #
    #  @param node Lambda expression.
    #  @return Source-location-qualified callable key.
    def _local_lambda_key(self, node):
        name = "<lambda>@%d:%d" % (node.lineno, node.col_offset)
        return self._local_callable_key(name)

    ## Preserve a local callable's identity when stored as a value.
    ## 将本地可调用对象作为值保存时保留其身份。
    #
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
    ## 访问 Import 节点并记录别名到模块的映射。
    #
    #  @param node The Import AST node.
    #  @return None; aliases and binding-source facts are recorded.
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
    ## 访问 ImportFrom 节点并记录别名到模块或符号的映射。
    #
    #  @param node The ImportFrom AST node.
    #  @return None; import bindings are recorded and child nodes are visited.
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


## Analyze a single source string and return per-file results.
## 分析单个 Python 源码字符串并返回逐文件结果。
#  该便捷函数解析源码并运行完整分析，生成包含符号、来源链和 API 调用的 FileAnalysis。
#
#  @param source Python source code string to parse and analyze.
#  @param file_path Optional source path recorded in the result.
#  @return FileAnalysis containing symbols, provenance chains, and API calls.
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
