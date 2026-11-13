## @package pcresolve._constructor_binding
#  Source-only implicit receiver binding for one constructor invocation phase.
#  仅基于源码为单个构造阶段推导隐式接收者绑定。

import ast
import copy
from dataclasses import asdict

from .scope_facts import statement_scope_facts
from .effect_facts import contains_yield
from ._constructor_entry import source_member, _definition_issues
from .class_attribute_effects import _ClassEffectLimit
from ._class_decoration import constructor_decorations
from ._class_creation import creation_effects


## Explain one selected constructor phase without claiming initialized instance state.
## 解释选定的构造阶段，但不声称实例状态已经初始化。
#
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

    ## Add a unique proof issue and attach source evidence when available.
    ## 添加唯一的证明问题，并在可用时附加源码证据。
    #
    #  @param reason Machine-readable reason for the failed premise.
    #  @param owner Optional source class owning the evidence location.
    #  @param source Optional syntax node identifying the evidence location.
    #  @return None; the issue is appended only once.
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

    # The first positional parameter is the implicit receiver in either phase.
    # 两个构造阶段的第一个位置参数都作为隐式接收者。
    parameters = method.args.posonlyargs + method.args.args
    if not parameters:
        issue('implicit_receiver_parameter_missing', ref, method)
    if initializer:
        if method.decorator_list or not analyzer._ordinary_construction(
                class_ref, allow_bounded_decorations=True):
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

    # Bound hierarchy expansion so malformed inheritance cannot grow the proof indefinitely.
    # 限制继承层级展开，避免异常继承结构让证明无限增长。
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
    selected = None
    decorations = []
    for owner, cls in checked:
        facts = constructor_decorations(analyzer, (owner, cls))
        if cls.keywords or facts is None:
            issue('constructor_class_lookup_customization', owner, cls)
        for fact in facts or []:
            decorations.append(fact)
            definition_paths.update(fact['source_hashes'])
            definition_assumptions.update(fact['assumptions'])
        members = [member for member in cls.body
                   if phase in statement_scope_facts([member]).bound]

        # MRO order determines the first class that binds this constructor phase.
        # MRO 顺序决定第一个绑定该构造阶段的类。
        if selected is None and members:
            selected = owner, source_member(analyzer, owner, cls, phase)
    hooks = creation_effects(analyzer, checked[0]) if checked else None
    if hooks is None:
        issue('constructor_class_creation_hook')
    for fact in hooks or []:
        definition_paths.update(fact['source_hashes'])
        definition_assumptions.update(fact['assumptions'])
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
    assumptions.extend(sorted(definition_assumptions))
    if len(analyzer._definition_index.find(ref.module, ref.qualname)) > 1:
        assumptions.append('stdlib_typing_overload_binding')
    paths = {item[0].file_path for item in checked} | {ref.file_path, summary.ref.file_path} | definition_paths
    result = {'status': 'unconfirmed' if issues else 'source_bound',
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
    if decorations:
        result['class_decorations'] = decorations
    if hooks:
        result['class_creation_hooks'] = hooks
    return result
