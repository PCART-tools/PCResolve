## @package pcresolve._constructor_entry
#  Source class query bindings, separate from actual call-site evidence.

import ast
from dataclasses import asdict

from .effect_facts import contains_yield
from .scope_facts import statement_scope_facts
from .class_attribute_effects import _ClassEffectLimit
from ._class_definition import namespace_issues
from ._constructor_retention import retained_stores


def _overload_declaration(analyzer, owner, cls, member):
    if (not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            or len(member.decorator_list) != 1
            or not isinstance(member.decorator_list[0], (ast.Name, ast.Attribute))):
        return False
    name = ast.unparse(member.decorator_list[0])
    head, dot, rest = name.partition('.')
    imported = analyzer.imports.get(owner.module, {}).get(head, '')
    if (imported + (dot + rest if dot else '') != 'typing.overload'
            or 'typing' in analyzer.module_bodies
            or not analyzer._stable_import_name(owner.module + '.' + head)):
        return False
    for previous in cls.body:
        if previous is member:
            break
        if head in statement_scope_facts([previous]).bound:
            return False
    parameters = member.args.posonlyargs + member.args.args + member.args.kwonlyargs
    parameters += [arg for arg in (member.args.vararg, member.args.kwarg) if arg is not None]
    annotations = [arg.annotation for arg in parameters] + [member.returns]
    defaults = member.args.defaults + [d for d in member.args.kw_defaults if d is not None]
    return (all(value is None or isinstance(value, (ast.Name, ast.Constant))
                for value in annotations)
            and all(isinstance(value, ast.Constant) for value in defaults))


def _definition_issues(analyzer, hierarchy, dependencies=None, assumptions=None):
    return namespace_issues(analyzer, hierarchy,
        declaration=lambda owner, cls, member: _overload_declaration(analyzer, owner, cls, member),
        dependencies=dependencies, assumptions=assumptions if assumptions is not None else set())


## Select a direct member or one final implementation after proven typing stubs.
#  @param analyzer Source generation and import bindings.
#  @param owner Class reference owning the member.
#  @param cls Class definition whose direct statements determine binding order.
#  @param name Member name, without inherited fallback.
#  @return Exact function pair, or None for ambiguous/assigned/effectful members.
def source_member(analyzer, owner, cls, name):
    members = [member for member in cls.body if name in statement_scope_facts([member]).bound]
    implementations = [member for member in members
                       if not _overload_declaration(analyzer, owner, cls, member)]
    if (not members or len(implementations) != 1 or members[-1] is not implementations[0]
            or not isinstance(implementations[0], (ast.FunctionDef, ast.AsyncFunctionDef))
            or implementations[0].name != name):
        return None
    matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
    return next((item for item in matches if item[1] is implementations[0]), None)


## Describe the first supported invocation of a queried source class.
#  @param analyzer Fixed source generation and bounded lookup machinery.
#  @param class_target Exact source class reference and definition.
#  @param target Selected allocator or ordinary initializer definition.
#  @return Source-only entry binding; no fabricated call site or initialized state.
def binding(analyzer, class_target, target):
    class_ref, cls = class_target
    ref, method = target
    phase = method.name
    issues = []

    def issue(reason, owner=None, source=None):
        item = {'reason': reason}
        if source is not None:
            item['evidence'] = {'file_path': owner.file_path,
                'lineno': source.lineno, 'col_offset': source.col_offset,
                'end_lineno': source.end_lineno, 'end_col_offset': source.end_col_offset}
        if item not in issues:
            issues.append(item)

    hierarchy = analyzer._class_mro(class_ref.module, class_ref.qualname)
    if not hierarchy or len(hierarchy) > 64:
        issue('constructor_mro_unconfirmed')
    checked = (hierarchy or [])[:64]
    definition_paths = set()
    definition_assumptions = set()
    try:
        for reason, owner, source in _definition_issues(
                analyzer, checked, definition_paths, definition_assumptions):
            issue('constructor_' + reason, owner, source)
    except _ClassEffectLimit:
        issue('constructor_class_definition_budget')
    if not analyzer._stable_import_name(class_ref.module + '.' + class_ref.qualname):
        issue('constructor_class_origin_unconfirmed')
    for owner, base in checked:
        if base.keywords or base.decorator_list or analyzer.definition_conditions.get(owner):
            issue('constructor_class_lookup_customization')
        if owner != class_ref and any('__init_subclass__' in
                statement_scope_facts([member]).bound for member in base.body):
            issue('constructor_class_creation_hook')
    parameters = method.args.posonlyargs + method.args.args
    if not parameters:
        issue('implicit_receiver_parameter_missing')
    if not isinstance(method, ast.FunctionDef) or contains_yield(method):
        issue('constructor_entry_deferred')
    if phase == '__new__':
        if method.decorator_list and analyzer._descriptor_kind(target) != 'staticmethod':
            issue('constructor_new_descriptor_unconfirmed')
    elif phase == '__init__':
        if method.decorator_list or not analyzer._ordinary_construction(class_ref):
            issue('constructor_initialization_unconfirmed')
    else:
        issue('constructor_phase_unconfirmed')
    writes, truncated = analyzer._class_binding_writes()
    if truncated:
        issue('constructor_binding_budget')
    affected = {'__new__', '__class__', '__bases__', '*', phase}
    if any(attribute in affected and any(written == owner for owner, _ in checked)
           for written, attribute, _, _, _ in writes):
        issue('constructor_binding_write')
    paths = {owner.file_path for owner, _ in checked} | {ref.file_path} | definition_paths
    assumptions = ['source_snapshot_bindings_hold', 'builtin_type_call_and_new_binding',
                   'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']
    assumptions.extend(sorted(definition_assumptions))
    if len(analyzer._definition_index.find(ref.module, ref.qualname)) > 1:
        assumptions.append('stdlib_typing_overload_binding')
    result = {'query_kind': 'source_class_call',
        'status': 'unconfirmed' if issues else 'source_bound', 'basis': 'source_snapshot',
        'receiver_class': asdict(class_ref), 'target': asdict(ref), 'phase': phase,
        'hierarchy': [asdict(owner) for owner, _ in checked],
        'execution_scope': 'new_invocation_only' if phase == '__new__' else 'init_invocation_only',
        'body_execution': 'synchronous' if isinstance(method, ast.FunctionDef)
                          and not contains_yield(method) else 'deferred',
        'instance_state': 'unmodeled', 'runtime_target_confirmed': False,
        'implicit_binding': {'parameter': parameters[0].arg if parameters else None,
            'status': 'unconfirmed' if issues else 'static_bound',
            'value_kind': 'class' if phase == '__new__' else 'instance'},
        'definition_evidence': {'file_path': class_ref.file_path,
            'lineno': cls.lineno, 'col_offset': cls.col_offset,
            'end_lineno': cls.end_lineno, 'end_col_offset': cls.end_col_offset},
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)
                          if path in analyzer.hashes},
        'assumptions': assumptions,
        'issues': issues}
    result['retained_instance_attribute_stores'] = retained_stores(analyzer, checked, target, result)
    return result
