## @package pcresolve.conditional_constructor
#  Signature references under explicit lookup requirements, never body bindings.

import ast
import copy
from itertools import islice

from .scope_facts import statement_scope_facts

_LIMIT = 2000
_TYPING = {'Any', 'Optional', 'Union', 'Dict', 'List', 'Tuple', 'Set', 'FrozenSet',
           'Callable', 'Awaitable', 'Type', 'Mapping', 'Sequence', 'Iterable'}
_SCALARS = {'str', 'bytes', 'int', 'float', 'bool', 'object'}


## Whether a plain source entry has a bounded constructor type-check query shape.
#  @param node Source entry AST; generic parameter-driven class queries are excluded.
#  @return True for a plain function containing a named isinstance class argument.
def supports_entry(node):
    if not isinstance(node, ast.FunctionDef) or node.decorator_list:
        return False
    nodes = list(islice(ast.walk(node), _LIMIT + 1))
    return len(nodes) <= _LIMIT and any(
        isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
        and item.func.id == 'isinstance' and len(item.args) == 2
        and isinstance(item.args[1], ast.Name) and not item.keywords for item in nodes)


def _namespace(summary, owner, cls):
    analyzer = summary.analyzer
    shadowed, properties = set(), set()

    def builtin(name):
        return (name not in shadowed and analyzer._builtin_name_status(
            owner, cls, name) == 'confirmed_builtin')

    def typing_name(node):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            return False
        name = ast.unparse(node)
        head, dot, tail = name.partition('.')
        imported = analyzer.imports.get(owner.module, {}).get(head, '')
        canonical = imported + (dot + tail if dot else '')
        return (head not in shadowed and canonical in {'typing.' + item for item in _TYPING}
                and 'typing' not in analyzer.module_bodies
                and analyzer._stable_import_name(owner.module + '.' + head))

    def annotation(node):
        if isinstance(node, ast.Constant):
            return type(node.value) in (str, type(None)) or node.value is Ellipsis
        if isinstance(node, ast.Name):
            return node.id in _SCALARS and builtin(node.id) or typing_name(node)
        if isinstance(node, (ast.Tuple, ast.List)):
            return all(annotation(value) for value in node.elts)
        if isinstance(node, ast.Subscript):
            return typing_name(node.value) and annotation(node.slice)
        if isinstance(node, ast.Attribute):
            if typing_name(node):
                return True
            root = node
            while isinstance(root, ast.Attribute):
                if root.attr.startswith('_'):
                    return False
                root = root.value
            if not isinstance(root, ast.Name) or root.id in shadowed:
                return False
            imported = analyzer.imports.get(owner.module, {}).get(root.id)
            # An imported reference can still execute module attribute hooks.
            # The emitted lookup predicate retains that uncertainty.
            return bool(imported and analyzer._stable_import_name(owner.module + '.' + root.id))
        return False

    def literal(node):
        try:
            ast.literal_eval(node)
            return True
        except (ValueError, TypeError, RecursionError):
            return False

    for member in cls.body:
        if isinstance(member, ast.FunctionDef):
            decorators = member.decorator_list
            if decorators:
                if (len(decorators) == 1 and isinstance(decorators[0], ast.Name)
                        and decorators[0].id == 'property' and builtin('property')):
                    properties.add(member.name)
                elif (len(decorators) == 1 and isinstance(decorators[0], ast.Attribute)
                        and isinstance(decorators[0].value, ast.Name)
                        and decorators[0].value.id == member.name and member.name in properties
                        and decorators[0].attr in ('setter', 'getter', 'deleter')):
                    pass
                else:
                    return False
            else:
                properties.discard(member.name)
            defaults = member.args.defaults + [v for v in member.args.kw_defaults if v is not None]
            arguments = member.args.posonlyargs + member.args.args + member.args.kwonlyargs
            arguments += [v for v in (member.args.vararg, member.args.kwarg) if v is not None]
            annotations = [arg.annotation for arg in arguments if arg.annotation is not None]
            if member.returns is not None:
                annotations.append(member.returns)
            if not all(literal(value) for value in defaults) or not all(map(annotation, annotations)):
                return False
        elif isinstance(member, (ast.Assign, ast.AnnAssign)):
            targets = member.targets if isinstance(member, ast.Assign) else [member.target]
            if not all(isinstance(target, ast.Name) for target in targets):
                return False
            value = member.value
            if value is not None and not literal(value):
                if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id == 'dict' and builtin('dict') and not value.args
                        and all(keyword.arg is not None and literal(keyword.value)
                                for keyword in value.keywords)):
                    return False
            if isinstance(member, ast.AnnAssign) and not annotation(member.annotation):
                return False
        elif not (isinstance(member, ast.Pass) or isinstance(member, ast.Expr)
                  and isinstance(member.value, ast.Constant) and type(member.value.value) is str):
            return False
        shadowed.update(statement_scope_facts([member]).bound)
    return True


## Describe a bounded conditional reference to a source initializer signature.
#  @param summary Current source caller and prior call facts.
#  @param node Constructor AST call with evaluated arguments.
#  @param fact Ordinary constructor binding, whose unconfirmed status is retained.
#  @param call_id Current constructor call identity for budget diagnostics.
#  @return Signature-only reference with a required lookup predicate, or None.
def signature_reference(summary, node, fact, call_id):
    analyzer = summary.analyzer
    if (not getattr(analyzer, '_conditional_source_state', False)
            or fact['status'] != 'unconfirmed' or fact['phase'] != '__init__'
            or not fact['issues'] or any(issue['reason'] not in (
                'constructor_class_origin_unconfirmed', 'constructor_namespace_unconfirmed',
                'constructor_definition_evaluation_unconfirmed') for issue in fact['issues'])):
        return None
    identity = fact['receiver_class']
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    if not hierarchy or len(hierarchy) != 1:
        return None
    owner, cls = hierarchy[0]
    if cls.keywords or cls.decorator_list or analyzer.definition_conditions.get(owner):
        return None
    if (sum(1 for _ in islice(ast.walk(cls), _LIMIT + 1)) > _LIMIT
            or sum(1 for _ in islice(ast.walk(summary.node), _LIMIT + 1)) > _LIMIT):
        summary.result.boundaries.append({'reason': 'conditional_source_budget',
                                          'call_id': call_id})
        return None
    if not _namespace(summary, owner, cls):
        return None
    writes, truncated = analyzer._class_binding_writes()
    if truncated or any(written == owner and attribute in (
            '__init__', '__new__', '__class__', '__bases__', '*')
            for written, attribute, _, _, _ in writes):
        return None
    probes = []
    ast_calls = {(value.lineno, value.col_offset): value for value in ast.walk(summary.node)
                 if isinstance(value, ast.Call)}
    for prior in summary.calls:
        exposed = [value for argument in prior.argument_sources for value in argument['sources']
                   if value.get('class_type') == identity]
        if not exposed:
            continue
        if any(value.get('value_incomplete') or value.get('import_incomplete')
               or value.get('import_modified') or value.get('class_lookup_mutations')
               or not isinstance(value.get('source_class_origin'), dict)
               for value in exposed):
            return None
        expression = ast_calls.get((prior.lineno, prior.col_offset))
        if (not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Name)
                or expression.func.id != 'isinstance' or len(expression.args) != 2
                or expression.keywords or not isinstance(expression.args[1], ast.Name)
                or expression.args[1].id != cls.name
                or analyzer._builtin_name_status(summary.ref, summary.node, 'isinstance')
                   != 'confirmed_builtin'):
            return None
        probes.append(prior.id)
    if not probes:
        return None
    predicate = {'kind': 'source_constructor_lookup', 'status': 'required',
        'receiver_class': copy.deepcopy(identity), 'target': copy.deepcopy(fact['target']),
        'runtime_confirmed': False, 'feasibility': 'not_proven',
        'scope': 'signature_only', 'preceding_type_checks': probes}
    return {'kind': 'conditional_constructor_signature', 'status': 'required',
        'scope': 'signature_only', 'target': copy.deepcopy(fact['target']),
        'receiver_class': copy.deepcopy(identity), 'runtime_target_confirmed': False,
        'feasibility': 'not_proven', 'conditions': copy.deepcopy(summary.conditions) + [predicate],
        'unconfirmed_binding_issues': copy.deepcopy(fact['issues']),
        'source_hashes': dict(analyzer.hashes), 'assumptions': copy.deepcopy(fact['assumptions'])}
