## @package pcresolve.flow.index.source
#  Build flow source indexes.
#
#
#  Source discovery, parsing and generation-local definition indexes.
#  源码发现、解析和按源码代次隔离的定义索引。



import ast

import os

from dataclasses import asdict, replace

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches

from pcresolve.flow.index.generation import same_generation

from pcresolve.facts.program_facts import SourceSpan, FunctionSignature, bind_ast_call

from pcresolve.frontend.source_snapshot import (SourceStore, ModuleIndex, FLOW_SOURCE, FLOW_MODULES,
                              module_name_for_path)

from pcresolve.facts.call_resolution import DefinitionRecord, DefinitionIndex, CallContext

from pcresolve.facts.scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)

from pcresolve.facts.import_facts import import_facts, resolve_relative_module

from pcresolve.facts.star_imports import static_star_imports


## Find root names of attribute or subscript writes in the current scope.
## 查找当前作用域内属性或下标写入的根名称。
#
#  @param node Source AST node.
#  @return Set of root names, excluding nested definitions.
def _attribute_write_roots(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                         ast.Lambda)):
        return set()
    roots = set()
    if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
            node.ctx, (ast.Store, ast.Del)):
        root = node.value
        while isinstance(root, (ast.Attribute, ast.Subscript)):
            root = root.value
        if isinstance(root, ast.Name):
            roots.add(root.id)
    for child in ast.iter_child_nodes(node):
        roots.update(_attribute_write_roots(child))
    return roots

## Build the source and definition index owned by one FlowAnalyzer.
## 构建单个 FlowAnalyzer 拥有的源码和定义索引。
class SourceIndexMixin:

    ## Build a source generation and reset per-query analysis state.
    ## 构建源码生成版本并重置每次查询的分析状态。
    #
    #  @param preserve_source_facts Reuse compatible facts from the same source generation.
    #  @return None
    def _index(self, preserve_source_facts=False):
        # Budgets, contracts and incoming contexts belong to one query even
        # when the source facts are unchanged.
        source_fact_cache_names = (
            '_scope_fact_cache', '_syntax_fact_cache', '_module_syntax_index_cache', '_kind_alias_module_cache',
            '_source_line_cache', '_source_evidence_cache',
            '_class_binding_write_cache',
            '_class_binding_escape_cache', '_class_decoration_cache',
            '_class_creation_cache', '_module_class_prefix_cache', '_native_class_protocol_cache',
            '_builtin_scope_cache', '_builtin_module_cache',
            '_decorator_import_namespace_cache', '_fresh_receiver_hook_premise',
            '_fresh_receiver_metadata_guard', '_fresh_function_observer_premise',
            '_contextmanager_namespace_premise', '_function_namespace_cache',
            '_function_factory_cache', '_signature_factory_namespace',
            '_metadata_stdlib_namespace',
            '_supporting_source_hashes',
            '_partial_class_namespace_premise', '_module_getattr_cache_premises',
            '_coroutine_namespace_premises', '_property_namespace_premises',
            '_decorator_literal_writes', '_class_type_test_namespace',
        )
        runtime_namespace_cache = getattr(self, '_runtime_namespace_cache', False)
        previous_runtime_namespace = (
            runtime_namespace_cache
            if self._analysis_budget is None and runtime_namespace_cache is not False
            else False)
        # Syntax facts depend only on this source generation. They stay valid
        # across unbudgeted queries even though every query owns its propagation
        # budget and incoming contexts.
        # 语法事实只依赖当前源码代次；在无协作预算时，不同查询可复用它们。
        generation_fact_names = ('_scope_fact_cache', '_builtin_scope_cache',
                                 '_builtin_module_cache')
        previous_generation_facts = (
            {name: getattr(self, name) for name in generation_fact_names if hasattr(self, name)}
            if self._analysis_budget is None else {})
        previous_source_facts = ({name: getattr(self, name) for name in source_fact_cache_names
                                  if hasattr(self, name)} if preserve_source_facts else {})
        self._scope_fact_cache = {}
        self._syntax_fact_cache = {}
        self._module_syntax_index_cache = {}
        self._kind_alias_module_cache = {}
        self._source_line_cache = {}
        self._source_evidence_cache = {}
        self._class_return_cache = {}
        self._class_return_stack = []
        self._context_summaries = {}
        self._context_call_count = 0
        self._object_return_cache = {}
        self._object_fact_functions = 500
        self._object_fact_steps = 2000
        self._function_effect_cache = {}
        self._function_effect_stack = set()
        self._nested_effect_failures = {}
        self._effect_fact_functions = 500
        self._effect_fact_steps = 2000
        self._class_effect_fact_steps = 2000
        self._fact_functions = 500
        self._fact_calls = 2000
        self._class_binding_write_cache = None
        self._class_binding_escape_cache = None
        self._class_binding_escape_scan = False
        self._callable_instance_binding_cache = {}
        self._capture_name_cache = {}
        self._decoration_fact_cache = {}
        self._fresh_decoration_fact_cache = {}
        self._class_decoration_cache = {}
        self._class_creation_cache = {}
        self._module_class_prefix_cache = {}
        self._metadata_query_cache = {}
        self._metadata_observer_cache = {}
        self._native_class_protocol_cache = {}
        self._class_type_test_namespace = None
        self._class_identity_cache = {}
        self._class_identity_steps = 20000
        self._class_identity_layout_guard = None
        self._class_identity_instance_guards = {}
        self._class_identity_guard_failures = {}
        self._decorator_import_namespace_cache = {}
        self._fresh_receiver_hook_premise = None
        self._fresh_receiver_metadata_guard = None
        self._fresh_function_observer_premise = False
        self._contextmanager_namespace_premise = None
        self._function_namespace_cache = {}
        self._function_factory_cache = {}
        self._signature_factory_namespace = None
        self._metadata_stdlib_namespace = {}
        self._runtime_namespace_cache = False
        self._supporting_source_hashes = {}
        self._partial_class_namespace_premise = None
        self._module_getattr_cache_premises = None
        self._builtin_scope_cache = {}
        self._builtin_module_cache = {}
        self._coroutine_namespace_premises = None
        self._property_namespace_premises = None
        self._decorator_literal_writes = None
        self._context_enter_cache = {}
        self._context_enter_stack = []
        self._context_exit_stack = []
        self._source_snapshot = (
            self._source_store.snapshot(sorted(self.files), FLOW_SOURCE, budget=self._analysis_budget)
            if self._analysis_budget is not None
            else self._source_store.snapshot(sorted(self.files), FLOW_SOURCE))
        previous = getattr(self, '_indexed_snapshot', None)
        if same_generation(previous, self._source_snapshot,
                           self._indexed_roots if previous is not None else (), self.roots):
            for name, value in previous_source_facts.items():
                setattr(self, name, value)
            # Runtime namespace writes depend only on this immutable source
            # generation. Preserve both complete results and conservative
            # unknown results across unbudgeted queries; budgeted queries must
            # rebuild so their work limits remain authoritative.
            # 源码版本不变时可复用事实；有预算的查询仍须重新计量工作量。
            if self._analysis_budget is None:
                self._runtime_namespace_cache = previous_runtime_namespace
                for name, value in previous_generation_facts.items():
                    setattr(self, name, value)
            return
        # Clear the reusable generation before construction so an interrupted
        # or failed build cannot expose partially rebuilt facts on the next query.
        # 构建前清空可复用版本，避免中断后暴露部分索引。
        self._indexed_snapshot = None
        self.definitions = []
        self.classes = []
        self.imports = {}
        self.module_bindings = {}
        self.module_bodies = {}
        self.import_binding_facts = {}
        self.texts = {}
        self.hashes = {}
        self.index_boundaries = []
        self.definition_conditions = {}
        # Preserve the prior behavior of deriving names only for parseable files.
        self._module_index = ModuleIndex.build(
            [path for path in sorted(self.files)
             if self._source_snapshot.documents[path].error is None], self.roots, FLOW_MODULES)
        next_file_indexes = {}
        for path in sorted(self.files):
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint(force=True)
            document = self._source_snapshot.documents[path]
            if document.error is not None:
                self.index_boundaries.append({
                    'file_path': path, 'reason': 'source_unavailable',
                    'detail': str(document.error),
                    'module': module_name_for_path(path, self.roots, FLOW_MODULES)})
                continue
            source, tree = document.text, document.tree
            self.texts[path] = source
            self.hashes[path] = document.sha256
            module = self._module_index.file_to_module[path]
            self.module_bodies.setdefault(module, []).append((path, tree.body))
            cached = getattr(self, '_file_indexes', {}).get(path)
            identity = (module, tuple(self.roots), self._source_snapshot.policy)
            if cached is None or cached[0] is not document or cached[1] != identity:
                facts = self._collect_file_index(path, document, module)
            else:
                facts = cached[2]
            next_file_indexes[path] = document, identity, facts
            bindings, aliases, bound, definitions, classes, conditions = facts
            self.import_binding_facts.setdefault(module, []).append(
                {name: list(nodes) for name, nodes in bindings})
            self.imports[module] = dict(aliases)
            self.module_bindings[module] = set(bound)
            self.definitions.extend(definitions)
            self.classes.extend(classes)
            self.definition_conditions.update(conditions)
        # Add statically supported wildcard bindings after collecting module bodies.
        # 收集模块体后，再加入静态支持的通配符导入绑定。
        star_facts = static_star_imports(self.module_bodies)
        for module, aliases in star_facts.aliases.items():
            self.imports[module].update(aliases)
            for name, statement in star_facts.bindings[module].items():
                self.import_binding_facts[module][0][name] = [statement]
        self._file_indexes = next_file_indexes
        self._definition_index = DefinitionIndex(
            [DefinitionRecord(ref.module, ref.qualname, (ref, node),
                              source_span=SourceSpan.from_ast(ref.file_path, node))
             for ref, node in self.definitions] +
            [DefinitionRecord(ref.module, ref.qualname, (ref, node), kind='class',
                              source_span=SourceSpan.from_ast(ref.file_path, node))
             for ref, node in self.classes])
        self._indexed_snapshot = self._source_snapshot
        self._indexed_roots = tuple(self.roots)

    ## Encode one source file for span extraction once per source generation.
    ## 每个源码文件在当前源码代次内只编码一次，供跨度提取复用。
    #
    #  @param path Source file path captured by the current generation.
    #  @return UTF-8 encoded source lines.
    def _source_lines(self, path):
        cached = self._source_line_cache.get(path)
        if cached is None:
            cached = [line.encode('utf-8') for line in self.texts[path].split('\n')]
            self._source_line_cache[path] = cached
        return cached

    ## Collect immutable file facts independently of query state.
    ## 独立于查询状态收集不可变文件事实。
    #
    #  @param path Source path.
    #  @param document Exact read-only source version.
    #  @param module Module identity under current import roots.
    #  @return Binding, import and definition facts in source order.
    def _collect_file_index(self, path, document, module):
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        tree = document.tree
        definitions, classes, definition_conditions = [], [], []
        bindings = {}
        contains_global_statement = any(
            isinstance(node, ast.Global) for node in ast.walk(tree))
        for statement in tree.body:
            names = (list(fact.python_binding for fact in import_facts(statement))
                     if isinstance(statement, (ast.Import, ast.ImportFrom))
                     else statement_scope_facts([statement]).bound
                     | _attribute_write_roots(statement))
            for name in names:
                bindings.setdefault(name, []).append(statement)
            if (contains_global_statement
                    and isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                               ast.ClassDef))):
                for scope in ast.walk(statement):
                    if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    facts = self._builtin_scope_facts(scope)
                    changed = facts.globals & facts.bound
                    if not changed:
                        continue
                    pending = list(scope.body)
                    while pending:
                        nested = pending.pop()
                        if isinstance(nested, ast.Global):
                            for name in changed & set(nested.names):
                                bindings.setdefault(name, []).append(nested)
                        elif not isinstance(nested, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                     ast.ClassDef, ast.Lambda)):
                            pending.extend(ast.iter_child_nodes(nested))
        aliases = {}
        for node in tree.body:
            for fact in import_facts(node):
                if fact.kind == 'import':
                    aliases[fact.python_binding] = (
                        fact.name if fact.asname else fact.python_binding)
                else:
                    prefix = (resolve_relative_module(
                        module,
                        os.path.basename(path).startswith('__init__.'),
                        fact.module, fact.level)
                        if fact.level else fact.module)
                    aliases[fact.python_binding] = prefix + '.' + fact.name
        module_bindings = {
            n.id for statement in tree.body
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for target in (statement.targets if isinstance(statement, ast.Assign) else [statement.target])
            for n in ast.walk(target) if isinstance(n, ast.Name)}
        evidence_cache = {}
        source_lines = None

        ## Cache source-span evidence and optionally recover exact source text.
        ## 缓存源码位置证据，并按需恢复精确源码文本。
        #
        #  @param node AST node with source positions.
        #  @param text Whether to include the source snippet.
        #  @return Source evidence dictionary.
        def evidence(node, text=False):
            nonlocal source_lines
            key = id(node), text
            if key not in evidence_cache:
                value = asdict(SourceSpan.from_ast(path, node))
                if text:
                    if source_lines is None:
                        source_lines = [line.encode('utf-8') for line in document.text.split('\n')]
                    first, last = node.lineno, node.end_lineno
                    start, end = node.col_offset, node.end_col_offset
                    snippet = (source_lines[first - 1][start:end] if first == last else
                               b'\n'.join([source_lines[first - 1][start:]] +
                                          source_lines[first:last - 1] +
                                          [source_lines[last - 1][:end]]))
                    value['source_text'] = snippet.decode('utf-8')
                evidence_cache[key] = value
            return evidence_cache[key]

        ## Collect nested definitions and their syntactic conditions.
        ## 收集嵌套定义及其语法条件。
        #
        #  @param body Statement sequence.
        #  @param prefix Enclosing qualified-name prefix.
        #  @param conditions Enclosing syntactic conditions.
        #  @return None
        def collect(body, prefix='', conditions=()):
            for node in body:
                if self._analysis_budget is not None:
                    self._analysis_budget.checkpoint()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = prefix + node.name
                    ref = FunctionRef(module, name, path, node.lineno)
                    if conditions:
                        definition_conditions.append((ref, conditions))
                    if not isinstance(node, ast.ClassDef):
                        definitions.append((ref, node))
                    else:
                        classes.append((ref, node))
                    collect(node.body, name + '.', conditions)
                else:
                    ## Collect lambdas without crossing another statement boundary.
                    ## 收集 lambda，不跨越其他语句边界。
                    #
                    #  @param item AST node to inspect.
                    #  @param root Whether this is the starting statement.
                    #  @return None
                    def collect_lambdas(item, root=False):
                        if isinstance(item, ast.Lambda):
                            name = prefix + '<lambda>@%s:%s' % (item.lineno, item.col_offset)
                            ref = FunctionRef(module, name, path, item.lineno)
                            definitions.append((ref, item))
                            if conditions:
                                definition_conditions.append((ref, conditions))
                            collect_lambdas(item.body)
                            return
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            return
                        if not root and isinstance(item, (ast.stmt, ast.ExceptHandler)):
                            return
                        for child in ast.iter_child_nodes(item):
                            collect_lambdas(child)
                    collect_lambdas(node, root=True)
                    for field, value in ast.iter_fields(node):
                        if not isinstance(value, list):
                            continue
                        for child in value:
                            condition = ({'test': evidence(node.test, text=True), 'branch': field == 'body'}
                                if isinstance(node, ast.If) and field in ('body', 'orelse') else
                                {'definition_context': type(node).__name__, 'region': field,
                                 'evidence': evidence(node)})
                            if isinstance(child, ast.stmt):
                                collect([child], prefix, conditions + (condition,))
                            elif isinstance(child, ast.ExceptHandler):
                                collect(child.body, prefix, conditions + ({'handler': evidence(child)},))
        collect(tree.body)
        return (tuple((name, tuple(nodes)) for name, nodes in bindings.items()),
                tuple(aliases.items()), frozenset(module_bindings),
                tuple(definitions), tuple(classes), tuple(definition_conditions))

