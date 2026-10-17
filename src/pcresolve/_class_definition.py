## @package pcresolve._class_definition
#  Restricted namespace evaluation shared by source class binding proofs.

import ast
from dataclasses import replace

from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts
from ._stdlib_function_decorators import namespace_function_decorator

_CLASS_DEFINITION_NODE_LIMIT = 2000


def _literal(value):
    if value is None or any(isinstance(node, ast.Call) for node in ast.walk(value)):
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


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
            for _ in ast.walk(cls):
                inspected[0] += 1
                if inspected[0] > _CLASS_DEFINITION_NODE_LIMIT:
                    raise _ClassEffectLimit()
            shadowed = set()
            for member in cls.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if declaration is not None and declaration(owner, cls, member):
                        shadowed.update(statement_scope_facts([member]).bound)
                        continue
                    ref = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)
                    if member.decorator_list and analyzer._descriptor_kind((ref, member)) is None:
                        premise = (namespace_function_decorator(
                            analyzer, owner, member, shadowed, dependencies)
                            if assumptions is not None else None)
                        if premise is None:
                            issues.append(('namespace_unconfirmed', owner, member))
                        else:
                            assumptions.add(premise)
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
                shadowed.update(statement_scope_facts([member]).bound)
        return issues

    return inspect(hierarchy, ())
