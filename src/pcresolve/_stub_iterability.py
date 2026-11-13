## @package pcresolve._stub_iterability
#  Conservative iterable-return facts from bounded installed type stubs.
#  根据有界的已安装类型存根保守推断可迭代返回事实。

"""Conservative iterable-return facts from bounded installed type stubs."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


## Resolve iterable return annotations within explicit file and node budgets.
## 在显式文件和节点预算内解析可迭代返回注解。
class _Resolver:
    ## Initialize source roots, budgets and per-query document caches.
    ## 初始化源码根目录、预算及本次查询的文档缓存。
    #
    #  @param roots Ordered import roots.
    #  @param max_files Maximum source files to inspect.
    #  @param max_nodes Maximum AST nodes across inspected files.
    #  @return None
    def __init__(self, roots, *, max_files=256, max_nodes=100000):
        self.roots = tuple(Path(root).resolve() for root in roots)
        self.max_files = max_files
        self.remaining = max_nodes
        self.documents = {}
        self.hashes = {}

    ## Locate a module source or stub inside an allowed root.
    ## 在允许的根目录中定位模块源码或存根。
    #
    #  @param module Dotted module name.
    #  @return Resolved path or None when unavailable.
    def _path(self, module):
        parts = module.split('.') if module else []
        if not parts or any(not part.isidentifier() for part in parts):
            return None
        for root in self.roots:
            base = root.joinpath(*parts)
            for path in (base.with_suffix('.pyi'), base.with_suffix('.py'),
                         base / '__init__.pyi', base / '__init__.py'):
                try:
                    resolved = path.resolve()
                    resolved.relative_to(root)
                except (OSError, ValueError):
                    continue
                if resolved.is_file():
                    return resolved
        return None

    ## Read, parse and cache a module within the source budgets.
    ## 在源码预算内读取、解析并缓存模块。
    #
    #  @param module Dotted module name.
    #  @return Tree and path pair, or None on failure or exhaustion.
    def _document(self, module):
        path = self._path(module)
        if path is None:
            return None
        key = str(path)
        if key in self.documents:
            return self.documents[key]
        if len(self.documents) >= self.max_files:
            return None
        try:
            text = path.read_text(encoding='utf-8-sig')
            tree = ast.parse(text, filename=key)
        except (OSError, UnicodeError, SyntaxError):
            return None

        # Do not publish a document whose nodes exceed the remaining budget.
        # 节点数超过剩余预算时不发布该文档。
        self.remaining -= sum(1 for _ in ast.walk(tree))
        if self.remaining < 0:
            return None
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        self.documents[key] = (tree, path)
        self.hashes[key] = digest
        return tree, path

    ## Collect explicit module import aliases for annotation resolution.
    ## 收集模块中的显式导入别名，供解析注解使用。
    #
    #  @param module Dotted module name.
    #  @param tree Parsed module AST.
    #  @param path Module source path.
    #  @return Mapping of local names to module and optional symbol.
    def _module_imports(self, module, tree, path):
        aliases = {}
        is_package = path.name.startswith('__init__.')
        package = module if is_package else module.rpartition('.')[0]
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split('.')[0]
                    target = alias.name if alias.asname else alias.name.split('.')[0]
                    aliases[local] = (target, None)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ''
                if node.level:
                    parts = package.split('.')
                    keep = len(parts) - node.level + 1
                    if keep < 0:
                        continue
                    prefix = parts[:keep]
                    base = '.'.join(prefix + ([base] if base else []))
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    aliases[alias.asname or alias.name] = (base, alias.name)
        return aliases

    ## Extract the qualified head of a supported annotation expression.
    ## 提取受支持注解表达式的限定名称头部。
    #
    #  @param expression Annotation AST.
    #  @return Dotted name or None when unsupported.
    @staticmethod
    def _head(expression):
        while isinstance(expression, ast.Subscript):
            expression = expression.value
        while isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
            return None
        if isinstance(expression, ast.Name):
            return expression.id
        if isinstance(expression, ast.Attribute):
            names = [expression.attr]
            value = expression.value
            while isinstance(value, ast.Attribute):
                names.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                return '.'.join([value.id] + list(reversed(names)))
        return None

    ## Collect direct or conditional module assignments to a name.
    ## 收集模块中对名称的直接或条件赋值。
    #
    #  @param body Statement sequence.
    #  @param name Assigned name.
    #  @return Assignment value expressions.
    @staticmethod
    def _module_assignments(body, name):
        values = []
        for node in body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == name for target in node.targets):
                values.append(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and node.target.id == name and node.value is not None:
                values.append(node.value)
            elif isinstance(node, ast.If):
                values.extend(_Resolver._module_assignments(node.body, name))
                values.extend(_Resolver._module_assignments(node.orelse, name))
        return values

    ## Resolve a generic-alias factory's preserved origin when its shape is proven.
    ## 在工厂形态得到证明时解析泛型别名所保留的来源。
    #
    #  @param module Dotted module name.
    #  @param tree Parsed module AST.
    #  @param path Module source path.
    #  @param expression Candidate factory call.
    #  @param seen Visited resolution keys.
    #  @return True if iterable, otherwise None or an unproven result.
    def _generic_alias_origin(self, module, tree, path, expression, seen):
        if not isinstance(expression, ast.Call) or not expression.args:
            return None
        factory = self._head(expression.func)
        if factory is None:
            return None
        target = self._qualified(module, tree, path, expression.func)
        if target is None:
            return None
        factory_module, factory_name = target
        document = self._document(factory_module)
        if document is None:
            return None
        factory_tree, factory_path = document
        classes = [node for node in factory_tree.body
                   if isinstance(node, ast.ClassDef) and node.name == factory_name]
        if len(classes) != 1:
            return None
        initializer = next((node for node in classes[0].body
                            if isinstance(node, ast.FunctionDef) and node.name == '__init__'), None)
        item_access = any(isinstance(node, ast.FunctionDef) and node.name == '__getitem__'
                          for node in classes[0].body)
        if initializer is None or not item_access or len(initializer.args.args) < 2:
            return None
        origin_name = initializer.args.args[1].arg
        stores_origin = any(isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Attribute) and target.attr in ('__origin__', 'origin', '_origin')
            and isinstance(target.value, ast.Name)
            and target.value.id == initializer.args.args[0].arg for target in node.targets)
            and isinstance(node.value, ast.Name) and node.value.id == origin_name
            for node in ast.walk(initializer))
        if not stores_origin:
            return None
        return self._expression_iterable(module, tree, path, expression.args[0], seen)

    ## Resolve a supported name through module import syntax.
    ## 通过模块导入语法解析受支持的名称。
    #
    #  @param module Dotted module name.
    #  @param tree Parsed module AST.
    #  @param path Module source path.
    #  @param expression Candidate annotation expression.
    #  @return Module and symbol pair, or None when unresolved.
    def _qualified(self, module, tree, path, expression):
        head = self._head(expression)
        if not head:
            return None
        parts = head.split('.')
        aliases = self._module_imports(module, tree, path)
        first = aliases.get(parts[0])
        if first is None:
            # A locally declared class or a known builtin type.
            if len(parts) == 1:
                return ('builtins', head) if head in {
                    'list', 'tuple', 'set', 'frozenset', 'dict', 'str', 'bytes', 'range'
                } else (module, head)
            return None
        base_module, imported = first
        result_module = base_module if imported is None else base_module
        result_name = imported
        if len(parts) > 1:
            if imported is None:
                result_module = base_module
                result_name = '.'.join(parts[1:])
            else:
                return None
        return result_module, result_name

    ## Resolve a function or type through imports and declarations.
    ## 通过导入和声明解析函数或类型。
    #
    #  @param module Dotted module name.
    #  @param name Symbol name.
    #  @param kind Function or type resolution mode.
    #  @param seen Visited resolution keys.
    #  @return True for proven iterable behavior, otherwise a false or unknown result.
    def _resolve_symbol(self, module, name, kind, seen):
        key = (module, name, kind)
        if key in seen or len(seen) > 16:
            return None

        # Cycles and deep alias chains cannot establish a return protocol.
        # 循环或过深的别名链不能证明返回协议。
        seen.add(key)
        document = self._document(module)
        if document is None:
            return None
        tree, path = document
        aliases = self._module_imports(module, tree, path)
        alias = aliases.get(name)
        if alias is not None:
            target_module, target_name = alias
            if target_name is not None:
                return self._resolve_symbol(target_module, target_name, kind, seen)
            # `import package.submodule` exposes a module; a later type name is
            # resolved by the caller as a member of that module.
            return None
        matching = [node for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == name]
        if kind == 'function' and matching:
            # Every collected overload must declare an iterable return.
            # 所有收集到的重载都必须声明可迭代返回值。
            returns = [node.returns for node in matching
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if not returns or any(item is None for item in returns):
                return None
            return self._all_iterable(module, tree, path, returns, seen)
        if kind == 'type' and matching:
            classes = [node for node in matching if isinstance(node, ast.ClassDef)]
            if not classes:
                return None
            return all(any(isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and member.name in ('__iter__', '__getitem__')
                           for member in cls.body) for cls in classes)
        assigned = self._module_assignments(tree.body, name)
        if kind == 'type' and assigned:
            outcomes = []
            for expression in assigned:
                target = self._qualified(module, tree, path, expression)
                if target is not None and target[1] is not None:
                    target_module, target_name = target
                    outcome = self._resolve_symbol(target_module, target_name, 'type', set(seen))
                else:
                    outcome = self._generic_alias_origin(
                        module, tree, path, expression, set(seen))
                outcomes.append(outcome)
            return True if all(outcome is True for outcome in outcomes) else None
        return None

    ## Resolve whether an annotation expression denotes an iterable type.
    ## 解析注解表达式是否表示可迭代类型。
    #
    #  @param module Dotted module name.
    #  @param tree Parsed module AST.
    #  @param path Module source path.
    #  @param expression Return annotation AST.
    #  @param seen Visited resolution keys.
    #  @return True when proven; otherwise false or None.
    def _expression_iterable(self, module, tree, path, expression, seen):
        if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
            return (self._expression_iterable(module, tree, path, expression.left, set(seen))
                    and self._expression_iterable(module, tree, path, expression.right, set(seen)))
        target = self._qualified(module, tree, path, expression)
        if target is None:
            return None
        target_module, target_name = target
        if target_name is None:
            return None
        if target_module == 'builtins' and target_name in {
                'list', 'tuple', 'set', 'frozenset', 'dict', 'str', 'bytes', 'range'}:
            return True
        if target_module in ('typing', 'collections.abc') and target_name in {
                'Iterable', 'Iterator', 'Generator', 'Sequence', 'MutableSequence',
                'Collection', 'Container', 'Reversible'}:
            return True
        return self._resolve_symbol(target_module, target_name, 'type', set(seen))

    ## Require iterable proof for every collected return annotation.
    ## 要求每个收集到的返回注解均证明为可迭代。
    #
    #  @param module Dotted module name.
    #  @param tree Parsed module AST.
    #  @param path Module source path.
    #  @param returns Return annotation expressions.
    #  @param seen Visited resolution keys.
    #  @return True when all are proven, otherwise None.
    def _all_iterable(self, module, tree, path, returns, seen):
        for expression in returns:
            outcome = self._expression_iterable(module, tree, path, expression, set(seen))
            if outcome is not True:
                return None
        return True

    ## Build a versioned iterable-return fact for a qualified function.
    ## 为限定函数构建带源码版本的可迭代返回事实。
    #
    #  @param qualified_target Dotted function name.
    #  @return Protocol evidence or None when unproven.
    def iterable_return(self, qualified_target):
        module, separator, name = qualified_target.rpartition('.')
        if not separator:
            return None
        outcome = self._resolve_symbol(module, name, 'function', set())
        return ({'target': qualified_target, 'source_hashes': dict(self.hashes),
                 'basis': 'bounded_stub_return_protocol'} if outcome is True else None)


## Prove iterable returns for all declarations of a qualified function.
## 证明限定函数的所有声明均返回可迭代类型。
#
#  @param qualified_target Dotted function name.
#  @param roots Ordered import roots.
#  @return Versioned protocol fact or None on uncertainty or analysis failure.
def iterable_return_fact(qualified_target, roots):
    """Prove every declared overload returns a type with an iteration method."""
    try:
        return _Resolver(roots).iterable_return(qualified_target)
    except (OSError, TypeError, ValueError, RecursionError):
        return None
