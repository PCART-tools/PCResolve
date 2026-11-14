## @package pcresolve.flow.proofs.namespaces.modules._export_lists
#  Finite export-list construction facts, not final module namespace bindings.
#  分析有限的导出列表构造事实，不推断最终模块命名空间绑定。

import ast
import copy
from dataclasses import dataclass
from pathlib import Path

from pcresolve.facts.import_facts import import_facts, resolve_relative_module
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.frontend.source_snapshot import FLOW_SOURCE, SourceStore
from pcresolve.facts.effect_facts import execution_nodes


## Signal that an export-list proof is incomplete or exceeds its limits.
## 表示导出列表证明不完整或超出分析限制。
class _OpenExports(ValueError):
    ## Preserve a machine-readable boundary reason and source location.
    ## 保存可供程序读取的边界原因和源码位置。
    #
    #  @param self Boundary exception instance.
    #  @param reason Stable boundary identifier.
    #  @param module Module being analyzed.
    #  @param node Optional AST node identifying the boundary.
    #  @return None.
    def __init__(self, reason, module='', node=None):
        super().__init__(reason)
        self.details = {'reason': reason, 'module': module,
                        'lineno': getattr(node, 'lineno', None)}


## Find source nodes that may execute while captured modules initialize.
## 查找已捕获模块初始化期间可能执行的源码节点。
#
#  @param documents Module-name to source-document mapping.
#  @param charge Callback charging each inspected execution node.
#  @return Set of AST nodes reachable during module initialization.
def _import_execution_nodes(documents, charge):
    functions, classes = {}, {}

    ## Index nested source definitions by qualified name for call resolution.
    ## 按限定名称索引嵌套源码定义以供调用解析。
    #
    #  @param module Module owning the source definitions.
    #  @param body Ordered statements to scan.
    #  @param prefix Enclosing qualified-name prefix.
    #  @return None; updates the enclosing definition indexes.
    def collect(module, body, prefix=''):
        for statement in body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = '.'.join(part for part in (prefix, statement.name) if part)
                functions.setdefault((module, name), []).append(statement)
                collect(module, statement.body, name)
            elif isinstance(statement, ast.ClassDef):
                name = '.'.join(part for part in (prefix, statement.name) if part)
                classes[(module, name)] = statement
                collect(module, statement.body, name)
            else:
                for child in ast.iter_child_nodes(statement):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        collect(module, [child], prefix)

    for module, document in documents.items():
        collect(module, document.tree.body)

    ## Collect import aliases visible to one execution root.
    ## 收集一个执行根节点中可见的导入别名。
    #
    #  @param module Module containing the execution root.
    #  @param root AST root whose executable statements are scanned.
    #  @return Alias mapping and resolved wildcard-import modules.
    def scope_imports(module, root):
        aliases, stars = {}, []
        package = documents[module].file_path.endswith('__init__.py')
        for node in execution_nodes(root):
            for fact in import_facts(node):
                if fact.kind == 'import':
                    target = fact.name if fact.asname else fact.python_binding
                    aliases.setdefault(fact.python_binding, set()).add(target)
                elif fact.wildcard:
                    stars.append(resolve_relative_module(
                        module, package, fact.module, fact.level))
                else:
                    base = resolve_relative_module(module, package, fact.module, fact.level)
                    aliases.setdefault(fact.python_binding, set()).add(base + '.' + fact.name)
        return aliases, stars

    ## Resolve possible source function or class targets for an expression.
    ## 为表达式解析可能的源码函数或类目标。
    #
    #  @param module Module containing the expression.
    #  @param root Scope root used for import bindings.
    #  @param expression Callable expression to resolve.
    #  @return Source definition pairs reachable from the expression.
    def targets(module, root, expression):
        aliases, stars = scope_imports(module, root)
        parts = []
        while isinstance(expression, ast.Attribute):
            parts.append(expression.attr)
            expression = expression.value
        if not isinstance(expression, ast.Name):
            return ()
        imported = aliases.get(expression.id)
        names = ({'.'.join((base, *reversed(parts))) for base in imported}
                 if imported else {'.'.join((module, expression.id, *reversed(parts)))})
        result = []
        for name in names:
            owner, _, qualname = name.rpartition('.')
            result.extend((target_module, node) for (target_module, target_name), nodes
                          in functions.items() if target_module == owner and target_name == qualname
                          for node in nodes)
            if not parts:
                result.extend((target_module, node) for (target_module, target_name), nodes
                              in functions.items() if target_module in stars
                              and target_name == expression.id
                              and not expression.id.startswith('_') for node in nodes)
            if name in classes:
                klass = classes[name]
                for method in ('__new__', '__init__', '__init_subclass__'):
                    result.extend((target_module, node)
                        for (target_module, target_name), nodes in functions.items()
                        if target_module == owner and target_name == qualname + '.' + method
                        for node in nodes)
        return tuple(result)

    pending = [(module, document.tree) for module, document in documents.items()]
    executed, visited = set(), set()
    while pending:
        module, root = pending.pop()
        if id(root) in visited:
            continue
        visited.add(id(root))
        for node in execution_nodes(root):
            charge()
            executed.add(node)
            if isinstance(node, ast.Call):
                pending.extend(targets(module, root, node.func))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    callee = decorator.func if isinstance(decorator, ast.Call) else decorator
                    pending.extend(targets(module, root, callee))
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        pending.extend(targets(module, root, base))
    return executed


## Store one bounded export value and whether it borrows an existing object.
## 保存一个有界导出值及其是否借用既有对象的信息。
@dataclass(frozen=True)
class _Values:
    kind: str
    names: tuple
    borrowed: bool = False


## Identify a direct child whose loading can bind an attribute of its parent.
## 识别加载后可能绑定到父模块属性的直接子模块。
#  This syntax fact is not evidence that the resulting module binding survives.
#  该语法事实不证明最终模块属性绑定能够保留。
#
#  @param owner Importing module name.
#  @param is_package Whether the owner source is a package initializer.
#  @param fact Parsed import fact.
#  @return Child module name, or None when the import is not an implicit child.
def implicit_submodule(owner, is_package, fact):
    if not is_package or fact.kind != 'from' or not fact.wildcard:
        return None
    target = resolve_relative_module(owner, True, fact.module, fact.level)
    return target if target.rpartition('.')[0] == owner else None


## Read literal export-list computations from explicit filesystem import roots.
## 从显式文件系统导入根读取字面量导出列表计算。
#  Each resolve() captures fresh source versions. It never imports target code.
#  每次 resolve() 都捕获新的源码版本，且不会导入目标代码。
class ExportListResolver:
    ## Configure source lookup and finite construction limits.
    ## 配置源码查找方式和有限构造预算。
    #
    #  @param import_roots Explicit source roots; ambiguous files are not selected.
    #  @param max_nodes Maximum charged source/evaluation nodes per resolve().
    #  @param max_modules Maximum source modules read for this construction.
    #  @param max_depth Maximum recursive imported-export depth.
    #  @param max_names Maximum number of names in any intermediate value.
    #  @param budget Optional cooperative analysis budget.
    #  @return None.
    def __init__(self, import_roots, max_nodes=1000000, max_modules=64,
                 max_depth=32, max_names=10000, budget=None):
        if any(type(value) is not int or value <= 0
               for value in (max_nodes, max_modules, max_depth, max_names)):
            raise ValueError('Export-list limits must be positive integers')
        self.roots = tuple(dict.fromkeys(Path(root).resolve() for root in import_roots))
        self.max_nodes, self.max_modules = max_nodes, max_modules
        self.max_depth, self.max_names, self.budget = max_depth, max_names, budget
        self.store = SourceStore()
        self.last_boundary = None

    ## Consume one source-analysis node from the export budget.
    ## 消耗一单位导出列表源码分析预算。
    #
    #  @param self Resolver state holding the current node budget.
    #  @return None; raises _OpenExports when the budget is exhausted.
    def charge(self):
        self.remaining -= 1
        if self.budget is not None:
            self.budget.checkpoint()
        if self.remaining < 0:
            raise _OpenExports('export_list_budget')

    ## Capture and cache one unique module source snapshot.
    ## 捕获并缓存唯一模块源码快照。
    #
    #  @param self Resolver with import roots and module limits.
    #  @param module Dotted module name to locate.
    #  @return Source document, or raises _OpenExports when lookup is ambiguous.
    def source(self, module):
        if module in self.documents:
            return self.documents[module]
        if len(self.documents) >= self.max_modules:
            raise _OpenExports('export_module_budget')
        if not module or not all(part.isidentifier() for part in module.split('.')):
            raise _OpenExports('invalid_export_module')
        paths = set()
        for root in self.roots:
            stem = root.joinpath(*module.split('.'))
            for candidate in (stem.with_suffix('.py'), stem / '__init__.py'):
                path = candidate.resolve()
                if path.is_file() and (path == root or root in path.parents):
                    paths.add(path)
        if len(paths) != 1:
            raise _OpenExports('export_source_missing_or_ambiguous')
        path = str(next(iter(paths)))
        document = self.store.snapshot([path], FLOW_SOURCE, self.budget).documents[path]
        if document.tree is None:
            raise _OpenExports('export_source_unavailable')
        self.documents[module] = document
        for _ in ast.walk(document.tree):
            self.charge()
        return document

    ## Resolve an imported expression while recording its binding evidence.
    ## 解析导入表达式并记录其绑定证据。
    #
    #  @param self Resolver with source documents and evidence collection.
    #  @param node Name or attribute expression to qualify.
    #  @param aliases Import alias to qualified-name mapping.
    #  @param bindings Module-level binding statements by local name.
    #  @param globals_written Names mutated through a global declaration.
    #  @param owner Module owning the expression.
    #  @return Qualified imported name, or raises _OpenExports if unproven.
    def qualify(self, node, aliases, bindings, globals_written, owner):
        parts = []
        while isinstance(node, ast.Attribute):
            if len(parts) >= self.max_depth:
                raise _OpenExports('export_attribute_depth')
            parts.append(node.attr)
            node = node.value
        if (not isinstance(node, ast.Name) or node.id in globals_written
                or len(bindings.get(node.id, ())) != 1 or node.id not in aliases):
            raise _OpenExports('export_import_binding_unproven')
        qualified = '.'.join([aliases[node.id], *reversed(parts)])
        statement = bindings[node.id][0]
        self.module_bindings.append({'module': owner, 'local_name': node.id,
            'target_module': qualified, 'status': 'required',
            'import_evidence': {'file_path': self.documents[owner].file_path,
                'lineno': statement.lineno, 'col_offset': statement.col_offset,
                'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset}})
        return qualified

    ## Validate and package a bounded set of export names.
    ## 校验并封装有界导出名称集合。
    #
    #  @param self Resolver with intermediate-name limits.
    #  @param kind Abstract value shape.
    #  @param values Candidate export names.
    #  @param borrowed Whether values alias a source object.
    #  @return Immutable bounded export value.
    def bounded(self, kind, values, borrowed=False):
        if len(values) > self.max_names or any(type(name) is not str or not name.isidentifier()
                                              for name in values):
            raise _OpenExports('export_names_unproven_or_exhausted')
        return _Values(kind, tuple(values), borrowed)

    ## Interpret the module's supported __all__ construction and imports.
    ## 解释模块受支持的 __all__ 构造及导入语句。
    #
    #  @param self Resolver with module, depth, and name budgets.
    #  @param module Module whose export values are requested.
    #  @return Export fact mapping, or raises _OpenExports when proof is open.
    def exports(self, module):
        if module in self.results:
            return self.results[module]
        if module in self.active or len(self.active) >= self.max_depth:
            raise _OpenExports('export_dependency_cycle_or_depth')
        self.active.add(module)
        document = self.source(module)
        aliases, bindings, globals_written, implicit = {}, {}, set(), {}
        for statement in document.tree.body:
            for name in statement_scope_facts([statement]).bound:
                bindings.setdefault(name, []).append(statement)
            for fact in import_facts(statement):
                if fact.kind == 'import':
                    aliases[fact.python_binding] = fact.name if fact.asname else fact.python_binding
                elif not fact.wildcard:
                    base = resolve_relative_module(module, document.file_path.endswith('__init__.py'),
                                                   fact.module, fact.level)
                    aliases[fact.python_binding] = base + '.' + fact.name
                else:
                    child = implicit_submodule(module, document.file_path.endswith('__init__.py'), fact)
                    if child is not None:
                        name = child.rpartition('.')[2]
                        implicit.setdefault(name, []).append((child, statement))
            for node in ast.walk(statement):
                if isinstance(node, ast.Global):
                    globals_written.update(node.names)
        for name, candidates in implicit.items():
            if name not in bindings:
                aliases[name] = candidates[0][0]
                bindings[name] = [statement for _, statement in candidates]
        if '__all__' in globals_written:
            raise _OpenExports('runtime_export_rebinding')
        current, allowed = None, set()

        ## Recognize a helper that extends one module export list safely.
        ## 识别可安全扩展模块导出列表的辅助函数。
        #
        #  @param function Candidate source helper function.
        #  @return True only for the supported finite extension pattern.
        def extension_helper(function):
            if (not isinstance(function, ast.FunctionDef) or function.decorator_list
                    or function.returns is not None or function.args.posonlyargs
                    or len(function.args.args) != 1 or function.args.defaults
                    or function.args.kwonlyargs or function.args.vararg or function.args.kwarg
                    or function.args.args[0].annotation is not None
                    or any(name in bindings or name in globals_written for name in ('set', 'getattr'))
                    or len(bindings.get(function.name, ())) != 1):
                return False
            body = function.body
            if len(body) != 3 or not all(isinstance(item, ast.Assign) for item in body[:2]):
                return False
            first, second, loop = body
            if (len(first.targets) != 1 or not isinstance(first.targets[0], ast.Name)
                    or len(second.targets) != 1 or not isinstance(second.targets[0], ast.Name)
                    or not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name)):
                return False
            names = {function.args.args[0].arg: 'module_arg', first.targets[0].id: 'existing',
                     second.targets[0].id: 'exports', loop.target.id: 'name'}
            if len(names) != 4:
                return False
            ## Normalize local names before comparing helper syntax trees.
            ## 比较辅助函数语法树前统一局部名称。
            class Rename(ast.NodeTransformer):
                ## Rename one AST identifier through the expected-shape mapping.
                ## 根据预期形状映射重命名一个 AST 标识符。
                #
                #  @param self Name-normalizing visitor.
                #  @param node AST name node to rewrite.
                #  @return Rewritten name node.
                def visit_Name(self, node):
                    node.id = names.get(node.id, node.id)
                    return node
            actual = Rename().visit(copy.deepcopy(ast.Module(body=body, type_ignores=[])))
            expected = ast.parse("""existing = set(__all__)
exports = getattr(module_arg, '__all__')
for name in exports:
    if name not in existing:
        __all__.append(name)
""")
            if ast.dump(actual, include_attributes=False) != ast.dump(expected, include_attributes=False):
                return False
            # Every use must be a direct top-level call; a leaked helper could
            # otherwise mutate the export list after construction.
            parents = {child: node for node in ast.walk(document.tree)
                       for child in ast.iter_child_nodes(node)}
            for node in ast.walk(document.tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == function.name:
                    call = parents.get(node)
                    statement = parents.get(call)
                    if not (isinstance(call, ast.Call) and call.func is node
                            and isinstance(statement, ast.Expr) and statement in document.tree.body):
                        return False
            return True

        helpers = {statement.name: statement for statement in document.tree.body
                   if extension_helper(statement)}

        ## Evaluate one export expression without importing its referenced code.
        ## 计算一个导出表达式，但不导入其引用代码。
        #
        #  @param node Export expression AST node.
        #  @return Bounded _Values result, or raises _OpenExports.
        def evaluate(node):
            self.charge()
            if isinstance(node, (ast.List, ast.Tuple)) and all(
                    isinstance(item, ast.Constant) and type(item.value) is str for item in node.elts):
                return self.bounded('list' if isinstance(node, ast.List) else 'tuple',
                                    [item.value for item in node.elts])
            if isinstance(node, ast.Name) and node.id == '__all__' and current is not None:
                return current
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left, right = evaluate(node.left), evaluate(node.right)
                if left.kind != right.kind:
                    raise _OpenExports('export_sequence_type_mismatch')
                return self.bounded(left.kind, left.names + right.names)
            if isinstance(node, ast.Attribute) and node.attr == '__all__':
                imported = self.qualify(node.value, aliases, bindings, globals_written, module)
                value = self.exports(imported)
                return _Values(value.kind, value.names, value.kind == 'list')
            raise _OpenExports('export_value_unmodeled')

        for statement in document.tree.body:
            self.charge()
            selected = False
            if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == '__all__'):
                current, selected = evaluate(statement.value), True
            elif (isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name)
                  and statement.target.id == '__all__' and isinstance(statement.op, ast.Add)):
                if current is None or current.borrowed:
                    raise _OpenExports('export_mutable_alias_or_missing_input')
                added = evaluate(statement.value)
                if current.kind == 'tuple' and added.kind != 'tuple':
                    raise _OpenExports('export_sequence_type_mismatch')
                current, selected = self.bounded(current.kind, current.names + added.names), True
            elif (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                  and isinstance(statement.value.func, ast.Name)
                  and statement.value.func.id in helpers):
                call = statement.value
                if (current is None or current.kind != 'list' or current.borrowed
                        or len(call.args) != 1 or call.keywords
                        or helpers[call.func.id].lineno >= statement.lineno):
                    raise _OpenExports('export_helper_input_unproven', module, statement)
                for prior in document.tree.body:
                    if prior is statement:
                        break
                    for fact in import_facts(prior):
                        if fact.wildcard:
                            source = resolve_relative_module(module,
                                document.file_path.endswith('__init__.py'), fact.module, fact.level)
                            if {'set', 'getattr', '__all__', call.func.id} & set(self.exports(source).names):
                                raise _OpenExports('export_helper_binding_unproven', module, prior)
                imported = self.qualify(call.args[0], aliases, bindings, globals_written, module)
                incoming = self.exports(imported)
                old = set(current.names)
                current = self.bounded('list', current.names + tuple(
                    name for name in incoming.names if name not in old))
                allowed.update(ast.walk(helpers[call.func.id]))
                selected = True
            elif (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                  and isinstance(statement.value.func, ast.Attribute)
                  and isinstance(statement.value.func.value, ast.Name)
                  and statement.value.func.value.id == '__all__'):
                call = statement.value
                if (current is None or current.kind != 'list' or current.borrowed
                        or call.keywords or len(call.args) != 1):
                    raise _OpenExports('export_list_method_unproven')
                name, argument = call.func.attr, call.args[0]
                if name == 'extend':
                    current = self.bounded('list', current.names + evaluate(argument).names)
                elif name in ('append', 'remove') and isinstance(argument, ast.Constant) and type(
                        argument.value) is str:
                    values = list(current.names)
                    if name == 'append':
                        values.append(argument.value)
                    elif argument.value in values:
                        values.remove(argument.value)
                    else:
                        raise _OpenExports('export_remove_missing_name')
                    current = self.bounded('list', values)
                else:
                    raise _OpenExports('export_list_method_unmodeled')
                selected = True
            if selected:
                allowed.update(ast.walk(statement))
                self.evidence.append({'module': module, 'file_path': document.file_path,
                    'lineno': statement.lineno, 'col_offset': statement.col_offset,
                    'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset})
        if current is None:
            raise _OpenExports('export_declaration_missing')
        for node in ast.walk(document.tree):
            self.charge()
            if node in allowed:
                continue
            imported_exports = False
            if isinstance(node, ast.Attribute) and node.attr == '__all__':
                head = node.value
                while isinstance(head, ast.Attribute):
                    head = head.value
                imported_exports = (not isinstance(node.ctx, ast.Load)
                                    or isinstance(head, ast.Name) and head.id in aliases)
            if (isinstance(node, ast.Name) and node.id == '__all__'
                    or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == '__all__'
                    or imported_exports):
                raise _OpenExports('export_use_outside_construction', module, node)
        self.active.remove(module)
        self.results[module] = current
        return current

    ## Prove a wildcard import binds a fresh child module on its parent.
    ## 证明通配符导入会在父模块上绑定新加载的子模块。
    #
    #  @param self Resolver with captured package sources and import facts.
    #  @param owner Package module receiving the child binding.
    #  @param statement Import statement that may create the binding.
    #  @param imported Parsed wildcard import fact.
    #  @return Child module name, or raises _OpenExports when shadowing is possible.
    def implicit_input(self, owner, statement, imported):
        document = self.documents[owner]
        target = implicit_submodule(owner, document.file_path.endswith('__init__.py'), imported)
        if target is None:
            raise _OpenExports('export_implicit_parent_binding_unproven', owner, statement)
        bound = statement_scope_facts(document.tree.body).bound
        children = {implicit_submodule(owner, True, fact)
                    for item in document.tree.body for fact in import_facts(item)} - {None}
        children = {child for child in children if child.rpartition('.')[2] not in bound}
        names = {child.rpartition('.')[2] for child in children}
        import_state = {'__path__', '__spec__', '__loader__', '__package__', '__name__',
                        '__class__', '__dict__', '__getattribute__', '__getattr__'}
        capabilities = {'__path__', '__spec__', '__loader__', '__dict__'}
        # Loading a child only creates this attribute on a fresh load. Cached
        # imports cannot repair a deleted/replaced parent attribute. Reject all
        # visible competing bindings, including names injected by other stars.
        for item in document.tree.body:
            self.charge()
            if (names | import_state) & statement_scope_facts([item]).bound:
                raise _OpenExports('export_implicit_parent_name_may_be_rebound', owner, item)
            for fact in import_facts(item):
                if fact.wildcard:
                    base = resolve_relative_module(owner, True, fact.module, fact.level)
                    if (names | import_state) & set(self.exports(base).names):
                        raise _OpenExports('export_implicit_parent_star_may_shadow_module', owner, item)
        # Audit the complete captured construction input set once per parent.
        # A child may directly modify or expose its parent during its import.
        key = owner, tuple(sorted(self.documents))
        if key not in self.implicit_guards:
            executed = _import_execution_nodes(self.documents, self.charge)
            for module, captured in list(self.documents.items()):
                aliases, parents = {}, {}
                for node in ast.walk(captured.tree):
                    self.charge()
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
                    for fact in import_facts(node):
                        if fact.kind == 'import':
                            canonical = fact.name if fact.asname else fact.python_binding
                        elif not fact.wildcard:
                            prefix = resolve_relative_module(module,
                                captured.file_path.endswith('__init__.py'), fact.module, fact.level)
                            canonical = prefix + '.' + fact.name
                        else:
                            continue
                        aliases.setdefault(fact.python_binding, set()).add(canonical)

                ## Resolve imported names referenced by executable namespace code.
                ## 解析可执行命名空间代码所引用的导入名称。
                #
                #  @param node Name or attribute expression to resolve.
                #  @return Canonical imported paths referenced by the expression.
                def references(node):
                    parts = []
                    while isinstance(node, ast.Attribute):
                        parts.append(node.attr)
                        node = node.value
                    return ({'.'.join([head, *reversed(parts)])
                             for head in aliases.get(node.id, ())}
                            if isinstance(node, ast.Name) else set())

                for node in ast.walk(captured.tree):
                    self.charge()
                    if node not in executed:
                        continue
                    if (module == owner and isinstance(node, ast.Global)
                            and (names | import_state) & set(node.names)
                            or isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                            and node.id in ('exec', 'eval', '__import__', '__builtins__')
                            or module == owner and isinstance(node, ast.Name)
                            and isinstance(node.ctx, ast.Load)
                            and node.id in capabilities | {'globals', 'locals', 'vars'}
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and references(node) & {'sys.modules', 'importlib.import_module',
                                'builtins.exec', 'builtins.eval', 'builtins.__import__'}
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and references(node) & {owner + '.' + name for name in capabilities}):
                        raise _OpenExports('export_implicit_parent_namespace_capability', module, node)
                    if (isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                            and owner in references(node.value)):
                        raise _OpenExports('export_implicit_parent_attribute_write', module, node)
                    if (isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load)
                            and owner in references(node)):
                        parent = parents.get(node)
                        if not isinstance(parent, ast.Attribute) or parent.value is not node:
                            raise _OpenExports('export_implicit_parent_namespace_escape', module, node)
            self.implicit_guards.add(key)
        return target

    ## Validate that an export import resolves to its expected module object.
    ## 校验导出导入是否解析为预期的模块对象。
    #
    #  @param self Resolver with captured source snapshots and budgets.
    #  @param requirement Recorded import-binding requirement.
    #  @return Source-bound module input proof, or raises _OpenExports.
    def module_input(self, requirement):
        owner = requirement['module']
        document = self.documents[owner]
        evidence = requirement['import_evidence']
        matching = [node for node in document.tree.body
            if all(getattr(node, field, None) == evidence[field]
                   for field in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'))]
        if len(matching) != 1:
            raise _OpenExports('export_import_site_unproven', owner)
        statement = matching[0]
        facts = [fact for fact in import_facts(statement)
                 if fact.python_binding == requirement['local_name']
                 or (implicit_submodule(owner, document.file_path.endswith('__init__.py'), fact)
                     or '').rpartition('.')[2] == requirement['local_name']]
        if len(facts) != 1:
            raise _OpenExports('export_import_name_unproven', owner, statement)
        imported = facts[0]
        target = requirement['target_module']
        if imported.kind == 'import' and '.' not in imported.name:
            expected = imported.name
        elif imported.kind == 'from' and imported.wildcard:
            expected = self.implicit_input(owner, statement, imported)
        elif imported.kind == 'from' and not imported.wildcard:
            base = resolve_relative_module(owner, document.file_path.endswith('__init__.py'),
                                           imported.module, imported.level)
            if base != owner or not document.file_path.endswith('__init__.py'):
                raise _OpenExports('export_parent_namespace_unproven', owner, statement)
            # A from-package import consults existing attributes before loading
            # a submodule. A matching filename alone cannot bypass that lookup.
            aliases = {}
            for root in document.tree.body:
                for item in ast.walk(root):
                    for fact in import_facts(item):
                        if fact.kind == 'import':
                            canonical = fact.name if fact.asname else fact.python_binding
                        elif not fact.wildcard:
                            prefix = resolve_relative_module(owner, True, fact.module, fact.level)
                            canonical = prefix + '.' + fact.name
                        else:
                            continue
                        aliases.setdefault(fact.python_binding, set()).add(canonical)

            ## Resolve canonical imports used by the package namespace prefix.
            ## 解析包命名空间前缀所使用的规范导入名称。
            #
            #  @param node Name or attribute expression.
            #  @return Canonical imported paths for the expression.
            def namespace_names(node):
                parts = []
                while isinstance(node, ast.Attribute):
                    parts.append(node.attr)
                    node = node.value
                if not isinstance(node, ast.Name):
                    return set()
                return {'.'.join([head, *reversed(parts)]) for head in aliases.get(node.id, ())}

            for prior in document.tree.body:
                self.charge()
                if prior is statement:
                    break
                bound = statement_scope_facts([prior]).bound
                if imported.name in bound or '__getattr__' in bound:
                    raise _OpenExports('export_parent_attribute_may_shadow_module', owner, prior)
                for node in ast.walk(prior):
                    self.charge()
                    if (isinstance(node, ast.Global)
                            and {imported.name, '__getattr__'} & set(node.names)
                            or isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                            and node.id in ('exec', 'eval', 'globals', 'locals', 'vars', '__import__')
                            or isinstance(node, (ast.Name, ast.Attribute))
                            and isinstance(node.ctx, ast.Load) and owner in namespace_names(node)
                            or isinstance(node, ast.Call)
                            and 'importlib.import_module' in namespace_names(node.func)
                            or isinstance(node, ast.Attribute) and node.attr == 'modules'
                            and 'sys' in namespace_names(node.value)):
                        raise _OpenExports('export_parent_namespace_write_or_escape', owner, node)
                for fact in import_facts(prior):
                    if not fact.wildcard:
                        continue
                    module = resolve_relative_module(owner, True, fact.module, fact.level)
                    exported = self.exports(module)
                    if imported.name in exported.names or '__getattr__' in exported.names:
                        raise _OpenExports('export_parent_star_may_shadow_module', owner, prior)
            expected = base + '.' + imported.name
        else:
            raise _OpenExports('export_module_import_protocol_unmodeled', owner, statement)
        if target != expected:
            raise _OpenExports('export_module_attribute_chain_unproven', owner, statement)
        target_source = self.source(target)
        sys_names = {fact.python_binding for node in ast.walk(target_source.tree)
                     for fact in import_facts(node)
                     if fact.kind == 'import' and fact.name == 'sys'}

        ## Match an expression that names the standard sys module.
        ## 匹配指向标准 sys 模块的表达式。
        #
        #  @param node AST expression to inspect.
        #  @return True when node refers to the imported or builtin sys module.
        def system_module(node):
            return (isinstance(node, ast.Name) and node.id in sys_names
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == '__import__' and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'sys')

        ## Match access to sys.modules through supported syntax forms.
        ## 匹配受支持语法形式中的 sys.modules 访问。
        #
        #  @param node AST expression to inspect.
        #  @return True when node denotes the module registry.
        def module_table(node):
            return (isinstance(node, ast.Attribute) and node.attr == 'modules'
                    and system_module(node.value)
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'getattr' and len(node.args) >= 2
                    and system_module(node.args[0]) and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == 'modules')

        for node in ast.walk(target_source.tree):
            self.charge()
            if (isinstance(node, ast.Attribute) and node.attr == '__class__'
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    or isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and module_table(node)
                    or isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del))
                    and module_table(node.value)
                    or isinstance(node, (ast.Assign, ast.AnnAssign)) and module_table(node.value)
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and module_table(node.func.value) and node.func.attr in (
                        'update', 'clear', 'pop', 'setdefault', '__setitem__', '__delitem__')
                    or isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
                    and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
                    in ('setattr', 'delattr', '__setattr__', '__delattr__')
                    and any(isinstance(arg, ast.Constant) and arg.value == '__class__'
                            for arg in node.args)):
                raise _OpenExports('export_imported_module_layout_or_registry_write', target, node)
        proof = {'kind': 'source_export_module_input', 'status': 'source_bound',
            'owner_module': owner, 'local_name': requirement['local_name'],
            'target_module': target, 'target_file_path': target_source.file_path,
            'import_evidence': dict(evidence),
            'completion': 'normal_import_return_only', 'runtime_module_confirmed': False,
            'assumptions': ['standard_source_import_protocol', 'standard_module_attribute_lookup',
                'no_unmodeled_indirect_module_mutation', 'no_external_monkeypatch_or_import_hook']}
        if imported.wildcard:
            proof['binding_protocol'] = 'implicit_parent_submodule_attribute'
        return proof

    ## Capture one finite export-list construction and its supporting source versions.
    ## 捕获有限导出列表构造及其依赖的源码版本。
    #
    #  @param module Qualified source module name.
    #  @param validate_module_inputs Require independently checked module import inputs.
    #  @return Construction fact or None; final callable namespace is never proved here.
    def resolve(self, module, validate_module_inputs=False):
        self.remaining = self.max_nodes
        self.documents, self.results, self.active, self.evidence = {}, {}, set(), []
        self.module_bindings = []
        self.implicit_guards = set()
        self.last_boundary = None
        self.last_evidence = None
        try:
            value = self.exports(module)
            module_inputs = []
            if validate_module_inputs:
                index = 0
                while index < len(self.module_bindings):
                    self.charge()
                    module_inputs.append(self.module_input(self.module_bindings[index]))
                    index += 1
        except _OpenExports as error:
            self.last_boundary = str(error)
            self.last_evidence = error.details
            return None
        assumptions = {'source_snapshot_bindings_hold', 'native_list_tuple_export_construction',
            'imported_export_list_module_bindings_hold', 'standard_module_attribute_lookup',
            'no_unmodeled_indirect_export_list_mutation', 'no_external_monkeypatch_or_import_hook'}
        for proof in module_inputs:
            assumptions.update(proof['assumptions'])
        return {'kind': 'source_export_list_construction', 'module': module,
            'status': 'construction_proven', 'scope': 'finite_source_export_list_construction',
            'completion': 'normal_construction_only', 'container_kind': value.kind,
            'values': list(value.names), 'borrowed_list': value.borrowed,
            'namespace_binding_proven': False, 'runtime_exports_confirmed': False,
            'required_module_bindings': list(self.module_bindings),
            'module_inputs_proven': bool(validate_module_inputs),
            'module_input_bindings': module_inputs,
            'construction_evidence': list(self.evidence),
            'source_hashes': {document.file_path: document.sha256
                              for document in self.documents.values()},
            'assumptions': sorted(assumptions)}
