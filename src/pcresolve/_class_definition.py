## @package pcresolve._class_definition
#  Restricted namespace evaluation shared by source class binding proofs.

import ast
from dataclasses import replace

from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts
from ._stdlib_function_decorators import namespace_function_decorator
from ._property_namespace import property_declaration

_CLASS_DEFINITION_NODE_LIMIT = 2000


def _namespace_syntax(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Function bodies are deferred. Defaults, annotations and decorators
            # can execute while forming the class namespace and remain in scope.
            children = []
            for name, value in ast.iter_fields(node):
                if name == 'body':
                    continue
                if isinstance(value, ast.AST):
                    children.append(value)
                elif isinstance(value, list):
                    children.extend(item for item in value if isinstance(item, ast.AST))
        else:
            children = list(ast.iter_child_nodes(node))
        pending.extend(reversed(children))


def _literal(value):
    if value is None or any(isinstance(node, ast.Call) for node in ast.walk(value)):
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


def _source_function_decoration(analyzer, target, dependencies, assumptions):
    # Reuse the bounded execution-effect proof; identity alone permits unknown
    # helper calls and is not enough to authorize class namespace formation.
    decorator = analyzer._decorator_definition(target)
    if decorator is None or not isinstance(decorator[1], ast.FunctionDef):
        return None
    active = getattr(analyzer, '_namespace_decoration_active', set())
    ref = target[0]
    if ref in active or len(active) >= 8:
        return None
    analyzer._namespace_decoration_active = active
    active.add(ref)
    try:
        facts = analyzer._decoration_facts(target)
    finally:
        active.remove(ref)
    if (len(facts) != 1 or facts[0]['body_binding_status'] != 'preserved'
            or facts[0]['identity_status'] != 'preserved' or facts[0]['boundaries']):
        return None
    fact = facts[0]
    if dependencies is not None:
        dependencies.update(fact['source_hashes'])
    assumptions.update(fact['assumptions'])
    return 'source_function_namespace_preservation'


## Identify class-definition operations that can change a source namespace.
#  @param analyzer Snapshot lookup machinery confirming builtin method descriptors.
#  @param hierarchy Bounded source MRO, whose metaclasses/hooks are checked separately.
#  @param declaration Optional predicate confirming a harmless typing declaration.
#  @param dependencies Optional set collecting additional source construction premises.
#  @param assumptions Optional set enabling and collecting standard decorator premises.
#  @return Tuples of neutral issue reason, source owner and AST witness.
#  @throws _ClassEffectLimit When inspecting the hierarchy exceeds the node limit.
def namespace_issues(analyzer, hierarchy, declaration=None, dependencies=None,
                     assumptions=None):
    inspected = [0]

    def plain_instance(value, owner, shadowed, seen):
        if (not isinstance(value, ast.Call) or value.args or value.keywords
                or not isinstance(value.func, (ast.Name, ast.Attribute))):
            return False
        try:
            name = ast.unparse(value.func)
        except RecursionError:
            raise _ClassEffectLimit()
        head = name.partition('.')[0]
        if head in shadowed or not analyzer._stable_import_name(owner.module + '.' + head):
            return False
        target = analyzer._resolve_class(owner, name)
        if target is None or '.' in target[0].qualname or target[0] in seen:
            return False
        if not analyzer._stable_import_name(target[0].module + '.' + target[0].qualname):
            return False
        sources = analyzer._class_mro(target[0].module, target[0].qualname)
        forbidden = {'__new__', '__init__', '__init_subclass__', '__set_name__',
                     '__getattribute__', '__getattr__', '__del__'}
        if (not sources or len(sources) > 64 or any(cls.keywords or cls.decorator_list
                or analyzer.definition_conditions.get(ref)
                or forbidden & statement_scope_facts(cls.body).bound for ref, cls in sources)):
            return False
        writes, truncated = analyzer._class_binding_writes()
        if truncated:
            raise _ClassEffectLimit()
        if any(attribute in forbidden | {'__class__', '__bases__', '*'}
               and any(written == ref for ref, _ in sources)
               for written, attribute, _, _, _ in writes):
            return False
        if inspect(sources, seen):
            return False
        if dependencies is not None:
            dependencies.update(ref.file_path for ref, _ in sources)
        return True

    def inspect(sources, seen):
        if len(seen) > 32:
            raise _ClassEffectLimit()
        issues = []
        for owner, cls in sources:
            if owner in seen:
                issues.append(('namespace_unconfirmed', owner, cls))
                continue
            for _ in _namespace_syntax(cls):
                inspected[0] += 1
                if inspected[0] > _CLASS_DEFINITION_NODE_LIMIT:
                    raise _ClassEffectLimit()
            shadowed = set()
            properties = set()
            for member in cls.body:
                property_premise = None
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if declaration is not None and declaration(owner, cls, member):
                        bound = statement_scope_facts([member]).bound
                        shadowed.update(bound)
                        properties.difference_update(bound)
                        continue
                    ref = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)
                    if member.decorator_list and analyzer._descriptor_kind((ref, member)) is None:
                        property_premise = (property_declaration(
                            analyzer, owner, member, shadowed, properties, dependencies)
                            if assumptions is not None else None)
                        premise = property_premise or (namespace_function_decorator(
                            analyzer, owner, member, shadowed, dependencies)
                            if assumptions is not None else None)
                        if premise is None and assumptions is not None:
                            premise = _source_function_decoration(
                                analyzer, (ref, member), dependencies, assumptions)
                        if premise is None:
                            issues.append(('namespace_unconfirmed', owner, member))
                        else:
                            assumptions.add(premise)
                            if property_premise:
                                assumptions.add('no_unmodeled_indirect_builtin_mutation')
                    expressions = member.args.defaults + [v for v in member.args.kw_defaults if v is not None]
                    parameters = member.args.posonlyargs + member.args.args + member.args.kwonlyargs
                    parameters += [arg for arg in (member.args.vararg, member.args.kwarg) if arg is not None]
                    expressions += [arg.annotation for arg in parameters if arg.annotation is not None]
                    if member.returns is not None:
                        expressions.append(member.returns)
                    if any(not (isinstance(value, ast.Name) or _literal(value)) for value in expressions):
                        issues.append(('definition_evaluation_unconfirmed', owner, member))
                elif isinstance(member, (ast.Assign, ast.AnnAssign)):
                    targets = member.targets if isinstance(member, ast.Assign) else [member.target]
                    if (not all(isinstance(target, ast.Name) for target in targets)
                            or member.value is not None and not (_literal(member.value)
                                or plain_instance(member.value, owner, shadowed, seen + (owner,)))
                            or isinstance(member, ast.AnnAssign)
                            and not isinstance(member.annotation, (ast.Name, ast.Constant))):
                        issues.append(('namespace_unconfirmed', owner, member))
                elif not (isinstance(member, ast.Pass) or isinstance(member, ast.Expr)
                          and isinstance(member.value, ast.Constant) and isinstance(member.value.value, str)):
                    issues.append(('namespace_unconfirmed', owner, member))
                bound = statement_scope_facts([member]).bound
                shadowed.update(bound)
                properties.difference_update(bound)
                if property_premise:
                    properties.add(member.name)
        return issues

    return inspect(hierarchy, ())
