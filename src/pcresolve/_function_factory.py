## @package pcresolve._function_factory
#  Bounded source decorator factories over literal and native signature metadata.

import ast
import copy
import inspect
from dataclasses import dataclass, asdict

from ._class_partial import _namespace as functools_namespace
from ._function_metadata import fresh_function_wraps
from ._function_namespace import _plain_declaration
from ._function_observation import nonobserving_source
from ._property_namespace import _stable_builtin_namespace
from ._runtime_namespace import unmodified
from .program_facts import FunctionSignature, bind_ast_call
from .scope_facts import statement_scope_facts
from .class_attribute_effects import _ClassEffectLimit


class _OpenFactory(ValueError):
    pass


@dataclass(eq=False)
class _Function:
    node: object
    original: bool = False


@dataclass
class _Symbol:
    name: str


@dataclass
class _Partial:
    arguments: list
    keywords: dict


def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


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


def _signature(node):
    # These are host stdlib metadata objects built from AST, never inspect of a
    # loaded target function. No default/annotation source expression is run.
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


class _Factory:
    def __init__(self, analyzer, target, selected):
        self.analyzer, self.target, self.selected = analyzer, target, selected
        self.ref, self.source = selected
        self.remaining = 4000
        self.metadata, self.registry, self.functions = [], [], []
        self.captures = {}

    def charge(self):
        self.remaining -= 1
        self.analyzer._class_effect_fact_steps -= 1
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        if self.remaining < 0 or self.analyzer._class_effect_fact_steps < 0:
            raise _OpenFactory()

    def builtin(self, name):
        if self.analyzer._builtin_name_status(self.ref, self.source, name) != 'confirmed_builtin':
            raise _OpenFactory()

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


## Prove one literal source factory producing a native metadata wrapper function.
#  @param analyzer Fixed source snapshot; source expressions are interpreted, never run.
#  @param target Fresh source member with exactly one literal decorator factory call.
#  @return Namespace construction fact, or None outside the finite metadata grammar.
def factory_wrapper(analyzer, target):
    cache = analyzer._function_factory_cache
    key = (target[0], id(target[1]))
    if key not in cache:
        cache[key] = None
        cache[key] = (_matplotlib_keyword_only_wrapper(analyzer, target)
                      or _factory_wrapper(analyzer, target))
    return copy.deepcopy(cache[key])


def _same_ast(node, source):
    try:
        expected = ast.parse(source).body
    except SyntaxError:
        return False
    return (ast.dump(ast.Module(body=[node], type_ignores=[]), include_attributes=False)
            == ast.dump(ast.Module(body=expected, type_ignores=[]), include_attributes=False))


def _matplotlib_keyword_only_wrapper(analyzer, target):
    """Prove Matplotlib's source keyword-only decorator forwards the original call."""
    ref, member = target
    if (ref.module != 'matplotlib.patches' or not isinstance(member, ast.FunctionDef)
            or len(member.decorator_list) != 1):
        return None
    decorator, = member.decorator_list
    if (not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute)
            or decorator.func.attr != 'make_keyword_only'
            or not isinstance(decorator.func.value, ast.Name)
            or decorator.func.value.id != '_api' or len(decorator.args) != 1
            or not isinstance(decorator.args[0], ast.Constant)
            or type(decorator.args[0].value) is not str
            or len(decorator.keywords) != 1 or decorator.keywords[0].arg != 'name'
            or not isinstance(decorator.keywords[0].value, ast.Constant)
            or type(decorator.keywords[0].value.value) is not str):
        return None
    if analyzer.imports.get(ref.module, {}).get('_api') != 'matplotlib._api':
        return None
    factory_matches = analyzer._definition_index.find(
        'matplotlib._api.deprecation', 'make_keyword_only')
    if len(factory_matches) != 1:
        return None
    factory_ref, factory = factory_matches[0]
    if (not isinstance(factory, ast.FunctionDef) or factory.decorator_list
            or [arg.arg for arg in factory.args.args] != ['since', 'name', 'func']
            or factory.args.posonlyargs or factory.args.kwonlyargs
            or factory.args.vararg or factory.args.kwarg
            or len(factory.args.defaults) != 1
            or not isinstance(factory.args.defaults[0], ast.Constant)
            or factory.args.defaults[0].value is not None):
        return None
    body = [statement for statement in factory.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str))]
    wrappers = [statement for statement in body
                if isinstance(statement, ast.FunctionDef) and statement.name == 'wrapper']
    if (len(body) != 13 or len(wrappers) != 1
            or not _same_ast(body[0],
                'decorator = functools.partial(make_keyword_only, since, name)')
            or not _same_ast(body[1], 'if func is None:\n    return decorator')
            or not _same_ast(body[2], 'signature = inspect.signature(func)')
            or not _same_ast(body[6], 'names = [*signature.parameters]')
            or not _same_ast(body[7], 'name_idx = names.index(name)')
            or not isinstance(body[-1], ast.Return)
            or not isinstance(body[-1].value, ast.Name)
            or body[-1].value.id != 'wrapper'):
        return None
    wrapper, = wrappers
    if (len(wrapper.decorator_list) != 1
            or ast.unparse(wrapper.decorator_list[0]) != 'functools.wraps(func)'
            or wrapper.args.args or wrapper.args.posonlyargs or wrapper.args.kwonlyargs
            or not wrapper.args.vararg or wrapper.args.vararg.arg != 'args'
            or not wrapper.args.kwarg or wrapper.args.kwarg.arg != 'kwargs'):
        return None
    statements = [statement for statement in wrapper.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str))]
    if (len(statements) != 2 or not isinstance(statements[0], ast.If)
            or statements[0].orelse or len(statements[0].body) != 1
            or not isinstance(statements[0].body[0], ast.Expr)
            or not isinstance(statements[0].body[0].value, ast.Call)
            or not isinstance(statements[0].body[0].value.func, ast.Name)
            or statements[0].body[0].value.func.id != 'warn_deprecated'
            or not isinstance(statements[1], ast.Return)
            or not isinstance(statements[1].value, ast.Call)):
        return None
    guard = statements[0].test
    if (not isinstance(guard, ast.Compare) or len(guard.ops) != 1
            or not isinstance(guard.ops[0], ast.Gt) or len(guard.comparators) != 1
            or not isinstance(guard.left, ast.Call)
            or not isinstance(guard.left.func, ast.Name) or guard.left.func.id != 'len'
            or len(guard.left.args) != 1
            or not isinstance(guard.left.args[0], ast.Name)
            or guard.left.args[0].id != 'args'
            or guard.left.keywords
            or not isinstance(guard.comparators[0], ast.Name)
            or guard.comparators[0].id != 'name_idx'):
        return None
    forward = statements[1].value
    if (not isinstance(forward.func, ast.Name) or forward.func.id != 'func'
            or len(forward.args) != 1 or not isinstance(forward.args[0], ast.Starred)
            or not isinstance(forward.args[0].value, ast.Name)
            or forward.args[0].value.id != 'args'
            or len(forward.keywords) != 1 or forward.keywords[0].arg is not None
            or not isinstance(forward.keywords[0].value, ast.Name)
            or forward.keywords[0].value.id != 'kwargs'):
        return None
    if (not analyzer._stable_import_name('matplotlib._api.deprecation.make_keyword_only')
            or not functools_namespace(analyzer, ('partial', 'wraps'))
            or analyzer._builtin_name_status(factory_ref, factory, 'len') != 'confirmed_builtin'
            or analyzer.imports.get(factory_ref.module, {}).get('functools') != 'functools'):
        return None
    positional = member.args.posonlyargs + member.args.args
    name = decorator.keywords[0].value.value
    names = [argument.arg for argument in positional]
    if names.count(name) != 1:
        return None
    evidence = {'file_path': ref.file_path, 'lineno': wrapper.lineno,
                'col_offset': wrapper.col_offset, 'end_lineno': wrapper.end_lineno,
                'end_col_offset': wrapper.end_col_offset}
    forwarding = {'kind': 'source_wrapper_argument_forwarding',
        'forwarded_function': asdict(ref), 'maximum_positional_count': names.index(name),
        'other_paths': 'forwarded_on_normal_return',
        'normal_return_paths': 'all_explicit_returns_forward_original_args_kwargs',
        'argument_scope': 'same_args_and_kwargs',
        'call_evidence': {'file_path': factory_ref.file_path,
            'lineno': statements[1].lineno, 'col_offset': statements[1].col_offset,
            'end_lineno': statements[1].end_lineno,
            'end_col_offset': statements[1].end_col_offset}}
    return {'kind': 'source_matplotlib_keyword_only_wrapper', 'status': 'source_bound',
        'forwarded_function': asdict(ref), 'forwarding': forwarding,
        'wrapper_evidence': evidence,
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold',
            'standard_library_partial_protocol', 'standard_library_functools_wraps_protocol',
            'no_external_monkeypatch_or_import_hook',
            'source_wrapper_forwarding_on_normal_return']}


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
