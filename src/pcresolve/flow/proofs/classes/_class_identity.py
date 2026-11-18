## @package pcresolve.flow.proofs.classes._class_identity
#  Prove class decorator return identity.
#
#
#  Normal class-decorator return identity, independent of class write effects.
#  独立于类属性写入效果，证明类装饰器正常返回时的对象身份。



import ast
import copy
from dataclasses import asdict

from pcresolve.flow.proofs.classes._class_partial import bind_partial
from pcresolve.flow.proofs.callables.decorators._decorator_effects import _DecoratorEffects
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.scope_facts import statement_scope_facts


## Build a source span record for one decoration or return expression.
## 为一次装饰或返回表达式构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Find every direct return of an unchanged ordinary parameter.
## 查找普通参数未经改变而直接返回的所有路径。
#
#  @param analyzer Analyzer providing query-local identity budget.
#  @param function Candidate source decorator function.
#  @param parameter Parameter name whose identity must be preserved.
#  @return Return nodes that preserve the parameter, or None if any path differs.
def _returns_input(analyzer, function, parameter):
    if (not isinstance(function, ast.FunctionDef) or not function.body
            or not isinstance(function.body[-1], ast.Return)
            or parameter in statement_scope_facts(function.body).bound):
        return None
    # A nested nonlocal declaration can change the outer cell during a helper
    # invocation even though its store is absent from the outer scope facts.
    # 嵌套 nonlocal 声明可在辅助函数调用时改变外层单元，即使外层作用域事实中看不到该写入。
    inspected = 0
    for node in ast.walk(function):
        inspected += 1
        analyzer._class_identity_steps -= 1
        if analyzer._analysis_budget is not None:
            analyzer._analysis_budget.checkpoint()
        if inspected > 2000 or analyzer._class_identity_steps < 0:
            return None
        if (isinstance(node, (ast.Global, ast.Nonlocal)) and parameter in node.names
                or isinstance(node, ast.Name) and node.id == parameter
                and isinstance(node.ctx, (ast.Store, ast.Del))
                or type(node).__name__ in ('MatchAs', 'MatchStar', 'MatchMapping')
                and parameter in (getattr(node, 'name', None), getattr(node, 'rest', None))):
            return None
    returns, pending = [], list(function.body)

    # Inspect only the decorator's immediate control flow, excluding nested definitions.
    # 只检查装饰器的直接控制流，并排除嵌套定义。
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            # Defaults/decorators cannot bind the outer parameter without a
            # visible store or frame mutation, already guarded separately.
            continue
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await)):
            return None
        if isinstance(node, ast.Return):
            if not isinstance(node.value, ast.Name) or node.value.id != parameter:
                return None
            returns.append(node)
        pending.extend(ast.iter_child_nodes(node))
    return returns or None


## Cache the proof that a callable instance's class-sensitive namespace is intact.
## 缓存可调用实例类敏感命名空间保持完整的证明结果。
#
#  @param analyzer Analyzer holding mutable namespace guard caches.
#  @param ref Source class reference associated with the decorator.
#  @param expression Decorator expression that selected the callable instance.
#  @param resolution Resolved callable-instance class and captured state.
#  @return True when no unsupported class mutation or escape was found.
def _instance_namespace(analyzer, ref, expression, resolution):
    name = ast.unparse(expression)
    head, dot, rest = name.partition('.')
    imported = analyzer.imports.get(ref.module, {}).get(head)
    key = (ref.module, name) if isinstance(expression, ast.Call) else (
        imported + (dot + rest if dot else '') if imported else ref.module + '.' + name)
    construction = resolution.construction or {}
    site = construction.get('expression', {})
    if construction.get('lifetime') == 'shared_source_instance' and site:
        # Chained source assignments give multiple names to this one creation
        # site. Their alias closure is identical; inspect it once per query.
        key = tuple(site.get(field) for field in (
            'file_path', 'lineno', 'col_offset', 'end_lineno', 'end_col_offset'))
    cache = analyzer._class_identity_instance_guards
    if key not in cache:
        # Seed the cache before the expensive project-wide guard scan.
        # 在昂贵的项目级保护扫描前先写入缓存占位。
        cache[key] = False
        cache[key] = _instance_namespace_uncached(analyzer, ref, expression, resolution)
    return cache[key]


## Check a callable instance for class mutation and reference escape.
## 检查可调用实例是否存在类变更或引用逃逸。
#
#  @param analyzer Analyzer containing source classes, calls, and budgets.
#  @param ref Source reference used to resolve the decorator expression.
#  @param expression Decorator expression evaluated by the source model.
#  @param resolution Resolved callable-instance class and captured state.
#  @return True only when the instance remains within the supported closed namespace.
def _instance_namespace_uncached(analyzer, ref, expression, resolution):
    # A shared source instance has a mutable __class__, unlike a native class
    # object. Resolution of its original constructor alone is insufficient.
    sensitive = {'__class__', '__call__', '__getattribute__', '__getattr__',
                 '__setattr__', '__delattr__', '__new__'}
    if analyzer._class_identity_layout_guard is None:
        analyzer._class_identity_layout_guard = False
        inspected = 0

        # Audit sensitive layout writes project-wide because an instance may be shared across modules.
        # 实例可能跨模块共享，因此在整个项目范围内审计敏感布局写入。
        for bodies in analyzer.module_bodies.values():
            for _, body in bodies:
                for statement in body:
                    for node in ast.walk(statement):
                        inspected += 1
                        if inspected > 1000000:
                            return False
                        if analyzer._analysis_budget is not None:
                            analyzer._analysis_budget.checkpoint()
                        if (isinstance(node, ast.Attribute) and node.attr in sensitive
                                and isinstance(node.ctx, (ast.Store, ast.Del))
                                or isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
                                and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
                                in ('setattr', 'delattr', '__setattr__', '__delattr__')
                                and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                                and node.args[1].value in sensitive):
                            return False
        analyzer._class_identity_layout_guard = True
    if not analyzer._class_identity_layout_guard:
        return False
    hierarchy = analyzer._class_mro(resolution.receiver_class.module,
                                    resolution.receiver_class.qualname)
    if not hierarchy:
        return False
    methods = {member.name for _, cls in hierarchy for member in cls.body
               if isinstance(member, ast.FunctionDef)}
    data_fields = set(resolution.state)
    for _, cls in hierarchy:
        for member in cls.body:
            if not isinstance(member, ast.FunctionDef):
                continue
            parameters = member.args.posonlyargs + member.args.args
            if not parameters:
                return False
            receiver = parameters[0].arg
            parents, nodes = {}, []
            for node in ast.walk(member):
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                if len(nodes) > 2000:
                    return False
                nodes.append(node)
                parents.update((child, node) for child in ast.iter_child_nodes(node))
            for node in nodes:
                if not isinstance(node, ast.Name) or node.id != receiver or not isinstance(node.ctx, ast.Load):
                    continue
                use = parents.get(node)
                if isinstance(use, ast.Attribute) and use.value is node and not use.attr.startswith('__'):
                    continue
                if isinstance(use, ast.Call) and use.func is node:
                    continue
                return False
    if isinstance(expression, ast.Call):
        return True  # Private construction, with separately guarded initializer.
    name = ast.unparse(expression)
    head, dot, rest = name.partition('.')
    imported = analyzer.imports.get(ref.module, {}).get(head)
    origin = imported + (dot + rest if dot else '') if imported else ref.module + '.' + name
    protected = {origin}
    scopes = []
    # Source inventory, use validation and finite alias closure have separate
    # work. The shared AnalysisLimits checkpoint still charges every visit.
    remaining = 3000000

    ## Record why a source namespace proof failed, with the first useful location.
    ## 记录源码命名空间证明失败的原因及首个有效位置。
    #
    #  @param reason Machine-readable boundary reason.
    #  @param module Module containing the evidence node.
    #  @param node Optional syntax node supporting the boundary.
    #  @return False, for direct propagation from guard checks.
    def fail(reason, module='', node=None):
        analyzer._class_identity_guard_failures[origin] = {
            'reason': reason, 'module': module,
            'lineno': getattr(node, 'lineno', None),
            'syntax': ast.unparse(node)[:240] if node is not None else None}
        return False

    ## Resolve a name-like source expression to its qualified module identity.
    ## 将名称类源码表达式解析为限定模块身份。
    #
    #  @param node Name, attribute, or supported globals subscript.
    #  @param module Module providing the lexical import context.
    #  @return Qualified identity, or an empty string for unsupported syntax.
    def identity(node, module):
        if isinstance(node, ast.Name):
            imported = analyzer.imports.get(module, {}).get(node.id)
            return imported or module + '.' + node.id
        if isinstance(node, ast.Attribute):
            return identity(node.value, module) + '.' + node.attr
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'globals'
                and isinstance(node.slice, ast.Constant) and type(node.slice.value) is str):
            return module + '.' + node.slice.value
        return ''

    # Capture and audit all project source before propagating aliases to a fixed point.
    # 在迭代传播别名前，先捕获并审计整个项目源码。
    for module, bodies in analyzer.module_bodies.items():
        for _, body in bodies:
            nodes, parents = [], {}
            for statement in body:
                for node in ast.walk(statement):
                    remaining -= 1
                    if remaining < 0:
                        return fail('instance_namespace_source_budget', module, node)
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    parents.update((child, node) for child in ast.iter_child_nodes(node))
            scopes.append((module, nodes, parents))
    assignments = [(module, node) for module, nodes, _ in scopes for node in nodes
                   if isinstance(node, ast.Assign)]
    for _ in range(32):
        before = len(protected)
        for module, node in assignments:
            remaining -= 1
            if remaining < 0:
                return fail('instance_namespace_alias_budget', module, node)
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            names = {module + '.' + target.id for target in node.targets if isinstance(target, ast.Name)}
            if identity(node.value, module) in protected or names & protected:
                protected.update(names)
        if len(protected) == before:
            break
    else:
        return fail('instance_namespace_alias_cycle')

    # Reject every use that can expose, reflect on, or mutate the shared instance class.
    # 拒绝所有可能暴露、反射访问或修改共享实例类的用法。
    for module, nodes, parents in scopes:
        for node in nodes:
            remaining -= 1
            if remaining < 0:
                return fail('instance_namespace_use_budget', module, node)
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if identity(node, module) not in protected or not isinstance(
                    getattr(node, 'ctx', None), ast.Load):
                continue
            use = parents.get(node)
            if isinstance(use, ast.Attribute) and use.value is node:
                if use.attr.startswith('__'):
                    return fail('instance_namespace_class_projection', module, use)
                invocation = parents.get(use)
                if use.attr in methods and isinstance(invocation, ast.Call) and invocation.func is use:
                    continue
                if use.attr in data_fields:
                    continue
                return fail('instance_namespace_attribute_exposure', module, use)
            if isinstance(use, ast.Call) and use.func is node:
                continue
            if (isinstance(use, ast.Assign) and use.value is node
                    and all(isinstance(target, ast.Name) for target in use.targets)):
                continue
            if isinstance(use, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node in use.decorator_list:
                continue
            return fail('instance_namespace_exposure', module, node)
    return True


## Prove only that each normal class-decorator return is its original input.
## 仅证明每个类装饰器的正常返回值仍是其原始输入对象。
#
#  @param analyzer Fixed source snapshot and query-local identity/effect budgets.
#  @param target Exact source class declaration before its decorators are applied.
#  @return Ordered identity-only records, or None for open bindings/returns.
def identity_decorations(analyzer, target):
    ref, cls = target
    if not cls.decorator_list:
        return []
    cache = analyzer._class_identity_cache
    if ref in cache:
        return copy.deepcopy(cache[ref])
    cache[ref] = None
    if analyzer.index_boundaries or len(cls.decorator_list) > 8 or '.' in ref.qualname:
        return None
    observations = nonobserving_source(analyzer)
    if observations is None:
        return None
    facts = []

    # Decorators execute from the innermost expression outward; prove each layer separately.
    # 装饰器按从内到外的顺序执行，因此逐层独立证明身份保持。
    for expression in reversed(cls.decorator_list):
        probe = copy.copy(cls)
        probe.decorator_list = [expression]
        selected = analyzer._decorator_definition((ref, probe))
        parameter, factory, resolution = None, None, None
        try:
            if selected is None and isinstance(expression, ast.Call):
                partial = bind_partial(analyzer, target, expression)
                if partial is not None:
                    selected, parameter, _, factory = partial
            if selected is None:
                resolution = _DecoratorEffects(analyzer, (ref, probe), _span, 2000)
                selected, _ = resolution.resolve(expression)
                if (selected is None or resolution.dispatch_unconfirmed or resolution.boundaries):
                    return None
            owner, function = selected
            args = function.args
            parameters = args.posonlyargs + args.args
            receiver = resolution is not None and resolution.receiver_class is not None
            if receiver and not _instance_namespace(analyzer, ref, expression, resolution):
                return None
            ordinary = parameters[1:] if receiver else parameters
            if factory is None:
                if (len(ordinary) != 1 or args.defaults or args.vararg or args.kwarg or args.kwonlyargs):
                    return None
                parameter = ordinary[0].arg
            if (function.decorator_list or not unmodified(analyzer, owner.module + '.' + owner.qualname)
                    or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)):
                return None
            returns = _returns_input(analyzer, function, parameter)
        except _ClassEffectLimit:
            return None
        if returns is None:
            return None
        assumptions = observations['assumptions'] + ['source_class_decorator_return_identity',
            'normal_return_preserves_input_reference', 'class_decorator_effects_unmodeled']
        if factory is not None:
            assumptions += factory['assumptions']
        if resolution is not None:
            assumptions += resolution.extra_assumptions
            if resolution.receiver_class is not None:
                assumptions += ['source_callable_instance_class_binding',
                    'no_unmodeled_indirect_callable_instance_class_mutation']
        fact = {'kind': 'source_class_decoration_identity', 'status': 'source_bound',
            'receiver_class': asdict(ref), 'decorator': asdict(owner), 'parameter': parameter,
            'identity_status': 'preserved', 'body_effects': 'unmodeled',
            'completion': 'normal_return_only', 'runtime_identity_confirmed': False,
            'decorator_evidence': _span(ref, expression),
            'return_evidence': [_span(owner, node) for node in returns],
            'observation_guard': observations, 'source_hashes': dict(sorted(analyzer.hashes.items())),
            'assumptions': sorted(set(assumptions))}
        if factory is not None:
            fact['factory_binding'] = factory
        facts.append(fact)
    cache[ref] = facts
    return copy.deepcopy(facts)
