## @package pcresolve.flow.proofs.namespaces.metadata._metadata_entry
#  Shared source declaration and member-lookup obligations for metadata helpers.
#  元数据辅助分析共享的源码声明及成员查找证据要求。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.classes._class_definition import namespace_issues
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.facts.scope_facts import statement_scope_facts


## Capture a source declaration's location.
## 捕获源码声明的位置。
#
#  @param ref Source identity.
#  @param node AST node with source positions.
#  @return Source location dictionary.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Describe a source helper's declaration or independently guarded member binding.
## 描述源码辅助函数的声明或独立守卫的成员绑定。
#
#  @param analyzer Fixed source snapshot and namespace machinery.
#  @param selected Exact source member reference and definition.
#  @param declaration_only Keep lookup integrity as an explicit input obligation.
#  @param private_result_reader Optional injected reader for private result lifetimes.
#  @return Source declaration/binding evidence, or None for unresolved mutations.
def entry(analyzer, selected, declaration_only=False, private_result_reader=None):
    ref, function = selected
    owner_name, dot, _ = ref.qualname.rpartition('.')
    if not dot or '.' in owner_name:
        return None
    owners = analyzer._definition_index.find(ref.module, owner_name, kind='class')
    if len(owners) != 1:
        return None
    owner, cls = owners[0]
    if (cls.bases or cls.keywords or cls.decorator_list or function not in cls.body
            or analyzer.definition_conditions.get(owner)
            or not analyzer._stable_import_name(ref.module + '.' + owner_name)
            or not unmodified(analyzer, ref.module + '.' + ref.qualname)):
        return None
    for member in cls.body:
        if not isinstance(member, ast.FunctionDef):
            continue
        methods = analyzer._definition_index.find(owner.module, owner.qualname + '.' + member.name)
        if len(methods) != 1 or methods[0][1] is not member:
            return None
        if (member.name in ('__new__', '__init_subclass__', '__class_getitem__')
                or analyzer._descriptor_kind(methods[0]) == 'classmethod'):
            return None
        parameters = member.args.posonlyargs + member.args.args
        receiver = parameters[0].arg if parameters else None
        if any(isinstance(node, ast.Attribute) and node.attr == '__class__'
               or isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == 'type' and any(isinstance(arg, ast.Name)
                   and arg.id == receiver for arg in node.args) for node in ast.walk(member)):
            return None
    projections = []
    if not declaration_only:
        # Visible class escapes require a separate private-result lifetime proof.
        # 可见类逃逸需要单独证明私有查询结果的生命周期。
        writes, truncated = analyzer._class_binding_writes(include_escapes=True)
        affected = [item for item in writes if item[0] == owner]
        if truncated or any(item[2] != 'visible_class_escape' for item in affected):
            return None
        if affected:
            if private_result_reader is None:
                return None
            projections = private_result_reader(analyzer, owners[0])
            if projections is None:
                return None
    # Declaration-only evidence deliberately leaves lookup binding as an obligation.
    # 仅声明证据有意将查找绑定保留为待证明条件。
    assumptions = set()
    if namespace_issues(analyzer, [owners[0]], assumptions=assumptions):
        return None
    members = [node for node in cls.body if function.name in statement_scope_facts([node]).bound]
    if members != [function]:
        return None
    assumptions.update(['source_class_member_declaration_shape' if declaration_only
                        else 'source_native_class_member_query_binding', 'builtin_type_class_creation_protocol',
        'source_snapshot_bindings_hold', 'no_external_monkeypatch_or_import_hook',
        'no_unmodeled_indirect_class_mutation'])
    for projection in projections:
        assumptions.update(projection['assumptions'])
    result = {'kind': 'source_native_class_member_query',
        'status': 'requires_source_member_bindings' if declaration_only else 'source_bound',
        'target': asdict(ref), 'owner_class': asdict(owner),
        'class_evidence': _span(owner, cls), 'definition_evidence': _span(ref, function),
        'completion': 'normal_attribute_lookup_only', 'runtime_target_confirmed': False,
        'source_hashes': dict(sorted(analyzer.hashes.items())), 'assumptions': sorted(assumptions)}
    if projections:
        result['private_query_results'] = projections
    return result
