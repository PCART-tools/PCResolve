## @package pcresolve.flow.index.definitions
#  Index flow definitions and class facts.
#
#
#  Source class hierarchy, scope and bounded definition facts.
#  源码类层次、作用域和有界定义事实。



import ast

import builtins

import os

from dataclasses import asdict, replace

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches

from pcresolve.flow.proofs.protocols import syntax_facts

from pcresolve.facts.scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)

from pcresolve.facts.import_facts import import_facts, resolve_relative_module

from pcresolve.flow.proofs.callables._constructor_entry import source_member as constructor_source_member

from pcresolve.flow.proofs.classes._class_decoration import constructor_decorations, member_preservation

from pcresolve.flow.proofs.classes._class_metadata_read import native_function_scalar

from pcresolve.flow.proofs.classes._class_type_tests import native_class_operand

from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified as namespace_unmodified



_CLASS_BINDING_NODE_LIMIT = 1000000

_CLASS_BINDING_IRRELEVANT_LEAVES = (
    ast.Constant, ast.expr_context, ast.operator, ast.unaryop, ast.boolop, ast.cmpop)

_BUILTIN_SCOPE = replace(FLOW_SCOPE, descend_lambdas=False,
                        include_comprehension_targets=False,
                        include_except_targets=True, import_from_root=False)



## Deduplicate values while retaining their first occurrence order.
## 去重并保留值首次出现的顺序。
#
#  @param values Iterable of comparable values.
#  @return List of unique values in input order.
def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

## Resolve class definitions and bounded source-level semantics.
## 解析类定义及其有界源码语义。
class ClassFactsMixin:

    ## Resolve exact source base classes without guessing dynamic bases.
    ## 解析精确源码基类，不猜测动态基类。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @return Tuple of base definitions or None when unresolved.
    def _base_classes(self, module, owner):
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        cls = classes[0][1]
        if cls.keywords:
            return None
        result = []
        for base in cls.bases:
            expression = base.value if isinstance(base, ast.Subscript) else base
            name = ast.unparse(expression)
            if (name == 'object' and 'object' not in self.imports.get(module, {})
                    and 'object' not in self.module_bindings.get(module, set())
                    and not self._definition_index.find(module, 'object')
                    and not self._definition_index.find(module, 'object', kind='class')):
                continue
            first, dot, rest = name.partition('.')
            if first in self.module_bindings.get(module, set()):
                return None
            alias = self.imports.get(module, {}).get(first)
            qualified = alias + dot + rest if alias else module + '.' + name
            matches = self._definition_index.find_qualified(
                [qualified], kind='class')
            if len(matches) != 1:
                return None
            result.append(matches[0])
        return tuple(result)

    ## Construct a source class MRO with cycle and ambiguity checks.
    ## 在循环和歧义检查下构造源码类 MRO。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @param seen Ancestor identities already visited.
    #  @return Ordered class definitions or None when unproven.
    def _class_mro(self, module, owner, seen=()):
        identity = (module, owner)
        if identity in seen:
            return None
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        bases = self._base_classes(module, owner)
        if bases is None:
            return None
        sequences = []
        for ref, _ in bases:
            inherited = self._class_mro(
                ref.module, ref.qualname, seen + (identity,))
            if inherited is None:
                return None
            sequences.append(list(inherited))
        sequences.append(list(bases))
        # Apply the C3 merge; incompatible base orders remain unresolved.
        # 执行 C3 合并；基类顺序不兼容时保持未解析。
        result = [classes[0]]
        while any(sequences):
            candidate = next((sequence[0] for sequence in sequences if sequence
                              and all(sequence[0] not in other[1:]
                                      for other in sequences)), None)
            if candidate is None:
                return None
            result.append(candidate)
            for sequence in sequences:
                if sequence and sequence[0] == candidate:
                    sequence.pop(0)
        return tuple(result)

    ## Find an inherited method only when source lookup remains unambiguous.
    ## 仅在源码查找无歧义时查找继承方法。
    #
    #  @param module Class module.
    #  @param owner Qualified class name.
    #  @param method Method name.
    #  @param seen Ancestor identities already visited.
    #  @param skip_current_members Whether to begin after the current class.
    #  @return Source definition or None when lookup is unproven.
    def _inherited_method(self, module, owner, method, seen=(),
                          skip_current_members=False):
        identity = (module, owner)
        if identity in seen:
            return None
        classes = self._definition_index.find(module, owner, kind='class')
        if len(classes) != 1:
            return None
        cls = classes[0][1]
        if cls.keywords:
            return None
        if (not skip_current_members and any(
               isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id == method
               for statement in cls.body if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               for n in ast.walk(statement))):
            return None
        blocked_names = ('__getattr__', '__getattribute__') if skip_current_members else (
            method, '__getattr__', '__getattribute__')
        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in blocked_names for n in cls.body):
            return None
        bases = self._base_classes(module, owner)
        if bases is None:
            return None
        if bases:
            ref, _ = bases[0]
            matches = self._definition_index.find(
                ref.module, ref.qualname + '.' + method)
            if len(matches) == 1:
                return matches[0]
        mro = self._class_mro(module, owner)
        if mro is None:
            return None
        for ref, base in mro[1:]:
            matches = self._definition_index.find(
                ref.module, ref.qualname + '.' + method)
            if len(matches) == 1:
                return matches[0]
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name in ('__getattr__', '__getattribute__')
                   for n in base.body):
                return None
            if any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                   and n.id == method for statement in base.body
                   if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                   for n in ast.walk(statement)):
                return None
        return None

    ## Select the first modeled allocator or initializer in the source MRO.
    ## 从源码 MRO 中选择首个已建模的分配器或初始化器。
    #
    #  @param target_class Class reference and AST pair.
    #  @return Constructor source member or None when lookup is unproven.
    def _constructor_target(self, target_class):
        ref, _ = target_class
        hierarchy = self._class_mro(ref.module, ref.qualname)
        if not hierarchy or len(hierarchy) > 64:
            return None
        # type.__call__ invokes the MRO-selected allocator before deciding
        # whether initialization applies. A direct __init__ cannot override
        # an inherited __new__, and an unresolved allocator cannot license it.
        # 分配器先于初始化器选择；未解析的分配器不能证明初始化器被调用。
        for method in ('__new__', '__init__'):
            if method == '__init__' and not self._ordinary_construction(
                    ref, allow_bounded_decorations=True):
                return None
            for owner, cls in hierarchy:
                members = [member for member in cls.body
                           if method in statement_scope_facts([member]).bound]
                if members:
                    return constructor_source_member(self, owner, cls, method)
        return None

    ## Select an instance member through an unchanged source MRO.
    ## 通过未变更的源码 MRO 选择实例成员。
    #
    #  @param module Source receiver module.
    #  @param owner Actual receiver class, which may differ from the lexical owner.
    #  @param method Attribute being invoked.
    #  @return Unique source definition or None for unproven lookup/state.
    def _instance_method_candidate(self, module, owner, method):
        hierarchy = self._class_mro(module, owner)
        if not hierarchy or len(hierarchy) > 64:
            return None
        for _, cls in hierarchy:
            if (cls.keywords or any(name in
                    statement_scope_facts(cls.body).bound
                    for name in ('__getattribute__', '__getattr__'))):
                return None
        if member_preservation(self, hierarchy,
                {method, '__getattribute__', '__getattr__', '__class__', '__bases__', '*'}) is None:
            return None
        writes, truncated = self._class_binding_writes()
        if truncated or any(attribute in (method, '*', '__class__', '__bases__')
                and any(written == ref for ref, _ in hierarchy)
                for written, attribute, _, _, _ in writes):
            return None
        for ref, cls in hierarchy:
            if method in statement_scope_facts(cls.body).bound:
                return constructor_source_member(self, ref, cls, method)
        return None

    ## Find the innermost indexed class enclosing a source definition.
    ## 查找包围源码定义的最内层已索引类。
    #
    #  @param ref Source definition identity.
    #  @return Class name or empty string when no class is found.
    def _lexical_class_name(self, ref):
        parts = ref.qualname.split('.')[:-1]
        for length in range(len(parts), 0, -1):
            if self._definition_index.find(ref.module, '.'.join(parts[:length]), kind='class'):
                return parts[length - 1]
        return ''

    ## Reuse statement-ordered syntax only within this immutable source generation.
    ## 仅在当前不可变源码生成版本内复用按语句排序的语法事实。
    #
    #  @param body Ordered statements, never a synthetic or modified source body.
    #  @param limit Remaining caller-specific node allowance.
    #  @return Complete structure, or None to retain budgeted per-node traversal.
    def _syntax_facts(self, body, limit):
        if self._analysis_budget is not None:
            # Budgeted traversals must charge their own visits.
            # 有预算的遍历必须单独计量节点访问。
            return None
        key = tuple(body)
        facts = self._syntax_fact_cache.get(key)
        if facts is None:
            facts = syntax_facts.body_syntax(key, limit)
            self._syntax_fact_cache[key] = facts
        elif len(facts.nodes) > limit:
            raise syntax_facts.SyntaxLimit()
        return facts

    ## Read immutable lexical facts once per AST definition in this source generation.
    ## 在当前源码生成版本内，每个 AST 定义只读取一次不可变词法事实。
    #
    #  @param node Function or lambda definition.
    #  @return Flow-compatible lexical facts.
    def _scope_facts(self, node):
        facts = self._scope_fact_cache.get(node)
        if facts is None:
            facts = function_scope_facts(node, FLOW_SCOPE)
            self._scope_fact_cache[node] = facts
        return facts

    ## Collect bindings relevant to builtin lookup, including definition inputs.
    ## 收集与内置名称查找相关的绑定，包括定义时求值的输入。
    #
    #  @param body Statement sequence.
    #  @return Lexical facts augmented with definition-evaluation bindings.
    def _builtin_statement_facts(self, body):
        facts = statement_scope_facts(body, _BUILTIN_SCOPE)
        bound = set(facts.bound)

        ## Visit expressions evaluated while a definition is created.
        ## 访问创建定义时求值的表达式。
        #
        #  @param node Source AST node.
        #  @return None
        def evaluations(node):
            if self._analysis_budget is not None:
                self._analysis_budget.checkpoint()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                expressions = list(node.args.defaults)
                expressions.extend(value for value in node.args.kw_defaults if value is not None)
                expressions.extend(getattr(node, 'decorator_list', []))
                arguments = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                arguments += [value for value in (node.args.vararg, node.args.kwarg) if value is not None]
                expressions.extend(argument.annotation for argument in arguments if argument.annotation is not None)
                if getattr(node, 'returns', None) is not None:
                    expressions.append(node.returns)
            elif isinstance(node, ast.ClassDef):
                expressions = list(node.decorator_list) + list(node.bases)
                expressions.extend(keyword.value for keyword in node.keywords)
            else:
                for child in ast.iter_child_nodes(node):
                    evaluations(child)
                return
            # Definition evaluation belongs to this lexical body, not the new
            # function/class/lambda body. Keep the shared collectors unchanged.
            # 定义输入在外层词法体求值，不属于新定义的执行体。
            bound.update(statement_scope_facts(expressions, _BUILTIN_SCOPE).bound)
            for expression in expressions:
                evaluations(expression)

        for statement in body:
            evaluations(statement)
        return replace(facts, bound=frozenset(bound))

    ## Cache builtin-lookup bindings for a function, lambda or class body.
    ## 缓存函数、lambda 或类体的内置名称查找绑定。
    #
    #  @param node Source definition AST.
    #  @return Immutable lexical facts for builtin lookup.
    def _builtin_scope_facts(self, node):
        facts = self._builtin_scope_cache.get(node)
        if facts is None:
            body = [node.body] if isinstance(node, ast.Lambda) else node.body
            facts = self._builtin_statement_facts(body)
            # The statement collector already supplies this policy's body
            # facts and definition-evaluation bindings. Only root parameters
            # distinguish the function collector; do not walk its body twice.
            if not isinstance(node, ast.ClassDef) and _BUILTIN_SCOPE.include_parameters:
                args = node.args
                parameters = {arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs}
                parameters.update(arg.arg for arg in (args.vararg, args.kwarg) if arg)
                if _BUILTIN_SCOPE.exclude_outer_declarations:
                    parameters.difference_update(facts.globals | facts.nonlocals)
                facts = replace(facts, bound=facts.bound | parameters)
            self._builtin_scope_cache[node] = facts
        return facts

    ## Classify a bare builtin spelling under explicit lexical lookup rules.
    ## 按显式词法查找规则分类裸内置名称。
    #
    #  @param ref Source function identity.
    #  @param node Source function or lambda whose lexical names are checked.
    #  @param name Bare name, not an attribute or import alias.
    #  @param env Optional current bindings, including unknown/empty local bindings.
    #  @param definition_scope Check a definition's enclosing scope, not its future body locals.
    #  @return confirmed_builtin, source_binding, or unconfirmed; no runtime proof.
    def _builtin_name_status(self, ref, node, name, env=None, definition_scope=False):
        if not hasattr(builtins, name):
            return 'unconfirmed'
        if env is not None and name in env:
            return 'source_binding'
        facts = (statement_scope_facts([]) if definition_scope else self._builtin_scope_facts(node))
        if name in facts.bound:
            return 'source_binding'
        nonlocal_name = name in facts.nonlocals
        parent = ref.qualname.rpartition('.')[0]
        if name not in facts.globals:
            while parent:
                enclosing = self._definition_index.find(ref.module, parent)
                if len(enclosing) > 1:
                    return 'unconfirmed'
                if enclosing:
                    outer = self._builtin_scope_facts(enclosing[0][1])
                    if name in outer.globals:
                        break
                    if name in outer.bound - outer.nonlocals:
                        return 'source_binding'
                    nonlocal_name = nonlocal_name or name in outer.nonlocals
                elif not self._definition_index.find(ref.module, parent, kind='class'):
                    return 'unconfirmed'
                parent = parent.rpartition('.')[0]
        if nonlocal_name:
            return 'unconfirmed'

        # A module binding, incomplete index or possible namespace write blocks proof.
        # 模块绑定、索引不完整或可能的命名空间写入都会阻止证明。
        if ref.module not in self._builtin_module_cache:
            bodies = self.module_bodies.get(ref.module, [])
            names = set()
            uncertain = len(bodies) != 1 or any(
                item.get('module') == ref.module for item in self.index_boundaries)
            for _, body in bodies:
                names.update(self._builtin_statement_facts(body).bound)
                for statement in body:
                    for child in ast.walk(statement):
                        if self._analysis_budget is not None:
                            self._analysis_budget.checkpoint()
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            scope = self._builtin_scope_facts(child)
                            names.update(scope.globals & scope.bound)
            self._builtin_module_cache[ref.module] = names, uncertain
        names, uncertain = self._builtin_module_cache[ref.module]
        if name in names:
            return 'source_binding'
        if uncertain or '*' in names or '__builtins__' in names:
            return 'unconfirmed'
        if not namespace_unmodified(self, ref.module + '.' + name):
            return 'unconfirmed'
        return 'confirmed_builtin'

    ## Find a uniquely constructed field and its undecorated source method.
    ## 查找唯一构造的字段及其未装饰源码方法。
    #
    #  @param ref Accessing method identity.
    #  @param field Instance field name.
    #  @param method Requested method name.
    #  @return Target definition and assignment, or None when unproven.
    def _field_candidate(self, ref, field, method):
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        if len(classes) != 1 or classes[0][1].decorator_list:
            return None
        cls = classes[0][1]
        methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(n.name in ('__getattribute__', '__getattr__', field) for n in methods):
            return None
        writes = []
        for member in methods:
            for statement in ast.walk(member):
                if isinstance(statement, ast.Attribute) and statement.attr == field and isinstance(statement.ctx, (ast.Store, ast.Del)):
                    writes.append(statement)
        init = next((n for n in methods if n.name == '__init__' and not n.decorator_list), None)
        if len(writes) != 1 or init is None:
            return None
        assignment = next((n for n in init.body if isinstance(n, ast.Assign)
                           and len(n.targets) == 1 and n.targets[0] is writes[0]), None)
        args = init.args.posonlyargs + init.args.args
        if (assignment is None or not args or not isinstance(writes[0].value, ast.Name)
                or writes[0].value.id != args[0].arg or not isinstance(assignment.value, ast.Call)):
            return None
        name = ast.unparse(assignment.value.func)
        first, dot, rest = name.partition('.')
        if first in self.module_bindings.get(ref.module, set()) or first in self._scope_facts(init).bound:
            return None
        alias = self.imports.get(ref.module, {}).get(first)
        qualified = alias + (dot + rest if dot else '') if alias else ref.module + '.' + name
        targets = self._definition_index.find_qualified([qualified], kind='class')
        if len(targets) != 1 or targets[0][1].decorator_list:
            return None
        target_class = targets[0]
        if any(isinstance(n, ast.FunctionDef) and n.name in ('__getattribute__', '__getattr__', '__new__') for n in target_class[1].body):
            return None
        target = self._definition_index.find(
            target_class[0].module, target_class[0].qualname + '.' + method)
        return (target[0], assignment) if len(target) == 1 and not target[0][1].decorator_list else None

    ## Find constructor-backed field types shared by every normal return path.
    ## 查找所有正常返回路径共享的构造函数字段类型。
    #
    #  @param target Local method definition.
    #  @return Bounded field/type facts with assignment and return AST evidence.
    def _returned_field_instances(self, target):
        ref, accessor = target
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        if len(classes) != 1 or classes[0][1].decorator_list or accessor.decorator_list:
            return []
        cls = classes[0][1]
        owner_hierarchy = self._class_mro(ref.module, owner)
        if owner_hierarchy is None or any(
                base.decorator_list or any(
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name in ('__getattr__', '__getattribute__',
                                        '__setattr__', '__delattr__')
                    for member in base.body)
                for _, base in owner_hierarchy):
            return []
        params = accessor.args.posonlyargs + accessor.args.args
        if not params or accessor.args.vararg or accessor.args.kwarg:
            return []
        receiver = params[0].arg
        methods = [member for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if any(isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name)
                       and isinstance(node.ctx, ast.Store)
                       and node.id == accessor.name
                       for node in ast.walk(statement))
               for statement in cls.body):
            return []

        ## Collect supported receiver-field returns and detect fallthrough paths.
        ## 收集受支持的接收者字段返回并检测可继续执行的路径。
        #
        #  @param statements Statement sequence to inspect.
        #  @return Return nodes and fallthrough flag, or None for unsupported syntax.
        def returns_from(statements):
            returns = []
            open_path = True
            for statement in statements:
                if not open_path:
                    break
                if isinstance(statement, ast.Return):
                    value = statement.value
                    if not (isinstance(value, ast.Attribute)
                            and isinstance(value.value, ast.Name)
                            and value.value.id == receiver):
                        return None
                    returns.append(statement)
                    open_path = False
                elif isinstance(statement, ast.If):
                    if not (isinstance(statement.test, ast.Constant)
                            or (isinstance(statement.test, ast.Name)
                                and statement.test.id != receiver)):
                        return None
                    left = returns_from(statement.body)
                    right = returns_from(statement.orelse)
                    if left is None or right is None:
                        return None
                    returns.extend(left[0] + right[0])
                    open_path = left[1] or right[1]
                elif isinstance(statement, ast.Pass) or (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str)):
                    continue
                else:
                    return None
            return returns, open_path

        paths = returns_from(accessor.body)
        if paths is None or paths[1] or not paths[0]:
            return []
        fields = {statement.value.attr for statement in paths[0]}
        if len(fields) != 1:
            return []
        field = next(iter(fields))
        if any(any(getattr(member, 'name', None) == field or
                   (isinstance(member, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    and any(isinstance(node, ast.Name)
                            and isinstance(node.ctx, ast.Store)
                            and node.id == field
                            for node in ast.walk(member)))
                   for member in base.body)
               for _, base in owner_hierarchy):
            return []
        writes = [node for member in methods for node in ast.walk(member)
                  if isinstance(node, ast.Attribute) and node.attr == field
                  and isinstance(node.ctx, (ast.Store, ast.Del))]
        initializers = [member for member in methods if member.name == '__init__']
        if (len(writes) != 1 or len(initializers) != 1
                or initializers[0].decorator_list):
            return []
        init = initializers[0]
        if any(isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
               and any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                       and node.id == '__init__' for node in ast.walk(statement))
               for statement in cls.body):
            return []
        assignment = next((statement for statement in init.body
                           if isinstance(statement, ast.Assign)
                           and len(statement.targets) == 1
                           and statement.targets[0] is writes[0]
                           and isinstance(writes[0].value, ast.Name)
                           and writes[0].value.id == receiver), None)
        if assignment is None:
            return []
        if any(statement is not assignment and not isinstance(statement, ast.Pass)
               and not (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))
               for statement in init.body):
            return []
        if any((isinstance(node, ast.Attribute)
                and node.attr == '__dict__')
               or isinstance(node, ast.NamedExpr)
               or (isinstance(node, ast.Call)
                   and ((isinstance(node.func, ast.Name)
                         and node.func.id in ('setattr', 'delattr', 'vars'))
                        or (isinstance(node.func, ast.Attribute)
                            and node.func.attr in ('__setattr__', '__delattr__'))))
               for member in methods for node in ast.walk(member)
               if node is not assignment.value):
            return []

        ## Resolve every supported conditional constructor alternative.
        ## 解析所有受支持的条件构造器候选。
        #
        #  @param value Constructor expression.
        #  @return Class identities or None when an alternative is unproven.
        def constructors(value):
            if isinstance(value, ast.IfExp):
                if any(isinstance(node, (ast.Call, ast.NamedExpr))
                       for node in ast.walk(value.test)):
                    return None
                left, right = constructors(value.body), constructors(value.orelse)
                return left + right if left is not None and right is not None else None
            if not isinstance(value, ast.Call):
                return None
            name = ast.unparse(value.func)
            first = name.partition('.')[0]
            if (first in self.module_bindings.get(ref.module, set())
                    or first in self._scope_facts(init).bound):
                return None
            match = self._resolve_class(ref, name)
            if match is None or match[1].decorator_list or match[1].keywords:
                return None
            hierarchy = self._class_mro(match[0].module, match[0].qualname)
            if hierarchy is None or any(
                    base.decorator_list or any(
                        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and member.name in ('__new__', '__getattribute__',
                                            '__getattr__')
                        for member in base.body)
                    for _, base in hierarchy):
                return None
            return [match[0]]

        types = constructors(assignment.value)
        if not types:
            return []
        return [{'field': field, 'instance_type': asdict(class_ref),
                 'assignment_ref': ref, 'assignment_node': assignment,
                 'return_ref': ref, 'return_nodes': paths[0]}
                for class_ref in _unique(types)]

    ## Recognize an unshadowed builtin staticmethod or classmethod decorator.
    ## 识别未被遮蔽的内置 staticmethod 或 classmethod 装饰器。
    #
    #  @param target Function identity and AST pair.
    #  @return Descriptor name or None when not proven.
    def _descriptor_kind(self, target):
        ref, node = target
        decorators = getattr(node, 'decorator_list', [])
        if len(decorators) != 1 or not isinstance(decorators[0], ast.Name):
            return None
        name = decorators[0].id
        if name not in ('staticmethod', 'classmethod'):
            return None
        if (name in self.imports.get(ref.module, {})
                or name in self.module_bindings.get(ref.module, set())
                or self._definition_index.find(ref.module, name)
                or self._definition_index.find(ref.module, name, kind='class')):
            return None
        owner = ref.qualname.rpartition('.')[0]
        classes = self._definition_index.find(ref.module, owner, kind='class')
        cls = classes[0][1] if classes else None
        if cls is None:
            return None
        for statement in cls.body:
            if statement is node:
                break
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Import,
                                      ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef)):
                names = {item.id for item in ast.walk(statement)
                         if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)}
                if name in names or getattr(statement, 'name', None) == name:
                    return None
        return name

    ## Scan bounded source for class-binding writes and optional escape evidence.
    ## 有界扫描源码中的类绑定写入及可选逃逸证据。
    #
    #  @param include_escapes Include possible class escapes in the scan.
    #  @param private_result Optional private-result projection callback.
    #  @return Pair of write records and truncation flag.
    def _class_binding_writes(self, include_escapes=False, private_result=None):
        cached = self._class_binding_escape_cache if include_escapes else self._class_binding_write_cache
        if cached is not None and private_result is None:
            return cached
        writes, remaining = [], [_CLASS_BINDING_NODE_LIMIT]
        closure_bindings = {}

        ## Find the unique source class owning a qualified method.
        ## 查找限定方法所属的唯一源码类。
        #
        #  @param qualified Qualified method name.
        #  @return Zero or one class identities.
        def method_owner(qualified):
            target = self._resolve_import_binding(qualified) if include_escapes else None
            owner = target[0].qualname.rpartition('.')[0] if target else ''
            classes = self._definition_index.find(target[0].module, owner, kind='class') if owner else []
            return [classes[0][0]] if len(classes) == 1 else []

        ## Resolve possible class identities from a bounded source expression.
        ## 从有界源码表达式解析可能的类标识。
        #
        #  @param expression Candidate expression.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @return Candidate class identities.
        def identity(expression, ref, aliases):
            if isinstance(expression, ast.IfExp):
                return _unique(identity(expression.body, ref, aliases)
                               + identity(expression.orelse, ref, aliases))
            if isinstance(expression, ast.Name) and expression.id in aliases:
                value = aliases[expression.id]
                return [value] if isinstance(value, FunctionRef) else value if isinstance(value, list) else []
            if not isinstance(expression, (ast.Name, ast.Attribute)):
                return []
            name = ast.unparse(expression)
            first, dot, rest = name.partition('.')
            if first in aliases:
                imported = aliases[first]
                if include_escapes and isinstance(imported, FunctionRef) and dot:
                    return method_owner(imported.module + '.' + imported.qualname + dot + rest)
                if isinstance(imported, str) and dot:
                    target = self._definition_index.resolve_qualified(
                        [imported + dot + rest], self.imports, kind='class')
                    return [target[0]] if target else method_owner(imported + dot + rest)
                return []
            target = self._resolve_class(ref, name)
            if target is None:
                target = self._class_symbol(ref.module + '.' + name)
            return [target[0]] if target else method_owner(ref.module + '.' + name)

        ## Find class identities potentially exposed by an expression.
        ## 查找表达式可能暴露的类标识。
        #
        #  @param expression Candidate expression.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @param held Captured class identities.
        #  @param result_only Restrict traversal to result projections.
        #  @param contained_only Treat candidates as contained exposures.
        #  @return Potentially exposed class identities.
        def exposed(expression, ref, aliases, held, result_only=False, contained_only=False):
            # Containment is an escape hazard, never an exact class identity.
            # 容器持有表示可能逃逸，不能据此断言精确类标识。
            found, pending = [], [(expression, aliases, held, result_only)]
            while pending:
                child, names, captures, projection = pending.pop()
                if child is None or isinstance(child, _CLASS_BINDING_IRRELEVANT_LEAVES):
                    continue
                remaining[0] -= 1
                if remaining[0] < 0:
                    break
                if child is None or projection and isinstance(child, ast.Call):
                    # Returning a call does not itself prove a returned class.
                    # Calls and their arguments are inspected separately below.
                    continue
                if (isinstance(child, ast.Attribute)
                        and native_function_scalar(self, child,
                            lambda value: identity(value, ref, names))):
                    # This scalar projection grants no class/method alias.
                    # Other escapes and every visible writer stay in the scan;
                    # consumers still require the complete closed-use invariant.
                    continue
                if (private_result is not None and isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Call)):
                    constructor = child.func.value
                    references = identity(constructor.func, ref, names)
                    if private_result(ref, child, references):
                        # Only the constructor's class identity is projected
                        # out. Input capabilities and both calls remain checked.
                        pending.extend((argument, names, captures, projection)
                                       for argument in constructor.args)
                        pending.extend((keyword.value, names, captures, projection)
                                       for keyword in constructor.keywords)
                        continue
                if isinstance(child, ast.Lambda):
                    defaults = child.args.defaults + [v for v in child.args.kw_defaults if v is not None]
                    pending.extend((value, names, captures, projection) for value in defaults)
                    bound = self._scope_facts(child).bound
                    local = dict(names)
                    local.update({name: None for name in bound})
                    retained = {name: refs for name, refs in captures.items() if name not in bound}
                    if ref not in closure_bindings:
                        enclosing = self._definition_index.find(ref.module, ref.qualname)
                        scope = self._scope_facts(enclosing[0][1]) if len(enclosing) == 1 else None
                        closure_bindings[ref] = ((scope.bound | scope.nonlocals) - scope.globals
                                                 if scope is not None else set())
                    for name in transitive_captured_names(child, set(names) | set(captures)):
                        remaining[0] -= 1
                        if remaining[0] < 0:
                            break
                        references = identity(ast.Name(id=name, ctx=ast.Load()), ref, names)
                        found.extend(captures.get(name, ()))
                        global_class = self._class_symbol(ref.module + '.' + name)
                        if (name in closure_bindings[ref] or global_class is None
                                or references != [global_class[0]]):
                            found.extend(references)
                    # A global name used as a future call's receiver is not
                    # stored in this function's closure. Actual arguments,
                    # returns and writes in that future body are scanned below.
                    pending.append((child.body, local, retained, True))
                    continue
                if isinstance(child, ast.Call) and native_class_operand(self, ref, child, names):
                    # The tested value still evaluates normally; nested calls
                    # can expose a class even though the native class operand
                    # itself does not pass to a user __instancecheck__ hook.
                    pending.append((child.args[0], names, captures, projection))
                    continue
                if isinstance(child, (ast.Name, ast.Attribute)):
                    if not contained_only:
                        found.extend(identity(child, ref, names))
                    if isinstance(child, ast.Name):
                        found.extend(captures.get(child.id, []))
                pending.extend((value, names, captures, projection) for value in ast.iter_child_nodes(child))
            return _unique(found)

        ## Record potential class escapes at a source node.
        ## 记录源码节点处可能发生的类逃逸。
        #
        #  @param references Class identities potentially exposed.
        #  @param ref Enclosing source identity.
        #  @param node Evidence AST node.
        #  @return None
        def escape(references, ref, node):
            writes.extend((class_ref, '*', 'visible_class_escape', ref, node)
                          for class_ref in references)

        ## Traverse one source node while tracking class aliases and captures.
        ## 遍历源码节点，同时跟踪类别名和捕获。
        #
        #  @param node AST node to inspect.
        #  @param ref Enclosing source identity.
        #  @param aliases Known local aliases.
        #  @param held Captured class identities.
        #  @return None
        def walk(node, ref, aliases, held):
            # These leaves cannot contain an import, class reference, closure or
            # effect. Inspect their parent operations, not repeated literal data.
            if isinstance(node, _CLASS_BINDING_IRRELEVANT_LEAVES):
                return
            remaining[0] -= 1
            if remaining[0] < 0:
                return
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                local = dict(aliases)
                bound = self._scope_facts(node).bound
                local.update({name: None for name in bound})
                retained = {name: refs for name, refs in held.items() if name not in bound}
                args = node.args
                for parameter in args.posonlyargs + args.args + args.kwonlyargs + [
                        arg for arg in (args.vararg, args.kwarg) if arg]:
                    local[parameter.arg] = None
                child_ref = FunctionRef(ref.module, (ref.qualname + '.' if ref.qualname else '')
                                        + getattr(node, 'name', '<lambda>'), ref.file_path)
                if isinstance(node, ast.Lambda):
                    for value in args.defaults + [v for v in args.kw_defaults if v is not None]:
                        walk(value, ref, aliases, held)
                    # Keep the enclosing source scope for builtin lookup;
                    # lambda parameters are masked in the scanner environment.
                    future = ast.copy_location(ast.Return(value=node.body), node.body)
                    walk(future, ref, local, retained)
                    return
                for statement in node.body if not isinstance(node, ast.Lambda) else []:
                    walk(statement, child_ref, local, retained)
                return
            if isinstance(node, ast.ClassDef):
                child_ref = FunctionRef(ref.module, (ref.qualname + '.' if ref.qualname else '')
                                        + node.name, ref.file_path)
                local = dict(aliases)
                retained = dict(held)
                for statement in node.body:
                    walk(statement, child_ref, local, retained)
                return
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for fact in import_facts(node):
                    qualified = (fact.name if fact.kind == 'import' else
                        (resolve_relative_module(ref.module,
                            os.path.basename(ref.file_path).startswith('__init__.'),
                            fact.module, fact.level)
                         if fact.level else fact.module) + '.' + fact.name)
                    target = self._class_symbol(qualified)
                    aliases[fact.python_binding] = target[0] if target else qualified
                    if include_escapes and target and ref.qualname:
                        held[fact.python_binding] = _unique(held.get(fact.python_binding, []) + [target[0]])
            if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
                owner = node.value
                attribute = node.attr if isinstance(node, ast.Attribute) else '*'
                if isinstance(owner, ast.Attribute) and owner.attr == '__dict__':
                    owner = owner.value
                target = identity(owner, ref, aliases)
                while not target and isinstance(owner, ast.Attribute):
                    attribute, owner = owner.attr, owner.value
                    target = identity(owner, ref, aliases)
                for class_ref in target:
                    writes.append((class_ref, attribute, 'visible_method_write', ref, node))
                if include_escapes:
                    escape([value for value in exposed(node.value, ref, aliases, held)
                            if value not in target], ref, node)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                function = ast.unparse(node.func)
                first, dot, rest = function.partition('.')
                imported = aliases.get(first)
                canonical = imported + dot + rest if isinstance(imported, str) else function
                if canonical in ('setattr', 'delattr', 'builtins.setattr', 'builtins.delattr') and node.args:
                    target = identity(node.args[0], ref, aliases)
                    if target:
                        attribute = (node.args[1].value if len(node.args) > 1
                            and isinstance(node.args[1], ast.Constant)
                            and isinstance(node.args[1].value, str) else '*')
                        writes.extend((class_ref, attribute, 'visible_dynamic_attribute_write', ref, node)
                                      for class_ref in target)
            if include_escapes:
                if isinstance(node, ast.Call):
                    escape(exposed(node.func, ref, aliases, held, contained_only=True), ref, node)
                    arguments = list(node.args) + [keyword.value for keyword in node.keywords]
                    if native_class_operand(self, ref, node, aliases):
                        arguments = arguments[:1]
                    for argument in arguments:
                        escape(exposed(argument, ref, aliases, held), ref, node)
                elif isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom)):
                    escape(exposed(node.value, ref, aliases, held, result_only=True), ref, node)
            for child in ast.iter_child_nodes(node):
                walk(child, ref, aliases, held)
            if isinstance(node, (ast.Assign, ast.AnnAssign)) or include_escapes and isinstance(
                    node, (ast.AugAssign, ast.NamedExpr)):
                target = identity(node.value, ref, aliases)
                contained = (exposed(node.value, ref, aliases, held, result_only=True)
                             if include_escapes else [])
                for destination in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(destination, ast.Name):
                        previous = aliases.get(destination.id)
                        previous = ([previous] if isinstance(previous, FunctionRef) else
                                    previous if isinstance(previous, list) else [])
                        aliases[destination.id] = _unique(previous + target)
                    if include_escapes:
                        if isinstance(destination, (ast.Attribute, ast.Subscript)):
                            escape(contained, ref, node)
                        else:
                            for child in ast.walk(destination):
                                if isinstance(child, ast.Name):
                                    held[child.id] = _unique(held.get(child.id, []) + contained)

        for module, bodies in self.module_bodies.items():
            for path, body in bodies:
                aliases, held = {}, {}
                for statement in body:
                    walk(statement, FunctionRef(module, '', path), aliases, held)
        result = writes, remaining[0] < 0
        if private_result is not None:
            return result
        if include_escapes:
            self._class_binding_escape_cache = result
        else:
            self._class_binding_write_cache = result
        return result
