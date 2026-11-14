## @package pcresolve.flow.proofs.protocols._source_protocols
#  Source-proven protocol helpers, independent of library/API spellings.
#  提供与库或 API 名称无关、由源码证据支持的协议分析辅助逻辑。

import ast

from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.namespaces.source._source_bindings import SourceBindingResolver
from pcresolve.flow.proofs.namespaces.modules._export_lists import implicit_submodule
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.import_facts import import_facts, resolve_relative_module


## Read finite source helper protocols from explicitly supplied dependency roots.
## 从显式提供的依赖根目录读取有限源码辅助协议。
class SourceProtocolResolver:
    ## Configure independent dependency lookup; analyzed code is never executed.
    ## 配置独立依赖查找；分析过程中不会执行目标代码。
    #
    #  @param import_roots Explicit dependency roots, separate from primary sources.
    #  @param budget Optional shared cooperative analysis budget.
    #  @param analyzer_factory Injected adapter factory; absence supplies no execution proof.
    #  @param ambient_documents Explicit (module, captured source document) pairs to audit.
    #  @param max_ambient_modules Separate finite limit on the supplied primary context.
    #  @param limits Finite SourceBindingResolver construction limits.
    #  @return None; resolver state and finite analysis limits are initialized.
    def __init__(self, import_roots, budget=None, analyzer_factory=None,
                 ambient_documents=(), max_ambient_modules=256, **limits):
        if type(max_ambient_modules) is not int or max_ambient_modules < 0:
            raise ValueError('Source protocol ambient module limit must be nonnegative')
        self.max_ambient_modules = max_ambient_modules
        self.roots, self.budget, self.limits = tuple(import_roots), budget, limits
        self.ambient_documents = tuple(ambient_documents)
        if analyzer_factory is not None and not callable(analyzer_factory):
            raise ValueError('Source protocol analysis provider must be callable')
        self.analyzer_factory = analyzer_factory
        self.last_boundary = None

    ## Resolve and capture one helper definition under the source binding rules.
    ## 按源码绑定规则解析并捕获一个辅助函数定义。
    #
    #  @param module Module exposing the requested helper.
    #  @param name Public helper name to resolve.
    #  @return Binding fact and matching function AST node.
    def _bind(self, module, name):
        options = {**self.limits, 'max_nodes': max(1, self.remaining)}
        reader = SourceBindingResolver(self.roots, budget=self.budget, **options)
        fact = reader.resolve(module, name)
        self.remaining -= options['max_nodes'] - reader.remaining

        # Merge captured documents only when repeated paths retain the same snapshot hash.
        # 仅当重复路径的快照哈希一致时，才合并捕获的文档。
        for captured_module, document in reader.documents.items():
            prior = self.documents.get(document.file_path)
            if prior is not None and prior.sha256 != document.sha256:
                raise ValueError('source_protocol_snapshot_changed')
            self.documents[document.file_path] = document
            self.module_names.setdefault(document.file_path, set()).add(captured_module)
            if len(self.documents) > self.limits.get('max_modules', 64):
                raise ValueError('source_protocol_module_budget')
        if fact is None:
            raise ValueError(reader.last_boundary)
        self.references.append(fact)
        ref = fact['target']
        candidates = [node for node in ast.walk(self.documents[ref['file_path']].tree)
                      if isinstance(node, ast.FunctionDef) and node.name == ref['qualname']
                      and node.lineno == ref['lineno']]
        if len(candidates) != 1:
            raise ValueError('source_protocol_function_unavailable')
        return fact, candidates[0]

    ## Audit callable aliases, rebinding, and escapes in captured source documents.
    ## 审计捕获源码文档中的可调用对象别名、重绑定和逃逸。
    #
    #  @return None; raises ValueError when a callable boundary is unproven.
    def _function_namespace(self):
        qualified = set()
        for reference in self.references:
            target = reference['target']
            qualified.add(target['module'] + '.' + target['qualname'])
            qualified.add(reference['requested']['module'] + '.' + reference['requested']['name'])
            for path in reference['paths']:
                qualified.update(item['module'] + '.' + item['binding_name']
                                 for item in path['imports'])
        protected = {'.'.join(name.split('.')[:index]) for name in qualified
                     for index in range(1, len(name.split('.')) + 1)}

        ## Charge one syntax visit against the finite resolver budget.
        ## 将一次语法节点访问计入有限解析预算。
        #
        #  @return None; raises ValueError when the shared budget is exhausted.
        def charge():
            self.remaining -= 1
            if self.budget is not None:
                self.budget.checkpoint()
            if self.remaining < 0:
                raise ValueError('source_protocol_namespace_budget')

        for document in self.documents.values():
            imports, assignments, references, parents, aliases = [], [], [], {}, {}
            # Charge the complete inventory once. Fixed-point alias work and
            # exposure checks visit only syntax that can carry a callable.
            for node in ast.walk(document.tree):
                charge()
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(node)
                if isinstance(node, ast.Assign):
                    assignments.append(node)
                if isinstance(node, (ast.Name, ast.Attribute)):
                    references.append(node)
                for child in ast.iter_child_nodes(node):
                    parents[child] = node

            # Build import aliases before propagating local name-to-name assignments.
            # 先建立导入别名，再传播本地名称到名称的赋值关系。
            modules = self.module_names[document.file_path]
            for node in imports:
                for fact in import_facts(node):
                    for module in modules:
                        child = implicit_submodule(module, document.file_path.endswith('__init__.py'), fact)
                        if child is not None:
                            aliases.setdefault(child.rpartition('.')[2], set()).add(child)
                        value = (fact.name if fact.kind == 'import' and fact.asname else
                            fact.python_binding if fact.kind == 'import' else
                            resolve_relative_module(module, document.file_path.endswith('__init__.py'),
                                fact.module, fact.level) + '.' + fact.name)
                        aliases.setdefault(fact.python_binding, set()).add(value)
            for module in modules:
                for name in qualified:
                    if name.rpartition('.')[0] == module:
                        aliases.setdefault(name.rpartition('.')[2], set()).add(name)

            ## Expand a name or attribute through the currently known aliases.
            ## 根据当前已知别名展开名称或属性。
            #
            #  @param node Expression to qualify through captured imports.
            #  @return Set of possible qualified spellings.
            def names(node):
                parts = []
                while isinstance(node, ast.Attribute):
                    parts.append(node.attr)
                    node = node.value
                return ({'.'.join([head, *reversed(parts)]) for head in aliases.get(node.id, ())}
                        if isinstance(node, ast.Name) else set())

            for _ in range(64):
                changed = False
                for node in assignments:
                    charge()
                    if not (names(node.value) & protected):
                        continue
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            old = aliases.setdefault(target.id, set())
                            extra = names(node.value) - old
                            old.update(extra)
                            changed = changed or bool(extra)
                if not changed:
                    break
            else:
                raise ValueError('source_protocol_alias_depth')

            # Reject every callable use that could rebind, expose, or mutate the proven function.
            # 拒绝所有可能重绑定、暴露或变更已证明函数对象的用法。
            for node in references:
                matched = names(node) & protected
                if not matched:
                    continue
                charge()
                parent = parents.get(node)
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    # Import/function-name stores do not have ast.Name nodes.
                    if isinstance(parent, ast.Assign) and node in parent.targets:
                        continue
                    raise ValueError('source_protocol_function_rebinding')
                if isinstance(parent, ast.Call) and parent.func is node:
                    if not matched.issubset(qualified):
                        raise ValueError('source_protocol_module_callable_escape')
                    continue
                if isinstance(parent, ast.Attribute) and parent.value is node:
                    if (isinstance(parent.ctx, ast.Load) and parent.attr not in (
                            '__code__', '__defaults__', '__kwdefaults__', '__globals__',
                            '__closure__', '__dict__', '__getattribute__')):
                        continue
                    raise ValueError('source_protocol_function_slot_write_or_escape')
                if (isinstance(parent, ast.Assign) and parent.value is node
                        and all(isinstance(target, ast.Name) for target in parent.targets)):
                    continue
                raise ValueError('source_protocol_function_object_escape')

    ## Prove a try-iter/except-TypeError Boolean predicate for native class inputs.
    ## 为原生类输入证明 try-iter/except-TypeError 布尔谓词。
    #
    #  @param module Public source module containing the helper binding.
    #  @param name Public source helper name; matching is structural, never by name.
    #  @return Conditional protocol fact or None; input type remains a consumer obligation.
    def iterability(self, module, name):
        self.documents, self.references, self.module_names = {}, [], {}
        self.remaining = self.limits.get('max_nodes', 1000000)
        self.last_boundary = None
        try:

            # Match the helper's exact signature and control-flow shape before analyzing dependencies.
            # 分析依赖前，先匹配辅助函数的精确签名和控制流结构。
            binding, function = self._bind(module, name)
            args = function.args
            parameters = args.posonlyargs + args.args
            if (len(parameters) != 1 or args.vararg or args.kwarg or args.kwonlyargs
                    or args.defaults or parameters[0].annotation is not None
                    or function.returns is not None):
                raise ValueError('source_protocol_signature')
            body = [node for node in function.body if not (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and type(node.value.value) is str)]
            if not (len(body) == 2 and isinstance(body[0], ast.Try)
                    and isinstance(body[1], ast.Return)
                    and isinstance(body[1].value, ast.Constant)
                    and type(body[1].value.value) is bool):
                raise ValueError('source_protocol_body')
            attempt = body[0]
            if not (len(attempt.body) == 1 and isinstance(attempt.body[0], ast.Expr)
                    and isinstance(attempt.body[0].value, ast.Call)
                    and len(attempt.handlers) == 1 and not attempt.orelse and not attempt.finalbody):
                raise ValueError('source_protocol_iteration')
            call, handler = attempt.body[0].value, attempt.handlers[0]
            if not (isinstance(call.func, ast.Name) and call.func.id == 'iter'
                    and len(call.args) == 1 and not call.keywords
                    and isinstance(call.args[0], ast.Name) and call.args[0].id == parameters[0].arg
                    and isinstance(handler.type, ast.Name) and handler.type.id == 'TypeError'
                    and handler.name is None and len(handler.body) == 1
                    and isinstance(handler.body[0], ast.Return)
                    and isinstance(handler.body[0].value, ast.Constant)
                    and type(handler.body[0].value.value) is bool):
                raise ValueError('source_protocol_handler')
            for expression in function.decorator_list:
                factory = expression.func if isinstance(expression, ast.Call) else expression
                if not isinstance(factory, ast.Name):
                    raise ValueError('source_protocol_decorator_lookup')
                self._bind(binding['target']['module'], factory.id)
            if len(self.ambient_documents) > self.max_ambient_modules:
                raise ValueError('source_protocol_ambient_module_budget')
            for ambient_module, document in self.ambient_documents:
                if document.tree is None or not document.sha256:
                    raise ValueError('source_protocol_ambient_source_unavailable')
                prior = self.documents.get(document.file_path)
                if prior is not None and prior.sha256 != document.sha256:
                    raise ValueError('source_protocol_snapshot_changed')
                self.documents[document.file_path] = document
                self.module_names.setdefault(document.file_path, set()).add(ambient_module)

            # Ensure all captured callable paths are closed before constructing an analyzer.
            # 构造分析器前，确保所有捕获的可调用路径均已封闭。
            self._function_namespace()
            if self.analyzer_factory is None:
                raise ValueError('source_protocol_analysis_provider_unavailable')
            analyzer = self.analyzer_factory(source_files=self.documents, import_roots=self.roots)
            analyzer._analysis_budget = self.budget
            analyzer._index()
            if any(analyzer.hashes.get(path) != document.sha256
                   for path, document in self.documents.items()):
                raise ValueError('source_protocol_snapshot_changed')
            ref = analyzer._definition_index.find(binding['target']['module'],
                                                   binding['target']['qualname'])
            if len(ref) != 1 or ref[0][1].lineno != binding['target']['lineno']:
                raise ValueError('source_protocol_function_selection')
            target = ref[0]
            for builtin in ('iter', 'TypeError'):
                if analyzer._builtin_name_status(target[0], target[1], builtin) != 'confirmed_builtin':
                    raise ValueError('source_protocol_shadowed_builtin')
            if not _stable_builtin_namespace(analyzer, target[0], ('iter', 'TypeError'))[0]:
                raise ValueError('source_protocol_builtin_namespace')
            decorations = analyzer._binding_decoration_facts(target)
            if any(fact['identity_status'] != 'preserved' or fact['body_binding_status'] != 'preserved'
                   or fact['boundaries'] for fact in decorations):
                raise ValueError('source_protocol_decorated_body')
        except (ValueError, _ClassEffectLimit) as error:
            self.last_boundary = str(error) or 'source_protocol_budget'
            return None
        assumptions = {'source_snapshot_bindings_hold', 'standard_builtin_namespace_preserved',
            'builtin_type_iteration_raises_typeerror', 'source_function_execution_binding_preserved',
            'no_external_frame_or_gc_observation', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_function_mutation', 'no_unmodeled_indirect_module_mutation'}
        for premise in self.references + decorations:
            assumptions.update(premise['assumptions'])
        return {'kind': 'source_native_type_iterability_predicate',
            'status': 'requires_native_type_input', 'basis': 'source_snapshot',
            'precondition': {'argument': {'position': 0}, 'exact_metaclass': 'type'},
            'result': handler.body[0].value.value, 'effects': 'none_if_precondition',
            'completion': 'normal_return_if_precondition_and_lookup_succeeds',
            'runtime_input_confirmed': False, 'source_binding': binding,
            'function_evidence': {'file_path': binding['target']['file_path'],
                **{field: getattr(function, field) for field in
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')}},
            'iteration_evidence': {'file_path': binding['target']['file_path'],
                **{field: getattr(call, field) for field in
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')}},
            'handler_evidence': {'file_path': binding['target']['file_path'],
                **{field: getattr(handler.body[0], field) for field in
                   ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')}},
            'primitive_bindings': {'iter': 'confirmed_builtin', 'TypeError': 'confirmed_builtin'},
            'decorator_effects': decorations,
            'source_hashes': {path: document.sha256 for path, document in self.documents.items()},
            'assumptions': sorted(assumptions)}
