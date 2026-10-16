## @package pcresolve._constructor_binding
#  Source-only implicit receiver binding for one constructor invocation phase.

import ast
import copy
from dataclasses import asdict

from .scope_facts import statement_scope_facts
from .effect_facts import contains_yield
from ._constructor_entry import source_member, _definition_issues
from .class_attribute_effects import _ClassEffectLimit


## Explain one selected constructor phase without claiming initialized instance state.
#  @param summary Current caller summary and source snapshot.
#  @param node Explicit source class call; its arguments have been evaluated.
#  @param class_ref Source class object selected before argument evaluation.
#  @param target Selected source allocator or ordinary initializer definition.
#  @param values Saved callee expression provenance, before argument evaluation.
#  @param invalidated Whether that class escaped or changed during argument evaluation.
#  @return Conditional lookup/implicit binding facts, with explicit proof issues.
def source_binding(summary, node, class_ref, target, values, invalidated):
    analyzer = summary.analyzer
    ref, method = target
    phase = method.name
    initializer = phase == '__init__'
    scope = 'init_invocation_only' if initializer else 'new_invocation_only'
    issues = []

    def issue(reason, owner=None, source=None):
        item = {'reason': reason}
        if source is not None:
            item['evidence'] = summary.evidence_at(owner or class_ref, source)
        if item not in issues:
            issues.append(item)

    identity = asdict(class_ref)
    if (invalidated or not values or not all(value.get('class_type') == identity
            and (value.get('kind') == 'class' or value.get('source_class_origin', {}).get(
                'basis') == 'source_symbol' and value['source_class_origin'].get('class') == identity)
            and value.get('relation') == 'direct' and not any(value.get(flag) for flag in (
                'projection', 'output_path', 'value_incomplete', 'import_modified',
                'import_incomplete', 'attribute_provenance')) for value in values)):
        issue('constructor_class_origin_unconfirmed')
    parameters = method.args.posonlyargs + method.args.args
    if not parameters:
        issue('implicit_receiver_parameter_missing', ref, method)
    if initializer:
        if method.decorator_list or not analyzer._ordinary_construction(class_ref):
            issue('constructor_initialization_unconfirmed', ref, method)
    elif (phase != '__new__'
            or method.decorator_list and analyzer._descriptor_kind(target) != 'staticmethod'):
        issue('constructor_new_descriptor_unconfirmed', ref, method)
    for keyword in node.keywords:
        if keyword.arg is not None:
            continue
        value = keyword.value
        if (isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Constant))
                or isinstance(value, ast.Dict) and any(isinstance(key, ast.Constant)
                    and type(key.value) is not str for key in value.keys)):
            issue('constructor_expansion_unconfirmed', summary.ref, value)
    hierarchy = analyzer._class_mro(class_ref.module, class_ref.qualname)
    if not hierarchy or len(hierarchy) > 64:
        issue('constructor_mro_unconfirmed')
    checked = (hierarchy or [])[:64]
    definition_paths = set()
    try:
        for reason, owner, source in _definition_issues(analyzer, checked, definition_paths):
            issue('constructor_' + reason, owner, source)
    except _ClassEffectLimit:
        issue('constructor_class_definition_budget')
    selected = None
    for owner, cls in checked:
        if cls.keywords or cls.decorator_list:
            issue('constructor_class_lookup_customization', owner, cls)
        if owner != class_ref and any('__init_subclass__' in
                statement_scope_facts([member]).bound for member in cls.body):
            issue('constructor_class_creation_hook', owner, cls)
        members = [member for member in cls.body
                   if phase in statement_scope_facts([member]).bound]
        if selected is None and members:
            selected = owner, source_member(analyzer, owner, cls, phase)
    owner_name = ref.qualname.rpartition('.')[0]
    if (selected is None or selected[0].module != ref.module
            or selected[0].qualname != owner_name or selected[1] != target):
        issue('constructor_phase_lookup_conflict')
    writes, truncated = analyzer._class_binding_writes()
    if truncated:
        issue('constructor_binding_budget')
    for written, attribute, reason, owner, source in writes:
        if any(written == item[0] for item in checked) and attribute in (
                '__new__', phase, '__class__', '__bases__', '*'):
            issue(reason, owner, source)
    assumptions = ['source_snapshot_bindings_hold', 'builtin_type_call_and_new_binding',
                   'no_external_monkeypatch_or_import_hook',
                   'no_unmodeled_indirect_class_mutation']
    if len(analyzer._definition_index.find(ref.module, ref.qualname)) > 1:
        assumptions.append('stdlib_typing_overload_binding')
    paths = {item[0].file_path for item in checked} | {ref.file_path, summary.ref.file_path} | definition_paths
    return {'status': 'unconfirmed' if issues else 'source_bound',
        'basis': 'source_snapshot', 'phase': phase,
        'execution_scope': scope, 'instance_state': 'unmodeled',
        'body_execution': ('synchronous' if isinstance(method, ast.FunctionDef)
                           and not contains_yield(method) else 'deferred'),
        'runtime_target_confirmed': False, 'target': asdict(ref),
        'receiver_class': identity,
        'definition_class': asdict(selected[0]) if selected else None,
        'implicit_binding': {'argument': {'constructor_instance' if initializer else 'constructor_class': True},
            'parameter': parameters[0].arg if parameters else None,
            'status': 'unconfirmed' if issues else 'static_bound',
            'receiver_class': identity},
        'call_evidence': summary.evidence(node),
        'class_sources': copy.deepcopy(values),
        'conditions': copy.deepcopy(summary.conditions),
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)
                          if path in analyzer.hashes},
        'assumptions': assumptions, 'issues': issues}
