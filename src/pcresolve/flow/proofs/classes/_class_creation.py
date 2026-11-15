## @package pcresolve.flow.proofs.classes._class_creation
#  Bounded __init_subclass__ effects before source class decoration.
#  对源码类装饰前的 __init_subclass__ 影响进行有界分析。

import ast
from pcresolve.flow.proofs.classes._class_effect_attributes import written_attributes
import copy
from importlib import import_module
from dataclasses import asdict

from pcresolve.flow.proofs.classes._class_definition import namespace_issues, _namespace_syntax
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.effect_facts import contains_yield, evaluation_contexts
from pcresolve.facts.scope_facts import statement_scope_facts

_ASSUMPTIONS = ['source_snapshot_bindings_hold', 'builtin_type_class_creation_protocol',
    'source_class_creation_effects', 'builtin_type_attribute_writes',
    'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation',
    'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation',
    'no_external_frame_introspection']


## Describe a source node's location for class-creation evidence.
## 描述类创建证据中源码节点的位置。
#
#  @param ref Definition reference carrying the source path.
#  @param node AST node carrying start and end coordinates.
#  @return Mapping of path and source coordinates.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno, 'col_offset': node.col_offset,
            'end_lineno': node.end_lineno, 'end_col_offset': node.end_col_offset}


## Check whether visible class escapes are deferred or bounded doc reads.
## 判断可见的类逃逸是否延后执行或属于有界文档读取。
#
#  @param analyzer Analyzer with the source snapshot and definition index.
#  @param owners Class identities relevant to this creation phase.
#  @param visible Visible class writes and escape records.
#  @return True only when every relevant record is an allowed escape.
def _deferred_class_escapes(analyzer, owners, visible):
    contexts = {}
    for module, bodies in analyzer.module_bodies.items():
        for _, body in bodies:
            for node, requirements in evaluation_contexts(ast.Module(
                    body=body, type_ignores=[])):
                contexts[node] = requirements
    ## Recognize a stable, uniquely defined undecorated source method doc read.
    ## 识别稳定且唯一确定的未装饰源码方法文档读取。
    #
    #  @param owner Class identity whose method documentation is read.
    #  @param source Source reference containing the read.
    #  @param node Candidate attribute read or documentation assignment.
    #  @return True when the read meets the bounded source conditions.
    def source_method_doc_read(owner, source, node):
        source_module = getattr(source, 'module', None)
        if not isinstance(source_module, str) or not source_module:
            return False
        assignment = node if isinstance(node, ast.Assign) else None
        if assignment is not None:
            if (len(assignment.targets) != 1
                    or not isinstance(assignment.targets[0], ast.Attribute)
                    or assignment.targets[0].attr != '__doc__'
                    or not isinstance(assignment.targets[0].value, ast.Name)):
                return False
            member_name = assignment.targets[0].value.id
            module_functions = [item for _, body in analyzer.module_bodies.get(source_module, [])
                for item in body if isinstance(item, ast.FunctionDef) and item.name == member_name]
            class_functions = []
            class_matches = analyzer._definition_index.find(
                source_module, getattr(source, 'qualname', ''), kind='class')
            if len(class_matches) == 1:
                class_functions = [item for item in class_matches[0][1].body
                    if isinstance(item, ast.FunctionDef) and item.name == member_name]
            if len(module_functions) + len(class_functions) != 1:
                return False
            node = assignment.value
        if not isinstance(node, ast.Attribute) or node.attr != '__doc__':
            return False
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name):
            return False
        parts.reverse()
        imported = analyzer.imports.get(source_module, {}).get(current.id)
        if (imported != owner.module or not analyzer._stable_import_name(
                source_module + '.' + current.id)
                or len(parts) != 3 or parts[0] != owner.qualname
                or parts[-1] != '__doc__'):
            return False
        members = analyzer._definition_index.find(
            owner.module, owner.qualname + '.' + parts[1])
        return (len(members) == 1 and isinstance(members[0][1], ast.FunctionDef)
                and members[0][1].name == parts[1] and not members[0][1].decorator_list)

    return all(reason == 'visible_class_escape' and (
            bool(contexts.get(node)) or source_method_doc_read(owner, source, node))
        for owner, _, reason, source, node in visible if owner in owners)


## Bound selected source hooks at class creation, including ancestor creation phases.
## 对类创建阶段选中的源码钩子及祖先创建阶段进行有界分析。
#
#  @param analyzer Fixed source snapshot and query-local class-effect budget.
#  @param target Exact new source class identity and declaration.
#  @return Hook effect records, an empty list for absence, or None for open effects.
def creation_effects(analyzer, target):
    ref, cls = target
    cache = analyzer._class_creation_cache
    if ref in cache:
        return copy.deepcopy(cache[ref])
    # Seed the cache with an open result to stop recursive class hierarchies.
    # 先缓存未确认结果，防止类层次递归时无限展开。
    cache[ref] = None
    sources = analyzer._class_mro(ref.module, ref.qualname)
    if not sources or len(sources) > 64:
        return None
    owners = {owner for owner, _ in sources}
    writes, truncated = analyzer._class_binding_writes()
    if truncated or any(owner in owners and name in ('__init_subclass__', '__class__', '__bases__', '*')
                         for owner, name, _, _, _ in writes):
        return None
    if not any('__init_subclass__' in statement_scope_facts(base.body).bound
               for _, base in sources[1:]):
        cache[ref] = []
        return []
    visible, truncated = analyzer._class_binding_writes(include_escapes=True)
    sensitive = {'__init_subclass__', '__class__', '__bases__', '__dict__', '__func__',
                 '__code__', '__defaults__', '__kwdefaults__', '*'}
    if (truncated or any(owner in owners and name in sensitive
                         and reason != 'visible_class_escape'
                         for owner, name, reason, _, _ in visible)
            or not _deferred_class_escapes(analyzer, owners, visible)):
        return None
    if (analyzer.index_boundaries or any(base.keywords or '.' in owner.qualname
            or analyzer.definition_conditions.get(owner)
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
            for owner, base in sources)):
        return None
    # Accumulate ancestor creation effects before selecting this class's hook.
    # 选择当前类的钩子前，先按创建顺序汇总祖先影响。
    records = []
    for parent in reversed(sources[1:]):
        effects = creation_effects(analyzer, parent)
        if effects is None:
            return None
        for fact in effects:
            if fact not in records:
                records.append(fact)
    selected = None
    for owner, base in sources[1:]:
        members = [node for node in base.body
                   if '__init_subclass__' in statement_scope_facts([node]).bound]
        if not members:
            continue
        if len(members) != 1 or not isinstance(members[0], ast.FunctionDef):
            return None
        matches = analyzer._definition_index.find(owner.module, owner.qualname + '.__init_subclass__')
        if len(matches) != 1 or matches[0][1] is not members[0]:
            return None
        selected = matches[0]
        break
    if selected is None:
        return None
    hook_ref, hook = selected
    args = hook.args
    parameters = args.posonlyargs + args.args
    if (len(parameters) != 1 or args.defaults or args.kwonlyargs or args.vararg
            or hook.returns is not None or parameters[0].annotation is not None or contains_yield(hook)
            or hook.decorator_list and analyzer._descriptor_kind(selected) != 'classmethod'):
        return None
    parameter = parameters[0].arg
    # Super carries an implicit class receiver. It cannot inherit the ordinary
    # expression check's exemption for calls with no explicit protected argument.
    if parameter in statement_scope_facts(hook.body).bound or any(
            isinstance(node, ast.Name) and node.id in ('super', '__class__') for node in ast.walk(hook)):
        return None
    # Namespace and hook analysis share a finite fact budget; exhaustion
    # leaves the effects open rather than asserting that no effect occurred.
    # 命名空间和钩子分析共用有限事实预算；耗尽时保留未确认结果。
    try:
        count = 0
        for _, base in sources:
            for _ in _namespace_syntax(base):
                count += 1
                analyzer._class_effect_fact_steps -= 1
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                if count > 2000 or analyzer._class_effect_fact_steps < 0:
                    return None
        # Namespace evaluation is distinct from invoking deferred method bodies.
        if namespace_issues(analyzer, sources, assumptions=set()):
            return None
        stable, _ = _stable_builtin_namespace(analyzer, hook_ref,
            ('object', 'type', '__build_class__', 'classmethod', 'setattr', 'delattr'))
        if not stable:
            return None

        class_prefix = {'kind': 'source_class_creation_prefix', 'status': 'source_bound',
            'receiver_class': asdict(ref), 'class_hierarchy': [asdict(owner) for owner, _ in sources],
            'phase': 'after_class_body_before_class_decorators',
            'hook': asdict(hook_ref), 'hook_evidence': _span(hook_ref, hook),
            'class_evidence': _span(ref, cls), 'runtime_execution_confirmed': False,
            'completion': 'native_type_creation_prefix_only',
            'source_hashes': dict(sorted(analyzer.hashes.items())),
            'assumptions': ['source_snapshot_bindings_hold', 'builtin_type_class_creation_protocol',
                'source_class_creation_phase_prefix', 'source_module_initialization_completed_before_query',
                'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_class_mutation']}
        call_effects = import_module(__package__ + '._class_creation_calls').creation_calls
        proof = call_effects(analyzer, target, selected, written_attributes(records),
                               ancestor_hooks=records, module_prefix=class_prefix)
    except _ClassEffectLimit:
        return None
    if proof is None:
        return None
    attributes, evidence, calls, queries, metadata_queries, signatures, class_queries = proof
    records.append({'kind': 'source_class_creation_hook', 'status': 'source_bound',
        'basis': 'source_snapshot', 'receiver_class': asdict(ref), 'target': asdict(hook_ref),
        'parameter': parameter, 'phase': 'before_class_decorators',
        'binding': 'implicit_classmethod', 'completion': 'normal_return_only',
        'preserved_scope': 'other_class_attributes', 'attributes': attributes,
        'runtime_hook_confirmed': False, 'class_evidence': _span(ref, cls),
        'hook_evidence': _span(hook_ref, hook),
        'evidence': evidence,
        'source_hashes': dict(sorted(analyzer.hashes.items())), 'assumptions': list(_ASSUMPTIONS)})
    if calls:
        records[-1]['method_calls'] = calls
        records[-1]['assumptions'].append('source_class_creation_call_graph')
    if queries:
        records[-1]['native_type_queries'] = queries
        records[-1]['assumptions'].append('source_class_creation_native_queries')
        records[-1]['assumptions'] = sorted(set(records[-1]['assumptions']).union(
            *(query['source_protocol']['assumptions'] for query in queries)))
    if metadata_queries:
        records[-1]['callable_metadata_queries'] = metadata_queries
        records[-1]['assumptions'] = sorted(set(records[-1]['assumptions']).union(
            *(query['assumptions'] for query in metadata_queries)))
    if signatures:
        records[-1]['signature_creations'] = signatures
        records[-1]['assumptions'] = sorted(set(records[-1]['assumptions']).union(
            *(signature['assumptions'] for signature in signatures)))
    if class_queries:
        records[-1]['class_metadata_queries'] = class_queries
        records[-1]['assumptions'] = sorted(set(records[-1]['assumptions']).union(
            *(query['assumptions'] for query in class_queries)))
    cache[ref] = records
    return copy.deepcopy(records)
