## @package pcresolve._class_name_binding
#  Restricted source-snapshot class-name values at a bound helper's entry.

import ast
import copy
from dataclasses import asdict, replace

from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts


def _literal(value):
    if value is None or any(isinstance(node, ast.Call) for node in ast.walk(value)):
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


def _write_name(value, function, receiver, class_name, before):
    """Read only stable, straight-line local names; no incoming default guesses."""
    stores = {}
    for item in ast.walk(function):
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store):
            stores[item.id] = stores.get(item.id, 0) + 1
    assignments = {}
    for item in function.body:
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
            assignments[item.targets[0].id] = item.value, item.lineno
    parameters = {arg.arg for arg in function.args.posonlyargs + function.args.args
                  + function.args.kwonlyargs}

    def root(name, seen=()):
        if name in seen or len(seen) > 16:
            return None
        assigned = assignments.get(name)
        if name in parameters and not stores.get(name):
            return name
        if (stores.get(name) == 1 and assigned and assigned[1] < before
                and isinstance(assigned[0], ast.Name)):
            return root(assigned[0].id, seen + (name,))
        return None

    protected = root(receiver)

    def read(node, seen=()):
        if len(seen) > 32:
            return None
        if isinstance(node, ast.Constant) and type(node.value) is str:
            return node.value if len(node.value) <= 2000 else None
        if (isinstance(node, ast.Attribute) and node.attr == '__name__'
                and isinstance(node.value, ast.Name) and protected
                and root(node.value.id) == protected):
            return class_name
        if isinstance(node, ast.Name) and node.id not in seen:
            assigned = assignments.get(node.id)
            if stores.get(node.id) == 1 and assigned and assigned[1] < before:
                return read(assigned[0], seen + (node.id,))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = read(node.left, seen + ('+',)), read(node.right, seen + ('+',))
            if left is not None and right is not None and len(left) + len(right) <= 2000:
                return left + right
        return None

    return read(value)


def _readonly_call(analyzer, ref, node):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return False
    if node.func.id not in ('super', 'isinstance', 'issubclass'):
        return False
    found = analyzer._definition_index.find(ref.module, ref.qualname)
    return (len(found) == 1 and isinstance(found[0][1], (ast.FunctionDef, ast.AsyncFunctionDef))
            and analyzer._builtin_name_status(ref, found[0][1], node.func.id) == 'confirmed_builtin')


def _global_calls(analyzer):
    cached = getattr(analyzer, '_class_name_global_calls', None)
    if cached is not None:
        return cached
    calls, remaining = [], [1000000]

    def visit(node, ref, depth=0):
        remaining[0] -= 1
        if remaining[0] < 0 or depth > 64:
            raise _ClassEffectLimit()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            expressions = list(getattr(node, 'decorator_list', [])) + list(node.args.defaults)
            expressions += [value for value in node.args.kw_defaults if value is not None]
            expressions += [arg.annotation for arg in node.args.posonlyargs + node.args.args
                            + node.args.kwonlyargs if arg.annotation is not None]
            expressions += [arg.annotation for arg in (node.args.vararg, node.args.kwarg)
                            if arg is not None and arg.annotation is not None]
            if getattr(node, 'returns', None) is not None:
                expressions.append(node.returns)
            for expression in expressions:
                visit(expression, ref, depth + 1)
            return
        if isinstance(node, ast.ClassDef):
            for expression in node.decorator_list + node.bases + [item.value for item in node.keywords]:
                visit(expression, ref, depth + 1)
            child = replace(ref, qualname=(ref.qualname + '.' if ref.qualname else '') + node.name)
            for item in node.body:
                visit(item, child, depth + 1)
            return
        if isinstance(node, ast.Call):
            calls.append((ref, node))
        for child in ast.iter_child_nodes(node):
            visit(child, ref, depth + 1)

    for module, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            ref = replace(analyzer.definitions[0][0], module=module, qualname='', file_path=path, lineno=0)
            for statement in body:
                visit(statement, ref)
    analyzer._class_name_global_calls = calls
    return calls


## Bind a source class's canonical name only within a restricted entry snapshot.
#  @param summary Bound caller summary; incoming origins have already been checked.
#  @param identity Exact source class identity, not a nominal receiver candidate.
#  @param definition Selected helper definition.
#  @param parameter Helper's bound ordinary class parameter.
#  @param call Actual producer call receiving this evidence.
#  @param node Caller AST call, for source evidence and escape disambiguation.
#  @return A conditional literal binding or explicit unconfirmed issues; never cache state.
def source_binding(summary, identity, definition, parameter, call, node):
    analyzer = summary.analyzer
    hierarchy = analyzer._class_mro(identity['module'], identity['qualname'])
    if not hierarchy:
        return None
    ref, cls = hierarchy[0]
    issues = []

    def issue(reason, owner=ref, source=cls):
        item = {'reason': reason, 'evidence': summary.evidence_at(owner, source)}
        if item not in issues:
            issues.append(item)

    if '.' in ref.qualname or not analyzer._stable_import_name(ref.module + '.' + ref.qualname):
        issue('class_name_source_binding_unconfirmed')
    if analyzer.index_boundaries:
        issue('class_name_source_scope_incomplete')
    inspected = 0
    for owner, source_class in hierarchy:
        for item in ast.walk(source_class):
            if inspected >= 2000 or analyzer._class_effect_fact_steps <= 0:
                raise _ClassEffectLimit()
            inspected += 1
            analyzer._class_effect_fact_steps -= 1
        if source_class.keywords or source_class.decorator_list:
            issue('class_name_type_lookup_unconfirmed', owner, source_class)
        if owner != ref and '__init_subclass__' in statement_scope_facts(source_class.body).bound:
            issue('class_name_creation_hook', owner, source_class)
        for function in source_class.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            function_ref = replace(owner, qualname=owner.qualname + '.' + function.name,
                                   lineno=function.lineno)
            parents = {child: parent for parent in ast.walk(function) for child in ast.iter_child_nodes(parent)}
            for item in parents:
                if (isinstance(item, ast.Attribute) and item.attr in ('__name__', '__class__', '__bases__')
                        and isinstance(item.ctx, (ast.Store, ast.Del))):
                    issue('class_name_write_possible', function_ref, item)
                if (isinstance(item, ast.Name) and item.id in ('setattr', 'delattr')
                        and not (isinstance(parents[item], ast.Call) and parents[item].func is item)):
                    issue('class_name_reflective_alias', function_ref, item)
                if (isinstance(item, ast.Attribute) and item.attr in (
                        'setattr', 'delattr', '__setattr__', '__delattr__', '__dict__')):
                    issue('class_name_reflective_write_unconfirmed', function_ref, item)
                if not (isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                        and item.func.id in ('setattr', 'delattr')):
                    continue
                name = (_write_name(item.args[1], function, item.args[0].id, cls.name, item.lineno)
                        if len(item.args) >= 2 and isinstance(item.args[0], ast.Name) else None)
                if (name is None or name in ('__name__', '__class__', '__bases__')
                        or analyzer._builtin_name_status(function_ref, function, item.func.id)
                           != 'confirmed_builtin'):
                    issue('class_name_dynamic_write_unconfirmed', function_ref, item)
    for owner, source_class in hierarchy:
        for member in source_class.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                member_ref = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)
                if member.decorator_list and analyzer._descriptor_kind((member_ref, member)) is None:
                    issue('class_name_namespace_unconfirmed', owner, member)
                expressions = member.args.defaults + [value for value in member.args.kw_defaults if value is not None]
                expressions += [arg.annotation for arg in member.args.posonlyargs + member.args.args
                                + member.args.kwonlyargs if arg.annotation is not None]
                expressions += [arg.annotation for arg in (member.args.vararg, member.args.kwarg)
                                if arg is not None and arg.annotation is not None]
                if member.returns is not None:
                    expressions.append(member.returns)
                if any(not (isinstance(value, ast.Name) or _literal(value)) for value in expressions):
                    issue('class_name_definition_evaluation_unconfirmed', owner, member)
            elif isinstance(member, (ast.Assign, ast.AnnAssign)):
                targets = member.targets if isinstance(member, ast.Assign) else [member.target]
                if (not all(isinstance(target, ast.Name) for target in targets)
                        or member.value is not None and not _literal(member.value)
                        or isinstance(member, ast.AnnAssign)
                        and not isinstance(member.annotation, (ast.Name, ast.Constant))):
                    issue('class_name_namespace_unconfirmed', owner, member)
            elif not (isinstance(member, ast.Pass) or isinstance(member, ast.Expr)
                      and isinstance(member.value, ast.Constant) and isinstance(member.value.value, str)):
                issue('class_name_namespace_unconfirmed', owner, member)
    writes, truncated = ([], False) if issues else analyzer._class_binding_writes(include_escapes=True)
    if truncated:
        raise _ClassEffectLimit()
    for written, attribute, reason, owner, source in writes:
        if written != ref:
            continue
        if reason == 'visible_class_escape':
            current_edge = ((owner.module, owner.qualname, owner.file_path)
                            == (summary.ref.module, summary.ref.qualname, summary.ref.file_path)
                            and summary.evidence_at(owner, source) == summary.evidence(node))
            if current_edge or _readonly_call(analyzer, owner, source):
                continue
            issue('class_name_source_escape', owner, source)
        elif attribute in ('__name__', '__class__', '__bases__', '*'):
            issue('class_name_visible_write', owner, source)
    for owner, source in (() if issues else _global_calls(analyzer)):
        for value in ast.walk(source):
            if not isinstance(value, (ast.Name, ast.Attribute)):
                continue
            name = ast.unparse(value)
            match = analyzer._resolve_class(owner, name) or analyzer._class_symbol(owner.module + '.' + name)
            if match and match[0] == ref:
                issue('class_name_global_activity', owner, source)
                break
    result = {'kind': 'class_name_literal', 'status': 'unconfirmed' if issues else 'source_bound',
        'basis': 'source_snapshot', 'attribute': '__name__', 'value_phase': 'call_entry',
        'runtime_value_confirmed': False, 'receiver_class': copy.deepcopy(identity),
        'target': asdict(definition[0]), 'parameter': parameter, 'call_id': call.id,
        'call_evidence': summary.evidence(node), 'evidence': [summary.evidence_at(ref, cls)],
        'source_hashes': dict(sorted(analyzer.hashes.items())), 'source_scope': 'analysis_source_snapshot',
        'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_name_metadata',
            'source_snapshot_class_name_binding_holds', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_class_mutation'], 'issues': issues}
    if not issues:
        result['literal'] = {'type': 'str', 'value': cls.name}
    return result
