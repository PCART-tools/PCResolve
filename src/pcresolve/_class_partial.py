## @package pcresolve._class_partial
#  Literal partial-application bindings used by source class decorators.

import ast
import copy
import math
from dataclasses import asdict

from .import_facts import import_facts
from .class_attribute_effects import _ClassEffectLimit
from ._property_namespace import _stable_builtin_namespace
from .effect_facts import contains_yield
from .syntax_facts import SyntaxLimit


def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
            'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}


def _literal(node):
    if sum(1 for _ in ast.walk(node)) > 128 or any(isinstance(item, ast.Call) for item in ast.walk(node)):
        return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, RecursionError):
        return None

    def encode(item, depth=0):
        if depth > 8:
            raise ValueError()
        if type(item) in (str, int, bool, float, type(None)):
            if type(item) is float and not math.isfinite(item):
                raise ValueError()
            return item
        if type(item) in (list, tuple) and len(item) <= 64:
            return [encode(value, depth + 1) for value in item]
        if type(item) is dict and len(item) <= 64 and all(type(key) is str for key in item):
            return {'kind': 'dict', 'items': [[key, encode(value, depth + 1)]
                                             for key, value in item.items()]}
        raise ValueError()
    try:
        return {'type': type(value).__name__, 'value': encode(value)}
    except ValueError:
        return None


def _readonly_type_test(analyzer, module, value, use, parents):
    if (not isinstance(use, ast.Call) or not isinstance(use.func, ast.Name)
            or use.func.id != 'isinstance' or len(use.args) != 2 or use.keywords
            or use.args[1] is not value):
        return False
    current, names, scope = use, [], None
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return False
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if scope is None:
                scope = current
            names.append(current.name)
    matches = analyzer._definition_index.find(module, '.'.join(reversed(names)))
    if (not isinstance(scope, ast.FunctionDef) or len(matches) != 1 or matches[0][1] is not scope
            or analyzer._builtin_name_status(matches[0][0], scope, 'isinstance') != 'confirmed_builtin'):
        return False
    try:
        stable, _ = _stable_builtin_namespace(analyzer, matches[0][0], ('isinstance',))
    except _ClassEffectLimit:
        return False
    return stable


def _namespace(analyzer, protected=('partial',)):
    key = tuple(sorted(protected))
    protected_names = {'functools.' + name for name in protected}
    cache = getattr(analyzer, '_partial_class_namespace_premise', None)
    cache = cache if isinstance(cache, dict) else {}
    if key in cache:
        return cache[key]
    stable, count = 'functools' not in analyzer.module_bodies, 0
    for module, bodies in analyzer.module_bodies.items():
        for _, body in bodies:
            try:
                syntax = analyzer._syntax_facts(body, 1000000 - count)
            except SyntaxLimit:
                cache[key] = False
                analyzer._partial_class_namespace_premise = cache
                return False
            aliases = {}
            if syntax is None:
                nodes, parents, imports = [], {}, []
                for statement in body:
                    for node in ast.walk(statement):
                        count += 1
                        if count > 1000000:
                            cache[key] = False
                            analyzer._partial_class_namespace_premise = cache
                            return False
                        analyzer._analysis_budget.checkpoint()
                        nodes.append(node)
                        parents.update((child, node) for child in ast.iter_child_nodes(node))
                        imports.extend(import_facts(node))
            else:
                nodes, parents, imports = syntax.nodes, syntax.parents, syntax.imports
                count += len(nodes)
            for fact in imports:
                if fact.kind == 'import' and fact.name == 'functools':
                    aliases[fact.python_binding] = 'functools'
                elif fact.kind == 'from' and fact.module == 'functools' and not fact.level:
                    if fact.name in protected or fact.name == '*':
                        aliases[fact.python_binding] = 'functools.' + fact.name
            for name in aliases:
                if not analyzer._stable_import_name(module + '.' + name):
                    stable = False
            for node in nodes:
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'functools'
                        and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                             or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module')):
                    stable = False
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                current, canonical = node, aliases[node.id]
                if not isinstance(node.ctx, ast.Load) or canonical.endswith('.*'):
                    stable = False
                if canonical == 'functools':
                    current = parents.get(node)
                    if not isinstance(current, ast.Attribute) or current.value is not node:
                        stable = False
                        continue
                    if current.attr.startswith('__'):
                        stable = False
                    canonical += '.' + current.attr
                if canonical in protected_names:
                    use = parents.get(current)
                    constant = canonical in ('functools.WRAPPER_ASSIGNMENTS', 'functools.WRAPPER_UPDATES')
                    if not isinstance(current.ctx, ast.Load) or not (constant or
                            isinstance(use, ast.Call) and use.func is current
                            or canonical == 'functools.partial'
                            and _readonly_type_test(analyzer, module, current, use, parents)):
                        stable = False
    cache[key] = stable
    analyzer._partial_class_namespace_premise = cache
    return stable


## Bind a literal factory returning a standard partial of its own source function.
#  @param analyzer Fixed source definitions and import bindings; nothing is imported.
#  @param target Decorated source class reference and AST.
#  @param expression Source decorator invocation with literal factory inputs.
#  @return Function/late-class parameter/string captures/premise, or None.
def bind_partial(analyzer, target, expression):
    if (not isinstance(expression, ast.Call) or expression.keywords
            or not 1 <= len(expression.args) <= 7 or analyzer.index_boundaries):
        return None
    ref, cls = target
    probe = copy.copy(cls)
    probe.decorator_list = [expression.func]
    selected = analyzer._decorator_definition((ref, probe))
    if selected is None or not isinstance(selected[1], ast.FunctionDef):
        return None
    owner, function = selected
    if contains_yield(function):
        return None
    args = function.args
    parameters = args.posonlyargs + args.args
    if ('.' in owner.qualname or len(parameters) != len(expression.args) + 1
            or args.vararg or args.kwarg or args.kwonlyargs or len(args.defaults) != 1
            or not isinstance(args.defaults[0], ast.Constant) or args.defaults[0].value is not None
            or function.returns is not None or any(parameter.annotation for parameter in parameters)
            or function.name in analyzer._scope_facts(function).bound
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)):
        return None
    nodes = list(ast.walk(function))
    if len(nodes) > 2000:
        return None
    if analyzer._analysis_budget is not None:
        analyzer._analysis_budget.checkpoint(force=True)
    body = [statement for statement in function.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and type(statement.value.value) is str)]
    parameter = parameters[-1].arg
    if (len(body) < 2 or not isinstance(body[0], ast.If) or body[0].orelse
            or len(body[0].body) != 1 or not isinstance(body[0].body[0], ast.Return)):
        return None
    guard = body[0].test
    if (not isinstance(guard, ast.Compare) or len(guard.ops) != 1
            or not isinstance(guard.ops[0], ast.Is) or not isinstance(guard.left, ast.Name)
            or guard.left.id != parameter or len(guard.comparators) != 1
            or not isinstance(guard.comparators[0], ast.Constant)
            or guard.comparators[0].value is not None):
        return None
    partial = body[0].body[0].value
    if (not isinstance(partial, ast.Call) or partial.keywords
            or len(partial.args) != len(parameters)
            or not isinstance(partial.func, (ast.Name, ast.Attribute))
            or not isinstance(partial.args[0], ast.Name) or partial.args[0].id != function.name
            or any(not isinstance(value, ast.Name) or value.id != argument.arg
                   for value, argument in zip(partial.args[1:], parameters[:-1]))):
        return None
    head, dot, rest = ast.unparse(partial.func).partition('.')
    canonical = analyzer.imports.get(owner.module, {}).get(head, '') + (dot + rest if dot else '')
    if (canonical != 'functools.partial' or head in analyzer._scope_facts(function).bound
            or not analyzer._stable_import_name(owner.module + '.' + head) or not _namespace(analyzer)):
        return None
    literals = [_literal(value) for value in expression.args]
    if any(value is None for value in literals):
        return None
    specialized = copy.copy(function)
    specialized.body = body[1:]
    records = [{'parameter': argument.arg, 'position': index,
                'value': literal['value'] if literal['type'] == 'dict'
                         else {'kind': literal['type'], 'value': literal['value']},
                'evidence': _span(ref, expression.args[index])}
               for index, (argument, literal) in enumerate(zip(parameters, literals))]
    premise = {'kind': 'source_partial_class_decorator', 'status': 'source_bound',
        'basis': 'source_snapshot', 'function': asdict(owner), 'class_parameter': parameter,
        'completion': 'normal_factory_return_only', 'runtime_factory_executed': False,
        'arguments': records, 'factory_evidence': _span(ref, expression),
        'partial_evidence': _span(owner, partial),
        'source_hashes': dict(sorted(analyzer.hashes.items())),
        'assumptions': ['source_snapshot_bindings_hold', 'standard_library_partial_protocol',
                        'standard_builtin_namespace_preserved',
                        'no_unmodeled_indirect_builtin_mutation',
                        'no_external_monkeypatch_or_import_hook',
                        'no_unmodeled_indirect_module_mutation']}
    strings = {argument.arg: literal['value'] for argument, literal in zip(parameters, literals)
               if literal['type'] == 'str'}
    return (owner, specialized), parameter, strings, premise
