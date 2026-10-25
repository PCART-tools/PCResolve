## @package pcresolve._class_type_tests
#  Non-escaping class operands of guarded native isinstance/issubclass tests.

import ast
import builtins
import copy

from ._property_namespace import _stable_builtin_namespace
from .class_attribute_effects import _ClassEffectLimit
from .import_facts import import_facts
from ._class_identity import identity_decorations
from .syntax_facts import SyntaxLimit


def _local_import_class(analyzer, ref, scope, head, rest):
    if not isinstance(scope, ast.FunctionDef):
        return None
    matches = [(statement, fact) for statement in scope.body
               if isinstance(statement, ast.ImportFrom) and statement.level == 0
               for fact in import_facts(statement) if fact.python_binding == head]
    if len(matches) != 1:
        return None
    statement, fact = matches[0]
    # Only a unique unconditional import without any other lexical binding can
    # supply this scope's exact class operand. A method saved under the same
    # name remains a function value, not its declaring class.
    probe = copy.copy(scope)
    probe.body = [node for node in scope.body if node is not statement]
    facts = analyzer._scope_facts(probe)
    if head in facts.bound | facts.globals | facts.nonlocals:
        return None
    canonical = fact.module + '.' + fact.name + rest
    return analyzer._definition_index.resolve_qualified([canonical], analyzer.imports,
        kind='class', qualified_guard=analyzer._stable_import_name)


def _namespace(analyzer, ref):
    cached = analyzer._class_type_test_namespace
    if cached is not None:
        return cached
    analyzer._class_type_test_namespace = False
    try:
        stable, _ = _stable_builtin_namespace(analyzer, ref,
            ('isinstance', 'issubclass', 'type', '__build_class__'))
    except _ClassEffectLimit:
        return False
    if not stable:
        return False
    functions = {'isinstance', 'issubclass', '__build_class__'}
    inspected = 0
    for bodies in analyzer.module_bodies.values():
        for _, body in bodies:
            try:
                syntax = analyzer._syntax_facts(body, 1000000 - inspected)
            except SyntaxLimit:
                return False
            for statement in body if syntax is None else (None,):
                parents = {} if syntax is None else syntax.parents
                for node in ast.walk(statement) if syntax is None else syntax.nodes:
                    inspected += 1
                    if inspected > 1000000:
                        return False
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    if syntax is None:
                        for child in ast.iter_child_nodes(node):
                            parents[child] = node
                    # A module or saved builtin function grants a route to the
                    # builtin namespace. This narrower proof does not authorize
                    # reflection through such capabilities.
                    if (isinstance(node, ast.Import) and any(alias.name == 'builtins'
                                                            for alias in node.names)
                            or isinstance(node, ast.ImportFrom) and node.module == 'builtins'
                            and any(not isinstance(getattr(builtins, alias.name, None), type)
                                    for alias in node.names)):
                        return False
                    if isinstance(node, ast.Name) and node.id in functions:
                        parent = parents.get(node)
                        if (not isinstance(node.ctx, ast.Load) or not isinstance(parent, ast.Call)
                                or parent.func is not node):
                            return False
    analyzer._class_type_test_namespace = True
    return True


## Recognize the class operand of a native type test as a non-escaping operand.
#  @param analyzer Fixed source/class/import bindings; no source module is executed.
#  @param ref Lexical source scope containing the call.
#  @param call Actual synchronous call syntax.
#  @param aliases Current scanner names; unknown/shadowed bindings remain open.
#  @return True only for an exact native test and ordinary source/builtin classes.
def native_class_operand(analyzer, ref, call, aliases):
    if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
            or call.func.id not in ('isinstance', 'issubclass') or len(call.args) != 2
            or call.keywords or call.func.id in aliases):
        return False
    candidates = analyzer._definition_index.find(ref.module, ref.qualname)
    if len(candidates) == 1:
        scope = candidates[0][1]
    elif not ref.qualname and len(analyzer.module_bodies.get(ref.module, ())) == 1:
        scope = ast.Module(body=analyzer.module_bodies[ref.module][0][1], type_ignores=[])
    else:
        return False
    if (analyzer._builtin_name_status(ref, scope, call.func.id,
                                      definition_scope=not ref.qualname) != 'confirmed_builtin'
            or not _namespace(analyzer, ref)):
        return False
    pending, count = [call.args[1]], 0
    while pending:
        node = pending.pop()
        count += 1
        if count > 64:
            return False
        if isinstance(node, ast.Tuple):
            pending.extend(node.elts)
            continue
        if not isinstance(node, (ast.Name, ast.Attribute)):
            return False
        name = ast.unparse(node)
        head = name.partition('.')[0]
        if head in aliases and aliases[head] in (None, []):
            return False
        if (isinstance(node, ast.Name) and isinstance(getattr(builtins, node.id, None), type)
                and analyzer._builtin_name_status(ref, scope, node.id,
                    definition_scope=not ref.qualname) == 'confirmed_builtin'):
            continue
        if isinstance(scope, ast.FunctionDef) and head in analyzer._scope_facts(scope).bound:
            target = _local_import_class(analyzer, ref, scope, head, name[len(head):])
        else:
            target = analyzer._resolve_class(ref, name)
        if target is None:
            return False
        hierarchy = analyzer._class_mro(target[0].module, target[0].qualname)
        # With native type/__build_class__ and source bases of metaclass type,
        # the metaclass is type. Namespace values and __init_subclass__ cannot
        # replace that class object's immutable native type. A class decorator
        # can return a different object; admitting it requires an independent
        # normal-return identity proof, never constructor-slot preservation.
        if (not hierarchy or len(hierarchy) > 64
                or any(cls.keywords
                       or analyzer.definition_conditions.get(owner)
                       or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
                       or cls.decorator_list and identity_decorations(analyzer, (owner, cls)) is None
                       for owner, cls in hierarchy)):
            return False
    return True
