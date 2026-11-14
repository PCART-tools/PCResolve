## @package pcresolve.flow.proofs.callables._function_factory
#  Bounded source decorator factories over literal and native signature metadata.
#  根据字面量和原生签名元数据有界分析源码装饰器工厂。

import ast
import copy
import inspect
from dataclasses import dataclass, asdict

from pcresolve.flow.proofs.classes._class_partial import _namespace as functools_namespace
from pcresolve.flow.proofs.callables._function_metadata import fresh_function_wraps
from pcresolve.flow.proofs.namespaces._function_namespace import _plain_declaration
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Signal that source-factory execution exceeds the supported static grammar.
## 表示源码工厂行为超出受支持的静态语法范围。
class _OpenFactory(ValueError):
    pass


## Represent a source function captured or constructed by a factory.
## 表示工厂捕获或构造的源码函数。
@dataclass(eq=False)
class _Function:
    node: object
    original: bool = False


## Represent a symbolic native name used during factory evaluation.
## 表示工厂求值期间使用的符号化原生名称。
@dataclass
class _Symbol:
    name: str


## Represent a bounded functools.partial construction.
## 表示有界的 functools.partial 构造结果。
@dataclass
class _Partial:
    arguments: list
    keywords: dict


## Capture source coordinates for a factory proof witness.
## 记录工厂证明证据的源码坐标。
#
#  @param ref Source definition reference.
#  @param node AST node supporting the witness.
#  @return File path and source coordinate mapping.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Resolve a local name or attribute through stable source imports.
## 通过稳定的源码导入解析局部名称或属性。
#
#  @param analyzer Source analyzer providing scopes and import facts.
#  @param ref Source definition reference containing the expression.
#  @param scope Lexical scope for local-shadowing checks.
#  @param node AST name or attribute expression.
#  @return Canonical dotted name, or an empty string when unresolved.
def _canonical(analyzer, ref, scope, node):
    if not isinstance(node, (ast.Name, ast.Attribute)):
        return ''
    name = ast.unparse(node)
    head, dot, rest = name.partition('.')
    bindings = (analyzer._scope_facts(scope).bound
                if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                else statement_scope_facts(scope.body).bound if isinstance(scope, ast.ClassDef)
                else set())
    if head in bindings:
        return ''
    imported = analyzer.imports.get(ref.module, {}).get(head, '')
    if imported and not analyzer._stable_import_name(ref.module + '.' + head):
        return ''
    return imported + (dot + rest if dot else '') if imported else ref.module + '.' + name


## Build a host inspect.Signature from syntax without loading target defaults.
## 根据语法构造宿主 inspect.Signature，不加载目标默认值。
#
#  @param node Source function AST node.
#  @return Native signature containing opaque placeholders for defaults.
def _signature(node):
    # These are host stdlib metadata objects built from AST, never inspect of a
    # loaded target function. No default/annotation source expression is run.
    # 这些宿主标准库元数据对象仅由 AST 构造，不检查已加载目标函数，也不运行默认值或注解表达式。
    args = node.args
    parameters = []
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for index, (arg, default) in enumerate(zip(positional, defaults)):
        kind = (inspect.Parameter.POSITIONAL_ONLY if index < len(args.posonlyargs)
                else inspect.Parameter.POSITIONAL_OR_KEYWORD)
        parameters.append(inspect.Parameter(arg.arg, kind, default=(
            inspect.Parameter.empty if default is None else object())))
    if args.vararg:
        parameters.append(inspect.Parameter(args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    parameters.extend(inspect.Parameter(arg.arg, inspect.Parameter.KEYWORD_ONLY,
        default=inspect.Parameter.empty if default is None else object())
        for arg, default in zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        parameters.append(inspect.Parameter(args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    return inspect.Signature(parameters)


## Prove inspect.Signature and Parameter bindings remain unmodified and unobserved.
## 证明 inspect.Signature 与 Parameter 绑定未被修改或动态观察。
#
#  @param analyzer Source analyzer with module bodies and stable imports.
#  @return True only when all protected metadata bindings are safe.
def _signature_namespace(analyzer):
    cached = analyzer._signature_factory_namespace
    if cached is not None:
        return cached
    analyzer._signature_factory_namespace = False
    if 'inspect' in analyzer.module_bodies:
        return False
    protected = {'inspect.signature', 'inspect.Signature', 'inspect.Parameter'}
    inspected = 0
    for module, bodies in analyzer.module_bodies.items():
        aliases = {name: value for name, value in analyzer.imports.get(module, {}).items()
                   if value == 'inspect' or value in protected}
        if any(not analyzer._stable_import_name(module + '.' + name) for name in aliases):
            return False
        for _, body in bodies:
            parents, nodes = {}, []
            for statement in body:
                for node in ast.walk(statement):
                    inspected += 1
                    if inspected > 10_000_000:
                        return False
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    parents.update((child, node) for child in ast.iter_child_nodes(node))
            for node in nodes:
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'inspect'
                        and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                             or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module')):
                    return False
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                current, name = node, aliases[node.id]
                if not isinstance(node.ctx, ast.Load):
                    return False
                if name == 'inspect':
                    current = parents.get(node)
                    if (not isinstance(current, ast.Attribute) or current.value is not node
                            or current.attr.startswith('__')):
                        return False
                    name += '.' + current.attr
                if name not in protected:
                    continue
                use = parents.get(current)
                if not isinstance(current.ctx, ast.Load):
                    return False
                if isinstance(use, ast.Call) and use.func is current:
                    continue
                if (name in ('inspect.Parameter', 'inspect.Signature') and isinstance(use, ast.Attribute)
                        and isinstance(use.ctx, ast.Load) and use.attr in (
                            'POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD', 'VAR_POSITIONAL',
                            'KEYWORD_ONLY', 'VAR_KEYWORD', 'empty')):
                    continue
                return False
    if any(not unmodified(analyzer, name) for name in protected):
        return False
    analyzer._signature_factory_namespace = True
    return True


## Interpret a restricted decorator-factory body using native metadata objects.
## 使用原生元数据对象解释受限的装饰器工厂函数体。
class _Factory:
    ## Initialize the selected factory and its bounded evaluation state.
    ## 初始化选中的工厂及其有界求值状态。
    #
    #  @param self Factory evaluator state.
    #  @param analyzer Source analyzer with snapshot and analysis budgets.
    #  @param target Decorated function whose factory result is being checked.
    #  @param selected Resolved source factory owner and function pair.
    #  @return None.
    def __init__(self, analyzer, target, selected):
        self.analyzer, self.target, self.selected = analyzer, target, selected
        self.ref, self.source = selected
        self.remaining = 4000
        self.metadata, self.registry, self.functions = [], [], []
        self.captures = {}

    ## Consume local and shared node budgets before interpreting more syntax.
    ## 在解释更多语法前消耗局部和共享节点预算。
    #
    #  @param self Factory evaluator state.
    #  @return None; raises _OpenFactory when either budget is exhausted.
    def charge(self):
        self.remaining -= 1
        self.analyzer._class_effect_fact_steps -= 1
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        if self.remaining < 0 or self.analyzer._class_effect_fact_steps < 0:
            raise _OpenFactory()

    ## Require the selected name to resolve to an unshadowed builtin.
    ## 要求指定名称解析为未被遮蔽的内建函数。
    #
    #  @param self Factory evaluator state.
    #  @param name Builtin identifier to validate.
    #  @return None; raises _OpenFactory when identity is not confirmed.
    def builtin(self, name):
        if self.analyzer._builtin_name_status(self.ref, self.source, name) != 'confirmed_builtin':
            raise _OpenFactory()

    ## Evaluate one expression from the finite factory metadata grammar.
    ## 计算有限工厂元数据语法中的一个表达式。
    #
    #  @param self Factory evaluator and evidence collector.
    #  @param node Expression AST node.
    #  @param env Current symbolic factory environment.
    #  @return Evaluated native or symbolic value; unsupported syntax raises _OpenFactory.
    def evaluate(self, node, env):
        self.charge()
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool, float, type(None)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            if node.id == self.source.name:
                return _Symbol('$factory')
            canonical = _canonical(self.analyzer, self.ref, self.source, node)
            if canonical in ('inspect', 'inspect.signature', 'inspect.Parameter',
                              'functools', 'functools.partial'):
                if not unmodified(self.analyzer, canonical):
                    raise _OpenFactory()
                return _Symbol(canonical)
            raise _OpenFactory()
        if isinstance(node, ast.Attribute):
            value = self.evaluate(node.value, env)
            if isinstance(value, _Symbol):
                name = value.name + '.' + node.attr
                if name in ('inspect.signature', 'inspect.Parameter', 'functools.partial'):
                    if not unmodified(self.analyzer, name):
                        raise _OpenFactory()
                    return _Symbol(name)
                if value.name == 'inspect.Parameter' and node.attr in (
                        'POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD', 'KEYWORD_ONLY',
                        'VAR_POSITIONAL', 'VAR_KEYWORD'):
                    return getattr(inspect.Parameter, node.attr)
            if isinstance(value, inspect.Signature) and node.attr == 'parameters':
                return dict(value.parameters)
            if isinstance(value, inspect.Parameter) and node.attr in ('kind', 'name'):
                return getattr(value, node.attr)
            raise _OpenFactory()
        if isinstance(node, (ast.List, ast.Tuple)):
            result = []
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    sequence = self.evaluate(item.value, env)
                    if not isinstance(sequence, (list, tuple, dict)):
                        raise _OpenFactory()
                    result.extend(sequence)
                else:
                    result.append(self.evaluate(item, env))
            if len(result) > 128:
                raise _OpenFactory()
            return result if isinstance(node, ast.List) else tuple(result)
        if isinstance(node, ast.Subscript):
            container = self.evaluate(node.value, env)
            if not isinstance(container, (list, tuple, dict, str)):
                raise _OpenFactory()
            if isinstance(node.slice, ast.Slice):
                index = slice(*(self.evaluate(value, env) if value is not None else None
                                for value in (node.slice.lower, node.slice.upper, node.slice.step)))
            else:
                index = self.evaluate(node.slice, env)
            return container[index]
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = self.evaluate(node.left, env), self.evaluate(node.comparators[0], env)
            operation = node.ops[0]
            if isinstance(operation, ast.Is):
                return left is right
            if isinstance(operation, ast.IsNot):
                return left is not right
            if isinstance(operation, ast.Eq):
                return left == right
            if isinstance(operation, ast.NotEq):
                return left != right
            if isinstance(operation, (ast.In, ast.NotIn)) and isinstance(right, (str, list, tuple, dict)):
                return (left in right) == isinstance(operation, ast.In)
            raise _OpenFactory()
        if isinstance(node, ast.BoolOp):
            for operand in node.values:
                value = self.evaluate(operand, env)
                if isinstance(value, (_Function, _Symbol, _Partial)):
                    raise _OpenFactory()
                if isinstance(node.op, ast.And) and not value or isinstance(node.op, ast.Or) and value:
                    return value
            return value
        if isinstance(node, ast.IfExp):
            return self.evaluate(node.body if self.evaluate(node.test, env) else node.orelse, env)
        if isinstance(node, ast.ListComp) and len(node.generators) == 1:
            generator = node.generators[0]
            if generator.is_async or not isinstance(generator.target, ast.Name):
                raise _OpenFactory()
            sequence = self.evaluate(generator.iter, env)
            if not isinstance(sequence, (list, tuple, dict)) or len(sequence) > 128:
                raise _OpenFactory()
            result = []
            for value in sequence:
                local = dict(env, **{generator.target.id: value})
                if all(self.evaluate(condition, local) for condition in generator.ifs):
                    result.append(self.evaluate(node.elt, local))
            return result
        if isinstance(node, ast.Call):
            if any(isinstance(arg, ast.Starred) for arg in node.args) or any(
                    keyword.arg is None for keyword in node.keywords):
                raise _OpenFactory()
            arguments = [self.evaluate(arg, env) for arg in node.args]
            keywords = {keyword.arg: self.evaluate(keyword.value, env) for keyword in node.keywords}
            if isinstance(node.func, ast.Name) and node.func.id == 'len':
                self.builtin('len')
                if len(arguments) == 1 and not keywords and isinstance(arguments[0], (list, tuple, dict, str)):
                    return len(arguments[0])
                raise _OpenFactory()
            if isinstance(node.func, ast.Attribute) and node.func.attr in ('index', 'values', 'replace'):
                receiver = self.evaluate(node.func.value, env)
                if node.func.attr == 'index' and isinstance(receiver, list) and len(arguments) == 1 and not keywords:
                    return receiver.index(arguments[0])
                if node.func.attr == 'values' and isinstance(receiver, dict) and not arguments and not keywords:
                    return list(receiver.values())
                if node.func.attr == 'replace' and not arguments:
                    if isinstance(receiver, inspect.Parameter) and set(keywords) == {'kind'}:
                        return receiver.replace(kind=keywords['kind'])
                    if isinstance(receiver, inspect.Signature) and set(keywords) == {'parameters'}:
                        return receiver.replace(parameters=keywords['parameters'])
                raise _OpenFactory()
            callee = self.evaluate(node.func, env)
            if isinstance(callee, _Symbol) and callee.name == 'functools.partial':
                if not arguments or arguments[0] != _Symbol('$factory'):
                    raise _OpenFactory()
                return _Partial(arguments[1:], keywords)
            if isinstance(callee, _Symbol) and callee.name == 'inspect.signature':
                if len(arguments) != 1 or keywords or not isinstance(arguments[0], _Function):
                    raise _OpenFactory()
                if not arguments[0].original:
                    raise _OpenFactory()
                return _signature(arguments[0].node)
            raise _OpenFactory()
        raise _OpenFactory()

    ## Execute a factory statement block in the restricted symbolic environment.
    ## 在受限符号环境中解释工厂语句块。
    #
    #  @param self Factory evaluator collecting wrappers and registry effects.
    #  @param statements Ordered source statements to interpret.
    #  @param env Mutable symbolic environment.
    #  @return Explicit return value, or None after normal fallthrough.
    def block(self, statements, env):
        for statement in statements:
            self.charge()
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and type(
                    statement.value.value) is str:
                continue
            if isinstance(statement, ast.If):
                result = self.block(statement.body if self.evaluate(statement.test, env)
                                    else statement.orelse, env)
                if result is not None:
                    return result
            elif isinstance(statement, ast.Assert):
                if not self.evaluate(statement.test, env):
                    raise _OpenFactory()
            elif isinstance(statement, ast.FunctionDef):
                if not _plain_declaration(statement) or len(statement.decorator_list) != 1:
                    raise _OpenFactory()
                premise = fresh_function_wraps(self.analyzer, self.ref, (self.source,),
                    statement.decorator_list[0], lambda name: isinstance(env.get(name), _Function)
                    and env[name].original)
                if premise is None:
                    raise _OpenFactory()
                self.metadata.append(premise)
                env[statement.name] = _Function(statement)
                self.functions.append(statement)
                self.captures[statement] = dict(env)
            elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                value = self.evaluate(statement.value, env)
                destination = statement.targets[0]
                if isinstance(destination, ast.Name):
                    env[destination.id] = value
                elif isinstance(destination, ast.Attribute) and isinstance(destination.value, ast.Name):
                    receiver = env.get(destination.value.id)
                    if not isinstance(receiver, _Function) or receiver.original:
                        raise _OpenFactory()
                    if destination.attr == '__signature__' and isinstance(value, inspect.Signature):
                        pass
                    elif destination.attr.startswith('__') or type(value) not in (str, int, bool, float, type(None)):
                        raise _OpenFactory()
                elif isinstance(destination, ast.Subscript) and isinstance(destination.value, ast.Name):
                    key = self.evaluate(destination.slice, env)
                    if (not isinstance(key, _Function) or key.original or not isinstance(value, _Partial)
                            or not self.registry_binding(destination.value.id)):
                        raise _OpenFactory()
                    self.registry.append({'object_kind': 'source_builtin_dict',
                        'name': self.ref.module + '.' + destination.value.id,
                        'key_kind': 'native_function', 'evidence': _span(self.ref, statement)})
                else:
                    raise _OpenFactory()
            elif isinstance(statement, ast.Return):
                return self.evaluate(statement.value, env)
            elif not isinstance(statement, ast.Pass):
                raise _OpenFactory()
        return None

    ## Confirm a module dictionary is a closed native-function registry.
    ## 确认模块字典是仅保存原生函数的封闭注册表。
    #
    #  @param self Factory evaluator with module import and binding facts.
    #  @param name Module-level registry variable name.
    #  @return True when all registry writes and reads match the supported protocol.
    def registry_binding(self, name):
        qualified = self.ref.module + '.' + name
        if (not unmodified(self.analyzer, qualified)
                or name in self.analyzer._scope_facts(self.source).bound):
            return False
        declarations = [statement for _, body in self.analyzer.module_bodies.get(self.ref.module, ())
            for statement in body if name in statement_scope_facts([statement]).bound]
        if (len(declarations) != 1 or not isinstance(declarations[0], ast.Assign)
                or len(declarations[0].targets) != 1 or not isinstance(declarations[0].targets[0], ast.Name)
                or not isinstance(declarations[0].value, ast.Dict) or declarations[0].value.keys):
            return False
        inspected = 0
        for module, bodies in self.analyzer.module_bodies.items():
            for path, body in bodies:
                parents, scopes, pending = {}, {}, [(statement, None) for statement in body]
                while pending:
                    node, scope = pending.pop()
                    inspected += 1
                    if inspected > 1000000:
                        return False
                    if self.analyzer._analysis_budget is not None:
                        self.analyzer._analysis_budget.checkpoint()
                    scopes[node] = scope
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
                        pending.append((child, node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                     ast.ClassDef, ast.Lambda)) else scope))
                for node, scope in scopes.items():
                    if not isinstance(node, (ast.Name, ast.Attribute)):
                        continue
                    ref = type(self.ref)(module, '<namespace>', path)
                    # The module initialization store is the only bound name
                    # permitted; runtime aliases would expose arbitrary keys.
                    if node is declarations[0].targets[0]:
                        continue
                    if _canonical(self.analyzer, ref, scope, node) != qualified:
                        continue
                    use = parents.get(node)
                    if isinstance(use, ast.Subscript) and isinstance(use.ctx, ast.Store):
                        if not isinstance(scope, ast.FunctionDef) or not isinstance(use.slice, ast.Name):
                            return False
                        key = use.slice.id
                        bindings = [item for item in scope.body if key in statement_scope_facts([item]).bound]
                        if (len(bindings) != 1 or not isinstance(bindings[0], ast.FunctionDef)
                                or bindings[0].name != key or len(bindings[0].decorator_list) != 1):
                            return False
                        # Only standard wraps can change the fresh key before
                        # insertion, and it still returns that native function.
                        scope_ref = type(self.ref)(module, scope.name, path)
                        if fresh_function_wraps(self.analyzer, scope_ref, (scope,),
                                bindings[0].decorator_list[0], lambda value: value in {
                                    arg.arg for arg in scope.args.posonlyargs + scope.args.args}) is None:
                            return False
                    elif (isinstance(use, ast.Attribute) and use.attr == 'get'
                            and isinstance(parents.get(use), ast.Call) and parents[use].func is use):
                        continue
                    else:
                        return False
        return True


## Prove a wrapper forwards its original positional and keyword arguments.
## 证明包装函数转发原始位置参数与关键字参数。
#
#  @param wrapper Constructed wrapper function AST node.
#  @param captures Symbolic values captured by the wrapper.
#  @param target Original function source reference and node.
#  @param ref Factory source reference for evidence locations.
#  @return Forwarding fact, or None when any path changes the arguments.
def _forwarding(wrapper, captures, target, ref):
    args = wrapper.args
    if args.posonlyargs or args.args or args.kwonlyargs or not args.vararg or not args.kwarg:
        return None
    maximum = None
    if (wrapper.body and isinstance(wrapper.body[0], ast.If)
            and not wrapper.body[0].orelse):
        test = wrapper.body[0].test
        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt) and len(test.comparators) == 1
                and isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Name)
                and test.left.func.id == 'len' and not test.left.keywords
                and len(test.left.args) == 1 and isinstance(test.left.args[0], ast.Name)
                and test.left.args[0].id == args.vararg.arg
                and isinstance(test.comparators[0], ast.Name)
                and test.comparators[0].id not in (args.vararg.arg, args.kwarg.arg)
                and type(captures.get(test.comparators[0].id)) is int):
            maximum = captures[test.comparators[0].id]
    parents = {child: parent for parent in ast.walk(wrapper)
               for child in ast.iter_child_nodes(parent)}

    ## Match a call that forwards the wrapper's original *args and **kwargs.
    ## 匹配转发包装函数原始 *args 和 **kwargs 的调用。
    #
    #  @param call Candidate return call expression.
    #  @return True when the call preserves both argument collections.
    def direct_forward(call):
        forwarded = captures.get(call.func.id) if isinstance(call.func, ast.Name) else None
        return (isinstance(forwarded, _Function) and forwarded.original
                and call.func.id not in (args.vararg.arg, args.kwarg.arg)
                and len(call.args) == 1 and isinstance(call.args[0], ast.Starred)
                and isinstance(call.args[0].value, ast.Name)
                and call.args[0].value.id == args.vararg.arg
                and len(call.keywords) == 1 and call.keywords[0].arg is None
                and isinstance(call.keywords[0].value, ast.Name)
                and call.keywords[0].value.id == args.kwarg.arg)

    returns = []

    ## Gather explicit returns without descending into nested definitions.
    ## 收集显式返回语句，但不进入嵌套定义。
    #
    #  @param node AST subtree whose return statements are collected.
    #  @return None; appends eligible return nodes to the enclosing list.
    def collect_returns(node):
        if node is not wrapper and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                      ast.Lambda, ast.ClassDef)):
            return
        if isinstance(node, ast.Return):
            returns.append(node)
        for child in ast.iter_child_nodes(node):
            collect_returns(child)

    collect_returns(wrapper)
    if not returns or any(not isinstance(node.value, ast.Call) or not direct_forward(node.value)
                          for node in returns):
        return None

    forward_calls = {node.value for node in returns}
    for node in ast.walk(wrapper):
        if not isinstance(node, ast.Name) or node.id not in (args.vararg.arg, args.kwarg.arg):
            continue
        if not isinstance(node.ctx, ast.Load):
            return None
        parent = parents.get(node)
        if (node.id == args.vararg.arg and isinstance(parent, ast.Call)
                and isinstance(parent.func, ast.Name) and parent.func.id == 'len'):
            if parent.args != [node] or parent.keywords:
                return None
            continue
        if isinstance(parent, ast.Starred) and isinstance(parents.get(parent), ast.Call):
            call = parents[parent]
            if call in forward_calls:
                continue
            if (isinstance(call.func, ast.Attribute) and call.func.attr == 'bind'
                    and call.args.count(parent) == 1 and len(call.keywords) == 1
                    and call.keywords[0].arg is None
                    and isinstance(call.keywords[0].value, ast.Name)
                    and call.keywords[0].value.id == args.kwarg.arg):
                continue
        if node.id == args.kwarg.arg and isinstance(parent, ast.keyword) and parent.arg is None:
            call = parents.get(parent)
            if call in forward_calls:
                continue
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == 'bind' and len(call.args) == 1
                    and isinstance(call.args[0], ast.Starred)
                    and isinstance(call.args[0].value, ast.Name)
                    and call.args[0].value.id == args.vararg.arg):
                continue
        if (node.id == args.kwarg.arg and isinstance(parent, ast.Compare)
                    and len(parent.comparators) == 1 and parent.comparators[0] is node
                    and len(parent.ops) == 1
                and isinstance(parent.ops[0], (ast.In, ast.NotIn))):
            continue
        return None

    return {'kind': 'source_wrapper_argument_forwarding', 'forwarded_function': asdict(target[0]),
            'maximum_positional_count': maximum,
            'other_paths': 'forwarded_on_normal_return',
            'normal_return_paths': 'all_explicit_returns_forward_original_args_kwargs',
            'argument_scope': 'same_args_and_kwargs',
            'call_evidence': _span(ref, returns[-1].value)}


## Prove one literal source factory produces a native metadata wrapper function.
## 证明字面量源码工厂会构造原生元数据包装函数。
#
#  @param analyzer Fixed source snapshot; source expressions are interpreted, never run.
#  @param target Fresh source member with exactly one literal decorator factory call.
#  @return Namespace construction fact, or None outside the finite metadata grammar.
## Return the cached wrapper-factory proof for an exact source member.
## 返回指定源码成员的缓存包装工厂证明。
#
#  @param analyzer Source analyzer with factory proof cache.
#  @param target Exact decorated function source reference and AST node.
#  @return Deep-copied wrapper construction fact, or None when unsupported.
def factory_wrapper(analyzer, target):
    cache = analyzer._function_factory_cache
    key = (target[0], id(target[1]))
    if key not in cache:
        cache[key] = None
        cache[key] = _factory_wrapper(analyzer, target)
    return copy.deepcopy(cache[key])


## Verify and summarize one supported literal decorator-factory construction.
## 验证并汇总一个受支持的字面量装饰器工厂构造。
#
#  @param analyzer Source analyzer providing definitions and namespace proofs.
#  @param target Exact decorated function source reference and AST node.
#  @return Source-bound construction fact, or None when proof is incomplete.
def _factory_wrapper(analyzer, target):
    ref, member = target
    if (analyzer.index_boundaries or not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], ast.Call)):
        return None
    expression = member.decorator_list[0]
    probe = copy.copy(member)
    probe.decorator_list = [expression.func]
    selected = analyzer._decorator_definition((ref, probe))
    if selected is None:
        return None
    owner, factory = selected
    if (not isinstance(factory, ast.FunctionDef) or '.' in owner.qualname or factory.decorator_list
            or factory.args.vararg or factory.args.kwarg or factory.args.kwonlyargs
            or factory.returns is not None or any(arg.annotation for arg in factory.args.posonlyargs + factory.args.args)
            or analyzer._scope_facts(factory).globals or analyzer._scope_facts(factory).nonlocals
            or not unmodified(analyzer, owner.module + '.' + owner.qualname)
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)):
        return None
    if not _signature_namespace(analyzer):
        return None
    try:
        if (not functools_namespace(analyzer, ('partial', 'wraps', 'update_wrapper',
                                              'WRAPPER_ASSIGNMENTS', 'WRAPPER_UPDATES'))
                or nonobserving_source(analyzer) is None):
            return None
        stable, _ = _stable_builtin_namespace(analyzer, owner, ('len', 'getattr', 'setattr', 'AttributeError'))
        if not stable:
            return None
        count = 0
        for _ in ast.walk(factory):
            count += 1
            if count > 2000:
                return None
        proof = _Factory(analyzer, target, selected)
        signature = FunctionSignature.from_ast(factory.args)
        records, reasons = bind_ast_call(expression, signature)
        if reasons or any(record['status'] != 'exact' for record in records):
            return None
        env = {name: ast.literal_eval(default) for name, default in signature.defaults}
        for record in records:
            node = record['node']
            if not isinstance(node, ast.Constant) or type(node.value) not in (str, int, bool, float, type(None)):
                return None
            env[record['parameter']] = node.value
        partial = proof.block(factory.body, dict(env))
        if not isinstance(partial, _Partial):
            return None
        parameters = factory.args.posonlyargs + factory.args.args
        bound = dict(partial.keywords)
        if len(partial.arguments) + 1 > len(parameters):
            return None
        for argument, value in zip(parameters, partial.arguments + [_Function(member, True)]):
            if argument.arg in bound:
                return None
            bound[argument.arg] = value
        second = {name: ast.literal_eval(default) for name, default in signature.defaults}
        second.update(bound)
        if set(second) != {arg.arg for arg in parameters}:
            return None
        result = proof.block(factory.body, second)
        if not isinstance(result, _Function) or result.original or result.node not in proof.functions:
            return None
        observations = nonobserving_source(analyzer)
        fact = {'kind': 'source_function_factory_wrapper_creation', 'status': 'source_bound',
            'function': asdict(ref), 'factory': asdict(owner), 'result_kind': 'native_function',
            'body_binding_status': 'unmodeled', 'identity_status': 'replaced',
            'completion': 'normal_return_only', 'runtime_factory_executed': False,
            'factory_evidence': _span(ref, expression), 'wrapper_evidence': _span(owner, result.node),
            'metadata_wrappers': proof.metadata, 'registry_writes': proof.registry,
            'observation_guard': observations, 'source_hashes': dict(sorted(analyzer.hashes.items())),
            'assumptions': sorted(set(observations['assumptions'] + [
                'source_native_function_wrapper_creation', 'standard_library_signature_metadata_protocol',
                'standard_library_partial_protocol', 'standard_library_default_wraps_metadata_protocol',
                'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
                'source_registry_native_function_keys_only', 'no_external_registry_mutation']))}
        forwarding = _forwarding(result.node, second, target, owner)
        if (forwarding is not None and not analyzer._scope_facts(result.node).nonlocals
                and 'len' not in analyzer._scope_facts(factory).bound and analyzer._builtin_name_status(
                owner, result.node, 'len') == 'confirmed_builtin'):
            fact['forwarding'] = forwarding
        return fact
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, _ClassEffectLimit):
        return None
