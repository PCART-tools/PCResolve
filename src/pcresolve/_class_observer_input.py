## @package pcresolve._class_observer_input
#  Class-metadata inputs at the current source class-creation phase.
#  当前源码类创建阶段中的类元数据输入分析。

import ast
import copy
from dataclasses import asdict

from ._class_definition import namespace_issues
from ._function_factory import _canonical
from ._function_metadata_formation import metadata_formation
from ._metadata_calls import _entry
from ._metadata_observer import observer_query
from .class_attribute_effects import _ClassEffectLimit
from .scope_facts import statement_scope_facts


def _inherited_method_documentation(analyzer, hierarchy, owner, name, decorations):
## Prove inherited inspect.getdoc lookup through a closed class MRO.
## 通过封闭的类 MRO 证明继承方法的 inspect.getdoc 查找结果。
#
#  @param analyzer Analyzer holding indexed definitions and source hashes.
#  @param hierarchy Closed class hierarchy in lookup order.
#  @param owner Class whose method requests the documentation.
#  @param name Method name whose documentation is queried.
#  @param decorations Proven class decorations that may affect method identity.
#  @return Source documentation evidence, or None when the lookup is open.
    """Prove inspect.getdoc's inherited method-doc lookup from a closed MRO."""
    positions = [index for index, (candidate, _) in enumerate(hierarchy)
                 if candidate == owner]
    if (len(positions) != 1 or any(cls.keywords or analyzer.definition_conditions.get(ref)
            for ref, cls in hierarchy)
            or any(fact.get('status') != 'source_bound'
                or fact.get('identity_status') != 'preserved'
                or '*' in fact.get('attributes', ())
                or name in fact.get('attributes', ())
                for fact in decorations)):
        return None
    selected = []
    for base_ref, base in hierarchy[positions[0] + 1:]:
        members = [node for node in base.body
                   if name in statement_scope_facts([node]).bound]
        if len(members) > 1:
            return None
        if not members:
            continue
        node = members[0]
        if not isinstance(node, ast.FunctionDef) or node.decorator_list:

    # Walk only bases after the requesting class, matching inherited lookup order.
    # 仅按继承查找顺序检查请求类之后的基类。
            return None
        matches = analyzer._definition_index.find(
            base_ref.module, base_ref.qualname + '.' + name)
        if len(matches) != 1 or matches[0][1] is not node:
            return None
        formation = metadata_formation(analyzer, matches[0])
        if formation is None:
            return None
        documentation = formation['metadata_shapes']['documentation']
        selected.append({'target': asdict(matches[0][0]), 'formation': formation})
        if documentation == ['str']:
            return {'kind': 'source_mro_inherited_method_documentation',
                'lookup': 'stdlib_inspect_getdoc_method_mro',
                'requesting_method': name, 'selected': selected,
                'completion': 'first_nonempty_source_method_documentation',
                'source_hashes': dict(sorted({key: value
                    for item in selected
                    for key, value in item['formation']['source_hashes'].items()}.items())),
                'assumptions': ['source_snapshot_bindings_hold',
                    'stable_source_class_mro', 'stdlib_inspect_getdoc_mro_semantics',
                    'source_function_metadata_formation',
                    'source_class_decorations_preserve_selected_method']}
        if documentation != ['NoneType']:
            return None
    return {'kind': 'source_mro_missing_method_documentation',
        'lookup': 'stdlib_inspect_getdoc_method_mro', 'requesting_method': name,
        'class_hierarchy': [asdict(ref) for ref, _ in hierarchy],
        'selected': selected, 'result_shape': 'NoneType',
        'completion': 'all_source_mro_method_documentation_absent',
        'source_hashes': dict(sorted({key: value for ref, _ in hierarchy
            for key, value in [(ref.file_path, analyzer.hashes.get(ref.file_path))]
            if value}.items())),
        'assumptions': ['source_snapshot_bindings_hold', 'stable_source_class_mro',
            'stdlib_inspect_getdoc_mro_semantics', 'source_function_metadata_formation',
            'source_class_decorations_preserve_selected_method']}


## Bind a single private observer to a source class before its own decorators.
#  @param analyzer Fixed source generation and shared class-effect budget.
#  @param target Exact class whose creation hook is currently being analyzed.
#  @param caller Exact hook or selected source classmethod.
#  @param parameter Implicit class receiver in that method.
#  @param call Immediate Observer(cls).query() invocation with literal query data.
#  @param ancestor_hooks Already proved ancestor phases supplied by the creation orchestrator.
#  @param module_prefix Optional first-module-call input established by the module orchestrator.
#  @return Input and query evidence, or None for any unresolved premise.
def bind_observer_call(analyzer, target, caller, parameter, call, ancestor_hooks=None, module_prefix=None):
    if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute)
            or not isinstance(call.func.value, ast.Call)):
        return None
## 在类自身装饰器运行前，将单个私有观察器绑定到源码类。
#
    constructor = call.func.value
    if (len(constructor.args) != 1 or constructor.keywords
            or not isinstance(constructor.args[0], ast.Name)
            or constructor.args[0].id != parameter):
        return None
    values = list(call.args) + [item.value for item in call.keywords]
    if (any(not isinstance(value, ast.Constant)
            or type(value.value) not in (str, int, bool, type(None)) for value in values)
            or any(item.arg is None for item in call.keywords)
            or len({item.arg for item in call.keywords}) != len(call.keywords)):
        return None
    canonical = _canonical(analyzer, caller[0], caller[1], constructor.func)
    if not canonical:
        return None
    observer = analyzer._definition_index.resolve_qualified([canonical], analyzer.imports,
        kind='class', qualified_guard=analyzer._stable_import_name)
    if observer is None:
        return None
    if ancestor_hooks is None:
        return None
    hierarchy = analyzer._class_mro(target[0].module, target[0].qualname)
    if (not hierarchy or len(hierarchy) > 64 or analyzer.index_boundaries
            or any(cls.keywords or analyzer.definition_conditions.get(owner)
                or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)
                for owner, cls in hierarchy)):
        return None
    decorations = []
    for owner, cls in hierarchy[1:]:
        if not cls.decorator_list:
            continue
        facts = (analyzer._class_decoration_cache.get(owner)
                 if owner in analyzer._class_decoration_cache else None)
        if owner not in analyzer._class_decoration_cache:
            from ._class_decoration import constructor_decorations

    # The class creation hierarchy must be closed and stable before observer reads are trusted.
    # 只有类创建层级完整且稳定时，才信任观察器读取结果。
            facts = constructor_decorations(analyzer, (owner, cls))
        if facts is None:
            return None
        decorations.extend(facts)
    owners = {owner for owner, _ in hierarchy}
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    class_creation_prefix = (module_prefix is not None
        and module_prefix.get('kind') == 'source_class_creation_prefix')
    if module_prefix is None and (truncated or any(owner in owners for owner, _, _, _, _ in writes)):
        return None
    if class_creation_prefix and (truncated or any(owner in owners and reason != 'visible_class_escape'
            for owner, _, reason, _, _ in writes)):
        return None
    query = observer_query(analyzer, observer, call.func.attr,
        positional_literals=tuple(value.value for value in call.args),
        keyword_literals={item.arg: item.value.value for item in call.keywords})
    selected = analyzer._definition_index.find(observer[0].module,
        observer[0].qualname + '.' + call.func.attr)
    entry = _entry(analyzer, selected[0]) if len(selected) == 1 and query is not None else None
    if entry is None:
        return None
    prefixes = query['input_preconditions']['member_prefixes']
    # Native object members are outside the source-function formation proof.
    if (not prefixes or any(not prefix or prefix.startswith('__') for prefix in prefixes)
            or any(name.startswith(tuple(prefixes)) for name in vars(object))):
        return None
    if class_creation_prefix and any(name == '*' or name.startswith(tuple(prefixes))
            for name in module_prefix.get('possible_class_writes', ())):
        return None
    if namespace_issues(analyzer, hierarchy, assumptions=set()):
        return None
    # The current creation proof is deliberately not a dependency of its own
    # input. Only completed ancestor phases can precede the fresh namespace.
    # The orchestrator appends the current hook after this function returns.
    # Keep the already completed prefix, not a live reference to that list.
    ancestors = copy.deepcopy(list(ancestor_hooks))
    prior = {name for fact in ancestors for name in fact['attributes']}
    special = {'*', '__class__', '__bases__', '__dict__', '__mro__'}
    if special & prior or any(name.startswith(tuple(prefixes)) for name in prior):
        return None
    # 原生 object 成员不属于源码函数形成证明的覆盖范围。
    generated = []
    for fact in decorations:
        if special & set(fact['attributes']):
            return None
        deferred = fact.get('deferred_functions', {})
        candidates = deferred.get('generated_class_members',
                                 fact.get('generated_class_members', []))
        sites = deferred.get('class_write_sites', fact.get('class_write_sites', []))
        for name in fact['attributes']:

            if not name.startswith(tuple(prefixes)):
                continue
            changed = [site for site in sites if site['attribute'] == name]
            direct_alias = (fact.get('kind') == 'source_class_alias_decoration'
                and any(member.get('attribute') == name
    # 当前创建证明不会反过来成为自身输入的前提，只使用已完成的祖先阶段快照。
                    and member.get('kind') == 'source_alias_method'
                    and member.get('evidence') for member in candidates))
            if not changed and direct_alias:
                continue
            if not changed or any(not any(member['attribute'] == name
                    and member['store_evidence'] == site['statement_evidence'] for member in candidates)
                    for site in changed):
                return None
        generated.extend({**member, '_source_class_decoration': fact} for member in candidates
                         if member['attribute'].startswith(tuple(prefixes)))
    members, seen, assumptions = [], set(), set(query['assumptions'] + entry['assumptions'])
    hashes = {**query['source_hashes'], **entry['source_hashes']}
    for fact in decorations:
        assumptions.update(fact['assumptions'])
        hashes.update(fact['source_hashes'])
    for member in generated:
        formation = member.get('metadata_formation')
        if (formation is None and member.get('kind') == 'source_alias_method'
                and member.get('function_metadata') == 'functools_wraps_then_alias_name_and_doc'
                and member.get('wrapper_body') == 'forward_same_arguments_to_target_method'):
            decoration = member.get('_source_class_decoration', {})
            owner = next((owner for owner, _ in hierarchy
                if asdict(owner) == decoration.get('receiver_class')), None)
            target_method = member.get('target_method')
            target_members = (analyzer._definition_index.find(
                owner.module, owner.qualname + '.' + target_method)
                if owner is not None and isinstance(target_method, str) else [])
            if len(target_members) != 1 or not isinstance(target_members[0][1], ast.FunctionDef):
                return None
            target_formation = metadata_formation(analyzer, target_members[0])
            if target_formation is None or target_formation['metadata_shapes']['module'] != ['str']:
                return None
            formation = {'kind': 'source_alias_function_metadata_formation',
                'status': 'source_bound', 'target': asdict(target_members[0][0]),
                'metadata_shapes': {'module': ['str'], 'documentation': ['str']},
                'alias_fact': copy.deepcopy(decoration),
                'target_metadata_formation': target_formation,
                'source_hashes': dict(sorted({**target_formation['source_hashes'],
                    **decoration.get('source_hashes', {})}.items())),
                'assumptions': sorted(set(target_formation['assumptions'] +
                    decoration['assumptions'] + ['source_alias_decorator_sets_documentation']))}
            member = {**copy.deepcopy(member), 'metadata_formation': formation}
            member.pop('_source_class_decoration', None)
            hashes.update(target_formation['source_hashes'])
        elif '_source_class_decoration' in member:
            member = {key: value for key, value in member.items()
                      if key != '_source_class_decoration'}
        if formation is None:
            return None
        if (formation['metadata_shapes']['module'] != ['str']
                or query['callable_metadata_queries']
                and formation['metadata_shapes']['documentation'] != ['str']):
            return None
        members.append(copy.deepcopy(member))
        assumptions.update(formation['assumptions'])
        hashes.update(formation['source_hashes'])
    inspected = 0
    for owner, cls in hierarchy:
        bindings = []
        for node in cls.body:
            inspected += 1
            analyzer._class_effect_fact_steps -= 1
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if inspected > 2000 or analyzer._class_effect_fact_steps < 0:
                raise _ClassEffectLimit()
            bindings.append(statement_scope_facts([node]).bound)
        counts = {}
        for bound in bindings:
            for name in bound:
                counts[name] = counts.get(name, 0) + 1
        for node, bound in zip(cls.body, bindings):
            for name in sorted(bound):
                if not name.startswith(tuple(prefixes)):
                    continue
                # Ancestor metadata may be inspected by MRO queries even when
                # the final class shadows the same spelling.
                if name in seen and not query['native_mro_queries']:
                    continue
                seen.add(name)
                if counts[name] != 1:
                    return None
                if not isinstance(node, ast.FunctionDef) or node.name != name:
                    return None
                matches = analyzer._definition_index.find(owner.module, owner.qualname + '.' + name)
                if len(matches) != 1 or matches[0][1] is not node:
                    return None
                formation = metadata_formation(analyzer, matches[0])
                if formation is None or formation['metadata_shapes']['module'] != ['str']:
                    return None
                # None documentation may initiate inspect's inherited lookup.
                documentation_resolution = None
                if (query['callable_metadata_queries']
                        and formation['metadata_shapes']['documentation'] != ['str']):
                    if (module_prefix is None or len(hierarchy) != 1 or node.decorator_list
                            or owner != target[0] or name in vars(object)
                            or formation['metadata_shapes']['documentation'] != ['NoneType']):
                        if (module_prefix is None
                                or module_prefix.get('kind') != 'source_class_creation_prefix'
                                or module_prefix.get('status') != 'source_bound'
                                or module_prefix.get('receiver_class') != asdict(target[0])
                                or module_prefix.get('phase') != 'after_class_body_before_class_decorators'
                                or module_prefix.get('class_hierarchy') != [asdict(item[0])
                                    for item in hierarchy]
                                or node.decorator_list or name in vars(object)
                                or formation['metadata_shapes']['documentation'] != ['NoneType']):
                            return None
                        documentation_resolution = _inherited_method_documentation(
                            analyzer, hierarchy, owner, name, decorations)
                        if documentation_resolution is None:
                            return None
                        assumptions.update(documentation_resolution['assumptions'])
                        hashes.update(documentation_resolution['source_hashes'])
                    else:
                        documentation_resolution = {
                            'kind': 'fresh_root_function_documentation_fallback',
                            'target': asdict(matches[0][0]), 'receiver_class': asdict(owner),
                            'phase': 'module_call_entry',
                            'ancestor_namespace': 'builtin_object_without_matching_member',
                            'function_metadata': 'fresh_native_module_name_and_qualname',
                            'runtime_documentation_confirmed': False,
                            'completion': 'normal_metadata_resolution_only'}
                        assumptions.add('source_module_root_function_documentation_resolution')
                members.append({'attribute': name, 'owner_class': asdict(owner),
                    'metadata_formation': formation,
                    **({'documentation_resolution': documentation_resolution}
                       if documentation_resolution is not None else {})})
                assumptions.update(formation['assumptions'])
                hashes.update(formation['source_hashes'])
    for fact in ancestors:
        assumptions.update(fact['assumptions'])
        hashes.update(fact['source_hashes'])
    assumptions.add('source_creation_phase_class_metadata_input')
    phase, dependency = 'before_class_decorators', 'ancestor_phases_only'
    if module_prefix is not None:
        if class_creation_prefix:
            if (module_prefix.get('receiver_class') != asdict(target[0])
                    or module_prefix.get('status') != 'source_bound'
                    or module_prefix.get('phase') != 'after_class_body_before_class_decorators'
                    or asdict(target[0]) not in module_prefix.get('class_hierarchy', ())):
                return None
            phase, dependency = 'class_creation_entry', 'source_class_creation_prefix'
        else:
            if (module_prefix.get('receiver_class') != asdict(target[0]) or len(hierarchy) != 1
                    or module_prefix.get('kind') != 'source_module_fresh_class_prefix'
                    or module_prefix.get('status') != 'source_bound'
                    or module_prefix.get('call_effects') != 'unproved'):
                return None
            phase, dependency = 'module_call_entry', 'source_module_prefix'
        assumptions.update(module_prefix['assumptions'])
        hashes.update(module_prefix['source_hashes'])
    return {'kind': 'source_bound_class_metadata_query', 'status': 'source_bound',
        'caller': asdict(caller[0]), 'receiver_class': asdict(target[0]),
        'query': query, 'entry_binding': entry, 'completion': 'normal_return_only',
        'runtime_execution_confirmed': False,
        'input_binding': {'kind': 'fresh_source_class_metadata', 'phase': phase,
            'creation_dependency': dependency, 'member_prefixes': prefixes,
            **({'class_creation_prefix' if class_creation_prefix else 'module_prefix':
                copy.deepcopy(module_prefix)} if module_prefix is not None else {}),
            'matching_members': members, 'ancestor_creation_hooks': ancestors,
            'ancestor_class_decorations': copy.deepcopy(decorations),
            'namespace': ('source_module_prefix_and_current_call_preservation' if module_prefix is not None
                          else 'no_visible_writes_or_escapes')},
        'call_evidence': {'file_path': caller[0].file_path, 'lineno': call.lineno,
            'col_offset': call.col_offset, 'end_lineno': call.end_lineno,
            'end_col_offset': call.end_col_offset},
        'result_shape': query['result_shape'], 'source_hashes': dict(sorted(hashes.items())),
        'assumptions': sorted(assumptions)}


## Bind a source documentation helper that reads a class through one private observer.
#  @param analyzer Fixed source generation and shared class-effect budget.
#  @param target Exact class whose first module call is being analyzed.
#  @param caller Exact hook or selected source classmethod.
#  @param parameter Implicit class receiver in that method.
#  @param call Helper call receiving the class as its sole argument.
#  @param module_prefix Independently established fresh module-call input.
#  @return Bounded observer and formatting evidence, or None for open behavior.
def bind_documentation_observer_call(analyzer, target, caller, parameter, call, module_prefix):
    if (module_prefix is None or not isinstance(call, ast.Call) or len(call.args) != 1
            or call.keywords or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != parameter):
        return None
    canonical = _canonical(analyzer, caller[0], caller[1], call.func)
    if not canonical:
        return None
    selected = analyzer._definition_index.resolve_qualified(
        [canonical], analyzer.imports, qualified_guard=analyzer._stable_import_name)
    if selected is None:
        return None
    helper_ref, helper = selected
## 绑定通过单个私有观察器读取类信息的源码文档辅助函数。
#
    args = helper.args
    parameters = args.posonlyargs + args.args
    body = helper.body[1:] if (helper.body and isinstance(helper.body[0], ast.Expr)
        and isinstance(helper.body[0].value, ast.Constant)
        and type(helper.body[0].value.value) is str) else helper.body
    if (not isinstance(helper, ast.FunctionDef) or helper.decorator_list
            or len(parameters) != 1 or parameters[0].annotation is not None
            or args.defaults or args.kwonlyargs or args.vararg or args.kwarg
            or helper.returns is not None or len(body) != 2):
        return None
    receiver_parameter = parameters[0].arg
    assignment, returned = body
    if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
            or not isinstance(assignment.targets[0], ast.Name)
            or not isinstance(assignment.value, ast.Call)
            or len(assignment.value.args) != 1 or assignment.value.keywords
            or not isinstance(assignment.value.args[0], ast.Name)
            or assignment.value.args[0].id != receiver_parameter):
        return None
    observer_name = assignment.targets[0].id
    observer_canonical = _canonical(analyzer, helper_ref, helper, assignment.value.func)
    if not observer_canonical:
        return None
    observer = analyzer._definition_index.resolve_qualified(
        [observer_canonical], analyzer.imports, kind='class',
        qualified_guard=analyzer._stable_import_name)
    if observer is None or not isinstance(returned, ast.Return):
        return None
    expression = returned.value
    branches = (expression.body, expression.orelse) if isinstance(expression, ast.IfExp) else (expression,)
    if isinstance(expression, ast.IfExp):
        # Branch selection is irrelevant to the string result, but the test may
        # not observe or expose the class passed to the helper.
        if (any(isinstance(node, ast.Call) for node in ast.walk(expression.test))
                or any(isinstance(node, ast.Name) and node.id in (receiver_parameter, observer_name)
                       for node in ast.walk(expression.test))):
            return None

    method_queries = []
    for branch in branches:
        calls = [node for node in ast.walk(branch) if isinstance(node, ast.Call)]
        observer_calls = [node for node in calls if isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == observer_name]
        joins = [node for node in calls if isinstance(node.func, ast.Attribute)
                 and node.func.attr == 'join']
        if (len(observer_calls) != 1 or len(joins) != 1 or len(calls) != 2
                or joins[0].args != observer_calls or joins[0].keywords
                or not isinstance(joins[0].func.value, ast.Constant)
                or type(joins[0].func.value.value) is not str):
            return None
        query_call = observer_calls[0]
        if (query_call.args or len(query_call.keywords) != 1
                or query_call.keywords[0].arg != 'leadingspace'
                or not isinstance(query_call.keywords[0].value, ast.Constant)
                or type(query_call.keywords[0].value.value) is not int):
        # 分支选择不影响字符串结果，但条件表达式不能观察或暴露传入辅助函数的类。
            return None
        if (any(isinstance(node, ast.Name) and node.id in (receiver_parameter, observer_name)
                for node in ast.walk(branch) if node is not query_call.func.value)):
            # The class may enter the observer only through its constructor;
            # the local observer may be used only for the bounded query.
            return None
        query = observer_query(analyzer, observer, query_call.func.attr,
            keyword_literals={'leadingspace': query_call.keywords[0].value.value})
        if (query is None or query['result_shape'] != 'native_string_list'
                or query['input_effects']['source_writes']
                or query['input_effects']['source_exposures']):
            return None
        method_queries.append(query)

    if len({item['target']['qualname'] for item in method_queries}) != len(method_queries):
        return None
    owner, cls = target
    hierarchy = analyzer._class_mro(owner.module, owner.qualname)
    class_creation_prefix = module_prefix.get('kind') == 'source_class_creation_prefix'
    if class_creation_prefix:
        if (module_prefix.get('receiver_class') != asdict(owner)
                or module_prefix.get('status') != 'source_bound'
                or module_prefix.get('phase') != 'after_class_body_before_class_decorators'
                or asdict(owner) not in module_prefix.get('class_hierarchy', ())
                or any(name == '*' for name in module_prefix.get('possible_class_writes', ()))):
            return None
    elif (module_prefix.get('receiver_class') != asdict(owner)
            or module_prefix.get('kind') != 'source_module_fresh_class_prefix'
            or module_prefix.get('status') != 'source_bound'
            or module_prefix.get('call_effects') != 'unproved'):
        return None
    if (not hierarchy or (not class_creation_prefix and len(hierarchy) != 1) or analyzer.index_boundaries
            or analyzer.definition_conditions.get(owner)
            or not analyzer._stable_import_name(owner.module + '.' + owner.qualname)):
        return None
    hashes = dict(module_prefix['source_hashes'])
    assumptions = set(module_prefix['assumptions']) | {
        'source_module_class_documentation_helper',
        'source_snapshot_bindings_hold',
        'documentation_helper_local_observer_alias'}
    for query in method_queries:
        hashes.update(query['source_hashes'])
        assumptions.update(query['assumptions'])
    hashes.update(analyzer.hashes)
    return {'kind': 'source_bound_class_documentation_helper', 'status': 'source_bound',
        'caller': asdict(caller[0]), 'target': asdict(helper_ref),
        'receiver_class': asdict(owner), 'observer_class': asdict(observer[0]),
        'call_evidence': {'file_path': caller[0].file_path, 'lineno': call.lineno,
            'col_offset': call.col_offset, 'end_lineno': call.end_lineno,
            'end_col_offset': call.end_col_offset},
        'observer_methods': [item['target']['qualname'].rsplit('.', 1)[-1]
                             for item in method_queries],
        'observer_queries': method_queries,
        'input_binding': {'kind': 'fresh_source_class_metadata',
            'phase': ('class_creation_entry' if class_creation_prefix else 'module_call_entry'),
            'creation_dependency': ('source_class_creation_prefix' if class_creation_prefix
                                    else 'source_module_prefix'),
            **({'class_creation_prefix' if class_creation_prefix else 'module_prefix':
                copy.deepcopy(module_prefix)}),
            'namespace': ('source_class_creation_prefix_and_read_only_observer'
                          if class_creation_prefix else 'source_module_prefix_and_read_only_observer')},
        'output_shape': 'str', 'completion': 'normal_return_only',
        'runtime_execution_confirmed': False,
        'source_hashes': dict(sorted(hashes.items())),
        'assumptions': sorted(assumptions)}
